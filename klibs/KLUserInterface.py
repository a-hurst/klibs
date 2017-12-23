__author__ = 'jono'

from time import time

from sdl2 import (SDL_KEYUP, SDL_KEYDOWN, SDL_MOUSEBUTTONUP, SDLK_UP, SDLK_DOWN,
	SDLK_LEFT, SDLK_RIGHT, SDLK_a, SDLK_b, SDLK_c, SDLK_p, SDLK_q)

from klibs.KLConstants import MOD_KEYS
from klibs import P
from klibs.KLUtilities import pump


def any_key(allow_mouse_click=True):
		"""
		A function that waits until any keyboard (or mouse, if enabled) input is received 
		before returning. Intended for use in situations when you want to require input before 
		progressing through the experiment (e.g. "To start the next block, press any key..."). 
		Not to be used for response collection (see :mod:`~klibs.KLResponseCollectors`).

		:param boolean allow_mouse_click: Whether to accept a mouse click as pause-ending event.
		:return boolean:
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

def key_pressed(keycode=None, queue=None):

	"""
	Checks an event queue to see if a given key has been pressed. If no keycode is specified,
	the function will return True if any key has been pressed. If an event queue is not
	manually specified, :func:`~klibs.KLUtilities.pump` will be called and the returned event
	queue will be used.

	Args:
		keycode (:obj:`sdl2.SDL_Keycode`, optional): The SDL keycode corresponding to the key
			to check. 
		queue (:obj:`list` of :obj:`sdl2.SDL_Event`, optional): A list of SDL_Events to check
			for valid keypress events.

	Returns:
		bool: True if key has been pressed, False otherwise.

	Raises:
		ValueError: If the keycode is anything other than an SDL_Keycode integer or None.

	"""

	if type(keycode).__name__ not in ['int', 'NoneType']:
		raise ValueError('keycode must be an SDL Keycode (int) or a NoneType') 
	
	pressed = False
	if queue == None:
		queue = pump(True)
	for e in queue:
		if e.type == SDL_KEYDOWN:
			ui_request(e.key.keysym)
			if not keycode or e.key.keysym.sym == keycode:
				pressed = True
				break

	return pressed

def konami_code(callback=None):
	"""
	An implementation of the classic Konami code. Waits 10 seconds for the keys to be pressed
	in the right sequence before returning. Useful for adding hidden debug menus and other 
	things you really don't want participants activating by mistake.

	:param callback: The function to be run upon successful input of the Konami code.
	:type callback: None or function
	:return boolean: True if sequence was correctly entered within 10 sec, otherwise False.
	"""
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

		Inspects input for interface commands (e.g. "quit"). If no specific event queue or
		keypress event(s) are passed to the function, the current contents of the SDL2 event
		queue are fetched and processed. 
		
		This function is called implicitly by many other klibs functions, but it should be
		called manually during loops when the experiment is unresponsive to user input.
		Currently only "quit" is implemented, but "pause" and "calibrate eye tracker" functions
		are planned.

		:param key_press: A keysym or list of keysyms to check for interface commands.
		:type keypress: None or SDL_Keysym or list[SDL_Keysym]
		:param boolean execute: Whether to execute a command or just return the command type.
		:param queue: A list of SDL Events to inspect for interface command keypresses.
		:type queue: None or list[SDL_Event]
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

