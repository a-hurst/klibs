# -*- coding: utf-8 -*-
"""
TODO: set this up such that all vars are in a dict with a key representing whether the var should be included in the
user's template of the params file, then autogenerate the template doc. AND the runtime params from that dict
"""

author = 'jono'
import logging, time
from random import seed
from datetime import datetime
from os import makedirs
from os.path import exists, join

from klibs.KLConstants import *

klibs_commit = None  # populated at runtime

#  project structure; default paths & filenames
klibs_dir = klibs_dir = "/usr/local/lib/klibs"
global project_name
global asset_dir
global resources_dir
global image_dir
global config_dir
global database_filename
global log_filename
global log_file_path
global database_path
global database_backup_path
global edf_dir
global incomplete_edf_dir
global schema_file_path
global schema_filename
global user_queries_file_path
global user_queries_filename
global data_dir
global incomplete_data_path
global factors_filename
global factors_file_path
global params_file_path
global events_file_path
global versions_dir
global initialized
global random_seed
global anonymous_username
global logo_file_path
global key_maps
global local_dir
code_dir = "ExpAssets/Resources/code"  # hard-coded because it's required *before* the Experiment class is instantiated

#########################################
# Logging Defaults
#########################################
log_to_file = True
level = logging.INFO


exp = None
exp_font_dir = "ExpAssets/Resources/font"
sys_font_dir = "/Library/Fonts"
user_font_dir = "~/Library/Fonts"
klibs_font_dir = join(klibs_dir, "font")
font_dirs = [exp_font_dir, sys_font_dir, user_font_dir, klibs_font_dir]


# default strings for communicating with participant
no_answer_string = None
invalid_answer_string = None

initialized = False
audio_initialized = False

skeleton_mode = False
calibrate_with_audio = True
calibrate_targets = 9

participant_id = None
database = None


id_field_name = "participant_id"
collect_demographics = True
demographics_collected = False

# eye tracking
eye_tracking = False
eye_tracker_available = False
exp_factors = None
manual_eyelink_setup = False
manual_eyelink_recording = False

# labjack
labjack_available = False
labjacking = False

instructions = False  # todo: instructions file
paused = False
testing = False
default_alert_duration = 1

default_fill_color = (45, 45, 45, 255)
default_drift_correct_fill_color = (125, 125, 125, 255)
default_color = (255, 255, 255, 255)
default_alert_color = (236, 88, 64, 255)
default_response_color = default_color
default_input_color = default_color
default_font_size = "28pt"
default_font_name = 'Frutiger'
default_timeout_message = "Too slow!"

monitor_x = None
monitor_y = None
diagonal_px = None
ppi = 0  # pixels-per-inch, varies between CRT & LCD screens
pixels_per_degree = None  # pixels-per-degree, ie. degree of visual angle
ppd = None  # pixels-per-degree, ie. degree of visual angle
screen_c = (None, None)
screen_ratio = None
screen_diagonal_in = None
screen_x = None
screen_y = None
screen_x_y = None
screen_degrees_x = None
screen_degrees_y = None
view_distance = 104  # in centimeters, 57m = in 1deg of visual angle per horizontal cm of screen
display_initialized = False

saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15

fixation_size = 1  # deg of visual angle
box_size = 1  # deg of visual angle
cue_size = 1  # deg of visual angle
cue_back_size = 1  # deg of visual angle
verbosity = -1  # 0-10, with 0 being no errors and 10 being all errors todo: actually implement this hahaha, so fail

trial_id = None
trial_number = 0
block_number = 0
trials_per_block = 0
blocks_per_experiment = 0
between_subject_conditions = None
multi_session_project = False

run_practice_blocks = True
show_practice_messages = True
practicing = False
recycle_count = 0  # reset on a per-block basis
manual_trial_generation = False
pre_render_block_messages = False

# database
data_columns = None
default_participant_fields = [["userhash", "participant"], "sex", "age", "handedness"]
default_participant_fields_sf = [["userhash", "participant"], "random_seed", "sex", "age", "handedness"]
default_demo_participant_str = TAB.join(["demo_user", "-", "-", "-"])
data_column_format = DB_COL_TITLE


# development mode & associated switches
debug_level = 3
development_mode = False  # when True, skips collect_demographics & prints various details to screen
dm_trial_show_mouse = True
dm_suppress_debug_pane = False
dm_auto_threshold = True
dm_print_log = True
dm_print_events = True
verbose_mode = False

