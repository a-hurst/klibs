"""

The purpose of this module is to make it easy to collect responses of different types
from participants (e.g. keypress responses, color wheel judgements). There are several
built-in ResponseListener types:

* :class:`KeypressListener` - For collecting keypress responses
* :class:`MouseButtonListener` - For collecting mouse button responses
* :class:`ColorWheelListener` - For collecting color wheel judgement responses

Additionally, you can create your own ResponseListener by creating a subclass of
:class:`BaseResponseListener`.


Basic Usage
-----------

To use a ResponseListener after defining it, simply call its ``collect`` method::

   resp, rt = self.key_listener.collect()

This will initiate the response collection loop and wait until either a response
has been made or the listener has timed out before returning.

For most response listeners, the ``collect()`` method returns a tuple with two
items: the response value (e.g. 'left') and the participant's reaction time in
milliseconds. Some listeners may return additional elements, so check the return
type documentation for a ResponseListener before using it.

For accurate response timing, you must present the stimuli that the participant
responds to (e.g. a target in a cueing task) immediately before starting response
collection. This is because it takes a few milliseconds (usually ~17) to refresh
the screen, so you want to mark the start of the response period as the moment
that the participant is shown the stimuli.


Loop Callbacks
--------------

During some tasks, you may need to update the screen during response collection
(e.g. removing a brief target stimulus, providing live feedback). In most cases
this can be done by providing the listener with a `callback function`, which is
then called internally every time the :meth:`collect` loop checks for new input.
For example, a callback that shows the current time elapsed since the start of
the collection loop might look like this::

   def show_elapsed(self):
       # Draw the elapsed time since response collection started
       elapsed = str(int(self.key_listener.elapsed))
       fill()
       message(elapsed, location=P.screen_c)
       flip()

Additionally, you may want to be able to end response collection early if certain
conditions are met (e.g. if the participant looks away from fixation during the
response period for an eye tracking task). These situations can also be handled
by a callback: if the callback returns ``True`` at any time during the
:meth:`collect` loop, response collection will be ended immediately::

   def ensure_fixation(self):
       # End trial and show error if gaze leaves fixation before response
       if self.el.saccade_from_boundary('fixation'):
           show_error_msg("Looked away!")
           return True


Advanced Usage
--------------

For advanced use cases (e.g. collecting two different types of response at once),
you may need to customize a listener's collection loop beyond what a custom
callback can provide. To support these edge cases, you can use ResponseListeners
in your own custom collection loops using the ``init``, ``listen`` and ``cleanup``
methods::

   self.key_listener.init()
   self.mouse_listener.init()

   key_resp = None
   mouse_resp = None
   while not (key_resp and mouse_resp):
       q = pump()
       ui_request(queue=q)
       if not key_resp:
           key_resp = self.key_listener.listen(q)
       if not mouse_resp:
           mouse_resp = self.mouse_listener.listen(q)

   self.key_listener.cleanup()
   self.mouse_listener.cleanup()

The ``init`` method sets the timestamp for the start of the collection loop and
performs any other necessary setup for the listener (e.g. making sure the mouse
cursor is visible for color wheel responses).

The ``listen`` method checks a given event queue for response input, returning
the response and reaction time if a valid response has been made or ``None``
otherwise.

The ``cleanup`` method resets the start time for the listener and does any other
necessary cleanup (e.g. re-hiding the cursor if it was originally hidden prior
to collecting a color wheel response).

"""

import sdl2

from klibs import P
from klibs.KLTime import precise_time
from klibs.KLEventQueue import pump, flush
from klibs.KLUserInterface import ui_request, mouse_pos

from klibs.KLBoundary import AnnulusBoundary
from klibs.KLUtilities import angle_between


