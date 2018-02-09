__author__ = 'jono'

import shutil
import sqlite3
from itertools import chain
from os import remove, rename
from os.path import join, isfile
from argparse import ArgumentParser

from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import DatabaseException
from klibs.KLConstants import (DB_CREATE, DB_COL_TITLE, DB_SUPPLY_PATH, SQL_COL_DELIM_STR,
	SQL_NUMERIC, SQL_INT, SQL_FLOAT, SQL_BIN, SQL_STR, SQL_KEY, SQL_REAL, SQL_NULL, 
	PY_NUM, PY_INT, PY_FLOAT, PY_BIN, PY_STR, QUERY_SEL, TAB, ID, DATA_EXT)
from klibs import P
from klibs.KLUtilities import (full_trace, type_str, iterable, bool_to_int, boolean_to_logical,
	snake_to_camel, unicode_to_str)
from klibs.KLUtilities import colored_stdout as cso
#TODO: replace all manual usage of colour output with cso


class EntryTemplate(object):
	null_field = "DELETE_THIS_FIELD"
	sql_field_delimiter = "`,`"
	table_name = None
	name = None
	schema = None
	data = None
	id = None

	def __init__(self, table_name, table_schema, instance_name):
		self.schema = table_schema
		self.table_name = table_name
		self.name = instance_name
		self.data = [None] * len(table_schema)  # create an empty tuple of appropriate length

	def __str__(self):
		return "<klibs.KLDatabase.KLEntryTemplate[{0}, {1}] object at {2}>".format(self.table_name, self.name, hex(id(self)))

	def pr_schema(self):
		schema_str = "\t\t{\n"
		for col in self.schema:
			schema_str += "\t\t\t" + col[0] + " : " + str(col[1:]) + "\n"
		schema_str += "\t\t}"
		return schema_str

		#TODO: build logic for update statements as well (as against only insert statements)
	def update_query(self, fields):
		query = "UPDATE {0} SET ".format(self.table_name)
		insert_template = []

		for column in self.schema:
			col_name = column[0]
			col_value = SQL_NULL
			try:
				if col_name not in fields or col_name == ID: continue
			except TypeError:  # ie. if fields is None update every field
				pass
			if self.data[self.index_of(col_name)] in [SQL_NULL, None]:
				if not self.allow_null(col_name): raise ValueError("Column '{0}' may not be null.".format(column))
				self.data[self.index_of(col_name)] = SQL_NULL
			else:
				col_value = self.data[self.index_of(col_name)]
			insert_template.append("`{0}` = {1}".format(col_name, col_value))

		return ", ".join(insert_template)

	def insert_query(self):
		insert_template = [SQL_NULL, ] * len(self.schema)

		for column in self.schema:
			if self.data[self.index_of(column[0])] == SQL_NULL or self.data[self.index_of(column[0])] is None:
				if self.allow_null(column[0]):
					insert_template[self.index_of(column[0])] = SQL_NULL
					self.data[self.index_of(column[0])] = SQL_NULL
				elif column[0] == ID:
					self.data[0] = SQL_NULL
					insert_template[0] = SQL_NULL
				elif self.table_name in P.table_defaults:
					for i in P.table_defaults[self.table_name]:
						if i[0] == column[0]:
							insert_template[self.index_of(column[0])] = str(i[1])
				else:
					print self.data
					raise ValueError("Column '{0}' may not be null.".format(column))
			else:
				insert_template[self.index_of(column[0])] = column[0]
		values = ",".join(filter(lambda column: column != SQL_NULL, [str(i) for i in self.data]))
		columns = "`{0}`".format(SQL_COL_DELIM_STR.join(filter(lambda column: column != SQL_NULL, insert_template)))

		query_string = "INSERT INTO `{0}` ({1}) VALUES ({2})".format(self.table_name, columns, values)

		return query_string

	def index_of(self, field):
		index = 0
		for col in self.schema:
			if col[0] == field:
				return index
			else:
				index += 1
		raise IndexError("Field '{0}' not found in table '{1}'".format(field, self.table_name))

	def type_of(self, field):
		for col in self.schema:
			if col[0] == field:
				return col[1]['type']
		e_msg = "Field '{0}' not found in table '{1}'".format(field, self.table_name)
		raise IndexError(e_msg)

	def allow_null(self, field):
		for col in self.schema:
			if col[0] == field:
				return col[1]['allow_null']
		raise IndexError("Field '{0}' not found in table '{1}'".format(field, self.table_name))

	def log(self, field, value):
		try:
			value = str(bool_to_int(value))
		except ValueError:
			if self.type_of(field) == PY_FLOAT:
				try:
					value = float(value)
				except TypeError:
					e_str = "Expected 'float' for column '{0}'; got '{1}' of type {2}".format(field, value, type(value))
					raise ValueError(e_str)
			else:
				value = str(value)
			if self.type_of(field) == PY_STR:
				value = "'{0}'".format(value)
			if value is None:
				value = SQL_NULL

		self.data[self.index_of(field)] = value

	def report(self):
		print self.schema


