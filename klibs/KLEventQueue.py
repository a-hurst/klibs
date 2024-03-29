# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

"""This module contains functions for updating, fetching, and clearing the input
event queue.

The input event queue contains events representing key presses, mouse movements, mouse
clicks, joystick events, and more. For example, if you press and release the 'z' key on
the keyboard, a 'key down' event will be added to the event queue when the key is first
pressed and a 'key up' event will be added when the key is released.

In order to read and react to input events in your experiment, you need to fetch the
contents of the queue with the :func:`pump` function and either handle them directly
or pass the queue contents to a function that processes input events (e.g.
:func:`~klibs.KLUserInterface.key_pressed`).

"""

# TODO: Consider whether additional functions/objects would be useful

from sdl2 import SDL_PumpEvents, SDL_FlushEvents, SDL_FIRSTEVENT, SDL_LASTEVENT
from sdl2.ext import get_events


def pump(return_events=True):
    """Retrieves the current contents of the input event queue.
    
    In general, ``pump()`` is usually called at the start of a loop checking
    for input::

        flush() # Clear the input queue before starting the loop
        response = None
        start_time = precise_time()
        while (precise_time() - start_time) < 5.0 and not response:

            q = pump() # Retrieve the current input queue contents

            if key_pressed('z', queue=q):
                response = 'left'
            elif key_pressed('/', queue=q):
                response = 'right'

    Note that calling ``pump()`` both returns and clears the contents of the
    event queue, so make sure to call it only once per loop to avoid missing
    input events.

    Args:
        return_events (bool): Deprecated, should always be True.

    Returns:
        list: A list of ``SDL_Event`` objects.

    """
    return get_events()


def flush():
    """Clears all unprocessed events from the input event queue.
    
    This should be called before any loops that check for input to ensure they
    are not disrupted by earlier input events.
    
    """
    SDL_PumpEvents() # Ensures all pending system events are added to event queue
    SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT)