class BaseResponseListener(object):
    """An abstract base class for creating response listeners.
    
    The purpose of ResponseListeners is to make it easy to collect responses of a
    given type from participants (e.g. keypress responses, mouse cursor responses).
    There are a number of built-in ResponseListener classes for common use cases, but
    this base class is provided so that you can create your own.

    Args:
        timeout (float, optional): The maximum duration (in seconds) to wait for a
            valid response. Defaults to None (no timeout).
        loop_callback (callable, optional): An optional function or method to be
            called every time the collection loop checks for new input.

    """
    def __init__(self, timeout=None, loop_callback=None):
        self._loop_start = None
        self._callback = loop_callback
        self.timeout_ms = timeout * 1000 if timeout else None
        self.default_response = (None, -1)

    def _timestamp(self):
        # The timestamp (in milliseconds) to use as the start time for the loop.
        return precise_time() * 1000

    def collect(self):
        """Collects a single response from the participant.

        This method starts the response collection loop and waits until either a
        response is made or the listener times out to return.

        Returns:
            tuple: A tuple containing the response value(s) and the reaction
            time of the response (in milliseconds).

        """
        resp = None
        self.init()
        while not resp:
            # End collection if the loop has timed out
            if self.timeout_ms:
                if self.elapsed > self.timeout_ms:
                    break
            # Fetch event queue and check for valid responses
            events = pump()
            resp = self.listen(events)
            ui_request(queue=events)
            # If a callback is provided, call it once per loop
            if not resp and self._callback:
                interrupt = self._callback()
                if interrupt:
                    break
        self.cleanup()
        # If no response given, return default response
        if not resp:
            resp = self.default_response
        return resp

    def init(self):
        """Initializes the listener for response collection.

        This method prepares the listener to enter its collection loop, initializing
        any necessary objects or hardware and setting the timestamp for when the
        collection loop started.
        
        This only needs to be called manually if using :meth:`listen` directly in a
        custom collection loop: otherwise, it is called internally by :meth:`collect`.

        """
        self._loop_start = self._timestamp()
        flush()

    def listen(self, q):
        """Checks a queue of input events for valid responses.

        This method checks a list of input events for valid responses, and
        returns the value and reaction time of the response if one has occured.
        It is the main method that needs to be defined when creating a custom
        ResponseListener.
        
        This method is used internally by :meth:`collect`, but can also be used
        directly to create custom response collection loops (along with
        :meth:`init` and :meth:`cleanup`) in cases where :meth:`collect` doesn't
        offer enough flexibility, e.g.::

           response = None

           listener.init()
           while not response:
               q = pump()
               ui_request(queue=q)
               response = listener.listen(q)

           listener.cleanup()

        Args:
            q (list): A list of input events to check for valid responses.

        Returns:
            tuple or None: A tuple containing the response value(s) and reaction
            time if a response has been made, otherwise None.
        
        """
        e = "ResponseListener subclass has no defined 'listen' method."
        raise NotImplementedError(e)

    def cleanup(self):
        """Performs any necessary cleanup after response collection.

        This method is the inverse of the :meth:`init` method, resetting any
        initialized hardware or configured options to their original states. For
        example, if collecting an audio response from a microphone and `init` opens
        an audio stream for the device, this method would close it again after a
        response has been collected.

        This only needs to be called manually if using :meth:`listen` directly in a
        custom collection loop: otherwise, it is called internally by :meth:`collect`.

        """
        self._loop_start = None

    @property
    def elapsed(self):
        """float: The elapsed time (in ms) since response collection began.

        If the listener's collection loop has ended or not started yet, the
        elapsed time will be 0.

        """
        if not self._loop_start:
            return 0.0
        return (self._timestamp() - self._loop_start)



