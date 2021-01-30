# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'


# Aliases for UI convenience
TAB = "\t"
NA = "NA"
ALL = "*"
RGBA = "RGBA"

# Time Constants
TK_MS = 1 # Use milliseconds
TK_S = 0 # Use seconds
DATETIME_STAMP = '%Y-%m-%d_%H-%M'

# KLBoundary shape aliases
RECT_BOUNDARY = "rectangle"
CIRCLE_BOUNDARY = "circle"
ANNULUS_BOUNDARY = "annulus"

# KLDraw Constants
STROKE_INNER = 1
STROKE_CENTER = 2
STROKE_OUTER = 3

# ResponseCollector Constants
RC_AUDIO = 'audio_listener'
RC_KEYPRESS = 'keypress_listener'
RC_COLORSELECT = 'color_listener'
RC_DRAW = 'draw_listener'
NO_RESPONSE = "NO_RESPONSE"
TIMEOUT = -1

# KLEyeTracking constants for writing readable eye tracking code
EL_LEFT_EYE = 0
EL_RIGHT_EYE = 1
EL_BOTH_EYES = 2
EL_NO_EYES = -1
EL_TRUE = 1
EL_FALSE = 0
# Constants corresponding to pylink's getTrackerVersion() return values
EYELINK_I = 1
EYELINK_II = 2
EYELINK_1000 = 3
# Variables indicating what to return from KLEyeTracking functions
EL_GAZE_START = "start gaze"
EL_GAZE_END = "end gaze"
EL_GAZE_AVG = "average gaze"
EL_TIME_START = "start time"
EL_TIME_END = "end time"
# KLEyeTracking event types
EL_GAZE_POS = 200
EL_BLINK_START = 3
EL_BLINK_END = 4
EL_BLINK_BOTH = [3, 4]
EL_FIXATION_START = 7
EL_FIXATION_END = 8
EL_FIXATION_BOTH = [7, 8]
EL_FIXATION_UPDATE = 9
EL_FIXATION_ALL = [7, 8, 9]
EL_SACCADE_START = 5
EL_SACCADE_END = 6
EL_SACCADE_BOTH = [5, 6]
EL_ALL_EVENTS = [
	EL_BLINK_START, EL_BLINK_END,
	EL_SACCADE_START, EL_SACCADE_END,
	EL_FIXATION_START, EL_FIXATION_END, EL_FIXATION_UPDATE
]

# KLNumpySurface Constants
NS_FOREGROUND = 1  # NumpySurface foreground layer
NS_BACKGROUND = 0  # NumpySurface background layer

# KLGraphics.blit() registration aliases
BL_CENTER = 5
BL_TOP = 8
BL_TOP_LEFT = 7
BL_TOP_RIGHT = 9
BL_LEFT = 4
BL_RIGHT = 6
BL_BOTTOM = 2
BL_BOTTOM_LEFT = 1
BL_BOTTOM_RIGHT = 3

# File Extensions
DB_EXT = ".db"
EDF_EXT = ".EDF"
DATA_EXT = ".txt"
BACKUP_EXT = ".backup"
LOG_EXT = "_log.txt"
SCHEMA_EXT = "_schema.sql"
USER_QUERIES_EXT = "_user_queries.json"
FACTORS_EXT = "_independent_variables.py"
PARAMS_EXT = "_params.py"
MESSAGING_EXT = "_messaging.csv"

# KLText Constants
TEXT_PT = "pt"
TEXT_PX = "px"
TEXT_MULTIPLE = "*"

# KLCommunication Constants (for query function)
AUTO_POS = "auto"
QUERY_ACTION_HASH = "hash"
QUERY_ACTION_UPPERCASE = "uppercase"

# KLDatabase Constants
PY_FLOAT = 'float'
PY_INT = 'int'
PY_BOOL = 'bool'
PY_STR = 'str'
PY_BIN = 'bytes'
SQL_NUMERIC = 'numeric'
SQL_FLOAT = 'float'
SQL_REAL = 'real'
SQL_INT = 'integer'
SQL_KEY = 'integer key'
SQL_BOOL = 'boolean'
SQL_STR = 'text'
SQL_BIN = 'blob'
SQL_NULL = 'null'
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

# AudioResponse Constants
AR_CHUNK_SIZE = 1024
AR_CHUNK_READ_SIZE = 1024
AR_RATE = 44100
