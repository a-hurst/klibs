__author__ = 'jono'

import os
import shutil
import sqlite3
import Params as Params


class EntryTemplate(object):
	null_field = "DELETE_THIS_FIELD"
	sql_field_delimiter = "`,`"
	table_name = None

	def __init__(self, table_name, table_schema, instance_name):

		if type(table_schema) is dict:
			self.schema = table_schema
		else:
			raise TypeError
		if type(table_name) is str:
			self.table_name = table_name
		else:
			raise TypeError
		try:
			self.name = instance_name
			if not self.name:
				raise AttributeError(
					'InstanceName could not be set, ensure parameter is passed during initialization and is a string.')
		except AttributeError as e:
			self.err(e, 'EntryTemplate', '__init__', kill=True)
		self.data = ['null', ] * len(table_schema)  # create an empty tuple of appropriate length

	def pr_schema(self):
		schema_str = "{\n"
		for col in self.schema:
			schema_str += "\t\t\t" + col + " : " + repr(self.schema[col]) + "\n"
		schema_str += "\t\t}"
		return schema_str

	def build_query(self, query_type):
		insert_template = ['null', ] * len(self.schema)
		for field_name in self.schema:
			field_params = self.schema[field_name]
			column_order = field_params['order']
			insert_template[column_order] = field_name
			if self.data[column_order] == self.null_field:
				if field_params['allow_null']:
					insert_template[column_order] = self.null_field
				elif query_type == 'insert' and field_name == 'id':
					self.data[0] = self.null_field
					insert_template[0] = self.null_field
				else:
					raise ValueError("No data for the required (ie. not null) column '{0}'.".format(field_name))

		insert_template = self.__tidy_nulls(insert_template)
		self.data = self.__tidy_nulls(self.data)
		if query_type == 'insert':
			fields = "`{0}`".format(self.sql_field_delimiter.join(insert_template))
			vals = ",".join(self.data)
			query_string = "INSERT INTO `{0}` ({1}) VALUES ({2})".format(self.table_name, fields, vals)
			return query_string
		elif query_type == 'update':
			pass
		#TODO: build logic for update statements as well (as against only insert statements)

	def __tidy_nulls(self, data):
		return filter(lambda column: column != self.null_field, data)

	def log(self, field, value):
		# TODO: Add some basic logic for making type conversions where possible (ie. if expecting a float
		# but an int arrives, try to cast it as a float before giving up
		column_order = self.schema[field]['order']
		column_type = self.schema[field]['type']
		if field not in self.schema:
			raise ValueError("No field named '{0}' exists in the table '{1}'".format(field, self.table_name))
		# SQLite has no bool data type; conversion happens now b/c the value/field comparison below can't handle a bool
		if value is True:
			value = 1
		elif value is False:
			value = 0
		# all values must be strings entering db; values enterting string columns must be single-quote wrapped as well
		if (self.schema[field]['allow_null'] is True) and value is None:
			self.data[column_order] = self.null_field
		elif column_type == 'str':
			self.data[column_order] = "'{0}'".format(str(value))
		else:
			self.data[column_order] = str(value)

	def report(self):
		print self.schema


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
		if user_action == "s":
			Params.database_path = raw_input("Great. Where might it be?")
			self.__init_db()
		elif user_action == "c":
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
				else:
					raise RuntimeError("Database exists but no tables were found and no table schema were provided.")
		else:
			self.__catch_db_not_found()

	def __tables(self):
		#TODO: I changed tableCount to tableList and made it an attribute as it seems to be used in rebuild. Verify this.
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
				table_cols = {}
				self.cursor.execute("PRAGMA table_info(" + table + ")")
				columns = self.cursor.fetchall()

				# convert sqlite3 types to python types
				for col in columns:
					if col[2] == 'text':
						col_type = 'str'
					elif col[2] == 'blob':
						col_type = 'binary'
					elif col[2] in ('integer', 'integer key'):
						col_type = 'int'
					elif col[2] in ('float', 'real'):
						col_type = 'float'
					else:
						col_type = 'unknown'
						e_str = "column '{0}' of table '{1}' has type '{2}' on the database but was assigned a type of \
								'unknown' during schema building'"
						self.warn(e_str.format(col[1], table, col[2]), "Database", "build_table_schemas")
					allow_null = False
					if col[3] == 0:
						allow_null = True
					table_cols[str(col[1])] = {'order': int(col[0]), 'type': col_type, 'allow_null': allow_null}
				tables[table] = table_cols
		self.table_schemas = tables

		return True

	def flush(self):
		self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
		for tableTuple in self.cursor.fetchall():
			table = str(tableTuple[0]) #str() necessary b/c tableTuple[0] is in unicode
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
			self.__current_entry = 'None'
			print  "Database successfully rebuilt; exiting program. Be sure to disable the call to Database.rebuild() before relaunching."
			# TODO: Make this call App.message() somehow so as to be clearer.Or better, relaunch the app somehow!!
			# m = "Database successfully rebuilt; exiting program. Be sure to disable the call to Database.rebuild() before relaunching."
			# App.message(m, location="center", fullscreen=True, fontSize=48, color=(0,255,0))
			quit()

	def entry(self, instance=None):
		if instance is None:
			try:
				return self.__open_entries[self.__current_entry]
			except:
				print self.err() + "Database\n\tentry(): A specific instance name was not provided and there is no current entry set.\n"
		else:
			try:
				return self.__open_entries[instance]
			except:
				print self.err() + "Database\n\tentry(): No currently open entries named '" + instance + "' exist."

	def init_entry(self, table_name, instance_name=None, set_current=True):
		if type(table_name) is str:
			if self.table_schemas[table_name]:
				if instance_name is None:
					instance_name = table_name
				self.__open_entries[instance_name] = EntryTemplate(table_name, self.table_schemas[table_name], instance_name)
				if set_current:
					self.current(instance_name)
			else:
				print "No table with the name '" + table_name + "' was found in the Database.tableSchemas."
		else:
			raise ValueError("tableName must be a string.")

	def empty(self, table):
		pass

	def log(self, field, value, instance=None):
		if instance is not None and self.__open_entries[instance]:
			self.__current_entry = instance
		elif instance is None and self.__current_entry != 'None':
			instance = self.__current_entry
		else:
			raise ValueError("No default entry is set and no instance was passed.")
		self.__open_entries[instance].log(field, value)

	def current(self, verbose=False):
		if verbose == (0 or None or 'None' or False):
			self.__current_entry = 'None'
			return True
		if verbose == 'return':
			return self.__current_entry
		if type(verbose) is str:
			if self.__open_entries[verbose]:
				self.__current_entry = verbose
				return True
			return False
		if self.__current_entry != 'None':
			if verbose:
				return self.__current_entry
			else:
				return True
		else:
			if verbose:
				return 'None'
			else:
				return False

	def is_unique(self, value, field, table):
		query = "SELECT * FROM `{0}` WHERE `{1}` = '{2}'".format(table, field, value)
		self.cursor.execute(query)
		result = self.cursor.fetchall()
		if len(result) > 0:
			return False
		else:
			return True

	def test_data(self, table):
		# TODO: allow rules per column such as length
		pass

	def insert(self, data=None, table=None, tidy_execute=True):
		# todo: check if the table uses participant_id column; if no id in data, add it
		if data is None:
			current = self.current('return')
			data = self.entry(current)
			if not data:
				raise AttributeError("No data was provided and a Database.__currentEntry is not set.")
		data_is_entry_template = False # expected use is to insert from an EntryTemplate object, but raw data is also allowed
		if data.__class__.__name__ == 'EntryTemplate':
			data_is_entry_template = True
			query = data.build_query('insert')
		else:
			# this else statement may be broken as of Aug 2013 (ie. since Ross was involved, it's not been returned to)
			template = None
			if table:
				if not self.__default_table:
					raise AttributeError(
						"Either provide a table when calling insert() or set a defaultTable with App.Database.setDefaultTable().")
				else:
					table = self.__default_table
				template = self.table_schemas[table]
			if not template:
				raise AttributeError(
					"The supplied table name, '{0}' was not found in Database.tableSchemas".format(table))
			field_count = len(template)
			if template['id']:
				field_count -= 1  # id will be supplied by database automatically on cursor.execute()
			clean_data = [None, ] * field_count
			insert_template = [None, ] * field_count
			if len(data) == field_count:
				for fieldName in template:
					field = template[fieldName]
					order = field['order']
					if template['id']:
						order -= 1
					if type(data[order]).__name__ == field['type']:
						insert_template[order] = fieldName
						if field['type'] == ('int' or 'float'):
							clean_data[order] = str(data[order])
						else:
							clean_data[order] = "'" + str(data[order]) + "'"
			else:
				raise AttributeError('Length of data list exceeds number of table columns.')
			query = "INSERT INTO `{0}` ({1}) VALUES ({2})".format(table, ",".join(insert_template), ",".join(clean_data))
		self.cursor.execute(query)
		self.db.commit()
		if tidy_execute and data_is_entry_template:
			if self.__current_entry == data.name:
				self.current()  # when called without a parameter current() clears the current entry
		return True

	def query(self, query, do_return=True):
		result = self.cursor.execute(query)
		self.db.commit()
		if result and do_return:
			return result
		#add in error handling for SQL errors

	def table_headers(self, table, join_with=[], as_string=False):
		# try:
			table = self.table_schemas[table]
			table_headers_list = [None] * len(table)
			participant_headers_list = None
			for column in table:
				table_headers_list[table[column]['order']] = column
			table_headers_list = table_headers_list[1:]  # remove id column

			table_indeces_map = {}  # keeps track of original table column indeces for multiple joins
			for i in range(0, len(table_headers_list)):
				table_indeces_map[str(i)] = i

			# try:
			for join in join_with:
		# 		try:
				print join
				join_headers = self.table_schemas[join[0]]
				excluded_columns = join[2] if len(join) == 3 else []
				join_headers_list = [None] * len(join_headers)
				print join_headers_list
				for column in join_headers:
					if column not in excluded_columns:
						index = join_headers[column]['order']
						join_headers_list[index] = column
				join_headers_list = [col for col in join_headers_list if col is not None]
				join_headers_list = join_headers_list[1:]
							# try:
				print table_indeces_map
				index = table_indeces_map[str(join[1])]
				table_headers_list[index:index] = join_headers_list
				table_indeces_map[str(join[1])] += len(join_headers_list)
				if len(table_indeces_map) < len(table_headers_list):
					table_indeces_map[str(len(table_headers_list))] = len(table_headers_list)
			# 			except Exception as e:
			# 				raise Exception(e)
			# 				raise ValueError("Second element of join_with tables must be a index in range of 'table'")
			# 		except Exception as e:
			# 			raise Exception(e)
			# 			raise ValueError("Table in argument 'join_with' was not found in in Database.tables dict ")
			# except Exception as e:
			# 	raise Exception(e)
