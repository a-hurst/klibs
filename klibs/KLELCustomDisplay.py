# -*- coding: utf-8 -*-
__author__ = 'jono'
import pylink

#  these are all from our framework but shouldn't be the source of any interference here
from KLAudioClip import AudioClip  # just a simple class for playing sdl2 sounds we made
from KLNumpySurface import *  # a class for easily moving between numpy pixel arrays and sdl2/openGL
import KLParams as Params  # a list of program-wide settings like screen dimensions, colors, etc.
import KLDraw

class ELCustomDisplay(pylink.EyeLinkCustomDisplay):

	window = None
	experiment = None
	tracker = None
	size = [None, None]

	def __init__(self, experiment, tracker):
		self.experiment = experiment  # a reference to the instance of the "experiment class" where most of the
		self.size = self.experiment.window.size
		self.tracker = tracker

		pylink.EyeLinkCustomDisplay.__init__(self)

		try:
			self.__target_beep__ = AudioClip("target_beep.wav")
			self.__target_beep__done__ = AudioClip("target_beep_done.wav")
			self.__target_beep__error__ = AudioClip("target_beep_error.wav")
		except:
			self.__target_beep__ = None
			self.__target_beep__done__ = None
			self.__target_beep__error__ = None

	def setup_cal_display(self):
		self.window = self.experiment.window
		self.clear_cal_display()

	def exit_cal_display(self):
		pass

	def record_abort_hide(self):
		pass

	def clear_cal_display(self):
		self.experiment.fill()
		self.experiment.flip()

	def erase_cal_target(self):
		self.clear_cal_display()

	def draw_cal_target(self, x, y=None, pump_events=True, flip=True):
		if pump_events: sdl2.SDL_PumpEvents()
		if y is None:
			y = x[1]
			x = x[0]
		self.experiment.blit(KLDraw.drift_correct_target(), 5, [int(x), int(y)])
		if flip: self.experiment.flip()

	def play_beep(self, clip):
		if clip == pylink.DC_TARG_BEEP or clip == pylink.CAL_TARG_BEEP:
			self.__target_beep__.play()
		elif clip == pylink.CAL_ERR_BEEP or clip == pylink.DC_ERR_BEEP:
			self.__target_beep__error__.play()
		else:
			self.__target_beep__done__.play()

	def get_input_key(self):
		tracker_mode = self.tracker.getTrackerMode()
		sdl2.SDL_PumpEvents()
		for event in sdl2.ext.get_events():
			if event.type == sdl2.SDL_KEYDOWN:
				keysym = event.key.keysym
				ui_request = self.experiment.ui_request(keysym)
				if keysym.sym == sdl2.SDLK_ESCAPE:  # don't allow escape to control tracker unless calibrating
					if tracker_mode in [pylink.EL_VALIDATE_MODE, pylink.EL_CALIBRATE_MODE]:
						return [pylink.KeyInput(sdl2.SDLK_ESCAPE, 0)]
					else:
						return False
				if ui_request:
					if ui_request == sdl2.SDLK_c and tracker_mode == pylink.EL_DRIFT_CORR_MODE:  # cmd+c returns to setup
						return [pylink.KeyInput(sdl2.SDLK_ESCAPE, 0)]
				return [pylink.KeyInput(keysym.sym, keysym.mod)]

	def get_mouse_state(self):
		return mouse_pos()

	def exit_image_display(self):
		self.clear_cal_display()

	def alert_printf(self, message):
		self.experiment.message(message, color=(255, 0, 0, 0), location=(0.05 * Params.screen_x, 0.05 * Params.screen_y))

	def setup_image_display(self, width, height):
		self.img_size = (width, height)

	def image_title(self, text):
		pass

	def draw_image_line(self, width, line, totlines, buff):
		# todo make this shizit work son
		try:
			for i in range(0, len(buff)):
				if type(buff[i]) is int:
					buff[i] = 3*[buff[i]]
			surf = NumpySurface(numpy.array(buff))
			self.experiment.blit(surf, location=[0, line], context=self.window)
		except:
			pass

	def draw_lozenge(self, x, y, width, height, colorindex):
		pass

	def draw_line(self, x1, y1, x2, y2, colorindex):
		pass

	def set_image_palette(self, r, g, b):
		pass
