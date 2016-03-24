__author__ = 'jono'

from os import listdir
from os.path import isfile, join
import re
import sqlite3

FIX = 'fixation'
SAC = 'saccade'
S_FIX = re.compile('^SFIX')
E_FIX = re.compile('^EFIX')
S_SAC = re.compile('^SSACC')
E_SAC = re.compile('^ESACC')
START = re.compile('^START')
END = re.compile('^END')
P_ID = re.compile('^.*p([0-9]{1,4})_Wald\.EDF.*$')

class Event(object):

	def __init__(self):
		self.lines = []

	def add_line(self, line):
		self.lines.append(line)


class Saccade(Event):

	def __init__(self):
		super(Saccade, self).__init__()
		self.start = None
		self.end = None
		self.start_x = None
		self.start_y = None
		self.end_x = None
		self.end_y = None
		self.dva = None
		self.duration = None
		self.messages = []

	def parse(self):
		for l in self.lines:
			data = l.split("\t")
			if data[0] == "MSG":
				msg = data[1].split(" ")
				self.messages.append([int(msg[0]), " ".join(data[1:])])
		data = self.lines[-1].split("\t")
		self.start = int(data[1])
		self.end = int(data[2])
		self.duration = int(data[3])
		self.start_x = float(data[4])
		self.start_y = float(data[5])
		self.end_x = float(data[6])
		self.end_y = float(data[7])
		self.dva = float(data[8])


class Fixation(Event):
	def __init__(self):
		super(Fixation, self).__init__()
		self.start = None
		self.end = None
		self.avg_x = None
		self.avg_y = None
		self.duration = None
		self.messages = []

	def parse(self):
		x_locs = []
		y_locs = []
		for l in self.lines:
			data = l.split("\t")
			if data[0] == "MSG":
				msg = data[1].split(" ")
				self.messages.append([int(msg[0]), " ".join(msg[1:])])
				# if msg[1] == "TRIAL_START\n":
				# 	self.start = int(msg[0])
				continue
			if not re.match('^[0-9]{1,10}.*', l):  # catches everything that's not eye activity or msg inside an event
				continue
			if l == self.lines[1]:
				self.start = int(data[0])
			if l == self.lines[-1]:
				self.end = int(data[0])
			x_locs.append(float(data[1]))
			y_locs.append(float(data[2]))
		try:
			self.avg_x = int( sum(x_locs) / len(x_locs) )
		except ZeroDivisionError:
			print self.lines
		self.avg_y = int( sum(y_locs) / len(y_locs) )
		self.duration = self.end - self.start

	def report(self, return_str=False):
		r_str = "Start: {0}, End: {1}, AvgX: {2}, AvgY:{3}, Duration: {4}".format(self.start, self.end, self.avg_x, self.avg_y, self.duration)
		if return_str:
			return r_str
		else:
			print r_str


class Trial(Event):

	def __init__(self):
		super(Trial, self).__init__()
		self.saccades = []
		self.fixations = []
		self.db_row = None

	def __event_id(self, event_type):
		index = len(self.fixations) if event_type == FIX else len(self.saccades)
		return "{0}_{1}".format(event_type, index)

	def add_event(self, event, event_type):
		if event_type == FIX:
			self.fixations.append(event)
		else:
			self.saccades.append(event)

	def parse(self):
		e = None
		e_type = None
		for l in self.lines:
			if not e:
				if S_FIX.match(l):
					e = Fixation()
					e_type = FIX
					continue
				if S_SAC.match(l):
					e = Saccade()
					e_type = SAC
					continue
			else:
				if E_FIX.match(l) or E_SAC.match(l):
					self.add_event(e, e_type)
					e = None
					e_type = None
					continue
				e.add_line(l)
		for f in self.fixations:
			e = f.parse()
			if e:
				print "Error! {0}, {1}".format(self.fixations.index(f), e)

	def report(self, return_str=False):
		r_str = "Saccades: {0}, Fixations:{1}".format(len(self.saccades), len(self.fixations))
		if return_str:
			return r_str
		else:
			print r_str

	def data_row(self, row):
		self.db_row = row


