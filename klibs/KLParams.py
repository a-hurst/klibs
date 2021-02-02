# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'
"""
TODO: Try making the Params "P" an object? Could set attributes dynamically
but also allow for sanity checks and renaming variables w/o breaking backwards
compatibility. Would also help with documentation.
"""

from os.path import join


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

# State Variables
initialized = False
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
#dm_suppress_debug_pane = False # (debug pane was never implemented but maybe a good idea)
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
edf_dir = join(asset_dir, "EDF")
local_dir = join(asset_dir, "Local")
resources_dir = join(asset_dir, "Resources")
versions_dir = join(asset_dir, ".versions")

# Project Subdirectories
incomplete_data_dir = join(data_dir, "incomplete")
incomplete_edf_dir = join(edf_dir, "incomplete")
logs_dir = join(local_dir, "logs")
audio_dir = join(resources_dir, "audio")
code_dir = join(resources_dir, "code")
exp_font_dir = join(resources_dir, "font")
image_dir = join(resources_dir, "image")
version_dir = None  # Dynamically set at runtime
font_dirs = None  # Dynamically set at runtime

# Project Filepaths (dynamically set at runtime)
database_path = None
database_local_path = None
database_backup_path = None
params_file_path = None
params_local_file_path = None
ind_vars_file_path = None
ind_vars_file_local_path = None
schema_file_path = None
user_queries_file_path = None
log_file_path = None
events_file_path = None
logo_file_path = None



def initialize_paths(project_name_str):

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
	global events_file_path

	project_name = project_name_str

	# Initialize project file names
	database_filename = "{0}.db".format(project_name)
	database_backup_filename = "{0}.db.backup".format(project_name)
	params_filename = "{0}_params.py".format(project_name)
	ind_vars_filename = "{0}_independent_variables.py".format(project_name)
	schema_filename = "{0}_schema.sql".format(project_name)
	user_queries_filename = "{0}_user_queries.json".format(project_name)
	log_filename = "{0}_log.txt".format(project_name)
	events_filename = "{0}_messaging.csv".format(project_name)

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
	events_file_path = join(config_dir, events_filename)


def initialize_runtime(project_name_str, seed_value=None):

	import tempfile
	from random import seed
	from pkg_resources import resource_filename, resource_string

	global random_seed
	global database_local_path
	global klibs_commit
	global font_dirs
	global logo_file_path
	global initialized

	# Initialize Python's random number generator with a reproducible seed
	random_seed = seed_value
	seed(random_seed)

	# Initialize project paths
	initialize_paths(project_name_str)
	database_local_filename = "{0}_{1}.db".format(project_name_str, random_seed)
	database_local_path = join(tempfile.gettempdir(), database_local_filename)

	# Load extra resources from package
	klibs_commit = str(resource_string('klibs', 'resources/current_commit.txt').decode('utf-8'))
	font_dirs = [exp_font_dir, resource_filename('klibs', 'resources/font')]
	logo_file_path = resource_filename('klibs', 'resources/splash.png')
	
	initialized = True
