# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

# TODO: Add top-level docstring explaining conceptual side
# TODO: Rewrite current docstrings
# TODO: Consider whether additional functions/objects would be useful

from sdl2 import SDL_PumpEvents, SDL_FlushEvents, SDL_FIRSTEVENT, SDL_LASTEVENT
from sdl2.ext import get_events


def pump(return_events=False):

	"""Pumps the SDL2 event queue and appends its contents to the EventManager log.
	The SDL2 event queue contains SDL_Event objects representing keypresses, mouse
	movements, mouse clicks, and other input events that have occured since last
	check.

	Pumping the SDL2 event queue clears its contents, so be careful of calling it
	(or functions that call it implicitly) multiple times in the same loop, as it
	may result in unexpected problems watching for input (e.g if you have two
	functions checking for mouse clicks within two different boundaries and both
	call pump(), the second one will only return True if a click within that boundary
	occurred within the sub-millisecond interval between the first and second functions.)
	To avoid these problems, you can manually fetch the queue once per loop and pass its
	contents to each of the functions in the loop inspecting user input.

	Args:
		return_events (bool): If true, returns the contents of the SDL2 event queue.

	Returns:
		A list of SDL_Event objects, if return_events=True. Otherwise, the return 
		value is None.

	"""
    # NOTE: get_events() empties queue, SDL_PumpEvents() doesn't
	SDL_PumpEvents()
	if return_events:
		return get_events()


def flush():
	"""Empties the event queue of all unprocessed input events. This should be called before
	any input-checking loops, to avoid any input events from before the loop being processed.
	
	"""
	SDL_PumpEvents() # Ensures all pending system events are added to event queue
	SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT)
