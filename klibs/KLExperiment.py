# -*- coding: utf-8 -*-
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
from KLAudio import AudioManager
from KLEyeLink import *
from KLExceptions import *
from KLNumpySurface import *
from KLDatabase import *
from KLKeyMap import KeyMap
from KLTextManager import TextManager
from KLUtilities import *
import KLParams as Params
from KLConstants import *
from KLELCustomDisplay import ELCustomDisplay
from KLDraw import *
from KLTrialFactory import TrialFactory
import AppKit


#  TODO: Pull all the interface commands, keymaps, overwatch, etc. into KLInterface and stick it on a separate process
#  TODO: Multiprocessing

class Experiment(object):
	"""
	Initializes a KLExperiment Object

	:param project_name: Project title, used in creating filenames and instance variables.
	:type project_name: String
	:param asset_path: Path to assets directory if assets directory is not in default location.
	:type asset_path: String
	:param export: ``DEPRECATED`` Provides instructions to export current data instead of running the experiment as normal
	:type export: Boolean or List of Booleans
	:raise EnvironmentError:
	"""

	__completion_message = "thanks for participating; please have the researcher return to the room."
	__wrong_key_msg = None
	window = None
	paused = False

	# runtime KLIBS modules  
	eyelink = None        # KLEyeLink instance
	database = None       # KLDatabase instance
	trial_factory = None  # KLTrialFactory instance
	text_manager = None   # KLTextManager instance
	debug = {}

	def __init__(self, project_name, display_diagonal_in, random_seed, export, development_mode, eyelink_available):
		"""
		Initializes a KLExperiment Object

		:param project_name: Project title, used in creating filenames and instance variables.
		:type project_name: String
		:param asset_path: Path to assets directory if assets directory is not in default location.
		:type asset_path: String
		:param export: ``DEPRECATED`` Provides instructions to export current data instead of running the experiment as normal
		:type export: Boolean or List of Booleans
		:raise EnvironmentError:
		"""

		super(Experiment, self).__init__()

		if development_mode:
			Params.development_mode = True
			Params.collect_demographics = False

		if not eyelink_available:
			Params.eye_tracker_available = False

		if not Params.setup(project_name, random_seed):
			raise EnvironmentError("Fatal error; Params object was not able to be initialized for unknown reasons.")

		#initialize the self.database instance
		try:
			iterable = iter(export)
		except:
			export = [export]
		self.__database_init(*export)
		Params.key_maps["*"] = KeyMap("*", [], [], [])
		Params.key_maps["over_watch"] = KeyMap("over_watch", [], [], [])
		Params.key_maps["drift_correct"] = KeyMap("drift_correct", ["spacebar"], [sdl2.SDLK_SPACE], ["spacebar"])
		Params.key_maps["eyelink"] = KeyMap("eyelink",
											["a", "c", "v", "o", "return", "spacebar", "up", "down", "left", "right"],
											[sdl2.SDLK_a, sdl2.SDLK_c, sdl2.SDLK_v, sdl2.SDLK_o, sdl2.SDLK_RETURN,
											 sdl2.SDLK_SPACE, sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT,
											 sdl2.SDLK_RIGHT],
											["a", "c", "v", "o", "return", "spacebar", "up", "down", "left", "right"])
		Params.time_keeper.start("Trial Generation")
		self.trial_factory = TrialFactory(self)
		if Params.manual_trial_generation is False:
			self.trial_factory.import_stim_file(Params.config_file_path)
			self.trial_factory.generate()
		Params.time_keeper.stop("Trial Generation")

		self.event_code_generator = None

		# initialize screen surface and screen parameters
		self.display_init(display_diagonal_in)

		# initialize the text management for the experiment
		self.text_manager = TextManager(Params.ppi)
		if Params.default_font_size:
			self.text_manager.default_font_size = Params.default_font_size

		# initialize audio management for the experiment
		self.audio = AudioManager(self)

		# initialize eyelink
		self.eyelink = EyeLink(self)
		self.eyelink.custom_display = ELCustomDisplay(self, self.eyelink)
		self.eyelink.dummy_mode = Params.eye_tracker_available is False

		if not Params.collect_demographics:
			self.collect_demographics(True)

	def __execute_experiment(self, *args, **kwargs):
		"""
		Private method, launches and manages the experiment after KLExperiment object's run() method is called.

		:param args:
		:param kwargs:
		"""

		phases = 2 if Params.practicing else 1
		Params.time_keeper.start("trial_execution")
		for i in range(phases):
			practicing = phases == 2 and i == 1
			for block in self.trial_factory.export_trials(practicing):
				Params.recycle_count = 0
				Params.block_number = block[0]
				self.block(block[0])    # ie. block number
				for trial in block[1]:  # ie. list of trials
					try:
						self.__trial(trial)
					except TrialException as e:
						block[1].recycle()
						Params.recycle_count += 1
						Params.tk.log(e.message)
						self.database.current(False)
						self.clear()
		Params.time_keeper.stop("trial_execution");
		self.clean_up()
		self.database.db.commit()
		self.database.db.close()


	def __trial(self, *args, **kwargs):
		"""
		Private method; manages a trial. Expected \*args = [trial_number, [practicing, param_1, param_2...]]

		"""
	
		args = args[0]
		self.debug['trial_factors'] = args[1]
		# try:
		if args[1][0] is True:  # ie. if practicing
			block_base = (Params.block_number * Params.trials_per_practice_block) - Params.trials_per_practice_block 
			Params.trial_number = block_base + args[0] + 1 - Params.recycle_count
		else:
			block_base = (Params.block_number * Params.trials_per_block) - Params.trials_per_block 
			Params.trial_number =   block_base + args[0] - Params.recycle_count
		self.trial_prep(args[1])
		try:
			trial_data = self.trial(args[1])
			trial_id = self.__log_trial(trial_data)
			self.trial_clean_up(trial_id, args[1])
		except TrialException as e:
			self.trial_clean_up(False, args[1])
			raise e


	def __database_init(self, *args):
		"""
		Initializes the project database; if export instructions are provided, also exports data and exits program.

		:param args:
		"""
		#  todo: probably, should just be a global variable called database, but I didn't want to implement just now
		self.database = Database()
		Params.database = self.database
		if args[0]:
			self.database.export(*args[1:])
			exit()

	def __log_trial(self, trial_data, auto_id=True):
		"""
		Private method, should not be called by user; use KLExperiment.log()

		:param trial_data:
		:param auto_id:
		"""

		if auto_id: trial_data[Params.id_field_name] = Params.participant_id
		if self.database.current() is None: self.database.init_entry('trials', "trial_{0}".format(Params.trial_number))
		for attr in trial_data: self.database.log(attr, trial_data[attr])
		return self.database.insert()
	
	def debug_print_trial_factors(self):
		print  "debug trial factors"
		msg = "Trial Factors: {0}".format(", ".join(self.debug["trial_factors"]))
		self.message(msg, location=[10,10], font_size=32, color=(255,255,255,255), bg_color=(126,126,126,255), flip=False)

	def display_init(self, diagonal_in):
		"""
		Creates an `SDL2 window object <http://pysdl2.readthedocs.org/en/latest/modules/sdl2ext_window.html>`_ in which the project runs.
		This is also the window object passed to :mod:`~klibs.KLELCustomDisplay`.\ :class:`~klibs.KLELCustomDisplay.ELCustomDisplay` instance.

		:param diagonal_in: The diagonal length of the monitor's viewable area.
		:type diagonal_in: Int or Float
		:raise TypeError:
		"""

		sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
		sdl2.mouse.SDL_ShowCursor(sdl2.SDL_DISABLE)
		sdl2.SDL_PumpEvents()
		screens = 0
		for screen in AppKit.NSScreen.screens():
			screens += 1
			if screens > 1:
				pass
				# TODO: throw an error
			else:
				Params.screen_x = int(screen.frame().size.width)
				Params.screen_y = int(screen.frame().size.height)
				Params.screen_x_y = [Params.screen_x, Params.screen_y]
		self.window = sdl2.ext.Window(Params.project_name, Params.screen_x_y, (0, 0), SCREEN_FLAGS)
		Params.screen_diagonal_in = diagonal_in
		Params.screen_c = (Params.screen_x / 2, Params.screen_y / 2)
		Params.diagonal_px = int(math.sqrt(Params.screen_x * Params.screen_x + Params.screen_y * Params.screen_y))
		Params.ppi = Params.diagonal_px // diagonal_in
		Params.monitor_x = Params.screen_x / Params.ppi
		Params.monitor_y = Params.screen_y / Params.ppi
		Params.screen_degrees_x = math.degrees(math.atan((2.55 * Params.monitor_x / 2.0) / Params.view_distance) * 2)
		Params.pixels_per_degree = Params.screen_x // Params.screen_degrees_x
		Params.ppd = Params.pixels_per_degree  # alias for convenience

		# these next six lines essentially assert a 2d, pixel-based rendering context; copied-and-pasted from Mike!
		gl_context = sdl2.SDL_GL_CreateContext(self.window.window)
		gl.glMatrixMode(gl.GL_PROJECTION)
		gl.glLoadIdentity()
		gl.glOrtho(0, Params.screen_x, Params.screen_y, 0, 0, 1)
		gl.glMatrixMode(gl.GL_MODELVIEW)
		gl.glDisable(gl.GL_DEPTH_TEST)
		self.clear()
		pump()

		self.fill()
		try:
			self.blit(NumpySurface("splash.png"), 5, 'center')
		except :
			print "splash.png not found; splash screen not presented"
		self.flip(2)

	def alert(self, alert_string, blit=True, display_for=0):
		"""
		Convenience function wrapping
		:mod:`~klibs.KLExperiment`.\ :class:`~klibs.KLExperiment.Experiment`.\ :func:`~klibs.KLExperiment.Experiment.message`
		``Alert_string`` is formatted as 'warning' text (ie. red, large, screen center).

		:param alert_string: Message to display as alert.
		:type alert_string: String
		:param blit: Return surface or :func:`~klibs.KLExperiment.Experiment.blit` automatically
		:type blit: Bool
		:param display_for: Number of seconds to display the alert message for (overrides 'any key' dismissal).
		:type display_for: Int

		"""
		# todo: instead hard-fill, "separate screen" flag; copy current surface, blit over it, reblit surf or fresh
		# todo: address the absence of default colors



		self.clear()
		self.fill(Params.default_fill_color)
		self.message(alert_string, color=(255, 0, 0, 255), location='center', registration=5,
					 font_size=self.text_manager.default_font_size * 2, blit=True)
		if display_for > 0:
			start = time.time()
			self.flip()
			while (time.time() - start) < display_for:
				pass
			return
		else:
			self.listen()  # remember that listen calls flip() be default

	def blit(self, source, registration=7, position=(0, 0), context=None):
		"""
		Draws passed content to display buffer.

		:param source: Image data to be buffered.
		:type source: :class:`~klibs.KLNumpySurface.NumpySurface`, :class:`~klibs.KLDraw.Drawjbect`, Numpy Array, or `PIL.Image <http://pillow.readthedocs.org/en/3.0.x/reference/Image.html>`_
		:param registration: Location on perimeter of surface that will be aligned to position (see manual for more information).
		:type registration: Int
		:param position: Location on screen to place source, either pixel coordinates or location string (ie. "center", "top_left")
		:type position: String or iterable
		:param context: ``NOT IMPLEMENTED`` A destination surface or display object for images built gradually.

		:raise TypeError:
		"""

		height = None
		width = None
		content = None
		if type(source) is NumpySurface:
			height = source.height
			width = source.width
			content = source.render()
		elif issubclass(type(source), Drawbject):
			height = source.surface_height
			width = source.surface_width
			# source.draw()
			content = source.render().render()
		elif type(source) is numpy.ndarray:
			height = source.shape[0]
			width = source.shape[1]
			content = source
		else:
			raise TypeError("Argument 'source' must be numpy.ndarray, klibs.KLNumpySurface.NumpySurface, or inherit from klibs.KLDraw.Drawbect.")

		# configure OpenGL for blit
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		t_id = gl.glGenTextures(1)
		gl.glBindTexture(gl.GL_TEXTURE_2D, t_id)
		gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
		gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, content)
		gl.glEnable(gl.GL_TEXTURE_2D)
		gl.glBindTexture(gl.GL_TEXTURE_2D, t_id)
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

		if 0 < registration < 10:
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
		gl.glDeleteTextures([t_id])
		del t_id
		gl.glDisable(gl.GL_TEXTURE_2D)

	def block_break(self, message=None):
		"""
		Display a break message between blocks

		:flag: heavy_modification_planned
		:flag: removal_possible

		:param message: Text to be displayed during break.
		:type message: String
		"""
		if Params.block_number == 1:
			return
		default = "Whew! You've completed block {0} of {1}. When you're ready to continue, press any key.".format(
			Params.block_number - 1, Params.blocks_per_experiment)
		if Params.testing: return
		if not message: message = default
		self.fill()
		self.message(message, location='center', registration=5)
		self.listen()

	def collect_demographics(self, anonymous_user=False):
		"""
		Gathers participant demographic information and enter it into the project database.
		Should not be explicitly called; see ``Params.collect_demographics``.

		:param anonymous_user: Toggles generation of arbitrary participant info in lieu of participant-supplied info.
		:type anonymous_user: Boolean
		"""

		# TODO: this function should have default questions/answers but should also be able to read from a CSV or dict
		if not Params.collect_demographics and not anonymous_user: return

		self.database.init_entry('participants', instance_name='ptcp', set_current=True)
		self.database.log("random_seed", Params.random_seed)
		if anonymous_user:
			name = Params.anonymous_username
		else:
			name_query_string = self.query(
				'What is your full name, banner number or e-mail address? \nYour answer will be encrypted and cannot be read later.',
				password=True)
			name_hash = hashlib.sha1(name_query_string)
			name = name_hash.hexdigest()
		self.database.log('userhash', name)

		# names must be unique; returns True if unique, False otherwise
		if self.database.is_unique('participants', 'userhash', name):
			if anonymous_user:
				sex = "m" if time.time() % 2 > 0  else "f"
				handedness = "a"
				age = 0
			else:
				sex_str = "What is your sex? \nAnswer with:  (m)ale,(f)emale"
				sex = self.query(sex_str, accepted=('m', 'M', 'f', 'F'))
				handedness_str = "Are right-handed, left-handed or ambidextrous? \nAnswer with (r)ight, (l)eft or (a)mbidextrous."
				handedness = self.query(handedness_str, accepted=('r', 'R', 'l', 'L', 'a', 'A'))
				age = self.query('What is  your age?', return_type='int')
			self.database.log('sex', sex)
			self.database.log('handedness', handedness)
			self.database.log('age', age)
			self.database.log('created', now(True))
			if not Params.demographics_collected:
				Params.participant_id = self.database.insert()
				Params.demographics_collected = True
			else:
				#  The context for this is: collect_demographics is set to false but then explicitly called later
				self.database.update(Params.participant_id)
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
		self.database.current(False)

	def drift_correct(self, location=None, events=EL_TRUE, samples=EL_TRUE):
		"""
		Performs a drift correction, or simulates one via the mouse when eye tracker is unavailable.
		Wraps method of same name in
		:mod:`~klibs.KLEyeLink`.\ :class:`~klibs.KLEyeLink.EyeLink`.\ :func:`~klibs.KLEyeLink.EyeLink.drift_correct`
		and original PyLink method.

		:flag: canonical_wrapper

		:param location: X-Y Location of drift correct target; if not provided, defaults to screen center.
		:type location: Iterable of Integers
		:param events: see PyLink documentation
		:param samples: see PyLink documentation
		:return Eyelink response code; see `PyLink documentation<http:kleinlab.psychology.dal.ca/pylink`_:
		"""

		self.clear()
		return self.eyelink.drift_correct(location, events, samples)

	def draw_fixation(self, location=BL_CENTER, size=None, stroke=None, color=None, fill_color=None, flip=False):
		"""
		Creates and renders a FixationCross (see :mod:`~klibs.KLDraw` inside an optional background circle at provided or
		default location.

		:flag: heavy_modification_possible
		:flag: relocation_planned

		:param location: X-Y Location of drift correct target; if not provided, defaults to screen center.
		:type location: Interable of Integers or `Relative Location Constant`
		:param size: Width and height in pixels of fixation cross.
		:type size: Integer
		:param stroke: Width in pixels of the fixation cross's horizontal & vertical bars.
		:type stroke: Integer
		:param color: Color of fixation cross as rgb or rgba values (ie. (255, 0, 0) or (255, 0, 0, 125).
		:type color: Iterable of Integers
		:param fill_color: Color of background circle as iterable rgb or rgba values; default is None.
		:type color: Iterable of Integers
		:param flip: Toggles automatic flipping of display buffer, see :func:`~klibs.KLExperiment.Experiment.flip``.
		"""

		if not size: size = Params.screen_y // 50
		if not stroke: stroke = size // 5
		cross = FixationCross(size, stroke, color, fill_color).draw()
		self.blit(cross, 5, absolute_position(location))
		if flip: self.flip()
		return True

	def exempt(self, index, state=True):
		"""
		:flag: deprecated

		.. warning:: This function is deprecated and slated for removal; do not use.
		"""
		if index in self.exemptions.keys():
			if state == 'on' or True:
				self.exemptions[index] = True
			if state == 'off' or False:
				self.exemptions[index] = False

	def flip(self, duration=0):
		"""
		Transfers content of draw buffer to current display then waits for either of:
		 - any key press
		 - a specified duration (if defined).

		:param duration: Duration in ms for which to display flipped buffer.
		:type duration: Integer
		:raises: AttributeError, TypeError
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

	def add_keymap(self, name, ui_labels=None, data_labels=None, sdl_keysyms=None):
		"""
		A convenience method that creates a :mod:`~klibs.KLKeyMap`.\ :class:`~klibs.KLKeyMap.KeyMap` instance from
		supplied information.

		:flag: relocation_planned

		Equivalent to::

			Params.key_maps['name'] = KLKeyMap.KeyMap(name, ui_labels, data_labels, sdl_keysyms)

		:param name: Name reference for the keymap (ie. 'response_keys' )
		:type name: String
		:param ui_labels: Labels for key mappings for human communication purposes (ie. "z", "/")
		:type ui_labels: Iterable of Strings
		:param data_labels: Labels for representing key mappings in a datafile (ie. "RIGHT","LEFT").
		:type data_labels: Iterable of Strings
		:param sdl_keysyms: SDL2 keysym values; see :ref:`sdl_keycode_reference` for complete list.
		:type sdl_keysyms: Iterable of SDL_keysyms
		:return: :class:`~klibs.KLKeyMap.KeyMap` or Boolean
		:raises: TypeError
		"""

		if type(name) is not str:
			raise TypeError("Argument 'name' must be a string.")

		# register the keymap if one is being passed in and set keyMap = name of the newly registered map
		if all(type(key_param) in [tuple, str] for key_param in [ui_labels, data_labels, sdl_keysyms]):
			Params.key_maps[name] = KeyMap(name, ui_labels, data_labels, sdl_keysyms)

		#retrieve registered keymap(s) by name
		if name in Params.key_maps:
			return Params.key_maps[name]
		else:
			return False

	def instructions(self, instructions_text=None):
		"""
		Presents contents of instructions.txt to participant.

		:flag: not_implemented
		:flag: heavy_modification_planned
		:flag: relocation_planned

		:param instructions_text: Instructions text or path to file containing the same; defaults to contents of default instructions.txt file if it exists.
		:type instructions_text: String
		"""

		try:
			self.message(open(instructions_text, 'rt').read(), location=BL_CENTER, flip=True)
		except IOError:
			self.message(instructions_text, location=BL_CENTER, flip=True)
		self.fill()

		self.listen()

	def ui_request(self, key_press, execute=False):
		"""
		Inspects a keypress for interface commands like "quit", "pause", etc.. Primarily used by
		:func:`~klibs.KLExperiment.Experiment.over_watch`; Currently only "quit" is implemented.

		:flag: extension_planned

		:param key_press:
		:param execute:
		:return:
		"""

		if key_press.mod in (MOD_KEYS["Left Command"], MOD_KEYS["Right Command"]):
			if key_press.sym in UI_METHOD_KEYSYMS:
				if key_press.sym == sdl2.SDLK_q:
					kl_quit()
				elif key_press.sym == sdl2.SDLK_c:
					if Params.eye_tracking and Params.eye_tracker_available:
						self.eyelink.calibrate()
				elif key_press.sym == sdl2.SDLK_p:
					if not self.paused:
						self.paused = True
						self.pause()
						return True
					if self.paused:
						self.paused = False
						return False
		return False

	def listen(self, max_wait=MAX_WAIT, key_map_name="*", el_args=None, null_response=None, response_count=None,
			   interrupt=True, flip=True, wait_callback=None, *wait_args, **wait_kwargs):
		"""
		Used for interacting with the participant via key presses; this is the primary method for collecting responses of any kind. See manual for extensive documentation.

		.. warning:: This method is slated for removal and will be completely replaced with the module ``KLListener`` in a future release.

		:flag: relocation_planned
		:flag: heavy_modification_planned
		:flag: backwards_compatibility_planned

		:param max_wait: Maximum time in seconds to await participant response. Default is an indefinite period.
		:type max_wait: Integer
		:param key_map_name: Reference name of the :class:`~klibs.KLKeyMap.KeyMap` instance to be used for handling participant responses.
		:type key_map_name: String
		:param el_args: Keyword arguments to be passed to :func:`~klibs.KlExperiment.Experiment.listen`.`ToDo: Detailed documentation on this`
		:type el_args: Dict
		:param null_response: Response to be returned on timeout, default is "NO_RESPONSE"
		:type null_response: Any
		:param response_count: ``NOT IMPLEMENTED`` Number of responses to collect from participant. Default is 1.
		:type response_count: Integer
		:param interrupt: When True, response is returned as soon as it is collected, otherwise allows max_wait to elapse. Default is True.
		:type interrupt: Boolean
		:param flip: Toggles automatic flipping of display buffer on initiating the listen loop.
		:type flip: Boolean
		:param wait_callback: Function to execute between each loop of listen.
		:type wait_callback: Function
		:param wait_args: Required arguments to be passed to wait_callback.
		:type wait_args: List or Tuple
		:param wait_kwargs: Key word arguments to be passed to  wait_callback.
		:type wait_kwargs: Dict
		:raise RuntimeError:
		:return: List
		"""

		exit_msg_thresh = 2
		# Add this to detailed documentation "Note: When False, creates a very small performance loss (>1ms) as KLExperiment.overwatch() is called to inspect the response before it is evaluated by the supplied KLKeyMap."
		# todo: listen is not a method; it should be a class, "listener", that gets configured
		# TODO: response_count should be a real thing
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
			key_map = Params.key_maps[key_map_name]
		except KeyError:
			if key_map_name is None:
				key_map = None
			elif key_map_name is str:
				raise KeyError("Argument 'key_map_name' did not match any registered KeyMap.")
			else:
				raise TypeError("Argument 'key_map_name' must be a string corresponding to a registered KeyMap.")
		response = None
		rt = -1

		start_time = time.time()
		waiting = True

		# enter with a clean event queue
		sdl2.SDL_PumpEvents()
		sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)  # upper/lower bounds of event queue,
		# ie. flush all
		if flip:
			self.flip()  # executed as close to wait loop as possible for minimum delay between timing and presentation

		key = None
		sdl_keysym = None
		key_name = None
		wrong_key = False
		# then = time.time()
		while waiting:
			# now = time.time()
			# then = now
			try:
				self.eyelink.listen(**el_args)
			except TypeError:
				self.eyelink.listen()

			sdl2.SDL_PumpEvents()
			if wait_callback:
				# try:
				wait_resp = wait_callback(*wait_args, **wait_kwargs)
				if wait_resp:
					waiting = False
					return [wait_resp, time.time() - start_time]
				# except Exception as e:
				# 	err_message = "wait callback failed with following message: {0}".format(e.message)
				# 	raise RuntimeError(err_message)
					# raise sys.exec_info[0], sys.exec_info[1], sys.exec_info[2]

			for event in sdl2.ext.get_events():
				if event.type == sdl2.SDL_KEYDOWN:
					rt = time.time() - start_time
					if not response:  # only record a response once per call to listen()
						key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
						sdl_keysym = key.keysym.sym
						key_name = sdl2.keyboard.SDL_GetKeyName(sdl_keysym)
						if key_map is not None:
							valid = key_map.validate(sdl_keysym)
						else:
							valid = False
						if valid:  # a KeyMap with name "*" (ie. any key) returns self.ANY_KEY
							response = key_map.read(sdl_keysym, "data")
							if interrupt:  # ONLY for TIME SENSITIVE reactions to participant response; this flag
							# voids overwatch()
								return [response, rt]
						else:
							if key_map is not None:
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
				return [TIMEOUT, -1]
		if not response:
			if null_response:
				return [null_response, rt]
			else:
				return [NO_RESPONSE, rt]
		else:
			return [response, rt]

	def message(self, message, font=None, font_size=None, color=None, bg_color=None, location=None, registration=None,
				wrap=None, wrap_width=None, line_delimiter=None, blit=True, flip=False, padding=None):
		# todo: padding should be implemented as a call to resize() on message surface; but you have to fix wrap first
		"""
		Generates and optionally renders formatted text to the display.

		.. warning:: This method will take a single argument, a KLTextManager.TextStyle object, in a future release. Backwards compatibility is tentatively planned.

		:flag: heavy_modification_planned
		:flag: backwards_compatibility_planned

		:param message: Text to be displayed.
		:type message: String
		:param font: Name of font to be used. Default is Helvetica. Must be a font installed on the system.
		:type font: String
		:param font_size: Font size in points to be used for the message text; default is :class:`~klibs.KLParams`.\ `default_font_size`.
		:type font_size: Integer
		:param color: Color of message text in rgb or rgba values; default is :class:`~klibs.KLParams`.\ default_color.
		:type color: Iterable of Integers
		:param bg_color: Background color of message text in rgb or rgba values; default is :class:`~klibs.KLParams`.\ default_bg_color.
		:type color: Iterable of Integers
		:param location: X-Y coordinates where the message should be placed. Default is screen center.
		:type location: Iterable of Integers or `Location Constant`
		:param registration: Location about message surface perimeter to be placed at supplied location. Default is center.
		:type registration: Integer
		:param wrap: When True, text will wrap when edge of screen is reached, or if line reaches wrap_width.
		:type wrap: Boolean
		:param wrap_width: Maximum width (px) of text line before breaking.
		:type wrap_width: Integer
		:param line_delimiter: Symbol or string indicating a line break. Default is unix new line operator, ie. "\\n".
		:type line_delimiter: String
		:param blit: Toggles whether message surface is automatically :func:`~klibs.KLExperiment.Experiment.blit` to the display buffer.
		:type blit: Boolean
		:param flip: Toggles whether :func:`~klibs.KLExperiment.Experiment.flip` is automatically called after blit.
		:type flip: Boolean
		:param padding: Width of white space (px) surrounding the message surface on all sides.
		:type padding: Integer
		:return: NumpySurface or Boolean
			"""

		render_config = {}
		message_surface = None  # unless wrap is true, will remain empty

		if font is None:
			font = self.text_manager.default_font

		if font_size is None:
			font_size = self.text_manager.default_font_size

		if color is None:
			if self.text_manager.default_color:
				color = self.text_manager.default_color

		if bg_color is None:
			bg_color = self.text_manager.default_bg_color

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
				raise ValueError(
					"Argument 'location' invalid; must be a location string, coordinate tuple, or NoneType")

		if not blit:
			if wrap:
				return message_surface
			else:
				message_surface = self.text_manager.render_text(message, render_config)
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
				message_surface = self.text_manager.render_text(message, font, font_size, color, bg_color)
				# if message_surface.shape[1] > self.screen_x:
				# 	wrap = True
				# 	return self.message(message, font, font_size, color, bg_color, location, registration,
				# 						wrap, wrap_width, delimiter, blit, flip)
				self.blit(message_surface, registration, location)
			if flip:
				self.flip()
		return True

	def numpy_surface(self, foreground=None, background=None, fg_position=None, bg_position=None, width=None,
					  height=None):
		"""
		Factory method for :func:`~klibs.KLNumpySurface.NumpySurface`.

		:param fg_position: Pixel coordinates or location identifier of foreground content. Will non-destructively clip content it extends beyond surface edges.
		:param bg_position: (see fg_position)
		:param foreground: Foreground content; must be a path to an image file, a numpy array of pixel data or another KLNumpySurface.
		:param background: (see foreground)
		:param width: If provided manually sets the width in pixels of surface.
		:param height: If provided manually sets the height in pixels of surface.
		:return:
		"""

		return NumpySurface(foreground, background, fg_position, bg_position, width, height)

	def over_watch(self, keypress_event=None):
		"""
		Inspects keypress events for interface requests (ie.  'quit', 'calibrate', 'pause', etc.) and executes them. When called without event argument, pumps and inspects the entire event queue, otherwise inspects only the supplied event.

		:param keypress_event: An sdl2.
		:return:
		"""

		input_collected = False
		repumping = False  # only repump once else holding a modifier key down can keep overwatch running forever
		keysym = None
		sym = None
		mod_name = None
		key_name = None
		event_stack = None
		if keypress_event is None:
			event_stack = sdl2.SDL_PumpEvents()
			if type(event_stack) is list:
				event_stack.reverse()
			else:
				return False  # ie. app is in a passive context and no input is happening
		else:
			event_stack = [keypress_event]
		while not input_collected:
			keypress_event = event_stack.pop()
			if keypress_event.type in [sdl2.SDL_KEYUP, sdl2.SDL_KEYDOWN]:
				keysym = keypress_event.key.keysym
				sym = keysym.sym  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
				key_name = sdl2.keyboard.SDL_GetKeyName(sym)
				if keypress_event.type == sdl2.SDL_KEYUP:  # modifier or no, a key up event implies user decision; exit loop
					input_collected = True
				if key_name not in MOD_KEYS:  # if event key isn't a modifier: get key info & exit loop
					mod_name = sdl2.keyboard.SDL_GetModState()
					input_collected = True
				elif repumping and keypress_event.repeat != 0:  # user holding mod key; return control to calling method calling
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
		"""
		Pauses an experiment.

		.. rst-class:: method-flags

			broken, heavy_modification-planned, backwards_compatibility-expected, interface-command

		"""

		pump()
		while self.paused:
			self.message('PAUSED', fullscreen=True, location='center', font_size=96, color=(255, 0, 0, 255),
						 registration=5, blit=False)
			self.over_watch()
			self.listen_refresh()

	def project_config(self):
		"""
		Global configuration of project settings. Slated for future release.

		.. rst-class:: method-flags

			not-implemented

		"""

		#todo: will be a screen that's shown before anything happens in the program to quickly tweak debug settings
		pass

	def query(self, query=None, password=False, font=None, font_size=None, color=None, locations=None, registration=5, return_type=None, accepted=None):
		"""
		Convenience function for collecting participant input with real-time visual feedback.

		Presents a string (ie. a question or response instruction) to the participant. Then listens for keyboard input
		and displays the participant's response on screen in real time.

		Experiment.query() makes two separate calls to Experiment.message(), which allows for query text and response
		text to be formatted independently. All of the formatting arguments can optionally be length-2 lists of the
		usual parameters, where the first element would be applied to the query string and the second to the response.
		If normal formatting values are supplied, they are applied to both the query and response text.

		.. rst-class:: method-flags

			relocation-planned, backwards_compatibility-planned

		:param query: A string of text to present to the participant usually a question or instruction about desired
		input.
		:param password: When true participant input will appear on screen in asterisks, though real key presses are
		recorded.
		:param font: See Experiment.message()
		:param font_size: See Experiment.message()
		:param color: See Experiment.message()
		:param locations:
		:param registration:
		:param return_type:
		:param accepted:
		:return: boolean
		:raise TypeError:

		**Example**


		The following::

			question = "What is your name?"
			font = "Helvetica"
			sizes = [24,16]
			colors = [rgb(0,0,0), rgb(255,0,0)]
			self.query(question, font=font_name, font_size=sizes, color=colors)


		Produces this formatting structure:

			+----------+-------------+---------+-----------+
			|**string**|**font size**|**color**| **font**  |
			+----------+-------------+---------+-----------+
			| query    |     24pt    | black   | Helvetica |
			+----------+-------------+---------+-----------+
			| response |   16pt      | red     | Helvetica |
			+----------+-------------+---------+-----------+

		*Note: As with Experiment.message() <#message_def> this method will eventually accept a TextStyle object
		instead of the formatting arguments currently implemented.*

		"""
		# TODO: 'accepted' might be better as a KLKeyMap object? Or at least more robust than a list of letters?

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
					input_config[1] = self.text_manager.font_sizes[font_size[0]]
					query_config[1] = self.text_manager.font_sizes[font_size[1]]
					vertical_padding = query_config[1]
					if input_config[1] < query_config[1]:  # smallest  size =  vertical padding from midline
						vertical_padding = input_config[1]
			else:
				input_config[1] = self.text_manager.font_sizes[font_size]
				query_config[1] = self.text_manager.font_sizes[font_size]
				vertical_padding = self.text_manager.font_sizes[font_size]
		else:
			input_config[1] = self.text_manager.default_font_size
			query_config[1] = self.text_manager.default_font_size
			vertical_padding = self.text_manager.default_font_size

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
			input_config[0] = self.text_manager.default_font
			query_config[0] = self.text_manager.default_font

		# process the possibility of different query/input colors
		if color is not None:
			if len(color) == 2 and all(isinstance(col, tuple) for col in color):
				input_config[2] = color[0]
				query_config[2] = color[1]
			else:
				input_config[2] = color
				query_config[2] = color
		else:
			input_config[2] = Params.default_response_color
			query_config[2] = Params.default_input_color

		# process locations
		generate_locations = False
		if locations is not None:
			if None in (locations.get('query'), locations.get('input')):
				query_location = self.text_manager.fetch_print_location('query')
				input_location = self.text_manager.fetch_print_location('response')
			else:
				query_location = locations['query']
				input_location = locations['input']
		else:
			generate_locations = True
		# infer locations if not provided (ie. center y, pad x from screen midline) create/ render query_surface
		# Note: input_surface not declared until user input received, see while loop below
		query_surface = None
		if query is None:
			query = self.text_manager.fetch_string('query')

		if query:
			query_surface = self.text_manager.render_text(query, *query_config)
		else:
			raise ValueError("A default query string was not set and argument 'query' was not provided")

		query_baseline = (Params.screen_y // 2) - vertical_padding
		input_baseline = (Params.screen_y // 2) + vertical_padding
		horizontal_center = Params.screen_x // 2
		if generate_locations:
			query_location = [horizontal_center, query_baseline]
			input_location = [horizontal_center, input_baseline]

		self.fill(Params.default_fill_color)
		self.blit(query_surface, query_registration, query_location)
		self.flip()

		# todo: split this into query_draw() [above code] and query_listen() [remaining code]
		input_string = ''  # populated in loop below
		user_finished = False  # True when enter or return are pressed
		no_answer_string = 'Please provide an answer.'
		invalid_answer_string = None
		error_string = None
		if accepted:
			try:
				iter(accepted)
				accepted_str = pretty_join(accepted, delimiter=",", before_last='or', prepend='[ ', append=']')
				invalid_answer_string = 'Your answer must be one of the following: {0}'.format(accepted_str)
			except:
				raise TypeError("Argument 'accepted' must be iterable.")
		while not user_finished:
			sdl2.SDL_PumpEvents()
			for event in sdl2.ext.get_events():
				if event.type not in [sdl2.SDL_KEYUP, sdl2.SDL_KEYDOWN]:
					continue
				self.over_watch(event)
				if event.type == sdl2.SDL_KEYUP:  # don't fetch letter on both events
					continue
				if error_string:
					error_string = None
					input_string = ''
				key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
				sdl_keysym = key.keysym.sym

				self.fill()
				self.blit(query_surface, query_registration, query_location)

				if sdl_keysym == sdl2.SDLK_BACKSPACE:  # ie. backspace
					input_string = input_string[:-1]

				if sdl_keysym in (sdl2.SDLK_KP_ENTER, sdl2.SDLK_RETURN):  # ie. if enter or return
					if len(input_string):
						if accepted:   # to make the accepted list work, there's a lot of checking yet to do
							if input_string in accepted:
								user_finished = True
							else:
								error_string = invalid_answer_string
						else:
							user_finished = True
					else:
						error_string = no_answer_string
					if error_string:
						error_config = copy(input_config)
						error_config[2] = self.text_manager.alert_color
						input_surface = self.text_manager.render_text(error_string, *error_config)
						input_string = ""
				if sdl_keysym == sdl2.SDLK_ESCAPE:  # if escape, erase the string
					input_string = ""
					input_surface = None

				if sdl_key_code_to_str(sdl_keysym):
					input_string += sdl_key_code_to_str(sdl_keysym)
				render_str = len(input_string) * '*' if password else input_string
				if not error_string:  # if error_string, input_surface already created with different config.
					try:
						input_surface = self.text_manager.render_text(render_str, *input_config)
					except IndexError:
						input_surface = None
				if input_surface:
					self.blit(input_surface, input_registration, input_location)
				self.flip()
					# else:
					# 	pass  # until a key-up event occurs, could be a ui request (ie. quit, pause, calibrate)
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
		"""
		Safely exits the program, ensuring data has been saved and that any connected EyeLink unit's recording is stopped. experimenters should use this, not Python's exit().

		"""
		try:
			self.database.db.commit()
		except Exception as e:
			if e.message == "Cannot operate on a closed database.":
				pass
			else:
				print "Commit() to self.database failed."
				raise e
		try:
			self.database.db.close()
		except:  # TODO: Determine exception tpye
			print "Database.close() unsuccessful."
		try:
			self.eyelink.shut_down_eyelink()
		except:
			print "EyeLink.stopRecording()  unsuccessful.\n ****** MANUALLY STOP RECORDING PLEASE & THANKS!! *******"
		try:
			Params.time_keeper.stop("experiment")
		except KeyError:
			pass
		sdl2.SDL_Quit()
		Params.time_keeper.log("exit")
		sys.exit()

	def run(self, *args, **kwargs):
		"""
		Executes the experiment. Experimenters should use this method to launch their program.

		:param args:
		:param kwargs:
		"""
		Params.time_keeper.start("experiment")
		if Params.collect_demographics:
			if not Params.demographics_collected:
				self.collect_demographics()
		elif not Params.demographics_collected:
			self.collect_demographics(True)

		if Params.eye_tracking and Params.eye_tracker_available:
			self.eyelink.setup()
		self.setup()
		self.__execute_experiment(*args, **kwargs)
		self.quit()

	def start(self):
		"""
		Sets KLExperiment.start_time to current time for tidily passing a trial's start time between methods.

		.. rst-class:: method-flags

			relocation-planned, deprecation-possible

		"""

		self.start_time = time.time()

	def track_mouse(self):
		self.blit(cursor(), 7, mouse_pos())
		return True

	def fill(self, color=None, context=None):
		"""
		Clears display buffer to a single color.

		:param color:
		:param context:
		"""

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
		"""
		Clears current display and display buffer with supplied color or else Params.default_fill_color.

		:param color:
		"""

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
	def block(self, block_num):
		pass

	@abc.abstractmethod
	def trial(self, trial_num, trial_factors):
		pass

	@abc.abstractmethod
	def trial_prep(self):
		pass

	@abc.abstractmethod
	def trial_clean_up(self):
		pass
