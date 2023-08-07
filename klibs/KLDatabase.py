__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import io
import time
import shutil
import sqlite3
import tempfile
from copy import copy
from collections import OrderedDict

from klibs.KLEnvironment import EnvAgent
from klibs.KLConstants import (
    PY_INT, PY_FLOAT, PY_BOOL, PY_BIN, PY_STR,
    SQL_NUMERIC, SQL_FLOAT, SQL_REAL, SQL_INT, SQL_BOOL, SQL_STR,
    SQL_BIN, SQL_KEY, SQL_NULL, SQL_COL_DELIM_STR,
    QUERY_SEL, TAB, DB_INTERNAL_TABLES,
)
from klibs import P
from klibs.KLInternal import full_trace, iterable, utf8
from klibs.KLRuntimeInfo import session_info_schema


export_history_schema = """
CREATE TABLE export_history (
    id integer primary key autoincrement not null,
    participant_id integer not null references participants(id),
    table_name text not null,
    timestamp float not null
)"""


def _set_type_conversions(export=False):
    # Customizes SQL -> Python type conversions for the current process.
    # During export, this converts boolean columns to be R-style TRUE/FALSE strings.
    # Otherwise, this converts boolean columns to Python True/False.
    if export:
        sqlite3.register_converter("boolean", lambda x: str(bool(int(x))).upper())
        sqlite3.register_converter("BOOLEAN", lambda x: str(bool(int(x))).upper())
    else:
        sqlite3.register_converter("boolean", lambda x: bool(int(x)))
        sqlite3.register_converter("BOOLEAN", lambda x: bool(int(x)))


def _as_column_type(value, col_type):
    # Coerces a value to the correct type for a given database column
    if col_type == PY_BOOL:
        # convert to int because sqlite3 has no native boolean type
        if utf8(value).lower() in ['true', '1']: value = 1
        elif utf8(value).lower() in ['false', '0']: value = 0
        else: raise TypeError
    elif col_type == PY_FLOAT:
        value = float(value)
    elif col_type == PY_INT:
        value = int(value)
    elif col_type == PY_STR:
        value = utf8(value)
        # convert true/false to uppercase for R
        if value.lower() in ['true', 'false']:
            value = value.upper()
    elif col_type == PY_BIN:
        raise NotImplementedError("SQL blob insertion is not supported.")
    else:
        e = "Unknown or unsupported column type '{0}'"
        raise RuntimeError(e.format(col_type))

    return value


def _convert_to_query_format(value, col_name, col_type):
    """Formats a given value for use in an SQL statement string.

    For internal KLibs use.
    
    Args:
        value: The value to convert.
        col_name (str): The name of the database column corresponding to the value.
        col_type (str): A string indicating data type for the corresponding column.
            Must be either 'str', 'int', 'float', or 'bool'.

    Returns:
        str: The value as an SQL-formatted string.

    """
    if value is None:
        return SQL_NULL

    # Get converted value as string & escape string if needed
    try:
        value = utf8(_as_column_type(value, col_type))
    except (TypeError, ValueError):
        e = "Could not coerce '{0}' to type '{1}' for column '{2}'"
        raise ValueError(e.format(value, col_type, col_name))

    if col_type == PY_STR:
        value = u"'{0}'".format(value)

    return value


def _get_user_tables(db):
    # Gets names of all user-defined tables in the database (including 'trials')
    non_user = ['session_info', 'export_history', 'participants']
    return [t for t in db.tables if not t in non_user]
            

def _build_filepath(multi, id_info=None, base=None, joined=[], duplicate=False):
    # If alternate base table or joined tables specified, note this in filename
    tables = ''
    if base != P.primary_table or len(joined):	
        joined_tables = '+'.join(['']+joined)
        primary = base if base != P.primary_table else ''
        tables = '[{0}{1}]'.format(primary, joined_tables)
    
    # Determine the basename, suffix, and output path for the file
    if multi:
        p_id, created, incomplete = id_info
        basename = "p{0}{1}.{2}".format(str(p_id), tables, created[:10])
        suffix = "_incomplete" if incomplete else ""
        outdir = P.incomplete_data_dir if incomplete else P.data_dir
    else:
        basename = "{0}_all_trials{1}".format(P.project_name, tables)
        suffix = ""
        outdir = P.data_dir

    # If the file is a duplicate, add a number to the suffix and increment until
    # we find a filename that doesn't exist yet
    duplicate_count = 1
    while duplicate:
        dupe_num = "_{0}".format(duplicate_count)
        filename = basename + suffix + dupe_num + P.datafile_ext
        if os.path.isfile(os.path.join(outdir, filename)):
            duplicate_count += 1
        else:
            suffix = suffix + dupe_num
            break

    return os.path.join(outdir, basename + suffix + P.datafile_ext)


