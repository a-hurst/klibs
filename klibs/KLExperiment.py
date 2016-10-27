# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

from hashlib import sha1
from sdl2 import SDL_Quit
from abc import abstractmethod
from os import mkdir
from os.path import join
from shutil import copyfile, copytree
# from time import time

from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import TrialException
from klibs import P
from klibs.KLKeyMap import KeyMap
from klibs.KLConstants import ALL
from klibs.KLUtilities import full_trace, pump, now, list_dimensions, force_quit, show_mouse_cursor, hide_mouse_cursor
from klibs.KLTrialFactory import TrialFactory
from klibs.KLGraphics import flip, blit, fill, clear #, display_init
from klibs.KLDatabase import Database
from klibs.KLUserInterface import any_key
from klibs.KLAudio import AudioManager
# from klibs.KLResponseCollectors import ResponseCollector
from klibs.KLCommunication import message, query

# from klibs.KLCommunication import  message
# import klibs.eyelink as el
# import klibs.database  as db

# todo: a) make display_refresh a standard method of an experiment object, and then b) add a default line that times it
# and warns the experimenter if more than 16.666ms are elapsing between calls



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

		if P.pre_render_block_messages:
			for i in range(1, P.blocks_per_experiment, 1):
				msg = self.block_break_message.format(i, P.blocks_per_experiment)
				r_msg = self.message(msg, blit=False)
				self.block_break_messages.append(r_msg)

		self.trial_factory = TrialFactory(self)
		if P.manual_trial_generation is False:
			try:
				self.trial_factory.import_stim_file(P.factors_file_path)
			except ValueError:
				self.trial_factory.import_stim_file(P.config_file_path_legacy)
			self.trial_factory.generate()

		self.event_code_generator = None

		# create an anonymous user if not collecting demographic information
		if not P.collect_demographics or P.development_mode:
			self.collect_demographics(True)
		self.initialized = True

	def show_logo(self):
		fill()
		blit(P.logo_file_path, 5, P.screen_c)
		flip()
		any_key()


	def __execute_experiment__(self, *args, **kwargs):
		"""
		Private method, launches and manages the experiment after KLExperiment object's run() method is called.

		:param args:
		:param kwargs:
		"""


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
					print "Ending trial {0}".format(self.database.last_id_from('trials') + 1)
				except TrialException:
					block.recycle()
					P.recycle_count += 1
					# self.evm.send('trial_recycled')
					self.database.current(False)
					clear()
					print "Ending trial {0} due to TrialException".format(self.database.last_id_from('trials') + 1)
				self.evm.clear()
				self.rc.reset()
		self.clean_up()
		self.evm.dump_events()
		self.database.db.commit()
		self.database.db.close()

	def __trial__(self, trial, practice):
		"""
		Private method; manages a trial. Expected \*args = [trial_number, [practicing, param_1,...param_n]]

		"""
		pump()
		for p in self.trial_factory.exp_parameters:
			attr_name = p[0]
			attr_val = trial[self.trial_factory.exp_parameters.index(p)]
			setattr(self, attr_name, attr_val)
		self.setup_response_collector()

		self.trial_prep()
		tx = None
		try:
			if P.development_mode and (P.dm_trial_show_mouse or (P.eye_tracking and not P.eye_tracker_available)):
				show_mouse_cursor()
			self.evm.start_clock()
			if P.eye_tracking:
				self.el.start(P.trial_number)
			self.__log_trial__(self.trial())
			if P.eye_tracking:
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
		if P.eye_tracking:
			self.el.stop()
		self.evm.clear()
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

	def collect_demographics(self, anonymous_user=False):
		"""
		Gathers participant demographic information and enter it into the project database.
		Should not be explicitly called; see ``P.collect_demographics``.

		:param anonymous_user: Toggles generation of arbitrary participant info in lieu of participant-supplied info.
		:type anonymous_user: Boolean
		"""

		# TODO: this function should have default questions/answers but should also be able to read from a CSV or dict
		if not P.collect_demographics and not anonymous_user: return
		if P.collect_demographics:
			if P.multi_session_project:
				id_str = query(
					"If you have already created an id for this experiment, please enter it now. Otherwise press 'return'.",
					password=True, accepted=ALL)
				if id_str:
					return self.init_session(id_str)

		self.db.init_entry('participants', instance_name='ptcp', set_current=True)
		self.db.log("random_seed", P.random_seed)
		try:
			self.db.log("klibs_commit", P.klibs_commit)
		except:
			pass  # older .versions of klibs did not include this param/db entry
		if anonymous_user:
			name = P.anonymous_username
		else:
			name_query_string = query(
				'What is your full name, banner number or e-mail address? \nYour answer will be encrypted and cannot be read later.',
				password=True)
			name_hash = sha1(name_query_string)
			name = name_hash.hexdigest()
		self.db.log('userhash', name)

		# names must be unique; returns True if unique, False otherwise
		if self.db.is_unique('participants', 'userhash', name):
			try:
				for q in P.demographic_questions:
					if anonymous_user:
						self.db.log(q[0], q[4])
					else:
						self.db.log(q[0], query(q[1], accepted=q[2], return_type=q[3]))
			except AttributeError:
				if anonymous_user:
					sex = "m" if now() % 2 > 0  else "f"
					handedness = "a"
					age = 0
				else:
					sex_str = "What is your sex? \nAnswer with:  (m)ale,(f)emale"
					sex = query(sex_str, accepted=('m', 'M', 'f', 'F'))
					handedness_str = "Are right-handed, left-handed or ambidextrous? \nAnswer with (r)ight, (l)eft or (a)mbidextrous."
					handedness = query(handedness_str, accepted=('r', 'R', 'l', 'L', 'a', 'A'))
					age = query('What is  your age?', return_type='int')
					self.db.log('sex', sex)
					self.db.log('handedness', handedness)
					self.db.log('age', age)
			self.db.log('created', now(True))
			if not P.demographics_collected:
				P.participant_id = self.db.insert()
				P.demographics_collected = True
			else:
				#  The context for this is: collect_demographics is set to false but then explicitly called later
				self.db.update(P.participant_id)
		else:
			retry = query('That participant identifier has already been used. Do you wish to try another? (y/n) ')
			if retry == 'y':
				self.collect_demographics()
			else:
				self.fill()
				message("Thanks for participating!", location=P.screen_c)
				any_key()
				self.quit()
		self.db.current(False)
		if P.collect_demographics and P.multi_session_project:
			self.init_session()

	def insert_practice_block(self, block_nums, trial_counts=None, factor_masks=None):
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
		if list_dimensions(factor_masks) == 2:
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
		if P.collect_demographics:
			if not P.demographics_collected:
				self.collect_demographics(self.database)
		elif not P.demographics_collected:
			self.collect_demographics(self.database, True)

		if not P.development_mode:
			version_dir = join(P.versions_dir, "p{0}_{1}".format(P.participant_id, now(True)))
			mkdir(version_dir)
			copyfile("experiment.py", join(version_dir, "experiment.py"))
			copytree(P.config_dir, join(version_dir, "Config"))

		if P.eye_tracking and P.eye_tracker_available:
			self.el.setup()
		self.blocks = self.trial_factory.export_trials()
		self.setup()
		try:
			self.__execute_experiment__(*args, **kwargs)
		except RuntimeError:
			force_quit()

		self.quit()


	# @property
	# def db_name(self):
	# 	return self.__db_name
	#
	# @db_name.setter
	# def db_name(self, db_name):
	# 	self.__db_name = db_name
	#
	# @property
	# def event_code_generator(self):
	# 	return self.__event_code_function
	#
	# @event_code_generator.setter
	# def event_code_generator(self, event_code_function):
	# 	if type(event_code_function).__name__ == 'function':
	# 		self.__event_code_function = event_code_function
	# 	elif event_code_function is None:
	# 		self.__event_code_function = None
	# 	else:
	# 		raise ValueError('App.codeFunc must be set to a function.')
	#
	# @property
	# def no_tracker(self):
	# 	return self.__no_tracker
	#
	# @no_tracker.setter
	# def no_tracker(self, no_tracker):
	# 	if type(no_tracker) is bool:
	# 		self.__no_tracker = no_tracker
	# 	else:
	# 		raise ValueError('App.noTracker must be a boolean value.')
	#
	# @property
	# def participant_instructions(self):
	# 	pass
	#
	# @participant_instructions.getter
	# def participant_instructions(self):
	# 	return self.participant_instructions
	#
	# @participant_instructions.setter
	# def participant_instructions(self, instructions_file):
	# 	with open("ExpAssets/participant_instructions.txt", "r") as ins_file:
	# 		self.participant_instructions = ins_file.read()

	@abstractmethod
	def clean_up(self):
		return

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
