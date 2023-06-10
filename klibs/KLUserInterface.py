__author__ = 'Jonathan Mulle & Austin Hurst'


import ctypes

from sdl2 import (SDL_GetKeyFromName, SDL_ShowCursor, SDL_PumpEvents, SDL_BUTTON,
    SDL_DISABLE, SDL_ENABLE, SDL_BUTTON_LEFT, SDL_BUTTON_RIGHT, SDL_BUTTON_MIDDLE,
    SDL_KEYUP, SDL_KEYDOWN, SDL_MOUSEBUTTONUP, SDL_MOUSEBUTTONDOWN, KMOD_CTRL, KMOD_GUI,
    SDLK_UP, SDLK_DOWN, SDLK_LEFT, SDLK_RIGHT, SDLK_a, SDLK_b, SDLK_c, SDLK_p, SDLK_q)
from sdl2.mouse import SDL_GetMouseState, SDL_GetMouseFocus, SDL_WarpMouseInWindow

from klibs import TK_S, TK_MS
from klibs import P
from klibs.KLTime import precise_time as time
from klibs.KLEventQueue import pump


def any_key(allow_mouse_click=True):
    """Stops and waits, continuing only after a key has been pressed.

    Intended for use in situations when you want to require input before progressing
    through the experiment (e.g. "To start the next block, press any key..."). 
    Not intended for use during time-sensitive response collection (see
    :mod:`~klibs.KLResponseCollectors`).

    If ``allow_mouse_click`` is True, this function will also return if a mouse
    button is clicked and released.

    Args:
        allow_mouse_click (bool, optional): Whether to return immediately on mouse
            clicks in addition to key presses.
    
    """
    any_key_pressed = False
    while not any_key_pressed:
        for event in pump(True):
            if event.type == SDL_KEYDOWN:
                ui_request(event.key.keysym)
                any_key_pressed = True
            if event.type == SDL_MOUSEBUTTONUP and allow_mouse_click:
                any_key_pressed = True


def key_pressed(key=None, released=False, queue=None):
    """Checks a given event queue for keypress events.
    
    If no key is specified, the function will return True if any key has been pressed.
    If an event queue is not manually specified, this function will fetch and clear the
    current contents of the input event queue.
    
    For a comprehensive list of valid key names, see the 'Name' column of the following 
    table: https://wiki.libsdl.org/StuartPBentley/CombinedKeyTable

    For a comprehensive list of valid SDL keycodes, consult the following table:
    https://wiki.libsdl.org/SDL_Keycode

    Args:
        key (str or :obj:`sdl2.SDL_Keycode`, optional): The key name or SDL keycode
            corresponding to the key to check. If not specified, any keypress will return
            True.
        released (bool, optional): If True, this function will look for 'key up' events
            instead of 'key down' events. Defaults to False.
        queue (:obj:`List` of :obj:`sdl2.SDL_Event`, optional): A list of events to check
            for valid keypress events.

    Returns:
        bool: True if key has been pressed, otherwise False.

    Raises:
        ValueError: If the keycode is anything other than an SDL_Keycode integer or None.

    """
    strtypes = [type(u" "), type(" ")] # for Python 2/3 unicode compatibility
    if type(key) in strtypes:
        keycode = SDL_GetKeyFromName(key.encode('utf8'))
        if keycode == 0:
            raise ValueError("'{0}' is not a recognized key name.".format(key))
    else:
        keycode = key

    if type(keycode).__name__ not in ['int', 'NoneType']:
        raise ValueError("'key' must be a string, an SDL Keycode (int), or None.") 
    
    pressed = False
    if queue == None:
        queue = pump(True)
    for e in queue:
        if e.type == SDL_KEYDOWN:
            ui_request(e.key.keysym)
        if e.type == (SDL_KEYUP if released else SDL_KEYDOWN):
            if not keycode or e.key.keysym.sym == keycode:
                pressed = True

    return pressed


