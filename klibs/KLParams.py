# -*- coding: utf-8 -*-
"""Contains the user-facing (and internal) runtime variables for the KLibs environment.

The purpose of KLParams is to make useful experiment configuration and runtime
variables easily accessible through a single module. Things like the current trial
number, block number, screen resolution (in pixels), asset folder paths, and custom
paramaters defined in a project's ``_params.py`` file are all accessible through
KLParams.

For convenience, this module can be imported through the main klibs namespace with
the alias ``P`` (e.g. ``from klibs import P``). 

"""

__author__ = 'Jonathan Mulle & Austin Hurst'

import logging
from os.path import join

# TODO: Try making the Params "P" an object or AttributeDict? Could set attributes
# dynamically but also allow for sanity checks and renaming variables w/o breaking
# backwards compatibility. Would also help with documentation.


# Runtime Variables
participant_id = None
p_id = None # alias for participant_id
trial_id = None
trial_number = 0
block_number = 0
session_number = 1
recycle_count = 0 # reset on a per-block basis

# Runtime Attributes
project_name = None
random_seed = None
klibs_commit = None

# State variables
display_initialized = False
demographics_collected = False
in_trial = False
paused = False # (not implemented)
practicing = False # True if during practice block
condition = None

# Experiment Attributes
collect_demographics = True
manual_demographics_collection = False
manual_trial_generation = False
multi_session_project = False
multi_user = False # creates temp copy of db that gets merged into master at end
trials_per_block = 0
blocks_per_experiment = 0
conditions = []
default_condition = None
table_defaults = {} # default column values for db tables when using EntryTemplate
run_practice_blocks = True # (not implemented in klibs itself)
color_output = False # whether cso() outputs colorized text or not

# Eye Tracking Settings
eye_tracking = False
eye_tracker_available = False
manual_eyelink_setup = False
manual_eyelink_recording = False
show_gaze_dot = False # overridden by dm_show_gaze_dot if in development mode
saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000 # (change to be more accurate?)
saccadic_motion_threshold = 0.15
#calibrate_with_audio = True (not implemented)
#calibrate_targets = 9 (not implemented)

# Labjack Settings
labjack_available = False
labjacking = False

# Slack Messaging Settings
slack_messaging = False

# Aesthetic Defaults
default_fill_color = (45, 45, 45, 255)
default_color = (255, 255, 255, 255)
default_alert_color = (236, 88, 64, 255)
default_font_size = 28
default_font_unit = 'pt'
default_font_name = 'Hind-Medium'

# Display defaults (user-defined)
view_distance = 57  # in centimeters, 57m = in 1deg of visual angle per horizontal cm of screen
additional_displays = [] # (not implemented)
screen_origin = (0,0)  # (not implemented) always (0,0) unless multiple displays in use
blit_flip_x = False
ignore_points_at = [] # For ignoring problematic pixel coordinates when using DrawResponse

# Display defaults (defined automatically on launch in KLGraphics.display_init())
ppi = 0  # pixels-per-inch
pixels_per_degree = None  # pixels-per-degree, ie. degree of visual angle
ppd = None  # alias of pixels_per_degree
screen_diagonal_in = None # defined by screensize argument to 'klibs run'
screen_diagonal_px = None
screen_x = None
screen_y = None
screen_x_y = None
screen_c = (None, None)
screen_degrees_x = None
screen_degrees_y = None
monitor_height = None
monitor_width = None
refresh_rate = None # Number of times the display refreshes per second (in Hz)
refresh_time = None # Expected time between display refreshes (in ms)

# Database Export Settings
id_field_name = "participant_id"
primary_table = "trials"
unique_identifier = "userhash"
default_participant_fields = [] # for legacy use
default_participant_fields_sf = [] # for legacy use
exclude_data_cols = ["created"]
append_info_cols = []
datafile_ext = ".txt"

# Development mode & associated switches
development_mode = False # when True, skips collect_demographics & prints various details to screen
dm_trial_show_mouse = True
dm_auto_threshold = True # for audio responses
dm_ignore_local_overrides = False
dm_show_gaze_dot = True
#debug_level = 3 # (not implemented)
#dm_print_log = True # (not implemented)
#dm_print_events = True # (not implemented)

# Verbose mode & logging params (not implemented)
verbose_mode = False
verbosity = -1
#log_to_file = True
#log_level = logging.INFO

