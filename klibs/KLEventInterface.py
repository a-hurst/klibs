# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import os
import csv
import time
import abc
from copy import copy
import multiprocessing as mp
from os import kill
from signal import SIGKILL


from klibs.KLEnvironment import Environment
from klibs.KLConstants import TK_S, TK_MS, TBL_EVENTS, EVI_CONSTANTS, EVI_DEREGISTER_EVENT, EVI_CLOCK_START,\
	EVI_CLOCK_STOP, EVI_CLOCK_RESET, EVI_TRIAL_START, EVI_SEND_TIME, EVI_EXP_END
from klibs import P
from klibs.KLUtilities import pump
from klibs.KLUserInterface import ui_request

# todo: all the event objects should be created from factory methods, ensuring the current env clock is available

class TrialEventTicket(object, Environment):
	#todo: relative needs to be either relative to now or an event so that relative events can be registered before trial start

	def __init__(self, label, onset, data=None, relative=False, unit=TK_MS):
		super(TrialEventTicket, self).__init__()
		self.__onset = None
		self.__label = None
		self.__unit = None
		self.label = label
		self.relative = relative
		self.unit = unit
		self.onset = onset
		self.data = data

	def __str__(self):
		return "<klibs.KLEventInterface.EventTicket, ('{0}': {1}, at {3})".format(self.label, self.onset, self.data, hex(id(self)))

	@property
	def onset(self):
		return self.__onset

	@onset.setter
	def onset(self, time_val):
		if type(time_val) not in [int, float] or time_val < 0:
			raise TypeError("Property 'onset' must be a positive integer; got {0}.".format(time_val))
		if self.relative:
			time_val += self.clock.trial_time if self.__unit == TK_S else self.clock.trial_time_ms
		if self.__unit == TK_S:
			time_val *= 1000
		self.__onset = time_val

	@property
	def label(self):
		return self.__label

	@label.setter
	def label(self, val):
		if type(val) is not str:
			raise TypeError("Property 'label' must be a string.")
		self.__label = val

	@property
	def unit(self):
		return self.__unit

	@unit.setter
	def unit(self, val):
		if val not in [TK_S, TK_MS]:
			raise TypeError("Property 'unit' must be a valid KLTimeKeeper constant.")
		self.__unit = val


class Event(object):

	def __init__(self, label, data=None, time_stamp=None, trial_time=None):
		self.label = label
		self.__created = time.time()
		self.time_stamp = time_stamp
		self.trial_time = trial_time
		self.data = data
		if type(data) is dict:
			for key in data:
				setattr(self, key, data[key])

	@abc.abstractmethod
	def __str__(self):
		pass


class DataEvent(Event):

	def __init__(self, label, arg_count, eeg_code_to_edf, code, message):
		super(DataEvent, self).__init__(label)
		self.label = label
		self.dynamic = int(arg_count) > 0 or arg_count is False
		self.arg_count = int(arg_count) if self.dynamic else 0
		self.eeg_code_to_edf = eeg_code_to_edf in ("true", "True")
		try:
			self.code = int(code)
		except TypeError:
			self.code = None
		self.message = message

	def __str__(self):
		return "<klibs.KLEventInterface.Event, ('{0}', EEG: {1}, EDF: {2} at {3})".format(self.label, self.code, self.message,  hex(id(self)))


class TrialEvent(Event):

	def __init__(self, label, time_stamp, trial_time, e_type):
		super(TrialEvent, self).__init__(label, time_stamp, trial_time)
		self.sdl_event_code = e_type

	def __str__(self):
		args = [self.sdl_event_code, self.label, self.trial_time, self.time_stamp, hex(id(self))]
		return "<klibs.KLUtilities.TrialEvent[{0}]: {1} ({2}, {3}) at {4}>".format(*args)