def mouse_clicked(button=None, released=False, within=None, queue=None):
    """Checks an event queue to see if a mouse button has been clicked.
    
    If a button is specified, this function will only return True when that button has
    been clicked. Otherwise, this function will return True for any mouse click events.
    Valid button names are ``'left'``, ``'right'``, and ``'middle'``.
    
    If a :obj:`~klibs.KLBoundary.Boundary` object is provided (e.g. a
    :obj:`~klibs.KLBoundary.RectangleBoundary`), this function will only return True
    if a click has occured within the boundary. If an event queue is not provided,
    this function will fetch and clear the current contents of the input event queue.

    Args:
        button (str, optional): The name of the button to check for clicks. Defaults to
            ``None`` (checks all buttons for clicks).
        released (bool, optional): If True, this function will look for mouse button
            release events instead of mouse button click events. Defaults to False.
        within (:obj:`~klibs.KLBoundary.Boundary`, optional): A specific region of the
            screen to check for clicks. Defaults to ``None`` (no boundary).
        queue (:obj:`List` of :obj:`sdl2.SDL_Event`, optional): A list of events to
            check for valid mouse button events.

    Returns:
        bool: True if the button has been clicked, otherwise False.

    Raises:
        ValueError: If an invalid button name is provided.

    """
    buttons = {
        'left': SDL_BUTTON_LEFT, 'right': SDL_BUTTON_RIGHT, 'middle': SDL_BUTTON_MIDDLE,
    }
    if button:
        if not button in buttons.keys():
            raise ValueError("'{0}' is not a valid mouse button name.".format(button))
        button = buttons[button]

    bounds = within
    if bounds != None:
        try:
            bounds.within((0, 0))
        except (AttributeError, NotImplementedError):
            err = "The provided boundary must be a valid Boundary object."
            raise TypeError(err)

    clicked = False
    if queue == None:
        queue = pump(True)
    for e in queue:
        if e.type == SDL_KEYDOWN:
            ui_request(e.key.keysym)
        elif e.type == (SDL_MOUSEBUTTONUP if released else SDL_MOUSEBUTTONDOWN):
            if not button or e.button.button == button:
                if bounds:
                    loc = (
                        e.button.x * P.screen_scale_x,
                        e.button.y * P.screen_scale_y
                    )
                    clicked = loc in bounds
                else:
                    clicked = True

    return clicked


def get_clicks(button=None, released=False, queue=None):
    """Gets the (x, y) pixel coordinates of any mouse clicks within the event queue.
    
    If a button is specified, this function will only return the pixel coordinates for
    clicks of that button. Otherwise, this function will return click coordinates for
    all buttons. Valid button names are ``'left'``, ``'right'``, and ``'middle'``.
    
     If an event queue is not provided, this function will fetch and clear the current
    contents of the input event queue.

    Args:
        button (str, optional): The name of the button to check for clicks. Defaults to
            ``None`` (returns clicks from all buttons).
        released (bool, optional): If True, this function will return the coordinates
            for mouse button release events instead of mouse button click events.
            Defaults to False.
        queue (:obj:`List` of :obj:`sdl2.SDL_Event`, optional): A list of events to
            checkfor valid mouse button events.

    Returns:
        :obj:`List`: A list containing the (x, y) coordinates of any matching mouse
        click events.

    Raises:
        ValueError: If an invalid button name is provided.

    """
    buttons = {
        'left': SDL_BUTTON_LEFT, 'right': SDL_BUTTON_RIGHT, 'middle': SDL_BUTTON_MIDDLE,
    }
    if button:
        if not button in buttons.keys():
            raise ValueError("'{0}' is not a valid mouse button name.".format(button))
        button = buttons[button]

    clicks = []
    if queue == None:
        queue = pump(True)
    for e in queue:
        if e.type == SDL_KEYDOWN:
            ui_request(e.key.keysym)
        elif e.type == (SDL_MOUSEBUTTONUP if released else SDL_MOUSEBUTTONDOWN):
            if not button or e.button.button == button:
                clicks.append((
                    int(e.button.x * P.screen_scale_x),
                    int(e.button.y * P.screen_scale_y)
                ))

    return clicks


def show_cursor():
    """Shows the mouse cursor if it is currently hidden.

    If the cursor is already visible, this function does nothing.

    """
    SDL_ShowCursor(SDL_ENABLE)


def hide_cursor():
    """Hides the mouse cursor if it is currently visible.
    
    If the cursor is already hidden, this function does nothing.
    
    """
    SDL_ShowCursor(SDL_DISABLE)


