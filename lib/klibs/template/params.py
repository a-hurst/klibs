import random
import logging

### Klibs Parameter overrides ###

# Any param that is commented out by default is either deprecated or else not
# yet implemented--don't uncomment or use

#########################################
# Logging Defaults
#########################################
log_to_file = True
level = logging.INFO

#########################################
# Display Settings
#########################################
additional_displays = []
screen_origin = (0,0)  # always (0,0) unless multiple displays in use

#########################################
# Available Hardware
#########################################
eye_tracker_available = False
eye_tracking = False
labjack_available = False
labjacking = False

#########################################
# Environment Aesthetic Defaults
#########################################
default_fill_color = (45, 45, 45, 255)
default_color = (255, 255, 255, 255)
default_response_color = default_color
default_input_color = default_color
default_font_size = 28
default_font_name = 'Frutiger'
default_timeout_message = "Too slow!"

#########################################
# EyeLink Sensitivities
#########################################
view_distance = 104  # in centimeters, 57m = in 1deg of visual angle per horizontal cm of screen
saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15

fixation_size = 1,  # deg of visual angle

#########################################
# Experiment Structure
#########################################
multi_session_project = False
collect_demographics = False
manual_demographics_collection = False
trials_per_block = 24
blocks_per_experiment = 1
table_defaults = {}

#########################################
# Development Mode Settings
#########################################
dm_suppress_debug_pane = False
dm_auto_threshold = True
dm_trial_show_mouse = True
dm_ignore_local_overrides = False

#########################################
# Data Export Settings
#########################################
data_columns = None
unique_identifier = "userhash"
default_participant_fields = [[unique_identifier, "participant"], "sex", "age", "handedness"]
default_participant_fields_sf = [[unique_identifier, "participant"], "random_seed", "sex", "age", "handedness"]

#########################################
# PROJECT-SPECIFIC VARS
#########################################
