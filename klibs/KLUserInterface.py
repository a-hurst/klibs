__author__ = 'jono'
from sdl2 import SDL_KEYUP, SDL_KEYDOWN, SDL_MOUSEBUTTONUP, SDLK_q, SDLK_p, SDLK_c,SDLK_UP, SDLK_DOWN, SDLK_LEFT, \
	SDLK_RIGHT, SDLK_b, SDLK_a
from time import time
from klibs.KLConstants import MOD_KEYS, UI_METHOD_KEYSYMS
from klibs import P
from klibs.KLUtilities import pump

def any_key(allow_mouse_click=True):
		"""
		Used for quickly allowing a user to acknowledge something on screen. Not to be used for response collection (see
		:mod:`~klibs.KLResponseCollectors`).

		:return Boolean:
		"""
		any_key_pressed = False
		while not any_key_pressed:
			for event in pump(True):
				if event.type == SDL_KEYDOWN:
					ui_request(event.key.keysym)
					any_key_pressed = True
				if event.type == SDL_MOUSEBUTTONUP and allow_mouse_click:
					any_key_pressed = True

		return True

def konami_code(callback=None):
	start = time()
	sequence = []
	konami_sequence = [SDLK_UP, SDLK_DOWN, SDLK_UP, SDLK_DOWN, SDLK_LEFT, SDLK_RIGHT, SDLK_LEFT, SDLK_RIGHT, SDLK_b, SDLK_a]
	while True:
		print sequence
		for event in pump(True):
			if time() - start > 10:
				return False
			if event.type != SDL_KEYDOWN:
				continue
			ui_request(event.key.keysym)
			key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
			# if not len(sequence) and key.keysym.sym != SDLK_UP:
			# 	return False
			sequence.append(key.keysym.sym)
			if len(sequence) == 10:
				if sequence == konami_sequence:
					if callable(callback):
						callback()
					return True


def ui_request(key_press=None, execute=True, queue=None):
		"""
		``extension_planned``

		Inspects a keypress for interface commands like "quit", "pause", etc.. Primarily used by
		:func:`~klibs.KLExperiment.Experiment.over_watch`; Currently only "quit" is implemented.

		:param key_press:
		:param execute:
		:return:
		"""

		if queue:
			ret_val = None
			for e in queue:
				v = ui_request(e)
				if v: ret_val = v
			return ret_val
		if not key_press:
			for event in pump(True):
				if event.type in [SDL_KEYUP, SDL_KEYDOWN]:
					request = ui_request(event.key.keysym)
					if request:
						return
				if event.type == SDL_KEYUP:
					return # ie it wasn't a ui request and can't become one now
			return False
		else:
			try:
				key_press = key_press.key.keysym
			except AttributeError:
				pass

		try:
			iter(key_press)
		except TypeError:
			key_press = [key_press]
		for k in key_press:
			if k.mod in (MOD_KEYS["Left Command"], MOD_KEYS["Right Command"]):
				if k.sym in UI_METHOD_KEYSYMS:
					if k.sym == SDLK_q:
						if execute:
							from klibs.KLEnvironment import exp
							exp.quit()
						else:
							return [True, "quit"]
					elif k.sym == SDLK_c:
						# todo: error handling here
						if execute:
							from klibs.KLEnvironment import el
							# if Params.eye_tracking and Params.eye_tracker_available:
							return el.calibrate()
						else:
							return [True, "el_calibrate"]
					elif k.sym == SDLK_p:
						if execute:
							return pause()
						else:
							return [True, "pause" if not P.paused else "unpause"]
		return False


def pause():
		"""
		``broken`` ``heavy_modification_planned`` ``backwards_compatibility_expected``

		Pauses an experiment by displaying a 'paused' message and updating the experiment's :mod:`~klibs.KLResponseCollectors`.\ :class:`~klibs.KLResponseCollectors.ResponseCollector`
		instance accordingly. Currently undergoing update; do not use.
		"""
		if not P.paused:
				# self.message('PAUSED', fullscreen=True, location='center', font_size=96, color=(255, 0, 0, 255),
				# 			 registration=5, blit=True)
			while P.paused:
				ui_request()
		else:
			P.paused = False

