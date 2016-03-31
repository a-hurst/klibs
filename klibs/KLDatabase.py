__author__ = 'jono'

import shutil
import sqlite3
from klibs.KLUtilities import *


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
		schema_str = "{\n"
		for col in self.schema:
			schema_str += "\t\t\t" + col + " : " + repr(self.schema[col]) + "\n"
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
			if self.data[self.index_of(column[0])] == SQL_NULL or not self.data[self.index_of(column[0])]:
				if self.allow_null(column[0]):
					insert_template[self.index_of(column)] = SQL_NULL
					self.data[self.index_of(column)] = SQL_NULL
				elif column[0] == ID:
					self.data[0] = SQL_NULL
					insert_template[0] = SQL_NULL
				else:
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
		raise IndexError("Field '{0}' not found in table '{1}'".format(field, self.table_name))

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
				value = float(value)
			else:
				value = str(value)
			if self.type_of(field) == PY_STR:
				value = "'{0}'".format(value)
			if not value:
				value = SQL_NULL

		self.data[self.index_of(field)] = value

	def report(self):
		print self.schema


# TODO: create a "logical" column type when schema-streama comes along & handling therewith in Database
class Database(object):
	__default_table = None
	__open_entries = {}
	__current_entry = None
	db = None
	cursor = None
	schema = None
	db_backup_path = None
	table_schemas = {}

	def __init__(self):
		self.__init_db()
		self.build_table_schemas()

	def __catch_db_not_found(self):
		self.db = None
		self.cursor = None
		self.schema = None
		err_string = "No database file was present at '{0}'. \nYou can (c)reate it, (s)upply a different path or (q)uit."
		user_action = raw_input(err_string.format(Params.database_path))
		if user_action ==DB_SUPPLY_PATH:
			Params.database_path = raw_input("Great. Where might it be?")
			self.__init_db()
		elif user_action == DB_CREATE:
			f = open(Params.database_path, "a").close()
			self.__init_db()
		else:
			quit()

	def __init_db(self):
		if os.path.exists(Params.database_path):
			shutil.copy(Params.database_path, Params.database_backup_path)
			self.db = sqlite3.connect(Params.database_path)
			self.cursor = self.db.cursor()
			table_list = self.__tables()
			if len(table_list) == 0:
				if os.path.exists(Params.schema_file_path):
					self.__deploy_schema(Params.schema_file_path)
					return True
				elif os.path.exists(Params.schema_file_path_legacy):
					self.__deploy_schema(Params.schema_file_path_legacy)
					return True
				else:
					raise RuntimeError("Database exists but no tables were found and no table schema were provided.")
		else:
			self.__catch_db_not_found()

	def __tables(self):
		# TODO: I changed tableCount to tableList and made it an attribute as it seems to be used in rebuild. Verify this.
		self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
		self.table_list = self.cursor.fetchall()
		return self.table_list

	def __drop_tables(self, table_list=None, kill_app=False):
		if table_list is None:
			table_list = self.__tables()
		for n in table_list:
			if str(n[0]) != "sqlite_sequence":
				self.cursor.execute("DROP TABLE `{0}`".format(str(n[0])))
		self.db.commit()
		if kill_app:
			self.db.close()
			self.__restore()
			quit()

	def __restore(self):
		# restores database file from the back-up of it
		os.remove(Params.database_path)
		os.rename(Params.database_backup_path, Params.database_path)

	def __deploy_schema(self, schema):
		f = open(schema, 'rt')
		self.cursor.executescript(f.read())
		return True

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
					if col[2] == SQL_STR:
						col_type = PY_STR
					elif col[2] == SQL_BIN:
						col_type = PY_BIN
					elif col[2] in (SQL_INT, SQL_KEY):
						col_type = PY_INT
					elif col[2] in (SQL_FLOAT, SQL_REAL):
						col_type = PY_FLOAT
					else:
						raise ValueError("Invalid or unsupported type ({0}) for {1}.{2}'".format(col[2], table, col[1]))
					allow_null = col[3] == 0
					table_cols.append([str(col[1]), {'type': col_type, 'allow_null': allow_null}])
				tables[table] = table_cols
		self.table_schemas = tables
		return True

	def flush(self):
		self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
		for tableTuple in self.cursor.fetchall():
			table = str(tableTuple[0])  # str() necessary b/c tableTuple[0] is in unicode
			if table == "sqlite_sequence":
				pass
			else:
				self.cursor.execute("DELETE from `{0}`".format(table))
		self.db.commit()

	def rebuild(self):
		#todo: make this optionally handle the backup database too
		self.__drop_tables()
		e = "Error: Database schema could not be deployed; there is a syntax error in the SQL file."
		if self.schema is not None:
			if self.__deploy_schema(self.schema, False):
				initialized = True
			else:
				self.__drop_tables(self.table_list, True)
				raise IOError(e)
		elif Params.schema_file_path is not None:
			if self.__deploy_schema(Params.schema_file_path):
				initialized = True
			else:
				self.__drop_tables(self.table_list)
				raise IOError(e)

		if self.build_table_schemas():
			self.__open_entries = {}
			self.__current_entry = None
			print  "Database successfully rebuilt; exiting program. Be sure to disable the call to Database.rebuild() before relaunching."
			quit()

	def fetch_entry(self, instance_name): return self.__open_entries[instance_name]

	def init_entry(self, table_name, instance_name=None, set_current=True):
		try:
			if instance_name is None: instance_name = table_name
			self.__open_entries[instance_name] = EntryTemplate(table_name, self.table_schemas[table_name], instance_name)
			if set_current: self.current(self.__open_entries[instance_name])
		except IndexError:
			raise IndexError("Table {0} not found in the KLDatabase.table_schemas.".format(table_name))

	def last_id_from(self, table, id_column='id'):
		if not table in self.table_schemas:
			raise ValueError("Table '{0}' not found in current database".format(table))

		found = False
		for col in self.table_schemas[table]:
			if col[0] == id_column:
				found = True
		if not found:
			raise ValueError("Table '{0}' does not have column '{1}'.".format(table, id_column))
		query = "SELECT max(`{0}`) from `{1}`".format(id_column, table)
		return self.query(query).fetchall()[0][0]
		# try:
		# except IndexError:
		# 	return False

	def empty(self, table):
		pass

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

	def is_unique(self, table, column, value, value_type=SQL_STR):
		if value_type in [SQL_FLOAT, SQL_INT, SQL_REAL]:
			query_str = "SELECT * FROM `{0}` WHERE `{1}` = {2}".format(table, column, value)
		else:
			query_str = "SELECT * FROM `{0}` WHERE `{1}` = '{2}'".format(table, column, value)
		return len(self.query(query_str, QUERY_SEL, True).fetchall()) == 0

	def exists(self, table, column, value, value_type=SQL_STR):
		if value_type in [SQL_FLOAT, SQL_INT, SQL_REAL]:
			query_str = "SELECT * FROM `{0}` WHERE `{1}` = {2}".format(table, column, value)
		else:
			query_str = "SELECT * FROM `{0}` WHERE `{1}` = '{2}'".format(table, column, value)
		return len(self.query(query_str, QUERY_SEL, True).fetchall()) > 0

	def test_data(self, table):
		# TODO: allow rules per column such as length
		pass

	def insert(self, data=None, table=None, clear_current=True):
		# todo: check if the table uses participant_id column; if no id in data, add it
		if data is None:
			try:
				data = self.current()
			except RuntimeError:  # exception below is a more informative account of the current problem
				raise RuntimeError("No data to insert; provide insert data or assign a current KLEntryTemplate instance.")
			if not table: table = data.table_name

		try:
			self.cursor.execute(data.insert_query())
			if clear_current and self.current().name == data.name: self.current(False)
		except AttributeError:
			self.cursor.execute(self.query_str_from_raw_data(table, data))
		self.db.commit()
		return self.cursor.lastrowid

	def query_str_from_raw_data(self, table, data):
		try:
			template = self.table_schemas[table]
		except KeyError:
			try:
				template = self.table_schemas[self.__default_table]
			except:
				raise RuntimeError("Table not found; provide table reference or ensure KLDatabase.__default_table is set.")
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

	def query(self, query, query_type=QUERY_SEL, return_result=True):
		result = self.cursor.execute(query)
		if query_type != QUERY_SEL: self.db.commit()
		return result if return_result else True

	def p_filename_str(self, participant_id, multi_file=False, incomplete=False, duplicate_count=None):
			if multi_file:
		 		created = str(self.query("SELECT `created` FROM `participants` WHERE `id` = {0}".format(1)).fetchone()[0][:10])
			fname = "p{0}.{1}".format(str(participant_id), created) if multi_file else "{0}_all_trials".format(Params.project_name)
			if duplicate_count: fname += "_{0}".format(duplicate_count)
			if incomplete: fname += "_incomplete"
			fname += DATA_EXT
			if incomplete:
				return [fname, os.path.join(Params.incomplete_data_path, fname)]
			else:
				return [fname, os.path.join(Params.data_path, fname)]

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
			self.cursor.execute(self.query_str_from_raw_data(table, data))
		self.db.commit()
		return self.cursor.lastrowid

	def collect_export_data(self, multi_file=True):
		participant_ids = self.query("SELECT `id`, `userhash` FROM `participants`").fetchall()
		participant_ids.insert(0, (-1,))  # for test data collected before anonymous_user added to collect_demographics()
		data = []

		#  build query strings for retrieving data as/if configured by experimenter
		p_field_str = ""
		t_field_str = ""

		#  random_seed has to be added to every participant row when exporting to multi-file
		default_fields = Params.default_participant_fields if multi_file else Params.default_participant_fields_sf
		for field in default_fields:
			if iterable(field):  # ie. the id/userhash field--id used internally, userhash for output
				p_field_str += "`participants`.`{0}` AS `{1}`, ".format(*field)
			else:
				p_field_str += "`participants`.`{0}`, ".format(field)
		for field in self.table_schemas['trials']:
			if field[0] not in [ID, Params.id_field_name]:
				t_field_str += "`trials`.`{0}`, ".format(field[0])
		t_field_str = t_field_str[:-2]  # remove additional comma & space
		for p in participant_ids:
			if p[0] == -1:  # legacy test data collected before anonymous_user added to collect_demographics()
				q = "SELECT {0} FROM `trials` WHERE `trials`.`participant_id` = -1".format(t_field_str)
			else:
				q = "SELECT {0} {1} FROM `trials` JOIN `participants` ON `trials`.`participant_id` = {2} WHERE `participant` = '{3}'".format(p_field_str, t_field_str, p[0], p[1])
			p_data = []
			for trial in self.query(q).fetchall():
				row_str = TAB.join(str(col) for col in trial)
				if p[0] == -1: row_str = TAB.join([Params.default_demo_participant_str, row_str])
				p_data.append(row_str) if multi_file else data.append(row_str)
			if multi_file: data.append([p[0], p_data])
		return data if multi_file else [data]

	def export_header(self, user_id=None):
		# the display information below isn't available when export is called but SHOULD be accessible, somehow, for export--probably this should be added to the participant table at run time
		# klibs_vars = [ "KLIBS Info", ["KLIBs Version", Params.klibs_version], ["Display Diagonal Inches", Params.screen_diagonal_in], ["Display Resolution", "{0} x {1}".format(*Params.screen_x_y)], ["Random Seed", random_seed]]
		klibs_vars = [ "KLIBS INFO", ["KLIBs Commit", Params.klibs_commit]]
		if user_id:  # if building a header for a single participant, include the random seed
			q = "SELECT `random_seed` from `participants` WHERE `participants`.`id` = '{0}'".format(user_id)
			klibs_vars.append(["random_seed", self.query(q).fetchall()[0][0]])
		eyelink_vars = [ "EYELINK SETTINGS",
						 ["Saccadic Velocity Threshold", Params.saccadic_velocity_threshold],
						 ["Saccadic Acceleration Threshold", Params.saccadic_acceleration_threshold],
						 ["Saccadic Motion Threshold", Params.saccadic_motion_threshold]]
		exp_vars = [ "EXPERIMENT SETTINGS",
					 ["Trials Per Block", Params.trials_per_block],
					 ["Trials Per Practice Block", Params.trials_per_practice_block],
					 ["Blocks Per Experiment", Params.blocks_per_experiment],
					 ["Practice Blocks Per Experiment", Params.practice_blocks_per_experiment] ]
		header = ""
		for info in [klibs_vars, eyelink_vars, exp_vars]:
			header += "# >>> {0}\n".format(info[0])
			header += "\n".join(["# {0}: {1}".format(var[0], var[1]) for var in info[1:]])
			header += "\n"
			if info[0] != "EXPERIMENT SETTINGS": header += "#\n"

		return header

	def build_column_header(self, multi_file=True):
		column_names = []
		for field in (Params.default_participant_fields if multi_file else Params.default_participant_fields_sf):
			column_names.append(field[1]) if iterable(field) else column_names.append(field)
		column_names = [snake_to_camel(col) for col in column_names]

		for field in self.table_schemas['trials']:
			if field[0][-2:] != "id": column_names.append(field[0])
		return  TAB.join(column_names)

	def export(self, multi_file=True, join_tables=None):
		column_names = self.build_column_header()
		data = self.collect_export_data(multi_file)

		for data_set in data:
			p_id = data_set[0]
			if p_id == -1:
				pass
			else:
				header = self.export_header(p_id)
				if multi_file:
					incomplete = multi_file and len(data_set[1]) != Params.trials_per_block * Params.blocks_per_experiment
				else:
					incomplete = False
				file_strings = self.p_filename_str(p_id, multi_file, True) if incomplete else self.p_filename_str(p_id, multi_file)
				if os.path.isfile(file_strings[1]):
					duplicate_count = 1
					while os.path.isfile(os.path.join(file_strings[1])):
						file_strings = self.p_filename_str(p_id, multi_file, incomplete, duplicate_count)
						duplicate_count += 1
				data_file = open(os.path.join(file_strings[1]), "w+")
				data_file.write("\n".join([header, column_names, "\n".join(data_set[1])]))
				data_file.close()

	@property
	def default_table(self):
		return self.__default_table

	@default_table.setter
	def default_table(self, name):  # todo: error handling
		self.__default_table = name