# TODO: create a "logical" column type when schema-streama comes along & handling therewith in Database
# TODO: look for required tables and columns explicitly and give informative error if absent (ie. participants, created)
class Database(EnvAgent):

	__default_table = None
	__open_entries = None
	__current_entry = None

	db = None
	cursor = None
	table_schemas = None

	def __init__(self, path):
		super(EnvAgent, self).__init__()
		self.db = sqlite3.connect(path)
		self.cursor = self.db.cursor()
		self.__open_entries = {}
		if len(self._tables()) == 0:
			if isfile(P.schema_file_path):
				self._deploy_schema(P.schema_file_path)
			else:
				raise RuntimeError("Database exists but no tables were found and no table schema were provided.")
		self.build_table_schemas()

	def _tables(self):
		# TODO: I changed tableCount to tableList and made it an attribute as it seems to be used in rebuild. Verify this.
		self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
		self.table_list = self.cursor.fetchall()
		return self.table_list

	def _drop_tables(self, table_list=None):
		if table_list is None:
			table_list = self._tables()
		for n in table_list:
			if str(n[0]) != "sqlite_sequence":
				self.cursor.execute("DROP TABLE `{0}`".format(str(n[0])))
		self.db.commit()

	def _deploy_schema(self, schema):
		f = open(schema, 'rt')
		self.cursor.executescript(f.read())
		
	def build_table_schemas(self):
		self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
		tables = {}
		for table in self.cursor.fetchall():
			table = str(table[0])  # unicode value
			if table != "sqlite_sequence":  # a table internal to the database structure
				table_cols = []
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
					elif col[2].lower() in (SQL_FLOAT, SQL_REAL):
						col_type = PY_FLOAT
					elif col[2].lower() == SQL_NUMERIC:
						 col_type = PY_NUM
					else:
						raise ValueError("Invalid or unsupported type ({0}) for {1}.{2}'".format(col[2], table, col[1]))
					allow_null = col[3] == 0
					table_cols.append([str(col[1]), {'type': col_type, 'allow_null': allow_null}])
				tables[table] = table_cols
		self.table_schemas = tables
		return True

	def current(self, instance=None):
		if instance is False:
			self.__current_entry = None
			return
		if instance is None:
			return self.__current_entry
		try:
			self.__current_entry = instance
			return self.__current_entry.name
		except AttributeError:
			self.__current_entry = self.__open_entries[instance]
			return instance

	def exists(self, table, column, value):
		return len(self.query("SELECT * FROM `?` WHERE `?` = ?", QUERY_SEL, q_vars=[table, column, value])) > 0

	def fetch_entry(self, instance_name): return self.__open_entries[instance_name]

	def flush(self):
		self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
		for tableTuple in self.cursor.fetchall():
			table = str(tableTuple[0])  # str() necessary b/c tableTuple[0] is in unicode
			if table == "sqlite_sequence":
				pass
			else:
				self.cursor.execute("DELETE from `{0}`".format(table))
				#self.cursor.execute("UPDATE sqlite_sequence SET (SELECT MAX(col) FROM {0}) WHERE name=`{0}`".format(table))
		self.db.commit()

	def init_entry(self, table_name, instance_name=None, set_current=True):
		try:
			if instance_name is None: instance_name = table_name
			self.__open_entries[instance_name] = EntryTemplate(table_name, self.table_schemas[table_name], instance_name)
			if set_current: self.current(self.__open_entries[instance_name])
		except IndexError:
			raise IndexError("Table {0} not found in the KLDatabase.table_schemas.".format(table_name))

	def insert(self, data=None, table=None, clear_current=True):
		if data is None:
			try:
				data = self.current()
				if not table:
					table = data.table_name
			except RuntimeError:  # exception below is a more informative account of the current problem
				raise RuntimeError("No data to insert; provide insert data or assign a current KLEntryTemplate instance.")

		try:
			self.cursor.execute(data.insert_query())
			if clear_current and self.current().name == data.name: self.current(False)
		except AttributeError:
			try:
				self.cursor.execute(self.query_str_from_raw_data(data, table))
			except Exception as e:
				# when insert() is directly used to add data to a table in the db, and that table
				# doesn't exist, KLibs crashes hard with an IOError: Broken Pipe. Need to add proper
				# and informative error handling for this.
				print "Error: unable to write data to database."
				raise e
		except sqlite3.OperationalError:
			print full_trace()
			print "\n\n"
			print "Tried to match the following:\n\n{0}\n\nwith\n\n{1}".format(self.table_schemas[table], data.insert_query())
			self.exp.quit()
		self.db.commit()
		return self.cursor.lastrowid

	def is_unique(self, table, column, value):
		return len(self.query("SELECT * FROM `?` WHERE `?` = ?", q_vars=[table, column, value])) == 0

	def last_id_from(self, table):
		if not table in self.table_schemas:
			raise ValueError("Table '{0}' not found in current database".format(table))
		# dunno why, but this does NOT work if the format statement isn't used in place of a proper SQL var
		return self.query("SELECT max({0}) from `{1}` WHERE `participant_id`={2}".format('id', table, P.participant_id))[0][0]

	def log(self, field, value, instance=None, set_to_current=True):
		# convert boolean strings/boolean literals to uppercase boolean strings for R
		if boolean_to_logical(value): value = boolean_to_logical(value)
		try:
			instance.log(field, value)
		except AttributeError:
			try:
				self.__open_entries[instance].log(field, value)
			except KeyError:
				entry = self.current()
				entry.log(field, value)
		if set_to_current:
			self.current(instance)

	def query(self, query, query_type=QUERY_SEL, q_vars=None, return_result=True, fetch_all=True):
		if q_vars:
			result = self.cursor.execute(query, tuple(q_vars))
		else:
			result = self.cursor.execute(query)

		if query_type != QUERY_SEL: self.db.commit()
		if return_result:
			if fetch_all:
				return unicode_to_str(result.fetchall())
			else:
				return result
		return True

	def query_str_from_raw_data(self, data, table=None):
		if table == None:
			table = self.__default_table
		try:
			template = self.table_schemas[table]
		except KeyError:
			raise RuntimeError("Table not found; provide table reference or ensure KLDatabase.default_table is set.")
		columns = []
		values = []
		if template[0][0] == 'id':
			template = template[1:]
		try:
			for column in template:
				column_index = template.index(column)
				try:
					data_value = data[column_index]
				except KeyError:
					data_value = data[column[0]]
				if boolean_to_logical(data_value): data_value = boolean_to_logical(data_value)
				if type_str(data_value) == column[1]['type']:
					if column[1]['type'] in (PY_INT, PY_FLOAT):
						data_value =  str(data_value)
					else:
						data_value = "'{0}'".format(data_value)
				elif column[1]['type'] == PY_NUM and isinstance(data_value, (int, long, float, complex)):
					data_value = str(data_value)
				else:
					error_data = [column[1]['type'], column[0], type_str(data_value), data_value]
					raise TypeError("Expected '{0}' for column '{1}', got '{2}' ({3}).".format(*error_data))
				values.append(data_value)
				columns.append(column[0])
			if column_index + 1 > len(data):
				raise ValueError('Cannot map data to table: more data elements than columns.')
		except IndexError:
			raise AttributeError('Cannot map data to table: fewer data elements than columns.')
		columns_str = ",".join(columns)
		values_str = ",".join(values)
		return "INSERT INTO `{0}` ({1}) VALUES ({2})".format(table, columns_str, values_str)
			
	def test_data(self, table):
		# TODO: allow rules per column such as length
		pass

	def update(self, record_id=None, data=None, fields=None, table=None, clear_current=True):
		if not data:
			try:
				data = self.current()
			except RuntimeError:  # exception below is a more informative account of the current problem
				raise RuntimeError(
					"No data to insert; provide insert data or assign a current KLEntryTemplate instance.")
			if not table: table = data.table_name
			if not record_id and not data.id:
				raise RuntimeError("No record to update; no record_id provided or present in KLEntryTemplate instance.")
		try:
			self.cursor.execute(data.update_query(fields))
			if clear_current and self.current().name == data.name: self.current(False)
		except AttributeError:
			self.cursor.execute(self.query_str_from_raw_data(data, table))
		self.db.commit()
		return self.cursor.lastrowid

	@property
	def default_table(self):
		return self.__default_table

	@default_table.setter
	def default_table(self, name):  # todo: error handling
		self.__default_table = name


