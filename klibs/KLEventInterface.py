# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import os
import csv
import abc
from time import time, sleep
import multiprocessing as mp

from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import EventError
from klibs.KLNamedObject import NamedObject, NamedInventory, CachedInventory
from klibs.KLConstants import (TK_S, TK_MS, TBL_EVENTS, EVI_CONSTANTS, EVI_DEREGISTER_EVENT,
	EVI_SEND_TIME, EVI_CLOCK_RESET, EVI_TRIAL_START, EVI_TRIAL_STOP, EVI_EXP_END)
from klibs import P
from klibs.KLUtilities import pump
from klibs.KLUserInterface import ui_request


class TrialEventTicket(EnvAgent, NamedObject):
	#todo: relative needs to be either relative to now or an event so that relative events can be registered before trial start

	def __init__(self, label, onset=None, data=None, relative=False, unit=TK_MS):
		EnvAgent.__init__(self)
		NamedObject.__init__(self, label)
		if not onset:
			if label in EVI_CONSTANTS:
				onset = 0
			else:
				raise TypeError("TrialEventTicket expected an onset value.")
		self.__onset__ = None
		self.__label__ = None
		self.__unit__ = None
		self.label = label
		self.relative = relative
		self.unit = unit
		self.onset = onset
		self.data = data
		self.issued = False
		self.issued_at = None
		self.trial = P.trial_number
		self.block = P.block_number
		self.created = time()

	def __str__(self):
		return "<klibs.KLEventInterface.EventTicket, ('{0}': {1} at {2})>".format(self.label, self.onset, hex(id(self)))

	def issue(self, trial_time):
		self.issued = True
		self.issued_at = trial_time
		try:
			return [self.label, self.data, time(), trial_time, self.el.now()]
		except AttributeError:
			return [self.label, self.data, time(), trial_time, -1]


	@property
	def onset(self):
		return self.__onset__

	@onset.setter
	def onset(self, time_val):
		if type(time_val) not in [int, float] or time_val < 0:
			raise TypeError("Property 'onset' must be a positive integer; got {0}.".format(time_val))
		if self.relative:
			if not self.evm.start_time:
				raise EventError("Trial has not started; relatively-timed event onsets not possible.")
			time_val += self.evm.trial_time if self.__unit__ == TK_S else self.evm.trial_time_ms
		if self.__unit__ == TK_S:
			time_val *= 1000
		self.__onset__ = time_val

	@property
	def label(self):
		return self.__label__

	@label.setter
	def label(self, val):
		if type(val) is not str:
			raise TypeError("Property 'label' must be a string.")
		self.__label__ = val

	@property
	def unit(self):
		return self.__unit__

	@unit.setter
	def unit(self, val):
		if val not in [TK_S, TK_MS]:
			raise TypeError("Property 'unit' must be a valid KLTimeKeeper constant.")
		self.__unit__ = val


class Event(NamedObject):

	def __init__(self, label, data=None, time_stamp=None, trial_time=None):
		super(Event, self).__init__(label)
		self.label = label
		self.__created__ = time()
		self.time_stamp = time_stamp
		self.trial_time = trial_time
		self.trial_id = P.trial_id
		self.data = data
		self.trial = P.trial_number
		self.block = P.block_number
		self.participant_id = P.participant_id

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
	# label, time_stamp, trial_time, eyelink_time, sdl_event_code
	def __init__(self, label, data, time_stamp, trial_time, eyelink_time, e_type):
		super(TrialEvent, self).__init__(label, data, time_stamp, trial_time)
		self.sdl_event_code = e_type
		self.eyelink_time = eyelink_time

	def __str__(self):
		args = [self.sdl_event_code, self.__name__, self.trial_time, self.time_stamp, hex(id(self))]
		return "<klibs.KLUtilities.TrialEvent[{0}]: {1} ({2}, {3}) at {4}>".format(*args)

	def dump(self):
		return {
		"participant_id": self.participant_id,
		"trial_id": self.trial_id,
		"trial_num": self.trial,
		"block_num": self.block,
		"label": self.label,
		"event_data": self.data,
		"unix_timestamp": self.time_stamp,
		"trial_time": self.trial_time,
		"eyelink_time": self.eyelink_time,
		"sdl_event_code" : self.sdl_event_code}