class EventManager(object, Environment):
	events = {}
	sent_events = {}
	stages = {}
	last_trial = None
	sent = {}  # reset on each trial
	trial_event_log = []
	events_dumped = False
	polling = False  # true whilst awaiting reply from trial_clock process
	start_time = None
	__message_log__ = []
	__clock__ = None

	def __init__(self):
		super(EventManager, self).__init__(self)
		self.pipe, child = mp.Pipe()
		self.p = __event_clock__(child)
		self.pid = self.p.pid


	def __poll__(self):
		"""
		Get incoming messages from the trial_clock.

		:return: :raise t:
		"""
		self.polling = True
		while not self.pipe.poll():
			ui_request()
		self.polling = False
		t = self.pipe.recv()
		if isinstance(t, Exception):
			raise t
		return t

	def __update_event__(self, label, update_onset=False, onset=None, unit=TK_S, update_data=False, data=None):
		"""
		Change any aspect of a registered event (if it has not been issued).

		:param label:
		:param update_onset:
		:param onset:
		:param unit:
		:param update_data:
		:param data:
		:raise RuntimeError:
		"""
		try:
			for e in self.events:
				if e.label == label:
					if update_onset:
						if unit == TK_S: onset *= 1000
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
				raise RuntimeError("Event '{0}' has already been issued.".format(e_copy.label))
			self.updated_events.append(e_copy.label)
			self.events.append(e_copy)

	def __sync__(self, events=True, stages=True):
		"""
		Sends registered events to trial_clock and transfers events from self.events to self.sent_events.
		Stages not usefully or reliably implemented yet.

		:param events:
		:param stages:
		:return:
		"""
		e = self.events if events else False
		s = self.stages if stages else False
		self.pipe.send([e, s])
		for e in self.events:
			self.sent_events.append(e)
			self.events.remove(e)
		return time()

	def after(self, label, pump_events=False):
		"""
		Checks if event has been issued yet.

		:param label:
		:param pump_events:
		:return: :raise NameError:
		"""
		if not self.registered(label):
			raise NameError("'{0}' not registered.".format(label))

		if pump_events:
			pump()
			ui_request()
		for e in self.process_queue_data:
			if self.process_queue_data[e].label == label:
				return True
		return False

	def before(self, label, pump_events=False):
		"""
		Checks if event has been issued yet.

		:param label:
		:param pump_events:
		:return: :raise NameError:
		"""
		if not label:
			raise ValueError("Expected 'str' for argument label; got {0}.".format(type(label)))
		if not self.registered(label):
			e_msg = "'{0}' not registered.".format(label)
			raise NameError(e_msg)
		if pump_events:
			pump()
			ui_request()
		for e in self.process_queue_data:
			if self.process_queue_data[e].label == label:
				return False
		return True

	def between(self, label_1, label_2):
		"""
		Checks if first event, but not the second, has been issued yet.

		:param label_1:
		:param label_2:
		:return: :raise NameError:
		"""
		if not self.registered(label_1):
			raise NameError("'{0}' not registered.".format(label_1))
		if not self.registered(label_2):
			raise NameError("'{0}' not registered.".format(label_2))

		return self.after(label_1) and not self.after(label_2)

	def clear(self):
		"""
		Removes entire pending event queue.

		"""
		self.events = {}

	def deregister(self, label):
		"""
		Broken; do not use.

		:param label:
		:return: :raise RuntimeError:
		"""
		reg_start = time()
		# todo: fix this fucker, it's broken; trial clock doesn't look for lists, just strings or event objects
		removed = False
		try:
			self.__registry__.remove(label)
		except NameError:
			raise NameError("No such event '{0}' registered.".format(label))
		for e in self.events:
			if e[1] == label:
				self.register_event([label, EVI_DEREGISTER_EVENT])
				if self.__poll__():
					self.events.remove(e)
				else:
					raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(label))
				removed = True
		if not removed:
			for e in self.sent_events:
				if e[1] == label:
					raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(label))
			raise RuntimeError("No such event '{0}'.".format(label))

		return self.__sync__() - reg_start

	def dump_events(self):
		"""
		Records entire event queue to event table of the database.

		"""
		# todo: logic for when this is called a second time (ie. clear events from database before re-entering
		for ev in self.process_queue_data:
			e = self.process_queue_data[ev]
			self.log_trial_event(e.label, e.trial_time)
		for e in self.trial_event_log:
			try:
				self.db.query_str_from_raw_data(TBL_EVENTS, e)
				self.db.insert(e, TBL_EVENTS, False)
			except RuntimeError:
				print "Event Table not found; if this is an old KLIBs experiment, consider updating the SQL schema to the new standard."
				break
		self.events_dumped = True

	def import_events(self):
		"""
		Imports trial and data events from an external file.


		"""
		if os.path.exists(P.events_file_path):
			event_file = csv.reader(open(P.events_file_path, 'rb'))
			for row in event_file:
				try:
					if len(row) == 0:  # skip empty rows
						continue
					if row[0][0] == "#":  # ie. skip header line, which wasn't in earlier .versions of the config file
						continue
				except IndexError:
					pass
				self.events[row[0]] = DataEvent(*row)

	def log_trial_event(self, label, trial_time, eyelink_time=-1):
		"""
		Records that an event has been issued; not permanently stored until dump_events() is called.

		:param label:
		:param trial_time:
		:param eyelink_time:
		"""
		e = [P.participant_id, P.trial_id, P.trial_number, label, trial_time, eyelink_time]
		if P.verbose_mode:
			print "Logging: {0}".format(e)
		self.trial_event_log.append(e)

	def start(self):
		"""
		Starts the trial clock. This is automatically called by the parent KLExperiment object.

		"""
		self.register_event(EVI_TRIAL_START)
		self.pipe.poll()
		while not self.start_time:
			self.start_time = self.pipe.recv()
		el_val = self.exp.eyelink.now() if P.eye_tracking and P.eye_tracker_available else -1

		self.log_trial_event(EVI_CLOCK_START, self.start_time, el_val)

	def stop(self):
		"""
		Stops the trial clock. This is automatically called by the parent KLExperiment object.

		"""
		el_val = self.experiment.eyelink.now() if P.eye_tracking and P.eye_tracker_available else -1
		self.log_trial_event(EVI_CLOCK_STOP, self.trial_time, el_val)
		self.env.process_queue_data = {}
		self.register_event(EVI_CLOCK_RESET)
		self.events = []
		self.sent_events = []
		self.stages = []
		self.start_time = None
		self.__sync__()
		while not self.__poll__():
			if P.verbose_mode:
				print "TrialClock polling from stop()"
			else:
				pass

	def terminate(self, max_wait=1):
		self.tk.start("terminate")
		self.register_event(EVI_EXP_END)
		while self.tk.elapsed("terminate") < max_wait:
			pump()
		if self.p.is_alive():
			kill(self.clock.p.pid, SIGKILL)

	def register_events(self, events):

		reg_start = self.timestamp
		for e in events:
			if e not in EVI_CONSTANTS and not isinstance(e, TrialEventTicket):
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
			self.__registry__.append(event.label)
		except AttributeError:
			self.__registry__.append(event)
		self.events.append(event)
		return self.__sync__(stages=False) - reg_start


	def registered(self, label):
		"""
		Determines if an event exists in the events log
		:param label:
		"""
		return label in self.events

	def send(self, label, max_per_trial=1, args=None, eeg_code_to_edf=None, code=None, message=None):
		if label in self.sent and self.sent[label] >= max_per_trial:
			return
		if label not in self.sent:
			self.sent[label] = 1
		else:
			self.sent[label] += 1
		try:
			e = self.events[label]
		except KeyError:
			try:
				iter(args)
				arg_count = len(args)
			except:
				arg_count = 0
			e = DataEvent(label, arg_count, eeg_code_to_edf, code, message)
			self.events[label] = e
		if e.code:
			self.write(e.code, False, True)
		if e.message:
			try:
				message = e.message.format(*args)
			except TypeError:
				message = e.message
			if e.eeg_code_to_edf and e.code:
				message = "TA_{0}: {1}".format(e.code, message)
			self.write(message, True, False)

	def update_event_onset(self, label, onset, unit=TK_MS):
		"""
		Changes the  onset time for a registered event (if it has not yet been issued).

		:param label:
		:param onset:
		:param unit:
		"""
		self.__update_event__(label, update_onset=True, onset=onset, unit=unit)

	def update_event_data(self, label, data):
		"""
		Changes the data for a registered event (if it has not yet been issued).

		:param label:
		:param data:
		"""
		self.__update_event__(label, update_data=True, data=data)

	def written(self, message):
		"""
		Determines if an message exists in the message log
		:param message:
		"""
		return message in self.__message_log__

	def write(self, message, edf=True, eeg=True):
		if not P.labjacking:
			eeg = False
		if not P.eye_tracking:
			edf = False
		self.__message_log__.append(message)
		if type(message) in [list, tuple]:
			edf_send = message[0]
			eeg_send = message[1]
		else:
			if type(message) is int and eeg:
				edf_send = message
				eeg_send = message
			elif type(message) is str and edf:
				edf_send = message
			else:
				raise ValueError("Can only send integer values to eeg via LabJack.")
		if P.eye_tracker_available and P.eye_tracking and edf:
			self.experiment.eyelink.write(edf_send)
		if P.labjack_available and P.labjacking and eeg:
			self.experiment.labjack.write(eeg_send)

		if P.verbose_mode and edf:
			print "\t\033[94mEvent (\033[92mEDF\033[94m): \033[0m{0}".format(edf_send)
		if P.verbose_mode and eeg:
			print "\t\033[94mEvent (\033[92mEEG\033[94m): \033[0m{0}".format(eeg_send)

	@property
	def trial_time(self):
		self.register_event(EVI_SEND_TIME)
		while self.polling:
			pass
		return self.__poll__()

	@property
	def trial_time_ms(self):
		self.register_event(EVI_SEND_TIME)
		while self.polling:
			pass
		return self.__poll__() * 1000

	@property
	def timestamp(self):
		# it's not clear that this should exist... it's purpose is semantic; to direct all time-based requests to the
		# Eventclock. But enh...?
		return time()

	# Debugging Methods

	def debug_list_events(self):
		for e in self.events:
			print e


@threaded
def __event_clock__(pipe):
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
				if not isinstance(e, TrialEventTicket):
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
						env.process_queue.put(e_data)
					except IndexError:
						e_data[1] = None
						env.process_queue.put(e_data)
	except Exception as e:
		pipe.send(full_trace())