__author__ = 'Jonathan Mulle & Austin Hurst'

"""The KLEnvironment module defines the objects that are available to users in the KLibs runtime
environment. When an experiment is launched with KLibs, the variables in this module are filled in
with with useful objects, which can then be accessed from anywhere within the KLibs runtime
by importing it from here.

Attributes:
	exp (:obj:`Experiment`): A pointer to the Experiment object of the current project.
	evm (:obj:`EventManager`): The EventManager instance for the current KLibs session.
	txtm (:obj:`TextManager`): The TextManager instance for the current project.
	db (:obj:`DatabaseManager`): The connection to the current project's database.
	el (:obj:`EyeLinkExt` or None): If 'P.eye_tracking' is True, this is the EyeLink (or TryLink)
		object for the current experiment. 

"""

exp = None  	# Experiment instance
evm = None  	# EventManager instance
txtm = None  	# TextManager instance
db = None  		# DatabaseManager instance
el = None  		# EyeLink instance


class EnvAgent(object):

	def __init__(self):
		object.__init__(self)

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
	def el(self):
		from klibs.KLEnvironment import el
		return el