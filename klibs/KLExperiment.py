# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import sys
from abc import abstractmethod
from os.path import join
from shutil import copyfile, copytree

import sdl2

from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import TrialException
from klibs import P
from klibs.KLKeyMap import KeyMap
from klibs.KLUtilities import full_trace, pump, flush, now, show_mouse_cursor, hide_mouse_cursor
from klibs.KLUtilities import colored_stdout as cso
from klibs.KLTrialFactory import TrialFactory
from klibs.KLGraphics import flip, blit, fill, clear
from klibs.KLGraphics.KLNumpySurface import NumpySurface as NpS
from klibs.KLGraphics import KLDraw as kld
from klibs.KLDatabase import EntryTemplate
from klibs.KLUserInterface import any_key
from klibs.KLAudio import AudioManager
from klibs.KLResponseCollectors import ResponseCollector
from klibs.KLCommunication import message, query, collect_demographics


class Experiment(EnvAgent):
	
	window = None
	paused = False
	
	blocks = None

	def __init__(self):
		super(Experiment, self).__init__()

		self.audio = AudioManager() # initialize audio management for the experiment
		self.rc = ResponseCollector() # add default response collector
		self.database = self.db # use database from evm

		self.trial_factory = TrialFactory(self)
		if P.manual_trial_generation is False:
			self.trial_factory.generate()
		self.event_code_generator = None


	def __execute_experiment__(self, *args, **kwargs):
		"""For internal use, actually runs the blocks/trials of the experiment in sequence.

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
					self.database.current(False)
					clear()
				self.rc.reset()
		self.clean_up()

	def __trial__(self, trial, practice):
		"""
		Private method; manages a trial.
		"""
		pump()

		# At start of every trial, before setup_response_collector or trial_prep are run, retrieve
		# the values of the independent variables (factors) for that trial (as generated earlier by
		# TrialFactory) and set them as attributes of the experiment object.
		factors = list(self.trial_factory.exp_factors.keys())
		for iv in factors:
			iv_value = trial[factors.index(iv)]
			setattr(self, iv, iv_value)

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

	def __log_trial__(self, trial_data):
		"""Internal method, logs trial data to database.

		"""
		trial_template = EntryTemplate('trials')
		trial_template.log(P.id_field_name, P.participant_id)
		for attr in trial_data:
			trial_template.log(attr, trial_data[attr])
		return self.database.insert(trial_template)

	def before_flip(self):
		if P.show_gaze_dot and P.eye_tracking and P.in_trial:
			try:
				self.tracker_dot
			except AttributeError:
				self.tracker_dot = kld.Ellipse(8, stroke=[2, (255,255,255)], fill=(255,0,0)).render()
			try:
				blit(self.tracker_dot, 5, self.el.gaze())
			except RuntimeError:
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

	def quit(self):
		"""Safely exits the program, ensuring data has been saved and any connected EyeLink unit's
		recording is stopped. This, not Python's sys.exit(), should be used to exit an experiment.

		"""
		#TODO: this needs hella cleanup, so much commented-out and messy code
		if P.verbose_mode:
			print(full_trace())

		try:
			try:
				self.database.commit()
			except Exception as e:
				if str(e) == "Cannot operate on a closed database.":
					pass
				else:
					print("Commit() to self.database failed.")
					raise e
			self.database.close()
		except Exception:
			print(full_trace())

		if P.eye_tracking and P.eye_tracker_available:	
			try:
				self.el.shut_down()
			except:
				print("EyeLink.stopRecording() unsuccessful.")
				cso("<red>****** MANUALLY STOP RECORDING PLEASE & THANKS!! *******</red>")
				
		#Commented out until LabJack integration is reimplemented/reconsidered
		#if P.labjacking and P.labjack_available:
		#	try:
		#		lj.shut_down()
		#	except:
		#		print("LabJack.shutdown() unsuccessful.")
		#		cso("<red>****** DISCONNECT & RECONNECT LABJACK PLEASE & THANKS! *******</red>")

		self.audio.shut_down()
		sdl2.ext.quit()

		cso("\n\n<green>*** '{0}' successfully shutdown. ***</green>\n\n".format(P.project_name))
		os._exit(1)


	def run(self, *args, **kwargs):
		"""The method that gets run by 'klibs run' after the runtime environment is created. Runs
		the actual experiment.

		"""

		if not P.development_mode:
			version_dir = join(P.versions_dir, "p{0}_{1}".format(P.participant_id, now(True)))
			os.mkdir(version_dir)
			copyfile("experiment.py", join(version_dir, "experiment.py"))
			copytree(P.config_dir, join(version_dir, "Config"))

		if P.eye_tracking and not P.manual_eyelink_setup:
			self.el.setup()

		self.setup()
		try:
			self.__execute_experiment__(*args, **kwargs)
		except RuntimeError:
			print(full_trace())

		self.quit()

	def show_logo(self):
		logo = NpS(P.logo_file_path)
		flush()
		for i in (1, 2):
			fill()
			blit(logo, 5, P.screen_c)
			flip()
		any_key()


	## Define abstract methods to be overridden in experiment.py ##
	#TODO: Add in-line documentation for most of these

	if P.multi_session_project:
		@abstractmethod
		def init_session(self, id_str):
			pass

	@abstractmethod
	def setup(self):
		pass

	@abstractmethod
	def block(self):
		pass

	@abstractmethod
	def setup_response_collector(self):
		pass
	
	@abstractmethod
	def trial_prep(self):
		pass

	@abstractmethod
	def trial(self):
		pass

	@abstractmethod
	def trial_clean_up(self):
		pass
	
	@abstractmethod
	def clean_up(self):
		pass
