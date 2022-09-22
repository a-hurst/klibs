# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import sys
from abc import abstractmethod
from traceback import print_tb, print_stack

from klibs import P
from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import TrialException
from klibs.KLInternal import full_trace
from klibs.KLInternal import colored_stdout as cso


class Experiment(EnvAgent):
	
	window = None
	paused = False

	def __init__(self):
		from klibs.KLAudio import AudioManager
		from klibs.KLResponseCollectors import ResponseCollector
		from klibs.KLTrialFactory import TrialFactory

		super(Experiment, self).__init__()

		self.incomplete = True # flag for keeping track of session completeness
		self.blocks = None # blocks of trials for the experiment
		self.tracker_dot = None # overlay of eye tracker gaze location in devmode

		self.audio = AudioManager() # initialize audio management for the experiment
		self.rc = ResponseCollector() # add default response collector
		self.database = self.db # use database from evm

		self.trial_factory = TrialFactory()
		if P.manual_trial_generation is False:
			self.trial_factory.generate()
		self.event_code_generator = None


	def __execute_experiment__(self, *args, **kwargs):
		"""For internal use, actually runs the blocks/trials of the experiment in sequence.

		"""
		from klibs.KLGraphics import clear

		if self.blocks == None:
			self.blocks = self.trial_factory.export_trials()

		P.block_number = 0
		for block in self.blocks:
			P.recycle_count = 0
			P.block_number += 1
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
					clear() # NOTE: is this actually wanted?
				self.rc.reset()
		self.clean_up()

		self.incomplete = False
		if 'session_info' in self.database.table_schemas.keys():
			where = {'session_number': P.session_number}
			self.database.update('session_info', {'complete': True}, where)


	def __trial__(self, trial, practice):
		"""
		Private method; manages a trial.
		"""
		from klibs.KLEventQueue import pump
		from klibs.KLUserInterface import show_cursor, hide_cursor

		# At start of every trial, before setup_response_collector or trial_prep are run, retrieve
		# the values of the independent variables (factors) for that trial (as generated earlier by
		# TrialFactory) and set them as attributes of the experiment object.
		factors = list(self.trial_factory.exp_factors.keys())
		for iv in factors:
			iv_value = trial[factors.index(iv)]
			setattr(self, iv, iv_value)

		pump()
		self.setup_response_collector()
		self.trial_prep()
		tx = None
		try:
			if P.development_mode and (P.dm_trial_show_mouse or (P.eye_tracking and not P.eye_tracker_available)):
				show_cursor()
			self.evm.start_clock()
			if P.eye_tracking and not P.manual_eyelink_recording:
				self.el.start(P.trial_number)
			P.in_trial = True
			self.__log_trial__(self.trial())
			P.in_trial = False
			if P.eye_tracking and not P.manual_eyelink_recording:
				self.el.stop()
			if P.development_mode and (P.dm_trial_show_mouse or (P.eye_tracking and not P.eye_tracker_available)):
				hide_cursor()
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


	def __log_trial__(self, trial_data):
		"""Internal method, logs trial data to database.

		"""
		from klibs.KLDatabase import EntryTemplate

		trial_template = EntryTemplate('trials')
		trial_template.log(P.id_field_name, P.participant_id)
		for attr in trial_data:
			trial_template.log(attr, trial_data[attr])

		return self.database.insert(trial_template)


	## Define abstract methods to be overridden in experiment.py ##

	@abstractmethod
	def setup(self):
		"""The first part of the experiment that gets run. Locations, sizes, stimuli, and
		other experiment resources that stay the same throughout the experiment should be
		initialized and defined here.

		"""
		pass

	@abstractmethod
	def block(self):
		"""Run once at the start of every block. Block messages, block-level stimulus generation,
		and similar content should go here.

		"""
		pass

	@abstractmethod
	def setup_response_collector(self):
		"""Run immediately before trial_prep during each iteration of the trial loop. If using a
		:obj:`~klibs.KLResponseCollectors.ResponseCollector` that requires configuration at the
		start of each trial, that code should go here.
		
		"""
		pass
	
	@abstractmethod
	def trial_prep(self):
		"""Run immediately before the start of every trial. All trial preparation unrelated to
		response collection should go here.

		"""
		pass

	@abstractmethod
	def trial(self):
		"""The core of the experiment. All code related to the presentation of stimuli during a
		given trial, the collection and processing of responses, and the writing out of primary
		data should go here.

		The timing of events in the built-in :obj:`~klibs.KLEventManager.EventManager` instance
		(``self.evm``) are all relative to when this method is called.

		"""
		pass

	@abstractmethod
	def trial_clean_up(self):
		"""Run immediately after the end of every trial.

		"""
		pass
	
	@abstractmethod
	def clean_up(self):
		"""Run once at the end of the experiment, after all trials have been completed. Anything
		you want to happen at the very end of the session should go here.

		"""
		pass
	

	def insert_practice_block(self, block_nums, trial_counts=None, factor_mask=None):
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

		Args:
			block_nums (:obj:`list` of int): Index numbers at which to insert the blocks.
			trial_counts (:obj:`list` of int, optional): The numbers of trials to insert for each
				of the inserted blocks.
			factor_mask (:obj:`dict` of :obj:`list`, optional): Override values for the variables
				specified in independent_variables.py.

		Raises:
			TrialException: If called after the experiment's :meth:`setup` method has run.

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
		for i in range(0, len(block_nums)):
			self.trial_factory.insert_block(block_nums[i], True, trial_counts[i], factor_mask)
			P.blocks_per_experiment += 1

	
	def before_flip(self):
		"""A method called immediately before every refresh of the screen (i.e. every time
		:func:`~klibs.KLGraphics.flip` is called).
		
		By default, this is used for drawing the current gaze location to the screen when using an
		eye tracker (and ``P.show_gaze_dot`` is True), but can be overridden with a different
		function if desired.

		"""
		from klibs.KLGraphics import blit

		if P.show_gaze_dot and self.el.recording:
			try:
				blit(self.tracker_dot, 5, self.el.gaze())
			except RuntimeError:
				pass


	def quit(self):
		"""Safely exits the program, ensuring data has been saved and any connected EyeLink unit's
		recording is stopped. This, not Python's sys.exit(), should be used to exit an experiment.

		"""
		import sdl2
		if P.verbose_mode:
			print_tb(print_stack(), 6)

		err = ''
		try:
			self.database.commit()
			self.database.close()
		except Exception:
			err += "<red>Error encountered closing database connection:</red>\n\n"
			err += full_trace()+"\n\n"
			err += "<red>Some data may not have been saved.</red>\n\n\n"

		if P.eye_tracking and P.eye_tracker_available:	
			try:
				self.el.shut_down(incomplete=self.incomplete)
			except Exception:
				err += "<red>Eye tracker encountered error during shutdown:</red>\n\n"
				err += full_trace()+"\n\n"
				err += "<red>You may need to manually stop the tracker from recording.</red>\n\n\n"

		if P.multi_user and P.version_dir:
			newpath = P.version_dir.replace(str(P.random_seed), str(P.participant_id))
			os.rename(P.version_dir, newpath)

		self.audio.shut_down()
		sdl2.ext.quit()

		if err:
			cso("\n\n" + err + "<red>*** Errors encountered during shutdown. ***</red>\n\n")
			os._exit(1)
		cso("\n\n<green>*** '{0}' successfully shut down. ***</green>\n\n".format(P.project_name))
		os._exit(1)


	def run(self, *args, **kwargs):
		"""The method that gets run by 'klibs run' after the runtime environment is created. Runs
		the actual experiment.

		"""
		from klibs.KLGraphics.KLDraw import Ellipse
	
		if P.eye_tracking:
			RED = (255, 0, 0)
			WHITE = (255, 255, 255)
			self.tracker_dot = Ellipse(8, stroke=[2, WHITE], fill=RED).render()
			if not P.manual_eyelink_setup:
				self.el.setup()

		self.setup()
		try:
			self.__execute_experiment__(*args, **kwargs)
		except RuntimeError:
			print(full_trace())

		self.quit()


	def show_logo(self):
		from klibs.KLEventQueue import flush
		from klibs.KLUserInterface import any_key
		from klibs.KLGraphics import fill, blit, flip
		from klibs.KLGraphics import NumpySurface as NpS
		logo = NpS(P.logo_file_path)
		flush()
		for i in (1, 2):
			fill()
			blit(logo, 5, P.screen_c)
			flip()
		any_key()
