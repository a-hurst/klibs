__author__ = 'jono'

import sys
import random
from collections import OrderedDict
from copy import copy, deepcopy
from itertools import product
from os.path import exists, join
from os import makedirs
from imp import load_source
		
from klibs.KLEnvironment import EnvAgent
from klibs import P
from klibs.KLIndependentVariable import IndependentVariableSet


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
			if practice:
				self.practice_blocks.append(index)
			self.blocks.insert(index, block)
			self.length = len(self.blocks)
		else:
			insert_err = "Can't insert block at index {0}; it has already passed."
			raise ValueError(insert_err.format(index))

	def next(self): # alias for python2
		return self.__next__()

	def __next__(self):
		if self.i >= self.length:
			self.i = 0 # reset index so we can iterate over it again
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

	def __next__(self):
		if self.i >= self.length:
			self.i = 0
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

	exp_factors = None
	excluded_practice_factors = None
	trial_generator = None
	event_code_generator = None

	def __init__(self, trial_generator=None):
		self.trial_generator = trial_generator

	def __generate_trials__(self, factors=None, block_count=None, trial_count=None):
		# if a well-formatted factor list is passed, use that instead of self.exp_factors
		if factors is None:
			factors = self.exp_factors

		factor_list = []
		for name, values in factors.items(): # convert dict to list
			factor_list.append([name, values])

		trial_tuples = list(product(*[factor[1][:] for factor in factor_list]))
		if len(trial_tuples) == 0: trial_tuples = [ [] ]
		# convert each trial tuple to a list
		trial_set = []
		for t in trial_tuples:
			trial_set.append( list(t) )

		trial_set_count = len(trial_set)
		trials = copy(trial_set)
		random.shuffle(trials)

		# Generate one complete set of trials based on given factors
		if block_count is None:
			block_count = 1 if not P.blocks_per_experiment > 0 else P.blocks_per_experiment
		if trial_count is None:
			if P.trials_per_block <= 0:
				P.trials_per_block = trial_set_count
			trial_count = P.trials_per_block

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
		
		# Divide full list of trials into blocks of equal size (block size = trial_count)
		blocks = []
		for i in range(0, len(trials), trial_count):
			blocks.append(trials[i:i + trial_count])
		return blocks

	def generate(self, exp_factors=None):
		if not exp_factors:
			set_name = "{0}_ind_vars".format(P.project_name)
			try:
				if P.dm_ignore_local_overrides:
					raise RuntimeError("Ignoring local overrides")
				sys.path.append(P.ind_vars_file_local_path)
				var_set = load_source("*", P.ind_vars_file_local_path).__dict__[set_name]
				factors = var_set.to_dict()
			except (IOError, RuntimeError):
				var_set = load_source("*", P.ind_vars_file_path).__dict__[set_name]
				factors = var_set.to_dict()
		else:
			factors = exp_factors.to_dict()

		# Create alphabetically-sorted ordered dict from factors
		self.exp_factors = OrderedDict(sorted(factors.items(), key=lambda t: t[0]))

		try:
			self.blocks = BlockIterator(self.trial_generator(self.exp_factors))
		except TypeError:
			self.blocks = BlockIterator(self.__generate_trials__())

	def export_trials(self):
		return self.blocks

	def add_factor_by_inference(self, factor_name, generator, argument_list):
		"""

		:param factor_name:
		:param generator:
		:param argument_list:
		"""
		self.exp_factors[factor_name] = {"f": generator, "arg_list": argument_list}

	def insert_block(self, block_num, practice=False, trial_count=None, factor_mask=None):
		"""

		:param block_num:
		:param practice:
		:param trial_count:
		:param factor_mask:
		"""
		if factor_mask:
			if not isinstance(factor_mask, dict):
				raise TypeError("Factor overrides must be in the form of a dictionary.")
			
			factors = deepcopy(self.exp_factors) # copy factors to new list
			for name in factor_mask.keys():
				if name in factors.keys():
					new_values = factor_mask[name]
					if hasattr(new_values, '__iter__') == False:
						new_values = [new_values] # if not iterable, put in list
					factors[name] = new_values
				else:
					e = "'{0}' is not the name of an active independent variable".format(name)
					raise ValueError(e)
		else:
			# If no factor mask, generate trials randomly based on self.exp_factors
			factors = None

		block = self.__generate_trials__(factors, 1, trial_count)
		# there is no "zero" block from the UI/UX perspective, so adjust insertion accordingly
		self.blocks.insert(block_num - 1, block[0], practice)

	def define_trial(self, rule, quantity):
		pass

	def num_values(self, factor):
		"""

		:param factor:
		:return: :raise ValueError:
		"""
		try:
			n = len(self.exp_factors[factor])
			return n
		except KeyError:
			e_msg = "Factor '{0}' not found.".format(factor)
			raise ValueError(e_msg)

	def dump(self):
		if not exists(P.local_dir):
			makedirs(P.local_dir)
		with open(join(P.local_dir, "TrialFactory_dump.txt"), "w") as log_f:
			log_f.write("Blocks: {0}, ".format(P.blocks_per_experiment))
			log_f.write("Trials: {0}\n\n".format(P.trials_per_block))
			log_f.write("*****************************************\n")
			log_f.write("*                Factors                *\n")
			log_f.write("*****************************************\n\n")
			for name, values in self.exp_factors.items():
				log_f.write("{0}: {1}\n".format(name, values))
			log_f.write("\n\n\n")
			log_f.write("*****************************************\n")
			log_f.write("*                Trials                 *\n")
			log_f.write("*****************************************\n\n")
			block_num = 1
			for b in self.blocks:
				log_f.write("Block {0}\n".format(block_num))
				trial_num = 1
				for t in b:
					log_f.write("\tTrial {0}: {1} \n".format(trial_num, t))
					trial_num += 1
				block_num += 1
				log_f.write("\n")

	@property
	def trial_generation_function(self, trial_generator):
		"""

		:param trial_generator:
		:return:
		"""
		return self.trial_generator

	@trial_generation_function.setter
	def trial_generation_function(self, trial_generator):
		"""

		:param trial_generator:
		:raise ValueError:
		"""
		if not hasattr(trial_generator, '__call__'):
			raise ValueError("trial_generator must be a function definition.")
		else:
			self.trial_generator = trial_generator
