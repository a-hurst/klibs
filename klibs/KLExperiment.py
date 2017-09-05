# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

from sdl2 import SDL_Quit
from abc import abstractmethod
from os import mkdir
from os.path import join
from shutil import copyfile, copytree

from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import TrialException
from klibs import P
from klibs.KLKeyMap import KeyMap
from klibs.KLUtilities import full_trace, pump, now, list_dimensions, force_quit, show_mouse_cursor, hide_mouse_cursor
from klibs.KLTrialFactory import TrialFactory
from klibs.KLGraphics import flip, blit, fill, clear #, display_init
from klibs.KLDatabase import Database
from klibs.KLUserInterface import any_key
from klibs.KLAudio import AudioManager
# from klibs.KLResponseCollectors import ResponseCollector
from klibs.KLCommunication import message, query, collect_demographics

# from klibs.KLCommunication import  message
# import klibs.eyelink as el
# import klibs.database  as db


class Experiment(EnvAgent):
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

	__completion_message__ = "Thanks for participating; please have the researcher return to the room."
	initialized = False
	window = None
	paused = False

	# runtime KLIBS modules  
	eyelink = None        # KLEyeLink instance
	database = None       # KLDatabase instance
	trial_factory = None  # KLTrialFactory instance
	text_manager = None   # KLTextManager instance
	block_break_message = "Whew! You've completed block {0} of {1}. When you're ready to continue, press any key."
	block_break_messages = []
	blocks = None

	def __init__(self, project_name):
		"""
		Initializes a KLExperiment Object
		:param project_name: Project title, used in creating filenames and instance variables.
		:type project_name: String
		:raise EnvironmentError:
		"""
		super(Experiment, self).__init__()

		# initialize audio management for the experiment
		self.audio = AudioManager()

		self.database = Database()

		self.trial_factory = TrialFactory(self)
		if P.manual_trial_generation is False:
			self.trial_factory.generate()
		self.event_code_generator = None

		self.initialized = True

	def __execute_experiment__(self, *args, **kwargs):
		"""
		Private method, launches and manages the experiment after KLExperiment object's run() method is called.
		:param args:
		:param kwargs:
		"""

		if not self.blocks:
			self.blocks = self.trial_factory.export_trials()
		for block in self.blocks:
			P.recycle_count = 0
			P.block_number = self.blocks.i
			P.practicing = block.practice
			self.block()
			P.trial_number = 1
			for trial in block:  # ie. list of trials
				try:
					try:
						P.trial_id = self.database.last_id_from('trials') + 1
					except TypeError:
						P.trial_id = 1
					self.__trial__(trial, block.practice)
					P.trial_number += 1
				except TrialException:
					block.recycle()
					P.recycle_count += 1
					# self.evm.send('trial_recycled')
					self.database.current(False)
					clear()
				self.rc.reset()
		self.clean_up()
		self.database.db.commit()
		self.database.db.close()

	def __trial__(self, trial, practice):
		"""
		Private method; manages a trial. Expected \*args = [trial_number, [practicing, param_1,...param_n]]
		"""
		pump()
		for p in self.trial_factory.exp_factors:
			attr_name = p[0]
			attr_val = trial[self.trial_factory.exp_factors.index(p)]
			setattr(self, attr_name, attr_val)
		self.setup_response_collector()

		self.trial_prep()
		tx = None
		try:
			if P.development_mode and (P.dm_trial_show_mouse or (P.eye_tracking and not P.eye_tracker_available)):
				show_mouse_cursor()
			self.evm.start_clock()
			if P.eye_tracking and not P.manual_eyelink_recording:
				self.el.start(P.trial_number)
			P.in_trial = True
			self.__log_trial__(self.trial())
			P.in_trial = False
			if P.eye_tracking and not P.manual_eyelink_recording:
				self.el.stop()
			if P.development_mode and (P.dm_trial_show_mouse or (P.eye_tracking and not P.eye_tracker_available)):
				hide_mouse_cursor()
			self.evm.stop_clock()
			self.trial_clean_up()
		except TrialException as e:
			P.trial_id = False
			self.trial_clean_up()
			self.evm.stop_clock()
			tx = e
		if P.eye_tracking and not P.manual_eyelink_recording:
			# todo: add a warning, here, if the recording hasn't been stopped when under manual control
			self.el.stop()
		if tx:
			raise tx

	def __log_trial__(self, trial_data, auto_id=True):
		"""
		Private method, should not be called by user; use KLExperiment.log()
		:param trial_data:
		:param auto_id:
		"""

		if auto_id: trial_data[P.id_field_name] = P.participant_id
		if self.database.current() is None: self.database.init_entry('trials', "trial_{0}".format(P.trial_number))
		for attr in trial_data: self.database.log(attr, trial_data[attr])
		return self.database.insert()

	def before_flip(self):
		if P.eye_tracking and P.eye_tracker_available:
			try:
				if self.el.draw_gaze:
					blit(self.el.gaze_dot, 5, self.el.gaze())
			except AttributeError:
				pass

		# KLDebug in very early stages and not ready for UnitTest branch of klibs; below code may return later
		# if P.development_mode and not P.dm_suppress_debug_pane:
		# 	try:
		# 		self.debug.print_logs(cli=False)
		# 	except AttributeError as e:  # potentially gets called once before the Debugger is intialized during init
		# 		if P.display_initialized:
		# 			raise

	def insert_practice_block(self, block_nums, trial_counts=None, factor_masks=None):
		"""
		Adds one or more practice blocks to the experiment. This function must be called during setup(),
		otherwise the trials will have already been exported and this function will no longer have
		any effect. If you want to add a block to the experiment after setup() for whatever reason,
		you can manually generate one using trial_factory.generate() and then insert it using
		self.blocks.insert().
		
		If multiple block indexes are given but only a single integer is given for trial counts, 
		then all practice blocks inserted will be trial_counts trials long. If not trial_counts 
		value is provided, the number of trials per practice block defaults to the global 
		experiment trials_per_block parameter.

		If multiple block indexes are given but only a single factor mask is provided, the same
		factor mask will be applied to all appended practice blocks. If no factor mask is provided,
		the function will generate a full set of trials based on all possible combination of factors,
		and will randomly select trial_counts trials from it for each practice block.

		:param block_nums: Numbers in the sequence of blocks at which to append practice blocks.
		:type block_nums: Iterable of Ints
		:param trial_counts: Numbers of trials per practice block.
		:type trial_counts: Iterable of Ints
		:param factor_masks: Mask specifying the possible combinations of factors for each practice block.
		:type factor_masks: Iterable of Iterables of Ints
		:raises: TrialException
		"""
		if self.blocks:
			# If setup has passed and trial execution has started, blocks have already been exported
			# from trial_factory so this function will no longer work. If it is called after it is no
			# longer useful, we throw a TrialException
			raise TrialException("Practice blocks cannot be inserted after setup() is complete.")
		try:
			iter(block_nums)
		except TypeError:
			block_nums = [block_nums]
		try:
			iter(trial_counts)
		except TypeError:
			trial_counts = ([P.trials_per_block]  if trial_counts is None else [trial_counts]) * len(block_nums)
		while len(trial_counts) < len(block_nums):
			trial_counts.append(P.trials_per_block)
		if list_dimensions(factor_masks) == 2 or not factor_masks:
			factor_masks = [factor_masks] * len(block_nums)
		for i in range(0, len(block_nums)):
			self.trial_factory.insert_block(block_nums[i], True, trial_counts[i], factor_masks[i])
			P.blocks_per_experiment += 1

	def add_keymap(self, name, ui_labels=None, data_labels=None, sdl_keysyms=None):
		"""
		``relocation_planned``
		A convenience method that creates a :mod:`~klibs.KLKeyMap`.\ :class:`~klibs.KLKeyMap.KeyMap` instance from
		supplied information.
		Equivalent to::
			P.key_maps['name'] = KLKeyMap.KeyMap(name, ui_labels, data_labels, sdl_keysyms)
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
			P.key_maps[name] = KeyMap(name, ui_labels, data_labels, sdl_keysyms)

		#retrieve registered keymap(s) by name
		if name in P.key_maps:
			return P.key_maps[name]
		else:
			return False

	def config(self):
		"""
		``not_implemented``
		Global configuration of project settings. Slated for future release.
		"""

		#todo: will be a screen that's shown before anything happens in the program to quickly tweak debug settings
		pass

	def quit(self):
		"""
		Safely exits the program, ensuring data has been saved and that any connected EyeLink unit's recording is
		stopped. This, not Python's exit()
		should be used to exit an experiment.
		"""
		if P.verbose_mode:
			full_trace()

		try:
			if not self.evm.events_dumped:
				self.evm.dump_events()
		except:
			pass

		try:
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
			except Exception as e:  # TODO: Determine exception tpye
				print "Database.close() unsuccessful."
				raise e
		except Exception:
			print full_trace()
		try:
			self.el.shut_down()
		except:
			if P.eye_tracking and P.eye_tracker_available:
				print "EyeLink.stopRecording() unsuccessful.\n \033[91m****** MANUALLY STOP RECORDING PLEASE & " \
					  "THANKS!! *******\033[0m"

		try:
			lj.shut_down()
		except:
			if P.labjacking and P.labjack_available:
				print "LabJack.shutdown() unsuccessful. \n\033[91m****** DISCONNECT & RECONNECT LABJACK PLEASE & " \
					  "THANKS! *******\033[0m"

		SDL_Quit()

		# temporary lines added for certain experiments using a log file
		try:
			self.log_f.close()
		except AttributeError:
			pass

		try:
			self.evm.terminate()
		except RuntimeError:
			force_quit()

		print "\n\n\033[92m*** '{0}' successfully shutdown. ***\033[0m\n\n".format(P.project_name)
		exit()

	def run(self, *args, **kwargs):
		"""
		Executes the experiment. Experimenters should use this method to launch their program.
		:param args:
		:param kwargs:
		"""
		if not self.initialized:
			self.quit()

		# if P.collect_demographics:
		# 	if not P.demographics_collected:
		# 		collect_demographics()
		# elif not P.demographics_collected:  # ie. anonymously, for dev. mode or when P.collect_demographics = False
		# 	collect_demographics(True)

		if not P.development_mode:
			version_dir = join(P.versions_dir, "p{0}_{1}".format(P.participant_id, now(True)))
			mkdir(version_dir)
			copyfile("experiment.py", join(version_dir, "experiment.py"))
			copytree(P.config_dir, join(version_dir, "Config"))

		if P.eye_tracking:
			try:
				if not P.manual_eyelink_setup:
					self.el.setup()
			except AttributeError:
				self.el.setup()

		# self.blocks = self.trial_factory.export_trials()
		self.setup()
		try:
			self.__execute_experiment__(*args, **kwargs)
		except RuntimeError:
			force_quit()

		self.quit()

	@abstractmethod
	def clean_up(self):
		return

	def show_logo(self):
		fill()
		blit(P.logo_file_path, 5, P.screen_c)
		flip()
		any_key()

	@abstractmethod
	def display_refresh(self):
		pass

	@abstractmethod
	def setup(self):
		pass

	@abstractmethod
	def block(self):
		pass

	@abstractmethod
	def trial(self):
		pass

	@abstractmethod
	def trial_prep(self):
		pass

	@abstractmethod
	def trial_clean_up(self):
		pass

	@abstractmethod
	def setup_response_collector(self):
		pass

	if P.multi_session_project:
		@abstractmethod
		def init_session(self, id_str):
			pass