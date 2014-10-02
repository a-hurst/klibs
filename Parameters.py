from os import path
#################################################################
#																#
#	REQUIRED PARAMETERS - DO NOT REMOVE, MODIFY ONLY IF SURE	#
#																#
#################################################################
SCRNFLGS = ["fullscreen", "doublebuf", "hwaccel", "hwsurface"]

BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)

SAC_VEL_THRESH = 10
SAC_ACC_THRESH = 10
SAC_MOTION_THRESH = 10

PPI = 96

VIEW_DISTANCE = 56

LoggedFields = list()
DB_NAME = "rsvp"
ASSET_PATH = "/KLAB/Non-Annual/Software Repository/KLIBSFramework/ExpAssets"
SCHEMA_FILENAME = "schema"
thesaurus = dict()

EDF_PATH = path.join(ASSET_PATH, "EDF")

NUM_BLOCKS = 1
TRIALS_PER_BLOCK = 256
NUM_PRACTICE_BLOCKS = 0
TRIALS_PER_PRACTICE_BLOCK = 0

FIX_SIZE = 1
BOX_SIZE = 1
CUE_SIZE = 1
CUE_BACK_SIZE = 1
X_SIZE = 1

THICK = 5
THIN = 1
FILL = 0

TAR_DUR = 300

NEGATIVE = 0
POSITIVE = 1
DURATION = 10000

TESTING = True
PAUSED = False
DEMOGRAPH = True
INSTRUCT = False
EXECUTE = True
ID_FIELD_NAME = "participant_id"
TRIAL_NUM = 0
BLOCK_NUM = 0
_EXP_FACTORS = None
KEYMAPS = dict()
WRONG_KEY_MSG = None
DEFAULT_FONT_SIZE = 28
COMPLETION_MESSAGE = "Thanks for participating; please have the researcher return to the room."


#################################################################
#																#
#	EXPERIMENT PARAMETERS - DEFINE AS NECESSARY					#
#																#
#################################################################
FACTORS = {"masks": ['full', 'central', 'peripheral'],
           "bgs": ['triangle_of_squares', 'triangle_of_circles', 'circle_of_triangles', 'square_of_triangles'],
           "fixation": ['center', 'top-middle', 'bottom-middle']}
METAFACTORS = [("1vd", "2vd", "4vd"),
               ("1vd", "4vd", "2vd"),
               ("2vd", "1vd", "4vd"),
               ("2vd", "4vd", "1vd"),
               ("4vd", "1vd", "2vd"),
               ("4vd", "2vd", "1vd")]
METACOND = None
KEYNAMES = ('z', '/')
KEYCODES = (122, 47)
KEYVALS = (0, 1)
LM_GREY = (223, 223, 223)