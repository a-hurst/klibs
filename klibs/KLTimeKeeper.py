# -*- coding: utf-8 -*-
__author__ = 'jono'
import time
from klibs.KLConstants import *
from klibs.KLUtilities import *
from klibs import KLParams as Params
from multiprocessing import Pipe
from signal import SIGKILL
import inspect

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

	def resume(self):
		self.started += time.time() - self.paused
		self.paused = False

	def remaining(self):
		return self.duration - (time.time() - self.started)

	def elapsed(self):
		return time.time() - self.started

	def unpause(self):
		self.resume()  # deprecated, maintained for backwards compatibility


class TimeKeeper(object):
	moments = {}
	periods = {}
	mean_moments = {}
	mean_periods = {}
	countdowns = {}

	# todo: add units argument as between secondds/ ms

	def __init__(self, experiment):
		super(TimeKeeper, self).__init__()
		self.experiment = experiment
		self.log("Instantiated")
		self.clock = EventClock(experiment)

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
		mean_val = sum(periods) / len(values)

		try:
			return [mean_val, values, periods ]
		except NameError:
			return [values, mean_val]

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

	def countdown(self, duration=None, label=None, start=True, unit=TK_S):
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


class EventClock(object):

	def __init__(self, experiment):
		self.tasks = []
		self.events = []
		self.sent_events = []
		self.stages = []
		self.events_index = {}
		self.start_time = None
		self.experiment = experiment
		self.events = []
		self.pipe = None
		self.p = None
		self.pipe, child = Pipe()
		self.p = __event_clock__(child)

	def register_events(self, events):
		for e in events:
		# 	if e not in
		# EVI_CONSTANTS and type(e) is not EventTicket:
		# 		raise ValueError("register_events() requires an iterable of EventTickets or KLEventInterface constants./"
		# 						 "Please use register_event() to register a single event.")
		# 	else:
		# 		if not iterable(e):
			self.register_event(e)


	def register_event(self, event):
		"""
		Inserts passed event into the Trial Clock's event queue. Event can be a string constant (see Event Interface
		constants) or a list of length 2 or 3. The first element must be the time at which the event should be issued;
		the second must be a string, the event label; the third and optional element may contain arbitrary data to be made
		available when the klibs.KLEventInterface.TrialEvent object is created. The contents will be accessible via the
		data attribute of the event (ie. TrialEvent.data). Additionally, if a dictionary is passed, the TrialEvebt object
		will be instantiated with a new attribute for each key thereof (this is supplemental to TrialEvent.data attribute).

		**Example**

		Example 1: No data attribute

		Params.clock.register_event(300, 'MyEvent', TK_MS)

		At 300ms an event, "MyEVent" will be issued; at the next call to KlUtilities.pump(), a TrialEvent object will be
		generated and made available at Params.process_queue_data['MyEvent'], ie:

		e = Params.process_queue_data['MyEvent']


		Example 2: Non-dictionary Data Supplied

		Params.clock.register_event([300, 'MyEvent', ['a','b', 'c']], TK_MS)

		As Example 1, and additionally:

		print e.data
		>> ["a","b", c"]


		Example 3: Dictionary Data Supplied
		Params.clock.register_event([300, 'MyEvent', {'attr1':'a','attr2:'b', 'attr3': 'c'}], TK_MS)

		As Example 2, and additionally:

		print e.attr1
		>> a

		:param event:
		:type event: String or List
		:param unit:
		"""
		self.events.append(event)
		self.__sync(stages=False)

	def register_stages(self, stages, unit=TK_MS):
		for s in stages:
			self.register_stage(s, unit)

	def register_stage(self, stage, unit=TK_MS):
		if unit == TK_S:
			stage[0] *= 1000
		self.events.append(stage)
		self.__sync(events=False)

	def start(self):
		"""
		Starts the trial clock. This is automatically called by the parent KLExperiment object.

		"""
		try:
			self.register_event(EVI_TRIAL_START)
			while not self.pipe.poll():
				pass
			self.start_time = self.pipe.recv()
			el_val = self.experiment.eyelink.now() if Params.eye_tracking and Params.eye_tracker_available else -1
			self.experiment.evi.log_trial_event(EVI_CLOCK_START, self.start_time, el_val)
		except:
			full_trace()

	def stop(self):
		"""
		Stops the trial clock. This is automatically called by the parent KLExperiment object.

		"""
		el_val = self.experiment.eyelink.now() if Params.eye_tracking and Params.eye_tracker_available else -1
		self.experiment.evi.log_trial_event(EVI_CLOCK_STOP, self.trial_time, el_val)
		Params.process_queue_data = {}
		self.register_event(EVI_CLOCK_RESET)
		self.tasks = []
		self.events = []
		self.sent_events = []
		self.stages = []
		self.events_index = {}
		self.start_time = None
		self.__sync()

	def deregister(self, event_label=None):
		if event_label:
			removed = False
			for e in self.events:
				if e[1] == event_label:
					self.register_event([event_label, EVI_DEREGISTER_EVENT])
					if self.__poll():
						self.events.remove(e)
					else:
						raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(event_label))
					removed = True
			if not removed:
				for e in self.sent_events:
					if e[1] == event_label:
						raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(event_label))
				raise RuntimeError("No such event '{0}'.".format(event_label))
		else:
			self.register_event(EVI_CLOCK_RESET)
		self.__sync()
		self.events = []

	def __sync(self, events=True, stages=True):
		e = self.events if events else False
		s = self.stages if stages else False
		self.pipe.send([e, s])
		for e in self.events:
			self.sent_events.append(e)
			self.events.remove(e)

	def __poll(self):
		while not self.pipe.poll():
			pass
		t = self.pipe.recv()
		if isinstance(t, Exception):
			raise t
		return t

	def terminate(self):
		self.register_event(EVI_EXP_END)

	@property
	def trial_time(self):
		self.register_event(EVI_SEND_TIME)
		return self.__poll()


	@property
	def timestamp(self):
		self.register_event(EVI_SEND_TIMESTAMP)
		return self.__poll()




