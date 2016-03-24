# -*- coding: utf-8 -*-
__author__ = 'jono'
import time
from klibs.KLConstants import *
from klibs import KLParams as Params


class CountDown(object):
	duration = 0
	started = 0
	paused = False

	def __init__(self, duration, start=True):
		super(CountDown, self).__init__()
		if type(duration) not in [int, float]:
			raise ValueError("Duration must be a positive number.")
		elif duration <= 0:
			raise ValueError("Authorization Denied: negative and null duration privileges restricted to user dr_who.")
		self.duration = float(duration)
		if start: self.start()

	def start(self):
		self.started = time.time()

	def counting(self):
		if self.paused is not False:
			return False
		else:
			return time.time() - self.started < self.duration

	def reset(self):
		self.start()
		self.paused = False

	def finish(self):
		self.started = time.time() - self.duration

	def add(self, time):
		self.started += time

	def pause(self):
		self.paused = time.time()

	def unpause(self):
		self.started += time.time() - self.paused
		self.paused = False

	def remaining(self):
		return self.duration - (time.time() - self.started)

	def elapsed(self):
		return time.time() - self.started


class TimeKeeper(object):
	moments = {}
	periods = {}
	mean_moments = {}
	mean_periods = {}
	countdowns = {}

	# todo: add units argument as between secondds/ ms

	def __init__(self, *args, **kwargs):
		super(TimeKeeper, self).__init__(*args, **kwargs)
		self.log("Instantiated")

	def log(self, label, time_value=None):
		self.moments[label] = time_value if time_value else time.time()

	def sample(self, label, time_value=None):
		if label in self.mean_moments:
			self.mean_moments[label].append(time_value if time_value else time.time())
		else:
			self.mean_moments[label] = [time_value if time_value else time.time()]

	def sample_start(self, label, time_value=None):
		sample_index = len(self.mean_periods[label]) - 1 if label in self.mean_periods else 0
		sample_key = "{0}.{1}".format(label, sample_index )
		if label in self.mean_periods:
			self.mean_periods[label].append([time_value if time_value else time.time(), None])
		else:
			self.mean_periods[label] = [[time_value if time_value else time.time(), None]]
		return sample_key

	def sample_stop(self, label, sample_key=None, time_value=None):
		sample_index = int(sample_key.split(".")[1]) if sample_key is not None else len(self.mean_periods[label]) - 1
		if self.mean_periods[label][sample_index][1] is not None:
			raise RuntimeError("Trying to stop a sample that has already finished.")
		self.mean_periods[label][sample_index][1] = time_value if time_value else time.time()

	def mean(self, label):
		try:
			values = self.mean_periods[label]
			periods = [key[1] - key[0] for key in self.mean_periods[label]]
		except KeyError:
			values = self.mean_moments[label]
		mean = sum(periods) / len(values)

		try:
			return [mean, values, periods ]
		except NameError:
			return [values, mean]

	def start(self, label, time_value=None):
		self.periods[label] = [time_value if time_value else time.time(), None]
		return self

	def stop(self, label, time_value=None):
		self.periods[label][1] = time_value if time_value else time.time()
		return self

	def period(self, label):
		try:
			return self.periods[label][1] - self.periods[label][0]
		except (KeyError, TypeError):
			self.stop(label)
			return self.period(label)

	def read(self, label):
		label_from_key = label.split(".")
		try:
			return self.mean_periods[label_from_key[0]][label_from_key[1]][1]
		except KeyError:
			try:
				return self.moments[label]
			except KeyError:
				try:
					return self.periods[label]
				except KeyError:
					raise KeyError("{0} not found in either of TimeKeeper.moments or TimeKeeper.periods".format(label))

	def export(self):
		output = ["Moments"]
		for m in self.moments:
			output.append( "{0}: {1}".format(m, self.moments[m]) )
		for p in self.periods:
			times = [self.periods[p][0], self.periods[p][1]]
			try:
				times.append(times[1] - times[0])
			except TypeError:
				times.append(None)
			output.append( "{0}: Start = {1}, End = {2}, Duration = {3}".format(p, *times))
		return "\n".join(output)

	def elapsed(self, label):
		return time.time() - self.periods[label][0]

	def countdown(self, duration=None, unit=TK_S, label=None, start=True):
		if unit == TK_MS:
			duration *= 0.001
		if duration is False:
			try:
				return self.countdowns[label]
			except KeyError:
				raise KeyError("No countdown started by that name. To start a countdown include a duration argument.")
		countdown = CountDown(duration, start)
		if label is not None:
			self.countdowns[label] = countdown
		return countdown


class TrialClock(object):

	def __init__(self, experiment):
		self.stages = []
		self.tasks = []
		self.events = []
		self.stages_index = {}
		self.start_time = None
		self.started = False
		self.experiment = experiment

	def register_stage(self, stage, start_time, duration):
		self.stages.append = [stage, start_time, duration]
		self.stages_index[stage] = len(self.stages) - 1

	def report_sequence(self):
		return sorted(self.stages, key=lambda start_time: start_time[1]).reverse()

	def started(self, stage):
		if not self.started:
			raise RuntimeError('TrialClock has not been started.')
		if not stage in self.start_index:
			raise ValueError('No stage named {0} defined.'.format(stage))

		return self.stages[self.stage_index[stage]][1] > time.time() - self.start_time

	def ended(self, stage):
		if not self.started:
			raise RuntimeError('TrialClock has not been started.')
		if not stage in self.start_index:
			raise ValueError('No stage named {0} defined.'.format(stage))
		stage = self.stages[self.stage_index[stage]]
		return stage[1] + stage[2] > time.time() - self.start_time

	def start(self):
		self.started = True
		self.start_time = time.time()
		data = [Params.participant_id, EVI_CLOCK_START, self.start_time, self.experiment.eyelink.now()]
		self.experiment.database.insert(data, TBL_EVENTS, False)

	def stop(self):
		pass
	# def register_task(self, at, do):








