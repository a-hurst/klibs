# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

from os import kill
from time import time
from signal import SIGKILL
from copy import copy
import multiprocessing as mp_lib  # incase you want to try billiard again later

from klibs.KLConstants import TK_S, TK_MS, EVI_CONSTANTS, EVI_CLOCK_START, EVI_CLOCK_STOP, EVI_CLOCK_RESET, EVI_CLOCK_SYNC, \
	EVI_TRIAL_START, EVI_DEREGISTER_EVENT, EVI_SEND_TIME, EVI_EXP_END
from klibs import P
from klibs.KLUtilities import pump, threaded, full_trace
from klibs.KLUserInterface import ui_request
from klibs import event_interface as evi

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
		self.started = time()

	def counting(self):
		if self.paused is not False:
			return False
		else:
			return time() - self.started < self.duration

	def reset(self):
		self.start()
		self.paused = False

	def finish(self):
		self.started = time() - self.duration

	def add(self, time):
		self.started += time

	def pause(self):
		self.paused = time()

	def resume(self):
		self.started += time() - self.paused
		self.paused = False

	def remaining(self):
		return self.duration - (time() - self.started)

	def elapsed(self):
		return time() - self.started

	def unpause(self):
		self.resume()  # deprecated, maintained for backwards compatibility


class TimeKeeper(object):
	moments = {}
	periods = {}
	mean_moments = {}
	mean_periods = {}
	countdowns = {}

	# todo: add units argument as between secondds/ ms

	def __init__(self):
		super(TimeKeeper, self).__init__()
		self.log("Instantiated")

	def log(self, label, time_value=None):
		self.moments[label] = time_value if time_value else time()

	def sample(self, label, time_value=None):
		if label in self.mean_moments:
			self.mean_moments[label].append(time_value if time_value else time())
		else:
			self.mean_moments[label] = [time_value if time_value else time()]

	def sample_start(self, label, time_value=None):
		sample_index = len(self.mean_periods[label]) - 1 if label in self.mean_periods else 0
		sample_key = "{0}.{1}".format(label, sample_index )
		if label in self.mean_periods:
			self.mean_periods[label].append([time_value if time_value else time(), None])
		else:
			self.mean_periods[label] = [[time_value if time_value else time(), None]]
		return sample_key

	def sample_stop(self, label, sample_key=None, time_value=None):
		sample_index = int(sample_key.split(".")[1]) if sample_key is not None else len(self.mean_periods[label]) - 1
		if self.mean_periods[label][sample_index][1] is not None:
			raise RuntimeError("Trying to stop a sample that has already finished.")
		self.mean_periods[label][sample_index][1] = time_value if time_value else time()

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
		self.periods[label] = [time_value if time_value else time(), None]
		return self

	def stop(self, label, time_value=None):
		self.periods[label][1] = time_value if time_value else time()
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
		return time() - self.periods[label][0]

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

	def __init__(self):
		self.__registry = []
		self.tasks = []
		self.events = []
		self.sent_events = []
		self.stages = []
		self.events_index = {}
		self.start_time = None
		self.start_lag = None
		self.pipe, child = mp_lib.Pipe()
		self.p = __event_clock__(child)
		self.pid = self.p.pid
		self.polling = False   # prevents multiple calls to polling simultaneously
		self.tk = TimeKeeper()

	def update_event_onset(self, label, onset, unit=TK_MS):
		self.__update_event(label, update_onset=True, onset=onset, unit=unit)

	def update_event_data(self, label, data):
		self.__update_event(label, update_data=True, data=data)

	def __update_event(self, label, update_onset=False, onset=None, unit=TK_S, update_data=False, data=None):
		try:
			for e in self.events:
				if e.label == label:
					if update_onset:
						if unit == TK_S:
							onset *= 1000
						e.onset = onset
					if update_data:
						e.data = data
		except IndexError:
			e_copy = None
			for e in self.sent_events:
				if e.label == label:
					e_copy = copy(self.sent_events[label])
			if update_onset:
				if unit == TK_S:
					onset *= 1000
				e_copy.onset = onset
			if update_data:
				e_copy.data = data
			if self.trial_time > e_copy.onset:
				raise RuntimeError("Too late to update event '{0}'.".format(e_copy.label))
			P.updated_events.append(e_copy.label)
			self.events.append(e_copy)


	def register_events(self, events):
		from klibs.KLEventInterface import EventTicket
		reg_start = self.timestamp
		for e in events:
			if e not in EVI_CONSTANTS and not isinstance(e, EventTicket):
				raise ValueError("Expected sequence of EventTicket objects or KLEventInterface constants."
								 "To register a single event, use register_event()")
			self.register_event(e)
		return self.timestamp - reg_start

	def register_event(self, event):
		"""
		Inserts passed event into the Trial Clock's event queue. Event can be a string constant (see Event Interface
		constants) or a list of length 2 or 3. The first element must be the time at which the event should be issued;
		the second must be a string, the event label; the third and optional element may contain arbitrary data to be made
		available when the klibs.KLEventInterface.TrialEvent object is created. The contents will be accessible via the
		data attribute of the event (ie. TrialEvent.data). Additionally, if a dictionary is passed, the TrialEvebt object
		will be instantiated with a new attribute for each key thereof (this is supplemental to TrialEvent.data attribute).

		:param event:
		:type event: String or List
		:param unit:
		"""
		reg_start = self.timestamp
		try:
			self.__registry.append(event.label)
		except AttributeError:
			self.__registry.append(event)
		self.events.append(event)
		return self.__sync(stages=False) - reg_start

	# todo: should be 'phase', for one; primarily will be used for setting events with fixed times relative to phase onsets
	# def register_stages(self, stages, unit=TK_MS):
	# 	for s in stages:
	# 		self.register_stage(s, unit)
	#
	# def register_stage(self, stage, unit=TK_MS):
	# 	if unit == TK_S:
	# 		stage[0] *= 1000
	# 	self.events.append(stage)
	# 	self.__sync(events=False)

	def registered(self, label):
		# todo: distinguish this from the method by the same name in EventInterface.
		return label in self.__registry

	def start(self):
		"""
		Starts the trial clock. This is automatically called by the parent KLExperiment object.

		"""
