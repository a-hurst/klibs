__author__ = "Jonathan Mulle (this.impetus@gmail.com, @thisimpetus, about.me/this.impetus), 2013"
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
#import numpy

#this is a comment

#############
#  CLASSES
#############
class KlibBase():
	def __init__(self):
		pygame.init()
		pygame.mouse.set_visible(False)
		self.header = "***{0}"
		self.rex = Thesaurus(self.header)

	def absolutePosition(self, pos, destination):
		height = 0
		width = 0
		if type(destination) is pygame.Surface:
			height = destination.get_height()
			width = destination.get_width()
		locs ={
			'center': [width//2, height//2],
			'top-left':[0,0],
			'top-center':[width//2, 0],
			'top-right':[width, 0],
			'left-center':[0,height//2],
			'right-center':[0,height],
			'bottom-left':[0,height],
			'bottom-center':[width//2, height],
			'bottom-right':[width, height]
		}
		return locs[pos]


	def alertHeader(self, alertType = 'error'):
		return self.header.format(alertType.upper())

	def autoConfig(self, keys, config = None):
		for n in keys:
			if not n in config.keys():
				config[n] = 'default'
		return config

	def bliterate(self, targ, registration = 7, pos=[0,0], destination = None ):
		locations = ['center','top-left','top-right','bottom-left','bottom-right','top-center','left-center','right-center','bottom-center']
		w = targ.get_width()
		h = targ.get_height()

		registrations = {
						1:[0,-1.0*h],
						2:[-1.0*w/2.0,h],
						3:[-1.0*w,-1.0*h],
						4:[0,-1.0*h/2.0],
						5:[-1.0*w/2.0,-1.0*h/2.0],
						6:[-1.0*w,-1.0*h/2.0],
						7:[0,0],
						8:[-1.0*w/2.0, 0],
						9:[-1.0*w,0]
						}

		if ( 0 < registration & registration < 10):
			regx = int(registrations[registration][0])
			regy = int(registrations[registration][1])
		else:
			regx = int(registrations[7][0])
			regy = int(registrations[7][1])

		if type(pos) is str:
			if pos in locations:
				pos = self.absolutePosition(pos, destination)
			else:
				raise Generror("Value '{0'} was passed for 'pos' but this was not a key in the locations dict.".format(repr(pos)))

		if type(pos) is tuple or type(pos) is list:
			regRefx = int(pos[0]) + int(regx)
			regRefy = int(pos[1]) + int(regy)
		else:
			raise Generror("Value of parameter 'pos' was neither a valid string nor a list or tupple of length 2; value '{0}' of type '{1}' passed.".format(repr(pos), type(pos)))
		if type(destination) is pygame.Surface:
			destination.blit(targ, (regRefx, regRefy))
		else:
			try:
				self.screen.blit(targ, (regRefx, regRefy))
			except:
				raise Generror("A surface was not provided on which to blit the target, nor was the App.screen available.")

	def equiv(self, key, syn):
		resp = self.rex.inspect(key, syn)
		return resp

	def err(self, errorString = '', config = {'class':'default', 'method':'default', 'alertType':'default'}, kill = False):
		alertType = 'error'
		stackBack = -2 #add one for every function call executed between the error and calling KlibBase.err()
		localTrace = ''
		if type(config) is list or type(config) is tuple:
			config = {'class':config[0],'method':config[1]}
		configkeys = ('class','method', 'alertType')
		config = self.autoConfig(configkeys, config)
		if config['alertType'] != 'default':
			#future programs may have more than two types of alert, but for now, it's a binary choice or err or warn
			alertType = config['alertType']
			stackBack = -3
		if config['class'] != 'default':
			if config['method'] != 'default':
				localTrace = "Class: {0}\n\tMethod: {1}(): ".format(config['class'],config['method'])
			else:
				localTrace = "Class: {0}\n\t: ".format(config['class'])
		elif config['method'] != 'default':
			localTrace = "\t{0}(): ".format(config['method'])
		trace = traceback.extract_stack()[stackBack]
		fileName = ntpath.basename(trace[0])
		line = trace[1]
		if self.equiv('true', kill):
			print "{0} ON LINE '{1}' OF '{2}'***\n{3}{4} Exiting program...\n".format(self.alertHeader(alertType), line, fileName, localTrace, errorString)
			self.quit()
		else:
			print "{0} ON LINE 1{1}' OF '{2}'***\n{3}{4}\n".format(self.alertHeader(alertType), line, fileName, localTrace, errorString)

	def ln(self):
		return  traceback.extract_stack()[-2][1]

	def peak(self, v1, v2):
		if v1 > v2:
			return v1
		else:
			return v2

	def prettyJoin(self, array, config = {'prepend':'default',
										  'afterFirst':'default',
										  'beforeLast':'default',
										  'eachN':'default',
										  'whitespace':'default',
										  'append':'default',
										  'delimiter':'default',
										  'delimitBehavior':'default',
										  'delimitBehaviour':'default'}):
		configKeys = ['prepend','afterFirst','beforeLast','eachN', 'whitespace','append','delimiter','delimitBehavior','delimitBehaviour']
		config = self.autoConfig(configKeys, config)
		msg = "Trying to use  a .join() call instead." # gets repeated in several 'raise' statements, easier to reuse
		if config['delimiter'] == 'default':
			config['delimiter'] = "'"
		#catch British vs American spellings of 'behavior'
		if config['delimitBehaviour'] != 'default':
			config['delimitBehavior'] = config['delimitBehaviour']
		try:
			if config['whitespace'] in ('default',1,'single','true','True',True):
				config['whitespace'] = ' '
			elif config['whitespace'] in (2,'double'):
				config['whitespace'] ='  '
			elif config['whitespace'] in ("tab"):
				config['whitespace'] = '	'
			elif config['whitespace'] in (0,None,'none','None','false','False',False):
				config['whitespace'] = ''
			elif type(config['whitespace']) is int:
				ws = ''
				for n in range(config['whitespace']):
					ws += ' '
				config['whitespace'] = ws
			else:
				raise Generror("Invalid value of '{0}' passed for config['whitespace']. Defaulting to single-space.".format(config['whitespace']))
		except Generror as e:
			print self.warn(e, {'class':'KlibBase','method':'prettyJoin'})
			config['whitespace'] = ' '
		output = ''
		if config['prepend'] != 'default':
			output = config['prepend']
		for n in range(len(array)):
			#if after first iteration, print whitespace
			if n > 1:
				output = output + config['whitespace']
			#if beforeLast is set, print it and add whitespace
			if (n == (len(array)-1)) and (config['beforeLast'] != 'default'):
				output = output + config['beforeLast'] + config['whitespace']
			# if eachN is set and the iterator is divisible by N, print an eachN and add whitespace
			if config['eachN'] is (list or tuple):
				if len(config['eachN']) == 2:
					if type(config['eachN'][0]) is int:
						if n % config['eachN'] == 0:
							output = output + str(config['eachN'][1]) + config['whiteSpace']
					else:
						raise Generror("Klib.prettyJoin() config parameter 'eachN[0]' must be an int, '{0}' {1} passed. {2}".format(config['eachN'], type(config['eachN'], msg)))
				else:
					raise Generror("Klib.prettyJoin() config parameter 'eachN' must be a tuple or list of length 2, but {0} of length '{1}' passed. {2}".format(type(config['eachN']),len(config['eachN']), msg))
			elif config['eachN'] != 'default':
				raise Generror("Klib.prettyJoin() config parameter 'eachN' must be a list or tuple, '{0}' passed. {1}".format(type(config['eachN']), msg))
			# if delimiter is set to default or wrap, print a delimiter before the array item
			if config['delimitBehavior'] in ('wrap', 'default'):
				output = output + config['delimiter']
			# finally print the array item
			output = output + str(array[n]) + config['delimiter'] + config['whitespace']
			# if afterFirst is set, print it and add whitespace
			if (n == 0) and (config['afterFirst'] != 'default'):
				output = output + config['afterFirst'] + config['whitespace']
		if config['append'] != 'default':
			output = output + config['append']

		return output

	def quit(self):
		pygame.quit()
		sys.exit()

	def isTuplist(self, var):
		if type(var) is tuple:
			return True
		if type(var) is list:
			return True
		return False

	def warn(self, errorString = '', config = {'class':'default', 'method':'default'}, kill = False ):
		if self.isTuplist(config):
			config = {'class':config[0], 'method':config[1]}
		configkeys = ('class', 'method')
		config = self.autoConfig(configkeys, config)
		config['alertType'] = 'warning'
		return self.err(errorString, config, kill)


class App(KlibBase):
	def __init__(self, viewRules, isCRT = True, scale = 90):
		KlibBase.__init__(self)
		if (isCRT == True):
			self.dpi = 75
		else:
			self.dpi = 96
		self.__screenParams(viewRules)
		self.pal = Palette() #required by subsequent vars in app, hence breaking alphabetical order
		self.appy = int( math.floor( (scale / 100.0 * self.screeny) ) ) 							# app happens to be a square, may change later
		self.appx = self.appy																		# screen width > screen height so height is a bottleneck
		self.appxy = [self.appx, self.appy]
		self.appx0 = (self.screenx - self.appx)//2
		self.appy0 = (self.screeny - self.appy)//2
		self.autoExempt = True
		self.blocks = 1  #50
		self.blockLogs = {'incorrect':0,'correct':0, 'notarget':0, 'timeout':0, 'trials':0}
		self.blockLogTemplate = self.blockLogs.copy()
		self.blockAccuracy = 0
		self.blockCount = 0

		self.boxl = int(math.floor(self.appy / 3.0)) 												# box length should be 1/3 of app height minus stroke width
		self.boxrect = pygame.Rect( (0,0), (self.boxl, self.boxl) )
		self.bstroke = self.__setStroke()
		 															# for every 500px in app height, increase box stroke by 1
		self.computeAccuracyByResponse = True
		self.computeAccuracyByTimeout = True

		self.crossState = 'On'

		self.db = Database('nback_test',('schema', True) )

		self.defaultListenInterval = 0.5
		self.exemptions = {'incorrect':False, 'correct':False, 'notarget':False, 'timeout':False, 'trials':True}
		self.keyMaps = {'default':['SPACEBAR',32,1], '*':['*',-1,True]}
		self.locations = {
						'center':self.screenc,
						'top-left':[self.appx0,self.appy0],
						'top-right':[self.appx0+self.appx, self.appy0],
						'bottom-left':[self.appx0, self.appy0+self.appy],
						'bottom-right':[self.appx0+self.appx, self.appy0+self.appy]
						}

		self.paths = {'font':'default','image':'assets/img','asset':'assets'}

		self.participantId = -1

		self.paused = False

		self.practiceBlocks = False
		self.practicing = False
		self.responseInterval = 0
		self.soa = 0.5 #I think something *like* this should exist in the final framework, but perhaps as a member of a dict with most or all possible intervals listed
		self.startTime = None #see above, maybe? I'm not sure if every trial of every program will only ever have one "start time". If not, then this is insufficient
		self.testing = False
		self.text = TextLayer(self.appxy, self.screenxy, self.dpi, {'path':self.paths['font'],
																	'fonts':[('Arial','ttf'),('Arial Black','ttf')]
																	}
		)
		self.token = self.__buildToken()
		self.trialCount = 0
		self.trialsPerBlock = 20 + self.nRank
		self.trialsPerPracticeBlock = 'default'
		self.trialStart = None

		#set up columns in the database equal to the current nRank
		self.__addNCols(self.nRank, True)


	def __addNCols(self, count, nRankInc = False):
		for n in range(1,count+1):
			try:
				if not nRankInc :
					n += self.nRank
				query = "ALTER TABLE `trials` ADD COLUMN `N{0}` INTEGER".format(n)
				self.db.cursor.executescript(query)
				self.db.db.commit()
			except sqlite3.Error as e:
				self.warn("The database returned an error, '{0}'".format(e.args[0]),{'class':'App','method':'__addNCols'})
		self.db.db.commit()
		self.db.buildTableSchemas()

	def __buildToken(self):
		#this works around a bug in Python 2.7.2 and Pygame whereby Pygame will only import a .bmp's
		try:
			tokenf = pygame.image.load("assets/img/token.png")
		except:
			tokenf = pygame.image.load("assets/img/token.bmp")
		token = pygame.transform.smoothscale( tokenf, (int(0.6*self.boxl),int(0.6*self.boxl)) )
		return token

	def __demote(self):
		if self.nRank > 1:
			self.nRank -= 1

	def __getScreenRatio(self):
		dividend = round(float(self.screenx)/float(self.screeny), 3)
		if dividend == 1.333:
			return "4:3"
		elif dividend == 1.778:
			return "16:9"
		elif dividend == 1.6:
			return "16:10"
		else:
			return "X:Y"

	def __generateTrials(self, practice = False):
		trials = []
		matchCount = 0
		trialCount = 0
		if not practice :
			trialCount = self.trialsPerBlock
		else:
			trialCount = self.trialsPerPracticeBlock

		for n in range(trialCount):
			loc = None
			while loc is None :
				l = random.randrange(1,10,1)
				if l == 5:
					pass
				else:
					loc = l
		n = self.nRank
		while n <= (len(trials)):
			if trials[n] == trials[n-self.nRank]:
				match += 1
			n += 1
		if matchCount > 0:
			return trials
		else:
			return self.__generateTrials()

	def __logTrial(self, nloc, resp):
		self.db.log('block_num', self.blockCount)
		self.db.log('trial_num',self.trialCount - self.nRank)
		self.db.log('practicing', self.practicing)
		self.db.log('participant_id', self.participantId)
		self.db.log('current_loc', nloc)
		self.db.log('nrank', self.nRank)
		self.db.log('rt', resp['rt'])
		#should N1...Nnrank exist, retrieve & record it
		for n in range(1,self.nRank+1):
			self.db.log("N"+str(n),self.nBackLog[n-1])
		responseAccuracy = -1
		#next line is VERY handy for debugging, leave in until dead sure of accuracy
		#print "Trial #{0}:\n\tblockLogs[trials]: {1}\n\tnBackLog: {2}\n\tresp: {3}\n\tthisN: {4}\n\tnBack: {5}\n".format(self.trialCount,self.blockLogs['trials'], repr(self.nBackLog), resp, nloc, self.nBack)
		if self.nBack:
			if (nloc == self.nBack):
				if resp == 1:
					responseAccuracy = 1
					self.blockLogs['correct'] += 1
				else:
					responseAccuracy = 0
					self.blockLogs['timeout'] += 1
			else:
				if resp == 1:
					responseAccuracy = 0
					self.blockLogs['incorrect'] += 1
				else:
					responseAccuracy = 1
					self.blockLogs['notarget'] += 1
		self.blockLogs['trials'] += 1
		self.nBackLog.insert(0,nloc)
		self.nBackLog.pop()
		self.db.log('response_accuracy', responseAccuracy)
		self.db.insert()

	def __loadKeyMap(self, keyMap):
		if type(keyMap) is str:
			try:
				if not keyMap in self.keyMaps.keys():
					raise Generror("No keyMap named '{0}' was found in App.keyMaps. Exiting program...".format(keyMap))
				else:
					return self.keyMaps[keyMap]
			except Generror as e:
				print self.err(e, {'class':'App','method':'listen'})
				self.quit()
		elif type(keyMap) is dict:
			for key in keyMap.keys():
				try:
					if (type(keyMap[key]) is (list or tuple)) and (len(keyMap[key]) == 3):
						self.keyMaps[key] = keyMap[key]
						return keyMap[key]
					else:
						raise Generror("Parsing the keyMap failed; the dict key '{0}' wasn't paired with a tuple or list of length 3. Exiting program...".format(key))
				except Generror as e:
					print self.err(e, {'class':'App','method':'listen'})
					self.quit()
		else:
			raise Generror("Parsing the keyMap failed for unknown reasons. Ensure that all its elements conform to convention.")

	def __promote(self):
		if self.nRank == self.nReached:
			self.nReached += 1
			self.__addNCols(1)
			if self.trialCount > 0:
				for n in range(self.trialCount):
					query = "UPDATE `trials` SET `{0}` = -1 WHERE `participant_id` = {1} AND `trial_num`={2}".format('N'+str(self.nRank), self.participantId, self.trialCount)
					self.db.cursor.execute(query)
				self.db.db.commit()
		self.nRank += 1

	def __setStroke(self):
		stroke =  int(1 * math.floor(self.appy / 500.0))
		if (stroke < 1):
			stroke = 1
		return stroke

	def __screenParams(self, viewDistance):
		self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWACCEL | pygame.HWSURFACE )
		screen = self.screen.get_size()
		self.screenx = int(screen[0])
		self.screeny = int(screen[1])
		self.screenw = self.dpi
		self.screenxy = [self.screenx, self.screeny]
		self.ratio = self.__getScreenRatio()
		self.screenc = [self.screenx/2, self.screeny/2]
		self.diag_px = int(math.sqrt(self.screenx * self.screenx + self.screeny * self.screeny))	# pythagoras yo


		# calculate physical size of screen; screenModes[0] = largest resolution current monitor can display
		screenModes = pygame.display.list_modes()
		self.physicalScreenx = screenModes[0][0]/self.dpi
		self.physicalScreeny = screenModes[0][1]/self.dpi

		# interpret viewDistance
		try:
			if self.isTuplist(viewDistance):
				if type(viewDistance[0]) is int:
					if self.equiv('inch',viewDistance[1]):
						self.viewDistance = viewDistance[0]
						self.viewUnit = 'inch'
					elif self.equiv('cm',viewDistance[1]):
						self.viewDistance = viewDistance[0]
						self.viewUnit = 'cm'
						#convert physical screen measurements to cm
						self.physicalScreenx *= 2.55
						self.physicalScreeny *= 2.55
					else:
						raise Generror("viewRule must be int or a tuple/list containing [int,str]; '{0}' of type '{1}' passed.".format(repr(viewDistance), type(viewDistance)))
				else:
					raise Generror("viewRule must be int or a tuple/list containing [int,str]; '{0}' of type '{1}' passed.".format(repr(viewDistance), type(viewDistance)))
			elif type(viewDistance) is int:
				self.viewDistance = viewDistance
				self.viewUnit = 'inch'
			else:
				raise Generror("viewRule must be int or a tuple/list containing [int,str]; '{0}' of type '{1}' passed.".format(repr(viewDistance), type(viewDistance)))
		except Generror as e:
			self.err(e, ('App','__init__'), True)

		self.screenDegx = math.degrees(math.atan((self.physicalScreenx/2.0)/self.viewDistance)*2)
		self.pixelsPerDegree = self.screenx/self.screenDegx
		self.ppd = self.pixelsPerDegree #alias for convenience

    def __initEyeLink():
        from pylink import *
        try:----$
                EYELINK = EyeLink()--$
        except:-$
                print "Unable to contact EyeLink"$
                quit()$
        flushGetkeyQueue()-$
        EYELINK.setOfflineMode()-$
        EYELINK.sendCommand("screen_pixel_coords = 0 0 %d %d" %(scn_size[0], scn_size[1]))-$
        EYELINK.sendMessage("link_event_filter = SACCADE")-$
        EYELINK.sendMessage("link_event_data = SACCADE")-$
        EYELINK.sendMessage("DISPLAY_COORDS 0 0 %d %d" %(scn_size[0], scn_size[1]))$
        EYELINK.setSaccadeVelocityThreshold(SAC_VEL_THRESH)$
        EYELINK.setAccelerationThreshold(SAC_ACC_THRESH)$
        EYELINK.setMotionThreshold(SAC_MOTION_THRESH)$
        this.eyelink = EYELINK

    def alert(self, alertString, urgent = False):
        text = None
        if not urgent:
            return self.message(alertString, {'color':self.pal.alert,
                                       'location':'top-right',
                                       'registration':9,
                                       'return':'flip',
                                    }
                        )
        else:
            text = self.message(alertString, {'color':self.pal.white,
                                              'location':self.screenc,
                                              'registration':5,
                                              'fontSize':self.text.defaultFontSize * 2,
                                              'return':'return'
                                            }
                                )
        width = int(math.ceil(text.get_width()*1.2))
        height = int(math.ceil(text.get_height()*1.2))
        bounds = pygame.Surface((width, height))
        bounds.fill((0,0,0))
        bounds.set_alpha(150)
        self.bliterate(bounds, 5, self.screenc)
        self.bliterate(text, 5, self.screenc)
        self.flip()

	def autoExempt(self, state):
		if state == 'on' or True:
			self.autoExempt = True
		if state == 'off' or False:
			self.autoExempt = False

	def block(self, blockNum):
		self.blockLogs = self.blockLogTemplate.copy()
		self.blockCount = blockNum
		self.nBackLog = [-1,]*self.nRank
		if self.practicing :
			for trialNum in range(self.trialsPerPracticeBlock + self.nRank):
				self.trial(trialNum,True)
		else:
			for trialNum in range(self.trialsPerBlock + self.nRank):
				self.trial(trialNum)
		self.performanceEval()
		if blockNum+1 < self.blocks:
			self.block_break()

	def blockBreak(self, message ='default', isPath = False):
		default = "You've completed block {0} of {1}. When you're ready to continue, press any key.".format(self.blockCount+1, self.blocks)
		if isPath:
			try:
				pathExists = os.path.exists(message)
				if pathExists:
					with open (message, "r") as f:
						message = f.read().replace("\n",'')
				else:
					raise Generror("'isPath' parameter was True but '{0}' was not a valid path. Using default message".format(message))
			except Generror as e:
				self.warn(e, ('App','blockBreak'))
				message = default
		if self.testing:
			pass
		else:
			if type(message) is str:
				if message == 'default':
					message = default
				self.message(message,{'fullscreen':True,'return':'flip','location':'center','registration':5})
				self.listen('*','*')

	def crossOn(self):
		self.crossState = 'On'

	def crossOff(self):
		self.crossState = 'Off'

	def crossFlash(self):
		self.crossState = 'Flash'

	def	demograph(self):
		self.db.initEntry('participants',{'instanceName':'ptcp', 'setCurrent':True})
		nameQuery = self.query("What is your full name, banner number or e-mail address? Your answer will be encrypted and cannot be read later.", {'password':True})
		nameHash = hashlib.sha1(nameQuery)
		name = nameHash.hexdigest()
		self.db.log('userhash',name)

		if self.db.requireUnique(name, 'userhash', 'participants'): #names must be unique; returns True is unique, False otherwise
			self.db.log('gender', self.query("What is your gender? Answer with:  (m)ale,(f)emale or (o)ther)",{'accepted':['m','M','f','F','o','O']}))
			self.db.log('handedness', self.query('Are right-handed, left-handed, or ambidextrous? Answer with (r)ight, (l)eft or (a)mbidextrous).', {'accepted':('r','R','l','L','a','A')}))
			self.db.log('age', self.query('What is  your age?', {'returnType':'int'}))
			self.db.log('created', self.now())
			self.db.log('modified', self.now())
			try:
				self.db.insert()
			except Generror as e:
				print e
			try:
				self.db.cursor.execute("SELECT `id` FROM `participants` WHERE `userhash` = '"+name+"'")
				result = self.db.cursor.fetchall()
				self.participantId = result[0][0]
			except:
				print self.err()+"App\n\tdemograph(): problem was encountered when retrieving participant id."
				self.quit()
		else:
			retry = self.query('That participant identifier has already been used. Do you wish to try another? (y/n) ')
			if retry == 'y':
				self.demograph()
			else:
				self.sf()
				self.message("Thanks for participating!", {'location':self.screenc})
				pygame.display.flip()
				time.sleep(1)
				self.quit()

	def experimentSchema(self, blocks, trialsPerBlock, practiceBlocks, trialsPerPracticeBlock = 'default'):
		try:
			if type(blocks) and type(trialsPerBlock) and type(practiceBlocks) is int:
				self.blocks = blocks
				self.trialsPerBlock = trialsPerBlock
				self.practiceBlocks = practiceBlocks
			else:
				raise Generror("All parameters must be of type 'int'.")

			if trialsPerPracticeBlock != 'default':
				if type(trialsPerPracticeBlock) is int:
					self.trialsPerPracticeBlock = trialsPerPracticeBlock
				else:
					raise Generror("All parameters must be of type 'int'.")
			else:
				self.trialsPerPracticeBlock = trialsPerBlock
		except Generror as e:
			self.err(e, {'class':'App','method':'experimentSchema'}, True)


	def exempt(self, index, state = True):
		if index in self.exemptions.keys():
			if state == 'on' or True:
				self.exemptions[index] = True
			if state == 'off' or False:
				self.exemptions[index] = False

	def flip(self, duration = 0):
		pygame.display.flip()
		if duration == 0:
			return None
		try:
			if type(duration) is int:
				if duration > 0:
					start = time.time()
					while time.time() - start < duration:
						self.overWatch()
				else:
					raise Generror("Duration must be a positive number, '{0}' was passed".format(duration))
			else:
				raise Generror("Duration must be expressed as an integer, '{0}' was passed.".format(type(duration)))
		except Generror as e:
			print self.err(e, {'class':'App', 'method':'flip'})

	def gridWiz(self, index = None):
		if index:
			return self.grid.get(index)
		else:
			return self.grid.grid

	def keyMapper(self, keyMap):
		keyMapList = []
		responseKeys = []
		responseVals = {}
		responseKeyNames = {}
		try:
			if type(keyMap) is str:
				keyMapList.append(self.__loadKeyMap(keyMap))
			else:
				raise Generror("There was no key '{0}' in App.keyMaps; add it before calling or pass a dict to listen formatted thus:  {'mapName':(keyName,keyVal,returnVal)}. Exiting program...")

			if type(keyMap) is (tuple or list):
				for km in keyMap:
					if type(km) is str:
						keyMapList.append(self.__loadKeyMap(km))
					elif ( type(km) is (list or tuple)) and (len(km) == 3):
						keyMapList.append(km)
					elif type(km) is dict:
						for i in km:
							try:
								keyMapList.append(self.__loadKeyMap(km))
							except Generror as e:
								print self.err(e, {'class':'App', 'method':'listen'})
								self.quit()
					else:
						raise Generror("Parsing the keyMap failed; an item it contained was neither a string for a tuple or list of length 3. Exiting program...")
		except Generror as e:
			print self.err(e, {'class':'App', 'method':'listen'})
			self.quit()
		try:
			for key in keyMapList:
				try:
					responseKeys.append(int(key[1]))
					responseVals[str(key[1])] = str(key[2])
					responseKeyNames[str(key[1])] = str(key[0])
				except Exception as e:
					raise Generror("Something went wrong when parsing the keyMap; make sure it is formatted as per convention. Exiting program...")
		except Generror as e:
			print self.err(e, {'class':'App','method':'keyMapper'})
			self.quit()
		return {'names':responseKeyNames, 'keys':responseKeys, 'vals':responseVals}

	def lastBack(self):
		return self.nBackLog[self.nRank-1]

	def listen(self, keyMap = 'default', interval = 'default', config ={'wrongKey':'default',
																		'wrongKeyMessage':'default',
																		'timeOut':'default',
																		'timeOutMessage':'default',
																		'responseCount':'default',
																		'responseMap':'default'
																		}):
		# TODO: have customizable wrong key & time-out behaviors (ie. utilize the config dict)
		#enter with a clean event queue
		pygame.event.clear()
		self.flip()

		#process keymap (ie. establish which keys to listen for & how to respond)
		keyMap = self.keyMapper(keyMap)

		#establish an interval for which to listen()
		if interval == 'default':
			interval = self.defaultListenInterval
		elif interval == '*':
			interval = 999999 #an approximation of 'forever' since '*' is not an integer (see the while loop below)

		response = {'response':'', 'rt':-1.0} #TODO:make this customizable
		wrongKey = False
		#establish time reference (ie. now or from some point before the call to listen() )
		if self.startTime is None :
			startTime = time.time()
		else:
			startTime = self.startTime

		#listen!
		while (time.time() - startTime) < interval:
			pygame.event.pump()
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					response['rt'] = time.time() - startTime
					if response['response'] == '': # so as to only record a response once per call to listen()
						key = event.key
						if key in keyMap['keys']: # -1 is assigned when a keymap of '*' is entered ie. -1 = 'any key'
							response['response'] = keyMap['vals'][str(key)]
						else:
							wrongKey = True
				if event.type == pygame.KEYUP: # KEYDOWN is bad when listening for mod keys b/c the mod is itself also a key
					metaEvent = self.overWatch(event) # ensure the 'wrong key' wasn't a call to quit or pause
					if keyMap['keys'][0] == -1:
							response['response'] = keyMap['vals']['-1'] #str of key is always used as the dict index for assigned return values
							if interval == 999999: #allows the possibility of an 'any key' response within a finite interval
								return True
					if not metaEvent and wrongKey == True: # flash an error for an actual wrong key
						self.alert("Please respond using 'SPACEBAR'.", True)
						wrongKey = False
		if response['response'] == '':
			response['response'] = -1
		return response




	def memoryLoad(self):
		if self.nRank == 1:
			return self.nBackLog[0]
		else:
			return ''.join(self.nBackLog[0:(self.nRank-1)])

	def message(self, message, config={'font':'default',
									   'fontSize':'default',
									   'color':'default',
									   'bgcolor':'default',
									   'bgIsKey':'default',
									   'location':'default',
									   'registration':'default',
									   'wrap':'default',
									   'wrapWidth':'default',
									   'delimiter':'default',
									   'return':'default',
									   'fullscreen':'default'
										}):
		originalConfig = config.copy()
		config = self.autoConfig(('font','fontSize','color','bgcolor','bgIsKey','location','registration','wrap','wrapWidth','delimiter','return','fullscreen'), config)
		renderConfig = {}
		messageSurface = None # unless wrap is true, will remain empty

		####
		#RENDERCONFIG: extract those config options needed for pygame.font.FONT.render() (called later)
		####
		#----RENDERCONFIG: font
		try:
			if config['font'] == 'default':
				if self.text.defaultFont:
					renderConfig['font'] = self.text.defaultFont
				else:
					raise Generror("Cannot render text; no font passed and no default font has been set.")
			else:
				renderConfig['font'] = config['font']
		except Generror as e:
			self.err(e, ('App','message'), True)

		#----RENDERCONFIG: fontSize
		try:
			if config['fontSize'] == 'default':
				if self.text.defaultFontSize:
					renderConfig['fontSize'] = self.text.defaultFontSize
				else:
					raise Genwarning("No font size was passed, and no default is set. Using 14pt as a standard.")
			else:
				renderConfig['fontSize'] = config['fontSize']
		except Genwarning as e:
			renderConfig['fontSize'] = self.text.size('14pt')
			self.warn(e,('App','message'))

		#----RENDERCONFIG: color
		try:
			if config['color'] == 'default':
				if self.text.defaultColor:
					renderConfig['color'] = self.text.defaultColor
				else:
					raise Genwarning("No color passed and no default color set. Using app.palette.black as default.")
			else:
				renderConfig['color'] = config['color']
		except Genwarning as e:
			renderConfig['color'] = self.pal.black
			self.warn(e, ('App','message'))

		#----RENDERCONFIG: bgcolor
		try:
			if config['bgcolor'] == 'default':
				if self.text.defaultColor:
					renderConfig['bgcolor'] = self.text.defaultBgColor
				else:
					raise Genwarning("No background color passed and no default background color set. Using app.palette.white as default.")
			else:
				renderConfig['bgcolor'] = config['bgcolor']
		except Genwarning as e:
			renderConfig['bgcolor'] = self.pal.white
			self.warn(e, ('App','message'))

		#wrapping detection and processing
		if self.equiv('true',config['wrap']):
			message = self.text.wrappedText(message,config)
			lineSurfaces = []
			messageHeight = 0
			messageWidth = 0
			for line in message:
				try:
					lineSurface = self.text.renderText(line, renderConfig)
				except Generror as e:
					self.warn(e,('App','message'))
				lineSurfaces.append((lineSurface, [0,messageHeight]))
				messageWidth = self.peak(lineSurface.get_width(), messageWidth)
				messageHeight = messageHeight + lineSurface.get_height()
			messageSurface = pygame.Surface((messageWidth, messageHeight))
			messageSurface.fill(renderConfig['bgcolor'])
			if self.equiv('true', config['bgIsKey']):
				print "here"
				messageSurface.set_colorkey(renderConfig['bgcolor'])
			for lsurf in lineSurfaces:
				self.bliterate(lsurf[0],7,lsurf[1],messageSurface )

		#process location, infer if need be; failure here is considered fatal
		try:
			if self.isTuplist(config['location']):
				if len(config['location']) == 2:
					pass #just a reasonably thorough test for a correctish value
				else:
					raise Generror("Coordinate locations must be either a tuple or list of length 2; '{0}' passed".format(repr(config['location'])))
			elif config['location'] == 'default':
				# By Default: wrapped text blits to screen center; single-lines blit to top-left with a padding = fontSize
				if self.equiv('true',config['wrap']):
					config['location'] = self.screenc
				else:
					xOffset = (self.screenx - self.appx)//2 + renderConfig['fontSize']
					yOffset = (self.screeny - self.appy)//2 + renderConfig['fontSize']
					config['location'] = [xOffset,yOffset]
			elif type(config['location']) is str:
				try:
					config['location'] = self.absolutePosition(config['location'], self.screen)
				except:
					raise Generror("The given location, '{0}' wasn't found in the App's list of relative locations.".format(config['location']))
			else:
				raise Generror("The location '{0}' could not be interpreted by the App, please use a tuple/list of coordinates or else a relative keyword (ie. 'center')".format(repr(config['location'])))
		except Generror as e:
			self.err(e, ('App','message'), True)

		#process blit registration
		if config['registration'] == 'default':
			if self.equiv('true', config['wrap']):
				config['registration'] = 5
			else:
				config['registration'] = 7

		#Two return options; flip immediately and return True or return the prepared surface and nothing else
		#----return = flip
		if config['return'] in ('default','blit','flip'):
			if self.equiv('true',config['fullscreen']):
				#TODO:make it possible to sf() with a passed or preset color
				self.sf()
			if self.equiv('true',config['wrap']):
				self.bliterate(messageSurface, 5, self.screenc)
			else:
				try:
					messageSurface = self.text.renderText(message, renderConfig)
					if messageSurface.get_width() > self.appx:
						raise Genwarning("The message was too long to fit on one line, setting config['wrap'] to True and trying again...")
				except Genwarning as e:
					self.warn(e, {'class':'App','method':'message'})
					originalConfig['wrap'] = True
					return self.message(message, originalConfig)
				self.bliterate(messageSurface, config['registration'], config['location'] )
			if config['return'] == 'flip':
				self.flip()
				return True

		#----return = return/true
		if config['return'] == 'return' or self.equiv('true', config['return']):
			if self.equiv('true',config['wrap']):
				#by this point, wrapped messages have, by necessity, already been rendered
				return messageSurface
			else:
				try:
					messageSurface = self.text.renderText(message, renderConfig)
					#check for single lines that extend beyond the app area and wrap if need be
					if messageSurface.get_width() > self.appx:
						raise Genwarning("The message was too long to fit on one line, setting config['wrap'] to True and trying again...")
					else:
						return messageSurface
				except Genwarning as e:
					self.warn(e, {'class':'App','method':'message'})
					config['wrap'] = True
					return self.message(message, config)
		#if return = flip/blit/default, return True in case program logic depends on confirming the blit
		return True

	def nextBack(self):
		nextBack = random.randrange(1,10,1)
		if nextBack == 5:
			return self.nextBack()
		if self.blockLogs['trials'] >= self.nRank: # = included b/c backLogs['trials'] does ++ at the *end* of the def.
			nBack = self.nBackLog[self.nRank-1]
		else:
			nBack = None
		if nBack:
			if nBack == nextBack:
				self.nBack = [nextBack, True]
			else:
				self.nBack = [nextBack, False]
		else:
			self.nBack = None
		return nextBack

	def now(self):
		today = datetime.datetime
		return today.now().strftime("%Y-%m-%d %H:%M:%S")

	def nStartRank(self, rank):
		try:
			if type(rank) is int:
				self.nRank = rank
				self.__addNCols(rank, True)
			else:
				raise Generror("Parameter 'rank' must be of type 'int'; value '{0}' of type '{1}' passed. Defaulting to Rank 1.".format(repr(rank), type(rank)))
		except Generror as e:
			print self.warn(e, {'class':'App', 'method':'startingRank'})
			self.nRank = 1

	def overWatch(self, event = None):
		keyup = False
		key = -1
		mod = -1
		while not keyup :
			if event is None :
				pygame.event.pump()
				for event in pygame.event.get() :
						if event.type == pygame.KEYDOWN:
							key = event.key
							mod = event.mod
						elif event.type == pygame.KEYUP:
							if key is None and mod is None :
								key = event.key
								mod = event.mod
							keyup = True
				if key == -1 and mod == -1 and keyup == False:
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


		if key == 113 and mod == (1024 or 2048): #quit
			self.quit()
		if key == 49 and mod == (1024 or 2048):  #calibrate
			pass
			return True
		if key == 50 and mod == (1024 or 2048):  #pause
			if not self.paused :
				self.paused = True
				self.pause()
				return True
			if self.paused :
				self.paused = False
				return False
		if mod != (1024 or 2048):
			return False

	def pause(self):
		time.sleep(0.2) #to prevent unpausing immediately due to a key(still)down event
		while self.paused :
			self.message('PAUSED',{
									'fullscreen':True,
									'location':'center',
									'fontSize':96,
									'color':(255,0,0),
									'registration':5,
									'return':'flip'
									})
			self.overWatch()
			self.flip()

	def performanceEval(self):
		numerator = 0
		demoninator = 0
		if self.computeAccuracyByTimeout :
			numerator = numerator + self.blockLogs['notarget']
		if self.computeAccuracyByResponse :
			numerator = numerator + self.blockLogs['correct']

		for n in self.exemptions.keys():
			if not self.exemptions[n]:
				demoninator = demoninator + self.blockLogs[n]
		score = float(numerator) / float(demoninator)
		#print "Numerator: {0} and Denominator: {1} and Score: {2}".format(numerator, demoninator, score)
		if score > self.promoteThreshold:
			self.__promote()
		if score < self.demoteThreshold:
			self.__demote()
		r = self.blockLogs['correct'] + self.blockLogs['notarget']
		w = self.blockLogs['timeout'] + self.blockLogs['incorrect']
		print "performanceEval():\n\tcorrect:{0} incorrect:{1} notarget: {2} timeout: {3}\n\tright/wrong: {4}/{5}\n\tright/total: {6}/{7}\n\tComputed: {8}%\n".format(self.blockLogs['correct'], self.blockLogs['incorrect'],self.blockLogs['notarget'],self.blockLogs['timeout'],r,w,r,self.blockLogs['trials'] - self.nRank,score*100)
		return score

	def query(self, query='default', config={'password':False,
										'font':'default',
										'fontSize':'default',
										'color':'default',
									   	'locations':{'query':'default','input':'default'},
									   	'registration':7,
										'returnType':'default',
										'accepted':'default'
										}):

		configKeys = ['password','accepted','font','fontSize','color','locations','registration', 'returnType']
		config = self.autoConfig(configKeys, config)
		if config['locations'] == 'default':
			config['locations'] = {'query':'default', 'input':'default'}
		inputRenderConfig = {}
		inputLocation = None
		queryRenderConfig = {}
		queryLocation = None
		verticalPadding = None
		queryRegistration = 8
		inputRegistration = 2

		# build config argument(s) for __renderText()
		# process the possibility of different query/input font sizes
		if config['fontSize']!= 'default':
			if type(config['fontSize']) is (tuple or list):
				if  len(config['fontSize'])==2:
					inputRenderConfig['fontSize'] = self.text.fontSizes[config['fontSize'][0]]
					queryRenderConfig['fontSize'] = self.text.fontSizes[config['fontSize'][1]]
					verticalPadding = queryRenderConfig['fontSize']
					if inputRenderConfig['fontSize'] < queryRenderConfig['fontSize']: #use smaller of two font sizes as vertical padding from midline
						verticalPadding = inputRenderConfig['fontSize']
			else:
				inputRenderConfig['fontSize'] = self.text.fontSizes[config['fontSize']]
				queryRenderConfig['fontSize'] = self.text.fontSizes[config['fontSize']]
				verticalPadding  = self.text.fontSizes[config['fontSize']]
		else:
			inputRenderConfig['fontSize'] = self.text.defaultFontSize
			queryRenderConfig['fontSize'] = self.text.defaultFontSize
			verticalPadding = self.text.defaultFontSize

		if config['registration'] != 'default':
			if type(config['registration']) is (tuple or list):
				inputRegistration = config['registration'][0]
				queryRegistration = config['registration'][1]
			else:
				inputRegistration = config['registration']
				queryRegistration = config['registration']

		# process the (unlikely) possibility of different query/input fonts
		if config['font']!= 'default':
			if type(config['font']) is (tuple or list) and len(config['font'])==2:
				try:
					inputRenderConfig['font'] = config['font'][0]
				except:
					print "Font provided in query()->config parameter not found in app.text.fonts, attempting to use default... "
					inputRenderConfig['font'] = self.text.defaultFont
				try:
					queryRenderConfig['font'] = config['font'][1]
				except:
					print "Font provided in query()->config parameter not found app.text.fonts, attempting to use default... "
					queryRenderConfig['font'] = self.text.defaultFont
			else:
				inputRenderConfig['font']  = config['font']
				queryRenderConfig['font'] = config['font']
		elif self.text.defaultFont != '':
			inputRenderConfig['font']  = self.text.defaultFont
			queryRenderConfig['font'] = self.text.defaultFont
		else:
			self.quit() #error

		# process the possibility of different query/input colors
		if config['color'] != 'default':
			if len(config['color']) == 2:
				inputRenderConfig['color'] = config['color'][0]
				queryRenderConfig['color'] = config['color'][1]
			else:
				inputRenderConfig['color'] = config['color']
				queryRenderConfig['color'] = config['color']
		else:
			inputRenderConfig['color'] = self.text.defaultColor
			queryRenderConfig['color'] = self.text.defaultColor

		# process config['locations']
		generateLocations = False
		if 'locations' in config.keys():
			if config['locations']['query'] == 'default' or config['locations']['input'] == 'default':
				if self.text.defaultLocations['query'] and self.text.defaultLocations['input']:
					queryLocation = self.text.defaultLocations['query']
					inputLocation = self.text.defaultLocations['input']
				else:
					generateLocations = True
			else:
				queryLocation = config['locations']['query']
				inputLocation = config['locations']['input']
		else:
			generateLocations = True
		# infer config['locations'] if none are provided (ie. center horizontally, vertically padded from screen midline)
		# create & render querySurface
		#
		# Note: inputString is on a separate surface, declared later in this function!
		querySurface = None
		queryText = ''
		try:
			if query != 'default':
				querySurface = self.text.renderText(query, queryRenderConfig)
			elif self.text.defaultQueryString is not None :
				querySurface = self.text.renderText(self.text.defaultQueryString, queryRenderConfig)
			else:
				raise Generror("A default query was not set and no query was provided. Exiting program...")
		except Generror as e:
			print self.err(e, {'class':'App','method':'query'})
			self.quit()

		queryBaseline = (self.screeny//2) - verticalPadding
		inputBaseline = (self.screeny//2) + verticalPadding
		horizontalCenter = self.screenx//2
		if generateLocations:
			queryLocation = [horizontalCenter, queryBaseline]
			inputLocation = [horizontalCenter, inputBaseline]

		self.sf()
		self.bliterate(querySurface, queryRegistration, queryLocation)
		self.flip()

		inputString = '' #declare now, populate in loop below, '' instead of None to ensure initialization as strings
		userFinished = False #True when enter or return are pressed
		noAnswerMessage = 'Please provide an answer.'
		badAnswerMessage = None
		if config['accepted']!='default':
			try:
				accepted = self.prettyJoin(config['accepted'], {'beforeLast':'or','prepend':'[ ','append':' ]'})
			except Generror as e:
				print self.warn(e, {'class':'App','method':'query'})
				try:
					if type(config['accepted'] is (tuple or list)):
						accepted = ''.join(config['accepted'])
					else:
						raise Generror("config['accepted'] must be a tuple or list.")
				except Generror as e:
					self.err(e, {'class':'App','method':'query'})
			badAnswerMessage = 'Your answer must be one of the following: {0}'.format(config['accepted'])
		while not userFinished:
			pygame.event.pump()
			for event in pygame.event.get() :
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
							inputString = inputString[0:(len(inputString)-1)]
							if 'password' in config.keys():
								if config['password'] == True  and len(inputString)!=0:
									pwstring =''+len(inputString)*'*'
									inputSurface = self.text.renderText(pwstring, inputRenderConfig)
								else:
									inputSurface = self.text.renderText(inputString, inputRenderConfig)
							self.sf()
							self.bliterate(querySurface, queryRegistration, queryLocation )
							self.bliterate(inputSurface, inputRegistration, inputLocation )
							self.flip()
					elif key == 13 or key == 271:
						badAnswer = False
						noAnswer = False
						if len(inputString) > 0:
							if config['accepted'] != 'default':   #to make the accepted list work, there's a lot of checking yet to do
								if inputString in config['accepted']:
									userFinished = True
								else:
									badAnswer = True
							else:
								userFinished = True
						else:
							noAnswer = True

						if (badAnswer == True) or (noAnswer == True):
							if badAnswer :
								inputString = badAnswerMessage
							else:
								inputString = noAnswerMessage
							tempColor = inputRenderConfig['color']
							inputRenderConfig['color'] = self.text.alertColor
							inputSurface = self.text.renderText(inputString, inputRenderConfig)
							self.sf()
							self.bliterate(querySurface, queryRegistration, queryLocation )
							self.bliterate(inputSurface, inputRegistration, inputLocation )
							self.flip()
							inputRenderConfig['color'] = tempColor
							inputString = ''
					elif key == 27:
						inputString = ''
						inputSurface = self.text.renderText(inputString, inputRenderConfig)
						self.sf()
						self.bliterate(querySurface, queryRegistration, queryLocation )
						self.bliterate(inputSurface, inputRegistration, inputLocation )
						self.flip()

					else:
						inputString += str( ukey )
						inputSurface = None
						if 'password' in config.keys():
							if config['password'] == True  and len(inputString)!=0:
								pwstring =''+len(inputString)*'*'
								inputSurface = self.text.renderText(pwstring, inputRenderConfig)
							else:
								inputSurface = self.text.renderText(inputString, inputRenderConfig)
						else:
							inputSurface = self.text.renderText(inputString, inputRenderConfig)
						self.sf()
						self.bliterate(querySurface, queryRegistration, queryLocation)
						self.bliterate(inputSurface, inputRegistration, inputLocation )
						self.flip()
				elif event.type == pygame.KEYUP:
					self.overWatch(event)
		self.sf()
		self.flip()
		if config['returnType'] != 'default':
			if config['returnType'] == 'int':
				return int(inputString)
			if config['returnType'] == 'str':
				return str(inputString)
		else:
			return inputString

	def quit(self):
		try:
			self.db.db.commit()
		except:
			print "Commit() to database failed."
			pass
		try:
			self.db.db.close()
		except:
			print "Database close() unsuccessful."
			pass
		pygame.quit()
		sys.exit()

	def regrid(self, nloc = 0, flip = True):
		self.sf()
		self.grid.reset()
		if self.crossState == 'On':
			self.bliterate(self.grid.cross, 5, 'center', self.gridWiz())
		elif self.crossState == 'Flash' and nloc == 0:
			self.bliterate(self.grid.cross, 5, 'center', self.gridWiz())
		if nloc != 0:
			self.bliterate(self.token, 5, self.gridWiz(nloc), self.gridWiz())
		self.bliterate(self.gridWiz(), 5, self.screenc)
		self.message('n-Back level: '+ str(self.nRank), {'location':[self.appx0, self.appy0]})
		self.message('POSITION MATCH', {'location':'bottom-center','color':self.pal.grey3})
		if flip:
			self.flip()

	def request(self, attribute):
		appDict = self.__dict__
		if type(attribute) is (tuple or list):
			request = []
			for n in attribute:
				if (appDict[n]):
					request.append(appDict[n])
			return request
		else:
			if (appDict[attribute]):
				return appDict[attribute]

	def run(self):
		self.nReached = self.nRank
		# in test mode, don't create new participants, display instructions, offer block breaks or an exit message
		if not self.testing:
			pass
		else:
			with open ("assets/instructions.txt", "r") as f:
				instructions = f.read().replace("\n",'')
				self.message(instructions, {'fullscreen':True, 'fontSize':24, 'return':'flip', 'delimiter':"[br]",'wrap':True})
				self.listen('*','*')
				self.demograph()
		if self.practiceBlocks > 0:
			self.practicing = True
			for blockNum in range(self.practiceBlocks):
				self.nBackLog = [0,]*self.nRank
				self.block(blockNum)
			self.practicing = False
		for blockNum in range(self.blocks):
			self.block(blockNum)

		if self.testing:
			pass
		else:
			self.message("Thanks for participating! Please call the researcher to relieve you. Press any key to exit.",
						 {'fullscreen':True,
						  'return':'flip',
						  'location':'center',
						  'registration':5}
						)
			self.listen('*','*')
		self.quit()

	def setAccuracyIndex(self,index):
		if type(index) is str:
			if index == 'correct':
				self.computeAccuracyByResponse = True
				self.computeAccuracyByTimeout = False
				if self.autoExempt :
					self.exemptions['notarget'] = True
				return None

			if index == 'timeout':
				self.computeAccuracyByResponse = False
				self.computeAccuracyByTimeout = True
				if self.autoExempt :
					self.exemptions['correct'] = True
				return None

			if index == 'both':
				self.computeAccuracyByResponse = True
				self.computeAccuracyByTimeout = True

	def setCrossState(self, state):
		try:
			if state == 'On':
				self.crossState = 'On'
			elif state == 'Off':
				self.crossState = 'Off'
			elif state == 'Flash':
				self.crossState = 'Flash'
			else:
				raise Generror("Cross state parameter must be one of 'On', 'Off' or 'Flash")
		except Generror as e:
			self.err(e,['App','crossState'], True)

	def setIntervals(self,config = {'soa':1, 'responseInterval':2}):
		configKeys = ('soa','responseInterval')
		config = self.autoConfig(configKeys, config)
		if config['soa'] != 'default':
			self.soa = config['soa']
		if config['responseInterval'] != 'default':
			self.responseInterval = config['responseInterval']

	def sf(self, config ={'color':'default', 'surface':'default'}):
		configKeys = ('color','surface')
		for n in configKeys:
			if not n in config:
				config[n] = 'default'

		if config['color'] == 'default':
			config['color'] = (255,255,255)

		if config['surface'] == 'default':
			self.screen.fill(config['color'])
		else:
			config['screen'].fill(config['color'])

	def start(self):
		self.startTime = time.time()

	def testMode(self, mode):
		self.testing = mode

	def trial(self, trialNum, practicing = False):
		self.trialCount = trialNum
		if practicing:
			self.practicing = True
		else:
			self.practicing = False
		nloc = self.nextBack()
		self.db.initEntry('trials', {'setCurrent':True})
		self.regrid()
		self.regrid(nloc, False)
		self.start()
		while (time.time() - self.startTime) < self.soa:
			self.overWatch('pass')
		if self.responseInterval != 0:
			response = self.listen(interval = self.responseInterval)
		else:
			response = self.listen()
		self.regrid() # occasionally __logTrial takes longer than usual, this prevents the token from hanging on the grid
		self.__log_trial(nloc, response)

class Palette(KlibBase):
		def __init__(self):
			KlibBase.__init__(self)
			self.black = (0,0,0)
			self.white = (255,255,255)
			self.grey1 = (50,50,50)
			self.grey2 = (100,100,100)
			self.grey3 = (150,150,150)
			self.grey4 = (200,200,200)
			self.grey5 = (250,250,250)
			self.alert = (255,0,0)

		def hsl(self, index):
			print("to be defined later")


class Thesaurus(KlibBase):
	def __init__(self, errorHeader):
		self.header = errorHeader # mirror of KlibBase's same; cannot call KlibBase.__init__() without causing an infinite loop
		self.thesaurus = {'true':[True, 'true','TRUE','True'],
					 'false':[False,'false','False','FALSE'],
					 'none':[None,'none','NONE','None'],
					 'int':['integer', 'integer key','INTEGER','INTEGER KEY'],
					 'float':['real','REAL','float','FLOAT'],
					 'inch':['inch','inches','INCH','INCHES','Inch','Inches','in','IN','In'],
					 'cm':['cm','CM','centimeter','centimeters','CENTIMETER','CENTIMETERS','Centimeter','Centimeters']}

	def addKey(self, key, synList):
		try:
			if type(key) is str:
				if key in self.thesaurus:
					self.addSynonym(key,synList)
					raise Genwarning("The key '{0}' is already registered; any new synonyms in the provided synList will be added.")
				else:
					self.thesaurus[key] = ''
					self.addSynonym(key, synList)
			else:
				raise Generror("Parameter 'key' must be a string, value '{0}' of type '{1}' was passed.".format(repr(key), type(key)))
		except Genwarning as e:
			self.warn(e, ('Thesaurus','addKey'))
		except Generror as e:
			self.err(e, ('Thesuars','addkey'), True)
		return True

	def addSynonym(self, key, synList):
		doList = False
		try:
			if type(key) is str:
				if key in self.thesaurus:
					doList = True
				else:
					raise Genwarning("Key '{0}' was not registered; adding it before processing synList...".format(key))
		except Genwarning as e:
			self.warn(e, ('Thesaurus','addSynonym'))
			self.addKey(key)
		try:
			if doList :
				if type(synList) is list or type(synList) is tuple:
					for n in synList:
						if not n in self.thesaurus[key]:
							self.thesaurus[key].append(n)
				else:
					self.thesaurus[key].append(synList)
			else:
				raise Generror("A valid key was no provided, without which there is no index for which synonyms can be stored.")
		except Generror as e:
			self.err(e, ('Thesaurus','addSynonym'), True)
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
					raise Generror("The key '{0}' was not found in the Klib thesaurus.".format(key))
			else:
				raise Generror("Search key must be a string, but the key '{0}' was of type '{1}'".format(repr(key), type(key)))
		except Generror as e:
			self.err(e, ('Thesaurus','inspect'))
			return False

class Grid(KlibBase):
		def __init__(self, gridVars):
			KlibBase.__init__(self)
			self.gridVars = gridVars
			self.__buildCross()
			self.__buildGrid()
			self.__gloc = {
					1: [self.gridVars['boxLength'] // 2, self.gridVars['boxLength'] // 2],
					2: [self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2), self.gridVars['boxLength'] // 2],
					3: [2*self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2), self.gridVars['boxLength'] // 2],
					4: [self.gridVars['boxLength'] // 2, self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2)],
					5: [self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2),self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2)],
					6: [2*self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2), self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2)],
					7: [self.gridVars['boxLength'] // 2, 2*self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2)],
					8: [self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2), 2*self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2)],
					9: [2*self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2), 2*self.gridVars['boxLength'] + (self.gridVars['boxLength'] // 2)]
			}
			self.fillColor = (255,255,255)

		def get(self, index = None):
			if (not index):
				return self.grid
			else:
				return self.__gloc[index]

		def __buildCross(self):
			surface = pygame.Surface((self.gridVars['boxLength']//4, self.gridVars['boxLength']//4))
			surface.fill(self.gridVars['white'])
			boxl = surface.get_width()
			crossVertStart = [boxl//2, 0]
			crossVertEnd = [boxl//2, boxl]
			crossHorStart = [0, boxl//2]
			crossHorEnd = [boxl, boxl//2]
			pygame.draw.line(surface, self.gridVars['black'], crossVertStart, crossVertEnd, self.gridVars['stroke'])
			pygame.draw.line(surface, self.gridVars['black'], crossHorStart, crossHorEnd, self.gridVars['stroke'])
			self.cross = surface

		def __buildGrid(self):
			surface = pygame.Surface( (3*self.gridVars['boxLength']+self.gridVars['stroke'], 3*self.gridVars['boxLength']+self.gridVars['stroke']) )
			surface.fill(self.gridVars['white'])
			for i in range(4):
				if i==1 or i==2:
					pygame.draw.line(surface, self.gridVars['black'],(i*self.gridVars['boxLength'], 0),(i*self.gridVars['boxLength'], self.gridVars['appx']), self.gridVars['stroke'] )
				for j in range(4):
					if j==1 or j==2:
						pygame.draw.line(surface, self.gridVars['black'],(0, j*self.gridVars['boxLength']),(self.gridVars['appy'], j*self.gridVars['boxLength']), self.gridVars['stroke'] )
			self.grid = surface
			self.gridTemplate = surface.copy()

		def reset(self):
			self.grid = self.gridTemplate.copy()

class Database(KlibBase):
	#TODO: improve path management; currently this class cannot be used by any other app
	def __init__(self, dbname, sqlSchema = (None,False), startEmpty = False):
		KlibBase.__init__(self)
		self.dbpath = "assets/"+dbname+".db"
		initialized = False
		self.defaultTable = -1
		self.db = sqlite3.connect(self.dbpath)
		if self.db:
			self.cursor = self.db.cursor()
			tableList = self.__tables()
			if len(tableList) == 0:
				if (sqlSchema[0]):
					if (sqlSchema[1]):
						self.schemaSQL = None
						self.sqlSchemaPath = "assets/"+sqlSchema[0]+".sql"
						try:
							self.__deploySqlSchema(self.sqlSchemaPath, True)
							initialized = True
						except:
							self.__dropTables(tableList, True)
							self.err("Database schema could not be deployed; there is a syntax error in the SQL file.",('Database',"__init__"), True)

					else:
						self.schemaSQL = sqlSchema[0]
						self.sqlSchemaPath = None
						try:
							self.__deploySqlSchema(sqlSchema[0], False)
							initialized = True
						except:
							print self.err("Database schema could not be deployed; there is a syntax error in the SQL file.",{'class':'Database','method':'__init__'})
							self.__dropTables(tableList, True)
							self.quit()
			else:
				initialized = True
				if (sqlSchema[1]):
					self.schemaSQL = None
					self.sqlSchemaPath = "assets/"+sqlSchema[0]+".sql"
				else:
					self.schemaSQL = sqlSchema[0]
					self.sqlSchemaPath = None

		if initialized:
			if self.buildTableSchemas():
				self.__openEntries = {}
				self.__currentEntry = None


	def __tables(self):
		self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
		tableCount = self.cursor.fetchall()
		return tableCount

	def __dropTables(self, tableList = None, killApp = False):
		if tableList is None :
			tableList = self.__tables()
		for n in tableList:
			if str(n[0]) != "sqlite_sequence":
				self.cursor.execute("DROP TABLE `"+str(n[0])+"`")
		self.db.commit()
		if killApp:
			try:
				self.db.close()
			except Generror('For unknown reasons, the database could not be closed.') as e:
				print self.err(e, {'class':'database','method':'__init__'})
			try:
				os.remove(self.dbpath)
			except Generror('The database has been corrupted but the attempt to delete it before rebuilding it has failed; program will now end.') as e:
				print self.err(e, {'class':'database','method':'__init__'})
			self.quit()

	def	__deploySqlSchema(self, sqlSchema, isPath = True):
		query = None
		if isPath:
			f =  open(sqlSchema, 'rt')
			query = f.read()
		elif (type(sqlSchema) == 'str'):
			query = sqlSchema
		self.cursor.executescript(query)

	def buildTableSchemas(self):
		self.cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table'")
		tables = {}
		for tableTuple in self.cursor.fetchall():
			table = str(tableTuple[0]) #str() necessary b/c tableTuple[0] is in unicode
			if table != "sqlite_sequence":
				tableCols = {}
				self.cursor.execute("PRAGMA table_info("+table+")")
				columns = self.cursor.fetchall()
				for col in columns:
					if col[2] in ('text', 'TEXT'):
						colType = 'str'
					elif self.equiv('int',col[2]):
						colType = 'int'
					elif col[2] in ('blob','BLOB'):
						colType = 'binary'
					elif self.equiv('float',col[2]):
						colType = 'float'
					else:
						colType = 'unknown'
						print self.warn("Database\n\tbuildTableSchemas(): column '{0}' of table '{1}' has type '{1}' on the database but was assigned a type of 'unknown' during schema building'".format(col[1], col[2], table))
					allowNull = False
					if col[3] == 0:
						allowNull = True
					tableCols[str(col[1])] ={'order':int(col[0]), 'type':colType, 'allowNull':allowNull}
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
		self.__dropTables()
		try:
			if self.schemaSQL is not None :
				try:
					self.__deploySqlSchema(self.schemaSQL, False)
					initialized = True
				except:
					print "Error: Database schema could not be deployed; there is a syntax error in the SQL file."
					self.__dropTables(tableList, True)
			elif self.sqlSchemaPath is not None :
				try:
					self.__deploySqlSchema(self.sqlSchemaPath, True)
					initialized = True
				except:
					print self.err()+"Database\n\t__init__(): Database schema could not be deployed; there is a syntax error in the SQL file."
					self.__dropTables(tableList, True)

			if self.buildTableSchemas():
				self.__openEntries = {}
				self.__currentEntry = 'None'
		except:
			print self.err()+"Database\n\tflush(): Database instance has no access to original schema."

	def entry(self,instance = 'default'):
		if instance == 'default':
			try:
				return self.__openEntries[self.__currentEntry]
			except:
				print self.err()+"Database\n\tentry(): A specific instance name was not provided and there is no current entry set.\n"
		else:
			try:
				return self.__openEntries[instance]
			except:
				print self.err()+"Database\n\tentry(): No currently open entries named '"+instance+"' exist."

	def initEntry(self, tableName, config = {'instanceName':'default', 'setCurrent':True}):
		config = self.autoConfig(('instanceName','setCurrent'), config)

		if type(tableName) is str:
			if self.tableSchemas[tableName]:
				if config['instanceName'] == 'default':
					config['instanceName'] = tableName
				self.__openEntries[config['instanceName']] =  EntryTemplate(tableName, self.tableSchemas[tableName], config['instanceName'])
				if config['setCurrent'] :
					self.current(config['instanceName'])
			else:
				print "No table with the name '"+tableName+"' was found in the Database.tableSchemas."
		else:
			pass #throw error

	def log(self, field, value, instance = 'default'):
		try:
			if (instance != 'default') and (self.__openEntries[instance]):
				self.__currentEntry = instance
			elif instance == 'default' and self.__currentEntry != 'None':
				instance = self.__currentEntry
			else:
				raise Generror("No default entry is set and no instance was passed.")
		except Generror as e:
			self.err(e, {'class':'Database','method':'log'}, True)
		try:
			self.__openEntries[instance].log(field, value)
		except:
			e= "[instance:'{0}'] Something went wrong trying to log '{1}' as '{2}'".format(instance, field, value)
			self.err(e, {'class':'Database','method':'log'}, True)

	def current(self, verbose = False):
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

	def requireUnique(self, value, field, table):
		query = "SELECT * FROM `" + table + "` WHERE `" + field +"` = '" + value +"'"
		self.cursor.execute(query)
		result = self.cursor.fetchall()
		if len(result) > 0:
			return False
		else:
			return True

	def setDefaultTable(self, name):
		self.defaultTable = name

	def insert(self, data = 'default', config = {'table':'default','tidyExecute':True} ):
		if data == 'default':
			try:
				current = self.current('return')
				data = self.entry(current)
			except:
				print self.err()+"Database\n\tinsert(): No data was provided and a Database.__currentEntry is not set."
				self.quit()
		config = self.autoConfig(('table','tidyExecute'), config)
		query = ''
		dataIsEntryTemplate = False
		if data.__class__.__name__ == 'EntryTemplate':
			dataIsEntryTemplate = True
			query = data.buildQuery('insert')
		else:
			template = None
			if config['table'] != 'default':
				if self.defaultTable == -1:
					raise Generror(self.err()+"Database\n\tinsert():Either provide a table when calling insert() or set a defaultTable with App.Database.setDefaultTable().")
				else:
					table = self.defaultTable
			try:
				template = self.tableSchemas[config['table']]
			except:
				print self.err()+"Database\n\tinsert(): The supplied table name, '{0}' was not found in Database.tableSchemas".format(config['table'])
				self.quit()
			fieldCount = len(template)
			if template['id']:
				fieldCount -= 1#id will be supplied by database automatically on cursor.execute()
			cleanData = [None,]*fieldCount
			insertTemplate = [None,]*fieldCount
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
							cleanData[order] = "'"+str(data[order])+"'"
			else:
				raise Generror(self.err()+'Database\n\tinsert(): Length of data list does not much number of columns.')
			query = "INSERT INTO `" + table + "` (" + ", ".join(insertTemplate) + ") VALUES (" + ",".join(cleanData) + ")"
		self.cursor.execute(query)
		if self.db.commit():
			if (config['tidyExecute'] == True) and (dataIsEntryTemplate == True):
				if self.__currentEntry == data.name:
					self.current() #when called without a parameter current() clears the current entry
			return True
		else:
			return False

	def query(self, query, doReturn = True):
		result = self.cursor.execute(query)
		self.db.commit()
		if (result and doReturn ):
			return result
		#add in error handling for SQL errors

class EntryTemplate(KlibBase):
	def __init__(self, tableName, tableSchema, instanceName):
		KlibBase.__init__(self)
		if type(tableSchema) is dict:
			self.schema = tableSchema
		else:
			pass #throw error
		if type(tableName) is str:
			self.tableName = tableName
		else:
			pass #throw error
		try:
			self.name = instanceName
		except Exception as e:
			print self.err("instanceName could not be set, ensure parameter is passed during initialization and is a string.", {'class':'EntryTemplate','method':'__init__'})
		self.data = ['null',]*len(tableSchema) #create an empty tuple of appropriate length

	def buildQuery(self, queryType):
		insertTemplate = ['null',]*len(self.schema)
		for fieldName in self.schema:
			field = self.schema[fieldName]
			insertTemplate[field['order']] = fieldName
			try:
				if self.data[field['order']] in ('null','NULL','none','None','NONE', None): #should just always be 'null', but this gives some wiggle room for human error
					if field['allowNull'] :
						self.data[field['order']] = 'DELETE_THIS_FIELD'
						insertTemplate[field['order']] = 'DELETE_THIS_FIELD'
					elif (queryType == 'insert') and (fieldName == 'id'):
						self.data[0] = 'DELETE_THIS_FIELD'
						insertTemplate[0]= 'DELETE_THIS_FIELD'
					else:
						raise NullColumn("[instance '{0}']: The required column '{1}' had a null value.".format(self.name,fieldName))
			except NullColumn as e:
				self.err(e, {'class':'EntryTemplate','method':'buildQuery'}, True)
			except Generror("[instance '{0}] an index was found in EntryTemplate.schema that exceeds the range of EntryTemplate.data; debug info to follow...".format(self.name)) as e:
				print self.err(e, {'class':'EntryTemplate','method':'buildQuery()'})
				print "\t\tOrder was:\n\t\t\t{0}\n\t\tSchema was:\n\t\t\t{1}\n\t\tData was:\n\t\t\t{2}\n\nExiting program...".format(str(field['order']),repr(self.schema),repr(self.data))
				self.quit()
		insertTemplate = self.__tidyNulls(insertTemplate)
		self.data = self.__tidyNulls(self.data)
		if queryType == 'insert':
			try:
				return  "INSERT INTO `" + self.tableName + "` (" + ", ".join(insertTemplate) + ") VALUES (" + ",".join(self.data) + ")"
			except Exception as e:
				print self.err("[instance '{0}'] SQL query string couldn't be written because NoneType items were found in either 'insertTemplate' or 'EntryTemplate.data'; printing debug info, then exiting program...".format(self.name),{'class':'EntryTemplate','method':'buildQuery'})
				print "\tSome helpful debugging information:\n\t\t***NUBNOTE: 'repr()' is the 'represent' function, useful when printing lists and strings in one statement)\n\trepr(insertTemplate) = {0}\n\trepr(self.data) = {1}".format(repr(insertTemplate), repr(self.data))
				self.quit()
			#do one for update too.

	def __tidyNulls(self,data):
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
		try:
			if field in self.schema:
				if value :
					value = 1
				if not value :
					value = 0
				if (type(value).__name__ == self.schema[field]['type']):
					if self.schema[field]['type'] == ('int' or 'float'):
						self.data[self.schema[field]['order']] = str(value)
					else:
						self.data[self.schema[field]['order']] = "'"+str(value)+"'"
				elif (self.schema[field]['allowNull'] == True) and value in (None,'','null','NULL','none', 'NONE'):
					self.data[self.schema[field]['order']] = None
				else:
					raise Generror("Schema for this table expected type '{0}', but the passed value ('{1}') was of '{2}'.".format(self.schema[field]['type'], value, type(value)))
			else:
				raise Generror("The field '{0}' wasn't found in this table's schema.".format(field))
		except Generror as e:
			self.err(e, {'class':'EntryTemplate', 'method':'__log'}, True)

	def report(self):
		print self.schema

class TextLayer(KlibBase):
	def __init__(self, appDimensions, screenDimensions, dpi, config = {'path':None,
															  'fonts':'default',
															  'defaultQueryString':None,
															  'defaultInputString':None,
															  'defaultLocations':None}):
		KlibBase.__init__(self)
		self.fontSizes = {}
		self.fonts = {}
		self.strings = {}
		self.labels = {}
		self.antialias = True
		self.queue = {}
		self.appx = appDimensions[0]
		self.appy = appDimensions[1]
		self.screenx = screenDimensions[0]
		self.screeny = screenDimensions[1]
		self.defaultColor = (0,0,0)
		self.defaultBgColor = (255,255,255)
		self.defaultFontSize = None
		self.defaultFont = ''
		self.alertColor = (255,0,0)
		self.defaultMessageDuration = 1

		configKeys = ['path','fonts','defaultQueryString','defaultInputString', 'defaultLocations']
		for n in configKeys:
			if not n in config.keys():
				config[n] = 'default'

		self.defaultQueryString = config['defaultQueryString']
		self.defaultInputString = config['defaultInputString']

		if type(config['defaultLocations']) is (tuple or list) and len(config['defaultLocations']) == 2:
			self.defaultLocations = config['defaultLocations']
		else:
			self.defaultLocations ={'query':None, 'input':None}

		if config['path'] != 'default':
			self.fontsDir =  config['path']
		else:
			self.fontsDir = "/Library/Fonts/"

		if type(self.appx) is int and type(dpi) is int:
			self.__buildFontSizes(dpi)
			self.setDefaultFontSize('12pt')
		else:
			pass # actually raise an exception

		if config['fonts'] != 'default':
			self.__buildFonts( config['fonts'] )
			self.setDefaultFont(config['fonts'][0][0])
		elif os.path.isfile(self.fontsDir + "Helvetica.ttf"):
				self.addFont('Helvetica', 'ttf')
				self.setDefaultFont('Helvetica')
		else:
			pass # throw error

	def __buildFontSizes(self, dpi):
		sizeList = range(3,96,1)
		self.fontSizes = {}
		for num in sizeList:
			key = str(num) + 'pt'
			self.fontSizes[key] = int(math.floor(1.0/72*dpi*num))

	def __buildFonts(self, fonts):
		for font in fonts:
			self.addFont(font[0], font[1])
		return None

	def size(self, text): #add a config dict later
		renderFont = pygame.font.Font(self.defaultFont, self.defaultFontSize)
		return renderFont.size()

	def renderText(self, string, config={'font':'default', 'fontSize':'default', 'color':'default', 'bgcolor':'default'} ):
		configKeys = ('font', 'fontSize', 'color', 'bgcolor')
		config = self.autoConfig(configKeys, config)

		if config['color'] == 'default':
			if hasattr(self, 'defaultColor'):
				config['color'] = self.defaultColor
			else:
				config['color'] = (0,0,0)

		renderFont = self.renderFont({'font':config['font'],'fontSize':config['fontSize']})
		try:
			return renderFont.render(string, True, config['color'], )
		except:
			raise Genwarning("Call to renderText() failed; string, when rendered, is too large for screen. Setting config['wrap'] to True and trying again...")

	def addFont(self, font, fontFormat):
		if type(font) and type(fontFormat) is str:
			if self.fontsDir is not None :
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

	def toggleAntialias(self, value):
		try:
			if self.equiv('true', value):
				self.antialias = True
			elif self.equiv('false', value):
				self.antialias = False
			else:
				raise Genwarning("Valid responses are true & false (or a registered synonym). Defaulting to 'true'.")
		except Genwarning as e:
			self.warn(e, ('TextLayer','toggleAntialias'))
			self.antialias = True
		return None

	def renderFont(self, config={'font':'default', 'fontSize':'default'}):
		configKeys = ('font', 'fontSize')
		config = self.autoConfig(configKeys, config)

		# process the fontSize argument or assign a default
		if config['fontSize']!= 'default':
			if type(config['fontSize']) is str:
					config['fontSize'] = self.fontSizes[config['fontSize']]
			elif int(config['fontSize']):
				pass #if it's an int, it's already correct, just need to be sure for error checking
			else:
				self.warn("")
		elif self.defaultFontSize:
			config['fontSize'] = self.defaultFontSize
		else:
			pass # throw error

		# process the font argument, or assign a default
		if config['font'] != 'default':
			if type(config['font']) is (tuple or list):
				if self.fonts[config['font'][0]]: #if trying to add a font that's been registered, just call it instead
					config['font'] = self.fonts[config['font']]
				else: #otherwise, add it, then call it
					self.addFont(config['font'][0], config['font'][1])
					font = self.fonts[config['font']]
			elif self.fonts[config['font']]:
				config['font'] = self.fonts[config['font']]
			else:
				pass #throw error
		elif self.defaultFont:
				config['font'] = self.fonts[self.defaultFont]
		else:
			pass # throw error
		return pygame.font.Font(config['font'], config['fontSize'])

	def setDefaultQuery(self, query):
		if type(query) is str:
			self.defaultQueryString = query

	def setDefaultLocations(self, queryLocation, inputLocation):
			if type(query) is (tuple or list) and type(input) is (tuple or list):
				self.defaultLocations['query'] = queryLocation
				self.defaultLocations['input'] = inputLocation

	def setDefaultInput(self, input):
		if type(input) is str:
			self.defaultInputString = input

	def setDefaultColor(self, color):
		if type(color) is list:
			self.color = color

	def setDefaultFontSize(self, size):
		if type(size) is str:
			#add in extra checking to make sure the format passed to self.size is 'XXpt'
			self.defaultFontSize = self.fontSizes[size]

	def setDefaultFont(self, font):
		if  self.fonts[font]:
			self.defaultFont = font
		else:
			pass #throw error

	def setDefaults(self, defaults):
		if type(defaults) is dict:
			if 'color' in defaults.keys():
				self.setDefaultColor(defaults['color'])
			if 'fontSize' in defaults.keys():
				self.setDefaultFontSize(defaults['fontSize'])
			if 'font' in defaults.keys():
				if type(defaults['font']) is (tuple or list):
					if defaults['font'][0] in self.fonts.keys():
						self.setDefaultFont(defaults['font'][0])
					else:
						self.addFont( defaults['font'][0],defaults['font'][1] )
						self.setDefaultFont(defaults['font'][0])
				else:
					if self.fonts[defaults['font']]:
						self.defaultFont = defaults['font']
			if 'query' in defaults.keys():
				self.setDefaultQuery(defaults['query'])
			if 'input' in defaults.keys():
				self.setDefaultInput(defaults['input'])
			if 'inputLocation' in defaults.keys():
				self.setDefaultLocations['input'] = defaults['inputLocation']
			if 'queryLocation' in defaults.keys():
				self.setDefaultLocations['query'] = defaults['queryLocation']
		else:
			pass #error handling

	def wrappedText(self, text, config = {'delimiter':'default','fontSize':'default','font':'default','wrapWidth':'default'}):
		configKeys = ('delimiter','fontSize','color','font','wrapWidth')
		config = self.autoConfig(configKeys, config)
		renderConfig = {'font':'default','fontSize':'default', 'color':'default'}
		if config['font'] != 'default':
			renderConfig['font'] = config['font']
		if config['fontSize'] != 'default':
			renderConfig['fontSize'] = config['fontSize']
		if config['delimiter'] == 'default':
			config['delimiter'] = "\n"
		try:
			if config['wrapWidth'] != 'default':
				if type(config['wrapWidth']) is not (int or float):
					raise Generror("The config option 'wrapWidth' must be an int or a float; '{0}' was passed. Defaulting to 80% of app width.".format(repr(config['wrapWidth'])))
				elif 1 > config['wrapWidth'] > 0 : #assume it's a percentage of app width.
					config['wrapWidth'] = int(config['wrapWidth'] * self.appx)
				elif config['wrapWidth'] > self.appx or config['wrapWidth'] < 0:
					raise Generror("A wrapWidth of '{0}' was passed which is either too big to fit inside the app or else is negative (and must be positive). Defaulting to 80% of app width.")
				#having passed these tests, wrapWidth must now be correct
			else:
				config['wrapWidth'] = int(0.8 * self.appx)
		except Generror as e:
			print self.warn(e, {'class':'TextLayer', 'method':'wrapText'})
			config['wrapWidth'] = int(0.8 * self.appx)
		renderFont = self.renderFont({'font':renderConfig['font'],'fontSize':renderConfig['fontSize']})
		paragraphs = None
		try:
			paragraphs = text.split(config['delimiter'])
		except Generror("'{0}' was passed as a delimiter, should be a simple string that won't appear by accident (ie.'\\n')".format(repr(config['delimiter']))) as e:
			print self.err(e, {'class':'TextLayer', 'method':'wrapText'})
		
		renderList = []
		lineHeight = 0
		# this loop was written by Mike Lawrence (mike.lwrnc@gmail.com) and then (slightly) modified for this program
		for p in paragraphs:
			wordList = p.split(' ')
			if len(wordList) == 1:
				renderList.append(wordList[0])
				if (p != paragraphs[len(paragraphs)-1]):
					renderList.append(' ')
					lineHeight = lineHeight + renderFont.get_linesize()
			else:
				processedWords = 0
				while processedWords < (len(wordList)-1):
					currentLineStart = processedWords
					currentLineWidth = 0

					while (processedWords < (len(wordList)-1)) and (currentLineWidth <= config['wrapWidth']):
						processedWords += 1
						currentLineWidth = renderFont.size(' '.join(wordList[currentLineStart:(processedWords+1)]))[0]
					if processedWords < (len(wordList)-1):
						#last word went over, paragraph continues
						renderList.append(' '.join(wordList[currentLineStart:(processedWords-1)]))
						lineHeight = lineHeight + renderFont.get_linesize()
						processedWords -= 1
					else:
						if currentLineWidth <= config['wrapWidth']:
							#short final line
							renderList.append(' '.join(wordList[currentLineStart:(processedWords+1)]))
							lineHeight = lineHeight + renderFont.get_linesize()
						else:
							#full line then 1 word final line
							renderList.append(' '.join(wordList[currentLineStart:processedWords]))
							lineHeight = lineHeight + renderFont.get_linesize()
							renderList.append(wordList[processedWords])
							lineHeight = lineHeight + renderFont.get_linesize()
						#at end of paragraph, check whether a inter-paragraph space should be added
						if (p!=paragraphs[len(paragraphs)-1]):
							renderList.append(' ')
							lineHeight = lineHeight + renderFont.get_linesize()
		return renderList

	def addQuery(self, label, string):
		if type(label) is str and type(string) is str:
			self.labels[label]= string

class NullColumn(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg

class Generror(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg

class Genwarning(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg
            