class KeypressListener(BaseResponseListener):
    """A simple class for collecting keypress responses.

    This listener collects keypress responses from the participant, with the
    valid response keys and their corresponding output labels being specified
    in a dictionary::

       self.key_listener = KeypressListener({
         "z": "left",
         "/": "right",
       })

    The keys in the dictionary (e.g. 'z', '/') specify which keys to watch for
    responses (other keys will be ignored). Their values (e.g. 'left', 'right')
    specify the response label returned by the listener when that key is pressed.
    
    See the first column in `this table <https://wiki.libsdl.org/SDL2/SDL_Keycode>`_
    for a full list of valid key names.

    Args:
        keymap (dict): A dictionary specifying the keys to check for and their
            corresponding response labels.
        timeout (float, optional): The maximum duration (in seconds) to wait for a
            valid response. Defaults to None (no timeout).
        loop_callback (callable, optional): An optional function or method to be
            called every time the collection loop checks for new input.

    """
    def __init__(self, keymap, timeout=None, loop_callback=None):
        super(KeypressListener, self).__init__(timeout, loop_callback)
        self._keymap = self._parse_keymap(keymap)

    def _timestamp(self):
        # Since keypress events have SDL timestamps, use SDL_GetTicks to mark the
        # start of the collection loop.
        return sdl2.SDL_GetTicks()

    def _parse_keymap(self, keymap):
        # Perform basic validation of the keymap
        if not isinstance(keymap, dict):
            raise TypeError("keymap must be a properly-formatted dict.")
        if len(keymap) == 0:
            raise ValueError("keymap must contain at least one key/label pair.")
        # Convert all key names in the map to SDL keycodes
        keycode_map = {}
        for key, label in keymap.items():
            if type(key) is str:
                keycode = sdl2.SDL_GetKeyFromName(key.encode('utf8'))
            else:
                keycode = key
            if keycode == 0:
                raise ValueError("'{0}' is not a recognized key name.".format(key))
            keycode_map[keycode] = label

        return keycode_map

    def collect(self):
        """Collects a single keypress response from the participant.

        This method starts the response collection loop and waits until either a
        response is made or the listener times out to return::

           response, rt = self.key_listener.collect()
           if not response:
               response = "NA"
               err = "timeout"

        If the listener times out before a response is made, this will return a
        response value of ``None`` and a reaction time of -1.

        Returns:
            tuple: A ``(response, rt)`` tuple containing the response key's
            label and the reaction time of the response (in milliseconds).
        
        """
        return super(KeypressListener, self).collect()

    def listen(self, q):
        """Checks a queue of input events for valid keypress responses.

        Along with :meth:`init` and :meth:`cleanup`, this method can be used to
        create custom response collection loops is cases where :meth:`collect`
        doesn't offer enough flexibility. e.g.::

           key_listener.init()

           response = None
           while not response:
               q = pump()
               ui_request(queue=q)
               response = key_listener.listen(q)

           key_listener.cleanup()
           resp, rt = response

        Args:
            q (list): A list of input events to check for valid key responses.

        Returns:
            tuple or None: A ``(response, rt)`` tuple if a keypress response has
            been made, otherwise None.

        """
        # Checks the input queue for any keypress events for keys in the keymap
        for event in q:
            if event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym # keyboard button event object
                if key.sym in self._keymap.keys():
                    value = self._keymap[key.sym]
                    rt = (event.key.timestamp - self._loop_start)
                    return (value, rt)
        return None


