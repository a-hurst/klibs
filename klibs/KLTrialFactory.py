__author__ = 'jono'

import random
from re import compile
import csv
from copy import copy

import numpy as np

from klibs.KLUtilities import *
from itertools import product
from math import ceil


class BlockIterator(object):
	def __init__(self, blocks):
		self.blocks = blocks
		self.practice_blocks = []
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

	def insert(self, index, block, practice):
		if self.i <= index:
			self.practice_blocks.append(index)
			self.blocks.insert(index, block)
			self.length = len(self.blocks)
		else:
			raise ValueError("Can't insert block at index {0}; it has already passed.".format(index))

	def next(self):
		if self.i >= self.length:
			raise StopIteration
		else:
			self.i += 1
			trials = TrialIterator(self.blocks[self.i - 1])
			trials.practice = self.i - 1 in self.practice_blocks

			return trials




class TrialIterator(BlockIterator):

	def __init__(self, block_of_trials):
		self.trials = block_of_trials
		self.length = len(block_of_trials)
		self.i = 0
		self.__practice = False

	def next(self):
		if self.i >= self.length:
			raise StopIteration
		else:
			self.i += 1
			return self.trials[self.i - 1]

	def recycle(self):
		self.trials.append(self.trials[self.i - 1])
		temp = self.trials[self.i:]
		random.shuffle(temp)
		self.trials[self.i:] = temp
		self.length += 1

	@property
	def practice(self):
		return self.__practice

	@practice.setter
	def practice(self, practicing):
		self.__practice = practicing == True


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
	trial_generator = None
	event_code_generator = None

	def __init__(self, experiment, trial_generator=None):
		self.experiment = experiment
		self.param_weight_search = compile("^.*[ ]*\[([0-9]{1,3})\]$")
		self.param_label_search = compile("^(.*)([ ]*\[[0-9]{1,3}\])$")

	def __generate_trials(self, factors=None, block_count=None, trial_count=None):
		#  by default just process self.exp_parameters, but, if a well-formatted factor list is passed, use that
		if factors is None:
			factors = self.exp_parameters
		trial_tuples = list(product(*[factor[1][:] for factor in factors]))
		if len(trial_tuples) == 0: trial_tuples = [ [] ]

		# convert each trial tuple to list and insert at the front of it a boolean indicating if it is a practice trial
		trial_set = []
		for t in trial_tuples:
			trial_set.append( list(t) )

		trial_set_count = len(trial_set)
		trials = copy(trial_set)
		random.shuffle(trials)

		# Run one complete set of trials in no values are supplied for trial & block length
		if block_count is None:
			block_count = 1 if not Params.blocks_per_experiment > 0 else Params.blocks_per_experiment
		if trial_count is None:
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

	def __generate_trials_from_stim_file(self):
		for row in self.exp_parameters:
			trial = []
			for el in row:
				if el[0] in [TF_TRIAL_COUNT, TF_TRIAL_COUNT_UC]:
					pass
				else:
					trial.append(el[0])
		#  not finished, just cramemd it here when talking with ross

	def import_stim_file(self, path):
		if os.path.exists(path):
			config_file = csv.reader(open(path, 'rb'))
			row_count = 0
			for row in config_file:
				try:
					if row[0][0] == "#":  # ie. skip header line, which wasn't in earlier .versions of the config file
						continue
				except IndexError:
					pass
				for i in range(0, len(row)):
					row[i] = row[i].replace(" ", "")
				self.config_file_rows.append(row)
				self.__parse_parameters_row(row, header= row_count == 0)
				row_count += 1
		else:
			raise ValueError("No config file found at provided path..")
		if len(self.exp_parameters) == 0: return True
		# Strip out trial_count column if it exists but doesn't contain integers
		if self.exp_parameters[-1][0] in [TF_TRIAL_COUNT, TF_TRIAL_COUNT_UC]:
			if not all(type(val) is int for val in zip(*self.exp_parameters)[-1]):
				self.exp_parameters = self.exp_parameters[:-1]
			else:
				self.trial_generation_scheme = TF_STIM_FILE

	def generate(self):
		try:
			self.blocks = self.trial_generator(self.exp_parameters)
		except TypeError:
			self.blocks = self.__generate_trials()

	def __parse_parameters_row(self, row, header=False):
		col = 0
		for el in row:
			if header:
				column_name = el.split(".")
				try:
					if column_name[1] == TF_PARAM:
						self.exp_parameters.append([column_name[0].replace(" ", ""), []])
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

	def export_trials(self):
		return BlockIterator(self.blocks)

	def add_factor_by_inference(self, factor_name, generator, argument_list):
		self.exp_parameters[factor_name] = {"f": generator, "arg_list": argument_list}

	def insert_block(self, block_num, practice, trial_count="*", factor_mask=None):
		factors = []
		col_index = 0
		for col in factor_mask:
			val_index = 0
			col_name = self.exp_parameters[col_index][0]
			vals = []
			for val in col:
				for i in range(0,val):
					try:
						vals.append(self.exp_parameters[col_index][1][val_index])
					except IndexError:
						pass
				val_index += 1
			col_index += 1
			factors.append([col_name, vals if len(vals) else [None]])
		block = self.__generate_trials(factors, 1, trial_count)
		self.experiment.blocks.insert(block_num - 1, block[0], practice)  # there is no "zero" block from the UI/UX perspective

 	def define_trial(self, rule, quantity):
		pass

	@property
	def trial_generation_function(self, trial_generator):
		return self.trial_generator

	@trial_generation_function.setter
	def trial_generation_function(self, trial_generator):
		if not hasattr(trial_generator, '__call__'):
			raise ValueError("trial_generator must be a function definition.")
		else:
			self.trial_generator = trial_generator