class EventManager(EnvAgent):
	queued_tickets = None
	issued_tickets = None
	trial_events = None
	data_events = None
	stages = None
	last_trial = None
	sent = None  # reset on each trial
	trial_event_log = []
	events_dumped = False
	polling = False  # true whilst awaiting reply from trial_clock process
	start_time = None
	__all_tickets__ = None
	__clock__ = None

	def __init__(self):
		super(EventManager, self).__init__()
		self.__all_tickets__ = []
		self.queued_tickets = NamedInventory()
		self.issued_tickets = NamedInventory()
		self.data_events = CachedInventory()
		self.trial_events = CachedInventory()
		self.pipe, child = mp.Pipe()
		self.clock_sync_queue = mp.Queue()
		self.clock = mp.Process(target=__event_clock__, args=(child, self.clock_sync_queue))
		self.clock.start()

	def __poll__(self):
		"""
		Get incoming messages from the trial_clock.

		:return: :raise t:
		"""
		self.polling = True
		while not self.pipe.poll():
			pass
		self.polling = False
		t = self.pipe.recv()
		if isinstance(t, Exception):
			raise t
		return t

	def __update_ticket__(self, label, update_onset=False, onset=None, unit=TK_S, update_data=False, data=None):
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
		if label in self.queued_tickets:
			if update_onset:
				if unit == TK_S: onset *= 1000
				self.queued_tickets[label].onset = onset
			if update_data: self.queued_tickets[label].data = data
		else:
			raise EventError("Event '{0}' has already been issued.".format(label))

	def __sync_tickets__(self, events=True, stages=True):
		"""
		Sends registered events to trial_clock and transfers events from self.events to self.sent_events.
		Stages not usefully or reliably implemented yet.

		:param events:
		:param stages:
		:return:
		"""
		e = self.queued_tickets if events else False
		s = self.stages if stages else False
		self.pipe.send([e, s])
		for e in self.queued_tickets:
			self.issued_tickets.add(self.queued_tickets.pop(e))

	def after(self, label, pump_events=False):
		"""
		Checks if event has been issued yet.

		:param label:
		:param pump_events:
		:return: :raise NameError:
		"""
		if type(label) is not str:
			raise ValueError("Expected 'str' for argument label; got {0}.".format(type(label)))
		if not self.registered(label):
			raise NameError("Event '{0}' not registered with the EventInterface.".format(label))
		if pump_events:
			ui_request()

		return label in self.trial_events

	def before(self, label, pump_events=False):
		"""
		Checks if event has been issued yet.

		:param label:
		:param pump_events:
		:return: :raise NameError:
		"""
		if type(label) is not str:
			raise ValueError("Expected 'str' for argument label; got {0}.".format(type(label)))
		if not self.registered(label):
			raise NameError("Event '{0}' not registered with the EventInterface.".format(label))
		if pump_events:
			ui_request()

		return label not in self.trial_events

	def between(self, label_1, label_2):
		"""
		Checks if first event, but not the second, has been issued yet.

		:param label_1:
		:param label_2:
		"""

		return self.after(label_1) and self.before(label_2)

	def clear(self):
		"""
		Removes entire pending & sent event queue.

		"""
		self.trial_events.cache("B{0}_T{1}".format(P.block_number, P.trial_number))
		self.data_events.cache("B{0}_T{1}".format(P.block_number, P.trial_number))
		self.queued_tickets.clear()
		self.issued_tickets.clear()
		self.__all_tickets__ = []

	def dump_events(self):
		"""
		Records entire event queue to event table of the database.

		"""
		for cache in self.trial_events.dump().values():
			for e in cache:
				try:
					self.db.insert(cache[e].dump(), TBL_EVENTS, False)
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
				self.queud_events.add(DataEvent(*row))

	def log_trial_event(self, label, time_stamp, trial_time, data=None, eyelink_time=None, sdl_event_code=None):
		"""
		Records issued events; not permanently stored until dump_events() is called.

		:param label:
		:param trial_time:
		:param eyelink_time:
		"""
		self.trial_events.add(TrialEvent(label, data, time_stamp, trial_time, eyelink_time, sdl_event_code))

	def log_data_event(self, data_event, edf=True, eeg=True):

		# override instructions if project is not currently using given device
		if not P.labjacking: eeg = False
		if not P.eye_tracking: edf = False

		self.data_events.add(data_event)

		if type(data_event) in [list, tuple]:
			edf_send = data_event[0]
			eeg_send = data_event[1]
		else:
			if type(data_event) is int and eeg:
				edf_send = data_event
				eeg_send = data_event
			elif type(data_event) is str and edf:
				edf_send = data_event
			else:
				raise ValueError("Can only send integer values to eeg via LabJack.")
		if P.eye_tracker_available and P.eye_tracking and edf:
			self.exp.eyelink.log_data_event(edf_send)
		if P.labjack_available and P.labjacking and eeg:
			self.exp.labjack.log_data_event(eeg_send)

		if P.verbose_mode and edf:
			print "\t\033[94mEvent (\033[92mEDF\033[94m): \033[0m{0}".format(edf_send)
		if P.verbose_mode and eeg:
			print "\t\033[94mEvent (\033[92mEEG\033[94m): \033[0m{0}".format(eeg_send)

	def registered(self, label):
		"""
		Determines if an event ticket exists in either the queued or issued event logs.

		:param label:
		"""
		return label in self.__all_tickets__

	def register_tickets(self, events):
		"""
		Batch registration of event tickets (or lists of event data).

		:param events:
		:raise ValueError:
		"""
		for e in events:
			if e not in EVI_CONSTANTS and not isinstance(e, TrialEventTicket):
				try:
					iter(e)
				except AttributeError:
					raise ValueError("Expected sequence of EventTicket objects or KLEventInterface constants. \
					To register a single event, use register_event()")
			self.register_ticket(e)

	def register_ticket(self, event):
		"""
		Inserts passed event into the Trial Clock's event queue. Event can be a string constant (see Event Interface
		constants) or a list of length 2 or 3. The first element must be the time at which the event should be issued;
		the second must be a string, the event label; the third and optional element may contain arbitrary data to be made
		available when the klibs.KLEventInterface.TrialEvent object is created. The contents will be accessible via the
		data attribute of the event (ie. TrialEvent.data). Additionally, if a dictionary is passed, the TrialEvebt object
		will be instantiated with a new attribute for each key thereof (this is supplemental to TrialEvent.data attribute).

		:param event:
		:type event: String, TrialEventTicket or List
		:param unit:
		"""
		# reg_start = self.timestamp  # this line is only used for debugging
		if event in EVI_CONSTANTS:
			event = TrialEventTicket(event)
		if not isinstance(event, TrialEventTicket):
			try:
				event = TrialEventTicket(*event)
			except SyntaxError:
				raise TypeError("Expected TrialEventTicket, EventInterface constant or list for argument 'event'.")
		self.__all_tickets__.append(event.label)
		self.queued_tickets.add(event)
		self.__sync_tickets__(stages=False)
		# return self.__sync_tickets__(stages=False) - reg_start # this line is only used for debugging

	def since(self, label):
		if type(label) is not str:
			raise ValueError("Expected 'str' for argument label; got {0}.".format(type(label)))
		if not self.registered(label):
			raise NameError("Event '{0}' not registered with the EventInterface.".format(label))
		if label not in self.trial_events:
			raise EventError("Event '{0}' has not yet been issued.".format(label))
		return self.trial_time_ms - self.issued_tickets[label].onset

	def start_clock(self):
		"""
		Starts the trial clock. This is automatically called by the parent KLExperiment object.

		"""
		self.register_ticket(EVI_TRIAL_START)
		self.pipe.poll()
		while not self.start_time:
			self.start_time = self.pipe.recv()
		el_val = self.el.now() if P.eye_tracking and P.eye_tracker_available else -1
		self.log_trial_event(EVI_TRIAL_START, time(), self.start_time, None, el_val, None)

	def stop_clock(self):
		"""
		Stops the trial clock. This is automatically called by the parent KLExperiment object.

		"""
		el_val = self.el.now() if P.eye_tracking and P.eye_tracker_available else -1
		self.log_trial_event(EVI_TRIAL_STOP, time(), self.trial_time, None, el_val, None)
		self.register_ticket(EVI_CLOCK_RESET)
		self.clear()
		self.start_time = None
		self.__sync_tickets__()
		while not self.__poll__(): pass

	def terminate(self, max_wait=1):
		self.tk.start("terminate")
		self.clock.terminate()
		while self.tk.elapsed("terminate") < max_wait:
			sleep(0.05)
			if not self.clock.is_alive():
				break
		if self.clock.is_alive():
			raise RuntimeError("Unable to terminate clock process")

	def until(self, label):
		self.__sync_tickets__()
		if type(label) is not str:
			raise ValueError("Expected 'str' for argument label; got {0}.".format(type(label)))
		if not self.registered(label):
			raise KeyError("Event '{0}' not registered with the EventInterface.".format(label))
		if label in self.trial_events:
			raise EventError("Event '{0}' already issued.".format(label))
		return self.issued_tickets[label].onset - self.trial_time_ms

	def update_ticket_onset(self, label, onset, unit=TK_MS):
		"""
		Changes the  onset time for a registered event (if it has not yet been issued).

		:param label:
		:param onset:
		:param unit:
		"""
		self.__update_ticket__(label, update_onset=True, onset=onset, unit=unit)

	def update_ticket_data(self, label, data):
		"""
		Changes the data for a registered event (if it has not yet been issued).

		:param label:
		:param data:
		"""
		self.__update_ticket__(label, update_data=True, data=data)

	def written(self, data_event):
		"""
		Determines if a data event exists in the log.

		:param data_event:
		"""
		return data_event in self.data_events

	@property
	def trial_time(self):
		self.register_ticket(EVI_SEND_TIME)
		while self.polling:
			pass
		return self.__poll__()

	@property
	def trial_time_ms(self):
		self.register_ticket(EVI_SEND_TIME)
		while self.polling:
			pass
		return self.__poll__() * 1000

	@property
	def timestamp(self):
		# it's not clear that this should exist... it's purpose is semantic; to direct all time-based requests to the
		# Eventclock. But enh...?
		return time()

	# Debugging Methods

	def debug_list_tickets(self):
		for e in self.queued_tickets:
			print e

