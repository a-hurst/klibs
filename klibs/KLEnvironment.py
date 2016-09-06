__author__ = 'jono'

evm = None  	# EventManager instance
exp = None  	# Experiment instance
db = None  		# Database instance
txtm = None  	# TextManager instance
tk = None  		# TimeKeeper instance
rc = None  		# ResponseCollector instance
el = None  		# EyeLink instance

class EnvAgent(object):

	def __init__(self):
		super(EnvAgent, self).__init__()

	@property
	def evm(self):
		from klibs.KLEnvironment import evm
		return evm

	@property
	def exp(self):
		from klibs.KLEnvironment import exp
		return exp

	@property
	def txtm(self):
		from klibs.KLEnvironment import txtm
		return txtm

	@property
	def db(self):
		from klibs.KLEnvironment import db
		return db

	@property
	def tk(self):
		from klibs.KLEnvironment import tk
		return tk

	@property
	def rc(self):
		from klibs.KLEnvironment import rc
		return rc

	@property
	def el(self):
		from klibs.KLEnvironment import el
		return el