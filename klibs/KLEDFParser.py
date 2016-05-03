__author__ = 'jono'

from os import listdir
from os.path import isfile, join
import re
import sqlite3
import time
from klibs.KLConstants import *

# todo: this whole thing is a rudimentary start on what might later be required; mostly this is one-off script
# that was written with massive extension in mind without having actually *done* said extension

FIX = 'fixation'
SAC = 'saccade'
S_FIX = re.compile('^SFIX')
E_FIX = re.compile('^EFIX')
S_SAC = re.compile('^SSACC')
E_SAC = re.compile('^ESACC')
START = re.compile('^START')
START_TIME = re.compile('^START\t([0-9]{1,}).*')
END = re.compile('^END')
END_TIME = re.compile('^END\t([0-9]{1,}).*')
P_ID = re.compile('^.*p([0-9]{1,4})_Wald\.EDF.*$')

db_path = "/KLAB/2015-2016/Projects/ColinDataRecovery/ExpAssets/WaldoReplication.db"
edf_path = "/KLAB/2015-2016/Projects/ColinDataRecovery/ExpAssets/EDF/Test"
db = sqlite3.connect(db_path)
cursor = db.cursor()
tolerance = 150

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
		self.valid = True

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
		self.valid = False

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

	def __init__(self, start_time):
		super(Trial, self).__init__()
		self.saccades = []
		self.fixations = []
		self.db_row = None
		self.valid = True
		self.locations = None
		self.__start = None
		self.__end = None
		self.duration = None
		self.start = start_time

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

	def valid_fixations(self):
		v = []
		for f in self.fixations:
			if f.valid:
				v.append(f)
		return v

	@property
	def end(self):
		return self.__end

	@end.setter
	def end(self, end_time):
		self.__end = int(end_time)
		self.duration = self.__end - self.start

	@property
	def start(self):
		return self.__start

	@start.setter
	def start(self, start_time):
		self.__start = int(start_time)



class Participant(object):

	def __init__(self, edf_path):
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
			if P_ID.match(l) is not None:
				id = P_ID.match(l).group(1)
			if START.match(l) is not None:
				t = Trial(START_TIME.match(l).group(1))
				continue
			if END.match(l) is not None:
				t.end = END_TIME.match(l).group(1)
				self.add_trial(t)
				t = None
				continue
			if t:
				t.add_line(l)
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

	def valid_trials(self):
		v = []
		for t in self.trials:
			if t.valid:
				v.append(t)
		return v

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
		self.import_max = 2
		self.data_dir_path = data_dir_path
		self.participants = []
		self.import_data()

	def import_data(self):
		for f in listdir(self.data_dir_path)[1:]:
			if f[-3:] != "asc":
				continue
			if self.import_max == 0:
				break
			self.participants.append(Participant(join(self.data_dir_path, f)))
			self.import_max -= 1

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
	locations = cursor.execute(query).fetchall()

	all_matched = True
	valid = []
	for l in locations:
		d_x =  l[5]
		d_y =  l[6]
		dx_lower = d_x - threshold
		dx_upper = d_x + threshold
		dy_lower = d_y - threshold
		dy_upper = d_y + threshold
		matched_loc = False
		for f in edf_trial.fixations:
			# if f.valid:
			# 	continue
			t_x = f.avg_x
			t_y = f.avg_y
			if t_x in range(dx_lower, dx_upper) and t_y in range(dy_lower, dy_upper):
				if f in valid:
					f.invalid = True
					continue
				valid.append(f)
				f.valid = True
				matched_loc = True
				break
		if not matched_loc:
			all_matched = False
	# if len(locations) != len(valid) and r[7] == "FALSE":
	# 	print "Locs: {0}, VFix: {1}, {2}".format(len(locations), len(valid), r[7] == "TRUE")

	return [ all_matched, locations]
	# return all_matched


start = time.time()
exp_dat = ExperimentData(edf_path)
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
				inspection = inspect_trial(p.id, trial, r, tolerance)
				failed_trial = not inspection[0]
				if inspection[0]:
					trial.db_row = [i for i in r]
					trial.locations = inspection[1]
					if r[7] == 'TRUE':
						trial.valid = False
				else:
					trial.valid = False
					failed_trial = True
			if failed_trial:
				p.delete_trial(trial)
				trial = None
				matched = False
			else:
				trial = None
				matched = True
for p in exp_dat.participants:
	for t in p.trials:
		if not t.valid:
			continue
		valid_count = 0
		for f in t.fixations:
			valid_count += 1 if f.valid else 0
		if len(t.locations) != valid_count:
			t.valid = False
	v_trials = [t.valid for t in p.trials]

	print "Trials:{0}, VTrials: {3}, InvTrials: {1}, Diff:{2}".format(len(p.trials), len(p.invalid_trials), len(p.trials) - len(p.invalid_trials), len(v_trials))

def infer_rt(trial):
	pre_rt = 0
	last_f = None
	vf = trial.valid_fixations()
	for f in vf:
		if last_f is None:
			last_f = f
			continue
		if vf.index(f) > 2:
			diff = (f.start - last_f.end) - 500
			pre_rt += diff if diff > 0 else 0
		last_f = f
	# pre_rt += 500 * (len(vf) - 1)
	min_l_time = 700 + pre_rt + (len(trial.locations) * 500)
	print "Duration: {0}, Locations: {1}, MinLTime: {2}, LFix: {4}, Diff:{3}".format(trial.duration, len(trial.locations), min_l_time, trial.duration - min_l_time, pre_rt)
#	print vf[-1].start - (vf[0].start + pre_rt)

for t in exp_dat.participants[1].trials:
	if t.valid:
		infer_rt(t)





print time.time() - start