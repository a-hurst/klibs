__author__ = 'jono'

from klibs.KLUtilities import *
import klibs.KLParams as Params
import os
import csv
import time
import abc
import multiprocessing as mp_lib


class EventTicket(object):
	#todo: relative needs to be either relative to now or an event so that relative events can be registered before trial start

	def __init__(self, label, onset, data=None, relative=False, unit=TK_MS):
		super(EventTicket, self).__init__()
		print label, onset, data, relative, unit
		self.__onset = None
		self.__label = None
		self.__unit = None
		self.label = label
		self.relative = relative
		self.unit = unit
		self.onset = onset
		self.data = data

		if Params.clock.start_time:
			Params.clock.trial_time
			print self

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
			time_val += Params.clock.trial_time if self.__unit == TK_S else Params.clock.trial_time * 1000
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


class KlibsEvent(object):

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


class DataEvent(KlibsEvent):

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


class TrialEvent(KlibsEvent):

	def __init__(self, label, time_stamp, trial_time, e_type):
		super(TrialEvent, self).__init__(label, time_stamp, trial_time)
		self.sdl_event_code = e_type

	def __str__(self):
		args = [self.sdl_event_code, self.label, self.trial_time, self.time_stamp, hex(id(self))]
		return "<klibs.KLUtilities.TrialEvent[{0}]: {1} ({2}, {3}) at {4}>".format(*args)


class EventInterface(object):
	experiment = None
	events = {}
	last_trial = None
	sent = {}  # reset on each trial
	trial_event_log = []
	events_dumped = False
	__message_log = []

	def __init__(self, experiment):
		#todo: add default events like recycled trials, etc.
		self.experiment = experiment
		self.import_events()

	def clear(self):
		self.events = {}

	def import_events(self):
		if os.path.exists(Params.events_file_path):
			event_file = csv.reader(open(Params.events_file_path, 'rb'))
			for row in event_file:
				try:
					if len(row) == 0:  # skip empty rows
						continue
					if row[0][0] == "#":  # ie. skip header line, which wasn't in earlier .versions of the config file
						continue
				except IndexError:
					pass
				self.events[row[0]] = DataEvent(*row)

	def list_events(self):
		for e in self.events:
			print e

	def log_trial_event(self, label, trial_time, eyelink_time=-1 ):
		e = [Params.participant_id, Params.trial_id, Params.trial_number, label, trial_time, eyelink_time]
		if Params.dm_print_log:
			print "Logging: {0}".format(e)
		self.trial_event_log.append(e)

	def dump_events(self):
		for ev in Params.process_queue_data:
			e = Params.process_queue_data[ev]
			self.log_trial_event(e.label, e.trial_time)
		for e in self.trial_event_log:
			try:
				self.experiment.database.query_str_from_raw_data(TBL_EVENTS, e)
				self.experiment.database.insert(e, TBL_EVENTS, False)
			except RuntimeError:
				print "Event Table not found; if this is an old KLIBs experiment, consider updating the SQL schema to the new standard."
				break
		self.events_dumped = True

	def after(self, label, pump_events=False):
		if pump_events:
			self.experiment.ui_request(pump(True))
		for e in Params.process_queue_data:
			if Params.process_queue_data[e].label == label:
				return True
		return False

	def registered(self, label):
		"""
		Determines if an event exists in the events
		:param label:
		"""
		return label in self.events

	def written(self, message):
		"""
		Determines if an message exists in the message log
		:param message:
		"""
		return message in self.__message_log

	def before(self, label, pump_events=False):
		if pump_events:
			self.experiment.ui_request(pump())
		for e in Params.process_queue_data:
			if Params.process_queue_data[e].label == label:
				return False
		return True

	def between(self, event_1, event_2):
		return self.after(event_1) and not self.after(event_2)

	def write(self, message, edf=True, eeg=True):
		if not Params.labjacking:
			eeg = False
		if not Params.eye_tracking:
			edf = False
		self.__message_log.append(message)
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
		if Params.eye_tracker_available and Params.eye_tracking and edf:
			self.experiment.eyelink.write(edf_send)
		if Params.labjack_available and Params.labjacking and eeg:
			self.experiment.labjack.write(eeg_send)

		if Params.development_mode and edf and not Params.eye_tracker_available:
			print "\t\033[94mEvent (\033[92mEDF\033[94m): \033[0m{0}".format(edf_send)
		if Params.development_mode and eeg and not Params.labjack_available:
			print "\t\033[94mEvent (\033[92mEEG\033[94m): \033[0m{0}".format(eeg_send)

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


