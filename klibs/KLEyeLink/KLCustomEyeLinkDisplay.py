# -*- coding: utf-8 -*-
__author__ = 'j. mulle & austin hurst'

from klibs import PYLINK_AVAILABLE

if PYLINK_AVAILABLE:

	import pylink
	import sdl2

	from numpy import asarray
	from PIL import Image
	from aggdraw import Draw, Brush, Pen
	
	from klibs.KLEnvironment import EnvAgent
	from klibs import P
	from klibs.KLUtilities import pump, mouse_pos
	from klibs.KLUserInterface import ui_request
	from klibs.KLGraphics import fill, flip, blit
	from klibs.KLGraphics.KLDraw import drift_correct_target
	from klibs.KLCommunication import message  # Too slow to use here yet
	from klibs.KLAudio import AudioClip  # just a simple class for playing sdl2 sounds we made

	class ELCustomDisplay(pylink.EyeLinkCustomDisplay, EnvAgent):

		#TODO: add scaling support for images without ruining performance (OpenGL scale?)
		#TODO: test fix for get_mouse_state
		#TODO: reimplement draw_lozenge so it matches their weird specifications

		def __init__(self):
			EnvAgent.__init__(self)
			self.size = (0,0)
			self.imagebuffer = []
			self.palette = []
			self.img = None # PIL.Image
			self.drawer = None # aggdraw Draw with self.img as context
			self.title = None

			self.dc_target = drift_correct_target()

			pylink.EyeLinkCustomDisplay.__init__(self)

			# Define dict mapping sdl2 keycodes to pylink keycodes
			self.pylink_keycodes = dict([
				(sdl2.SDLK_F1, pylink.F1_KEY),
				(sdl2.SDLK_F2, pylink.F2_KEY),
				(sdl2.SDLK_F3, pylink.F3_KEY),
				(sdl2.SDLK_F4, pylink.F4_KEY),
				(sdl2.SDLK_F5, pylink.F5_KEY),
				(sdl2.SDLK_F6, pylink.F6_KEY),
				(sdl2.SDLK_F7, pylink.F7_KEY),
				(sdl2.SDLK_F8, pylink.F8_KEY),
				(sdl2.SDLK_F9, pylink.F9_KEY),
				(sdl2.SDLK_F10, pylink.F10_KEY),
				(sdl2.SDLK_PAGEUP, pylink.PAGE_UP),
				(sdl2.SDLK_PAGEDOWN, pylink.PAGE_DOWN),
				(sdl2.SDLK_UP, pylink.CURS_UP),
				(sdl2.SDLK_DOWN, pylink.CURS_DOWN),
				(sdl2.SDLK_LEFT, pylink.CURS_LEFT),
				(sdl2.SDLK_RIGHT, pylink.CURS_RIGHT),
				(sdl2.SDLK_RETURN, pylink.ENTER_KEY),
				(sdl2.SDLK_ESCAPE, pylink.ESC_KEY),
				(sdl2.SDLK_BACKSPACE, ord('\b')),
				(sdl2.SDLK_TAB, ord('\t'))
			])

			# Define dict mapping pylink colour constants to RGB colours
			self.pylink_colors = [
				(0, 0, 0), 			# 0 = placeholder (transparent)
				(255, 255, 255),	# 1 = pylink.CR_HAIR_COLOR (white)        
				(255, 255, 255),	# 2 = pylink.PUPIL_HAIR_COLOR (white)
				(0, 255, 0),		# 3 = pylink.PUPIL_BOX_COLOR (green)
				(255, 0, 0),		# 4 = pylink.SEARCH_LIMIT_BOX_COLOR (red)
				(255, 0, 0)			# 5 = pylink.MOUSE_CURSOR_COLOR (red)
			]

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
			blit(self.dc_target, 5, (int(x), int(y)))
			flip()

		def erase_cal_target(self):
			self.clear_cal_display()

		def play_beep(self, clip):
			try:
				if clip in [pylink.DC_TARG_BEEP, pylink.CAL_TARG_BEEP]:
					self.__target_beep__.play()
				elif clip in [pylink.CAL_ERR_BEEP, pylink.DC_ERR_BEEP]:
					self.__target_beep__error__.play()
				else:
					self.__target_beep__done__.play()
			except:
				pass

		def get_input_key(self):
			keys = []
			for event in pump(True):
				if event.type == sdl2.SDL_KEYDOWN:
					keysym = event.key.keysym
					ui_request(keysym)
					try:
						key = self.pylink_keycodes[keysym.sym]
					except KeyError:
						key = keysym.sym
					# don't allow escape to control tracker unless calibrating
					if key == pylink.ESC_KEY and not self.el.in_setup():  
						key = pylink.JUNK_KEY
					keys.append(pylink.KeyInput(key, keysym.mod))
			return keys

		def get_mouse_state(self):
			x, y, b = mouse_pos(pump_event_queue=False, return_button_state=True)
			if b != 1: # Register left clicks only
				b = 0
			return ((int(x), int(y)), b)

		def alert_printf(self, message):
			# Commented out until message() is fast enough to not cause problems
			# or better way of rendering text here is devised.
			#
			#message(message, color=(255, 0, 0, 255),
			#						location=(0.05 * P.screen_x, 0.05 * P.screen_y))
			print "EyeLink Alert: {0}".format(message)

		def setup_image_display(self, width, height):
			'''Sets camera image to the provided size, returns 1 on success.'''
			self.size = (width, height)
			self.clear_cal_display()
			return 1

		def exit_image_display(self):
			self.clear_cal_display()

		def image_title(self, text):
			#TODO: add text style w/ font size that fits image
			self.title = message(text, blit_txt=False)

		def set_image_palette(self, r, g, b):
			'''
			Sets the palette to use for the camera image and clears the image buffer.
			Converts r,g,b (lists containing the RGB palette) to a list of colours
			([R,G,B,R,G,B,...]) that can be used by PIL.Image.
			'''
			self.imagebuffer = []
			self.palette = list(sum(zip(r,g,b), ()))

		def draw_image_line(self, width, line, totlines, buff):
			'''
			Reads in the buffer from the EyeLink camera image line by line and writes it
			into a buffer of size (width * totlines). Once the last line of the image
			has been read into the buffer, the image buffer is placed in a PIL.Image
			with the palette set by set_image_palette, converted to RGBA, resized,
			and then rendered to the middle of the screen. After rendering, the image
			buffer is cleared.
			'''
			if len(self.imagebuffer) > (width*totlines):
				self.imagebuffer = []
			self.imagebuffer += buff
			if int(line) == int(totlines):
				# Render complete camera image and resize to self.size
				img = Image.new("P", (width, totlines), 0)
				img.putpalette(self.palette)
				img.putdata(self.imagebuffer)
				self.img = img.convert('RGBA').resize(self.size)
				# Set up aggdraw to draw crosshair/bounds/etc. on image surface
				self.drawer = Draw(self.img)
				self.drawer.setantialias(True)
				self.draw_cross_hair()
				self.drawer.flush()
				# Draw complete image to screen
				fill()
				blit(asarray(self.img), 5, P.screen_c)
				if self.title:
					loc_x = (P.screen_c[0])
					loc_y = (P.screen_c[1] + self.size[1]/2 + 20)
					blit(self.title, 8, (loc_x, loc_y))
				flip()
				# Clear image buffer
				self.imagebuffer = []

		def draw_lozenge(self, x, y, width, height, colorindex):
			lozenge_pen = Pen(self.pylink_colors[colorindex], 3, 255)
			self.drawer.ellipse((x, y, width, height), lozenge_pen)

		def draw_line(self, x1, y1, x2, y2, colorindex):
			line_pen = Pen(self.pylink_colors[colorindex], 3, 255)
			self.drawer.line((x1, y1, x2, y2), line_pen)
