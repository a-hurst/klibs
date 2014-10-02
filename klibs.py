#TODO: 1) App.query() is intermittently using accepted_list; look into & fix
import abc
import pygame
import math
import sys
import os
import random
import time
import datetime
import traceback
import ntpath
import sqlite3
import hashlib
import re
import pylink
import shutil
import numpy
from functools import wraps

#Minimum velocity in degrees per second before an eye movement is classified as a Saccade
SAC_VEL_THRESH = 22
#Minimum acceleration in degrees per second^2 before an eye movement is classified as a Saccade
SAC_ACC_THRESH = 5000
#Minimum distance moved in degrees before an eye movement is classified as a Saccade
SAC_MOTION_THRESH = 0.15
#Allowable eye drift from mandatory fixation in degrees of visual angle
MAX_DRIFT_DEG = 3
#Minimum distance moved in degrees before eye movement counts as an initial saccade for response direction detection
INIT_SAC_DIST = 3

# string constants, included for tidyness below basically
SQL = ".sql"
DB = ".db"
BACK = ".backup"


thesaurus = {'Test': False}
global mute
mute = False
global swatcount
swatcount = 0


def pr(desc=None, subj=None):
	if mute:
		return None
	###just for debugging, a quick 'got here' with optional details
	global swatcount
	swatcount += 1
	if not desc or (desc and subj == None):
		print str(swatcount) + ". Got Here" + repr(desc)
	if desc and subj:
		print str(swatcount) + ". " + desc + " : " + repr(subj)


