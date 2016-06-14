__author__ = 'jono'

from os import kill
from signal import SIGKILL
from sys import exit
from sdl2 import SDL_Quit
from klibs.KLConstants import *
from klibs.KLUtilities import pump
import klibs.KLParams as P
from klibs.KLUtilities import full_trace
import klibs.event_interface as evi
import klibs.experiment as exp
import klibs.eyelink as el
import klibs.labjack as lj


def any_key(self, allow_mouse_click=True):
		"""
		Used for quickly allowing a user to acknowledge something on screen. Not to be used for response collection (see
		:mod:`~klibs.KLResponseCollectors`).

		:return Boolean:
		"""
		pump()
		any_key_pressed = False
		while not any_key_pressed:
			for event in sdl2.ext.get_events():
				if event.type == sdl2.SDL_KEYDOWN:
					self.ui_request(event.key.keysym)
					any_key_pressed = True
				if event.type == sdl2.SDL_MOUSEBUTTONUP:
					any_key_pressed = True

		return True


def ui_request(self, key_press=None, execute=True):
		"""
		``extension_planned``

		Inspects a keypress for interface commands like "quit", "pause", etc.. Primarily used by
		:func:`~klibs.KLExperiment.Experiment.over_watch`; Currently only "quit" is implemented.

		:param key_press:
		:param execute:
		:return:
		"""
		if not key_press:
			for event in sdl2.ext.get_events():
				if event.type in [sdl2.SDL_KEYUP, sdl2.SDL_KEYDOWN]:
					ui_request = self.ui_request(event.key.keysym)
					if ui_request:
						return
				if event.type == sdl2.SDL_KEYUP:
					return # ie it wasn't a ui request and can't become one now
			return False
		else:
			try:
				key_press = key_press.key.keysym
			except AttributeError:
				pass

		try:
			iter(key_press)
			for key in key_press:
				if self.ui_request(key):
					return True
		except TypeError:
			if key_press.mod in (MOD_KEYS["Left Command"], MOD_KEYS["Right Command"]):
				if key_press.sym in UI_METHOD_KEYSYMS:
					if key_press.sym == sdl2.SDLK_q:
						return self.quit() if execute else [True, "quit"]
					elif key_press.sym == sdl2.SDLK_c:
						# if Params.eye_tracking and Params.eye_tracker_available:
						return self.eyelink.calibrate() if execute else [True, "el_calibrate"]
					elif key_press.sym == sdl2.SDLK_p:
						if execute:
							return self.pause()
						else:
							return [True, "pause" if not self.paused else "unpause"]
		return False

def pause(self):
		"""
		``broken`` ``heavy_modification_planned`` ``backwards_compatibility_expected``

		Pauses an experiment by displaying a 'paused' message and updating the experiment's :mod:`~klibs.KLResponseCollectors`.\ :class:`~klibs.KLResponseCollectors.ResponseCollector`
		instance accordingly. Currently undergoing update; do not use.
		"""
		if not self.paused:
			pump()
			while self.paused:
				self.message('PAUSED', fullscreen=True, location='center', font_size=96, color=(255, 0, 0, 255),
							 registration=5, blit=True)
				self.ui_listen()
		else:
			self.paused = False

