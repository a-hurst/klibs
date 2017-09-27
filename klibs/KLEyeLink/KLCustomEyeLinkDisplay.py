# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import array
import sys
from klibs import PYLINK_AVAILABLE

if PYLINK_AVAILABLE:

	from pylink import (EyeLinkCustomDisplay, KeyInput, DC_TARG_BEEP, CAL_TARG_BEEP,
		CAL_ERR_BEEP, DC_ERR_BEEP, ENTER_KEY, ESC_KEY)

	from sdl2 import SDL_KEYDOWN, SDLK_ESCAPE, SDLK_RETURN, SDLK_c, SDLK_v
	from numpy import asarray
	from aggdraw import Draw, Pen
	from PIL.Image import frombytes

	from klibs.KLEnvironment import EnvAgent
	from klibs import P
	from klibs.KLUtilities import pump, mouse_pos
	from klibs.KLUserInterface import ui_request
	from klibs.KLGraphics import fill, flip, blit, aggdraw_to_array
	from klibs.KLGraphics.KLDraw import drift_correct_target
	from klibs.KLAudio import AudioClip  # just a simple class for playing sdl2 sounds we made

	class ELCustomDisplay(EyeLinkCustomDisplay, EnvAgent):

		def __init__(self):
			EnvAgent.__init__(self)
			self.size = (0,0)
			self.last_flip = None
			if sys.byteorder == 'little':
				self.byteorder = 1
			else:
				self.byteorder = 0
			self.imagebuffer = array.array('I')
			self.pal = None
			self.__img__ = None

			EyeLinkCustomDisplay.__init__(self)

			try:
				self.__target_beep__ = AudioClip("target_beep.wav")
				self.__target_beep__done__ = AudioClip("target_beep_done.wav")
				self.__target_beep__error__ = AudioClip("target_beep_error.wav")
			except:
				self.__target_beep__ = None
				self.__target_beep__done__ = None
				self.__target_beep__error__ = None

		def setup_cal_display(self):
			self.clear_cal_display()

		def exit_cal_display(self):
			self.clear_cal_display()

		def record_abort_hide(self):
			pass

		def clear_cal_display(self):
			fill()
			flip()
			fill()

		def erase_cal_target(self):
			self.clear_cal_display()

		def draw_cal_target(self, x, y=None, pump_events=True):
			fill()
			if pump_events: pump()
			if y is None:
				y = x[1]
				x = x[0]
			blit(drift_correct_target(), 5, (int(x), int(y))
			flip()

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

		def exit_image_display(self):
			self.clear_cal_display()

		def alert_printf(self, message):
			message(message, color=(255, 0, 0, 0),
									location=(0.05 * P.screen_x, 0.05 * P.screen_y))

		def setup_image_display(self, width, height):
			self.size = (width, height)
			self.clear_cal_display()

		def image_title(self, text):
			pass

		def draw_image_line(self, width, line, totlines, buff):
			i = 0
			while i < width:
				if buff[i] >= len(self.pal):
					buff[i] = len(self.pal) - 1
				self.imagebuffer.append(self.pal[buff[i] & 0x000000FF])
				i += 1
			if width == totlines:
				fill()
				img = frombytes('RGBX', (width, totlines), self.imagebuffer.tostring()).convert('RGBA')
				blit(img, registration=5, location=P.screen_c)
				flip()
				self.imagebuffer = array.array('I')

		def draw_lozenge(self, x, y, width, height, colorindex):
			pass

		def draw_line(self, x1, y1, x2, y2, colorindex):
			# maybe use opengl quads instead for simplicity?
			try:
				print "Draw Line: {0}".format(x1, x2, y1, y2, colorindex)
				line = Draw("RGBA", [x2 - x1, y2 - y1])
				p = Pen((255, 255, 255), 2)
				line.line((0, 0, x2, y2), p)
				blit(aggdraw_to_array(line), registration=5, location=P.screen_c)
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
					self.pal.append((rf << 16) | (gf << 8) | (bf))
				else:
					self.pal.append((bf << 24) | (gf << 16) | (rf << 8)) #for mac
				i += 1