class Participant(object):

	def __init__(self, edf_path):
		self.import_max = 3
		self.id = None
		self.trials = []
		self.invalid_trials = []
		self.edf_path = edf_path
		self.__import_edf()
		self.parse_trials()
		self.current_trial_index = -1

	def __import_edf(self):
		t = None
		id = None
		for l in open(self.edf_path).readlines():
			if self.import_max == 0:
				break
			if P_ID.match(l) is not None:
				id = P_ID.match(l).group(1)
			if START.match(l) is not None:
				t = Trial()
				continue
			if END.match(l) is not None:
				self.add_trial(t)
				t = None
				continue
			if t:
				t.add_line(l)
			self.import_max -+ 1
		self.id = id

	def add_trial(self, trial):
		self.trials.append(trial)

	def parse_trials(self):
		for tr in self.trials:
			tr.parse()

	def next_trial(self):
		self.current_trial_index += 1
		try:
			return self.current_trial
		except IndexError:
			return False

	def delete_trial(self, trial):
		self.invalid_trials.append(trial)

	@property
	def current_trial(self):
		return self.trials[self.current_trial_index]

	@property
	def trial_count(self):
		return len(self.trials)


class ExperimentData(object):

	def __init__(self, data_dir_path):
		self.data_dir_path = data_dir_path
		self.participants = []
		self.import_data()

	def import_data(self):
		for f in listdir(self.data_dir_path)[1:]:
			f_path = join(self.data_dir_path, f)
			self.participants.append(Participant(f_path))

	def report(self):
		for p in self.participants:
			print "P{0} Trials: {1}".format(self.participants.index(p), p.trial_count)
			valid_trials = 0
			for t in p.trials:
				if not t in p.invalid_trials:
					valid_trials += 1
					print "\t[{0}]T{1}: {2}".format(valid_trials, p.trials.index(t), t.report(True))




def inspect_trial(id, edf_trial, trial_data, threshold):
	query = "SELECT * FROM `trial_locations` WHERE `participant_id` = {0} AND `trial_num` = {1}".format(id, trial_data[3])
	locs = cursor.execute(query).fetchall()
	all_matched = True
	for l in locs:
		d_x =  l[5]
		d_y =  l[6]
		dx_lower = d_x - threshold
		dx_upper = d_x + threshold
		dy_lower = d_y - threshold
		dy_upper = d_y + threshold
		matched_loc = False
		for f in edf_trial.fixations:
			t_x = f.avg_x
			t_y = f.avg_y
			if t_x in range(dx_lower, dx_upper) and t_y in range(dy_lower, dy_upper):
				matched_loc = True
		if not matched_loc:
			all_matched = False
	return all_matched


exp_dat = ExperimentData("/KLAB/2015-2016/Projects/ColinDataRecovery/ExpAssets/EDF/Test")

db_path = "/KLAB/2015-2016/Projects/ColinDataRecovery/ExpAssets/WaldoReplication.db"
db = sqlite3.connect(db_path)
cursor = db.cursor()


thresh = 150
failed = []
f_str = "Trial{0} ({1}): d_xy: ({2}, {3}) t_xy: ({4},{5}), d_xrng: ({6}:{7}), d_yrng: ({8}:{9})"
for p in exp_dat.participants:
	result = cursor.execute("SELECT * FROM `trials` WHERE `participant_id` = {0}".format(p.id)).fetchall()
	for r in result:
		matched = False
		trial = None
		while not matched:
			failed_trial = False
			if not trial:
				trial = p.next_trial()
				if not trial:
					break
			if not failed_trial:
				if not inspect_trial(p.id, trial, r, thresh):
					failed_trial = True
			if failed_trial:
				p.delete_trial(trial)
				trial = None
				matched = False
			else:
				trial = None
				matched = True
	# for f in failed:
	# 	print f
	# print "Failed: {0} of {1}".format(len(failed), len(exp_dat.participants[0].trials))
for p in exp_dat.participants:
	print len(p.trials) - len(p.invalid_trials)