# def deregister(self, label):
	# 	"""
	# 	Broken; do not use.
	#
	# 	:param label:
	# 	:return: :raise RuntimeError:
	# 	"""
	# 	reg_start = time()
	# 	# todo: fix this fucker, it's broken; trial clock doesn't look for lists, just strings or event objects
	# 	removed = False
	# 	try:
	# 		self.__registry__.remove(label)
	# 	except NameError:
	# 		raise NameError("No such event '{0}' registered.".format(label))
	# 	for e in self.queud_events:
	# 		if e[1] == label:
	# 			self.register_event([label, EVI_DEREGISTER_EVENT])
	# 			if self.__poll__():
	# 				self.queud_events.remove(e)
	# 			else:
	# 				raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(label))
	# 			removed = True
	# 	if not removed:
	# 		for e in self.issued_events:
	# 			if e[1] == label:
	# 				raise RuntimeError("Cannot remove event '{0}' as it has already been sent.".format(label))
	# 		raise RuntimeError("No such event '{0}'.".format(label))
	#
	# 	return self.__sync__() - reg_start


# def send(self, label, max_per_trial=1, args=None, eeg_code_to_edf=None, code=None, message=None):
	# 	if label in self.issued_events and self.issued_events[label].issued >= max_per_trial:
	# 		return
	# 	if label not in self.sent:
	# 		self.sent[label] = 1
	# 	else:
	# 		self.sent[label] += 1
	# 	try:
	# 		e = self.queud_events[label]
	# 	except KeyError:
	# 		try:
	# 			iter(args)
	# 			arg_count = len(args)
	# 		except:
	# 			arg_count = 0
	# 		e = DataEvent(label, arg_count, eeg_code_to_edf, code, message)
	# 		self.queud_events[label] = e
	# 	if e.code:
	# 		self.write(e.code, False, True)
	# 	if e.message:
	# 		try:
	# 			message = e.message.format(*args)
	# 		except TypeError:
	# 			message = e.message
	# 		if e.eeg_code_to_edf and e.code:
	# 			message = "TA_{0}: {1}".format(e.code, message)
	# 		self.write(message, True, False)