@threaded
def __event_clock__(pipe):
	start = time.time()
	events = []
	stages = []
	sent = []
	if pipe.poll():
		events, stages = pipe.recv()
	trial_started = False
	try:
		while True:
			if pipe.poll():
				new_e, new_s = pipe.recv()  # new_e/s will be false if not syncing
				if new_e:
					events += new_e
				if new_s:
					stages += new_s
			for e in events:
				if e in EVI_CONSTANTS:
					if e == EVI_CLOCK_RESET:
						trial_started = False
						events = []
						stages = []
						sent = []
						break

					if e == EVI_TRIAL_START:
						sent.append(e)
						events.remove(e)
						start = time.time()
						trial_started = True
						pipe.send(start)
						continue

					if e == EVI_EXP_END:
						return

					if e == EVI_SEND_TIME:
						if not trial_started:
							pipe.send(RuntimeError("Trial has not started."))
						events.remove(e)
						sent.append(e)
						pipe.send(time.time() - start)
						continue

					if e == EVI_SEND_TIMESTAMP:
						if not trial_started:
							pipe.send(RuntimeError("Trial has not started."))
						events.remove(e)
						pipe.send(time.time())
						continue

					if e == EVI_DEREGISTER_EVENT:
						try:
							events.remove(e)
							pipe.send(True)
						except ValueError:
							pipe.send(False)
				if not trial_started:  # allows for registration during setup(), trial_prep(), etc.
					continue

				if e in sent:		   # ensures events aren't multiply sent
					events.remove(e)
					continue

				if (time.time() - start) * 1000  >= e.onset or e.onset == 0:  # ie. something should happen IMMEDIATELY
					if Params.development_mode or True:
						print "\t...Sent '{0}' at {1}".format(e.label, time.time() - start)
					sent.append(e)
					try:
						Params.process_queue.put([e.label, e.data,  time.time(), time.time() - start])
					except IndexError:
						Params.process_queue.put([e.label, None, time.time(), time.time() - start])
	except Exception as e:
		pipe.send(full_trace())