def _build_export_header(db, user_id=None):
    # Old versions of KLibs didn't have session_info table for runtime info,
    # so we do a bit of work to keep export compatibility with old databases
    legacy = False
    if 'session_info' in db.tables:
        info_table = 'session_info'
        info_cols = db.get_columns('session_info')
        info_cols.remove('participant_id')
    else:
        info_table = 'participants'
        info_cols = ['klibs_commit', 'random_seed']
        legacy = True

    # Gather runtime info, checking for non-unique values if multi-participant export
    runtime_info = {}
    for colname in info_cols:
        q = "SELECT DISTINCT {0} FROM {1}".format(colname, info_table)
        if user_id:
            q += " WHERE `participant_id` = ?"
            values = db.query(q, q_vars=[user_id])
        else:
            values = db.query(q)
        runtime_info[colname] = "(multiple)" if len(values) > 1 else values[0][0]

    # If database is from a legacy project, guess at runtime values from params
    if legacy:
        runtime_info['trials_per_block'] = P.trials_per_block
        runtime_info['blocks_per_session'] = P.blocks_per_experiment
        runtime_info['el_velocity_thresh'] = P.saccadic_velocity_threshold
        runtime_info['el_accel_thresh'] = P.saccadic_acceleration_threshold
        runtime_info['el_motion_thresh'] = P.saccadic_motion_threshold

    # Map header sections/fields to runtime info keys
    header = {
        "KLIBS INFO": [
            ("KLibs Commit", 'klibs_commit'),
        ],
        "EXPERIMENT SETTINGS": [
            ("Trials Per Block", 'trials_per_block'),
            ("Blocks Per Session", 'blocks_per_session'),
        ],
        "SYSTEM INFO": [
            ("Operating System", 'os_version'),
            ("Python Version", 'python_version'),
        ],
        "DISPLAY INFO": [
            ("Screen Size", 'screen_size'),
            ("Resolution", 'screen_res'),
            ("View Distance", 'viewing_dist'),
        ],
        "EYELINK SETTINGS": [
            ("Tracker Model", 'eyetracker'),
            ("Saccadic Velocity Threshold", 'el_velocity_thresh'),
            ("Saccadic Acceleration Threshold", 'el_accel_thresh'),
            ("Saccadic Motion Threshold", 'el_motion_thresh'),
        ],
    }
    sections = ["KLIBS INFO", "EXPERIMENT SETTINGS"]
    if info_table == 'session_info':
        sections += ["SYSTEM INFO", "DISPLAY INFO"]
    if P.eye_tracking:
        sections.append("EYELINK SETTINGS")

    # Actually generate the header string from the info above
    chunks = []
    for section in sections:
        lines = ["# {0}".format(section)]
        for field, key in header[section]:
            if key in runtime_info.keys():
                lines += ["#  > {0}: {1}".format(field, runtime_info[key])]
        chunks.append("\n".join(lines) + "\n")

    return "#\n".join(chunks)


