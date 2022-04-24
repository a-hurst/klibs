__author__ = 'Jonathan Mulle & Austin Hurst'

import io
import shutil
import sqlite3
from copy import copy
from itertools import chain
from os import remove, rename
from os.path import join, isfile, basename
from collections import OrderedDict

from klibs.KLEnvironment import EnvAgent
from klibs.KLConstants import (DB_CREATE, DB_COL_TITLE, DB_SUPPLY_PATH, SQL_COL_DELIM_STR,
	SQL_NUMERIC, SQL_FLOAT, SQL_REAL, SQL_INT, SQL_BOOL, SQL_STR, SQL_BIN, SQL_KEY, SQL_NULL,
	PY_INT, PY_FLOAT, PY_BOOL, PY_BIN, PY_STR, QUERY_SEL, TAB, ID)
from klibs import P
from klibs.KLUtilities import (full_trace, type_str, iterable, bool_to_int, boolean_to_logical,
	snake_to_camel, utf8)
from klibs.KLUtilities import colored_stdout as cso
from klibs.KLRuntimeInfo import session_info_schema


def _convert_to_query_format(value, col_name, col_type):
	'''A convenience function for converting Python variables to sqlite column types so
	they can then be used in SQL INSERT statements using Python's str.format() method. For
	internal KLibs use.

	Args:
		value: The Python value to convert.
		colname(str): The name of the database column the value will be inserted into.
		coltype(str): A string indicating the Python type to convert the value to before
			formatting for query use. Must be one of 'str', 'int', 'float', or 'bool'.

	Returns:
		str: the SQL query-formatted value.

	Raises:
		ValueError: if the value cannot be coerced to the given data type, or if an invalid
			data type is given.

	'''

	err_str = "'{0}' could not be coerced to '{1}' for insertion into column '{2}'"
	
	if value is None:
		return SQL_NULL

	if col_type not in [PY_BOOL, PY_FLOAT, PY_INT, PY_STR, PY_BIN]:
		type_err = "'{0}' is not a valid EntryTemplate data type."
		raise ValueError(type_err.format(col_type))

	try:
		if col_type == PY_BOOL:
			# convert to int because sqlite3 has no native boolean type
			if utf8(value).lower() in ['true', '1']: value = '1'
			elif utf8(value).lower() in ['false', '0']: value = '0'
			else: raise TypeError
		elif col_type == PY_FLOAT:
			value = str(float(value))
		elif col_type == PY_INT:
			value = str(int(value))
		elif col_type == PY_STR:
			if utf8(value).lower() in ['true', 'false']:
				value = utf8(value).upper() # convert true/false to uppercase for R
			value = u"'{0}'".format(utf8(value))
		elif col_type == PY_BIN:
			raise NotImplementedError("SQL blob insertion is not yet supported.")

	except (TypeError, ValueError):
		# if value can't be converted to column type, raise an exception
		raise ValueError(err_str.format(value, col_type, col_name))
	
	return value



class EntryTemplate(object):


	def __init__(self, table):
		from klibs.KLEnvironment import db
		self.table = table
		self.schema = db.table_schemas[table]
		self.defined = {}
		self.data = [None] * len(self.schema)  # create an empty list of appropriate length


	def __str__(self):
		s = "<klibs.KLDatabase.KLEntryTemplate[{0}] object at {1}>"
		return s.format(self.table, hex(id(self)))


	def pr_schema(self):
		schema_str = "\t\t{\n"
		for colname, info in self.schema.items():
			schema_str += "\t\t\t" + colname + " : " + str(info) + "\n"
		schema_str += "\t\t}"
		return schema_str


	def insert_query(self):
		
		insert_template = [SQL_NULL, ] * len(self.schema)
		query_template = u"INSERT INTO `{0}` ({1}) VALUES ({2})"

		cols = list(self.schema.keys())
		for col_name in cols:
			col_index = cols.index(col_name)
			if self.data[col_index] in [SQL_NULL, None]:
				if self.schema[col_name]['allow_null']:
					insert_template[col_index] = SQL_NULL
					self.data[col_index] = SQL_NULL
				elif col_name == ID:
					self.data[0] = SQL_NULL
					insert_template[0] = SQL_NULL
				elif self.table in P.table_defaults:
					for i in P.table_defaults[self.table]:
						if i[0] == col_name:
							insert_template[col_index] = utf8(i[1])
				else:
					print(self.data)
					raise ValueError("Column '{0}' may not be null.".format(col_name))
			else:
				insert_template[col_index] = col_name

		values = u",".join([utf8(i) for i in self.data if i != SQL_NULL])
		columns = u",".join([i for i in insert_template if i != SQL_NULL])
		return query_template.format(self.table, columns, values)


	def log(self, field, value):
		try:
			index = list(self.schema.keys()).index(field)
		except ValueError:
			err = "Column '{0}' does not exist in table '{1}'."
			raise ValueError(err.format(field, self.table))
		formatted_value = _convert_to_query_format(value, field, self.schema[field]['type'])
		self.data[index] = formatted_value
		self.defined[field] = value



