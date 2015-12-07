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
				# h = sum([l.height for l in content])
				panel = Rectangle(Params.screen_x, content.shape[0], fill=[0,0,0,125]).render()
				panel.foreground = panel.foreground.astype(numpy.uint8)
				# panel.blit(content, position=[Params.screen_c[0], panel.height // 2], registration=5)
				self.experiment.blit(panel, position=[0,Params.screen_y], registration=1)
				# self.experiment.blit(content, position=[Params.screen_c[0],Params.screen_y], registration=2)
				self.experiment.blit(content, position=[Params.screen_c[0], Params.screen_y], registration=2)
				# lines = 0
				# for l in content:
				# 	height = Params.screen_y - (h - (l.height * lines))
				# 	lines += 1
				# 	self.experiment.blit(l, position=[Params.screen_c[0], height], registration=8)