# TODO: look for required tables and columns explicitly and give informative error if absent
# (ie. participants, created). Need to make list of required columns first.
def rebuild_database(path, schema):
    """Creates (or rebuilds) an empty KLibs database from an SQL schema.

    In addition to the tables specified in the schema, a 'session_info' table
    used internally for storing experiment runtime information will be
    automatically added to the created database.

    Args:
        path (str): The path at which to create the empty database.
        schema (str): The path to the SQL schema with which to build the
            empty database.

    """
    # Create empty database file at temporary path
    tmpdir = tempfile.gettempdir()
    tmppath = os.path.join(tmpdir, "klibs_tmp.db")
    open(tmppath, "w").close()

    # Open file as database and initialize with schema
    db = sqlite3.connect(tmppath, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = db.cursor()
    with io.open(schema, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
    cursor.execute(session_info_schema)
    cursor.execute(export_history_schema)
    cursor.close()
    db.close()

    # If successful, back up old database and replace with new one
    backup_path = path + ".backup"
    if os.path.exists(path):
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(path, backup_path)
    shutil.move(tmppath, path)



class EntryTemplate(object):

    def __init__(self, table):
        from klibs.KLEnvironment import db
        self.table = table
        self.schema = db.table_schemas[table]
        self.data = [None] * len(self.schema)  # create an empty list of appropriate length
        self._values = {}

    def log(self, field, value):
        try:
            index = list(self.schema.keys()).index(field)
        except ValueError:
            err = "Column '{0}' does not exist in table '{1}'."
            raise ValueError(err.format(field, self.table))
        formatted_value = _convert_to_query_format(value, field, self.schema[field]['type'])
        self.data[index] = formatted_value
        self._values[field] = value



class Database(object):
    """An object for reading, writing, and modifying data in the KLibs database.

    Args:
        path (str): The path to the database file to load. The database must
            already exist before loading.

    """
    def __init__(self, path):
        super(Database, self).__init__()
        self.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.text_factory = sqlite3.OptimizedUnicode
        self.cursor = self.db.cursor()
        self.table_schemas = self._build_table_schemas()

    def _to_sql_equals_statements(self, data, table):
        sql_strs = []
        for column, value in data.items():
            try:
                col_type = self.table_schemas[table][column]['type']
            except KeyError:
                err = "Column '{0}' does not exist in the table '{1}'."
                raise ValueError(err.format(column, table))
            formatted_value = _convert_to_query_format(value, column, col_type)
            sql_strs.append("`{0}` = {1}".format(column, formatted_value))
        return sql_strs

    def _ensure_table(self, table):
        if not table in self.tables:
            e = "No table named '{0}' in the current database"
            raise ValueError(e.format(table))

    def _build_table_schemas(self):
        self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
        tables = {}
        for table in self.cursor.fetchall():
            table = str(table[0])  # unicode value
            if table != "sqlite_sequence":  # a table internal to the database structure
                table_cols = OrderedDict()
                self.cursor.execute("PRAGMA table_info({0})".format(table))
                columns = self.cursor.fetchall()

                # convert sqlite3 types to python types
                for col in columns:
                    if col[2].lower() == SQL_STR:
                        col_type = PY_STR
                    elif col[2].lower() == SQL_BIN:
                        col_type = PY_BIN
                    elif col[2].lower() in (SQL_INT, SQL_KEY):
                        col_type = PY_INT
                    elif col[2].lower() in (SQL_FLOAT, SQL_REAL, SQL_NUMERIC):
                        col_type = PY_FLOAT
                    elif col[2].lower() == SQL_BOOL:
                         col_type = PY_BOOL
                    else:
                        err_str = "Invalid or unsupported type ({0}) for {1}.{2}'"
                        raise ValueError(err_str.format(col[2], table, col[1]))
                    allow_null = col[3] == 0
                    table_cols[col[1]] = {'type': col_type, 'allow_null': allow_null}
                tables[table] = table_cols
        return tables

    def _flush(self):
        # Clears all data from the database while keeping its table structure.
        # This also resets the row id counts for each table.
        for table in self.tables:
            self.cursor.execute(u"DELETE FROM `{0}`".format(table))
            self.cursor.execute(u"DELETE FROM sqlite_sequence WHERE name='{0}'".format(table))
        self.db.commit()

    def _gather_insert_values(self, data, table):
        # Gathers and validates columns/values for insertion into a given table
        self._ensure_table(table)
        template = copy(self.table_schemas[table])
        template.pop('id', None) # remove id column from template if present
        # Ensure all provided values correspond to an existing column
        for colname in data.keys():
            if colname not in template.keys():
                err = "Column '{0}' does not exist in table '{1}'."
                raise ValueError(err.format(colname, table))
        # Gather all values to insert into the database
        cols = []
        values = []
        for colname, info in template.items():
            if colname in data.keys():
                try:
                    value = _as_column_type(data[colname], info['type'])
                except (TypeError, ValueError):
                    e = "Could not coerce '{0}' to type '{1}' for column '{2}' in '{3}'"
                    raise ValueError(
                        e.format(data[colname], info['type'], colname, table)
                    )
                cols.append(u"`{0}`".format(colname))
                values.append(value)
            elif info['allow_null']:
                continue
            else:
                raise ValueError("No value provided for column '{0}'.".format(colname))
        return cols, values

    
    def close(self):
        """Closes the connection to the database.

        Once called, the Database object can no longer be used.

        """
        self.cursor.close()
        self.db.close()
        self.table_schemas = {}


    def get_columns(self, table):
        """Retrieves the names of all columns in a given table.

        Args:
            table (str): The name of the table to query.

        Returns:
            list: The names of the columns in the table.

        """
        self._ensure_table(table)
        return list(self.table_schemas[table].keys())


    def exists(self, table, column, value):
        """Checks whether a value already exists within a given column.

        Args:
            table (str): The name of the table to query.
            column (str): The name of the column to check for the value.
            value: The value to check for in the given column.

        Returns:
            bool: True if the value already exists in the column, otherwise False.

        """
        self._ensure_table(table)
        q = "SELECT * FROM `{0}` WHERE `{1}` = ?".format(table, column)
        return len(self.query(q, q_vars=[value])) > 0


    def insert(self, data, table=None):
        """Inserts a row of data into a table in the database.

        Args:
            data (:obj:`dict`): A dictionary in the format ``{'column': value}``
                specifying the values to insert for each column in the row. The
                column names must match the columns of the table.
            table (str): The name of the table to insert the data into.

        """
        if isinstance(data, EntryTemplate):
            if not table:
                table = data.table
            data = data._values
        elif isinstance(data, dict):
            if not table:
                raise ValueError("A table must be specified when inserting a dict.")
        else:
            raise TypeError("Argument 'data' must be either an EntryTemplate or a dict.")

        cols, values = self._gather_insert_values(data, table)
        cols_str = u", ".join(cols)
        qmark_str = u", ".join(["?"] * len(values))
        q = u"INSERT INTO `{0}` ({1}) VALUES({2})".format(table, cols_str, qmark_str)
        try:
            self.cursor.execute(q, values)
        except sqlite3.OperationalError as e:
            err = "\n\n\nTried to match the following:\n\n{0}\n\nwith\n\n{1}"
            print(full_trace())
            print(err.format(self.table_schemas[table], q))
            raise e
        self.db.commit()
        return self.cursor.lastrowid


    def last_row_id(self, table):
        """Retrieves the highest row id for a given table.

        Args:
            table (str): The name of the table to query.

        Returns:
            int: The highest ``id`` column value for the table.
        
        """
        self._ensure_table(table)
        return self.query("SELECT max({0}) from `{1}`".format('id', table))[0][0]


    def query(self, query, q_vars=(), commit=False):
        # Can probably also be made private after updating TraceLab
        result = self.cursor.execute(query, tuple(q_vars))
        if commit:
            self.db.commit()
        return result.fetchall()


    def select(self, table, columns=None, where=None, distinct=False):
        """Retrieves a given set of rows from a table in the database.

        Args:
            table (str): The name of the database table to retrieve.
            columns (:obj:`list`, optional): The names of the columns to retrieve from the
                table. Selects all rows in the table if not specified.
            where (:obj:`dict`, optional): A dict in the form {column: value}, defining the
                conditions that rows must match in order to be retrieved.
            distinct (bool, optional): If True, duplicate rows for the selected columns
                will be removed before returning. Defaults to False.
        
        Returns:
            list: A list of rows from the database, containing the values for
            the selected columns.

        """
        self._ensure_table(table)
        if not columns:
            columns = self.get_columns(table)

        columns_str = ", ".join(columns)
        q = "SELECT DISTINCT " if distinct else "SELECT "
        q += "{0} FROM {1}".format(columns_str, table)
        if where and len(where) > 0:
            filters = self._to_sql_equals_statements(where, table)
            filter_str = " AND ".join(filters)
            q += " WHERE {0}".format(filter_str)

        return self.query(q)


    def delete(self, table, where):
        """Removes all rows from a table that match a set of criteria.

        .. note:: This function permanently deletes data from the database. Be
                  sure you know what you're doing!

        Args:
            table (str): The name of the database table to remove rows from.
            where (:obj:`dict`): A dict in the form {column: value}, defining the
                conditions that rows must match in order to be removed (e.g.
                ``{'incomplete': True}``).

        Returns:
            int: The number of rows deleted from the table.

        """
        self._ensure_table(table)

        # Delete selected rows from the database
        q = "DELETE FROM `{0}`".format(table)
        if where and len(where) > 0:
            filters = self._to_sql_equals_statements(where, table)
            filter_str = " AND ".join(filters)
            q += " WHERE {0}".format(filter_str)
        self.cursor.execute(q)
        self.db.commit()

        return self.cursor.rowcount


    def update(self, table, columns, where={}):
        """Updates the values of data already written to the database for the current participant.

        Args:
            table (str): The name of the database table to update values in.
            columns (:obj:`dict`): A dict in the form {column: value} defining the columns and
                corresponding values to overwrite existing data with.
            where (:obj:`dict`, optional): A dict in the form {column: value}, defining the
                conditions that rows must match in order for their values to be updated.

        """
        self._ensure_table(table)

        # prevent overwriting data from other participants
        id_column = 'id' if table == 'participants' else P.id_field_name
        where[id_column] = P.participant_id

        replacements = self._to_sql_equals_statements(columns, table)
        filters = self._to_sql_equals_statements(where, table)
        replacements_str = ", ".join(replacements)
        filter_str = " AND ".join(filters)

        if not len(self.query("SELECT id FROM {0} WHERE {1}".format(table, filter_str))):
            err = "No rows of table '{0}' matching filter criteria '{1}'."
            raise ValueError(err.format(table, filter_str))

        q = "UPDATE `{0}` SET {1} WHERE {2}".format(table, replacements_str, filter_str)
        self.cursor.execute(q)
        self.db.commit()
        return self.cursor.lastrowid
    
    @property
    def tables(self):
        """list: The names of all tables in the database."""
        return list(self.table_schemas.keys())



class DatabaseManager(EnvAgent):
    
    def __init__(self, path, local_path=None):
        super(DatabaseManager, self).__init__()
        # Initialize column type conversions for session
        _set_type_conversions()
        # Initialize paths and settings
        self.multi_user = local_path != None
        self._path = path
        self._local_path = local_path
        # Initialize connections to database(s)
        self._primary = Database(path)
        self._validate_structure(self._primary)
        self._local = None
        if self.multi_user:
            shutil.copy(path, local_path)
            self._local = Database(local_path)
            self._local._flush()
            print("Local database: {0}".format(local_path))
        # Aliases for compatibility
        self.__master = self._primary
        self.__local = self._local

    @property
    def _current(self):
        # An alias for the current database, which is the local db in multi-user
        # mode and the normal database otherwise
        return self._local if self.multi_user else self._primary
    
    def _validate_structure(self, db):
        # Ensure basic required tables exist
        e = "Required table '{0}' is not present in the database."
        required = ['participants', P.primary_table]
        for table in required:
            if not table in db.tables:
                raise RuntimeError(e.format(table))  
        # Ensure participants table has the basic required columns
        if not P.unique_identifier in db.get_columns('participants'):
            e = ("The unique identifier specified in the project's params file "
                "('{0}') does not exist in the database's 'participants' table.")
            raise RuntimeError(e.format(P.unique_identifier))
        e = "Requred column '{0}' not present in the database's 'participants' table."
        if not 'created' in db.get_columns('participants'):
            raise RuntimeError(e.format('created'))
        # Ensure all user-defined tables have a participant_id column
        e = "User-defined table '{0}' missing required column 'participant_id'."
        for table in _get_user_tables(db):
            if not 'participant_id' in db.get_columns(table):
                raise RuntimeError(e.format(table))

    def _is_complete(self, pid):
        # TODO: For multisession projects, need to know the number of sessions
        # per experiment for this to work correctly: currently, this only checks
        # whether all sessions so far were completed, even if there are more
        # sessions remaining.
        if 'session_info' in self._primary.table_schemas:	
            q = "SELECT complete FROM session_info WHERE participant_id = ?"
            sessions = self._primary.query(q, q_vars=[pid])
            complete = [bool(s[0]) for s in sessions]
            return all(complete)
        else:
            q = "SELECT id FROM trials WHERE participant_id = ?"
            trialcount = len(self._primary.query(q, q_vars=[pid]))
            return trialcount >= P.trials_per_block * P.blocks_per_experiment

    def _log_export(self, pid, table):
        # Logs a successfully exported participant in the database
        if 'export_history' in self._primary.tables:
            self._primary.insert(
                {'participant_id': pid, 'table_name': table, 'timestamp': time.time()},
                table='export_history'
            )

    def _already_exported(self, pid, table):
        # Checks whether an id/table combination has already been exported
        if not 'export_history' in self._primary.tables:
            return False
        this_id = {'participant_id': pid, 'table_name': table}
        matches = self._primary.select('export_history', where=this_id)
        return len(matches) > 0
    

    def get_unique_ids(self):
        """Retrieves all existing unique id values from the main database.

        """
        id_rows = self._primary.select('participants', columns=[P.unique_identifier])
        return [row[0] for row in id_rows]
    

    def write_local_to_master(self):
        attach_q = 'ATTACH `{0}` AS master'.format(self._path)
        self._local.cursor.execute(attach_q)
        self.copy_columns(table='participants', ignore=['id'])

        master_p_id = self._local.cursor.lastrowid
        update_p_id = {'participant_id': master_p_id, 'user_id': master_p_id}
        P.participant_id = master_p_id
        
        for table in self._local.tables:
            if table == 'participants': continue
            self.copy_columns(table, ignore=['id'], sub=update_p_id)
        
        self._local.cursor.execute('DETACH DATABASE `master`')
            

    def copy_columns(self, table, ignore=[], sub={}):
        colnames = []
        for colname in self._local.get_columns(table):
            if colname not in ignore:
                colnames.append(colname)
        columns = ", ".join(colnames)
        
        col_data = columns
        for colname in sub.keys():
            col_data = col_data.replace(colname, "\'{0}\'".format(sub[colname]))
            
        q = "INSERT INTO master.{0} ({1}) SELECT {2} FROM {0}".format(table, columns, col_data)
        self._local.cursor.execute(q)
        self._local.db.commit()
    
    
    def close(self):
        self._primary.close()
        if self.multi_user:
            # TODO: Retry some number of times on write failure (locked db)
            self.write_local_to_master()
            self._local.close()


    def collect_export_data(self, base_table, multi_file=True, join_tables=[]):
        uid = P.unique_identifier
        participant_ids = self._primary.query("SELECT `id`, `{0}` FROM `participants`".format(uid))

        colnames = []
        sub = {P.unique_identifier: 'participant'}

        # if P.default_participant_fields(_sf) is defined use that, but otherwise use
        # P.exclude_data_cols since that's the better way of doing things
        fields = P.default_participant_fields if multi_file else P.default_participant_fields_sf
        if len(fields) > 0:
            for field in fields:
                if iterable(field):
                    sub[field[0]] = field[1]
                    colnames.append(field[0])
                else:
                    colnames.append(field)
        else:
            for colname in self._primary.get_columns('participants'):
                if colname not in ['id'] + P.exclude_data_cols:
                    colnames.append(colname)
        for colname in P.append_info_cols:
            if colname not in self._primary.get_columns('session_info'):
                err = "Column '{0}' does not exist in the session_info table."
                raise RuntimeError(err.format(colname))
            colnames.append(colname)
        for t in [base_table] + join_tables:
            for colname in self._primary.get_columns(t):
                if colname not in ['id', P.id_field_name] + P.exclude_data_cols:
                    colnames.append(colname)
        column_names = TAB.join(colnames)
        for colname in sub.keys():
            column_names = column_names.replace(colname, sub[colname])
        
        data = []
        for p in participant_ids:
            selected_cols = ",".join(["`"+col+"`" for col in colnames])
            q = "SELECT " + selected_cols + " FROM participants "
            if len(P.append_info_cols) and 'session_info' in self._primary.table_schemas:
                info_cols = ",".join(['participant_id'] + P.append_info_cols)
                q += "JOIN (SELECT " + info_cols + " FROM session_info) AS info "
                q += "ON participants.id = info.participant_id "
            for t in [base_table] + join_tables:
                q += "JOIN {0} ON participants.id = {0}.participant_id ".format(t)
            q += " WHERE participants.id = ?"
            p_data = [] 
            for trial in self._primary.query(q, q_vars=tuple([p[0]])):
                row_str = TAB.join(utf8(col) for col in trial)
                p_data.append(row_str)
            data.append([p[0], p_data])

        return [column_names, data]


    def export(self, table=None, multi_file=True, join_tables=None):
        #TODO: make option for exporting non-devmode/complete participants only
        table = P.primary_table if not table else table
        try:
            join_tables = join_tables[0].split(",")
        except TypeError:
            join_tables = []

        _set_type_conversions(export=True)
        column_names, data = self.collect_export_data(table, multi_file, join_tables)

        if multi_file:
            for p_id, trials in data:
                header = _build_export_header(self._primary, p_id)
                incomplete = (self._is_complete(p_id) == False)
                created = self._primary.select(
                    'participants', ['created'], where={'id': p_id}
                )[0][0]
                id_info = (p_id, created, incomplete)
                file_path = _build_filepath(True, id_info, table, join_tables)
                # If file already exists at path and id/table was already exported, skip
                if os.path.exists(file_path):
                    if self._already_exported(p_id, table):
                        continue
                    file_path = _build_filepath(
                        True, id_info, table, join_tables, duplicate=True
                    )
                # Actually write out the file
                with io.open(file_path, 'w+', encoding='utf-8') as out:
                    out.write(u"\n".join([header, column_names, "\n".join(trials)]))
                self._log_export(p_id, table) # Log successful export in database
                print("    - Participant {0} successfully exported.".format(p_id))
        else:
            combined_data = []
            p_count = 0
            for data_set in data:
                p_count += 1
                combined_data += data_set[1]
            header = _build_export_header(self._primary)
            # If file already exists, add numeric suffix
            file_path = _build_filepath(multi=False, base=table, joined=join_tables)
            if os.path.exists(file_path):
                file_path = _build_filepath(
                    multi=False, base=table, joined=join_tables, duplicate=True
                )
            # Actually write out the file
            with io.open(file_path, 'w+', encoding='utf-8') as out:
                out.write(u"\n".join([header, column_names, "\n".join(combined_data)]))
            msg = "    - Data for {0} participant{1} successfully exported."
            print(msg.format(p_count, "" if p_count == 1 else "s"))


    def num_data_rows(self, unique_id):
        """Checks how many rows of data exist for a given unique ID.

        If there are any rows matching the ID in the primary table, the number
        of matching rows in that table will be returned. If none are found,
        the total number of rows matching the ID in all data tables will be
        returned,

        Args:
            unique_id (str): The unique identifier of the participant to count
                the data rows for in the database.

        Returns:
            int: The number of rows of data matching the given unique ID.

        """
        # Get id row number for the provided unique ID in the participants table
        id_filter = {P.unique_identifier: unique_id}
        ret = self._primary.select('participants', columns=['id'], where=id_filter)
        if not len(ret):
            e = "No participant with the identifier '{0}' exists in the database"
            raise ValueError(e.format(unique_id))
        pid = ret[0][0]

        # First, check for any data in the primary table
        rows = self._primary.select(P.primary_table, where={'participant_id': pid})
        if len(rows):
            return len(rows)

        # If no rows in the primary table, check for rows in any others
        n_rows = 0
        skip = DB_INTERNAL_TABLES + ['participants', P.primary_table]
        for table in self._primary.tables:
            if table in skip:
                continue
            rows = self._primary.select(table, where={'participant_id': pid})
            n_rows += len(rows)
        
        return n_rows

    
    def remove_data(self, unique_id):
        """Removes all data for a given participant ID from the database.

        Args:
            unique_id (str): The unique identifier of the participant to remove
                from the database.

        """
        # Get id row number for the provided unique ID in the participants table
        id_filter = {P.unique_identifier: unique_id}
        ret = self._primary.select('participants', columns=['id'], where=id_filter)
        if not len(ret):
            e = "No participant with the identifier '{0}' exists in the database"
            raise ValueError(e.format(unique_id))
        pid = ret[0][0]

        # For each table in the database, remove all data associated with the ID
        for table in self._primary.tables:
            if table != 'participants':
                self._primary.delete(table, where={'participant_id': pid})
        self._primary.delete('participants', where={'id': pid})


    ## Convenience methods that all pass to corresponding method of current DB ##

    def commit(self):
        self._current.db.commit()

    def exists(self, *args, **kwargs):
        return self._current.exists(*args, **kwargs)
    
    def insert(self, *args, **kwargs):
        return self._current.insert(*args, **kwargs)
    
    def last_row_id(self, *args, **kwargs):
        return self._current.last_row_id(*args, **kwargs)

    def query(self, *args, **kwargs):
        return self._current.query(*args, **kwargs)

    def select(self, *args, **kwargs):
        return self._current.select(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._current.delete(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self._current.update(*args, **kwargs)
    
    def get_columns(self, table):
        return self._current.get_columns(table)

    @property
    def tables(self):
        """list: The names of all tables in the database."""
        return self._current.tables

    @property
    def table_schemas(self):
        return self._current.table_schemas
        