class MouseButtonListener(BaseResponseListener):
    """A simple class for collecting mouse button responses.

    This listener collects mouse button responses from the participant, with the
    allowed buttons and their corresponding output labels being specified in a
    dictionary::

       button_map = {
         "left": "same",
         "right": "different",
       }
       self.mouse_listener = MouseButtonListener(button_map, timeout=3)

    The keys in the dictionary (e.g. 'left') specify which mouse buttons to watch
    for responses (others will be ignored). Their values (e.g. 'same') specify
    the response label returned by the listener if that button is pressed. Valid
    mouse button names are 'left', 'right', 'middle', or 'any' (if any mouse
    button should be considered a valid response).

    Args:
        buttonmap (dict): A dictionary specifying the mouse buttons to check for
            input and their corresponding response labels.
        timeout (float, optional): The maximum duration (in seconds) to wait for a
            valid response. Defaults to None (no timeout).
        loop_callback (callable, optional): An optional function or method to be
            called every time the collection loop checks for new input.

    """
    def __init__(self, buttonmap, timeout=None, loop_callback=None):
        super(MouseButtonListener, self).__init__(timeout, loop_callback)
        self._buttonmap = self._parse_buttonmap(buttonmap)

    def _timestamp(self):
        # Since click events have SDL timestamps, use SDL_GetTicks to mark the
        # start of the collection loop.
        return sdl2.SDL_GetTicks()

    def _parse_buttonmap(self, b_map):
        # Perform basic validation of the button map
        if not isinstance(b_map, dict):
            raise TypeError("button map must be a properly-formatted dict.")
        if len(b_map) == 0:
            raise ValueError("button map must contain at least one key/label pair.")
        # Convert all buttons in the map to SDL constants
        name_map = {
            "left": sdl2.SDL_BUTTON_LEFT,
            "right": sdl2.SDL_BUTTON_RIGHT,
            "middle": sdl2.SDL_BUTTON_MIDDLE,
        }
        sdl_button_map = {}
        for button, label in b_map.items():
            button = button.lower()
            # If any button allowed, set same label for all buttons
            if button == "any":
                for b in ["left", "right", "middle"]:
                    sdl_button_map[name_map[b]] = label
                return sdl_button_map
            # Otherwise, set button labels individually based on map
            if not button in name_map.keys():
                e = "Invalid mouse button name '{0}'."
                raise ValueError(e.format(button))
            sdl_button_map[name_map[button]] = label

        return sdl_button_map

    def collect(self):
        """Collects a single mouse button response from the participant.

        This method starts the response collection loop and waits until either a
        response is made or the listener times out to return::

            response, rt = self.mouse_listener.collect()

        If the listener times out before a response is made, this will return a
        response value of ``None`` and a reaction time of -1.

        Returns:
            tuple: A ``(response, rt)`` tuple containing the response button's
            label and the reaction time of the response (in milliseconds).
        
        """
        return super(MouseButtonListener, self).collect()

    def listen(self, q):
        """Checks a queue of input events for valid mouse button responses.

        Along with :meth:`init` and :meth:`cleanup`, this method can be used to
        create custom response collection loops is cases where :meth:`collect`
        doesn't offer enough flexibility.

        Args:
            q (list): A list of input events to check for mouse button events.

        Returns:
            tuple or None: A ``(response, rt)`` tuple if a mouse button response
            has been made, otherwise None.

        """
        # Checks the input queue for any matching mouse button events
        for event in q:
            if event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                b = event.button.button
                if b in self._buttonmap.keys():
                    value = self._buttonmap[b]
                    rt = (event.button.timestamp - self._loop_start)
                    return (value, rt)
        return None


