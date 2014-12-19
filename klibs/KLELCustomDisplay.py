__author__ = 'jono'
import pylink
import array
import time

#  these are all from our framework but shouldn't be the source of any interference here
from AudioClip import AudioClip  # just a simple class for playing sdl2 sounds we made
from NumpySurface import *  # a class for easily moving between numpy pixel arrays and sdl2/openGL
from UtilityFunctions import *  # as it sounds, some helper functions our framework is using
import Params  # a list of program-wide settings like screen dimensions, colors, etc.


class KLELCustomDisplay(pylink.EyeLinkCustomDisplay):
	__eyelink_key_translations = {
		"left": pylink.CURS_LEFT,
		"right": pylink.CURS_RIGHT,
		"up": pylink.CURS_UP,
		"down": pylink.CURS_DOWN,
		"return": pylink.EL_IMAGE_MODE,
		"space": sdl2.SDLK_SPACE,
		"a": sdl2.SDLK_a,
		"c": pylink.EL_CALIBRATE_MODE,
		"o": pylink.EL_OUTPUT_MENU_MODE,
		"v": pylink.EL_VALIDATE_MODE
	}

	window = None
	window_id = None
	window_surface = None
	window_array = None
	experiment = None
	tracker = None
	size = [None, None]
	fill_color = [128, 128, 128, 255]
	byteorder = None

	def __init__(self, experiment, tracker):
		self.experiment = experiment  # a reference to the instance of the "experiment class" where most of the
		self.size = self.experiment.window.size
		self.tracker = tracker

		if sys.byteorder == 'little':
			self.byteorder = 1
		else:
			self.byteorder = 0

		pylink.EyeLinkCustomDisplay.__init__(self)

		try:
			self.__target_beep__ = AudioClip("target_beep.wav")
			self.__target_beep__done__ = AudioClip("target_beep_done.wav")
			self.__target_beep__error__ = AudioClip("target_beep_error.wav")
		except:
			self.__target_beep__ = None
			self.__target_beep__done__ = None
			self.__target_beep__error__ = None

		self.imagebuffer = array.array('L')
		"""
		unknown var
		"""
		self.pal = None
		self.width = Params.screen_x
		self.height = Params.screen_y

	def setup_cal_display(self):
		print "setup_cal_display()"
		self.window = sdl2.ext.Window("Calibration", size=Params.screen_x_y, position=(0, 0), flags=SCREEN_FLAGS)
		self.window_id = sdl2.SDL_GetWindowID(self.window.window)
		self.window_surface = sdl2.SDL_GetWindowSurface(self.window.window)
		self.window_array = sdl2.ext.pixels3d(self.window_surface.contents)
		self.clear_cal_display()
		time.sleep(0.1)
		sdl2.SDL_PumpEvents()

	def exit_cal_display(self):
		print "exit_cal_display()"
		sdl2.SDL_DestroyWindow(self.window.window)

	def record_abort_hide(self):
		print "record_abort_hide()"
		pass

	def clear_cal_display(self):
		print "clear_cal_display()"
		r, g, b, a = self.fill_color
		sdl2.ext.fill(self.window_surface.contents, sdl2.pixels.SDL_Color(r, g, b, a))
		self.window.refresh()
		sdl2.ext.fill(self.window_surface.contents, sdl2.pixels.SDL_Color(r, g, b, a))
		sdl2.SDL_PumpEvents()

	def erase_cal_target(self):
		print "erase_cal_target()"
		self.clear_cal_display()

	def draw_cal_target(self, location):
		print "draw_cal_target(): {0}".format(location)
		draw_context_length = Params.screen_x // 70
		black_brush = aggdraw.Brush(tuple(0, 0, 0, 255))
		white_brush = aggdraw.Brush(tuple(255, 255, 255, 255))
		draw_context = aggdraw.Draw("RGBA", [draw_context_length, draw_context_length], (0, 0, 0, 0))
		draw_context.ellipse([0, 0, draw_context_length, draw_context_length], black_brush)
		draw_context.ellipse([0, 0, draw_context_length // 2, draw_context_length // 2], white_brush)
		self.experiment.blit(from_aggdraw_context(draw_context), 5, location)

	def play_beep(self, clip):
		print "play_beep(): {0}".format(clip)
		if clip == pylink.DC_TARG_BEEP or clip == pylink.CAL_TARG_BEEP:
			self.__target_beep__.play()
		elif clip == pylink.CAL_ERR_BEEP or clip == pylink.DC_ERR_BEEP:
			self.__target_beep__error__.play()
		else:
			self.__target_beep__done__.play()

	def get_input_key(self):
		key = self.experiment.listen(MAX_WAIT, "eyelink", flip=False)[0]
		if key in self.__eyelink_key_translations:
			return pylink.KeyInput(self.__eyelink_key_translations[key], False)
		else:
			return pylink.KeyInput(self.__eyelink_key_translations[pylink.JUNK_KEY], False)

	def get_mouse_state(self):
		print "get_mouse_state()"
		return mouse_pos()

	def exit_image_display(self):
		print "exit_image_display()"
		self.experiment.clear(self.fill_color)
		self.experiment.flip()

	def alert_printf(self, message):
		print "alert_printf(): message -> {0}".format(message)
		self.experiment.message(message, color=(255, 0, 0, 0), location=(0.05 * Params.screen_x, 0.05 * Params.screen_y))

	def setup_image_display(self, width, height):
		print "setup_image_display(): width -> {0}, heigh -> {1}".format(width, height)

		self.img_size = (width, height)
		self.image_vp.parameters.screen.clear()
		pass

	def image_title(self, text):
		print "image_title(): text -> {0}".format(text)

	def draw_image_line(self, width, line, totlines, buff):
		print "draw_image_line(): width -> {0}, line -> {1}, totlines -> {2}, buff -> {3}".format(width, line, totlines, buff)

	def draw_lozenge(self, x, y, width, height, colorindex):
		print "draw_lozenge(): x -> {0}, y -> {1}, width -> {2}, height -> {3}, colorindex -> {4}".format(x, y, width, height, colorindex)

	def draw_line(self, x1, y1, x2, y2, colorindex):
		print "draw_line(): x1 -> {0}, y1 -> {1}, x2 -> {2}, y2 -> {3}, colorindex -> {4}".format(x1, y1, x2, y2, colorindex)

	def set_image_palette(self, r, g, b):
		print "set_image_palette(): r -> {0}, g -> {1}, b -> {2}".format(r, g, b)
