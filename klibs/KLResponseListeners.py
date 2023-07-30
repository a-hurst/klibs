import sdl2

from klibs.KLTime import precise_time
from klibs.KLEventQueue import pump, flush
from klibs.KLUserInterface import ui_request
from klibs.KLResponseCollectors import Response

# NOTE: Do away with Response class and just return two-item (value, rt) tuple?


class BaseResponseListener(object):
    """An abstract base class for creating response listeners.
    
    The purpose of ResponseListeners is to make it easy to collect responses of a
    given type from participants (e.g. keypress responses, mouse cursor responses).
    There are a number of built-in ResponseListener classes for common use cases, but
    this base class is provided so that you can create your own.

    For accurate response timing, the stimuli that the participant responds to (e.g.
    a target in a cueing task) needs to be draw to the screen immediately before the
    collection loop starts. This is because it takes a few milliseconds (usually ~17)
    to refresh the screen, so you want to mark the start of the response period as
    immediately after the participant sees the stimuli.

    Args:
        timeout (float, optional): The maximum duration (in seconds) to wait for a
            valid response.

    """
    def __init__(self, timeout=None):
        self._loop_start = None
        self.timeout_ms = timeout * 1000 if timeout else None

    def _timestamp(self):
        # The timestamp (in milliseconds) to use as the start time for the loop.
        return precise_time() * 1000

    def collect(self):
        """Collects a single response from the participant.
        
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
            ui_request(queue=events)
            resp = self.listen(events)
        self.cleanup()
        # If no response given, return default response
        if not resp:
            resp = Response(None, -1)
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
            :obj:`klibs.KLResponseCollector.Response` or None: A Response object
            containing the value and reaction time (in milliseconds) of the
            response, or None if no response has been made.
        
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
    """A convenience class for collecting keypress responses.

    This listener collects keypress responses from the participant, with the
    valid response keys and their corresponding output labels being specified
    in a dictionary::

      self.key_listener = KeypressListener({
        "z": "left",
        "/": "right",
      })

    The keys in the dictionary (e.g. 'z', '/') specify which keys to watch for
    responses (other keys will be ignored). Their values (e.g. 'left', 'right')
    specify their corresponding response labels if that key is pressed during
    response collection.
    
    See the first column in `this table <https://wiki.libsdl.org/SDL2/SDL_Keycode>`_
    for a full list of valid key names.

    Args:
        keymap (dict): A dictionary specifying the keys to check for and their
            corresponding response labels.
        timeout (float, optional): The maximum duration (in seconds) to wait for a
            valid response.

    """
    def __init__(self, keymap, timeout=None):
        super(KeypressListener, self).__init__(timeout)
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

           resp = self.key_listener.collect()
           accuracy = resp.value == target
           rt = resp.rt

        If the listener times out before a response is made, the returned
        Response object will have a value of ``None`` and a reaction time of -1.

        Returns:
            :obj:`klibs.KLResponseCollector.Response`: A Response object
            containing the label and reaction time (in milliseconds) of the
            response.
        
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

        Args:
            q (list): A list of input events to check for valid key responses.

        Returns:
            :obj:`klibs.KLResponseCollector.Response` or None: A Response object
            containing the label and reaction time (in milliseconds) of the
            response, or None if no response has been made.

        """
        # Checks the input queue for any keypress events for keys in the keymap
        for event in q:
            if event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym # keyboard button event object
                if key.sym in self._keymap.keys():
                    value = self._keymap[key.sym]
                    rt = (event.key.timestamp - self._loop_start)
                    return Response(value, rt)
        return None