class DatabaseManager(EnvAgent):

	__local = None
	__master = None
	__current = None
	
	def __init__(self):
		super(EnvAgent, self).__init__()
		self.__load_master__()
		if P.multi_user:
			print(P.database_local_path)
			shutil.copy(P.database_path, P.database_local_path)
			self.__local = Database(P.database_local_path)
			self.__local.flush()
			self.__current = self.__local
		else:
			self.__current = self.__master
			
	def __catch_db_not_found__(self):
		cso("<green_d>No database file was present at '{0}'.</green_d>", args=[P.database_path])
		err_string = cso(
			"<green_d>You can</green_d> "
			"<purple>(c)</purple><green_d>reate it,</green_d> "
			"<purple>(s)</purple><green_d>upply a different path or</green_d> "
			"<purple>(q)</purple><green_d>uit: </green_d>", print_string=False
		)
		db_action = ArgumentParser()
		db_action.add_argument('action', type=str, choices=['c', 's', 'q'])
		action = db_action.parse_args([raw_input(err_string).lower()[0]]).action

		if action == DB_SUPPLY_PATH:
			P.database_path = raw_input(cso("<green_d>Great. Where might it be?</green_d>", False))
			self.__load_master__()
		elif action == DB_CREATE:
			open(P.database_path, "a").close()
			self.__load_master__()
		elif action == "q":
			raise DatabaseException("Quitting.")
		else:
			raise DatabaseException("No valid response.")
	
	def __load_master__(self):
		if isfile(P.database_path):
			shutil.copy(P.database_path, P.database_backup_path)
			self.__master = Database(P.database_path)
		else:
			self.__catch_db_not_found__()
	
	def __restore__(self):
		# restores database file from the back-up of it
		remove(P.database_path)
		rename(P.database_backup_path, P.database_path)
	
	def write_local_to_master(self):
		attach_q = 'ATTACH `{0}` AS master'.format(P.database_path)
		self.__local.cursor.execute(attach_q)
		self.copy_columns(table='participants', ignore=['id'])

		master_p_id = self.__local.cursor.lastrowid
		update_p_id = {'participant_id': master_p_id, 'user_id': master_p_id}
		
		for table in self.__local.table_schemas.keys():
			if table == 'participants': continue
			self.copy_columns(table, ignore=['id'], sub=update_p_id)
		
		self.__local.cursor.execute('DETACH DATABASE `master`')
			
	def copy_columns(self, table, ignore=[], sub={}):
		colnames = []
		for col in self.__local.table_schemas[table]:
			colname = col[0]
			if colname not in ignore:
				colnames.append(colname)
		columns = ", ".join(colnames)
		
		col_data = columns
		for colname in sub.keys():
			col_data = col_data.replace(colname, "\'{0}\'".format(sub[colname]))
			
		q = "INSERT INTO master.{0} ({1}) SELECT {2} FROM {0}".format(table, columns, col_data)
		self.__local.cursor.execute(q)
	
	def build_column_header(self, multi_file=True, join_tables=None):
		column_names = []
		for field in (P.default_participant_fields if multi_file else P.default_participant_fields_sf):
			column_names.append(field[1]) if iterable(field) else column_names.append(field)
		column_names = [snake_to_camel(col) for col in column_names]
		for t in [P.primary_table] + join_tables:
			for field in self.__master.table_schemas[t]:
				if field[0][-2:] != "id": column_names.append(field[0])
		return TAB.join(column_names)
	
	def close(self):
		self.__master.cursor.close()
		self.__master.db.close()
		if P.multi_user:
			self.write_local_to_master()
			self.__local.cursor.close()
			self.__local.db.close()

	def collect_export_data(self, multi_file=True,  join_tables=[]):
		participant_ids = self.__master.query("SELECT `id`, `{0}` FROM `participants`".format(P.unique_identifier))
		participant_ids.insert(0, (-1,))  # for test data collected before anonymous_user added to collect_demographics()
		default_fields = P.default_participant_fields if multi_file else P.default_participant_fields_sf

		t_cols = []
		data = []

		#  random_seed has to be added to every participant row when exporting to multi-file
		p_cols = [f for f in default_fields]
		for t in [P.primary_table] + join_tables:
			for field in self.__master.table_schemas[t]:
				if field[0] not in [ID, P.id_field_name]:
					t_cols.append(field[0])

		for p in participant_ids:
			wc_count = 0
			q_wildcards = []
			q_vars = []
			cols = p_cols + t_cols if p[0] != -1 else t_cols
			for c in cols:
				if not iterable(c):
					q_vars.append(c)
					q_wildcards.append( "`{"+str(wc_count)+"}`")
					wc_count += 1
				else:
					q_vars += c
					q_wildcards.append("`{"+str(wc_count)+"}` AS `{"+ str(wc_count + 1)+"}`")
					wc_count += 2
			q = "SELECT " + ",".join(q_wildcards) + " FROM `{0}` ".format(P.primary_table)
			for t in ['participants'] + join_tables if p[0] != -1 else join_tables:
				key = 'id' if t == 'participants' else 'participant_id'
				q += " JOIN {0} ON `{1}`.`participant_id` = `{0}`.`{2}` ".format(t, P.primary_table, key)
			q += " WHERE `{0}`.`participant_id` = ?".format(P.primary_table)
			q = q.format(*q_vars)
			p_data = []
			for trial in self.__master.query(q, q_vars=tuple([p[0]])):
				row_str = TAB.join(str(col) for col in trial)
				if p[0] == -1: row_str = TAB.join([P.default_demo_participant_str, row_str])
				p_data.append(row_str)
			data.append([p[0], p_data])
		return data


	def export(self, table=None, multi_file=True, join_tables=None):
		#TODO: make sure p_id increments sequentially, ie. skips demo_user
		#TODO: make option for exporting non-devmode/complete participants only
		if table != None:
			P.primary_table = table
		try:
			join_tables = join_tables[0].split(",")
		except TypeError:
			join_tables = []
		column_names = self.build_column_header(multi_file, join_tables)
		data = self.collect_export_data(multi_file, join_tables)

		cso("\n<green>*** Exporting data from {0} ***</green>\n".format(P.project_name))
		if multi_file:
			for data_set in data:
				p_id = data_set[0]
				if p_id != -1:
					header = self.export_header(p_id)
					incomplete = len(data_set[1]) != P.trials_per_block * P.blocks_per_experiment
					file_path = self.filepath_str(p_id, multi_file, incomplete)
					data_file = open(file_path, "w+")
					data_file.write("\n".join([header, column_names, "\n".join(data_set[1])]))
					data_file.close()
					print("    - Participant {0} successfully exported.".format(p_id))
		else:
			combined_data = []
			p_count = 0
			for data_set in data:
				if data_set[0] != -1:
					p_count += 1
					combined_data += data_set[1]
			header = self.export_header()
			file_path = self.filepath_str(multi_file=False)
			data_file = open(file_path, "w+")
			data_file.write("\n".join([header, column_names, "\n".join(combined_data)]))
			data_file.close()
			print("    - Data for {0} participants successfully exported.".format(p_count))
		print("") # newline between export info and next prompt for aesthetics' sake


	def export_header(self, user_id=None):
		#TODO: make header info reflect info when participant was run, instead of just current settings which
		# is somewhat misleading (add runtime_info table)
		klibs_vars   = ["KLIBS INFO", ["KLibs Commit", P.klibs_commit]]
		eyelink_vars = ["EYELINK SETTINGS",
						["Saccadic Velocity Threshold", P.saccadic_velocity_threshold],
						["Saccadic Acceleration Threshold", P.saccadic_acceleration_threshold],
						["Saccadic Motion Threshold", P.saccadic_motion_threshold]]
		exp_vars 	 = ["EXPERIMENT SETTINGS",
						["Trials Per Block", P.trials_per_block],
						["Blocks Per Experiment", P.blocks_per_experiment]]
		
		header = ""
		header_info = [klibs_vars, exp_vars]
		if P.eye_tracking and P.eye_tracker_available:
			header_info.insert(1, eyelink_vars)
		for info in header_info:
			header += "# >>> {0}\n".format(info[0])
			header += "\n".join(["# {0}: {1}".format(var[0], var[1]) for var in info[1:]])
			header += "\n"
			if info[0] != "EXPERIMENT SETTINGS": header += "#\n"

		return header
		

	def filepath_str(self, participant_id=None, multi_file=False, incomplete=False):
		if multi_file:
			created_q = "SELECT `created` FROM `participants` WHERE `id` = ?"
			created = str(self.__master.query(created_q, q_vars=[1], fetch_all=False).fetchone()[0][:10])
		basename = "p{0}.{1}".format(str(participant_id), created) if multi_file else "{0}_all_trials".format(P.project_name)
		duplicate_count = 0
		while True:
			# Generate suffix and see if file already exists with that name. If it does, keep incremeting
			# the numeric part of the suffix until it doesn't.
			suffix = DATA_EXT
			if incomplete: suffix = "_incomplete" + suffix
			if duplicate_count: suffix = "_{0}".format(duplicate_count) + suffix
			fname = basename + suffix
			filepath = join(P.incomplete_data_dir if incomplete else P.data_dir, fname)
			if isfile(filepath):
				duplicate_count += 1
			else:
				break
		return filepath

	def rebuild(self):
		if not isfile(P.schema_file_path):
			print("Error: No SQL schema found at '{0}'. Please make sure there is a valid "
				  "schema file at this location and try again.\n".format(P.schema_file_path))
			return False

		self.__master._drop_tables()
		try:
			self.__master._deploy_schema(P.schema_file_path)
			self.__master.build_table_schemas()
			print("\nDatabase successfully rebuilt! Please make sure to update your experiment.py "
				  "to reflect any changes you might have made to tables or column names.\n")
		except (sqlite3.ProgrammingError, sqlite3.OperationalError, ValueError) as e:
			cso("\n<red>Syntax error encountered in '{0}'. Please double-check the formatting of "
				"the schema and try again.</red>\n".format(P.schema_filename))
			self.__master._drop_tables(self.__master.table_list)
			self.__restore__()
			raise e

	## Convenience methods that all pass to corresponding method of current DB ##

	def commit(self):
		self.__current.db.commit()

	def current(self, *args, **kwargs):
		return self.__current.current(*args, **kwargs)

	def exists(self, *args, **kwargs):
		return self.__current.exists(*args, **kwargs)
	
	def init_entry(self, *args, **kwargs):
		return self.__current.init_entry(*args, **kwargs)
	
	def insert(self, *args, **kwargs):
		return self.__current.insert(*args, **kwargs)
	
	def is_unique(self, *args, **kwargs):
		return self.__current.is_unique(*args, **kwargs)
	
	def last_id_from(self, *args, **kwargs):
		return self.__current.log(*args, **kwargs)

	def log(self, *args, **kwargs):
		return self.__current.log(*args, **kwargs)

	def query(self, *args, **kwargs):
		return self.__current.query(*args, **kwargs)

	def update(self, *args, **kwargs):
		return self.__current.update(*args, **kwargs)
		