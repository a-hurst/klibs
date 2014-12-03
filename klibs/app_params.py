__author__ = 'jono'
from constants import *

class AppParams(object):
	initialized = False

	key_maps = dict()  # todo: create a class, KeyMapper, to manage key maps
	id_field_name = "participant_id"
	__random_seed = None
	collect_demographics = True
	__eye_tracking = False
	__exp_factors = None
	__instructions = False  # todo: instructions file
	__practicing = False
	__paused = False
	testing = False
	__default_alert_duration = 1
	default_alert_duration = 3  # seconds
	default_fill_color = (255, 255, 255)

	__project_name = None
	__database_filename = None
	__schema_filename = None
	__log_filename = None

	__asset_path = None
	__database_path = None
	__database_backup_path = None
	__edf_path = None
	__log_file_path = None
	__schema_file_path = None

	__monitor_x = None
	__monitor_y = None
	__diagonal_px = None
	__ppi = 96  # pixels-per-inch, varies between CRT & LCD screens
	__pixels_per_degree = None  # pixels-per-degree, ie. degree of visual angle
	__ppd = None  # pixels-per-degree, ie. degree of visual angle
	__screen_c = (None, None)
	__screen_ratio = None
	__screen_x = None
	__screen_y = None
	__screen_x_y = (None, None)
	__view_unit = "in"  # inch, not the preposition
	__view_distance = 56  # in centimeters, 56cm = in 1deg of visual angle per horizontal cm of screen

	__saccadic_velocity_threshold = 20
	__saccadic_acceleration_threshold = 5000
	__saccadic_motion_threshold = 0.15
	__default_font_size = 28

	__fixation_size = 1  # deg of visual angle
	__box_size = 1  # deg of visual angle
	__cue_size = 1  # deg of visual angle
	__cue_back_size = 1  # deg of visual angle
	__verbosity = 10  # Should hold a value between 0-10, with 0 being no errors and 10 being all errors

	__trials = 0
	__trials_per_block = 0
	__trials_per_practice_block = 0
	__blocks = 0
	__blocks_per_experiment = 0
	__practice_blocks_per_experiment = 0
	# tar_dur = 300   # todo: ask ross wtf this is
	# negative = 0   # todo: ask ross wtf this is
	# positive = 1   # todo: ask ross wtf this is
	# duration = 10000  # todo: ask ross wtf this is

	def __init__(self):
		pass

	def init_project(self):
		# todo: write checks in these setters to not overwrite paths that don't include asset_paths (ie. arbitrarily set)
		self.database_filename = self.project_name
		self.schema_filename = self.project_name
		self.log_filename = self.project_name
		self.edf_path = os.path.join(self.asset_path, EDF)  # todo: write edf management
		self.log_file_path = os.path.join(self.asset_path, self.log_filename)
		self.schema_file_path = os.path.join(self.asset_path, self.schema_filename)
		self.database_path = os.path.join(self.asset_path, self.database_filename)
		self.database_backup_path = self.database_path + BACK
		self.data_path = os.path.join(self.asset_path, "Data")
		self.incomplete_data_path = os.path.join(self.data_path, "incomplete")
		self.initialized = True
		return True

	def setup(self, project_name, asset_path):
		self.project_name = project_name
		self.asset_path = asset_path
		return self.init_project()

	@property
	def project_name(self):
		return self.__project_name

	@project_name.setter
	def project_name(self, project_name):
		if type(project_name) is str:
			self.__project_name = project_name
		else:
			raise TypeError("Argument 'project_name' must be a string.")

	@property
	def asset_path(self):
		return self.__asset_path

	@asset_path.setter
	def asset_path(self, asset_path):
		if type(asset_path) is str:
			if os.path.exists(asset_path):
				if os.path.isdir(asset_path):
					self.__asset_path = asset_path
				else:
					raise IOError("Argument 'asset_path' does not point to a directory.")
			else:
				raise IOError("Argument 'asset_path' does not point to valid  location on the file system.")
		else:
			raise TypeError("Argument 'asset_path' must be string indicating a the path to a writeable directory..")

	@property
	def database_filename(self):
		return self.__database_filename

	@database_filename.setter
	def database_filename(self, database_filename):
		if type(database_filename) is str:
			database_filename.rstrip(DB)
			self.__database_filename = database_filename + DB
		else:
			raise TypeError("Argument 'database_filename' must be a string.")

	@property
	def database_path(self):
		return self.__database_path

	@database_path.setter
	def database_path(self, database_path):
		if type(database_path) is str:
			self.__database_path = database_path  # eventually, check if the parent directory exists if the file doesn't
		# 	if os.path.exists(database_path):
		# 		if os.path.isdir(database_path):
		# 			raise IOError("Argument 'database_path' is a directory.")
		# 		else:
		# 	else:  # todo: try to create it
		# 		pass  # it may be created by the Database class initialization process
		# else:
		# 	raise TypeError("Argument 'database_path' must be a string and a valid file system location..")

	@property
	def database_backup_path(self):
		return self.__database_backup_path

	@database_backup_path.setter
	def database_backup_path(self, database_backup_path):
		if type(database_backup_path) is str:
			self.__database_backup_path = database_backup_path
		# 	if os.path.exists(database_backup_path):
		# 		if os.path.isdir(database_backup_path):
		# 			raise IOError("Argument 'database_backup_path' is a directory.")
		# 		else:
		# 	else:  # todo: try to create it
		# 		pass  # it may be created by the Database class initialization process
		# else:
		# 	raise TypeError("Argument 'database_backup_path' must be a string and a valid file system location..")

	@property
	def edf_path(self):
		return self.__edf_path

	@edf_path.setter
	def edf_path(self, edf_path):
		if type(edf_path) is str:
			if os.path.exists(edf_path):
				if os.path.isdir(edf_path):
					self.__edf_path = edf_path
				else:
					raise IOError("Argument 'edf_path' does not point to a directory.")
			else:
				raise IOError("Argument 'edf_path' does not point to valid  location on the file system.")
		else:
			raise TypeError("Argument 'edf_path' must be string indicating a the path to a writeable directory..")

	@property
	def data_path(self):
		return self.__data_path

	@data_path.setter
	def data_path(self, data_path):
		if type(data_path) is str:
			if os.path.exists(data_path):
				if os.path.isdir(data_path):
					self.__data_path = data_path
				else:
					raise IOError("Argument 'data_path' does not point to a directory.")
			else:
				raise IOError("Argument 'data_path' does not point to valid  location on the file system.")
		else:
			raise TypeError("Argument 'data_path' must be string indicating a the path to a writeable directory..")

	@property
	def incomplete_data_path(self):
		return self.__incomplete_data_path

	@incomplete_data_path.setter
	def incomplete_data_path(self, incomplete_data_path):
		if type(incomplete_data_path) is str:
			if os.path.exists(incomplete_data_path):
				if os.path.isdir(incomplete_data_path):
					self.__incomplete_data_path = incomplete_data_path
				else:
					raise IOError("Argument 'incomplete_data_path' does not point to a directory.")
			else:
				raise IOError("Argument 'incomplete_data_path' does not point to valid  location on the file system.")
		else:
			raise TypeError("Argument 'incomplete_data_path' must be string indicating a the path to a writeable directory..")


	@property
	def exp_factors(self):
		return self.__exp_factors


	@exp_factors.setter
	def exp_factors(self, factors):
		if type(factors) == dict:
			self.__exp_factors = factors
		elif factors is None:
			self.__exp_factors = None
		else:
			raise ValueError("Argument 'factors' must be a dict.")


	@property
	def log_filename(self):
		return self.__log_filename

	@log_filename.setter
	def log_filename(self, log_filename):
		if type(log_filename) is str:
			log_filename.rstrip(LOG)
			self.__log_filename = log_filename + LOG
		else:
			raise TypeError("Argument 'log_filename' must be a string.")

	@property
	def log_file_path(self):
		return self.__log_file_path

	@log_file_path.setter
	def log_file_path(self, log_file_path):
		if type(log_file_path) is str:
			if os.path.exists(log_file_path):
				if os.path.isdir(log_file_path):
					raise IOError("Argument 'log_file_path' is a directory.")
				else:
					self.__log_file_path = log_file_path
			else:  # todo: try to create it
				raise IOError("Argument 'log_file_path' does not point to a valid location on the file system.")
		else:
			raise TypeError(
				"Argument 'log_file_path' must be a string and a valid file system location..")

	@property
	def schema_filename(self):
		return self.__schema_filename

	@schema_filename.setter
	def schema_filename(self, schema_filename):
		if type(schema_filename) is str:
			schema_filename.rstrip(SCHEMA)
			self.__schema_filename = schema_filename + SCHEMA
		else:
			raise TypeError("Argument 'schema_filename' must be a string.")

	@property
	def schema_file_path(self):
		return self.__schema_file_path

	@schema_file_path.setter
	def schema_file_path(self, schema_file_path):
		if type(schema_file_path) is str:
			if os.path.exists(schema_file_path):
				if os.path.isdir(schema_file_path):
					raise IOError("Argument 'schema_file_path' is a directory.")
				else:
					self.__schema_file_path = schema_file_path
			else:  # todo: try to create it
				raise IOError("Argument 'schema_file_path' does not point to a valid location on the file system.")
		else:
			raise TypeError(
				"Argument 'schema_file_path' must be a string and a valid file system location..")

	@property
	def view_unit(self):
		return self.__view_unit

	@view_unit.setter
	def view_unit(self, unit):
		if type(unit) is str and unit in (INCH, CM):
			self.__view_unit = unit
		else:
			err_str = "Argument 'unit' must be one two strings, klibs.INCH ('{0}') or klibs.CM ('{1}')."
			raise TypeError(err_str.format(INCH, CM))

	@property
	def view_distance(self):
		return self.__view_distance

	@view_distance.setter
	def view_distance(self, distance):
		if type(distance) in (int, float) and distance > 0:
			self.__view_distance = distance
		else:
			raise TypeError("Argument 'distance' must be a positive number .")

	@property
	def monitor_x(self):
		return self.__monitor_x

	@monitor_x.setter
	def monitor_x(self, monitor_x):
		if type(monitor_x) in (int, float) > 0:
			self.__monitor_x = monitor_x
		else:
			raise TypeError("Argument 'monitor_x' must be a positive number.")

	@property
	def monitor_y(self):
		return self.__monitor_y


	@monitor_y.setter
	def monitor_y(self, monitor_y):
		if type(monitor_y) in (int, float) > 0:
			self.__monitor_y = monitor_y
		else:
			raise TypeError("Argument 'monitor_y' must be a positive number.")

	@property
	def screen_ratio(self):
		return self.__screen_ratio


	@screen_ratio.setter
	def screen_ratio(self, screen_ratio):
		if type(screen_ratio) is tuple and len(screen_ratio) == 2 and all(type(val) is int > 0 for val in screen_ratio):
			self.__screen_ratio = screen_ratio
		elif type(screen_ratio) is str:
			pass  # todo: keep a dict of common screen ratios and look this up rather than doing string manipulation
		else:
			raise TypeError("Argument 'screen_ratio' must be a tuple of two positive integers.")

	@property
	def blocks_per_experiment(self):
		return self.__blocks_per_experiment

	@blocks_per_experiment.setter
	def blocks_per_experiment(self, blocks_per_experiment):
		if type(blocks_per_experiment) is int and blocks_per_experiment >= 0:
			self.__blocks_per_experiment = blocks_per_experiment
		else:
			raise TypeError("Argument 'blocks_per_experiment' must be a positive integer.")


	@property
	def block_number(self):
		return self.__block_number

	@block_number.setter
	def block_number(self, block_number):
		if type(block_number) is int and block_number >= 0:
			self.__block_number = block_number
		else:
			raise TypeError("Argument 'block_number' must be a positive integer.")


	@property
	def practice_blocks_per_experiment(self):
		return self.__practice_blocks_per_experiment

	@practice_blocks_per_experiment.setter
	def practice_blocks_per_experiment(self, practice_blocks_per_experiment):
		if type(practice_blocks_per_experiment) is int and practice_blocks_per_experiment >= 0:
			self.__practice_blocks_per_experiment = practice_blocks_per_experiment
		else:
			raise TypeError("Argument 'practice_blocks_per_experiment' must be a positive integer.")


	@property
	def trials_per_block(self):
		return self.__trials_per_block

	@trials_per_block.setter
	def trials_per_block(self, trials_per_block):
		if type(trials_per_block) is int and trials_per_block >= 0:
			self.__trials_per_block = trials_per_block
		else:
			raise TypeError("Argument 'trials_per_block' must be a positive integer.")


	@property
	def total_trials(self):
		return self.__total_trials

	@total_trials.setter
	def total_trials(self, total_trials):
		if type(total_trials) is int and total_trials >= 0:
			self.__total_trials = total_trials
		else:
			raise TypeError("Argument 'total_trials' must be a positive integer.")


	@property
	def trials_per_practice_block(self):
		return self.__trials_per_practice_block

	@trials_per_practice_block.setter
	def trials_per_practice_block(self, trials_per_practice_block):
		if type(trials_per_practice_block) is int and trials_per_practice_block >= 0:
			self.__trials_per_practice_block = trials_per_practice_block
		else:
			raise TypeError("Argument 'trials_per_practice_block' must be a positive integer.")


	@property
	def trials(self):
		return self.__trials


	@trials.setter
	def trials(self, trials):
		if type(trials) is int and trials >= 0:
			self.__trials = trials
		else:
			raise TypeError("Argument 'trials' must be a positive integer.")

	@property
	def blocks(self):
		return self.__blocks


	@blocks.setter
	def blocks(self, blocks):
		if type(blocks) is int and blocks >= 0:
			self.__blocks = blocks
		else:
			raise TypeError("Argument 'blocks' must be a positive integer.")


	@property
	def diagonal_px(self):
		return self.__diagonal_px

	@diagonal_px.setter
	def diagonal_px(self, diagonal_px):
		if type(diagonal_px) in (int, float)  > 0:
			self.__diagonal_px = diagonal_px
		else:
			raise TypeError("Argument 'diagonal_px' must be a positive number.")

	@property
	def screen_c(self):
		return self.__screen_c

	@screen_c.setter
	def screen_c(self, screen_c):
		if type(screen_c) is tuple and len(screen_c) == 2 and all(type(val) is int > 0 for val in screen_c):
			self.__screen_c = screen_c
		else:
			raise TypeError("Argument 'screen_c' must be a tuple of two positive integers.")

	@property
	def screen_x(self):
		return self.__screen_x

	@screen_x.setter
	def screen_x(self, screen_x):
		if type(screen_x) in (int, float) > 0:
			self.__screen_x = screen_x
		else:
			raise TypeError("Argument 'screen_x' must be a positive number.")

	@property
	def screen_y(self):
		return self.__screen_y

	@screen_y.setter
	def screen_y(self, screen_y):
		if type(screen_y) in (int, float) > 0:
			self.__screen_y = screen_y
		else:
			raise TypeError("Argument 'screen_y' must be a positive number.")

	@property
	def screen_x_y(self):
		return self.__screen_x_y

	@screen_x_y.setter
	def screen_x_y(self, screen_x_y):
		if type(screen_x_y) is tuple and len(screen_x_y) == 2 and all(type(val) is int > 0 for val in screen_x_y):
			self.__screen_x_y = screen_x_y
		else:
			raise TypeError("Argument 'screen_x_y' must be a tuple of two positive integers.")

	@property
	def ppi(self):
		return self.__ppi

	@ppi.setter
	def ppi(self, ppi):
		if type(ppi) is int > 0:
			self.__ppi = ppi
		else:
			raise TypeError("Argument 'ppi' must be a positive integer.")


	@property
	def pixels_per_degree(self):
		return self.__pixels_per_degree

	@pixels_per_degree.setter
	def pixels_per_degree(self, pixels_per_degree):
		if type(pixels_per_degree) is int > 0:
			self.__pixels_per_degree = pixels_per_degree
		else:
			raise TypeError("Argument 'pixels_per_degree' must be a positive integer.")


	@property
	def ppd(self):
		return self.__ppd

	@ppd.setter
	def ppd(self, ppd):
		if type(ppd) is int > 0:
			self.__ppd = ppd
		else:
			raise TypeError("Argument 'ppd' must be a positive integer.")


	@property
	def saccadic_velocity_threshold(self):
		return self.__saccadic_velocity_threshold

	@saccadic_velocity_threshold.setter
	def saccadic_velocity_threshold(self, value):
		if type(value) is int > 0:
			self.__saccadic_velocity_threshold = value
		else:
			raise TypeError("Argument 'value' must be a positive integer.")


	@property
	def saccadic_acceleration_threshold(self):
		return self.__saccadic_acceleration_threshold

	@saccadic_acceleration_threshold.setter
	def saccadic_acceleration_threshold(self, value):
		if type(value) is int > 0:
			self.__saccadic_acceleration_threshold = value
		else:
			raise TypeError("Argument 'value' must be a positive integer.")


	@property
	def saccadic_motion_threshold(self):
		return self.__saccadic_motion_threshold

	@saccadic_motion_threshold.setter
	def saccadic_motion_threshold(self, value):
		if type(value) is int > 0:
			self.__saccadic_motion_threshold = value
		else:
			raise TypeError("Argument 'value' must be a positive integer.")


	@property
	def default_font_size(self):
		return self.__default_font_size

	@default_font_size.setter
	def default_font_size(self, font_size):
		if type(font_size) is str:
			self.__default_font_size = pt_to_px(font_size)
		elif type(font_size) is int:
			self.__default_font_size = font_size
		else:
			raise TypeError("Argument 'font_size' must be either an integer (px) or a point-value string (ie. '8pt').")


	#todo: look into whether these next 4 params should be included by default (especially without a drawing API)

	@property
	def fixation_size(self):
		return self.__fixation_size

	@fixation_size.setter
	def fixation_size(self, fixation_size):
		if type(fixation_size) is int > 0:
			self.__fixation_size = fixation_size
		else:
			raise TypeError("Argument 'fixation_size' must be a positive integer.")


	@property
	def box_size(self):
		return self.__box_size

	@box_size.setter
	def box_size(self, box_size):
		if type(box_size) is int > 0:
			self.__box_size = box_size
		else:
			raise TypeError("Argument 'box_size ' must be a positive integer.")


	@property
	def cue_size(self):
		return self.__cue_size

	@cue_size.setter
	def cue_size(self, cue_size):
		if type(cue_size) is int > 0:
			self.__cue_size = cue_size
		else:
			raise TypeError("Argument 'cue_size ' must be a positive integer.")


	@property
	def cue_back_size(self):
		return self.__cue_back_size

	@cue_back_size.setter
	def cue_back_size(self, cue_back_size):
		if type(cue_back_size) is int > 0:
			self.__cue_back_size = cue_back_size
		else:
			raise TypeError("Argument 'cue_back_size ' must be a positive integer.")


	@property
	def verbosity(self):
		return self.__verbosity

	# todo: make use of this or delete it
	@verbosity.setter
	def verbosity(self, verbosity):
		if type(verbosity) is int in range(1, 10):
			self.__verbosity = verbosity
		else:
			raise TypeError("Argument 'verbosity' must be an integer between 1 and 10.")