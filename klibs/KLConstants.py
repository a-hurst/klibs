__author__ = 'jono'
import sdl2

DB = ".db"
EDF = "EDF"
EDF_EXT = ".EDF"
DATA = ".txt"
BACK = ".backup"
LOG = "_log.txt"
SCHEMA = "_schema.sql"
INCH = "in"
CM = "cm"
NS_FOREGROUND = 1  # NumpySurface foreground layer
NS_BACKGROUND = 0  # NumpySurface background layer
MAX_WAIT = 9999999
OVER_WATCH = "over_watch"
ANY_KEY = "ANY_KEY"
TIMEOUT = "TIMEOUT"
NO_RESPONSE = "NO_RESPONSE"

ON = 1
OFF = 0

PARTICIPANT_FILE = 1
EDF_FILE = 0

# EyeSome definitions for visually clean interaction with the EyeLink C++ libraries
EL_LEFT_EYE = 0
EL_RIGHT_EYE = 1
EL_BOTH_EYES = 2
EL_NO_EYES = -1
EL_TRUE = 1
EL_FALSE = 0
PARALELL_AVAILABLE = False
MAX_DRIFT_DEG = 3
INIT_SAC_DIST = 3  # Min. distance (degrees) before eye movement == initiating saccade for response direction
EL_TEMP_FILE = "temp_participant{0}".format(EDF)
# lists of sdl2 key representations needed by klibs
MOD_KEYS = {"Left Shift": 1, "Right Shift": 2, "Left Ctrl": 64, "Right Ctrl": 128,  # todo: make __mod_keysyms
			"Left Alt": 256, "Right Alt": 512, "Left Command": 1024, "Right Command": 2048}
UI_METHOD_KEYSYMS = [sdl2.SDLK_q, sdl2.SDLK_c, sdl2.SDLK_p]

SCREEN_FLAGS = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP | sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
RECT = 0
CIRCLE = 1
RGBA = "RGBA"

# TrialFactory Constants
TF_FACTOR = 0
TF_STIMFILE = 0
TF_RULES = 0