#		try:
		self.register_event(EVI_TRIAL_START)
		self.pipe.poll()
		while not self.start_time:
			self.start_time = self.pipe.recv()
		el_val = self.experiment.eyelink.now() if P.eye_tracking and P.eye_tracker_available else -1
		evi.log_trial_event(EVI_CLOCK_START, self.start_time, el_val)
#		except:
#			print full_trace()

	def stop(self):
		"""
		Stops the trial clock. This is automatically called by the parent KLExperiment object.

		"""
		el_val = self.experiment.eyelink.now() if P.eye_tracking and P.eye_tracker_available else -1
		evi.log_trial_event(EVI_CLOCK_STOP, self.trial_time, el_val)
		P.process_queue_data = {}
		self.register_event(EVI_CLOCK_RESET)
		self.tasks = []
		self.events = []
		self.sent_events = []
		self.stages = []
		self.start_time = None
		self.__sync()
		while not self.__poll():
			if P.verbose_mode:
				print "TrialClock polling from stop()"
			else:
				pass

	def deregister(self, label):
		reg_start = time()
		# todo: fix this fucker, it's broken; trial clock doesn't look for lists, just strings or event objects
		removed = False
		try:
			self.__registry.remove(label)
		except NameError:
			raise NameError("No such event '{0}' registered.".format(label))
		for e in self.events:
			if e[1] == label:
				self.register_event([label, EVI_DEREGISTER_EVENT])
				if self.__poll():
					self.events.remove(e)
				else:
					raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(label))
				removed = True
		if not removed:
			for e in self.sent_events:
				if e[1] == label:
					raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(label))
			raise RuntimeError("No such event '{0}'.".format(label))

		return self.__sync() - reg_start

	def __sync(self, events=True, stages=True):
		e = self.events if events else False
		s = self.stages if stages else False
		self.pipe.send([e, s])
		for e in self.events:
			self.sent_events.append(e)
			self.events.remove(e)
		# if blocking:
		# 	while not self.__poll():
		# 		pass
		# 		if self.__poll() == EVI_EVENT_SYNC_COMPLETE:
		# 			break
		return time()

	def __poll(self):
		self.polling = True
		while not self.pipe.poll():
			ui_request()
		self.polling = False
		t = self.pipe.recv()
		if isinstance(t, Exception):
			raise t
		return t

	def terminate(self, max_wait=1):
		self.tk.start("terminate")
		self.register_event(EVI_EXP_END)
		while self.tk.elapsed("terminate") < max_wait:
			pump()
		if self.p.is_alive():
			kill(self.clock.p.pid, SIGKILL)



	@property
	def trial_time(self):
		self.register_event(EVI_SEND_TIME)
		while self.polling:
			pass
		return self.__poll()

	@property
	def trial_time_ms(self):
		self.register_event(EVI_SEND_TIME)
		while self.polling:
			pass
		return self.__poll() * 1000


	@property
	def timestamp(self):
		# it's not clear that this should exist... it's purpose is semantic; to direct all time-based requests to the
		# Eventclock. But enh...?
		return time()




@threaded
def __event_clock__(pipe):
	from klibs.KLEventInterface import EventTicket
	start = time()
	events = []
	stages = []
	sent = []
	if pipe.poll():
		events, stages = pipe.recv()
	trial_started = False
	def trial_time_ms():
		return (time() - start) * 1000
	try:
		while True:
			if pipe.poll():
				new_e, new_s = pipe.recv()  # new_e/s will be false if not syncing
				if new_e:
					events += new_e
				if new_s:
					stages += new_s

			for e in events:
				if not isinstance(e, EventTicket):
					if e == EVI_CLOCK_RESET:
						start = None
						trial_started = False
						events = []
						stages = []
						sent = []
						pipe.send(True)
						print "TrialReset: {0}, start: {1}".format(trial_started, start)
						break

					if e == EVI_TRIAL_START:
						sent.append(e)
						events.remove(e)
						start = time()
						trial_started = True
						print "TrialStarting: {0}, current time: {1}".format(trial_started, time() - start)
						pipe.send(start)
						continue

					if e == EVI_EXP_END:
						return

					if e == EVI_SEND_TIME:
						if not trial_started:
							print "TrialStarted: {0}, current time: {1}".format(trial_started, time() - start)
							time.sleep(0.1)
							pipe.send(RuntimeError("Trial has not started."))
						events.remove(e)
						sent.append(e)
						pipe.send(time() - start)
						continue

					if e == EVI_DEREGISTER_EVENT:
						# todo: this doesn't seem like it does anything...
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

				if trial_time_ms() >= e.onset or e.onset == 0:  # ie. something should happen IMMEDIATELY
					e_data = [e.label, e.data,  time(), time() - start]
					if P.verbose_mode: print "\tTrialClock sent '{0}' at {1}".format(e_data[0], e_data[3])
					sent.append(e)
					try:
						P.process_queue.put(e_data)
					except IndexError:
						e_data[1] = None
						P.process_queue.put(e_data)
	except Exception as e:
		pipe.send(full_trace())

# # global runtime instances
# tk = TimeKeeper()
# tc = EventClock()