# -*- coding: utf-8 -*-
__author__ = 'j. mulle & austin hurst'

import pylink
import sdl2

from numpy import asarray
from PIL import Image
from aggdraw import Draw, Brush, Pen
from math import ceil, floor
	
from klibs.KLEnvironment import EnvAgent
from klibs.KLConstants import EYELINK_1000
from klibs import P
from klibs.KLUtilities import clip
from klibs.KLEventQueue import pump
from klibs.KLUserInterface import ui_request, mouse_pos
from klibs.KLGraphics import fill, flip, blit
from klibs.KLGraphics.KLDraw import drift_correct_target
from klibs.KLText import add_text_style
from klibs.KLCommunication import message
from klibs.KLAudio import AudioClip  # just a simple class for playing sdl2 sounds we made

# TODO: Add flexible image scaling support (tab to toggle size?)


class ELCustomDisplay(pylink.EyeLinkCustomDisplay, EnvAgent):
	"""An EyeLinkCustomDisplay implementation for KLibs.

	This class allows for interactive EyeLink camera setup and calibration in
	KLibs, and has been tested with EyeLink II and EyeLink 1000 trackers.

	"""
	def __init__(self):
		EnvAgent.__init__(self)
		self.__imgwidth__ = 0
		self.__imgheight__ = 0
		self._output_height = 480  # scaled output height for camera image
		self.imagebuffer = []
		self.palette = []
		self.img = None # PIL.Image
		self.drawer = None # aggdraw Draw with self.img as context
		self.title = None

		add_text_style("el_setup", "20px", font="Hind-Medium")
		self.dc_target = drift_correct_target()

		pylink.EyeLinkCustomDisplay.__init__(self)

		# If using an EyeLink 1000 or newer, these commands need to be sent
		# to the tracker for everything to work correctly
		if self.el.getTrackerVersion() >= EYELINK_1000:
			self.el.sendCommand("enable_search_limits=YES")
			self.el.sendCommand("track_search_limits=YES")
			self.el.sendCommand("autothreshold_click=YES")
			self.el.sendCommand("autothreshold_repeat=YES")
			self.el.sendCommand("enable_camera_position_detect=YES")

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

	def _scale_up(self, x, y):
		# Scales up coords from PyLink size to image size
		scale_factor = self._output_height / float(self.size[1])
		return (int(x * scale_factor), int(y * scale_factor))

	def _scale_down(self, x, y):
		# Scales down coords from image size to PyLink size
		scale_factor = self._output_height / float(self.size[1])
		return (int(x / scale_factor), int(y / scale_factor))

	def record_abort_hide(self):
		# Called if recording aborted on EyeLink? Not really worth implementing.
		pass

	def clear_cal_display(self):
		# Clears the calibration display and prepares for targets to be drawn.
		fill()
		flip()
		fill()

	def setup_cal_display(self):
		# Called immediately before calibration/validation
		self.clear_cal_display()

	def exit_cal_display(self):
		# Called after finishing or exiting calibration/validation
		self.clear_cal_display()

	def draw_cal_target(self, x, y=None, pump_events=True):
		# Draws a single calibration/validation target at a given location
		fill()
		if pump_events: pump()
		if y is None:
			y = x[1]
			x = x[0]
		blit(self.dc_target, 5, (int(x), int(y)))
		flip()

	def erase_cal_target(self):
		# Erases the target previously drawn by draw_cal_target.
		# NOTE: Should this be fill() instead, or do we need to redraw as well?
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
				if not self.el._quitting:  
					# don't process quit requests while already quitting
					ui_request(keysym)
				try:
					key = self.pylink_keycodes[keysym.sym]
				except KeyError:
					key = keysym.sym
				# don't allow escape to control tracker unless calibrating
				if key == pylink.ESC_KEY and not self.el.in_setup:  
					key = pylink.JUNK_KEY
				keys.append(pylink.KeyInput(key, keysym.mod))
		return keys

	def get_mouse_state(self):
		# Gets the current mouse state (cursor x/y and button state) relative to
		# the EyeLink camera image
		x, y, b = mouse_pos(pump_event_queue=False, return_button_state=True)
		size = self._scale_up(*self.size)
		x = int(x) - (P.screen_c[0] - size[0] / 2)
		y = int(y) - (P.screen_c[1] - size[1] / 2)
		# Restrict mouse coords to within bounds of camera image
		x = clip(x, minimum=0, maximum=size[0])
		y = clip(y, minimum=0, maximum=size[1])
		if b != 1: # Register left clicks only 
			b = 0
		return (self._scale_down(x, y), b)

	def alert_printf(self, message):
		# Prints any EyeLink alert messages to the console
		print("EyeLink Alert: {0}".format(message))

	def setup_image_display(self, width, height):
		# Sets the EyeLink camera image to the provided size.
		self.__imgwidth__ = width
		self.__imgheight__ = height
		self.clear_cal_display()
		return 1  # returns 1 on success

	def exit_image_display(self):
		# Called when exiting EyeLink setup
		self.clear_cal_display()

	def image_title(self, text):
		# Draws the caption text underneath the camera image
		self.title = message(text, "el_setup", blit_txt=False)

	def set_image_palette(self, r, g, b):
		"""Sets the palette colours to use for rendering the camera image.

		"""
		# Clear the current image buffer
		self.imagebuffer = []
		# Converts the supplied RGB lists into PIL palette format
		self.palette = list(sum(zip(r, g, b), ()))

	def draw_image_line(self, width, line, totlines, buff):
		"""Reads in and displays the camera image from the EyeLink.

		The EyeLink sends image data to the Display PC one line of pixels at a time.
		This method gathers those lines of pixels until a full image is available,
		at which point it draws the image, caption text, and any crosshairs or overlays
		to the screen.

		"""
		if len(self.imagebuffer) > (width * totlines):
			self.imagebuffer = []
		# Add the latest line of pixels to the image buffer
		self.imagebuffer += buff
		# If we have a complete image, draw it
		if int(line) == int(totlines):
			# Render complete camera image and resize to the output size
			img = Image.new("P", (width, totlines), 0)
			img.putpalette(self.palette)
			img.putdata(self.imagebuffer)
			size = self._scale_up(*self.size)
			self.img = img.convert('RGBA').resize(size, Image.BILINEAR)
			# Set up aggdraw to draw crosshair/bounds/etc. on image surface
			self.drawer = Draw(self.img)
			self.drawer.setantialias(True)
			self.draw_cross_hair()
			self.drawer.flush()
			# Draw complete image to screen
			fill()
			blit(asarray(self.img), 5, P.screen_c)
			if self.title:
				y_offset = int(size[1] / 2) + 20
				loc_x = (P.screen_c[0])
				loc_y = (P.screen_c[1] + y_offset)
				blit(self.title, 8, (loc_x, loc_y))
			flip()
			# Clear image buffer
			self.imagebuffer = []

	def draw_lozenge(self, x, y, width, height, colorindex):
		x, y = self._scale_up(x, y)
		width, height = self._scale_up(width, height)
		# Draws the pupil search boundary limits on the camera image
		lozenge_pen = Pen(self.pylink_colors[colorindex], 3, 255)
		# If width > height, sides are round & top/bottom are flat
		if width > height:
			gap = width - height
			middle = x + width / 2.0
			arc_left = (x, y, x + height, y + height)
			arc_right = (x + gap, y, x + width, y + height)
			line_x1, line_x2 = (floor(middle - gap / 2.0), ceil(middle + gap / 2.0))
			line_top = (line_x1, y, line_x2, y)
			line_bottom = (line_x1, y + height, line_x2, y + height)
			# Draw the different parts of the pupil search bounds
			self.drawer.arc(arc_left, 90, 270, lozenge_pen)
			self.drawer.arc(arc_right, -90, 90, lozenge_pen)
			self.drawer.line(line_top, lozenge_pen)
			self.drawer.line(line_bottom, lozenge_pen)
		# If height > width, top/bottom are round & sides are flat
		elif height > width:
			gap = height - width
			middle = y + height / 2.0
			arc_top = (x, y, x + width, y + width)
			line_y1, line_y2 = (floor(middle - gap / 2.0), ceil(middle + gap / 2.0))
			arc_bottom = (x, y + gap, x + width, y + height)
			line_left = (x, line_y1, x, line_y2)
			line_right = (x + width, line_y1, x + width, line_y2)
			# Draw the different parts of the pupil search bounds
			self.drawer.arc(arc_top, 0, 180, lozenge_pen)
			self.drawer.arc(arc_bottom, 180, 360, lozenge_pen)
			self.drawer.line(line_left, lozenge_pen)
			self.drawer.line(line_right, lozenge_pen)
		# If height == width, search bounds are a perfect circle
		else:
			self.drawer.ellipse((x, y, x + width, y + height), lozenge_pen)

	def draw_line(self, x1, y1, x2, y2, colorindex):
		x1, y1 = self._scale_up(x1, y1)
		x2, y2 = self._scale_up(x2, y2)
		# Draws a line with a given colour on the camera image
		line_pen = Pen(self.pylink_colors[colorindex], 3, 255)
		self.drawer.line((x1, y1, x2, y2), line_pen)

	@property
	def size(self):
		# The current height and width of the camera image.
		return (self.__imgwidth__, self.__imgheight__)
