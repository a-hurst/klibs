__author__ = 'jono'
from klibs.KLParams import *
from klibs.KLExceptions import *
from klibs.KLUtilities import *
import os
import csv

class Event(object):

	def __init__(self, data):
		self.label = data[0]
		self.dynamic = int(data[1]) > 0 or data[1] is False
		self.arg_count = int(data[1]) if self.dynamic else 0
		self.eeg_code_to_edf = data[2] in ("true", "True")
		self.code = int(data[3])
		self.message = data[4]

	def __str__(self):
		return "klibs.Event, ('{0}', EEG: {1}, EDF: {2} at {3})".format(self.label, self.code, self.message,  hex(id(self)))


class EventInterface(object):
	experiment = None
	events = {}
	last_trial = None
	sent = {}  # reset on each trial

	def __init__(self, experiment):
		self.experiment = experiment
		self.import_events()

	def import_events(self):
		if os.path.exists(Params.events_file_path):
			event_file = csv.reader(open(Params.events_file_path, 'rb'))
			for row in event_file:
				try:
					if len(row) == 0:  # skip empty rows
						continue
					if row[0][0] == "#":  # ie. skip header line, which wasn't in earlier versions of the config file
						continue
				except IndexError:
					pass
				self.events[row[0]] = Event(row)

	def list_events(self):
		for e in self.events:
			print e

	def write(self, message, edf=True, eeg=True):
		if iterable(message):
			edf_send = message[0]
			eeg_send = message[1]
		else:
			if type(message) is int and eeg:
				edf_send = message
				eeg_send = message
			elif type(message) is str and edf and not eeg:
				edf_send = message
			else:
				raise ValueError("Can only send integer values to eeg via LabJack.")
		if Params.eye_tracker_available and Params.eye_tracking and edf:
			self.experiment.eyelink.write(edf_send)
		if Params.labjack_available and Params.labjacking and eeg:
			self.experiment.labjack.write(eeg_send)

		if Params.development_mode and edf and not Params.eye_tracker_available:
			print "\t\033[94mEvent (\033[92mEDF\033[94m): \033[0m'{0}".format(edf_send)
		if Params.development_mode and eeg and not Params.labjack_available:
			print "\t\033[94mEvent (\033[92mEEG\033[94m): \033[0m'{0}".format(eeg_send)

	def send(self, label, max_per_trial=1, args=None):
		if label in self.sent and self.sent[label] >= max_per_trial:
			return
		if label not in self.sent:
			self.sent[label] = 1
		else:
			self.sent[label] += 1
		e = self.events[label]

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


