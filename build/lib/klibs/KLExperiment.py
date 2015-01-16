__author__ = 'jono'
import random
import numpy
import math
import time
import hashlib
import re
from copy import copy
import OpenGL.GL as gl
import sdl2.ext
import aggdraw
from KLEyeLink import *
from KLExceptions import *
from KLNumpySurface import *
from KLDatabase import *
from KLKeyMap import KeyMap
from KLText import TextLayer
from KLUtilities import *
import KLParams as Params
from KLConstants import *
from KLELCustomDisplay import KLELCustomDisplay
from KLDraw import *


class TrialIterator(object):
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


class Experiment(object):
	__completion_message = "thanks for participating; please have the researcher return to the room."
	trial_number = 0
	block_number = 0
	__wrong_key_msg = None

	logged_fields = list()

	testing = True
	paused = False
	execute = True
	eyelink = None
	wrong_key_message = None
	core_graphics = None

	def __init__(self, project_name, el=None, asset_path="ExpAssets"):
		if not Params.setup(project_name, asset_path):
			raise EnvironmentError("Fatal error; Params object was not able to be initialized for unknown reasons.")

		Params.key_maps["*"] = KeyMap("*", [], [], [])
		Params.key_maps["drift_correct"] = KeyMap("drift_correct", ["spacebar"], [sdl2.SDLK_SPACE], ["spacebar"])
		Params.key_maps["eyelink"] = KeyMap("eyelink",
										["a", "c", "v", "o", "return", "spacebar", "up", "down", "left", "right"],
										[sdl2.SDLK_a, sdl2.SDLK_c, sdl2.SDLK_v, sdl2.SDLK_o, sdl2.SDLK_RETURN,
										sdl2.SDLK_SPACE, sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT],
										["a", "c", "v", "o", "return", "spacebar", "up", "down", "left", "right"])

		# this is silly but it makes importing from the params file work smoothly with rest of App
		self.event_code_generator = None

		#initialize the self.database instance
		self.__database_init()

		# initialize screen surface and screen parameters
		self.display_init(Params.view_distance)

		# initialize the self.text layer for the app
		self.text_layer = TextLayer(Params.screen_x_y, Params.screen_x_y, Params.ppi)
		if Params.default_font_size:
			self.text_layer.default_font_size = Params.default_font_size

		# initialize eyelink
		if PYLINK_AVAILABLE and Params.eye_tracking:
			if el:
				self.eyelink = el
			else:
				self.eyelink = KLEyeLink()
			self.eyelink.custom_display = KLELCustomDisplay(self, self.eyelink)
			self.eyelink.dummy_mode = Params.eye_tracker_available is False

	def __trial_func(self, *args, **kwargs):
		"""
		Manages a trial.
		"""
		# try:
		Params.trial_number += 1
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
		for i in range(Params.practice_blocks_per_experiment):
			self.__generate_trials(practice=True, event_code_generator=self.__event_code_function)
			if Params.trials_per_practice_block % len(Params.trials):
				if Params.trials_per_practice_block < len(Params.trials):
					Params.trials = Params.trials[:Params.trials_per_practice_block]
				else:
					e_str = "The desired number of trials in the practice block, \
							{0}, is not a multiple of the minimum number of trials, {1}."
					raise ValueError(e_str.format(Params.trials_per_practice_block, len(Params.trials)))
			else:
				Params.trials *= (Params.trials_per_practice_block / len(Params.trials))
			self.__trial_func(*args, **kwargs)
		for i in range(Params.blocks_per_experiment):
			Params.block_number = i + 1  # added this for data-out aesthetics more than use in program logic
			self.block(Params.block_number)
			self.__generate_trials(practice=False, event_code_generator=self.__event_code_function)
			if Params.trials_per_block % len(Params.trials):
				e = "The desired number of trials in the block, {0}, is not a multiple of the minimum number of trials, {1}."
				raise ValueError(e.format(Params.trials_per_block, len(Params.trials)))
			else:
				Params.trials *= (Params.trials_per_block / len(Params.trials))
				random.shuffle(Params.trials)
			for trial_factors in Params.trials:
				self.__trial_func(trial_factors, Params.trial_number)
			self.block_break()
		self.clean_up()
		self.database.db.commit()
		self.database.db.close()

	def __database_init(self):
		self.database = KLDatabase()
		# Params.database = self.database

	def __generate_trials(self, practice=False, event_code_generator=None):
		"""
		Example usage:
		Jono: event_code_gen: literally creates an event code, as per some rule, that will be in the trial_factors list
		passed to trial() for use with EEG bidnis
		event_code_generator = self.event_code_generator, cue=['right', 'left'], target=['right', 'left'],
		type=['word', 'nonword'], cued_bool='cue==target'
		To create an expression, simply pass a named string ending in _bool with a logical expression inside:
		cued_bool='peripheral==cue'
		Do not include other expression variables in an expression.
		They are evaluated in arbitrary order and may not yet exist.
		:param practice:
		:param event_code_generator:
		:return:
		"""
		trials = [[practice]]
		factors = ['practice']
		eval_queue = list()
		for factor in Params.exp_factors:
			label = factor[0]
			elements = factor[1]
			temp = list()
			if label[-5:] == '_bool':
				eval_queue.append([label, elements])
			else:
				factors.append(label)
				for element in trials:
					if element:
						for v in elements:
							te = element[:]
							te.append(v)
							temp.append(te)
				trials = temp[:]
		for element in eval_queue:
			factors.append(element[0][:-5])
			# print "element: " + element[1]
			operands = re.split('[=>!<]+', str(element[1]).strip())
			operator = re.search('[=<!>]+', str(element[1])).group()
			for t in trials:
				t.append(eval('t[factors.index(\'' + operands[0] + '\')]' + operator + 't[factors.index(\'' + operands[
					1] + '\')]'))
		if event_code_generator is not None and type(event_code_generator).__name__ == 'function':
			factors.append('code')
			for t in trials:
				t.append(event_code_generator(t))
		Params.trials = trials

	def __log_trial(self, trial_data, auto_id=True):
		#  todo: move this to a DB function.... :/
		if auto_id:
			if Params.testing or not Params.collect_demographics:
				self.participant_id = -1
			trial_data[Params.id_field_name] = self.participant_id
		for attr in trial_data:
			self.database.log(attr, trial_data[attr])
		self.database.insert()

	def __set_stroke(self):
		stroke = int(1 * math.floor(Params.screen_y / 500.0))
		if (stroke < 1):
			stroke = 1
		return stroke

	def display_init(self, view_distance, ppi="crt"):
		sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
		sdl2.mouse.SDL_ShowCursor(sdl2.SDL_DISABLE)
		Params.screen_x_y = [Params.screen_x, Params.screen_y]
		self.window = sdl2.ext.Window(Params.project_name, Params.screen_x_y, (0, 0), SCREEN_FLAGS)
		Params.screen_c = (Params.screen_x / 2, Params.screen_y / 2)
		Params.diagonal_px = int(math.sqrt(Params.screen_x * Params.screen_x + Params.screen_y * Params.screen_y))

		# these next six lines essentially assert a 2d, pixel-based rendering context; copied-and-pasted from Mike!
		gl_context = sdl2.SDL_GL_CreateContext(self.window.window)
		gl.glMatrixMode(gl.GL_PROJECTION)
		gl.glLoadIdentity()
		gl.glOrtho(0, Params.screen_x, Params.screen_y, 0, 0, 1)
		gl.glMatrixMode(gl.GL_MODELVIEW)
		gl.glDisable(gl.GL_DEPTH_TEST)
		self.clear()
		sdl2.SDL_PumpEvents()

		self.fill()
		try:
			self.blit(NumpySurface("splash.png"), 5, 'center')
		except:
			print "splash.png not found; splash screen not presented"
		self.flip(1)

		# this error message can be used in three places below, it's easier set it here

		# interpret view_distance
		if type(view_distance) is tuple and type(view_distance[0]) is int:
			if equiv('inch', view_distance[1]):
				Params.view_distance = view_distance[0]
				Params.view_unit = 'inch'
			elif equiv('cm', view_distance[1]):
				Params.view_distance = view_distance[0]
				Params.view_unit = 'cm'
				#convert physical screen measurements to cm
				Params.monitor_x *= 2.55
				Params.monitor_y *= 2.55
			else:
				raise TypeError("view_distance must be int (inches) or a tuple containing (int, str).")
		elif type(view_distance) is int:
			Params.view_distance = view_distance
			Params.view_unit = INCH
		else:
			raise TypeError("view_distance must be int (inches) or a tuple containing (int,str).")

		# TODO: THIS IS BROKEN. PPI needs to be calculated diagonally, this is using horizontal math only.
		# http://en.wikipedia.org/wiki/Pixel_density
		if equiv(ppi, "CRT"):
			Params.ppi = 72
		elif equiv(ppi, "LCD"):
			Params.ppi = 96
		elif type(ppi) is int:
			Params.ppi = ppi
		else:
			raise TypeError("ppi must be either an integer or a string representing monitor type (CRT/LCD).")
		# Params.monitor_x = Params.screen_x / Params.ppi
		# Params.monitor_y = Params.screen_y / Params.ppi
		Params.monitor_x = 23.3
		Params.monitor_y = Params.screen_y / Params.ppi
		Params.screen_degrees_x = math.degrees(math.atan((Params.monitor_x / 2.0) / Params.view_distance) * 2)
		Params.pixels_per_degree = int(Params.screen_x / Params.screen_degrees_x)
		Params.ppd = Params.pixels_per_degree  # alias for convenience

	def alert(self, alert_string, urgent=False, display_for=0):
		# TODO: address the absence of default colors
		# todo: instead hard-fill, "separate screen" flag; copy current surface, blit over it, reblit surf or fresh surf
		"""
		Display an alert

		:param alert_string: - Message to display
		:param urgent: - Boolean, returns alert surface for manual handling rather waiting for 'any key' response
		"""
		# if urgent:
		# 	return self.message(alert_string, color=(255, 0, 0, 255), location='topRight', registration=9,
		# 						font_size=text.default_font_size * 2, blit=True, flip=True)
		self.clear()
		self.fill(Params.default_fill_color)
		self.message(alert_string, color=(255, 0, 0, 255), location='center', registration=5,
							font_size=self.text_layer.default_font_size * 2, blit=True)
		if display_for > 0:
			start = time.time()
			self.flip()
			while (time.time() - start) < display_for:
				pass
			return
		else:
			self.listen()  # remember that listen calls flip() be default

	def blit(self, source, registration=7, position=(0, 0), context=None):
		height = None
		width = None
		content = None
		if type(source) is NumpySurface:
			height = source.height
			width = source.width
			content = source.render()
		elif type(source) is numpy.ndarray:
			height = source.shape[0]
			width = source.shape[1]
			content = source
		else:
			raise TypeError("Argument 'source' must be either of type numpy.ndarray or klibs.NumpySurface.")

		# configure OpenGL for blit
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		id = gl.glGenTextures(1)
		gl.glBindTexture(gl.GL_TEXTURE_2D, id)
		gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
		gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, content)
		gl.glEnable(gl.GL_TEXTURE_2D)
		gl.glBindTexture(gl.GL_TEXTURE_2D, id)
		gl.glBegin(gl.GL_QUADS)

		# convert english location strings to x,y coordinates of destination surface
		if type(position) is str:
			position = absolute_position(position, Params.screen_x_y)

		# define boundaries coordinates of region being blit to
		x_bounds = [position[0], position[0] + width]
		y_bounds = [position[1], position[1] + height]

		# shift boundary mappings to reflect registration
		#
		# 1--2--3  Default assumes registration = 5, but if registration = 3 (top-right), X/Y would be shifted
		# 4--5--6  by the distance from the object's top-left  to it's top-right corner
		# 7--8--9  ie. Given an object of width = 3, height = 3, with registration 9 being blit to (5,5) of some
		#          surface, the default blit behavior (placing the  top-left coordinate at 5,5) would result in
		#          the top-left corner being blit to (2,2), such that the bottom-right corner would be at (5,5)
		registrations = build_registrations(height, width)

		if 0 < registration & registration < 10:
			x_bounds[0] += int(registrations[registration][0])
			x_bounds[1] += int(registrations[registration][0])
			y_bounds[0] += int(registrations[registration][1])
			y_bounds[1] += int(registrations[registration][1])
		else:
			x_bounds[0] += int(registrations[7][0])
			x_bounds[1] += int(registrations[7][0])
			y_bounds[0] += int(registrations[7][1])
			y_bounds[1] += int(registrations[7][1])

		gl.glTexCoord2f(0, 0)
		gl.glVertex2f(x_bounds[0], y_bounds[0])
		gl.glTexCoord2f(1, 0)
		gl.glVertex2f(x_bounds[1], y_bounds[0])
		gl.glTexCoord2f(1, 1)
		gl.glVertex2f(x_bounds[1], y_bounds[1])
		gl.glTexCoord2f(0, 1)
		gl.glVertex2f(x_bounds[0], y_bounds[1])
		gl.glEnd()
		gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
		gl.glDeleteTextures([id])
		del id
		gl.glDisable(gl.GL_TEXTURE_2D)

	@abc.abstractmethod
	def block(self, block_num):
		pass

	def block_break(self, message=None, is_path=False):
		"""
		Display a break message between blocks

		:param message: A message string or path to a file containing a message string
		:param is_path:
		:raise:
		"""
		default = "You've completed block {0} of {1}. When you're ready to continue, press any key.".format(
			Params.block_number, Params.blocks)
		if is_path:
			try:
				path_exists = os.path.exists(message)
				if path_exists:
					with open(message, "r") as f:
						message = f.read().replace("\n", '')
				else:
					e = "'isPath' parameter was True but '{0}' was not a valid path. Using default message".format(
						message)
					raise IOError(e)
			except IOError as e:
				self.warn(e, 'App', 'blockBreak')
				message = default
		if self.testing:
			pass
		else:
			if type(message) is str:
				if message is None:
					message = default
				self.message(message, location='center', registration=5)
				self.listen()

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
			e ="Argument 'pos' must be a tuple, others must be integers."
			raise TypeError()

	def collect_demographics(self):
		"""
		Gather participant demographic information and enter it into the self.database

		"""
		# TODO: this function should have default questions/answers but should also be able to read from a
		# CSV or array for custom Q&A
		self.database.init_entry('participants', instance_name='ptcp', set_current=True)
		name_query_string = self.query(
			"What is your full name, banner number or e-mail address? Your answer will be encrypted and cannot be read later.",
			as_password=True)
		name_hash = hashlib.sha1(name_query_string)
		name = name_hash.hexdigest()
		self.database.log('userhash', name)

		# names must be unique; returns True if unique, False otherwise
		if self.database.is_unique(name, 'userhash', 'participants'):
			gender = "What is your gender? Answer with:  (m)ale,(f)emale or (o)ther)"
			handedness = "Are right-handed, left-handed or ambidextrous? Answer with (r)ight, (l)eft or (a)mbidextrous."
			self.database.log('gender', self.query(gender, accepted=('m', 'M', 'f', 'F', 'o', 'O')))
			self.database.log('handedness', self.query(handedness, accepted=('r', 'R', 'l', 'L', 'a', 'A')))
			self.database.log('age', self.query('What is  your age?', return_type='int'))
			self.database.log('created', self.now())
			if not self.database.insert():
				raise DatabaseException("Database.insert(), which failed for unknown reasons.")
			self.database.cursor.execute("SELECT `id` FROM `participants` WHERE `userhash` = '{0}'".format(name))
			Params.participant_id = self.database.cursor.fetchall()[0][0]
			if not Params.participant_id:
				raise ValueError("For unknown reasons, 'participant_id' couldn't be set or retrieved from self.database.")
		else:
			retry = self.query('That participant identifier has already been used. Do you wish to try another? (y/n) ')
			if retry == 'y':
				self.collect_demographics()
			else:
				self.fill()
				self.message("Thanks for participating!", location=Params.screen_c)
				self.window.refresh()
				time.sleep(2)
				self.quit()

	def drift_correct(self, location=None, events=EL_TRUE, samples=EL_TRUE):
		# try:
			self.clear()
			dc = self.eyelink.drift_correct(location, events, samples)
			print dc
		# except:
		# 	self.fill()
		# 	sdl2.mouse.SDL_ShowCursor(1)
		# 	dc_length = Params.screen_x // 50
		# 	color = []
		# 	for channel in Params.default_fill_color:
		# 		color.append(255 - channel)
		# 	color[3] = 255
		# 	brush = aggdraw.Brush(tuple(color))
		# 	pen = aggdraw.Pen(Params.default_fill_color, dc_length // 10)
		# 	draw_context = aggdraw.Draw("RGBA", [dc_length, dc_length], (0, 0, 0, 0))
		# 	draw_context.ellipse([0, 0, dc_length, dc_length], brush)
		# 	x1 = dc_length // 2
		# 	y1 = dc_length // 5
		# 	x2 = x1
		# 	y2 = dc_length - y1
		# 	stroke = dc_length // 5
		# 	draw_context.line([x1, y1, x2, y2], pen)
		# 	draw_context.line([y1, x1, y2, x2], pen)
		# 	self.blit(from_aggdraw_context(draw_context), 5, "center")
		# 	x_min = Params.screen_c[0] - dc_length // 2
		# 	x_max = Params.screen_c[0] + dc_length // 2
		# 	y_min = Params.screen_c[1] - dc_length // 2
		# 	y_max = Params.screen_c[1] + dc_length // 2
		# 	x_range = range(x_min, x_max)
		# 	y_range = range(y_min, y_max)
		# 	self.flip()
		# 	mouse_in_bounds = False
		# 	while not mouse_in_bounds:
		# 		self.listen(MAX_WAIT, "drift_correct", flip=False)
		# 		pos = mouse_pos()
		# 		if pos[0] in x_range and pos[1] in y_range:
		# 			mouse_in_bounds = True
		# 	sdl2.mouse.SDL_ShowCursor(0)
		# 	return True

	def draw_fixation(self, width=None, stroke=None, color=None, fill=None, flip=False):
		if not width:
			width = Params.screen_y // 50
		if not stroke:
			stroke = width // 5
		cross = FixationCross(width, stroke, color, fill).draw()

		self.blit(cross, 5, Params.screen_c)
		if flip:
			self.flip()
		return True

	def exempt(self, index, state=True):
		if index in self.exemptions.keys():
			if state == 'on' or True:
				self.exemptions[index] = True
			if state == 'off' or False:
				self.exemptions[index] = False

	def flip(self, duration=0):
		"""
		Flip the window and wait for an optional duration
		:param duration: The duration to wait in ms
		:return: :raise: AttributeError, TypeError, GenError
		"""

		sdl2.SDL_GL_SwapWindow(self.window.window)

		if duration == 0:
			return
		if type(duration) in (int, float):
			if duration > 0:
				start = time.time()
				while time.time() - start < duration:
					self.over_watch()
			else:
				raise AttributeError("Duration must be a positive number, '{0}' was passed".format(duration))
		else:
			raise TypeError("Duration must be expressed as an integer, '{0}' was passed.".format(type(duration)))

	def key_mapper(self, name, key_names=None, key_codes=None, key_vals=None):
		if type(name) is not str:
			raise TypeError("Argument 'name' must be a string.")

		# register the keymap if one is being passed in and set keyMap = name of the newly registered map
		if all(type(key_param) in [tuple, str] for key_param in [key_names, key_codes, key_vals]):
			Params.key_maps[name] = KeyMap(name, key_names, key_codes, key_vals)

		#retrieve registered keymap(s) by name
		if name in Params.key_maps:
			return Params.key_maps[name]
		else:
			return False

	def instructions(self, text, is_path=False):
		#  todo: remove arguments and use Params.instructions_file after you create it
		if is_path:
			if type(text) is str:
				if os.path.exists(text):
					f = open(text, 'rt')
					text = f.read()
				else:
					raise IOError("Argument 'is_path' was true but path to instruction text does not exist.")
			else:
				raise TypeError("Argument 'text' must be of type 'str' but '{0}' was passed.".format(type(text)))
		self.fill()
		self.message(text, location="center", flip=True)
		self.listen()

	def ui_request(self, key_press, execute=False):
		if key_press.mod in (MOD_KEYS["Left Command"], MOD_KEYS["Right Command"]):
			if key_press.sym in UI_METHOD_KEYSYMS:
				if key_press.sym == sdl2.SDLK_q:
					quit()
				elif key_press.sym in [sdl2.SDLK_c, sdl2.SDLK_s]:
					return key_press.sym
				elif key_press.sym == sdl2.SDLK_p:
					if not self.paused:
						self.paused = True
						self.pause()
						return True
					if self.paused:
						self.paused = False
						return False
		return False

	# todo: listen is not a method; it should be a class, "listener", that gets configured
	def listen(self, max_wait=MAX_WAIT, key_map_name="*", wait_callback=None, wait_cb_args=None, wait_cb_kwargs=None,
			el_args=None, null_response=None, time_out_message=None, response_count=None, response_map=None,
			interrupt=True, quick_return=False, flip=True):
		# TODO: have customizable wrong key & time-out behaviors
		# TODO: make RT & Response part of a customizable ResponseMap object
		# TODO: start_time should be optionally predefined and/or else add a latency param to be added onto starTime
		# TODO: make it possible to pass the parameters of a new KeyMap directly to listen()
		# TODO: add functionality for wait_callback() to exit the loop
		# establish an interval for which to listen for responding
		key_map = None

		if type(max_wait) not in (int, float):
			raise TypeError("Argument 'max_wait' must be an integer.")
		try:
			if key_map_name in Params.key_maps:
				key_map = Params.key_maps[key_map_name]
			else:
				raise ValueError("Argument 'key_map_name' did not match any registered KeyMap.")
		except:
			raise TypeError("Argument 'key_map_name' must be a string corresponding to a registered KeyMap.")
		response = None
		rt = -1

		start_time = time.time()
		waiting = True

		# enter with a clean event queue
		sdl2.SDL_PumpEvents()
		sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)  # upper/lower bounds of event queue,ie. flush all
		if flip:
			self.flip()  # executed as close to wait loop as possible for minimum delay between timing and presentation

		key = None
		sdl_keysym = None
		key_name = None
		wrong_key = False
		# then = time.time()
		while waiting:
			# now = time.time()
			# if print_interval:  # todo: this was once an argument; should be a component of verbosity once implemented
			# 	print str(int((now - then) * 1000)) + "ms"
			# 	# print "%f" % (now - then)
			# then = now

			if el_args:
				if type(el_args) is dict:
					self.eyelink_response = self.eyelink.listen(**el_args)
				else:
					raise TypeError("Argument 'el_args' must be a dict.")
			if wait_callback is not None and type(wait_callback).__name__ == 'instancemethod':  # todo: fix second cond.
				if wait_cb_args is None:
					wait_callback()
				elif type(wait_cb_args) is dict:
					# abstract method, allows for blits, flips and other changes during a listen() call
					wait_callback(*wait_cb_args, **wait_cb_kwargs)
				else:
					raise TypeError("Argument 'wait_cb_args' must be a dict.")
			sdl2.SDL_PumpEvents()
			for event in sdl2.ext.get_events():
				if event.type == sdl2.SDL_KEYDOWN:
					rt = time.time() - start_time
					if not response:  # only record a response once per call to listen()
						key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
						sdl_keysym = key.keysym.sym
						key_name = sdl2.keyboard.SDL_GetKeyName(sdl_keysym)
						valid = key_map.validate(sdl_keysym)
						if valid:  # a KeyMap with name "*" (ie. any key) returns self.ANY_KEY
							response = key_map.read(sdl_keysym, "data")
							if interrupt:  # ONLY for TIME SENSITIVE reactions to participant response; this flag voids overwatch()
								return [response, rt]
						else:
							wrong_key = True
					if key_name not in MOD_KEYS and key_name is not None:
						self.over_watch(event)  # ensure the 'wrong key' wasn't a call to quit or pause
						if interrupt:    # returns response immediately; else waits for maxWait to elapse
							if response:
								return [response, rt]
							elif key_map.any_key:
								return [key_map.any_key_string, rt]
						if wrong_key is True:  # flash an error for an actual wrong key
							pass
							# todo: make wrong key message modifable; figure out how to turn off to not fuck with RTs
							# wrong_key_message = "Please respond using '{0}'.".format(key_map.valid_keys())
							# self.alert(wrong_key_message)
							# wrong_key = False
			if (time.time() - start_time) > max_wait:
				waiting = False
				if time_out_message:
					self.alert(time_out_message, display_for=Params.default_alert_duration)
					return [TIMEOUT, -1]
		if not response:
			if null_response:
				return [null_response, rt]
			else:
				return [NO_RESPONSE, rt]
		else:
			return [response, rt]

	def message(self, message, font=None, font_size=None, color=None, bg_color=None, location=None, registration=None,
				wrap=None, wrap_width=None, delimiter=None, blit=True, flip=False, padding=None):
		# todo: padding should be implemented as a call to resize() on message surface; but you have to fix wrap first
		render_config = {}
		message_surface = None  # unless wrap is true, will remain empty

		if font is None:
			font = self.text_layer.default_font

		if font_size is None:
			font_size = self.text_layer.default_font_size

		if color is None:
			if self.text_layer.default_color:
				color = self.text_layer.default_color

		if bg_color is None:
			bg_color = self.text_layer.default_bg_color

		# if wrap:
		# 	print "Wrapped text is not currently implemented. This feature is pending."
		# 	exit()
		# 	message = text.wrapped_text(message, delimiter, font_size, font, wrap_width)
		# 	line_surfaces = []
		# 	message_height = 0
		# 	message_width = 0
		# 	for line in message:
		# 		line_surface = text.render_text(line, render_config)
		# 		line_surfaces.append((line_surface, [0, message_height]))
		# 		message_width = peak(line_surface.get_width(), message_width)
		# 		message_height = message_height + line_surface.get_height()
		# 	message_surface = pygame.Surface((message_width, message_height))
		# 	message_surface.fill(bg_color)
		# 	for ls in line_surfaces:
		# 		self.blit(ls[0], 7, ls[1], message_surface)

		#process blit registration
		if location == "center" and registration is None:  # an exception case for perfect centering
			registration = 5
		if registration is None:
			if wrap:
				registration = 5
			else:
				registration = 7

		# process location, infer if need be; failure here is considered fatal
		if location is None:
			# By Default: wrapped text blits to screen center; single-lines blit to topLeft with a padding = fontSize
			if wrap:
				location = Params.screen_c
			else:
				x_offset = (Params.screen_x - Params.screen_x) // 2 + font_size
				y_offset = (Params.screen_y - Params.screen_y) // 2 + font_size
				location = (x_offset, y_offset)
		elif type(location) is str:
			location = absolute_position(location, self.window)
		else:
			try:
				iter(location)
				if len(location) != 2:
					raise ValueError()
			except:
				raise ValueError("Argument 'location' invalid; must be a location string, coordinate tuple, or NoneType")


		if not blit:
			if wrap:
				return message_surface
			else:
				message_surface = self.text_layer.render_text(message, render_config)
				#check for single lines that extend beyond the app area and wrap if need be
				# if message_surface.shape[1] > self.screen_x:
				# 	return self.message(message, wrap=True)
				# else:
				# 	return message_surface
				return message_surface
		else:
			if wrap:
				self.blit(message_surface, registration, Params.screen_c)
			else:
				message_surface = self.text_layer.render_text(message, font, font_size, color, bg_color)
				# if message_surface.shape[1] > self.screen_x:
				# 	wrap = True
				# 	return self.message(message, font, font_size, color, bg_color, location, registration,
				# 						wrap, wrap_width, delimiter, blit, flip)
				self.blit(message_surface, registration, location)
			if flip:
				self.flip()
		return True

	def now(self):
		today = datetime.datetime
		return today.now().strftime("%Y-%m-%d %H:%M:%S")

	def numpy_surface(self, foreground=None, background=None, fg_position=None, bg_position=None, width=None, height=None):
			"""
			Factory method for klibs.NumpySurface
			:param foreground:
			:param background:
			:param width:
			:param height:
			:return:
			"""
			return NumpySurface(foreground, background, fg_position, bg_position, width, height)

	def over_watch(self, event=None):
		"""
		Inspects keyboard events for app-wide functions calls like 'quit', 'calibrate', 'pause', etc.
		When event argument is passed only that event in inspected.
		When called without event argument, pumps and inspects the entire event queue.
		:param event:
		:return:
		"""
		input_collected = False
		repumping = False  # only repump once else holding a modifier key down can keep overwatch running forever
		keysym = None
		sym = None
		mod_name = None
		key_name = None
		event_stack = None
		if event is None:
			event_stack = sdl2.SDL_PumpEvents()
			if type(event_stack) is list:
				event_stack.reverse()
			else:
				return False  # ie. app is in a passive context and no input is happening
		else:
			event_stack = [event]
		while not input_collected:
			event = event_stack.pop()
			if event.type in [sdl2.SDL_KEYUP, sdl2.SDL_KEYDOWN]:
				keysym = event.key.keysym
				sym = keysym.sym  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
				key_name = sdl2.keyboard.SDL_GetKeyName(sym)
				if event.type == sdl2.SDL_KEYUP:  # modifier or no, a key up event implies user decision; exit loop
					input_collected = True
				if key_name not in MOD_KEYS:  # if event key isn't a modifier: get key info & exit loop
					mod_name = sdl2.keyboard.SDL_GetModState()
					input_collected = True
				elif repumping and event.repeat != 0:  # user holding mod key; return control to calling method calling
					return False
				elif len(event_stack) == 0:
					sdl2.SDL_PumpEvents()
					event_stack = sdl2.ext.get_events()
					event_stack.reverse()
					if len(event_stack) > 0:
						repumping = True
					else:
						return False
				else:
					pass
			else:
				return False   # event argument was no good; just bail

		self.ui_request(keysym)
		return False

	def pause(self):
		time.sleep(0.2)  # to prevent unpausing immediately due to a key(still)down event
		while self.paused:
			self.message('PAUSED', fullscreen=True, location='center', font_size=96, color=(255, 0, 0, 255),
						registration=5, blit=False)
			self.over_watch()
			self.flip_callback()

	def pre_blit(self, source, start_time, end_time, registration=7, pos=(0, 0), destination=None, flags=None, area=None,
				interim_action=None):
		"""
		Blit to the screen buffer, wait until endTime to flip. Check func often if set.
		:type start_time: float
		:param source:
		:param start_time: Time trial began (from time.time())
		:param end_time: The time post trial after which the screen should be flipped.
		:param registration:
		:param pos:
		:param destination:
		:param flags:
		:param area:
		:param interim_action: A function called repeatedly until the duration has passed. Don't make it long.
		"""
		self.blit(source, registration, pos, destination, flags, area)
		now = time.time()
		while now < start_time + end_time:
			if interim_action is not None:
				interim_action()
			now = time.time()
		self.flip_callback()
		return now - start_time + end_time

	def pre_bug(self):
		#todo: will be a screen that's shown before anything happens in the program to quickly tweak debug settings
		pass

	def query(self, query=None, as_password=False, font=None, font_size=None, color=None,
				locations=None, registration=5, return_type=None, accepted=None):
		input_config = [None, None, None, None]  # font, font_size, color, bg_color
		query_config = [None, None, None, None]
		vertical_padding = None
		input_location = None
		query_location = None
		query_registration = 8
		input_registration = 2

		# build config argument(s) for __render_text()
		# process the possibility of different query/input font sizes
		if font_size is not None:
			if type(font_size) is (tuple or list):
				if len(font_size) == 2:
					input_config[1] = self.text_layer.font_sizes[font_size[0]]
					query_config[1] = self.text_layer.font_sizes[font_size[1]]
					vertical_padding = query_config[1]
					if input_config[1] < query_config[1]:  # smallest  size =  vertical padding from midline
						vertical_padding = input_config[1]
			else:
				input_config[1] = self.text_layer.font_sizes[font_size]
				query_config[1] = self.text_layer.font_sizes[font_size]
				vertical_padding = self.text_layer.font_sizes[font_size]
		else:
			input_config[1] = self.text_layer.default_font_size
			query_config[1] = self.text_layer.default_font_size
			vertical_padding = self.text_layer.default_font_size

		if registration is not None:
			if type(registration) is (tuple or list):
				input_registration = registration[0]
				query_registration = registration[1]
			else:
				input_registration = registration
				query_registration = registration

		# process the (unlikely) possibility of different query/input fonts
		if type(font) is tuple and len(font) == 2:
			input_config[0] = font[0]
			query_config[0] = font[1]
		elif type(font) is str:
			input_config[0] = font
			query_config[0] = font
		else:
			input_config[0] = self.text_layer.default_font
			query_config[0] = self.text_layer.default_font

		# process the possibility of different query/input colors
		if color is not None:
			if len(color) == 2 and all(isinstance(col, tuple) for col in color):
				input_config[2] = color[0]
				query_config[2] = color[1]
			else:
				input_config[2] = color
				query_config[2] = color
		else:
			input_config[2] = self.text_layer.default_input_color
			query_config[2] = self.text_layer.default_color

		# process locations
		generate_locations = False
		if locations is not None:
			if None in (locations.get('query'), locations.get('input')):
				query_location = self.text_layer.fetch_print_location('query')
				input_location = self.text_layer.fetch_print_location('response')
			else:
				query_location = locations['query']
				input_location = locations['input']
		else:
			generate_locations = True
		# infer locations if not provided (ie. center y, pad x from screen midline) create/ render query_surface
		# Note: input_surface not declared until user input received, see while loop below
		query_surface = None
		if query is None:
			query = self.text_layer.fetch_string('query')

		if query:
			query_surface = self.text_layer.render_text(query, *query_config)
		else:
			raise ValueError("A default query string was not set and argument 'query' was not provided")

		query_baseline = (Params.screen_y // 2) - vertical_padding
		input_baseline = (Params.screen_y // 2) + vertical_padding
		horizontal_center = Params.screen_x // 2
		if generate_locations:
			query_location = [horizontal_center, query_baseline]
			input_location = [horizontal_center, input_baseline]

		self.fill((255, 255, 255))
		self.blit(query_surface, query_registration, query_location)
		self.flip()

		# todo: split this into query_draw() [above code] and query_listen() [remaining code]
		input_string = ''  # populated in loop below
		user_finished = False  # True when enter or return are pressed
		no_answer_string = 'Please provide an answer.'
		invalid_answer_string = None

		if accepted is not None:
			try:
				accepted_iter = iter(accepted)
				accepted_str = pretty_join(accepted, delimiter=",", before_last='or', prepend='[ ', append=']')
				invalid_answer_string = 'Your answer must be one of the following: {0}'.format(accepted_str)
			except:
				raise TypeError("Argument 'accepted' must be iterable.")
		while not user_finished:
			sdl2.SDL_PumpEvents()
			for event in sdl2.ext.get_events():
				if event.type == sdl2.SDL_KEYDOWN:
					if input_string == no_answer_string:
						input_string = ''
					key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
					sdl_keysym = key.keysym.sym
					key_name = sdl2.keyboard.SDL_GetKeyName(sdl_keysym)
					shift_key = False
					self.over_watch(event)

					if sdl2.keyboard.SDL_GetModState() in (sdl2.KMOD_LSHIFT, sdl2.KMOD_RSHIFT, sdl2.KMOD_CAPS):
						shift_key = True
					if sdl_keysym == sdl2.SDLK_BACKSPACE:  # ie. backspace
						if input_string:
							input_string = input_string[0:(len(input_string) - 1)]
							render_string = None
							if as_password is True and len(input_string) != 0:
								render_string = len(input_string) * '*'
							else:
								render_string = input_string

							if len(render_string) > 0:
								input_surface = self.text_layer.render_text(render_string, *input_config)
								self.fill()
								self.blit(query_surface, query_registration, query_location)
								self.blit(input_surface, input_registration, input_location)
								self.flip()
							else:
								self.fill()
								self.blit(query_surface, query_registration, query_location)
								self.flip()
					elif sdl_keysym in (sdl2.SDLK_RETURN, sdl2.SDLK_RETURN):  # ie. if enter or return
						invalid_answer = False
						empty_answer = False
						if len(input_string) > 0:
							if accepted:   # to make the accepted list work, there's a lot of checking yet to do
								if input_string in accepted:
									user_finished = True
								else:
									invalid_answer = True
							else:
								user_finished = True
						else:
							empty_answer = True
						if invalid_answer or empty_answer:
							error_string = ""
							if invalid_answer:
								error_string = invalid_answer_string
							else:
								error_string = no_answer_string
							error_config = copy(input_config)
							error_config[2] = self.text_layer.alert_color
							input_surface = self.text_layer.render_text(error_string, *error_config)
							self.fill()
							self.blit(query_surface, query_registration, query_location)
							self.blit(input_surface, input_registration, input_location)
							self.flip()
							input_string = ""
					elif sdl_keysym == sdl2.SDLK_ESCAPE:  # if escape, erase the string
						input_string = ''
						input_surface = self.text_layer.render_text(input_string, *input_config)
						self.fill()
						self.blit(query_surface, query_registration, query_location)
						self.blit(input_surface, input_registration, input_location)
						self.flip()
					else:
						if key_name not in (MOD_KEYS):  # TODO: probably use sdl keysyms as keys instead of key_names
							if shift_key:
								input_string += key_name
							else:
								input_string += key_name.lower()
							input_surface = None
							if as_password:
								if as_password is True and len(input_string) != 0:
									password_string = '' + len(input_string) * '*'
									input_surface = self.text_layer.render_text(password_string, *input_config)
								else:
									input_surface = self.text_layer.render_text(input_string, *input_config)
							else:
								input_surface = self.text_layer.render_text(input_string, *input_config)
							self.fill()
							self.blit(query_surface, query_registration, query_location)
							self.blit(input_surface, input_registration, input_location)
							self.flip()
						# else:
						# 	pass  # until a key-up event occurs, could be a ui request (ie. quit, pause, calibrate)
				elif event.type is sdl2.SDL_KEYUP:
					self.over_watch(event)
		self.fill()
		self.flip()
		if return_type in (int, str):
			if return_type is int:
				return int(input_string)
			if return_type is str:
				return str(input_string)
		else:
			return input_string

	def quit(self):
		try:
			self.database.db.commit()
		except:  # TODO: Determine exception type
			print "Commit() to self.database failed."
		try:
			self.database.db.close()
		except:  # TODO: Determine exception tpye
			print "Database.close() unsuccessful."
		try:
			self.eyelink.stopRecording()
		except:
			print "EyeLink.stopRecording()  unsuccessful.\n ****** MANUALLY STOP RECORDING PLEASE & THANKS!! *******"

		sdl2.SDL_Quit()
		sys.exit()

	def run(self, *args, **kwargs):
		self.__experiment_manager(*args, **kwargs)

	def start(self):
		self.start_time = time.time()

	def fill(self, color=None, context=None):
		# todo: consider adding sdl2's "area" argument, to fill a subset of the surface
		if color is None:
			color = Params.default_fill_color

		if len(color) == 3:
			color = rgb_to_rgba(color)

		gl_color = [0] * 4
		for i in range(0, 4):
			gl_color[i] = 0 if color[i] == 0 else color[i] / 255.0
		gl.glClearColor(gl_color[0], gl_color[1], gl_color[2], gl_color[3])
		gl.glClear(gl.GL_COLOR_BUFFER_BIT)

	def clear(self, color=None):
		if color is None:
			color = Params.default_fill_color
		self.fill(color)
		self.flip()
		self.fill(color)
		self.flip()

	@property
	def db_name(self):
		return self.__db_name

	@db_name.setter
	def db_name(self, db_name):
		self.__db_name = db_name

	@property
	def event_code_generator(self):
		return self.__event_code_function

	@event_code_generator.setter
	def event_code_generator(self, event_code_function):
		if type(event_code_function).__name__ == 'function':
			self.__event_code_function = event_code_function
		elif event_code_function is None:
			self.__event_code_function = None
		else:
			raise ValueError('App.codeFunc must be set to a function.')

	@property
	def no_tracker(self):
		return self.__no_tracker

	@no_tracker.setter
	def no_tracker(self, no_tracker):
		if type(no_tracker) is bool:
			self.__no_tracker = no_tracker
		else:
			raise ValueError('App.noTracker must be a boolean value.')

	@property
	def participant_instructions(self):
		pass

	@participant_instructions.getter
	def participant_instructions(self):
		return self.participant_instructions

	@participant_instructions.setter
	def participant_instructions(self, instructions_file):
		with open("ExpAssets/participant_instructions.txt", "r") as ins_file:
			self.participant_instructions = ins_file.read()

	@abc.abstractmethod
	def clean_up(self):
		return

	@abc.abstractmethod
	def setup(self):
		pass

	@abc.abstractmethod
	def trial(self, trial_factors, trial_num):
		pass

	@abc.abstractmethod
	def trial_prep(self):
		pass

	@abc.abstractmethod
	def trial_clean_up(self):
		pass

	@abc.abstractmethod
	def flip_callback(self, **kwargs):
		pass