# TODO: look for required tables and columns explicitly and give informative error if absent
# (ie. participants, created)
class Database(EnvAgent):

	db = None
	cursor = None
	table_schemas = None

	def __init__(self, path):
		super(Database, self).__init__()
		self.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
		self.db.text_factory = sqlite3.OptimizedUnicode
		self.cursor = self.db.cursor()
		if len(self._tables()) == 0:
			self._deploy_schema(P.schema_file_path)
		self.build_table_schemas()

	def _tables(self):
		self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
		self.table_list = self.cursor.fetchall()
		return self.table_list

	def _drop_tables(self, table_list=None):
		if table_list is None:
			table_list = self._tables()
		for n in table_list:
			if n[0] != "sqlite_sequence":
				self.cursor.execute(u"DROP TABLE `{0}`".format(n[0]))
		self.db.commit()

	def _deploy_schema(self, schema):
		with io.open(schema, 'r', encoding='utf-8') as f:
			self.cursor.executescript(f.read())
		self.cursor.execute(session_info_schema)

	def _to_sql_equals_statements(self, data, table):
		sql_strs = []
		for column, value in data.items():
			try:
				col_type = self.table_schemas[table][column]['type']
			except KeyError:
				err = "Column '{0}' does not exist in the table '{1}'."
				raise ValueError(err.format(column, table))
			formatted_value = _convert_to_query_format(value, column, col_type)
			sql_strs.append("{0} = {1}".format(column, formatted_value))
		return sql_strs


	def build_table_schemas(self):
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
		self.table_schemas = tables
		return True


	def exists(self, table, column, value):
		q = "SELECT * FROM `?` WHERE `?` = ?"
		return len(self.query(q, QUERY_SEL, q_vars=[table, column, value])) > 0


	def flush(self):
		for table in self.table_schemas.keys():
			self.cursor.execute(u"DELETE FROM `{0}`".format(table))
			self.cursor.execute(u"DELETE FROM sqlite_sequence WHERE name='{0}'".format(table))
		self.db.commit()


	def insert(self, data, table=None):

		if isinstance(data, EntryTemplate):
			if not table:
				table = data.table
			query = data.insert_query()
		elif isinstance(data, dict):
			if not table:
				raise ValueError("A table must be specified when inserting a dict.")
			query = self.query_str_from_raw_data(data, table)
		else:
			raise TypeError("Argument 'data' must be either an EntryTemplate or a dict.")

		try:
			self.cursor.execute(query)
		except sqlite3.OperationalError:
			err = "\n\n\nTried to match the following:\n\n{0}\n\nwith\n\n{1}"
			print(full_trace())
			print(err.format(self.table_schemas[table], query))
			self.exp.quit()
		self.db.commit()
		return self.cursor.lastrowid


	def is_unique(self, table, column, value):
		q = "SELECT * FROM `?` WHERE `?` = ?"
		return len(self.query(q, q_vars=[table, column, value])) == 0


	def last_id_from(self, table):
		if not table in self.table_schemas.keys():
			raise ValueError("Table '{0}' not found in current database".format(table))
		return self.query("SELECT max({0}) from `{1}`".format('id', table))[0][0]


	def query(self, query, query_type=QUERY_SEL, q_vars=None, return_result=True, fetch_all=True):
		if q_vars:
			result = self.cursor.execute(query, tuple(q_vars))
		else:
			result = self.cursor.execute(query)

		if query_type != QUERY_SEL: self.db.commit()
		if return_result:
			if fetch_all:
				return result.fetchall()
			else:
				return result
		return True


	def query_str_from_raw_data(self, data, table):
		# TODO: replace this with EntryTemplate for consistency?
		try:
			template = copy(self.table_schemas[table])
		except KeyError:
			raise ValueError("Table '{0}' does not exist in the database.".format(table))
		values = []
		columns = []
		template.pop('id', None) # remove id column from template if present
		for colname in list(data.keys()):
			if colname not in list(template.keys()):
				err = "Column '{0}' does not exist in table '{1}'."
				raise ValueError(err.format(colname, table))
		for colname, info in template.items():
			try:
				value = data[colname]
			except KeyError:
				raise ValueError("No value provided for column '{0}'.".format(colname))
			formatted_value = _convert_to_query_format(value, colname, info['type'])
			values.append(formatted_value)
			columns.append(colname)
		columns_str = u",".join(columns)
		values_str = u",".join(values)
		return u"INSERT INTO `{0}` ({1}) VALUES ({2})".format(table, columns_str, values_str)
		

	def update(self, table, columns, where={}):
		"""Updates the values of data already written to the database for the current participant.

		Args:
			table (str): The name of the database table to update values in.
			columns (:obj:`dict`): A dict in the form {column: value} defining the columns and
				corresponding values to overwrite existing data with.
			where (:obj:`dict`, optional): A dict in the form {column: value}, defining the
				conditions that rows must match in order for their values to be updated.

		"""
		if not table in self.table_schemas.keys():
			raise ValueError("The table '{0}' does not exist in the database.".format(table))

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

		q = "UPDATE {0} SET {1} WHERE {2}".format(table, replacements_str, filter_str)
		self.cursor.execute(q)
		self.db.commit()
		return self.cursor.lastrowid



