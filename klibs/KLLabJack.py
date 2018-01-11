__author__ = 'jono'

import warnings
from klibs import P

try:
	with warnings.catch_warnings():
		warnings.simplefilter("ignore")
		import u3
		warnings.simplefilter("default")
except ImportError:
	P.labjack_available = False
	if P.labjacking:
		print(
			"\n\033[91m\t - Unable to import LabJack library, 'u3'. "
			"Fix installation or install from here: "
			"https://labjack.com/support/software/examples/ud/labjackpython \033[0m"
		)


class LabJack(object):
	labjack = None
	messages = {}

	def __init__(self):
		if P.labjacking and P.labjack_available:
			self.labjack = u3.U3()
			self.labjack.configU3()
			self.labjack.getFeedback(u3.LED(State=False))

	def shut_down(self):
		self.labjack.getFeedback(u3.PortStateWrite(State=[0, 0, 0]))
		self.labjack.close()

	def add_messages(self, labels, values):
		if type(labels) is str:
			labels = [labels]
		if type(values) is int:
			values = [values]

		for i in range(0, len(labels)):
			try:
				self.messages[labels[i]] = values[i]
			except IndexError:
				raise IndexError("Number of labels and values must be equal.")

	def write(self, state):
		self.labjack.getFeedback(u3.PortStateWrite([state, 0, 0]))

	def read(self, state):
		self.labjack.getFeedback(u3.PortStateRead([state, 0, 0]))
