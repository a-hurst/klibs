# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

from klibs import PYLINK_AVAILABLE

if PYLINK_AVAILABLE:

	from pylink import (EyeLinkCustomDisplay, KeyInput, DC_TARG_BEEP, CAL_TARG_BEEP,
		CAL_ERR_BEEP, DC_ERR_BEEP, ENTER_KEY, ESC_KEY)

	from sdl2 import SDL_KEYDOWN, SDLK_ESCAPE, SDLK_RETURN, SDLK_c, SDLK_v
	from numpy import asarray
	from PIL import Image

	from klibs.KLEnvironment import EnvAgent
	from klibs import P
	from klibs.KLUtilities import pump, mouse_pos
	from klibs.KLUserInterface import ui_request
	from klibs.KLGraphics import fill, flip, blit
	from klibs.KLGraphics.KLDraw import drift_correct_target
	from klibs.KLAudio import AudioClip  # just a simple class for playing sdl2 sounds we made

	class ELCustomDisplay(EyeLinkCustomDisplay, EnvAgent):

		def __init__(self):
			EnvAgent.__init__(self)
			self.size = (0,0)
			self.raw_size = (0,0)
			self.imagebuffer = []
			self.palette = None

			EyeLinkCustomDisplay.__init__(self)

			try:
				self.__target_beep__ = AudioClip("target_beep.wav")
				self.__target_beep__done__ = AudioClip("target_beep_done.wav")
				self.__target_beep__error__ = AudioClip("target_beep_error.wav")
			except:
				self.__target_beep__ = None
				self.__target_beep__done__ = None
				self.__target_beep__error__ = None

		def record_abort_hide(self):
			pass

		def clear_cal_display(self):
			fill()
			flip()
			fill()

		def setup_cal_display(self):
			self.clear_cal_display()

		def exit_cal_display(self):
			self.clear_cal_display()

		def draw_cal_target(self, x, y=None, pump_events=True):
			fill()
			if pump_events: pump()
			if y is None:
				y = x[1]
				x = x[0]
			blit(drift_correct_target(), 5, (int(x), int(y)))
			flip()

		def erase_cal_target(self):
			self.clear_cal_display()

		def play_beep(self, clip):
			try:
				if clip == DC_TARG_BEEP or clip == CAL_TARG_BEEP:
					self.__target_beep__.play()
				elif clip == CAL_ERR_BEEP or clip == DC_ERR_BEEP:
					self.__target_beep__error__.play()
				else:
					self.__target_beep__done__.play()
			except:
				pass

		def get_input_key(self):
			for event in pump(True):
				if event.type == SDL_KEYDOWN:
					keysym = event.key.keysym
					keysym.sym = ENTER_KEY if keysym.sym == SDLK_RETURN else keysym.sym
					request = ui_request(keysym)
					if keysym.sym == SDLK_ESCAPE:  # don't allow escape to control tracker unless calibrating
						if self.el.in_setup():
							return [KeyInput(ESC_KEY, 0)]
						else:
							return 0
					if request:
						if request == SDLK_c and not self.el.in_setup():
							return [KeyInput(SDLK_ESCAPE, 0)]
					return [KeyInput(keysym.sym, keysym.mod)]

		def get_mouse_state(self):
			return mouse_pos()

		def alert_printf(self, message):
			message(message, color=(255, 0, 0, 255),
									location=(0.05 * P.screen_x, 0.05 * P.screen_y))

		def setup_image_display(self, width, height):
			self.size = (width, height)
			self.clear_cal_display()

		def exit_image_display(self):
			self.clear_cal_display()

		def image_title(self, text):
			pass

		def set_image_palette(self, r, g, b):
			'''
			Sets the palette to use for the camera image and clears the image buffer.
			Converts r,g,b (lists containing the RGB palette) to a list of colours
			([R,G,B,R,G,B,...]) that can be used by PIL.Image.
			'''
			self.imagebuffer = []
			self.palette = list(sum(zip(r,g,b), ()))

		def draw_image_line(self, width, line, totlines, buff):
			if self.raw_size != (width, totlines):
				self.raw_size = (width, totlines)
			self.imagebuffer += buff
			if int(line) == int(totlines):
				fill()
				img = Image.new("P", self.raw_size, 0)
				img.putpalette(self.palette)
				img.putdata(self.imagebuffer)
				blit(asarray(img.convert('RGBA').resize(self.size)), 5, position=P.screen_c)
				flip()
				self.imagebuffer = []

		def draw_lozenge(self, x, y, width, height, colorindex):
			pass

		def draw_line(self, x1, y1, x2, y2, colorindex):
			# maybe use opengl quads instead for simplicity?
			pass
