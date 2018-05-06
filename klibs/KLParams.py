# -*- coding: utf-8 -*-
__author__ = 'jono'
"""
TODO: set this up such that all vars are in a dict with a key representing whether the var should
be included in the user's template of the params file, then autogenerate the template doc. AND the
runtime params from that dict (this was Jon's idea, is it worth the effort / likely API breaking?)
"""

import sys
import logging, time, tempfile
from random import seed
from datetime import datetime
from os import makedirs, environ
from os.path import exists, join, expanduser
from pkg_resources import resource_filename, resource_string

from klibs.KLConstants import (TAB, DATETIME_STAMP, DB_EXT, SCHEMA_EXT, USER_QUERIES_EXT, LOG_EXT,
	FACTORS_EXT, PARAMS_EXT, MESSSAGING_EXT, BACK_EXT)

klibs_commit = str(resource_string('klibs', 'resources/current_commit.txt').decode('utf-8'))

# Runtime Variables
participant_id = None
p_id = None # alias for participant_id
trial_id = None
trial_number = 0
block_number = 0
recycle_count = 0 # reset on a per-block basis

# State variables
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
table_defaults = {} # default column values for db tables when using EntryTemplate
run_practice_blocks = True # (not implemented in klibs itself)

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
default_font_name = 'Frutiger' #TODO: find a new default font

# Display defaults (user-defined)
view_distance = 57  # in centimeters, 57m = in 1deg of visual angle per horizontal cm of screen
additional_displays = [] # (not implemented)
screen_origin = (0,0)  # (not implemented) always (0,0) unless multiple displays in use
blit_flip_x = False
ignore_points_at = [] # For ignoring problematic pixel coordinates when using DrawResponse

# Display defaults (defined automatically on launch in KLGrapics.display_init())
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
default_participant_fields = [["userhash", "participant"], "sex", "age", "handedness"]
default_participant_fields_sf = [["userhash", "participant"], "random_seed", "sex", "age", "handedness"]
default_demo_participant_str = TAB.join(["demo_user", "-", "-", "-"])

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

# default strings for communicating with participant (is this still useful?)
no_answer_string = None
invalid_answer_string = None

# Default Paths & Filenames (filled in by setup() and init_project() below)
project_name = None
asset_dir = None
config_dir = None
data_dir = None
incomplete_data_dir = None
edf_dir = None
incomplete_edf_dir = None
image_dir = None
code_dir = None
local_dir = None
resources_dir = None
versions_dir = None

database_filename = None
database_path = None
database_local_path = None
database_backup_path = None
events_filename = None
events_file_path = None
ind_vars_filename = None
ind_vars_file_path = None
ind_vars_file_local_path = None
log_filename = None
log_file_path = None
params_file_path = None
params_local_file_path = None
schema_filename = None
schema_file_path = None
user_queries_filename = None
user_queries_file_path = None
logo_file_path = None

anonymous_username = None
random_seed = None
key_maps = None


def init_project():
	from klibs.KLKeyMap import KeyMap
	global key_maps # ? (should global keymaps be a thing?)

	global data_dir
	global incomplete_data_dir
	global edf_dir
	global incomplete_edf_dir
	global local_dir
	global logs_dir
	global versions_dir
	global font_dirs
	
	global database_filename
	global database_path
	global database_local_path
	global database_backup_path
	global events_filename
	global events_file_path
	global ind_vars_filename
	global ind_vars_file_path
	global ind_vars_file_local_path
	global log_filename
	global log_file_path
	global params_filename
	global params_file_path
	global params_local_file_path
	global schema_filename
	global schema_file_path
	global user_queries_filename
	global user_queries_file_path

	global initialized


	key_maps = {"*": KeyMap("*", [], [], [])} # ?
	key_maps["*"].any_key = True # ?

	# file names
	database_filename = str(project_name) + DB_EXT
	schema_filename = str(project_name) + SCHEMA_EXT
	user_queries_filename = str(project_name) + USER_QUERIES_EXT
	log_filename = str(project_name) + LOG_EXT
	ind_vars_filename = str(project_name) + FACTORS_EXT
	params_filename = str(project_name) + PARAMS_EXT
	events_filename = str(project_name) + MESSSAGING_EXT

	# project paths
	data_dir = join(asset_dir, "Data")
	local_dir = join(asset_dir, "Local")
	edf_dir = join(asset_dir, "EDF")  # todo: write edf management
	incomplete_edf_dir = join(data_dir, "incomplete")
	log_file_path = join(asset_dir, log_filename)
	schema_file_path = join(config_dir, schema_filename)
	user_queries_file_path = join(config_dir, user_queries_filename)
	database_path = join(asset_dir, database_filename)
	database_local_path = join(tempfile.gettempdir(), database_filename)
	database_backup_path = database_path + BACK_EXT
	incomplete_data_dir = join(data_dir, "incomplete")
	ind_vars_file_path = join(config_dir, ind_vars_filename)
	ind_vars_file_local_path = join(local_dir, ind_vars_filename)
	params_file_path = join(config_dir, params_filename)
	params_local_file_path = join(local_dir, params_filename)
	events_file_path = join(config_dir, events_filename)
	versions_dir = join(asset_dir, ".versions")
	logs_dir = join(local_dir, "logs")

	# Font folder info
	font_dirs = [exp_font_dir, resource_filename('klibs', 'resources/font')]

	project_structure = [
		local_dir, logs_dir, versions_dir, edf_dir, data_dir,
		incomplete_data_dir, incomplete_edf_dir
	]
	for path in project_structure:
		if not exists(path):
			try:
				makedirs(path)
			except OSError:
				pass

	initialized = True
	return True

def setup(project_name_str, seed_value=None):
	global project_name
	global random_seed
	global anonymous_username
	global asset_dir
	global exp_font_dir
	global image_dir
	global code_dir
	global config_dir
	global resources_dir
	global logo_file_path

	timestamp = datetime.fromtimestamp(time.time()).strftime(DATETIME_STAMP)
	anonymous_username = "demo_user_{0}".format(timestamp)
	random_seed = seed_value
	
	seed(random_seed)
	project_name = project_name_str
	asset_dir = "ExpAssets"
	resources_dir = join(asset_dir, "Resources")
	exp_font_dir = join(resources_dir, "font")
	image_dir = join(resources_dir, "image")
	code_dir = join(resources_dir, "code")
	config_dir = join(asset_dir, "Config")
	logo_file_path = resource_filename('klibs', 'resources/splash.png')

	for path in [exp_font_dir, image_dir]:
		if not exists(path):
			try:
				makedirs(path)
			except OSError:
				pass

	return init_project()