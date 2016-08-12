# -*- coding: utf-8 -*-
author = 'jono'

from random import seed

# from klibs.KLUtilities import *
# from klibs.KLTimeKeeper import TimeKeeper
import time
from datetime import datetime
from klibs.KLConstants import *
import os
import multiprocessing as mp

klibs_commit = 'f2125deb865bfaf2019d175f9964ad88b931787e'

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
global schema_file_path
global schema_file_path_legacy
global schema_filename
global data_path
global incomplete_data_path
global config_filename
global config_file_path
global config_file_path_legacy
global params_file_path
global events_file_path
global versions_dir
global initialized
global random_seed
global anonymous_username

exp = None
exp_font_dir = "ExpAssets/Resources/font"
sys_font_dir = "/Library/Fonts"
user_font_dir = "~/Library/Fonts"
klibs_font_dir = os.path.join(klibs_dir, "font")
font_dirs = [exp_font_dir, sys_font_dir, user_font_dir, klibs_font_dir]


demographic_questions = [
	['sex', "What is your sex? \nAnswer with:  (m)ale,(f)emale", ('m', 'M', 'f', 'F'), 'str', 'f'],
	['handedness', "Are right-handed, left-handed or ambidextrous? \nAnswer with (r)ight, (l)eft or (a)mbidextrous.",
	 ('r', 'R', 'l', 'L', 'a', 'A'), 'str', 'r'],
	['age', 'What is  your age?', None, 'int', -1]
]

initialized = False
audio_initialized = False

skeleton_mode = False
calibrate_with_audio = True
calibrate_targets = 9

participant_id = None
database = None

key_maps = dict()  # todo: create a class, KeyMapper, to manage key maps
id_field_name = "participant_id"
collect_demographics = True
demographics_collected = False

# eye tracking
eye_tracking = False
eye_tracker_available = False
exp_factors = None

# labjack
labjack_available = False  # todo: put this back to true you fucking monkey
labjacking = False

instructions = False  # todo: instructions file
paused = False
testing = False
default_alert_duration = 1

#  todo: add a lot more default colors, a default font, etc.
default_fill_color = (45, 45, 45, 255)
default_color = (255, 255, 255, 255)
default_response_color = default_color
default_input_color = default_color
default_font_size = 28
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
view_distance = 57  # in centimeters, 57m = in 1deg of visual angle per horizontal cm of screen
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
dm_suppress_debug_pane = False
dm_auto_threshold = True
dm_print_log = True
dm_print_events = True
verbose_mode = False
process_queue = mp.Queue()
updated_events = []
process_queue_data = {}


def init_project():
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
	global schema_file_path
	global schema_file_path_legacy
	global schema_filename
	global data_path
	global incomplete_data_path
	global config_filename
	global config_file_path
	global config_file_path_legacy
	global params_file_path
	global events_file_path
	global versions_dir
	global initialized

	# file names
	database_filename = str(project_name) + DB_EXT
	schema_filename = str(project_name) + SCHEMA_EXT
	log_filename = str(project_name) + LOG_EXT
	config_filename = str(project_name) + CONFIG_EXT
	params_filename = str(project_name) + PARAMS_EXT
	events_filename = str(project_name) + MESSSAGING_EXT

	# project paths
	edf_dir = os.path.join(asset_dir, "EDF")  # todo: write edf management
	log_file_path = os.path.join(asset_dir, log_filename)
	schema_file_path = os.path.join(config_dir, schema_filename)
	schema_file_path_legacy = os.path.join(asset_dir, schema_filename)
	database_path = os.path.join(asset_dir, database_filename)
	database_backup_path = database_path + BACK_EXT
	data_path = os.path.join(asset_dir, "Data")
	incomplete_data_path = os.path.join(data_path, "incomplete")
	config_file_path = os.path.join(config_dir, config_filename)
	config_file_path_legacy = os.path.join(asset_dir, config_filename)
	params_file_path = os.path.join(config_dir, params_filename)
	events_file_path = os.path.join(config_dir, events_filename)
	versions_dir = os.path.join(asset_dir, ".versions")

	initialized = True
	return True

def setup(project_name_str, previous_random_seed):
	global project_name
	global asset_dir
	global random_seed
	global anonymous_username
	global exp_font_dir
	global image_dir
	global config_dir
	global resources_dir

	anonymous_username = "demo_user_{0}".format(datetime.fromtimestamp(time.time()).strftime(DATETIME_STAMP))


	#  seed the experiment with either a passed random_seed or else the current unix time
	random_seed = previous_random_seed if previous_random_seed else time.time()
	seed(random_seed)
	project_name = project_name_str
	asset_dir = "ExpAssets"
	resources_dir = os.path.join(asset_dir, "Resources")
	exp_font_dir = os.path.join(resources_dir, "font")
	image_dir = os.path.join(resources_dir, "image")
	config_dir = os.path.join(asset_dir, "Config")
	return init_project()