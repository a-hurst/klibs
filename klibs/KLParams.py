author = 'jono'

from KLConstants import *
from KLUtilities import *
import os

#  project structure; default paths & filenames
global project_name
global asset_path
global database_filename
global log_filename
global log_file_path
global database_path
global database_backup_path
global edf_path
global schema_file_path
global schema_filename
global data_path
global incomplete_data_path
global config_filename
global config_file_path
global initialized

initialized = False
audio_initialized = False

skeleton_mode = False
debug_level = 3

calibrate_with_audio = True
calibrate_targets = 9

participant_id = None
database = None

key_maps = dict()  # todo: create a class, KeyMapper, to manage key maps
id_field_name = "participant_id"
random_seed = None
collect_demographics = True
eye_tracking = False
eye_tracker_available = False
exp_factors = None
instructions = False  # todo: instructions file
practicing = False
paused = False
testing = False
default_alert_duration = 1

#  todo: add a lot more default colors, a default font, etc.
default_fill_color = [45, 45, 45, 255]
default_response_color = [41,28, 70, 255]
default_input_color = [45, 25, 28, 255]
default_timeout_message = "Too slow!"
monitor_x = None
monitor_y = None
diagonal_px = None
ppi = None  # pixels-per-inch, varies between CRT & LCD screens
dpi = ppi  # todo: this is broken and totally wrong
pixels_per_degree = None  # pixels-per-degree, ie. degree of visual angle
ppd = None  # pixels-per-degree, ie. degree of visual angle
screen_c = (None, None)
screen_ratio = None
screen_x = None
screen_y = None
screen_x_y = None
screen_degrees_x = None
screen_degrees_y = None
view_unit = "in"  # inch, not the preposition
view_distance = 67  # in centimeters, 56cm = in 1deg of visual angle per horizontal cm of screen

saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15
default_font_size = 28

fixation_size = 1  # deg of visual angle
box_size = 1  # deg of visual angle
cue_size = 1  # deg of visual angle
cue_back_size = 1  # deg of visual angle
verbosity = -1  # 0-10, with 0 being no errors and 10 being all errors todo: actually implement this hahaha so fail

trial_number = 0
trials_per_block = 0
trials_per_practice_block = 0
block_number = 0
blocks_per_experiment = 0
practice_blocks_per_experiment = 0
trials_per_participant = 0

# database
data_columns = None
default_participant_fields = [["userhash", "participant"], "gender", "age", "handedness"]
default_demo_participant_str = TAB.join(["demo_user", "-", "-", "-"])


def init_project():
	# todo: write checks in these setters to not overwrite paths that don't include asset_paths (ie. arbitrarily set)
	global project_name
	global asset_path
	global database_filename
	global log_filename
	global log_file_path
	global database_path
	global database_backup_path
	global edf_path
	global schema_file_path
	global schema_filename
	global data_path
	global incomplete_data_path
	global config_filename
	global config_file_path
	global initialized

	database_filename = project_name + DB_EXT
	schema_filename = project_name + SCHEMA_EXT
	log_filename = project_name + LOG_EXT
	config_filename = project_name + CONFIG_EXT
	edf_path = os.path.join(asset_path, EDF)  # todo: write edf management
	log_file_path = os.path.join(asset_path, log_filename)
	schema_file_path = os.path.join(asset_path, schema_filename)
	database_path = os.path.join(asset_path, database_filename)
	database_backup_path = database_path + BACK_EXT
	data_path = os.path.join(asset_path, "Data")
	incomplete_data_path = os.path.join(data_path, "incomplete")
	config_file_path = os.path.join(asset_path, config_filename)
	initialized = True
	return True

def setup(project_name_str, asset_path_str):
	global project_name
	global asset_path
	project_name = project_name_str
	asset_path = asset_path_str
	return init_project()