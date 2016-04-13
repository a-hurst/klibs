# -*- coding: utf-8 -*-
from klibs import KLDraw

__author__ = 'jono'
import pylink

#  these are all from our framework but shouldn't be the source of any interference here
from klibs.KLAudio import AudioClip  # just a simple class for playing sdl2 sounds we made
from klibs.KLNumpySurface import *  # a class for easily moving between numpy pixel arrays and sdl2/openGL
import array
import sys

class ELCustomDisplay(pylink.EyeLinkCustomDisplay):

	window = None
	experiment = None
	tracker = None
	size = [None, None]

	def __init__(self, experiment, tracker):
		self.experiment = experiment  # a reference to the instance of the "experiment class" where most of the
		self.size = self.experiment.window.size
		self.tracker = tracker
		self.last_flip = None
		self.fill_color = [255,0,0]
		if sys.byteorder == 'little':
			self.byteorder = 1
		else:
			self.byteorder = 0
		self.imagebuffer = array.array('I')
		self.pal = None
		self.__img__ = None


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
		try:
			if clip == pylink.DC_TARG_BEEP or clip == pylink.CAL_TARG_BEEP:
				self.__target_beep__.play()
			elif clip == pylink.CAL_ERR_BEEP or clip == pylink.DC_ERR_BEEP:
				self.__target_beep__error__.play()
			else:
				self.__target_beep__done__.play()
		except:
			pass

	def get_input_key(self):
		sdl2.SDL_PumpEvents()
		for event in sdl2.ext.get_events():
			if event.type == sdl2.SDL_KEYDOWN:
				keysym = event.key.keysym
				keysym.sym = pylink.ENTER_KEY if keysym.sym == sdl2.SDLK_RETURN else keysym.sym
				ui_request = self.experiment.ui_request(keysym)
				if keysym.sym == sdl2.SDLK_ESCAPE:  # don't allow escape to control tracker unless calibrating
					if self.tracker.in_setup():
						return [pylink.KeyInput(pylink.ESC_KEY, 0)]
					else:
						return 0
				if ui_request:
					if ui_request == sdl2.SDLK_c and not self.tracker.in_setup():
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
		i = 0
		while i < width:
			if buff[i]>=len(self.pal):
				buff[i] = len(self.pal)-1
			self.imagebuffer.append(self.pal[buff[i]&0x000000FF])
			i += 1
		try:
			img = Image.frombytes('RGBX', (width,totlines), self.imagebuffer.tostring())
			img = img.convert('RGBA')
			self.experiment.blit(NumpySurface(numpy.asarray(img)), position=Params.screen_c, registration=5)
			self.experiment.flip()
			self.imagebuffer = array.array('I')
		except:
			pass
		return

	def draw_lozenge(self, x, y, width, height, colorindex):
		pass

	def draw_line(self, x1, y1, x2, y2, colorindex):
		try:
			print "Draw Line: {0}".format(x1, x2,y1,y2, colorindex)
			line = Image.Draw("RGBA",[x2 - x1, y2 - y1])
			p = Image.Pen((255,255,255), 2)
			line.line((0, 0, x2, y2), p)
			self.experiment.blit(from_aggdraw_context(line), position=Params.screen_c, registration=5)
		except:
			pass

	def set_image_palette(self, r, g, b):
		self.imagebuffer = array.array('I')
		sz = len(r)
		i = 0
		self.pal = []
		while i < sz:
			rf = int(b[i])
			gf = int(g[i])
			bf = int(r[i])
			if self.byteorder:
				self.pal.append((rf<<16) | (gf<<8) | (bf))
			else:
				self.pal.append((bf<<24) |  (gf<<16) | (rf<<8)) #for mac
			i +=1