#				raise TypeError("Argument 'join_with' must be iterable.")

			return table_headers_list if not as_string else "{0}\n".format("\t ".join(table_headers_list))
		# except:
		# 	raise ValueError("Value for argument 'table' was not found in Database.tables dict.")

	def export(self, path=None, multi_file=True, join_tables=None):
		# todo: write stuff for joining tables
		# todo: add behaviors for how to deal with multiple files with the same participant id (ie. append, overwrite, etc.)
		participants = self.query("SELECT * FROM `participants`").fetchall()
		table_header = self.table_headers("trials", [["participants", 1, ['userhash']]], True)
		# table_header = self.table_headers("trials", as_string=True)
		for p in participants:
			block_num = 1
			trials_this_block = 0
			trials = self.query("SELECT * FROM `trials` WHERE `participant_id` = {0}".format(p[0])).fetchall()
			file_name_str = "p{0}_{1}.txt"
			duplicate_file_name_str = "p{0}.{1}_{2}.txt"
			file_path = Params.data_path
			if len(trials) != Params.trials_per_block * Params.blocks_per_experiment:
				file_path = Params.incomplete_data_path
				file_name_str = "p{0}_{1}_incomplete.txt"
				duplicate_file_name_str = "p{0}.{1}_{2}_incomplete.txt"
			file_name = file_name_str.format(p[0], str(p[5])[:10])  # second format arg = date sliced from date-time
			if os.path.isfile(os.path.join(file_path, file_name)):
				unique_file = False
				append = 1
				while not unique_file:
					file_name = duplicate_file_name_str.format(p[0], append, str(p[5])[:10])
					if not os.path.isfile(os.path.join(file_path, file_name)):
						unique_file = True
					else:
						append += 1
			participant_file = open(os.path.join(file_path, file_name), "w+")
			participant_file.write(table_header)
			for trial in trials:
				trial = trial[1:]
				if trials_this_block == 120:
					block_num += 1
					trials_this_block = 0
				trials_this_block += 1
				trial = list(trial)
				trial[1:1] = p[2:]
				trial[5] = block_num
				row_string = "\t".join([str(col) for col in trial])
				participant_file.write("{0}\n".format(row_string))
			participant_file.close()



	@property
	def default_table(self):
		return self.__default_table

	@default_table.setter
	def default_table(self, name):  # todo: error handling
		self.__default_table = name