class ColorWheelListener(BaseResponseListener):
    """A convenience class for collecting color wheel responses.

    The color wheel listener is for measuring the accuracy with which a participant
    remembers or perceives a given color. For these sorts of tasks, a color wheel
    is drawn to the screen and the participant uses the mouse cursor to click the
    color they think best matches a previously-seen color stimulus. This listener
    collects these color judgements and calculates their angular error::

       self.wheel = ColorWheel(diameter=(P.screen_y // 2))
       self.color_listener = ColorWheelListener(self.wheel)

    Prior to collecting a response, you will also need to set the target color for
    the trial using the :meth:`set_target` method::

       # Set the target color for the listener
       self.color_listener.set_target(target_col)

    This class requires that the wheel has already been drawn to the screen and
    the target color has been specified via :meth:`set_target` prior to response
    collection.

    Args:
        wheel (:obj:`~klibs.KLDraw.ColorWheel`): The target color wheel from
            which to collect a color judgement response.
        center (tuple, optional): The (x, y) pixel coordinates for the center of
            the wheel. Defaults to the center of the screen if not specified.
        timeout (float, optional): The maximum duration (in seconds) to wait for a
            color response. Defaults to None (no timeout).
        loop_callback (callable, optional): An optional function or method to be
            called every time the collection loop checks for new input.

    """
    def __init__(self, wheel, center=None, timeout=None, loop_callback=None):
        super(ColorWheelListener, self).__init__(timeout, loop_callback)
        self.default_response = (None, None, -1)
        self._cursor_was_hidden = False
        self._center_xy = center if center else P.screen_c
        self._wheel = wheel
        self._bounds = self._get_wheel_bounds(wheel, self._center_xy)
        self._target = None

    def _get_wheel_bounds(self, wheel, center):
        if not hasattr(wheel, 'color_from_angle'):
            raise TypeError("'wheel' must be a ColorWheel object.")
        return AnnulusBoundary("wheel", center, wheel.radius, wheel.thickness)

    def _timestamp(self):
        return sdl2.SDL_GetTicks()

    def set_target(self, color):
        """Sets the target color for color judgements.

        This method defines the target color to use when calculating accuracy
        for color judgements. Will raise an error if provided color does not
        exist on the listener's color wheel.

        Args:
            color (tuple): An RGB tuple specifying the target color for the
                response collector.
        
        """
        if len(color) < 3 or len(color) > 4:
            e = "target color must be in (r, g, b) format."
            raise ValueError(e)
        color = (color[0], color[1], color[2], 255)
        self._wheel.angle_from_color(color) # Ensure color is present in wheel
        self._target = color

    def collect(self):
        """Collects a single color judgement response from the participant.

        This method starts the response collection loop and waits until either a
        response is made or the listener times out before returning::

           # Show the color wheel and collect a response
           fill()
           blit(self.wheel, 5, P.screen_c)
           flip()
           angle_err, resp_color, rt = self.color_listener.collect()
           if not angle_err:
               angle_err, resp_color = ("NA", "NA")
               err = "timeout"

        If the listener times out before a response is made, this will return 
        angluar error and color values of ``None`` and a reaction time of -1.

        Returns:
            tuple: An ``(err, color, rt)`` tuple containing the angular error of
            the colour judgement (in degrees), the RGB value of the chosen
            color, and the reaction time of the response (in milliseconds).
        
        """
        return super(ColorWheelListener, self).collect()

    def init(self):
        """Initializes the listener for response collection.

        This method shows the mouse cursor, warps it to the middle of the color
        wheel, and starts the response timer.

        Only needs to be called manually if using :meth:`listen` directly in a
        custom collection loop.

        """
        # Ensure a target color has been set before starting
        if not self._target:
            e = "A target color must be set before starting the collection loop"
            raise RuntimeError(e)
        # Start with cursor shown in middle of wheel
        self._cursor_was_hidden = sdl2.ext.cursor_hidden()
        sdl2.ext.show_cursor()
        mouse_pos(position=self._center_xy)
        # Clear any existing events in the queue and set the response start time
        flush()
        self._loop_start = self._timestamp()

    def listen(self, q):
        """Checks a queue of input events for color judgement responses.

        Along with :meth:`init` and :meth:`cleanup`, this method can be used to
        create custom response collection loops in cases where :meth:`collect`
        doesn't offer enough flexibility.

        Args:
            q (list): A list of input events to check for color responses.

        Returns:
            tuple or None: An ``(err, color, rt)`` tuple if a color judgement
            has been made, otherwise None.

        """
        for e in q:
            if e.type == sdl2.SDL_MOUSEBUTTONUP:
                # First, ensure mouse click was within the wheel boundary
                pos = (e.button.x * P.screen_scale_x, e.button.y * P.screen_scale_y)
                if not pos in self._bounds:
                    continue
                # Calculate the angle difference between the response & target colours
                target_angle = self._wheel.angle_from_color(self._target)
                response_angle = angle_between(pos, self._center_xy, 90, clockwise=True)
                color = self._wheel.color_from_angle(response_angle)[:3]
                diff = target_angle - self._wheel.angle_from_color(color)
                # Return the angular error
                angle_err = (
                    diff - 360 if diff > 180 else diff + 360 if diff < -180 else diff
                )
                rt = e.button.timestamp - self._loop_start
                return (angle_err, color, rt)
        return None

    def cleanup(self):
        """Performs any necessary cleanup after response collection.

        For the color wheel listener, this method hides the mouse cursor if it
        wasn't visible already when :meth:`init` was called, resets the response
        timer, and clears the target color.

        Only needs to be called manually if using :meth:`listen` directly in a
        custom collection loop.

        """
        self._target = None
        self._loop_start = None
        if self._cursor_was_hidden:
            sdl2.ext.hide_cursor()
