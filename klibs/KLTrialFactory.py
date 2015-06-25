__author__ = 'jono'

import random
from re import compile
import os
import csv
import KLParams as Params
import re
from KLUtilities import *
from itertools import product
from copy import copy
import numpy as np
from math import ceil


class BlockIterator(object):
	def __init__(self, blocks):
		self.blocks = blocks
		self.length = len(blocks)
		self.i = 0

	def __iter__(self):
		return self

	def __len__(self):
		return self.length

	def __getitem__(self, i):
		return self.blocks[i]

	def __setitem__(self, i, x):
		self.blocks[i] = x

	def next(self):
		if self.i >= self.length:
			raise StopIteration
		else:
			self.i += 1
			trials = TrialIterator(self.blocks[self.i - 1])
			return [self.i, trials]


class TrialIterator(BlockIterator):

	def __init__(self, block_of_trials):
		self.trials = block_of_trials
		self.length = len(block_of_trials)
		self.i = 0

	def next(self):
		if self.i >= self.length:
			raise StopIteration
		else:
			self.i += 1
			return [self.i, self.trials[self.i - 1]]

	def recycle(self):
		self.trials.append(self.trials[self.i - 1])
		temp = self.l[self.i:]
		random.shuffle(temp)
		self.trials[self.i:] = temp
		self.length += 1


class TrialFactory(object):
	experiment = None  # parent KLExperiment object
	blocks = None
	practice_blocks = None
	executed_trials = None
	meta_factors = None
	exp_parameters = []
	max_trials = None
	excluded_practice_factors = None
	config_file_rows = []

	# Behaviors
	trial_generation_scheme = None
	trial_generation_function = None
	event_code_generator = None

	def __init__(self, experiment):
		self.experiment = experiment
		self.param_weight_search = compile("^.*[ ]*\[([0-9]{1,3})\]$")
		self.param_label_search = compile("^(.*)([ ]*\[[0-9]{1,3}\])$")
		self.__import_stim_file(Params.config_file_path)

	def __generate_trials(self, practice_trials=False ):
		pr("KLTrialFactory.__generate_trials(self)", 2, ENTERING)
		trial_set = list(product(*[factor[1][:] for factor in self.exp_parameters]))

		# convert each trial tuple to list and insert at the front of it a boolean indicating if it is a practice trial
		for i in range( len(trial_set) ):
			trial_set[i] = list(trial_set[i])
			trial_set[i].insert(0, practice_trials)

		trial_set_count = len(trial_set)
		trials = copy(trial_set)
		random.shuffle(trial_set)

		block_count = None
		trial_count = None

		# Run one complete set of trials in no values are supplied for trial & block length
		if practice_trials:
			block_count = 1 if not Params.practice_blocks_per_experiment > 0 else Params.practice_blocks_per_experiment
			trial_count = trial_set_count if not Params.trials_per_practice_block > 0 else Params.trials_per_practice_block
		else:
			block_count = 1 if not Params.blocks_per_experiment > 0 else Params.blocks_per_experiment
			trial_count = trial_set_count if not Params.trials_per_block > 0 else Params.trials_per_block

		total_trials = block_count * trial_count

		if total_trials > trial_set_count:
			trial_shortage = total_trials - trial_set_count
			while len(trials) < total_trials:
				more_trials = copy(trial_set)
				random.shuffle(more_trials)
				if trial_shortage >= trial_set_count:
					trials.extend(more_trials)
					trial_shortage -= trial_set_count
				else:
					trials.extend(more_trials[0:trial_shortage])
		if total_trials < trial_set_count:
			while len(trials) > total_trials:
				trials.pop()
		blocks = []
		np_blocks = np.array_split(trials, block_count)
		for block in np_blocks:
			blocks.append(block.tolist())
		return blocks

	def __generate_trials_from_stimfile(self):
		pr("KLTrialFactory.__generate_trials_from_stimfile(self)", 2, ENTERING)
		for row in self.exp_parameters:
			trial = []
			for el in row:
				if el[0] in [TF_TRIAL_COUNT, TF_TRIAL_COUNT_UC]:
					pass
				else:
					trial.append(el[0])
		#  not finished, just cramemd it here when talking with ross

	def __import_stim_file(self, path, trial_generator=None):
		pr("KLTrialFactory.import_stim_file(self, path)", 2, ENTERING)
		if os.path.exists(path):
			config_file = csv.reader(open(path, 'rb'))
			row_count = 0
			for row in config_file:
				self.config_file_rows.append(row)
				self.__parse_parameters_row(row, header=row_count == 0)
				row_count += 1

		# Strip out trial_count column if it exists but doesn't contain integers
		if self.exp_parameters[-1][0] in [TF_TRIAL_COUNT, TF_TRIAL_COUNT_UC]:
			if not all(type(val) is int for val in zip(*self.exp_parameters)[-1]):
				self.exp_parameters = self.exp_parameters[:-1]
			else:
				self.trial_generation_scheme = TF_STIM_FILE

		if trial_generator is not None:
			self.blocks = trial_generator(Params.blocks_per_experiment, Params.trials_per_block, self.exp_parameters)
			if Params.practicing:
				self.practice_blocks = trial_generator(Params.practice_blocks_per_experiment,
													   Params.trials_per_practice_block, self.exp_parameters)
		else:
			self.blocks = self.__generate_trials()
			if Params.practicing:
				self.practice_blocks = self.__generate_trials(True)
		pr("KLTrialFactory.import_stim_file(self, path)", 2, EXITING)
		return True

	def __parse_parameters_row(self, row, header=False):
		pr("KLTrialFactory.__parse_parameters_row(self, row, header)", 2, ENTERING)
		col = 0
		for el in row:
			if header:
				column_name = el.split(".")
				try:
					if column_name[1] == TF_PARAM:
						self.exp_parameters.append([column_name[0], []])
				except:
					continue
			else:
				if len(el) > 0:
					weight = self.param_weight_search.match(el)
					param_label = self.param_label_search.match(el).group(1) if weight is not None else el
					try:
						param_label = int(param_label)
					except ValueError:
						try:
							param_label = float(param_label)
						except ValueError:
							pass
					weight_val = 1 if weight is None else int(weight.group(1))
					for i in range(weight_val):
						self.exp_parameters[col][1].append(param_label)
			col += 1
		pr("KLTrialFactory.__parse_parameters_row(self, row)", 2, EXITING)

	def export_trials(self, practicing=False):
		return BlockIterator(self.practice_blocks) if practicing else BlockIterator(self.blocks)

	def add_inferred_factor(self, factor_name, generator, argument_list):
		self.exp_parameters[factor_name] = {"f": generator, "arg_list": argument_list}

 	def define_trial(self, rule, quantity):
		pass

	@property
	def trial_generation_function(self, trial_generator):
		if not hasattr(trial_generator, '__call__'):
			raise ValueError("trial_generator must be a function definition.")
		else:
			self.trial_generation_function = trial_generator