def __event_clock__(pipe, queue):
	start = time()
	events = []
	stages = []
	sent = []

	if pipe.poll(): events, stages = pipe.recv()
	trial_started = False

	def trial_time_ms():
		return (time() - start) * 1000

	def trial_time():
		return time() - start

	while True:
		if pipe.poll():
			new_e, new_s = pipe.recv()  # new_e/s will be false if not syncing
			if new_e:
				events += new_e
			if new_s:
				stages += new_s

		for e in events:
			if e.label == EVI_CLOCK_RESET:
				start = None
				trial_started = False
				events = []
				stages = []
				sent = []
				pipe.send(True)
				# print "TrialReset: {0}, start: {1}".format(trial_started, start)
				break

			if e.label == EVI_TRIAL_START:
				sent.append(e)
				events.remove(e)
				start = time()
				trial_started = True
				# print "TrialStarting: {0}, current time: {1}".format(trial_started, trial_time())
				pipe.send(start)
				continue

			if e.label == EVI_EXP_END:
				return

			if e.label == EVI_SEND_TIME:
				if not trial_started:
					# print "TrialStarted: {0}, current time: {1}".format(trial_started, trial_time())
					sleep(0.1)
					pipe.send(RuntimeError("Trial has not started."))
				events.remove(e)
				sent.append(e)
				pipe.send(trial_time())
				continue

			if e.label == EVI_DEREGISTER_EVENT:
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

			if trial_time_ms() >= e.onset:  # issue event tickets whose onset has arrived
				queue.put(e.issue(trial_time_ms()))
				sent.append(e)
