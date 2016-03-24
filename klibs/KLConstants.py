# -*- coding: utf-8 -*-
__author__ = 'jono'
import sdl2

DB_EXT = ".db"
EDF = "EDF"
EDF_EXT = ".EDF"
DATA_EXT = ".txt"
BACK_EXT = ".backup"
LOG_EXT = "_log.txt"
SCHEMA_EXT = "_schema.sql"
CONFIG_EXT = "_config.csv"
PARAMS_EXT = "_params.py"
EVENTS_EXT = "_events.csv"
INCH = "in"
CM = "cm"
TAB = "\t"

# Display Constants
PPI_CRT = 72
PPI_LCD = 96
BL_CENTER = 5
BL_TOP = 8
BL_TOP_LEFT = 7
BL_TOP_RIGHT = 9
BL_LEFT = 4
BL_RIGHT = 6
BL_BOTTOM = 2
BL_BOTTOM_LEFT = 1
BL_BOTTOM_RIGHT = 3

LEGACY_LOCATIONS = {
		'center': BL_CENTER,
		'topLeft': BL_TOP_LEFT,
		'top': BL_TOP,
		'topRight': BL_TOP_RIGHT,
		'left': BL_TOP_LEFT,
		'right': BL_RIGHT,
		'bottomLeft': BL_BOTTOM_LEFT,
		'bottom': BL_BOTTOM,
		'bottomRight': BL_BOTTOM_RIGHT
	}


NS_FOREGROUND = 1  # NumpySurface foreground layer
NS_BACKGROUND = 0  # NumpySurface background layer
MAX_WAIT = 9999999
OVER_WATCH = "over_watch"
ANY_KEY = "ANY_KEY"
TIMEOUT = "TIMEOUT"
NO_RESPONSE = "NO_RESPONSE"


PARTICIPANT_FILE = 1
EDF_FILE = 0

# KLDatabase
PY_FLOAT = 'float'
PY_STR = 'str'
PY_BOOL = 'bool'
PY_INT = 'int'
PY_BIN = 'binary'
SQL_FLOAT = 'float'
SQL_REAL = 'real'
SQL_BIN = 'blob'
SQL_KEY = 'integer key'
SQL_INT = 'integer'
SQL_NULL = 'null'
SQL_STR = 'text'
SQL_COL_DELIM_STR = "`, `"
ID = "id"
DB_SUPPLY_PATH = "s"
DB_CREATE = "c"
QUERY_INS = "insert"
QUERY_UPD = "update"
QUERY_DEL = "delete"
QUERY_SEL = "select"
DB_COL_SNAKE = "snake_case"
DB_COL_CAMEL = "camelCase"
DB_COL_TITLE = "TitleCase"
TBL_PARTICIPANTS = "participants"
TBL_EVENTS = "events"
TBL_TRIALS = "trials"
TBL_LOGS = "logs"

# KLTextManager
ANS_VALID = "answer valid"
ANS_INVALID = "answer invalid"
ANS_EMPTY = "empty answer"

# EyeSome definitions for visually clean interaction with the EyeLink C++ libraries
EL_LEFT_EYE = 0
EL_RIGHT_EYE = 1
EL_BOTH_EYES = 2
EL_NO_EYES = -1
EL_TRUE = 1
EL_FALSE = 0
PARALLEL_AVAILABLE = False
MAX_DRIFT_DEG = 3
INIT_SAC_DIST = 3  # Min. distance (degrees) before eye movement == initiating saccade for response direction
EL_TEMP_FILE = "temp_participant{0}".format(EDF)
# these mirror eyelink event codes where their counterpart exists
EL_SACCADE_START = 5
EL_SACCADE_END = 8
EL_SACCADE_BOTH = [5,8]

# lists of sdl2 key representations needed by klibs
MOD_KEYS = {"Left Shift": 1, "Right Shift": 2, "Left Ctrl": 64, "Right Ctrl": 128,  # todo: make __mod_keysyms
			"Left Alt": 256, "Right Alt": 512, "Left Command": 1024, "Right Command": 2048}
UI_METHOD_KEYSYMS = [sdl2.SDLK_q, sdl2.SDLK_c, sdl2.SDLK_p]

SCREEN_FLAGS = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP | sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
EL_RECT_BOUNDARY = "rectangle"
EL_CIRCLE_BOUNDARY = "circle"
RGBA = "RGBA"

# TrialFactory Constants
TF_FACTORS = 0
TF_WEIGHTED_FACTORS = 1
TF_STIM_FILE = 2
TF_TRIAL_DATA = "Data"
TF_TRIAL_PARAMETERS = "Parameters"
TF_DATA = "data"
TF_PARAM = "param"
TF_TRIAL_COUNT = "trial_count"
TF_TRIAL_COUNT_UC = "Trial_Count"
TF_NAS = ["na", "n/a", "NA", "N/A", "nA", "Na", "n/A", "N/a"]

# Utilities Constants
ENTERING = 1
EXITING = 2
EXCEPTION = 3
DATETIME_STAMP = '%Y-%m-%d %H:%M:%S'

# Drawbject Constants
STROKE_INNER = 1
STROKE_CENTER = 2
STROKE_OUTER = 3

# AudioResponse Constants
AR_THRESHOLD = 1000
AR_AUTO_THRESHOLD = 1
AR_CHUNK_SIZE = 1024
AR_CHUNK_READ_SIZE = 1024
AR_RATE = 44100
AUDIO_ON = 1
AUDIO_OFF = 0

# TimeKeeper Constants
TK_MS = "milliseconds"
TK_S = "seconds"

# LabJack Constants
LABJACK_AVAILABLE = True

# ResponseCollector Constants
RC_AUDIO = 'audio'
RC_KEYPRESS = 'keypress'
RC_MOUSECLICK = 'mouseclick'
RC_MOUSEDOWN = 'mousedown'
RC_MOUSEUP = 'mouseup'
RC_SACCADE = 'saccade'
RC_FIXATION = 'fixation'

# EventInterface Event Constants
EVI_CLOCK_START = "CLOCK_START"
EVI_CLOCK_STOP = "CLOCK_STOP"
EVI_TRIAL_START = "TRIAL_START"
EVI_TRIAL_STOP = "TRIAL_STOP"
EVI_BLOCK_START = "BLOCK_START"
EVI_BLOCK_STOP = "BLOCK_STOP"
EVI_PR_TRIAL_START = "PRACTICE_TRIAL_START"
EVI_PR_TRIAL_STOP = "PRACTICE_TRIAL_STOP"
EVI_PR_BLOCK_START = "PRACTICE_BLOCK_START"
EVI_PR_BLOCK_STOP = "PRACTICE_BLOCK_STOP"
EVI_TRIAL_RECYCLED = "TRIAL_RECYCLED"
EVI_EL_START_REC = "EYELINK_START_RECORDING"
EVI_EL_STOP_REC = "EYELINK_STOP_RECORDING"
EVI_EXP_SETUP_START = "EXPERIMENT_SETUP_START"
EVI_EXP_SETUP_STOP = "EXPERIMENT_SETUP_STOP"
EVI_T_PREP_START = "TRIAL_PREP_START"
EVI_T_PREP_STOP = "TRIAL_PREP_STOP"
EVI_T_CLEANUP_START = "TRIAL_CLEANUP_START"
EVI_T_CLEANUP_STOP = "TRIAL_CLEANUP_STOP"