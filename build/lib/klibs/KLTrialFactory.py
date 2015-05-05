__author__ = 'jono'

import random
import re
import os
import csv
import KLParams as Params
import re
from collections import OrderedDict
from KLUtilities import *


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


class KLTrialFactory(object):
	trials = None
	executed_trials = None
	meta_factors = None
	exp_parameters = []
	max_trials = None
	trials_per_block = None
	practice_trials = None
	excluded_practice_factors = None
	config_file_rows = []

	# Behaviors
	trial_generation = None
	event_code_generator = None

	def __init__(self):
		self.param_weight_search = re.compile("^.*[ ]{0,}\[([0-9]{1,3})\]$")
		self.param_label_search = re.compile("^(.*)([ ]{0,}\[[0-9]{1,3}\])$")
		self.import_stim_file(Params.config_file_path)

	def define_trial(self, rule, quantity):
		pass

	def import_stim_file(self, path):
		pr("KLTrialFactory.import_stim_file(self, path)", 3, ENTERING)
		data_columns = []
		parameters = []
		if os.path.exists(path):
			config_file = csv.reader(open(path, 'rb'))
			row_count = 0
			for row in config_file:
				self.config_file_rows.append(row)
				self.__parse_parameters_row(row, header=row_count == 0)
				row_count += 1
		self.__generate_trials()
		pr("@T\tself.parameters: {0}".format(self.exp_parameters), 1)
		pr("KLTrialFactory.import_stim_file(self, path)\n", 3, EXITING)
		return True

	def __parse_parameters_row(self, row, header=False):
		pr("KLTrialFactory.__parse_parameters_row(self, row, header)", 1, ENTERING)
		pr("\t@Theader: {0}".format(header))
		col = 0
		for el in row:
			if header:
				column_name = el.split(".")
				try:
					if column_name[1] == TF_PARAM: self.exp_parameters.append([column_name[0], []])
				except:
					continue
			else:
				if len(el) > 0:
					weight = self.param_weight_search.match(el)
					param_label = self.param_label_search.match(el).group(1) if weight is not None else el
					pr("\t@Tweight:{0}, param_label: {1}".format(weight, param_label), 1)
					self.exp_parameters[col][1].append((param_label, 1 if weight is None else int(weight.group(1))))
			col += 1
		if self.exp_parameters[-1][0] in [TF_TRIAL_COUNT, TF_TRIAL_COUNT_UC]: self.trial_generation = TF_STIM_FILE
		pr("KLTrialFactory.__parse_parameters_row(self, row)", 1, EXITING)
		return None

	def add_inferred_factor(self, factor_name, generator, argument_list):
		self.exp_parameters[factor_name] = {"f": generator, "arg_list": argument_list}

	def __generate_trials(self):
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
		trials = [[Params.practicing]]
		exp_params = ['practice']
		if self.trial_generation == TF_STIM_FILE:
			for row in self.exp_parameters:
				trial = []
				for el in row:
					if el[0] in [TF_TRIAL_COUNT, TF_TRIAL_COUNT_UC]:
						pass
					else:
						trial.append(el[0])

		eval_queue = list()
		for factor in self.exp_parameters:
			label = factor[0]
			elements = factor[1]
			temp = list()
			if label[-5:] == '_bool':
				eval_queue.append([label, elements])
			else:
				exp_params.append(label)
				for element in trials:
					if element:
						for v in elements:
							te = element[:]
							te.append(v)
							temp.append(te)
				trials = temp[:]
		for element in eval_queue:
			exp_params.append(element[0][:-5])
			# print "element: " + element[1]
			operands = re.split('[=>!<]+', str(element[1]).strip())
			operator = re.search('[=<!>]+', str(element[1])).group()
			for t in trials:
				t.append(
					eval('t[exp_params.index(\'' + operands[0] + '\')]' + operator + 't[exp_params.index(\'' + operands[
						1] + '\')]'))
		try:
			if self.event_code_generator is not None:
				exp_params.append('code')
				for t in trials:
					t.append(self.event_code_generator(t))
		except:
			pass
		Params.trials = trials

	def pop(self):
		trial = self.trials.pop()
		self.executed_trials.append(trial)
		return trial

	def recycle(self, trial_number=None):
		recycled_trial = self.executed_trials.pop() if trial_number is None else self.executed_trials[trial_number]
		if self.recycle_behavior is "shuffle":
			self.trials.append(recycled_trial)
			random.shuffle(self.trials)
		return True