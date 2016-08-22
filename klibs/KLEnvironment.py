__author__ = 'jono'
import multiprocessing as mp

evm = None  # EventManager instance
clock = None  # TrialClock instance
exp = None  # Experiment instance
db = None  # Database instance
txtm = None  # TextManager instance
tk = None  # TimeKeeper instance
process_queue = mp.Queue()


class Environment(object):
	evm = None
	clock = None
	db = None
	txtm = None
	tk = None
	process_queue = None
	updated_events = []
	process_queue_data = {}

	def __init__(self):
		self.evm = evm
		self.clock = clock
		self.db = db
		self.txtm = txtm
		self.tk = tk
		self.process_queue = process_queue