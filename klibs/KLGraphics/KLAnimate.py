__author__ = 'jono'

from time import time

from klibs.KLEnvironment import EnvAgent
from klibs.KLConstants import TK_MS, TK_S
from klibs.KLUtilities import colored_stdout as cso
from klibs.KLUtilities import smart_sleep
from klibs.KLGraphics import flip, blit
from klibs.KLUserInterface import ui_request

class Animation(EnvAgent):
	draw_time = None
	frame_interval = None
	units = None
	frame_draw_cb = None
	frame_draw_cb_args = None
	frame_data_cb = None
	frame_data_cb_args = None
	frames = None
	frame_count = None
	
	
	def __init__(self, frames=None, frame_draw_cb=None, draw_time=None, frame_count=None, frame_interval=None, anim_units=TK_MS, frame_draw_cb_args=None, frame_data_cb=None, frame_data_cb_args=None, use_trial_clock=True, flip_after_cb=False):
		if frames and frame_draw_cb:
			e_msg = "Either a list of frames of a frame drawing callback function may be provided, but not both."
			raise ValueError(e_msg)
		self.units = anim_units
		self.__set_frame_and_draw_times__(draw_time, frame_count, frame_interval)
		self.frame_interval = int(frame_interval) if anim_units == TK_MS else int(frame_interval * 1000)
		self.frame_draw_cb = frame_draw_cb
		self.frame_draw_cb_args = frame_draw_cb_args
		self.frame_data_cb = frame_data_cb
		self.frame_data_cb_args = frame_data_cb_args
		self.use_trial_clock = use_trial_clock
		self.flip_after_cb = flip_after_cb

	def __set_frame_and_draw_times__(self, draw_time, frame_count, frame_interval):
		if draw_time and frame_count:
			self.draw_time = int(draw_time) if self.units == TK_MS else float(draw_time)
			self.frame_count = frame_count
			if frame_interval:
				e_msg = "Supplied arguments do not agree; 'draw_time' divided by 'frame_count' does not equal supplied 'frame_interval'."
				if self.units == TK_MS and int(frame_interval) != int(draw_time / frame_count):
					raise ValueError(e_msg)
				elif frame_interval != draw_time / frame_count:
					raise ValueError(e_msg)
			else:
				if draw_time % frame_count:
					cso("\t<red>Warning: A klibs.KLAnimation object has a draw_time not evenly divisable by its frame_count.")
				self.frame_interval = int(draw_time / frame_count) if self.units == TK_MS else float(draw_time) / frame_count
		elif frame_count and frame_interval:
			self.frame_count = frame_count
			self.frame_interval = int(frame_interval) if self.units == TK_MS else float(frame_interval)
			self.draw_time = int(frame_count * frame_interval) if self.units == TK_MS else frame_count * float(frame_interval)
		elif draw_time and frame_interval:
			if draw_time % frame_interval:
				cso("\t<red>Warning: A klibs.KLAnimation object has a draw_time not evenly divisable by its frame_interval.")
			self.draw_time = int(draw_time) if self.units == TK_MS else float(draw_time)
			self.frame_interval = int(draw_time) if self.units == TK_MS else float(draw_time)
			self.frame_count = int (draw_time / frame_interval)
				

	def run(self):
		if self.use_trial_clock:
			start = self.evm.trial_time
			if self.units == TK_S:
				start *= 0.001
		else:
			start = time()
			if self.units == TK_MS:
				start = int(start * 1000)
		for i in range(0, self.frame_count):
			if self.frames:
				for f in self.frames:
					pass  # create a Frame class that knows how to blit itself after loading and rendering assets
			else:
				self.frame_draw_cb(*self.frame_draw_cb_args)
				if self.flip_after_cb:
					flip()
			frame_running = True
			while frame_running:
				try:
					self.frame_data_cb(self.frame_draw_cb_args)
				except TypeError:
					pass
				if self.use_trial_clock:
					elapsed = self.evm.trial_time
					if self.units == TK_S:
						elapsed *= 0.001
				else:
					elapsed = time()
					if self.units == TK_MS:
						elapsed = int(start * 1000)
				frame_running = elapsed < i * self.frame_interval
				ui_request()