class DatabaseManager(EnvAgent):

	__local = None
	__master = None
	__current = None
	
	def __init__(self):
		super(DatabaseManager, self).__init__()
		self.__set_type_conversions()
		shutil.copy(P.database_path, P.database_backup_path)
		self.__master = Database(P.database_path)
		if P.multi_user:
			print("Local database: {0}".format(P.database_local_path))
			shutil.copy(P.database_path, P.database_local_path)
			self.__local = Database(P.database_local_path)
			self.__local.flush()
			self.__current = self.__local
		else:
			self.__current = self.__master
	
	def __restore__(self):
		# restores database file from the back-up of it
		remove(P.database_path)
		rename(P.database_backup_path, P.database_path)
	
	
	def __set_type_conversions(self, export=False):
		if export:
			sqlite3.register_converter("boolean", lambda x: str(bool(int(x))).upper())
			sqlite3.register_converter("BOOLEAN", lambda x: str(bool(int(x))).upper())
		else:
			sqlite3.register_converter("boolean", lambda x: bool(int(x)))
			sqlite3.register_converter("BOOLEAN", lambda x: bool(int(x)))


	def __is_complete(self, pid):
		#TODO: still needs modification to work with multi-session projects
		if 'session_info' in self.__master.table_schemas:	
			q = "SELECT complete FROM session_info WHERE participant_id = ?"
			sessions = self.__master.query(q, q_vars=[pid])
			complete = [bool(s[0]) for s in sessions]
			return all(complete)
		else:
			q = "SELECT id FROM trials WHERE participant_id = ?"
			trialcount = len(self.__master.query(q, q_vars=[pid]))
			return trialcount >= P.trials_per_block * P.blocks_per_experiment


	def write_local_to_master(self):
		attach_q = 'ATTACH `{0}` AS master'.format(P.database_path)
		self.__local.cursor.execute(attach_q)
		self.copy_columns(table='participants', ignore=['id'])

		master_p_id = self.__local.cursor.lastrowid
		update_p_id = {'participant_id': master_p_id, 'user_id': master_p_id}
		P.participant_id = master_p_id
		
		for table in self.__local.table_schemas.keys():
			if table == 'participants': continue
			self.copy_columns(table, ignore=['id'], sub=update_p_id)
		
		self.__local.cursor.execute('DETACH DATABASE `master`')
			

	def copy_columns(self, table, ignore=[], sub={}):
		colnames = []
		for colname in self.__local.table_schemas[table].keys():
			if colname not in ignore:
				colnames.append(colname)
		columns = ", ".join(colnames)
		
		col_data = columns
		for colname in sub.keys():
			col_data = col_data.replace(colname, "\'{0}\'".format(sub[colname]))
			
		q = "INSERT INTO master.{0} ({1}) SELECT {2} FROM {0}".format(table, columns, col_data)
		self.__local.cursor.execute(q)
		self.__local.db.commit()
	
	
	def close(self):
		self.__master.cursor.close()
		self.__master.db.close()
		if P.multi_user:
			# TODO: Retry some number of times on write failure (locked db)
			self.write_local_to_master()
			self.__local.cursor.close()
			self.__local.db.close()


	def collect_export_data(self, multi_file=True, join_tables=[]):
		uid = P.unique_identifier
		participant_ids = self.__master.query("SELECT `id`, `{0}` FROM `participants`".format(uid))

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
			for colname in self.__master.table_schemas['participants'].keys():
				if colname not in ['id'] + P.exclude_data_cols:
					colnames.append(colname)
		for colname in P.append_info_cols:
			if colname not in self.__master.table_schemas['session_info'].keys():
				err = "Column '{0}' does not exist in the session_info table."
				raise RuntimeError(err.format(colname))
			colnames.append(colname)
		for t in [P.primary_table] + join_tables:
			for colname in self.__master.table_schemas[t].keys():
				if colname not in ['id', P.id_field_name] + P.exclude_data_cols:
					colnames.append(colname)
		column_names = TAB.join(colnames)
		for colname in sub.keys():
			column_names = column_names.replace(colname, sub[colname])
		
		data = []
		for p in participant_ids:
			primary_t = P.primary_table
			selected_cols = ",".join(["`"+col+"`" for col in colnames])
			q = "SELECT " + selected_cols + " FROM participants "
			if len(P.append_info_cols) and 'session_info' in self.__master.table_schemas:
				info_cols = ",".join(['participant_id'] + P.append_info_cols)
				q += "JOIN (SELECT " + info_cols + " FROM session_info) AS info "
				q += "ON participants.id = info.participant_id "
			for t in [primary_t] + join_tables:
				q += "JOIN {0} ON participants.id = {0}.participant_id ".format(t)
			q += " WHERE participants.id = ?"
			p_data = [] 
			for trial in self.__master.query(q, q_vars=tuple([p[0]])):
				row_str = TAB.join(utf8(col) for col in trial)
				p_data.append(row_str)
			data.append([p[0], p_data])

		return [column_names, data]


	def export(self, table=None, multi_file=True, join_tables=None):
		#TODO: make option for exporting non-devmode/complete participants only
		if table != None:
			P.primary_table = table
		try:
			join_tables = join_tables[0].split(",")
		except TypeError:
			join_tables = []

		self.__set_type_conversions(export=True)
		column_names, data = self.collect_export_data(multi_file, join_tables)

		if multi_file:
			for p_id, trials in data:
				header = self.export_header(p_id)
				incomplete = (self.__is_complete(p_id) == False)
				file_path = self.filepath_str(p_id, multi_file, table, join_tables, incomplete)
				with io.open(file_path, 'w+', encoding='utf-8') as out:
					out.write(u"\n".join([header, column_names, "\n".join(trials)]))
				print("    - Participant {0} successfully exported.".format(p_id))
		else:
			combined_data = []
			p_count = 0
			for data_set in data:
				p_count += 1
				combined_data += data_set[1]
			header = self.export_header()
			file_path = self.filepath_str(multi_file=False, base=table, joined=join_tables)
			with io.open(file_path, 'w+', encoding='utf-8') as out:
				out.write(u"\n".join([header, column_names, "\n".join(combined_data)]))
			print("    - Data for {0} participants successfully exported.".format(p_count))


	def export_header(self, user_id=None):
		if 'session_info' in self.__master.table_schemas:
			info_table = 'session_info'
			info_cols = list(self.__master.table_schemas['session_info'].keys())
			info_cols.remove('participant_id')
		else:
			info_table = 'participants'
			info_cols = ['klibs_commit', 'random_seed']

		runtime_info = {}
		for colname in info_cols:
			q = "SELECT DISTINCT {0} FROM {1}".format(colname, info_table)
			if user_id:
				q += " WHERE `participant_id` = ?"
				values = self.__master.query(q, q_vars=[user_id])
			else:
				values = self.__master.query(q)
			runtime_info[colname] = "(multiple)" if len(values) > 1 else values[0][0]

		klibs_vars   = ["KLIBS INFO", ["KLibs Commit", runtime_info['klibs_commit']]]
		if info_table == 'session_info':
			exp_vars 	 = ["EXPERIMENT SETTINGS",
							["Trials Per Block", runtime_info['trials_per_block']],
							["Blocks Per Session", runtime_info['blocks_per_session']]]
			system_vars  = ["SYSTEM INFO",
							["Operating System", runtime_info['os_version']],
							["Python Version", runtime_info['python_version']]]
			display_vars = ["DISPLAY INFO",
							["Screen Size", runtime_info['screen_size']],
							["Resolution", runtime_info['screen_res']],
							["View Distance", runtime_info['viewing_dist']]]
			eyelink_vars = ["EYELINK SETTINGS",
							["Tracker Model", runtime_info['eyetracker']],
							["Saccadic Velocity Threshold", runtime_info['el_velocity_thresh']],
							["Saccadic Acceleration Threshold", runtime_info['el_accel_thresh']],
							["Saccadic Motion Threshold", runtime_info['el_motion_thresh']]]
		else:
			exp_vars 	 = ["EXPERIMENT SETTINGS",
							["Trials Per Block", P.trials_per_block],
							["Blocks Per Experiment", P.blocks_per_experiment]]
			eyelink_vars = ["EYELINK SETTINGS",
							["Saccadic Velocity Threshold", P.saccadic_velocity_threshold],
							["Saccadic Acceleration Threshold", P.saccadic_acceleration_threshold],
							["Saccadic Motion Threshold", P.saccadic_motion_threshold]]

		header_strs = []
		header_info = [klibs_vars, exp_vars]
		if info_table == 'session_info':
			header_info += [system_vars, display_vars]
		if P.eye_tracking:
			header_info.append(eyelink_vars)
		for info in header_info:
			section = "# {0}\n".format(info[0])
			section += "\n".join(["#  > {0}: {1}".format(var[0], var[1]) for var in info[1:]])
			header_strs.append(section + "\n")
		header = "#\n".join(header_strs)

		return header
		

	def filepath_str(self, p_id=None, multi_file=False, base=None, joined=[], incomplete=False):
		# if tables to join or alternate base table specified for export, note this in filename
		tables = ''
		if base != None or len(joined):	
			joined_tables = '+'.join(['']+joined)
			tables = '[{0}{1}]'.format(base if base != None else '', joined_tables)
		
		if multi_file:
			created_q = "SELECT `created` FROM `participants` WHERE `id` = ?"
			created = self.__master.query(created_q, q_vars=[p_id], fetch_all=False).fetchone()[0]
			basename = "p{0}{1}.{2}".format(str(p_id), tables, created[:10])
		else:
			basename = "{0}_all_trials{1}".format(P.project_name, tables)		

		duplicate_count = 0
		while True:
			# Generate suffix and see if file already exists with that name. If it does, keep 
			# incremeting the numeric part of the suffix until it doesn't.
			suffix = P.datafile_ext
			if incomplete: suffix = "_incomplete" + suffix
			if duplicate_count: suffix = "_{0}".format(duplicate_count) + suffix
			fname = basename + suffix
			filepath = join(P.incomplete_data_dir if incomplete else P.data_dir, fname)
			if isfile(filepath):
				duplicate_count += 1
			else:
				break

		return filepath

	
	def remove_last(self):
		"""Removes the last participant's data from the database. To be called through the CLI
		to remove the data of a participants who opt to withdraw their data, or for removing
		devmode testing participants.

		"""
		pid = self.__master.last_id_from('participants')
		for table in self.__master.table_schemas.keys():
			if table == "participants":
				delete_q = u"DELETE FROM {0} WHERE id = {1}".format(table, pid)
			else:
				delete_q = u"DELETE FROM {0} WHERE {1} = {2}".format(table, P.id_field_name, pid)
			self.__master.cursor.execute(delete_q)
		self.__master.db.commit()
		return pid


	def rebuild(self):
		self.__master._drop_tables()
		try:
			self.__master._deploy_schema(P.schema_file_path)
			self.__master.build_table_schemas()
		except (sqlite3.ProgrammingError, sqlite3.OperationalError, ValueError) as e:
			self.__master._drop_tables(self.__master.table_list)
			self.__restore__()
			raise e


	## Convenience methods that all pass to corresponding method of current DB ##

	def commit(self):
		self.__current.db.commit()

	def exists(self, *args, **kwargs):
		return self.__current.exists(*args, **kwargs)
	
	def insert(self, *args, **kwargs):
		return self.__current.insert(*args, **kwargs)
	
	def is_unique(self, *args, **kwargs):
		return self.__current.is_unique(*args, **kwargs)
	
	def last_id_from(self, *args, **kwargs):
		return self.__current.last_id_from(*args, **kwargs)

	def query(self, *args, **kwargs):
		return self.__current.query(*args, **kwargs)

	def update(self, *args, **kwargs):
		return self.__current.update(*args, **kwargs)

	@property
	def table_schemas(self):
		return self.__current.table_schemas
		