def init_project():
	from klibs.KLKeyMap import KeyMap
	global key_maps
	# todo: write checks in these setters to not overwrite paths that don't include asset_paths (ie. arbitrarily set)
	global project_name
	global asset_dir
	global config_dir
	global database_filename
	global log_filename
	global log_file_path
	global database_path
	global database_backup_path
	global edf_dir
	global incomplete_edf_dir
	global schema_file_path
	global schema_file_path_legacy
	global user_queries_file_path
	global user_queries_filename
	global schema_filename
	global data_dir
	global incomplete_data_path
	global factors_filename
	global factors_file_path
	global config_file_path_legacy
	global params_file_path
	global events_file_path
	global versions_dir
	global local_dir
	global logs_dir
	global initialized

	key_maps = {"*": KeyMap("*", [], [], []),
				"drift_correct": KeyMap("drift_correct", ["spacebar"], [sdl2.SDLK_SPACE], ["spacebar"]),
				"eyelink": KeyMap("eyelink",
								   ["a", "c", "v", "o", "return", "spacebar", "up", "down", "left", "right"],
								   [sdl2.SDLK_a, sdl2.SDLK_c, sdl2.SDLK_v, sdl2.SDLK_o, sdl2.SDLK_RETURN,
									sdl2.SDLK_SPACE, sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT,
									sdl2.SDLK_RIGHT],
								   ["a", "c", "v", "o", "return", "spacebar", "up", "down", "left", "right"])}
	key_maps["*"].any_key = True



	# file names
	database_filename = str(project_name) + DB_EXT
	schema_filename = str(project_name) + SCHEMA_EXT
	user_queries_filename = str(project_name) + USER_QUERIES_EXT
	log_filename = str(project_name) + LOG_EXT
	factors_filename = str(project_name) + FACTORS_EXT
	params_filename = str(project_name) + PARAMS_EXT
	events_filename = str(project_name) + MESSSAGING_EXT

	# project paths
	data_dir = join(asset_dir, "Data")
	edf_dir = join(asset_dir, "EDF")  # todo: write edf management
	incomplete_edf_dir = join(data_dir, "incomplete")
	log_file_path = join(asset_dir, log_filename)
	schema_file_path = join(config_dir, schema_filename)
	schema_file_path_legacy = join(asset_dir, schema_filename)
	user_queries_file_path = join(config_dir, user_queries_filename)
	database_path = join(asset_dir, database_filename)
	database_backup_path = database_path + BACK_EXT
	incomplete_data_path = join(data_dir, "incomplete")
	factors_file_path = join(config_dir, factors_filename)
	config_file_path_legacy = join(asset_dir, factors_filename)
	params_file_path = join(config_dir, params_filename)
	events_file_path = join(config_dir, events_filename)
	versions_dir = join(asset_dir, ".versions")
	local_dir = join(asset_dir, "Local")
	logs_dir = join(local_dir, "logs")

	for path in [local_dir, logs_dir, versions_dir, edf_dir, data_dir, incomplete_data_path, incomplete_edf_dir]:
		if not exists(path):
			try:
				makedirs(path)
			except OSError:
				pass

	initialized = True
	return True

def setup(project_name_str):
	global project_name
	global asset_dir
	global random_seed
	global anonymous_username
	global exp_font_dir
	global image_dir
	global config_dir
	global resources_dir
	global logo_file_path


	anonymous_username = "demo_user_{0}".format(datetime.fromtimestamp(time.time()).strftime(DATETIME_STAMP))


	#  seed the experiment with either a passed random_seed or else the current unix time
	if not 'random_seed' in globals():  # if passed from CLI will be set by now
		random_seed = time.time()
	seed(random_seed)
	project_name = project_name_str
	asset_dir = "ExpAssets"
	resources_dir = join(asset_dir, "Resources")
	exp_font_dir = join(resources_dir, "font")
	image_dir = join(resources_dir, "image")
	config_dir = join(asset_dir, "Config")
	logo_file_path = join(klibs_dir, "splash.png")

	for path in [exp_font_dir, image_dir]:
		if not exists(path):
			try:
				makedirs(path)
			except OSError:
				pass

	return init_project()