# Project Directories
asset_dir = "ExpAssets"
config_dir = join(asset_dir, "Config")
data_dir = join(asset_dir, "Data")
edf_dir = join(asset_dir, "EDF")  # TODO: Improve EDF file management
local_dir = join(asset_dir, "Local")
resources_dir = join(asset_dir, "Resources")
versions_dir = join(asset_dir, ".versions")

# Project Subdirectories
incomplete_data_dir = join(data_dir, "incomplete")
incomplete_edf_dir = join(edf_dir, "incomplete")
audio_dir = join(resources_dir, "audio")
code_dir = join(resources_dir, "code")
image_dir = join(resources_dir, "image")
logs_dir = join(local_dir, "logs")
exp_font_dir = join(resources_dir, "font")
version_dir = None  # Dynamically set at runtime
font_dirs = None  # Dynamically set at runtime

# Project Filepaths (dynamically set at runtime)
database_path = None
database_backup_path = None
database_local_path = None
params_file_path = None
params_local_file_path = None
ind_vars_file_path = None
ind_vars_file_local_path = None
schema_file_path = None
user_queries_file_path = None
log_file_path = None
logo_file_path = None


def initialize_paths(exp_name):
	"""Initializes the experiment's file paths within the Params module.

	Since the names of various files required by a KLibs experiment are based on
	the experiment name, they need to be dynamically determined at runtime. This
	internal function initializes the full paths to those files in the Params
	module based on the given experient name.

	Args:
		exp_name (str): The name of the Experiment class in the project's
			``experiment.py`` file.

	"""
	global project_name
	
	global database_path
	global database_backup_path
	global params_file_path
	global params_local_file_path
	global ind_vars_file_path
	global ind_vars_file_local_path
	global schema_file_path
	global user_queries_file_path
	global log_file_path

	# Set experiment name globally in module
	project_name = exp_name

	# Initialize project file names
	database_filename = "{0}.db".format(project_name)
	database_backup_filename = "{0}.db.backup".format(project_name)
	params_filename = "{0}_params.py".format(project_name)
	ind_vars_filename = "{0}_independent_variables.py".format(project_name)
	schema_filename = "{0}_schema.sql".format(project_name)
	user_queries_filename = "{0}_user_queries.json".format(project_name)
	log_filename = "{0}_log.txt".format(project_name)

	# Initialize project file paths
	database_path = join(asset_dir, database_filename)
	database_backup_path = join(asset_dir, database_backup_filename)
	params_file_path = join(config_dir, params_filename)
	params_local_file_path = join(local_dir, params_filename)
	ind_vars_file_path = join(config_dir, ind_vars_filename)
	ind_vars_file_local_path = join(local_dir, ind_vars_filename)
	schema_file_path = join(config_dir, schema_filename)
	user_queries_file_path = join(config_dir, user_queries_filename)
	log_file_path = join(asset_dir, log_filename)


def initialize_runtime(exp_name, randseed):
	"""Initializes all runtime paths and attributes within the Params module.

	In addition to the basic initialization done by :func:`initialize_paths`,
	this function sets the runtime's random seed and loads additional internal
	resources only required when actually running the experiment.
	
	Since the loading of package resources can be noticably slow, the
	separation of this function from `initialize_paths` allows KLibs to avoid
	unnecessary lag when calling things like ``klibs export`` or ``klibs -h``.

	Args:
		exp_name (str): The name of the Experiment class in the project's
			``experiment.py`` file.
		randseed (int): The random seed to use for the experiment runtime.

	"""
	import random
	import tempfile
	from pkg_resources import resource_filename, resource_string

	global random_seed
	global klibs_commit
	global database_local_path
	global logo_file_path
	global font_dirs

	# Initialize Python's random number generator with a reproducible seed
	random_seed = randseed
	random.seed(random_seed)

	# Initialize project paths
	initialize_paths(exp_name)
	database_local_filename = "{0}_{1}.db".format(project_name, random_seed)
	database_local_path = join(tempfile.gettempdir(), database_local_filename)

	# Load extra resources from KLibs package
	klibs_commit_raw = resource_string('klibs', 'resources/current_commit.txt')
	klibs_commit = str(klibs_commit_raw.decode('utf-8'))
	logo_file_path = resource_filename('klibs', 'resources/splash.png')
	font_dirs = [exp_font_dir, resource_filename('klibs', 'resources/font')]
	