def canonical(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		for kw in kwargs:
			if thesaurus.get(kwargs[kw]) is not None:
				kwargs[kw] = thesaurus.get(kwargs[kw])
		func(args, kwargs)

	return wrapper

#############
#  CLASSES
#############

class TrialIterator:
	def __init__(self, l):
		self.l = l
		self.length = len(l)
		self.i = 0

	def __iter__(self):
		return self

	def __len__(self):
		return self.length

	def __getitem__(self, i):
		return self.l[i]

	def __setitem__(self, i, x):
		self.l[i] = x

	def next(self):
		if self.i >= self.length:
			raise StopIteration
		else:
			self.i += 1
			return self.l[self.i - 1]

	def recycle(self):
		self.l.append(self.l[self.i - 1])
		temp = self.l[self.i:]
		random.shuffle(temp)
		self.l[self.i:] = temp
		self.length += 1


class KlibBase(object):
	__metaclass__ = abc.ABCMeta

	def __init__(self):
		pygame.init()
		pygame.mouse.set_visible(False)
		self.header = "***{0}"
		self.rex = Thesaurus(self.header)
		self.logfile = "logfile"
		self.verbosity = 10  # Should hold a value between 0-10, with 0 being no errors and 10 being all errors

	def absolutePosition(self, pos, destination):
		height = 0
		width = 0
		if type(destination) is pygame.Surface:
			height = destination.get_height()
			width = destination.get_width()
		locs = {
		'center': [width // 2, height // 2],
		'topLeft': [0, 0],
		'top': [width // 2, 0],
		'topRight': [width, 0],
		'left': [0, height // 2],
		'right': [0, height],
		'bottomLeft': [0, height],
		'bottom': [width // 2, height],
		'bottomRight': [width, height]
		}
		return locs[pos]

	def alert_header(self, alert_type='error'):
		return self.header.format(alert_type.upper())

	def equiv(self, key, syn):
		resp = self.rex.inspect(key, syn)
		return resp

	def eAttr(self, argName, given, expected, kw=True):
		if kw:
			err_string = "The keyword argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
		else:
			err_string = "The argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
		return err_string.format(argName, type(given), type(expected))

	def err(self, errorString='', className=None, method=None, alertType=None, kill=False):
		stackBack = -2  # add one for every function call executed between the error and calling KlibBase.err()
		if alertType == None:
			alertType = 'error'
		if className != None:
			if method != None:
				localTrace = "{0}.{1}(): ".format(className, method)
			else:
				localTrace = "{0}\n\t: ".format(className)
		elif method != None:
			localTrace = "\t{0}(): ".format(method)
		trace = traceback.extract_stack()[stackBack]
		fileName = ntpath.basename(trace[0])
		line = trace[1]
		if self.equiv('true', kill):
			print "{0} ON LINE '{1}' OF '{2}'***\n{3}{4} Exiting program...\n".format(self.alert_header(alertType),
			                                                                          line, fileName, localTrace,
			                                                                          errorString)
			self.quit()
		else:
			print "{0} ON LINE 1{1}' OF '{2}'***\n{3}{4}\n".format(self.alert_header(alertType), line, fileName,
			                                                       localTrace, errorString)

	def safeFlagstr(self, flags, prefix=None, uc=True):
		if prefix and type(prefix) is not str:
			e = "The keyword argument, 'prefix', must be of type 'str' but '{0}' was passed.".format(type(prefix))
			raise TypeError(e)

		if type(flags) is list:
			for i in range(0, len(flags)):
				if uc:
					flags[i] = flags[i].upper()
				else:
					flags[i] = flags[i]
				if prefix:
					flags[i] = prefix + "." + flags[i]
			flagstring = " | ".join(flags)

		else:
			e = "The 'flags' argument must be of type 'list' but '{0}' was passed.".format(type(flags))
			raise TypeError(e)

		return flagstring

	def ln(self):
		return traceback.extract_stack()[-2][1]

	def peak(self, v1, v2):
		if v1 > v2:
			return v1
		else:
			return v2

	def log(self, msg, priority):
		"""Log an event
		:param msg: - a string to log
		:param priority: - 	an integer from 1-10 specifying how important the event is,
							1 being most critical and 10 being routine. If set to 0 it
							will always be printed, regardless of what the user sets
							verbosity to. You probably shouldn't do that.
		"""
		if priority <= self.verbosity:
			with open(self.logfile, 'a') as log:
				log.write(str(priority) + ": " + msg)

	def prettyJoin(self, array, whitespace=1, delimiter="'", delimitBehavior=None, prepend=None,
	               beforeLast=None, eachN=None, afterFirst=None, append=None):
		"""Automates string combination. Parameters:
		:param array: - a list of strings to be joined
		:param config: - a dict with any of the following keys:
			'prepend':
			'afterFirst':
			'beforeLast':
			'eachN':
			'whitespace':	Whitespace to place between elements. Should be a positive integer, but can be a string if the number
							is smaller than three and greater than zero. May also be the string None or False, but you should probably
							just not set it if that's what you want.
			'append':
			'delimiter':
			'delimitBehavior':
			'delimitBehaviour':
		"""
		msg = "Trying to use  a .join() call instead." # gets repeated in several 'raise' statements, easier to reuse
		config = None
		ws = ''
		for n in range(whitespace):
			ws += ' '
		whitespace = ws

		output = ''
		if prepend is not None:
			output = prepend
		for n in range(len(array)):
			#if after first iteration, print whitespace
			if n > 1:
				output = output + whitespace
			#if beforeLast is set, print it and add whitespace
			if (n == (len(array) - 1)) and beforeLast is not None:
				output = output + beforeLast + whitespace
			# if eachN is set and the iterator is divisible by N, print an eachN and add whitespace
			if eachN is (list or tuple):
				if len(eachN) == 2:
					if type(eachN[0]) is int:
						if n % eachN == 0:
							output = output + str(eachN[1]) + whitespace
					else:
						self.log(
							"Klib.prettyJoin() config parameter 'eachN[0]' must be an int, '{0}' {1} passed. {2}".format(
								eachN, type(eachN, 10)))
				else:
					raise ValueError(
						"Klib.prettyJoin() config parameter 'eachN' must be a tuple or list of length 2, but {0} of length '{1}' passed. {2}".format(
							type(eachN), len(eachN), msg))
			elif eachN is not None:
				raise TypeError(
					"Klib.prettyJoin() config parameter 'eachN' must be a list or tuple, '{0}' passed. {1}".format(
						type(eachN), msg))
			# if delimiter is set to default or wrap, print a delimiter before the array item
			if delimitBehavior in ('wrap', None):
				output = output + delimiter
			# finally print the array item
			output = output + str(array[n]) + delimiter + whitespace
			# if afterFirst is set, print it and add whitespace
			if (n == 0) and (afterFirst is not None):
				output = output + afterFirst + whitespace
		if append is not None:
			output = output + append

		return output

	def quit(self, msg=None):
		if msg:
			print msg
		print "Exiting..."
		pygame.quit()
		sys.exit()

	def isTuplist(self, var):
		if type(var) is tuple:
			return True
		if type(var) is list:
			return True
		return False

	def pxToDeg(self, length): #length = px
		return length / self.PPD

	def degToPx(self, deg):
		return deg * self.PPD

	def warn(self, errorString='', className=None, method=None):
		return self.err(errorString, className, method, 'warn', False)


class App(KlibBase):


	def __init__(self, el=None, params_file=None, params_dir=None):
		KlibBase.__init__(self)

		# intialize experiment params from parameters file
		self.__load_params(params_file, params_dir)

		#initialize the database instance
		self.__db_init()

		# initialize screen surface and screen parameters
		self.__screen_init(self.VIEW_DISTANCE, flags=self.SCRNFLGS)
		pygame.init()

		# initialize the text layer for the app
		self.text = TextLayer(self.screenxy, self.screenxy, self.PPI)
		if self.DEFAULT_FONT_SIZE:
			self.text.defaultFontSize = self.DEFAULT_FONT_SIZE


		# assign custom EEG function, optional
		self._codeFunc = None

		# if el:
		# 	self.EL = el
		# else:
		# 	self.EL = EyeLink()
		# self.no_tracker = self.EL.dummy_mode
		# self.EL.screenSize = self.screenxy


	def __trial_func(self, *args, **kwargs):
		"""
		Manages a trial.
		"""
		# try:
		self.TRIAL_NUM += 1
		self.trial_prep(*args, **kwargs)
		trial_data = self.trial(*args, **kwargs)
		# except:
		# 	raise
		# finally:
		self.__log_trial(trial_data)
		self.trial_clean_up()

	def __experiment_manager(self, *args, **kwargs):
		"""
		Manages an experiment using the schema and factors.
		"""
		self.setup()
		# try:
		for i in range(self.practiceBlocks):
			self.__generate_trials(practice=True, codeGen=self._codeFunc, **self._EXP_FACTORS)
			if self.trialsPerPracticeBlock % len(self.trials):
				if self.trialsPerPracticeBlock < len(self.trials):
					self.trials = self.trials[:self.trialsPerPracticeBlock]
				else:
					raise ValueError("The desired number of trials in the practice block, \
					{0}, is not a multiple of the minimum number of trials, {1}.".format(self.trialsPerPracticeBlock,
					                                                                     len(self.trials)))
			else:
				self.trials *= (self.trialsPerPracticeBlock / len(self.trials))
			self.__trial_func(*args, **kwargs)
		for i in range(self.blocks):
			self.BLOCK_NUM = i + 1 # added this for out to data files more than use in program logic
			self.__generate_trials(practice=False, codeGen=self._codeFunc, **self._EXP_FACTORS)
			if self.trialsPerBlock % len(self.trials):
				e = "The desired number of trials in the block, {0}, is not a multiple of the minimum number of trials, {1}.".format(
					self.trialsPerBlock, len(self.trials))
				raise ValueError(e)
			else:
				self.trials *= (self.trialsPerBlock / len(self.trials))
				random.shuffle(
					self.trials)  # ROSS: SHOULD I HAVE DONE THIS? IT DOESN'T OTHERWISE SEEM THAT TRIALS ARE SHUFFLED?
			for t in self.trials:
				self.__trial_func(t, self.TRIAL_NUM)
			self.block_break()
		# except Exception as e:
		# 	print e
		# finally:
		# 	self.cleanUp()


	def __load_params(self, params_file=False, params_dir=False):
		if params_file and params_dir:
			path = os.join(params_dir, params_file)
		else:
			path = False

		if path:
			#todo: can't use import, here, should
			mod_contents = __import__("", globals(), locals(), ["Parameters"], -1)
			mod_contents = getattr(mod_contents, "Parameters.py")
			params = dir(mod_contents)
		else:
			mod_contents = __import__("Parameters")
			params = dir(mod_contents)


		for p in params:
			if p[:2] != "__":
				ucp = p.upper()
				val = getattr(mod_contents, p)
				setattr(self, ucp, val)
		#todo: write logic for exploring default locations for exp. intrux & other customizable strings
			# note that currently, instructions are a property with a getter & setter in App


	def __db_init(self):
		self.db = Database(self.DB_NAME, self.SCHEMA_FILENAME, self.ASSET_PATH)

	@property
	def screen_ratio(self):
		dividend = round(float(self.screenx) / float(self.screeny), 3)
		if dividend == 1.333:
			return "4:3"
		elif dividend == 1.778:
			return "16:9"
		elif dividend == 1.6:
			return "16:10"
		else:
			return "X:Y"

	def __generate_trials(self, practice=False, codeGen=None, **kwargs):
		"""
		Example usage:
		codeGen=self.codeFunc, cue=['right', 'left'], target=['right', 'left'], type=['word', 'nonword'], cued_bool='cue==target'
		To create an expression, simply pass a named string ending in _bool with a logical expression inside:
		cued_bool='peripheral==cue'
		Do not include other expression variables in an expression.
		They are evaluated in arbitrary order and may not yet exist.
		:param practice:
		:param codeGen:
		:return:
		"""
		trials = [[practice]]
		factors = ['practice']
		evalQueue = list()
		for k, f in kwargs.iteritems():
			temp = list()
			if k[-5:] == '_bool':
				evalQueue.append([k, f])
			else:
				factors.append(k)
				for e in trials:
					if e:
						for v in f:
							te = e[:]
							te.append(v)
							temp.append(te)
				trials = temp[:]
		for e in evalQueue:
			factors.append(e[0][:-5])
			print "e: " + e[1]
			operands = re.split('[=>!<]+', str(e[1]).strip())
			operator = re.search('[=<!>]+', str(e[1])).group()
			for t in trials:
				t.append(eval('t[factors.index(\'' + operands[0] + '\')]' + operator + 't[factors.index(\'' + operands[
					1] + '\')]'))
		if codeGen is not None and type(codeGen).__name__ == 'function':
			factors.append('code')
			for t in trials:
				t.append(codeGen(t))
		self.trials = trials
		self.factors = factors

	def __log_trial(self, trialData, autoID=True):
		if autoID:
			if self.TESTING or not self.DEMOGRAPH:
				self.participantId = -1
			trialData[self.ID_FIELD_NAME] = self.participantId
		for attr in trialData:
			self.db.log(attr, trialData[attr])
		self.db.insert()

	def __set_stroke(self):
		stroke = int(1 * math.floor(self.appy / 500.0))
		if (stroke < 1):
			stroke = 1
		return stroke

	def __screen_init(self, viewDistance, flags=None):
		if flags:
			flagstring = self.safeFlagstr(flags, 'pygame')
		if flagstring:
			self.screen = pygame.display.set_mode((0, 0), eval(flagstring))
		else:
			self.screen = pygame.display.set_mode((0, 0))
		# self.screen = pygame.Surface(self.screenxy, flags = eval(flagString), depth = 8)
		screen = self.screen.get_size()
		self.screenx = int(screen[0])
		self.screeny = int(screen[1])
		self.screenxy = [self.screenx, self.screeny]
		self.ratio = self.screen_ratio()
		self.screenc = [self.screenx / 2, self.screeny / 2]
		self.diag_px = int(math.sqrt(self.screenx * self.screenx + self.screeny * self.screeny))    # pythagoras yo
		self.canvas = pygame.display.get_surface()

		# calculate physical size of screen; screenModes[0] = largest resolution current monitor can display
		screenModes = pygame.display.list_modes()
		self.physicalScreenx = screenModes[0][0] / self.PPI
		self.physicalScreeny = screenModes[0][1] / self.PPI

		# this error message can be used in three places below, it's easier set it here
		e = "viewRule must be int or a tuple/list containing [int,str]; '{0}' of type '{1}' passed.".format(
			repr(viewDistance), type(viewDistance))

		# interpret viewDistance
		if self.isTuplist(viewDistance):
			if type(viewDistance[0]) is int:
				if self.equiv('inch', viewDistance[1]):
					self.viewDistance = viewDistance[0]
					self.viewUnit = 'inch'
				elif self.equiv('cm', viewDistance[1]):
					self.viewDistance = viewDistance[0]
					self.viewUnit = 'cm'
					#convert physical screen measurements to cm
					self.physicalScreenx *= 2.55
					self.physicalScreeny *= 2.55
				else:
					raise TypeError(e)
			else:
				raise TypeError(e)
		elif type(viewDistance) is int:
			self.viewDistance = viewDistance
			self.viewUnit = 'inch'
		else:
			raise TypeError(e)

		self.screenDegx = math.degrees(math.atan((self.physicalScreenx / 2.0) / self.viewDistance) * 2)
		self.pixelsPerDegree = self.screenx / self.screenDegx
		self.PPD = self.pixelsPerDegree #alias for convenience

	def alert(self, alertString, urgent=False, displayFor=0):
		#TODO: address the absence of default colors
		"""
		Display an alert

		:param alertString: - Message to display
		:param urgent: - Boolean, determines alert saliency
		"""
		if not urgent:
			return self.message(alertString, color=(255, 0, 0), location='top-right', registration=9)
		text = self.message(alertString, color=(255, 0, 0), location=self.screenc, registration=5,
		                    fontSize=self.text._defaultFontSize * 2, rtrn=True)
		width = int(math.ceil(text.get_width() * 1.2))
		height = int(math.ceil(text.get_height() * 1.2))
		bounds = pygame.Surface((width, height))
		bounds.fill((0, 0, 0))
		bounds.set_alpha(150)
		self.bliterate(bounds, 5, self.screenc)
		self.bliterate(text, 5, self.screenc)
		now = time.time()
		while time.time() - now < displayFor:
			self.flip()

	def bliterate(self, targ, registration=7, pos=[0, 0], destination=None, flags=None, area=None):
		# set method vars, build registration map
		tarW = targ.get_width()
		tarH = targ.get_height()
		if destination:
			desW = destination.get_width()
			desH = destination.get_width()
		else:
			destination = self.screen
			desW = self.screenx
			desH = self.screeny
		locations = ['center', 'topLeft', 'topRight', 'bottomLeft', 'bottomRight', 'top', 'left', 'right', 'bottom']
		registrations = {
		1: [0, -1.0 * tarH],
		2: [-1.0 * tarW / 2.0, tarH],
		3: [-1.0 * tarW, -1.0 * tarH],
		4: [0, -1.0 * tarH / 2.0],
		5: [-1.0 * tarW / 2.0, -1.0 * tarH / 2.0],
		6: [-1.0 * tarW, -1.0 * tarH / 2.0],
		7: [0, 0],
		8: [-1.0 * tarW / 2.0, 0],
		9: [-1.0 * tarW, 0]
		}
		# address flags and areas (if any)
		if flags:
			flagstr = self.safeFlagstr(flags, 'pygame')
		else:
			flagstr = None
		if area:
			if type(area).__name__ != 'pygame.Rect':
				e = self.eAttr('area', area, 'pygame.Rect')
				raise TypeError(e)

		# make sure the target fits within the destination
		# if tarW > desW or tarH > desH:
		# 	e = "The target, '{0}', cannot be blit to '{1}' because it is wider or taller than the destination surface.".format(repr(targ), repr(destination))
		# 	raise ValueError(e)
		# elif area:
		# 		if tarW > area.width or tarH > area.height:
		# 			e = "The target, '{0}', cannot be blit to '{1}' because it is wider or taller than the defined rect area.".format(repr(targ), repr(destination))
		# 			raise ValueError(e)

		# get coordinates from registration point
		if 0 < registration & registration < 10:
			regx = int(registrations[registration][0])
			regy = int(registrations[registration][1])
		else:
			regx = int(registrations[7][0])
			regy = int(registrations[7][1])

		# find absolute position if given relative location, or set it if provided as absolute
		if type(pos) is str:
			if pos in locations:
				pos = self.absolutePosition(pos, destination)
			else:
				e = "Value '{0}' was passed for 'pos' but this was not a key in the locations dict.".format(repr(pos))
				raise ValueError(e)

		if type(pos) is tuple or type(pos) is list:
			regRefx = int(pos[0]) + int(regx)
			regRefy = int(pos[1]) + int(regy)
		else:
			e = "Value of parameter 'pos' was neither a valid string nor a list or tupple of length 2; value '{0}' of type '{1}' passed.".format(
				repr(pos), type(pos))
			raise ValueError(e)
		if area:
			if flagstr:
				destination.blit(targ, (regRefx, regRefy), area, eval(flagstr))
			else:
				destination.blit(targ, (regRefx, regRefy), area)
		if flagstr:
			destination.blit(targ, (regRefx, regRefy), None, eval(flagstr))
		else:
			destination.blit(targ, (regRefx, regRefy))

	@abc.abstractmethod
	def block(self, blockNum):
		pass

	def block_break(self, message=None, isPath=False):
		"""
		Display a break message between blocks

		:param message: A message string or path to a file containing a message string
		:param isPath:
		:raise:
		"""
		default = "You've completed block {0} of {1}. When you're ready to continue, press any key.".format(
			self.BLOCK_NUM, self.blocks)
		if isPath:
			try:
				pathExists = os.path.exists(message)
				if pathExists:
					with open(message, "r") as f:
						message = f.read().replace("\n", '')
				else:
					e = "'isPath' parameter was True but '{0}' was not a valid path. Using default message".format(
						message)
					raise IOError(e)
			except IOError as e:
				self.warn(e, 'App', 'blockBreak')
				message = default
		if self.TESTING:
			pass
		else:
			if type(message) is str:
				if message is None:
					message = default
				self.message(message, fullscreen=True, rtrn='flip', location='center', registration=5)
				self.listen('*', '*')

	def bounded_by(self, pos, left, right, top, bottom):
		xpos = int(pos[0])
		ypos = int(pos[1])
		# todo: tighten up that series of ifs into one statement
		if all(type(val) is int for val in (left, right, top, bottom)) and type(pos) is tuple:
			if xpos > left:
				if xpos < right:
					if ypos > top:
						if ypos < bottom:
							return True
						else:
							return False
					else:
						return False
				else:
					return False
			else:
				return False
		else:
			raise TypeError(
				"One or more arguments of boundedBy() were of the wrong type; 'pos' must be a tuple and the remaining arguments must be integers.")

	def get_demographics(self):
		"""
		Gather participant demographic information and enter it into the database

		"""
		#TODO: this function should have default questions/answers but should also be able to read from a CSV or array for custom Q&A
		self.db.initEntry('participants', instanceName='ptcp', setCurrent=True)
		nameQuery = self.query(
			"What is your full name, banner number or e-mail address? Your answer will be encrypted and cannot be read later.",
			password=True)
		nameHash = hashlib.sha1(nameQuery)
		name = nameHash.hexdigest()
		self.db.log('userhash', name)

		if self.db.is_unique(name, 'userhash',
		                    'participants'): #names must be unique; returns True if unique, False otherwise
			self.db.log('gender', self.query("What is your gender? Answer with:  (m)ale,(f)emale or (o)ther)",
			                                 accepted=('m', 'M', 'f', 'F', 'o', 'O')))
			self.db.log('handedness', self.query(
				"Are right-handed, left-handed, or ambidextrous? Answer with (r)ight, (l)eft or (a)mbidextrous).",
				accepted=('r', 'R', 'l', 'L', 'a', 'A')))
			self.db.log('age', self.query('What is  your age?', returnType='int'))
			self.db.log('created', self.now())
			self.db.log('modified', self.now())
			if not self.db.insert():
				raise DbException("App.getDemographics() called Database.insert(), which failed for unknown reasons.")
			self.db.cursor.execute("SELECT `id` FROM `participants` WHERE `userhash` = '{0}'".format(name))
			result = self.db.cursor.fetchall()
			self.participantId = result[0][0]
			if not self.participantId:
				raise ValueError(
					"A problem was encountered when retrieving participant_id and it could not be set. Exiting program.")
		else:
			retry = self.query('That participant identifier has already been used. Do you wish to try another? (y/n) ')
			if retry == 'y':
				self.get_demographics()
			else:
				self.sf()
				self.message("Thanks for participating!", location=self.screenc)
				pygame.display.flip()
				time.sleep(2)
				print "quitting..."
				self.quit()

	def exp_structure(self, blocks, trialsPerBlock, practiceBlocks, trialsPerPracticeBlock=None):
		if type(blocks) and type(trialsPerBlock) and type(practiceBlocks) is int:
			self.blocks = blocks
			self.trialsPerBlock = trialsPerBlock
			self.practiceBlocks = practiceBlocks
		else:
			raise ValueError("All parameters must be of type 'int'.")

		if trialsPerPracticeBlock is not None:
			if type(trialsPerPracticeBlock) is int:
				self.trialsPerPracticeBlock = trialsPerPracticeBlock
			else:
				raise ValueError("All parameters must be of type 'int'.")
		else:
			self.trialsPerPracticeBlock = trialsPerBlock

	def exempt(self, index, state=True):
		if index in self.exemptions.keys():
			if state == 'on' or True:
				self.exemptions[index] = True
			if state == 'off' or False:
				self.exemptions[index] = False

	def flip(self, duration=0):
		"""
		Flip the screen and wait for an optional duration
		:param duration: The duration to wait in ms
		:return: :raise: AtributeError, TypeError, GenError
		"""
		pygame.display.flip()
		if duration == 0:
			return
		if type(duration) is int:
			if duration > 0:
				start = time.time()
				while time.time() - start < duration:
					self.overWatch()
			else:
				raise AttributeError("Duration must be a positive number, '{0}' was passed".format(duration))
		else:
			raise TypeError("Duration must be expressed as an integer, '{0}' was passed.".format(type(duration)))

	def keyMapper(self, name, keyNames=None, keyCodes=None, keyVals=None):
		if type(name) is not str:
			e = self.eAttr("name", type(name), "str")
			raise TypeError(e)

		# register the keymap if one is being passed in and set keyMap = name of the newly registered map
		if all(type(keyParam) in [tuple, str] for keyParam in [keyNames, keyCodes, keyVals]):
			self.KEYMAPS[name] = KeyMap(name, keyNames, keyCodes, keyVals)

		#retrieve registered keymap(s) by name
		if name in self.KEYMAPS:
			return self.KEYMAPS[name]
		elif name == "any": # just returns first registered map; if using one map per project, can call listen() with one param only
			if len(self.KEYMAPS) > 0:
				mapNames = self.KEYMAPS.keys()
				return self.KEYMAPS[mapNames[0]]
		elif name == "*":
			self.KEYMAPS['*'] = KeyMap('*', anyKey=True)
			return self.KEYMAPS['*']

	def instructions(self, text, isPath=False):
		if isPath:
			if type(text) is str:
				f = open(text, 'rt')
				text = f.read()
			else:
				e = "App.instructions() requires the param 'text' to be of type 'str' but '{0}' was passed.".format(
					type(text))
				raise TypeError(e)

		self.sf()
		self.message(text, location="center", wrapWidth=800)

	def listen(self, maxWait, keyMap=None, hostFunc=None, hostArgs=None, hostKWArgs=None, elArgs=None,
	           nullResponse=None, timeOutMessage=None, responseCount=None, responseMap=None, interrupt=True,
	           quickReturn=False):
		# TODO: have customizable wrong key & time-out behaviors
		# TODO: make RT & Response part of a customizable ResponseMap object
		# TODO: startTime should be optionally predefined and/or else add a latency param to be added onto starTime
		# TODO: make it possible to pass the parameters of a new KeyMap directly to listen()

		#establish an interval for which to listen()
		if maxWait == '*':
			maxWait = 999999 #an approximation of 'forever' since '*' is not an integer (see the while loop below)
		elif type(maxWait) not in (int, float):
			e = self.eAttr("interval", type(maxWait), "int", False)
			raise TypeError(e)
		if not keyMap:
			keyMap = "any"
		keyMap = self.keyMapper(keyMap)
		response = None
		rt = -1

		startTime = time.time()
		waiting = True

		# enter with a clean event queue
		pygame.event.clear()
		self.flip()

		wrongKey = False
		while waiting:
			if elArgs:
				if type(elArgs) is dict:
					self.ELResp = self.EL.listen(**elArgs)
				else:
					e = "elArgs must be a dict but type '{0}' was passed.".format(type(elArgs))
					raise TypeError(e)
			if hostArgs and hostFunc:
				if type(hostArgs) is dict:
					# abstract method, allows for blits, flips and other changes during a listen() call
					hostFunc(*hostArgs, **hostKWArgs)
				else:
					e = "updateArgs must be a dict but type '{0}' was passed.".format(type(elArgs))
					raise TypeError(e)
			pygame.event.pump()
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					rt = time.time() - startTime
					if not response: # only record a response once per call to listen()
						key = event.key
						if keyMap.validate(key): # a KeyMap with name "*" (ie. anykey) returns self.ANY_KEY
							response = keyMap.val(key)
							if interrupt: # ONLY for TIME SENSITIVE reactions to participant response; this flag voids overwatch()
								return (response, rt)
						else:
							wrongKey = True
				if event.type == pygame.KEYUP: # KEYDOWN is bad when listening for mod keys b/c the mod is itself also a key
					metaEvent = self.overWatch(event) # ensure the 'wrong key' wasn't a call to quit or pause
					if interrupt:    # returns response immediately; else waits for maxWait to elapse
						if response:
							return (response, rt)
						elif keyMap.anyKey:
							return (keyMap.anyKey, rt)
					if not metaEvent and wrongKey == True: # flash an error for an actual wrong key
						if not self.WRONG_KEY_MSG:
							wrongKeyMessage = "Please respond using '{0}'.".format(keyMap.validKeys())
						self.alert(wrongKeyMessage, True)
						wrongKey = False
			if (time.time() - startTime) > maxWait:
				waiting = False
		if not response:
			if nullResponse:
				return (nullResponse, rt)
			else:
				return ("NO_RESPONSE", rt)
		else:
			return (response, rt)

	# @canonical
	def message(self, message, font=None, fontSize=None, color=None, bgcolor=None, bgIsKey=None,
	            location=None, registration=None, wrap=None, wrapWidth=None, delimiter=None, rtrn=False,
	            flip=False, fullscreen=False):
		renderConfig = {}
		messageSurface = None  # unless wrap is true, will remain empty

		if font is None:
			if self.text.defaultFont:
				font = self.text.defaultFont
			else:
				raise AttributeError("Cannot render text; no font passed and no default font has been set.")

		try:
			if fontSize is None:
				if self.text._defaultFontSize:
					fontSize = self.text._defaultFontSize
				else:
					raise AttributeError("No font size was passed, and no default is set. Using 14pt as a standard.")
			else:
				fontSize = fontSize
		except AttributeError as e:
			renderfontSize = self.text.size('14pt')
			self.warn(e, (self.__class__.__name__, 'message'))

		if color == None:
			if self.text.defaultColor:
				color = self.text.defaultColor
			else:
				color = (0, 0, 0)
				e = "No color passed and no default color set. Using black (0,0,0) as default."
				self.warn(e, "App", "message")

		if bgcolor == None:
			if self.text.defaultBgColor:
				bgcolor = self.text.defaultBgColor
			else:
				e = "No background color passed and no default background color set. Using app.palette.white as default."
				bgcolor = (255, 255, 255)
				self.warn(e, (self.__class__.__name__, 'message'))

		#wrapping detection and processing
		if wrap:
			message = self.text.wrappedText(message, delimiter, fontSize, font, wrapWidth)
			lineSurfaces = []
			messageHeight = 0
			messageWidth = 0
			for line in message:
				lineSurface = self.text.renderText(line, renderConfig)
				lineSurfaces.append((lineSurface, [0, messageHeight]))
				messageWidth = self.peak(lineSurface.get_width(), messageWidth)
				messageHeight = messageHeight + lineSurface.get_height()
			messageSurface = pygame.Surface((messageWidth, messageHeight))
			messageSurface.fill(bgcolor)
			if self.equiv('true', bgIsKey):
				messageSurface.set_colorkey(bgcolor)
			for lsurf in lineSurfaces:
				self.bliterate(lsurf[0], 7, lsurf[1], messageSurface)

		#process location, infer if need be; failure here is considered fatal
		if self.isTuplist(location):
			if len(location) == 2:
				pass #just a reasonably thorough test for a correctish value
			else:
				raise AttributeError(
					"Coordinate locations must be either a tuple or list of length 2; '{0}' passed".format(
						repr(location)))
		elif location == None:
			# By Default: wrapped text blits to screen center; single-lines blit to topLeft with a padding = fontSize
			if wrap:
				location = self.screenc
			else:
				xOffset = (self.screenx - self.screenx) // 2 + fontSize
				yOffset = (self.screeny - self.screeny) // 2 + fontSize
				location = [xOffset, yOffset]
		elif type(location) is str:
			if location == "center" and registration is None: # an exception case for perfect centering
				registration = 5
			location = self.absolutePosition(location, self.screen)
		else:
			raise ValueError(
				"The location '{0}' could not be interpreted by the App, please use a tuple/list of coordinates or else a relative keyword (ie. 'center')".format(
					repr(location)))

		#process blit registration
		if registration is None:
			if wrap:
				registration = 5
			else:
				registration = 7

		if rtrn:
			if wrap:
				return messageSurface
			else:
				messageSurface = self.text.renderText(message, renderConfig)
				#check for single lines that extend beyond the app area and wrap if need be
				if messageSurface.get_width() > self.screenx:
					wrap = True
					return self.message(message, wrap=True)
				else:
					return messageSurface
		else:
			if fullscreen:
				self.sf() #TODO:make it possible to sf() with a passed or preset color
			if wrap:
				self.bliterate(messageSurface, 5, self.screenc)
			else:
				messageSurface = self.text.renderText(message, font, fontSize, color, bgcolor)
				if messageSurface.get_width() > self.screenx:
					return self.message(message)
				self.bliterate(messageSurface, registration, location)
			if flip:
				self.flip()
			return True

	def now(self):
		today = datetime.datetime
		return today.now().strftime("%Y-%m-%d %H:%M:%S")

	def overWatch(self, event=None):
		keyup = False
		key = -1
		mod = -1
		while not keyup:
			if event is None:
				pygame.event.pump()
				for event in pygame.event.get():
					if event.type == pygame.KEYDOWN:
						key = event.key
						mod = event.mod
					elif event.type == pygame.KEYUP:
						if key is None and mod is None:
							key = event.key
							mod = event.mod
						keyup = True
				if key == -1 and mod == -1 and keyup is False:
					keyup = True

			elif event == 'pass':
				keyup = True
				pass
			elif event.type == pygame.KEYDOWN:
				key = event.key
				mod = event.mod
				event = None
			elif event.type == pygame.KEYUP:
				key = event.key
				mod = event.mod
				keyup = True

		if key == 113 and mod == (1024 or 2048):  # quit
			self.quit()
		if key == 49 and mod == (1024 or 2048):  # calibrate
			self.calibrate()
			return True
		if key == 50 and mod == (1024 or 2048):  # pause
			if not self.PAUSED:
				self.PAUSED = True
				self.pause()
				return True
			if self.PAUSED:
				self.PAUSED = False
				return False
		if mod != (1024 or 2048):
			return False

	def pause(self):
		time.sleep(0.2)  # to prevent unpausing immediately due to a key(still)down event
		while self.PAUSED:
			self.message('PAUSED', fullscreen=True, location='center', fontSize=96, color=(255, 0, 0),
			             registration=5, rtrn='flip')
			self.overWatch()
			self.flip()

	def preBlit(self, targ, start_time, end_time, registration=7, pos=[0, 0], destination=None, flags=None, area=None, interim_action=None):
		"""
		Blit to the screen buffer, wait until endTime to flip. Check func often if set.
		:type start_time: float
		:param targ:
		:param start_time: Time trial began (from time.time())
		:param end_time: The time post trial after which the screen should be flipped.
		:param registration:
		:param pos:
		:param destination:
		:param flags:
		:param area:
		:param interim_action: A function called repeatedly until the duration has passed. Don't make it long.
		"""
		self.bliterate(targ, registration, pos, destination, flags, area)
		now = time.time()
		while now < start_time + end_time:
			if interim_action is not None:
				interim_action()
			now = time.time()
		self.flip()
		return now - start_time + end_time

	def preBug(self):
		#todo: will be a screen that's shown before anything happens in the program to quickly tweak debug settings
		pass


	def query(self, query=None, password=False, font=None, fontSize=None, color=None,
	          locations={'query': None, 'input': None}, registration=5, returnType=None, accepted=None):

		inputRenderConfig = {}
		inputLocation = None
		queryRenderConfig = {}
		queryLocation = None
		verticalPadding = None
		queryRegistration = 8
		inputRegistration = 2

		# build config argument(s) for __renderText()
		# process the possibility of different query/input font sizes
		if fontSize is not None:
			if type(fontSize) is (tuple or list):
				if len(fontSize) == 2:
					inputRenderfontSize = self.text.fontSizes[fontSize[0]]
					queryRenderfontSize = self.text.fontSizes[fontSize[1]]
					verticalPadding = queryRenderfontSize
					if inputRenderfontSize < queryRenderfontSize: #use smaller of two font sizes as vertical padding from midline
						verticalPadding = inputRenderfontSize
			else:
				inputRenderfontSize = self.text.fontSizes[fontSize]
				queryRenderfontSize = self.text.fontSizes[fontSize]
				verticalPadding = self.text.fontSizes[fontSize]
		else:
			inputRenderfontSize = self.text._defaultFontSize
			queryRenderfontSize = self.text._defaultFontSize
			verticalPadding = self.text._defaultFontSize

		if registration != None:
			if type(registration) is (tuple or list):
				inputRegistration = registration[0]
				queryRegistration = registration[1]
			else:
				inputRegistration = registration
				queryRegistration = registration

		# process the (unlikely) possibility of different query/input fonts
		if font is not None:
			if type(font) is (tuple or list) and len(font) == 2:
				try:
					inputRenderfont = font[0]
				except:
					print "Font provided in query()->config parameter not found in app.text.fonts, attempting to use default... "
					inputRenderfont = self.text.defaultFont
				try:
					queryRenderfont = font[1]
				except:
					print "Font provided in query()->config parameter not found app.text.fonts, attempting to use default... "
					queryRenderfont = self.text.defaultFont
			else:
				inputRenderfont = font
				queryRenderfont = font
		elif self.text.defaultFont != '':
			inputRenderfont = self.text.defaultFont
			queryRenderfont = self.text.defaultFont
		else:
			print "query() quitted"
			self.quit() #error

		# process the possibility of different query/input colors
		if color is not None:
			if len(color) == 2:
				inputRendercolor = color[0]
				queryRendercolor = color[1]
			else:
				inputRendercolor = color
				queryRendercolor = color
		else:
			inputRendercolor = self.text.defaultColor
			queryRendercolor = self.text.defaultColor

		# processlocations
		generateLocations = False
		if locations is not None:
			if locations.get('query') is None or locations.get('input') is None:
				if self.text.defaultLocations.get('query') is not None and self.text.defaultLocations.get(
						'input') is not None:
					queryLocation = self.text.defaultLocations['query']
					inputLocation = self.text.defaultLocations['input']
				else:
					generateLocations = True
			else:
				queryLocation = locations['query']
				inputLocation = locations['input']
		else:
			generateLocations = True
		# infer locations if none are provided (ie. center horizontally, vertically padded from screen midline)
		# create & render querySurface
		#
		# Note: inputString is on a separate surface, declared later in this function!
		querySurface = None
		queryText = ''
		if query is not None:
			querySurface = self.text.renderText(query, font=font, fontSize=fontSize, color=color, bgcolor=None)
		elif self.text.defaultQueryString is not None:
			querySurface = self.text.renderText(self.text.defaultQueryString, font=font, fontSize=fontSize,
			                                    color=color, bgcolor=None)
		else:
			raise ValueError("A default query was not set and no query was provided")

		queryBaseline = (self.screeny // 2) - verticalPadding
		inputBaseline = (self.screeny // 2) + verticalPadding
		horizontalCenter = self.screenx // 2
		if generateLocations:
			queryLocation = [horizontalCenter, queryBaseline]
			inputLocation = [horizontalCenter, inputBaseline]

		self.sf()
		self.bliterate(querySurface, queryRegistration, queryLocation)
		self.flip()
		inputString = ''  # declare now, populate in loop below, '' instead of None to ensure initialization as strings
		userFinished = False  # True when enter or return are pressed
		noAnswerMessage = 'Please provide an answer.'
		badAnswerMessage = None
		if accepted is not None:
			if not self.isTuplist(accepted):
				raise TypeError(
					"The set of accepted responses must be a tuple or a list but type '{0}' was given.".format(
						type(accepted)))
			accepted = self.prettyJoin(accepted, beforeLast='or', prepend='[ ', append=']')
			badAnswerMessage = 'Your answer must be one of the following: {0}'.format(accepted)
		while not userFinished:
			pygame.event.pump()
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					if inputString == noAnswerMessage:
						inputString = ''
					key = event.key
					ukey = event.unicode
					mod = event.mod
					self.overWatch(event)
					if key == 1024 | 2048:
						pass
					elif key == 8: #pygame defaults to ASCII, not UTF-8, so I've followed convention.
						if inputString:
							inputString = inputString[0:(len(inputString) - 1)]
							if password == True and len(inputString) != 0:
								pwstring = '' + len(inputString) * '*'
								inputSurface = self.text.renderText(pwstring, inputRenderConfig)
							else:
								inputSurface = self.text.renderText(inputString, inputRenderConfig)
							self.sf()
							self.bliterate(querySurface, queryRegistration, queryLocation)
							self.bliterate(inputSurface, inputRegistration, inputLocation)
							self.flip()
					elif key == 13 or key == 271:
						badAnswer = False
						noAnswer = False
						if len(inputString) > 0:
							if accepted:   #to make the accepted list work, there's a lot of checking yet to do
								if inputString in accepted:
									userFinished = True
								else:
									badAnswer = True
							else:
								userFinished = True
						else:
							noAnswer = True

						if badAnswer or noAnswer:
							if badAnswer:
								inputString = badAnswerMessage
							else:
								inputString = noAnswerMessage
							tempColor = inputRendercolor
							inputRendercolor = self.text.alertColor
							inputSurface = self.text.renderText(inputString, inputRenderConfig)
							self.sf()
							self.bliterate(querySurface, queryRegistration, queryLocation)
							self.bliterate(inputSurface, inputRegistration, inputLocation)
							self.flip()
							inputRendercolor = tempColor
							inputString = ''
					elif key == 27:
						inputString = ''
						inputSurface = self.text.renderText(inputString, inputRenderConfig)
						self.sf()
						self.bliterate(querySurface, queryRegistration, queryLocation)
						self.bliterate(inputSurface, inputRegistration, inputLocation)
						self.flip()

					else:
						inputString += str(ukey)
						inputSurface = None
						if password:
							if password == True and len(inputString) != 0:
								pwstring = '' + len(inputString) * '*'
								inputSurface = self.text.renderText(pwstring, inputRenderConfig)
							else:
								inputSurface = self.text.renderText(inputString, inputRenderConfig)
						else:
							inputSurface = self.text.renderText(inputString, inputRenderConfig)
						self.sf()
						self.bliterate(querySurface, queryRegistration, queryLocation)
						self.bliterate(inputSurface, inputRegistration, inputLocation)
						self.flip()
				elif event.type == pygame.KEYUP:
					self.overWatch(event)
		self.sf()
		self.flip()
		if returnType is not None:
			if returnType == 'int':
				return int(inputString)
			if returnType == 'str':
				return str(inputString)
		else:
			return inputString

	def quit(self):
		try:
			self.db.db.commit()
		except:  # TODO: Determine exception type
			print "Commit() to database failed."
			pass
		try:
			self.db.db.close()
		except:  # TODO: Determine exception tpye
			print "Database close() unsuccessful."
			pass
		if not self.no_tracker:
			if self.EL.el.isRecording():
				self.EL.el.stopRecording()
		pygame.quit()
		sys.exit()

	def run(self, *args, **kwargs):
		self.__experiment_manager(*args, **kwargs)


	def start(self):
		self.startTime = time.time()


	def sf(self, color=(255, 255, 255), surface=None): #switched order of color, surface for faster default use
		if surface is None:
			surface = self.screen
		surface.fill(color)


	@property
	def asset_path(self):
		return self.asset_path

	@asset_path.setter
	def asset_path(self, asset_path):
		if type(asset_path) is not str:
			err_string = "App.asset_path must be a string representation of a file path, but type '{0}' provided."
			raise TypeError(err_string.format(type(asset_path)))
		if not os.path.isdir(asset_path):
			raise ValueError("App.asset_path must be a directory.")

	@asset_path.getter
	def asset_path(self):
		return self.asset_path

	@property
	def event_code_manager(self):
		return self._codeFunc

	@event_code_manager.setter
	def event_code_manager(self, codeFunc):
		if type(codeFunc).__name__ == 'function':
			self._codeFunc = codeFunc
		elif codeFunc is None:
			self._codeFunc = None
		else:
			raise ValueError('App.codeFunc must be set to a function.')

	@property
	def no_tracker(self):
		return self._noTracker

	@no_tracker.setter
	def no_tracker(self, noTracker):
		if type(noTracker) is bool:
			self._noTracker = noTracker
		else:
			raise ValueError('App.noTracker must be a boolean value.')

	@property
	def exp_factors(self):
		return self._EXP_FACTORS

	@exp_factors.setter
	def exp_factors(self, factors):
		if type(factors) == dict:
			self._EXP_FACTORS = factors
		elif factors is None:
			self._EXP_FACTORS = None
		else:
			raise ValueError('App.exp_factors must be a dict.')

	@property
	def participant_instructions(self):
		pass

	@participant_instructions.getter
	def participant_instructions(self):
		return self.participant_instructions

	@participant_instructions.setter
	def participant_instructions(self, instructions_file):
		with open("ExpAssets/participant_instructions.py", "r") as ins_file:
			self.participant_instructions = ins_file.read()

	@abc.abstractmethod
	def cleanUp(self):
		return

	@abc.abstractmethod
	def setup(self):
		pass

	@abc.abstractmethod
	def trial(self, trialNum):
		pass

	@abc.abstractmethod
	def trial_prep(self):
		pass

	@abc.abstractmethod
	def trial_clean_up(self):
		pass

	@abc.abstractmethod
	def refresh_screen(self, **kwargs):
		pass


class Palette(KlibBase):
	def __init__(self):
		KlibBase.__init__(self)
		self.black = (0, 0, 0)
		self.white = (255, 255, 255)
		self.grey1 = (50, 50, 50)
		self.grey2 = (100, 100, 100)
		self.grey3 = (150, 150, 150)
		self.grey4 = (200, 200, 200)
		self.grey5 = (250, 250, 250)
		self.alert = (255, 0, 0)

	def hsl(self, index):
		print("to be defined later")


class Thesaurus(KlibBase):
	def __init__(self, errorHeader):
		self.header = errorHeader # mirror of KlibBase's same; cannot call KlibBase.__init__() without causing an infinite loop
		self.thesaurus = {'true': [True, 'true', 'TRUE', 'True'],
		                  'false': [False, 'false', 'False', 'FALSE'],
		                  'none': [None, 'none', 'NONE', 'None'],
		                  'int': ['integer', 'integer key', 'INTEGER', 'INTEGER KEY'],
		                  'float': ['real', 'REAL', 'float', 'FLOAT'],
		                  'inch': ['inch', 'inches', 'INCH', 'INCHES', 'Inch', 'Inches', 'in', 'IN', 'In'],
		                  'cm': ['cm', 'CM', 'centimeter', 'centimeters', 'CENTIMETER', 'CENTIMETERS', 'Centimeter',
		                         'Centimeters']}

	def addKey(self, key, synList):
		try:
			if type(key) is str:
				if key in self.thesaurus:
					self.addSynonym(key, synList)
					raise GenWarning(
						"The key '{0}' is already registered; any new synonyms in the provided synList will be added.")
				else:
					self.thesaurus[key] = ''
					self.addSynonym(key, synList)
			else:
				raise GenError(
					"Parameter 'key' must be a string, value '{0}' of type '{1}' was passed.".format(repr(key),
					                                                                                 type(key)))
		except GenWarning as e:
			self.warn(e, ('Thesaurus', 'addKey'))
		except GenError as e:
			self.err(e, ('Thesuars', 'addkey'), True)
		return True

	def addSynonym(self, key, synList):
		doList = False
		try:
			if type(key) is str:
				if key in self.thesaurus:
					doList = True
				else:
					raise GenWarning("Key '{0}' was not registered; adding it before processing synList...".format(key))
		except GenWarning as e:
			self.warn(e, ('Thesaurus', 'addSynonym'))
			self.addKey(key)
		try:
			if doList:
				if type(synList) is list or type(synList) is tuple:
					for n in synList:
						if not n in self.thesaurus[key]:
							self.thesaurus[key].append(n)
				else:
					self.thesaurus[key].append(synList)
			else:
				raise GenError(
					"A valid key was no provided, without which there is no index for which synonyms can be stored.")
		except GenError as e:
			self.err(e, ('Thesaurus', 'addSynonym'), True)
		return True

	def inspect(self, key, syn):
		try:
			if type(key) is str:
				if key in self.thesaurus:
					if syn in self.thesaurus[key]:
						return True
					else:
						return False
				else:
					raise GenError("The key '{0}' was not found in the Klib thesaurus.".format(key))
			else:
				raise GenError(
					"Search key must be a string, but the key '{0}' was of type '{1}'".format(repr(key), type(key)))
		except GenError as e:
			self.err(e.message, ('Thesaurus', 'inspect'))
			return False


class Database(KlibBase):
	#TODO: improve path management; currently this class cannot be used by any other app
	def __init__(self, db_name, schema_filename, asset_path):
		KlibBase.__init__(self)
		self.db = None
		self.cursor = None
		self.schema = None
		self.asset_path = asset_path
		self.schema_path = os.path.join(self.asset_path, schema_filename.rstrip(".sql") + SQL)
		self.db_path = os.path.join(self.asset_path, db_name + DB)
		self.db_backup_path = os.path.join(self.asset_path, db_name + DB + BACK)
		self.__default_table = -1

		self.__init_db()
		if self.buildTableSchemas():
			self.__openEntries = {}
			self.__currentEntry = None



	def __catch_db_not_found(self):
		self.db = None
		self.cursor = None
		self.schema = None
		err_string = "No database file was present at '{0}'. \nYou can (c)reate it, (s)upply a different path or (q)uit."
		user_action = raw_input(err_string.format(self.db_path))
		if user_action == "s":
			self.db_path = raw_input("Great. Where might it be?")
			self.__init_db()
		elif user_action == "c":
			try:
				f = open(self.db_path, "a").close()
			except IOError as e:
				print e
				self.quit()
			self.__init_db()
		else:
			self.quit()

	def __init_db(self):
		err_string = "Database schema could not be deployed; there is a syntax error in the SQL file."
		if os.path.exists(self.db_path):
			shutil.copy(self.db_path, self.db_backup_path)
			self.db = sqlite3.connect(self.db_path)
			self.cursor = self.db.cursor()
			table_list = self.__tables()
			if len(table_list) == 0:
				if os.path.exists(self.schema_path):
					self.__deploy_schema(self.schema_path)
					return True
						# self.__drop_tables(table_list, True)
						# self.err(err_string, ('Database', "__init__"), True)
				# else:
				# 	self.schema = self.temp_schema[0]
				# 	self.schema_path = None
				# 	try:
				# 		self.__deploy_schema(self.temp_schema[0], False)
				# 		return True
				# 	except:  #todo: wtf jon
				# 		print self.err(err_string, {'class': 'Database', 'method': '__init__'})
				# 		self.__drop_tables(table_list, True)
				# 		self.quit()
				else:
					raise RuntimeError("Database exists but no tables were found and no table schema were provided.")
		else:
			self.__catch_db_not_found()


	def __tables(self):
		#TODO: I changed tableCount to tableList and made it an attribute as it seems to be used in rebuild. Verify this.
		self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
		self.tableList = self.cursor.fetchall()
		return self.tableList

	def __drop_tables(self, table_list=None, kill_app=False):
		if table_list is None:
			table_list = self.__tables()
		for n in table_list:
			if str(n[0]) != "sqlite_sequence":
				self.cursor.execute("DROP TABLE `{0}`".format(str(n[0])))
		self.db.commit()
		if kill_app:
			self.db.close()
			self.__restore()
			self.quit()

	def __restore(self):
		# restores database file from the back-up of it
		os.remove(self.db_path)
		os.rename(self.db_backup_path, self.db_path)

	def __deploy_schema(self, sqlSchema):
		f = open(sqlSchema, 'rt')
		self.cursor.executescript(f.read())
		return True

	def buildTableSchemas(self):
		self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
		tables = {}
		for tableTuple in self.cursor.fetchall():
			table = str(tableTuple[0]) # str() necessary b/c tableTuple[0] is in unicode
			if table != "sqlite_sequence":
				tableCols = {}
				self.cursor.execute("PRAGMA table_info(" + table + ")")
				columns = self.cursor.fetchall()
				for col in columns:
					if col[2] in ('text', 'TEXT'):
						colType = 'str'
					elif self.equiv('int', col[2]):
						colType = 'int'
					elif col[2] in ('blob', 'BLOB'):
						colType = 'binary'
					elif self.equiv('float', col[2]):
						colType = 'float'
					else:
						colType = 'unknown'
						e = "column '{0}' of table '{1}' has type '{2}' on the database but was assigned a type of 'unknown' during schema building'".format(
							col[1], table, col[2])
						self.warn(e, "Database", "buildTableSchemas")
					allowNull = False
					if col[3] == 0:
						allowNull = True
					tableCols[str(col[1])] = {'order': int(col[0]), 'type': colType, 'allowNull': allowNull}
				tables[table] = tableCols
		self.tableSchemas = tables
		return True

	def flush(self):
		self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
		for tableTuple in self.cursor.fetchall():
			table = str(tableTuple[0]) #str() necessary b/c tableTuple[0] is in unicode
			if table == "sqlite_sequence":
				pass
			else:
				self.cursor.execute("DELETE from `{0}`".format(table))
		self.db.commit()

	def rebuild(self):
		self.__drop_tables()
		e = "Error: Database schema could not be deployed; there is a syntax error in the SQL file."
		if self.schema is not None:
			if self.__deploy_schema(self.schema, False):
				initialized = True
			else:
				self.__drop_tables(self.tableList, True)
				raise IOError(e)
		elif self.schema_path is not None:
			if self.__deploy_schema(self.schema_path, True):
				initialized = True
			else:
				self.__drop_tables(self.tableList, True)
				raise IOError(e)

		if self.buildTableSchemas():
			self.__openEntries = {}
			self.__currentEntry = 'None'
			print  "Database successfully rebuilt; exiting program. Be sure to disable the call to Database.rebuild() before relaunching."
			# TODO: Make this call App.message() somehow so as to be clearer.Or better, relaunch the app somehow!!
			# m = "Database successfully rebuilt; exiting program. Be sure to disable the call to Database.rebuild() before relaunching."
			# App.message(m, location="center", fullscreen=True, fontSize=48, color=(0,255,0))
			self.quit()

	def entry(self, instance=None):
		if instance == None:
			try:
				return self.__openEntries[self.__currentEntry]
			except:
				print self.err() + "Database\n\tentry(): A specific instance name was not provided and there is no current entry set.\n"
		else:
			try:
				return self.__openEntries[instance]
			except:
				print self.err() + "Database\n\tentry(): No currently open entries named '" + instance + "' exist."

	def initEntry(self, tableName, instanceName=None, setCurrent=True):
		if type(tableName) is str:
			if self.tableSchemas[tableName]:
				if instanceName is None:
					instanceName = tableName
				self.__openEntries[instanceName] = EntryTemplate(tableName, self.tableSchemas[tableName], instanceName)
				if setCurrent:
					self.current(instanceName)
			else:
				print "No table with the name '" + tableName + "' was found in the Database.tableSchemas."
		else:
			raise ValueError("tableName must be a string.")

	def empty(self, table):
		pass

	def log(self, field, value, instance=None):
		if (instance != None) and (self.__openEntries[instance]):
			self.__currentEntry = instance
		elif instance == None and self.__currentEntry != 'None':
			instance = self.__currentEntry
		else:
			raise ValueError("No default entry is set and no instance was passed.")
		self.__openEntries[instance].log(field, value)

	def current(self, verbose=False):
		if verbose == (0 or None or 'None' or False):
			self.__currentEntry = 'None'
			return True
		if verbose == 'return':
			return self.__currentEntry
		if type(verbose) is str:
			if self.__openEntries[verbose]:
				self.__currentEntry = verbose
				return True
			return False
		if self.__currentEntry != 'None':
			if verbose:
				return self.__currentEntry
			else:
				return True
		else:
			if verbose:
				return 'None'
			else:
				return False

	def is_unique(self, value, field, table):
		query = "SELECT * FROM `{0}` WHERE `{1}` = '{2}'".format(table, field, value)
		self.cursor.execute(query)
		result = self.cursor.fetchall()
		if len(result) > 0:
			return False
		else:
			return True

	@property
	def default_table(self):
			return self.__default_table

	@default_table.setter
	def default_table(self, name):
		self.__default_table = name

	def insert(self, data=None, table=None, tidyExec=True):
		if data is None:
			current = self.current('return')
			data = self.entry(current)
			if not data:
				raise AttributeError("No data was provided and a Database.__currentEntry is not set.")
		dataIsEntryTemplate = False # expected use is to insert from an EntryTemplate object, but raw data is also allowed
		if data.__class__.__name__ == 'EntryTemplate':
			dataIsEntryTemplate = True
			query = data.buildQuery('insert')
		else:
			# this else statement may be broken as of Aug 2013 (ie. since Ross was involved, it's not been returned to)
			template = None
			if table:
				if not self.__default_table:
					raise AttributeError(
						"Either provide a table when calling insert() or set a defaultTable with App.Database.setDefaultTable().")
				else:
					table = self.__default_table
				template = self.tableSchemas[table]
			if not template:
				raise AttributeError(
					"The supplied table name, '{0}' was not found in Database.tableSchemas".format(table))
			fieldCount = len(template)
			if template['id']:
				fieldCount -= 1  # id will be supplied by database automatically on cursor.execute()
			cleanData = [None, ] * fieldCount
			insertTemplate = [None, ] * fieldCount
			if len(data) == fieldCount:
				for fieldName in template:
					field = template[fieldName]
					order = field['order']
					if template['id']:
						order -= 1
					if type(data[order]).__name__ == field['type']:
						insertTemplate[order] = fieldName
						if field['type'] == ('int' or 'float'):
							cleanData[order] = str(data[order])
						else:
							cleanData[order] = "'" + str(data[order]) + "'"
			else:
				raise AttributeError(
					'Length of data list does not much number of table columns. You are collecting more data items than exist in the database table.')
			query = "INSERT INTO `" + table + "` (" + ", ".join(insertTemplate) + ") VALUES (" + ",".join(
				cleanData) + ")"
		self.cursor.execute(query)
		self.db.commit()
		if tidyExec and dataIsEntryTemplate:
			if self.__currentEntry == data.name:
				self.current()  # when called without a parameter current() clears the current entry
		return True

	def query(self, query, doReturn=True):
		result = self.cursor.execute(query)
		self.db.commit()
		if result and doReturn:
			return result
		#add in error handling for SQL errors


class EntryTemplate(KlibBase):
	def __init__(self, tableName, tableSchema, instanceName):
		KlibBase.__init__(self)
		if type(tableSchema) is dict:
			self.schema = tableSchema
		else:
			raise TypeError
		if type(tableName) is str:
			self.tableName = tableName
		else:
			raise TypeError
		try:
			self.name = instanceName
			if not self.name:
				raise AttributeError(
					'InstanceName could not be set, ensure parameter is passed during initialization and is a string.')
		except AttributeError as e:
			self.err(e, 'EntryTemplate', '__init__', kill=True)
		self.data = ['null', ] * len(tableSchema)  # create an empty tuple of appropriate length

	def prSchema(self):
		schemaStr = "{\n"
		for col in self.schema:
			schemaStr += "\t\t\t" + col + " : " + repr(self.schema[col]) + "\n"
		schemaStr += "\t\t}"
		return schemaStr

	def buildQuery(self, queryType):
		insertTemplate = ['null', ] * len(self.schema)
		for fieldName in self.schema:
			fieldParams = self.schema[fieldName]
			columnOrder = fieldParams[
				'order'] # the data order and schema order may differ, which is fatal; this index is for (re)correlating
			insertTemplate[columnOrder] = fieldName
			if self.data[columnOrder] == 'null':
				if fieldParams['allowNull']:
					self.data[columnOrder] = 'DELETE_THIS_FIELD'
					insertTemplate[columnOrder] = 'DELETE_THIS_FIELD'
				elif (queryType == 'insert') and (fieldName == 'id'):
					self.data[0] = 'DELETE_THIS_FIELD'
					insertTemplate[0] = 'DELETE_THIS_FIELD'
				else:
					e = "[instance '{0}']: The required fieldParams '{1}' had a null value.".format(self.name,
					                                                                                fieldName)
					raise IndexError(e)
				# I can't for the life of me figure out where the fuck this next bit was supposed to go, but the problem it
				# describes is a legit one, so I'm leaving it here until the problem shows up haha
				# else:
				# 	e ="[instance '{0}] an index was found in EntryTemplate.schema that exceeds the range of EntryTemplate.data; debug info to follow...".format(self.name)
				# 	debug ="\n***DEBUGGING INFO:\n\tOrder was:\n\t\t{0}\n\tSchema was:\n\t\t{1}\n\tData was:\n\t\t{2}".format(str(fieldParams['columnOrder']),self.prSchema(),repr(self.data))
				# 	raise IndexError(e+debug)
		insertTemplate = self.__tidyNulls(insertTemplate)
		self.data = self.__tidyNulls(self.data)
		if queryType == 'insert':
			try:
				fields = "`" + "`,`".join(insertTemplate) + "`"
				vals = ",".join(self.data)
				queryString = "INSERT INTO `{0}` ({1}) VALUES ({2})".format(self.tableName, fields, vals)
				return queryString
			except Exception as e:
				print e
				e = "[instance '{0}'] SQL query string couldn't be written because NoneType items were found in either 'insertTemplate' or 'EntryTemplate.data'; printing debug info.".format(
					self.name)
				debug = "\t****DEBUGGING INFO:\n\t\tinsertTemplate = {0}\n\t\tself.data = {1}".format(
					repr(insertTemplate), repr(self.data))
				self.err(e + debug, 'EntryTemplate', 'buildQuery', kill=True)
		elif queryType == 'update':
			pass
		#TODO: build logic for update statements as well (as against only insert statements)

	def __tidyNulls(self, data):
		keepFields = []
		index = 0
		for n in data:
			if n != 'DELETE_THIS_FIELD':
				keepFields.append(index)
			index += 1
		newData = []
		for n in keepFields:
			newData.append(data[n])
		return newData

	def log(self, field, value):
		# TODO: Add some basic logic for making type conversions where possible (ie. if expecting a float
		# but an int arrives, try to cast it as a float before giving up
		fieldOrder = self.schema[field]['order']
		fieldType = self.schema[field]['type']
		valueType = type(value).__name__
		if field not in self.schema:
			e = "No field named '{0}' exists in the table '{1}'".format(field, self.tableName)
			raise ValueError(e)
		# SQLite has no bool data type; conversion happens now b/c the value/field comparison below can't handle a bool
		if value == True:
			value = 1
			valueType = type(value).__name__
		elif value == False:
			value = 0
			valueType = type(value).__name__
		if (valueType == fieldType):
			if fieldType == 'int':
				self.data[fieldOrder] = str(value)
			elif fieldType == 'float':
				self.data[fieldOrder] = str(value)
			else:
				self.data[fieldOrder] = "'" + str(value) + "'"
		elif (self.schema[field]['allowNull'] == True) and value in (None, '', 'null', 'NULL', 'none', 'NONE'):
			self.data[fieldOrder] = None
		else:
			e = "Schema for this table expected the field '{0}' type '{1}', but the passed value ('{2}') was of type '{3}'.".format(
				field, self.schema[field]['type'], value, type(value).__name__)
			raise TypeError(e)

	def report(self):
		print self.schema


class EyeLink(pylink.EyeLink):
	dummy_mode = False
	screen_size = None

	def __init__(self, dummy_mode=False):
		self.is_dummy_mode = dummy_mode

	def tracker_init(self, dummy_mode=False):
		if dummy_mode:
			self.is_dummy_mode = True
		pylink.flushGetkeyQueue()
		self.setOfflineMode()
		self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(self._screenSize[0], self._screenSize[1]))
		self.sendMessage("link_event_filter = SACCADE")
		self.sendMessage("link_event_data = SACCADE")
		self.sendMessage("DISPLAY_COORDS 0 0 {0} {1}".format(self._screenSize[0], self._screenSize[1]))
		self.setSaccadeVelocityThreshold(SAC_VEL_THRESH)
		self.setAccelerationThreshold(SAC_ACC_THRESH)
		self.setMotionThreshold(SAC_MOTION_THRESH)


	def setup(self, fname="TEST", EDF_PATH="assets" + os.sep + "EDF"):
		pylink.openGraphics(self.screenSize)
		self.doTrackerSetup()
		self.openDataFile(fname + ".EDF")
		self.fname = fname
		self.EDF_PATH = EDF_PATH

	def start(self, tnum, samples=1, events=1, linkSamples=1, linkEvents=1):
		# ToDo: put some exceptions n here
		start = self.startRecording(samples, events, linkSamples, linkEvents)
		if start == 0:
			if self.__eye():
				self.sendMessage("TRIALID {0}".format(str(tnum)))
				self.sendMessage("TRIALSTART")
				self.sendMessage("SYNCTIME {0}".format('0.0'))
				return True
			else:
				return False
		else:
			return False

	def __eye(self):
		self.eye = self.eyeAvailable()
		if self.eye != -1:
			return True

	def sample(self):
		self.__currentSample = self.getNewestSample()
		print "Sample = {0}".format(repr(self.__currentSample))
		return True

	def stop(self):
		self.stopRecording()

	def drift(self, loc="center", events=1, samples=1, maxAttempts=1):
		if loc == "center":
			loc = self.screenc
		attempts = 1
		result = None
		print "Drift Correct Result: ".format(repr(result))
		try:
			if self.isTuplist(loc):
				if events:
					if samples:
						result = self.doDriftCorrect(loc[0], loc[1], 1, 1)
					else:
						result = self.doDriftCorrect(loc[0], loc[1], 1, 0)
				elif samples:
					result = self.doDriftCorrect(loc[0], loc[1], 0, 1)
				else:
					result = self.el.doDriftCorrect(loc[0], loc[1], 0, 0)
		except:
			print "****************DRIFT CORRECT EXCEPTION"
			return False
		# if attempts < maxAttempts:
		# 	return self.drift(loc, events, samples, maxAttempts-1)
		# else:
		# 	return False
		# if result == 27 and attempts < maxAttempts:
		# 	return self.drift(loc, events, samples, maxAttempts-1)
		# elif result == 27 and attempts > maxAttempts:
		# 	return False
		# else:
		# 	return True
		return True

	def gaze(self, eyeReq=None):
		if self.dummy_mode:
			return pygame.mouse.get_pos()
		if self.sample():
			if not eyeReq:
				rs = self.__currentSample.isRightSample()
				ls = self.__currentSample.isLeftSample()
				if self.eye == 1 and rs:
					return self.__currentSample.getRightEye().getGaze()
				if self.eye == 0 and ls:
					gaze = self.__currentSample.getLeftEye().getGaze()
					print gaze
					return gaze
				if self.eye == 2:
					return self.__currentSample.getLeftEye().getGaze()
			else:
				if eyeReq == 0:
					return self.__currentSample.getLeftEye().getGaze()
				if eyeReq == 1:
					return self.__currentSample.getLeftEye().getGaze()
		else:
			e = "Unable to collect a sample from the EyeLink."
			raise ValueError(e)

	def shutDownEyeLink(self):
		self.stopRecording()
		self.setOfflineMode()
		time.sleep(0.5)
		self.closeDataFile()  # tell eyelink to close_data_file()
		self.receiveDataFile(self.fname, self.EDF_PATH + self.fname)  # copy pa.EDF
		self.close()

	@abc.abstractmethod
	def listen(self, **kwargs):
		pass

	@property
	def screenSize(self):
		return self._screenSize

	@screenSize.setter
	def screenSize(self, screenSize):
		if type(screenSize).__name__ in ['tuple', 'list']:
			self._screenSize = screenSize
		else:
			raise ValueError("EyeLink.screenSize must be a tuple or a list; '{0}' passed.".format(type(screenSize)))

	@property
	def is_dummy_mode(self):
		return self.dummy_mode

	@is_dummy_mode.setter
	def is_dummy_mode(self, status):
		if type(status) is not bool:
			err_string = "Invalid argument provided for setting Eyelink.dummy_mode (boolean required, {0} passed."
			raise TypeError(err_string.format(type(status)))
		else:
			self.dummy_mode = True


class KeyMap(KlibBase):
	def __init__(self, name, keyNames=None, keyCodes=None, keyVals=None, anyKey=False):
		KlibBase.__init__(self)

		if type(name) is str:
			self.name = name
		else:
			e = self.eAttr("name", type(name), "str", False)
			raise TypeError(e)
		self.keyNames = None
		self.keyCodes = None
		self.keyVals = None

		# if all params are present, register the map; if none are, move on; if some are but not all throw an error
		if all(keyParam for keyParam in [keyNames, keyCodes, keyVals]):
			self.__register(keyNames, keyCodes, keyVals)
		elif any(keyParam for keyParam in [keyNames, keyCodes, keyVals]):
			e = "A KeyMap object must have either all or none of 'keyNames', 'keyCodes' and 'keyVals' present but one or more was missing."
			raise AttributeError(e)

		if anyKey:
			self.anyKey = anyKey
			self.keyCodes = []
			self.keyNames = []
			self.keyVals = []
		else:
			self.anyKey = False

	def __register(self, keyNames, keyCodes, keyVals):
		length = len(keyNames)
		if any(len(keyParam) != length for keyParam in [keyCodes, keyVals]):
			e = "Each tuple of a keymap must contain the same number of elements."
			raise TypeError(e)

		if any(type(keyParam) is not tuple for keyParam in [keyNames, keyCodes, keyVals]):
			e = "All arguments of a KeyMap object except 'name' must be tuples."
			raise TypeError(e)

		# names but be strings
		if all(type(name) == str for name in keyNames):
			if not self.keyNames:
				self.keyNames = keyNames
			else:
				self.keyNames.extend(keyNames)
		else:
			e = "All key names in the 'keyNames' argument of a KeyMap object must be of type 'str'."
			raise TypeError(e)

		# codes must be ints (ascii character equivalents)
		if all(type(code) == int for code in keyCodes):
			if not self.keyCodes:
				self.keyCodes = keyCodes
			else:
				self.keyCodes.extend(keyCodes)
		else:
			e = "All ascii codes in the 'keyCodes' argument of a KeyMap object must be of type 'int'."
			raise TypeError(e)

		# vals must be basic, single values ie. int, string or bool
		if all(type(i) in (int, str) for i in keyVals):
			if not self.keyVals:
				self.keyVals = keyVals
			else:
				self.keyVals.extend(keyVals)
		else:
			e = "All return values in the 'keyVals' argument of a KeyMap object must be one of type 'str' or 'int'."
			raise TypeError(e)

	def addKeys(self, keyNames, keyCodes, keyVals):
		if type(keyNames) is str and type(keyCodes) is int and type(keyVals) in (int, str):
			self.keyNames.append(keyNames)
			self.keyCodes.append(keyCodes)
			self.keyVals.append(keyVals)
		elif all(type(keyParam) is tuple for keyParam in [keyNames, keyCodes, keyVals]):
			self.__register(keyNames, keyCodes, keyVals)
		else:
			e = "One argument passed to addKey was of the wrong type; keyName was '{0}', keyCode was '{1}' and keyVal was '{2}'.".format(
				type(keyNames), type(keyCodes), type(keyVals))
			raise TypeError(e)

	def validate(self, keyCode):
		if type(keyCode) is int:
			if keyCode in self.keyCodes:
				return True
			elif self.anyKey:
				return True
			else:
				return False
		else:
			e = self.eAttr("keyCode", type(keyCode), "int", False)
			raise TypeError(e)

	def val(self, lookup):
		if type(lookup) is int:
			if lookup in self.keyCodes:
				ind = self.keyCodes.index(lookup)
				return self.keyVals[ind]
			elif self.anyKey:
				return "ANY_KEY_ACCEPTED"
			else:
				e = "The keyCode '{0}' was not found in the KeyMap object '{1}'".format(lookup, self.name)
				raise ValueError(e)

		if type(lookup) is str:
			if lookup in self.keyNames:
				for index, lookupe in enumerate(self.keyNames):
					return self.keyVals[index]
			else:
				e = "The keyName '{0}' was not found in the KeyMap object '{1}'".format(lookup, self.name)
				raise ValueError(e)
		e = self.eAttr("lookup", type(lookup), "int or str", False)
		raise TypeError(e)

	def validKeys(self):
		if "keyVals" in self.__dict__.keys():
			return ", ".join([str(name) for name in self.keyNames])
		elif self.anyKey:
			return "ANY_KEY_ACCEPTED"
		else:
			return None


class TextLayer(KlibBase):
	def __init__(self, appDimensions, screenDimensions, dpi, path=None, defaultQueryString=None,
	             defaultInputString=None, defaultLocations=None):
		KlibBase.__init__(self)
		self.fontSizes = {}
		self.strings = {}
		self.labels = {}
		self._antialias = True
		self.queue = {}
		self.appx = appDimensions[0]
		self.appy = appDimensions[1]
		self.screenx = screenDimensions[0]
		self.screeny = screenDimensions[1]
		self._defaultColor = (0, 0, 0)
		self._defaultBgColor = (255, 255, 255)
		self._defaultFontSize = None
		self._defaultFont = None
		self.alertColor = (255, 0, 0)
		self._defaultMessageDuration = 1
		self._defaultQueryString = defaultQueryString
		self._defaultInputString = defaultInputString

		if type(defaultLocations) is (tuple or list) and len(defaultLocations) == 2:
			self._defaultLocations = defaultLocations
		else:
			self._defaultLocations = {'query': None, 'input': None}

		if path is not None:
			self.fontsDir = path
		else:
			self.fontsDir = "/Library/Fonts/"

		if type(self.appx) is int and type(dpi) is int:
			self.__buildFontSizes(dpi)
			self.defaultFontSize = '18pt'
		else:
			raise ValueError("dpi must be an integer")

		self.defaultFont = 'Helvetica'

	def __buildFontSizes(self, dpi):
		sizeList = range(3, 96)
		self.fontSizes = {}
		for num in sizeList:
			key = str(num) + 'pt'
			self.fontSizes[key] = int(math.floor(1.0 / 72 * dpi * num))

	def __buildFonts(self, fonts):
		for font in fonts:
			self.addFont(font[0], font[1])
		return None

	def size(self, text):  # TODO: What is this function for?
		renderFont = pygame.font.Font(self.defaultFont, self._defaultFontSize)
		return renderFont.size()

	def renderText(self, string, font=None, fontSize=None, color=None, bgcolor=None):
		if color is None:
			if hasattr(self, 'defaultColor'):
				color = self.defaultColor
			else:
				color = (0, 0, 0)
		if font is None:
			font = self.defaultFont
		renderFont = self.renderFont(font=font, fontSize=fontSize)
		try:
			return renderFont.render(string, True, color)
		except:  # TODO: This exception is not true - nothing is being set or tried again
			raise GenWarning(
				"Call to renderText() failed; string, when rendered, is too large for screen. Setting wrap to True and trying again...")

	def addFont(self, font, fontFormat):
		if type(font) and type(fontFormat) is str:
			if self.fontsDir is not None:
				fontPath = os.path.join(self.fontsDir, font) + "." + fontFormat
				if os.path.isfile(fontPath):
					self.fonts[font] = self.fontsDir + font + "." + fontFormat
				else:
					print 'Path did not lead to file.'
					#TODO: Figure out what you meant to write here - this makes no sense: App.quit()
					pygame.quit()
					sys.exit(1)
			else:
				self.fonts[font] = font + "." + fontFormat
		else:
			pass #error handling

	@property
	def antialias(self):
		return self._antialias

	@antialias.setter
	@canonical
	def antialias(self, value):
		"""

		:param value:
		"""
		self._antialias = value

	def renderFont(self, font=None, fontSize=None):
		# process the fontSize argument or assign a default
		if fontSize is not None:
			if type(fontSize) is str:
				fontSize = self.fontSizes[fontSize]
			elif int(fontSize):
				pass #if it's an int, it's already correct, just need to be sure for error checking
			else:
				self.warn("")
		elif self._defaultFontSize:
			fontSize = self._defaultFontSize
		else:
			pass # throw error

		# process the font argument, or assign a default
		# if font is not None:
		# 	if type(font) is (tuple or list):
		# 		if self.fonts[font[0]]: #if trying to add a font that's been registered, just call it instead
		# 			font = self.fonts[font]
		# 		else: #otherwise, add it, then call it
		# 			self.addFont(font[0],font[1])
		# 			font = self.fonts[font]
		# 	elif self.fonts.get(font):
		# 		font = self.fonts[font]
		# 	else:
		# 		pass #throw error
		# elif self.defaultFont:
		# 		font = self.defaultFont
		# else:
		# 	pass # throw error
		if font is None:
			font = self.defaultFont
		return pygame.font.SysFont(font, fontSize)

	def setDefaultQuery(self, query):
		if type(query) is str:
			self.defaultQueryString = query

	@property
	def defaultLocations(self):
		return self._defaultLocations

	@defaultLocations.setter
	def defaultLocations(self, query, userInput):
		"""
		Set the default screen locations for prompts and responses
		:param query: Set the location of prompts and questions.
		:param userInput: Set the location for response entry.
		"""
		if type(query) is (tuple or list) and type(userInput) is (tuple or list):
			self._defaultLocations[query] = queryLocation
			self._defaultLocations[userInput] = inputLocation

	@property
	def defaultFont(self):
		return self._defaultFont

	def setDefaultInput(self, input):
		if type(input) is str:
			self._defaultInputString = input

	@property
	def defaultColor(self):
		"""


		:return:
		"""
		return self._defaultColor


	@defaultColor.setter
	def defaultColor(self, color):
		"""

		:param color:
		"""
		if type(color) is list:
			self._color = color

	@property
	def defaultBgColor(self):
		"""


		:return:
		"""
		return self._defaultBgColor

	@defaultBgColor.setter
	def defaultBgColor(self, color):
		"""

		:param color:
		"""
		if type(color) is list:
			self._defaultBgColor = color

	@property
	def defaultFontSize(self):
		return self._defaultFontSize

	@defaultFontSize.setter
	def defaultFontSize(self, size):
		"""

		:param size:
		"""
		if type(size) is str:
			self._defaultFontSize = self.fontSizes[size]
		elif type(size) is int:
			size = str(size) + "pt"
			self._defaultFontSize = self.fontSizes[size]


	@property
	def defaultFont(self):
		"""


		:return:
		"""
		return self._defaultFont

	@defaultFont.setter
	def defaultFont(self, font):
		"""

		:param font:
		:raise:
		"""
		self._defaultFont = font

	def wrappedText(self, text, delimiter=None, fontSize=None, font=None, wrapWidth=None):
		if font is not None:
			renderfont = font
		if fontSize is not None:
			renderfontSize = fontSize
		if delimiter is None:
			delimiter = "\n"
		try:
			if wrapWidth is not None:
				if type(wrapWidth) not in [int, float]:
					raise ValueError(
						"The config option 'wrapWidth' must be an int or a float; '{0}' was passed. Defaulting to 80% of app width.".format(
							repr(wrapWidth)))
				elif 1 > wrapWidth > 0: #assume it's a percentage of app width.
					wrapWidth = int(wrapWidth * self.appx)
				elif wrapWidth > self.appx or wrapWidth < 0:
					raise ValueError(
						"A wrapWidth of '{0}' was passed which is either too big to fit inside the app or else is negative (and must be positive). Defaulting to 80% of app width.")
				#having passed these tests, wrapWidth must now be correct
			else:
				wrapWidth = int(0.8 * self.appx)
		except ValueError as e:
			print self.warn(e, {'class': self.__class__.__name__, 'method': 'wrapText'})
			wrapWidth = int(0.8 * self.appx)
		renderFont = self.renderFont(renderfont, renderfontSize)
		paragraphs = None
		try:
			paragraphs = text.split(delimiter)
		except ValueError(
				"'{0}' was passed as a delimiter, should be a simple string that won't appear by accident (ie.'\\n')".format(
						repr(delimiter))) as e:
			print self.err(e, {'class': self.__class__.__name__, 'method': 'wrapText'})

		renderList = []
		lineHeight = 0
		# this loop was written by Mike Lawrence (mike.lwrnc@gmail.com) and then (slightly) modified for this program
		for p in paragraphs:
			wordList = p.split(' ')
			if len(wordList) == 1:
				renderList.append(wordList[0])
				if p != paragraphs[len(paragraphs) - 1]:
					renderList.append(' ')
					lineHeight += renderFont.get_linesize()
			else:
				processedWords = 0
				while processedWords < (len(wordList) - 1):
					currentLineStart = processedWords
					currentLineWidth = 0

					while (processedWords < (len(wordList) - 1)) and (currentLineWidth <= wrapWidth):
						processedWords += 1
						currentLineWidth = renderFont.size(' '.join(wordList[currentLineStart:(processedWords + 1)]))[0]
					if processedWords < (len(wordList) - 1):
						#last word went over, paragraph continues
						renderList.append(' '.join(wordList[currentLineStart:(processedWords - 1)]))
						lineHeight = lineHeight + renderFont.get_linesize()
						processedWords -= 1
					else:
						if currentLineWidth <= wrapWidth:
							#short final line
							renderList.append(' '.join(wordList[currentLineStart:(processedWords + 1)]))
							lineHeight = lineHeight + renderFont.get_linesize()
						else:
							#full line then 1 word final line
							renderList.append(' '.join(wordList[currentLineStart:processedWords]))
							lineHeight = lineHeight + renderFont.get_linesize()
							renderList.append(wordList[processedWords])
							lineHeight = lineHeight + renderFont.get_linesize()
						#at end of paragraph, check whether a inter-paragraph space should be added
						if p != paragraphs[len(paragraphs) - 1]:
							renderList.append(' ')
							lineHeight = lineHeight + renderFont.get_linesize()
		return renderList

	def addQuery(self, label, string):
		if type(label) is str and type(string) is str:
			self.labels[label] = string


class NullColumn(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg


class DbException(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg


class GenError(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg


class GenWarning(UserWarning):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg


#####################################################
#
# ASCII Character Code Reference for creating KeyMaps
#
# 32 = Space
# 33 = !
# 34 = "
# 35 = #
# 36 = $
# 37 = %
# 38 = &
# 39 = '
# 40 = (
# 41 = )
# 42 = *
# 43 = +
# 44 = ,
# 45 = -
# 46 = .
# 47 = /
# 48 = 0
# 49 = 1
# 50 = 2
# 51 = 3
# 52 = 4
# 53 = 5
# 54 = 6
# 55 = 7
# 56 = 8
# 57 = 9
# 58 = :
# 59 = ;
# 60 = <
# 61 = =
# 62 = >
# 63 = ?
# 64 = @
# 65 = A
# 66 = B
# 67 = C
# 68 = D
# 69 = E
# 70 = F
# 71 = G
# 72 = H
# 73 = I
# 74 = J
# 75 = K
# 76 = L
# 77 = M
# 78 = N
# 79 = O
# 80 = P
# 81 = Q
# 82 = R
# 83 = S
# 84 = T
# 85 = U
# 86 = V
# 87 = W
# 88 = X
# 89 = Y
# 90 = Z
# 91 = [
# 92 = \
# 93 = ]
# 94 = ^
# 95 = _
# 96 = `
# 97 = a
# 98 = b
# 99 = c
# 100 = d
# 101 = e
# 102 = f
# 103 = g
# 104 = h
# 105 = i
# 106 = j
# 107 = k
# 108 = l
# 109 = m
# 110 = n
# 111 = o
# 112 = p
# 113 = q
# 114 = r
# 115 = s
# 116 = t
# 117 = u
# 118 = v
# 119 = w
# 120 = x
# 121 = y
# 122 = z
# 123 = {
# 124 = |
# 125 = }
# 126 = ~
# 127 = Delete
#####################################################
