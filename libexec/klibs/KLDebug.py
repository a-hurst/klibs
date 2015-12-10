__author__ = 'jono'
import time
from libexec.klibs.KLDraw import *

class Debugger(object):
	experiment = None
	logs = []
	labelled_logs = {}
	display_location = "RIGHT"

	def __init__(self, experiment):
		self.experiment = experiment

	def log(self, value, message=None, label=None, display_print=True, cli_print=True):
		entry = [value, time.time(), message, display_print, cli_print]
		if label:
			self.labelled_logs[label] = entry
		else:
			self.logs.append(entry)

	def print_logs(self, display=True, cli=True, time_format=None):
		display_lines = []
		for l in self.logs:
			line = "{0}: {1} {2}".format(l[1], l[0], "({0})".format(l[2]) if l[2] else l[2])
			if l[3]:
				display_lines.append(line)
			if l[4] and cli:
				print line
		for l in self.labelled_logs:
			e = self.labelled_logs[l]
			line = "{0} [{1}]: {2} {3}".format(l, e[1], e[0], "({0})".format(e[2]) if e[2] else e[2])
			if e[3]:
				display_lines.append(line)
			if e[4] and cli:
				print line
		if display:
			if len(display_lines):
				text = "\n".join(display_lines)
				content = self.experiment.text_manager.render(text, "debug")
				if self.display_location == "LEFT":
					panel_h = Params.screen_y
					panel_w = content.shape[1] + 10
					panel_position = (0,Params.screen_y)
					panel_registration = 3
					content_position = (5,5)
					content_registration = 7
				if self.display_location == "RIGHT":
					panel_h = Params.screen_y
					panel_w = content.shape[1] + 10
					panel_position = (Params.screen_x - panel_w, Params.screen_y)
					panel_registration = 1
					content_position = (Params.screen_x - 5, 5)
					content_registration = 9
				if self.display_location == "BOTTOM":
					panel_h = content.shape[0]
					panel_w = Params.screen_x
					content_position = (Params.screen_c[0], Params.screen_y)
					content_registration = 2
				panel = Rectangle(panel_w, panel_h, fill=[0,0,0,125]).render()
				self.experiment.blit(panel, position=panel_position, registration=panel_registration)
				self.experiment.blit(content, position=content_position, registration=content_registration)