def mouse_pos(pump_event_queue=True, position=None, return_button_state=False):
    """Returns the current coordinates of the mouse cursor, or alternatively warps the
    position of the cursor to a specific location on the screen.

    Args:
        pump_event_queue (bool, optional): Pumps the SDL2 event queue. See documentation
            for pump() for more information. Defaults to True.
        position (None or iter(int,int), optional): The x,y pixel coordinates to warp
            the cursor to if desired. Defaults to None.
        return_button_state (bool, optional): If True, return the mouse button currently
            being pressed (if any) in addition to the current cursor coordinates. Defaults
            to False.

    Returns:
        A 2-element Tuple containing the x,y coordinates of the cursor as integer values.
        If position is not None, this will be the coordinates the cursor was warped to.
        If return_button_state is True, the function returns a 3-element Tuple containing
        the x,y coordinates of the cursor and the mouse button state (left pressed = 1,
        right pressed = 2, middle pressed = 3, none pressed = 0).

    """
    # NOTE: Should really be split into 2 or 3 functions for UI simplicity
    if pump_event_queue:
        SDL_PumpEvents()
    if not position:
        cx, cy = ctypes.c_int(0), ctypes.c_int(0)
        button_state = SDL_GetMouseState(ctypes.byref(cx), ctypes.byref(cy))
        x = int(cx.value * P.screen_scale_x)
        y = int(cy.value * P.screen_scale_y)
        if return_button_state:
            if (button_state & SDL_BUTTON(SDL_BUTTON_LEFT)): pressed = 1
            elif (button_state & SDL_BUTTON(SDL_BUTTON_RIGHT)): pressed = 2
            elif (button_state & SDL_BUTTON(SDL_BUTTON_MIDDLE)): pressed = 3
            else: pressed = 0
            return (x, y, pressed)
        else:
            return (x, y)
    else:
        x = int(position[0] / P.screen_scale_x)
        y = int(position[1] / P.screen_scale_y)
        window = SDL_GetMouseFocus()
        SDL_WarpMouseInWindow(window, x, y)
        return position


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
    # TODO: Might actually be useful if you could specify a custom code (e.g. 123)
    sequence = [
        SDLK_UP, SDLK_DOWN, SDLK_UP, SDLK_DOWN, SDLK_LEFT, SDLK_RIGHT, SDLK_LEFT, SDLK_RIGHT,
        SDLK_b, SDLK_a
    ]
    if not hasattr(konami_code, "input"):
        konami_code.input = [] # static variable, stays with the function between calls
    
    code_entered = False
    if queue == None:
        queue = pump(True)
    for e in queue:
        if e.type == SDL_KEYDOWN:
            ui_request(e.key.keysym)
            konami_code.input.append(e.key.keysym.sym)
            if konami_code.input != sequence[:len(konami_code.input)]:
                konami_code.input = [] # reset input if mismatch encountered
            elif len(konami_code.input) == len(sequence):
                code_entered = True

    if code_entered:
        konami_code.input = []
        if callable(callback):
            callback(**cb_args)

    return code_entered


def ui_request(key_press=None, execute=True, queue=None):
    """Checks keyboard input for interface commands, which currently include:
    
    - Quit (Ctrl/Command-Q): Quit the experiment runtime

    - Calibrate Eye Tracker (Ctrl/Command-C): Enter setup mode for the connected eye tracker, 
      if eye tracking is enabled for the experiment and not using TryLink simulation.
    
    If no event queue from :func:`~klibs.KLEventQueue.pump` and no keypress event(s) are
    supplied to this function, the current contents of the SDL2 event queue will be fetched
    and processed using :func:`~klibs.KLEventQueue.pump`. 
    
    This function is meant to be called during loops in your experiment where no other input
    checking occurs, to ensure that you can quit your experiment or recalibrate your eye
    tracker during those periods.
    
    This function is called implicitly by other functions that process keyboard/mouse input, such
    as :func:`any_key`, :func:`key_pressed`, and :func:`mouse_clicked` (but not :func:`mouse_pos`),
    so you will not need to call it yourself in places where one of them is already being called. 
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


def smart_sleep(interval, units=TK_MS):
    """Waits a given duration while still allowing for quit events.
    s
    This function is useful when you want your program to stop and wait
    for an interval while still listening for quit events during that
    period.

    Args:
        interval (float): The number of units of time to pause execution for.
        units (int, optional): The time unit of 'interval', must be one of
            `klibs.TK_S` (seconds) or `klibs.TK_MS` (milliseconds). Defaults
            to milliseconds.
            
    """
    if units == TK_MS:
        interval *= .001
    start = time()
    while time() - start < interval:
        ui_request()
