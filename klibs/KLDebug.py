__author__ = 'jono'
import time
from KLTextManager import *
from KLDraw import *

class Debugger(object):
	experiment = None
	logs = []
	labelled_logs = {}

	def __init__(self, experiment):
		self.experiment = experiment

	def log(self, value, message=None, label=None, display_print=True, cli_print=True):
		entry = [value, time.time(), message, display_print, cli_print]
		if label:
			self.labelled_logs[label] = entry
		else:
			self.logs.append(entry)

	def print_logs(self, display=True, cli=True, time_format=None):
		if display:
			display_lines = []
			for l in self.logs:
				line = "{0}: {1} {2}".format(l[1], l[0], "({0})".format(l[2]) if l[2] else l[2])
				if l[4]:
					print line
				if l[3]:
					display_lines.append(line)
			display_lines.append("\n")
			if len(display_lines):
				content = self.experiment.text_manager.render("\n".join(display_lines), "debug panel")
				panel = Rectangle(Params.screen_x, content.height, fill=[0,0,0,125])
				panel.blit(content, location=[Params.screen_c[0], panel.height // 2], registration=5)

		if cli:
			for l in self.labelled_logs:
				e = self.labelled_logs[l]
				line = "{0} [{1}]: {2} {3}".format(l, e[1], e[0], "({0})".format(e[2]) if e[2] else e[2])
				if e[4]:
					print line
				if e[3]:
					display_lines.append(line)





