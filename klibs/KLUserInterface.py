__author__ = 'Jonathan Mulle & Austin Hurst'

from sdl2 import (SDL_GetKeyFromName, SDL_KEYUP, SDL_KEYDOWN, SDL_MOUSEBUTTONUP, KMOD_CTRL,
	KMOD_GUI, SDLK_UP, SDLK_DOWN, SDLK_LEFT, SDLK_RIGHT, SDLK_a, SDLK_b, SDLK_c, SDLK_p, SDLK_q)

from klibs import P
from klibs.KLTime import precise_time as time
from klibs.KLUtilities import pump


def any_key(allow_mouse_click=True):
	"""A function that waits until any keyboard (or mouse, if enabled) input is received
	before returning. Intended for use in situations when you want to require input before
	progressing through the experiment (e.g. "To start the next block, press any key..."). 
	Not to be used for response collection (see :mod:`~klibs.KLResponseCollectors`).

	Args:
		allow_mouse_click (bool, optional): Whether to return immediately on mouse clicks in
			addition to key presses.
	
	"""
	any_key_pressed = False
	while not any_key_pressed:
		for event in pump(True):
			if event.type == SDL_KEYDOWN:
				ui_request(event.key.keysym)
				any_key_pressed = True
			if event.type == SDL_MOUSEBUTTONUP and allow_mouse_click:
				any_key_pressed = True


#todo: add a function that detects a mouse click like key_pressed
def key_pressed(key=None, queue=None):
	"""Checks an event queue to see if a given key has been pressed. If no key is specified,
	the function will return True if any key has been pressed. If an event queue is not
	manually specified, :func:`~klibs.KLUtilities.pump` will be called and the returned event
	queue will be used.
	
	For a comprehensive list of valid key names, see the 'Name' column of the following 
	table: https://wiki.libsdl.org/StuartPBentley/CombinedKeyTable

	For a comprehensive list of valid SDL keycodes, consult the following table:
	https://wiki.libsdl.org/SDL_Keycode

	Args:
		key (str or :obj:`sdl2.SDL_Keycode`, optional): The key name or SDL keycode
			corresponding to the key to check. If not specified, any keypress will return
			True.
		queue (:obj:`List` of :obj:`sdl2.SDL_Event`, optional): A list of SDL_Events to check
			for valid keypress events.

	Returns:
		bool: True if key has been pressed, otherwise False.

	Raises:
		ValueError: If the keycode is anything other than an SDL_Keycode integer or None.

	"""
	if type(key) is str:
		keycode = SDL_GetKeyFromName(key.encode('utf8'))
		if keycode == 0:
			raise ValueError("'{0}' is not a recognized key name.".format(key))
	else:
		keycode = key

	if type(keycode) not in [int, None]:
		raise ValueError("'key' must be a string, an SDL Keycode (int), or None.") 
	
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


def konami_code(callback=None, cb_args={}, queue=None):
	"""An implementation of the classic Konami code. If called repeatedly within a loop, this
	function will collect keypress matching the sequence and save them between calls until the full
	sequence has been entered correctly.
	
	If a callback function has been specified, it will be called once the code has been entered. 
	If any incorrect keys are pressed during entry, the collected input so far will be reset and
	the code will need to be entered again from the start.
	
	Useful for adding hidden debug menus and other things you really don't want participants
	activating by mistake...?

	Args:
		callback (function, optional): The function to be run upon successful input of the Konami
			code.
		cbargs (:obj:`Dict`, optional): A dict of keyword arguments to pass to the callback
			function when it's called.
		queue (:obj:`List` of :obj:`sdl2.SDL_Event`, optional): A list of SDL Events to check
			for valid keys in the sequence.

	Returns:
		bool: True if sequence was correctly entered, otherwise False.

	"""
	sequence = [
		SDLK_UP, SDLK_DOWN, SDLK_UP, SDLK_DOWN, SDLK_LEFT, SDLK_RIGHT, SDLK_LEFT, SDLK_RIGHT,
		SDLK_b, SDLK_a
	]
	if not hasattr(konami_code, "input"):
		konami_code.input = [] # static variable, stays with the function between calls
	
	if queue == None:
		queue = pump(True)
	for e in queue:
		if e.type == SDL_KEYDOWN:
			ui_request(e.key.keysym)
			konami_code.input.append(e.key.keysym.sym)
			if konami_code.input != sequence[:len(konami_code.input)]:
				konami_code.input = [] # reset input if mismatch encountered
			elif len(konami_code.input) == len(sequence):
				konami_code.input = []
				if callable(callback):
					callback(**cb_args)
				return True
	return False


def ui_request(key_press=None, execute=True, queue=None):
	"""Checks keyboard input for interface commands, which currently include:
	
	- Quit (Ctrl/Command-Q): Quit the experiment runtime

	- Calibrate Eye Tracker (Ctrl/Command-C): Enter setup mode for the connected eye tracker, 
	  if eye tracking is enabled for the experiment and not using TryLink simulation.
	
	If no event queue from :func:`~klibs.KLUtilities.pump` and no keypress event(s) are
	supplied to this function, the current contents of the SDL2 event queue will be fetched
	and processed using :func:`~klibs.KLUtilities.pump`. 
	
	This function is meant to be called during loops in your experiment where no other input
	checking occurs, to ensure that you can quit your experiment or recalibrate your eye
	tracker during those periods. This function is automatically called by other functions that
	process keyboard/mouse input, such as :func:`any_key` and :func:`key_pressed`, so you will
	not need to call it yourself in places where one of them is already being called. 
	In addition, the :obj:`~klibs.KLResponseCollectors.ResponseCollector` collect method also
	calls this function every loop, meaning that you do not need to include it when writing
	ResponseCollector callbacks.

	Args:
		key_press (:obj:`sdl2.SDL_Keysym`, optional): The key.keysym of an SDL_KEYDOWN event to
			check for a valid UI command.
		execute (bool, optional): If True, valid UI commands will be executed immediately. 
			Otherwise, valid UI commands will return a string indicating the type of command
			received. Defaults to True.
		queue (:obj:`List` of :obj:`sdl2.SDL_Event`, optional): A list of SDL Events to check
			for valid UI commands.
		
	Returns:
		str or bool: "quit" if a Quit request encountered, "el_calibrate" if a Calibrate 
			Eye Tracker request encountered, otherwise False.
	"""
	if key_press == None:
		if queue == None:
			queue = pump(True)
		for e in queue:
			if e.type == SDL_KEYDOWN:
				request = ui_request(e.key.keysym, execute)
				if request:
					return request
		return False

	else:
		try:
			key_press.mod
		except AttributeError:
			wrong = type(key_press).__name__
			e = "'key_press' must be a valid SDL Keysym object (got '{0}')".format(wrong)
			raise TypeError(e)

		k = key_press
		if any(k.mod & mod for mod in [KMOD_GUI, KMOD_CTRL]): # if ctrl or meta being held
			if k.sym == SDLK_q:
				if execute:
					from klibs.KLEnvironment import exp
					exp.quit()
				return "quit"
			elif k.sym == SDLK_c:
				if P.eye_tracking:
					from klibs.KLEnvironment import el
					if el.initialized: # make sure el.setup() has been run already
						if execute:
							el.calibrate()
						return "el_calibrate"
		return False
