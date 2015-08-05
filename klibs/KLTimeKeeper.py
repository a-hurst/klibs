__author__ = 'jono'
import time

class TimeKeeper(object):
	moments = {}
	periods = {}


	def __init__(self, *args, **kwargs):
		super(TimeKeeper, self).__init__(*args, **kwargs)
		self.log("Instantiated")

	def log(self, label, time_value=None):
		self.moments[label] = time_value if time_value else time.time()

	def start(self, label, time_value=None):
		self.periods[label] = [time_value if time_value else time.time(), None]

	def end(self, label, time_value=None):
		self.periods[label][1] = time_value if time_value else time.time()

	def period(self, label):
		return self.periods[label][1] - self.periods[label][0]

	def read(self, label):
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
				time.append(None)
			output.append( "{0}: Start = {1}, End = {2}, Duration = {3}".format(*times))
		return output.join("\n")

