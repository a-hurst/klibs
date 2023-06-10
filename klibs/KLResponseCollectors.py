__author__ = 'Jonathan Mulle & Austin Hurst'

import abc
from collections import namedtuple

import aggdraw
from sdl2 import SDL_GetKeyFromName, SDL_KEYDOWN, SDL_KEYUP, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP

from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import BoundaryError
from klibs.KLNamedObject import NamedObject
from klibs.KLConstants import (RC_AUDIO, RC_COLORSELECT, RC_DRAW, RC_KEYPRESS,
    NO_RESPONSE, TIMEOUT, TK_S, TK_MS)
from klibs import P
from klibs.KLKeyMap import KeyMap
from klibs.KLEventQueue import pump, flush
from klibs.KLUtilities import iterable, angle_between
from klibs.KLUserInterface import ui_request, hide_cursor, show_cursor, mouse_pos
from klibs.KLBoundary import BoundarySet, AnnulusBoundary
from klibs.KLGraphics import flip
from klibs.KLGraphics.utils import aggdraw_to_array
from klibs.KLGraphics.KLDraw import Annulus, ColorWheel, Drawbject
from klibs.KLAudio import PYAUDIO_AVAILABLE

# TODO: Add a callback that's called during collection that can end collection early
#       (e.g. for checking if gaze leaves fixation during response period)


class Response(namedtuple('Response', ['value', 'rt'])):
    """A response returned from a :class:`ResponseListener` subclass. Contains two elements: the
    response value, and the reaction time for that response value. Functions as a two-item tuple,
    except the response value and reaction time can be accessed by name using the 'value' and 'rt'
    attributes, respectively.

    For example::

        resp = Response('left', 233.4)
        value = resp[0]
        rt = resp[1]

    and::

        resp = Response('left', 233.4)
        value = resp.value
        rt = resp.rt
    
    are equivalent.

    Args:
        value: The value of the response made (e.g. the label of the key pressed, the RGBA value
            of the colour selected, the name of the boundary fixated). 
        rt (float): The reaction time for the response (in milliseconds). Usually the difference
            between the start of the response period and the collection of the response.

    """


class ResponseListener(NamedObject, EnvAgent):
    """A base class defining the essential attributes and methods required for a response listener
    class. All response listeners must inherit from this class in order to be usable with 
    :class:`ResponseCollector` objects.

    ResponseListener objects are intended to be used with :class:`ResponseCollector` objects, which
    take one or more ResponseListeners and iterate over them in a collection loop. This means that
    you can listen for and collect responses from different modalities (e.g. auditory and keypress)
    at the same time.

    Here is an example of the typical usage of a ResponseListener::

        # in setup() or setup_response_collector()
        self.rc.uses([MyResponseListener]) # Add listener to ResponseCollector
        
        # in trial()
        self.rc.collect() # Collect responses from all listeners in use
        response = self.rc.myresponse_listener.response() # Fetch collected response
    
    Note that once a ResponseListener is added to a ResponseCollector, it is assigned to an
    attribute of the ResponseCollector based on its given :attr:`name`. In the example above, the
    name of the MyResponseListener object is 'myresponse_listener', so it is accessed and
    configured through the 'myresponse_listener' attribute of the ResponseCollector.

    Args:
        name (:obj:`str`): The name of the response listener. When used within a 
            :class:`ResponseCollector` object, this will be the name of the attribute that the
            listener is assigned to (e.g. if 'name' was 'button_listener', the listener would be
            accessed through ResponseCollector.button_listener).
    
    Attributes:
        null_response: The default response value for a missing response within the listener.

    """

    def __init__(self, name):
        super(ResponseListener, self).__init__(name)
        self.responses = []
        self.null_response = NO_RESPONSE
        self.__eyetracking = False
        self.__timed_out = False
        self.__interrupts = True
        self.__min_response_count = 1
        self.__max_response_count = 1
        self._rc_start = None # The time the containing collect() loop starts

    @abc.abstractmethod
    def init(self):
        """Performs any needed preparation or sanity checking for the listener before
        the response collection loop starts (e.g. configurng hardware, ensuring all required
        settings have been provided).

        """
        pass

    def collect(self, event_queue):
        """Listens for and collects responses, unless the maximum number of responses has already
        been collected (in which case it returns immediately).
        
        This is the method called by the containing :class:`ResponseCollector`'s collection loop to
        check for responses, and calls the listener's :meth:`listen` method to collect responses.

        Args:
            event_queue (:obj:`List`): A list of input events to iterate over.

        Returns:
            bool: True if the maximum number of responses has been collected and :attr:`interrupts`
            is set to True. Otherwise, False.

        
        """
        max_collected = self.response_count == self.max_response_count
        if not max_collected:
            response = self.listen(event_queue)
            if response:
                self.responses.append(response)
        return max_collected and self.interrupts

    @abc.abstractmethod
    def listen(self, event_queue):
        """Performs the actual listening for responses. This is the only method that all
        ResponseListener subclasses *must* implement.

        Args:
            event_queue (:obj:`List`): A list of input events to iterate over.

        Returns:
            A :obj:`Response` object containing the value and reaction time of the response (if 
            one has been made), otherwise None.

        """
        pass

    @abc.abstractmethod
    def cleanup(self):
        """Performs any needed cleanup for the response listener before the containing 
        :class:`ResponseCollector`'s :meth:`ResponseCollector.collect` method returns (e.g. 
        disabling settings or external devices that were enabled in :meth:`init`).

        """
        pass

    def reset(self):
        """Resets the listener to its pre-collection state. Called by the
        :meth:`ResponseCollector.reset` method of the containing :class:`ResponseCollector`, which
        is typically called at the end of each trial.

        Should be overridden if anything other than the list of collected responses should be reset
        between trials for the listener.

        """
        self.responses = []

    def response(self, value=True, rt=True, index=0):
        """Retrieves a collected response from the listener.

        Args:
            value (bool, optional): If True, the value of the response will be returned. Defaults
                to True.
            rt (bool, optional): If True, the reaction time of the response will be returned.
                Defaults to True.
            index (int, optional): The index of the response to retrieve, if the listener is
                configured to collect multiple responses. Defaults to 0 (the first response
                collected).

        Returns:
            The value of the response if only value=True, the reaction time of the response if only
            rt=True, or a :obj:`Response` object if both are True.
        
        """
        max_index = self.max_response_count-1
        if index > max_index:
            e = "index '{0}' out of range for the listener (0-{1})"
            raise ValueError(e.format(index, max_index))
        if not value and not rt:
            raise ValueError("Why have you asked me to return nothing? Is this is a joke?")

        try:
            response = self.responses[index]
        except IndexError:
            response = Response(self.null_response, TIMEOUT)

        if value and rt:
            return response
        elif value:
            return response.value
        elif rt:
            return response.rt

    @property
    def min_response_count(self):
        """int: The minimum number of responses that the listener should produce. If fewer than
        this number of responses are collected by the listener at the end of the collection loop,
        :attr:`timed_out` will be True.

        """
        return self.__min_response_count

    @min_response_count.setter
    def min_response_count(self, count):
        if type(count) != int or count < 0 or count > self.max_response_count:
            e = "'min_response_count' must be an integer between 0 and 'max_response_count' ({0})."
            raise ValueError(e.format(self.max_response_count))
        self.__min_response_count = count

    @property
    def max_response_count(self):
        """int: The maximum number of responses that the listener can collect during the
        collection loop. If :attr:`interrupts` is set to 'True', the collection loop will end
        immediately after the listener has collected this many responses. Defaults to 1.

        """
        return self.__max_response_count

    @max_response_count.setter
    def max_response_count(self, count):
        if type(count) != int or count < 1:
            raise ValueError("'max_response_count' must be an integer greater than 1.")
        if count < self.min_response_count:
            e = "'max_response_count' cannot be less than the minimum response count ({0})."
            raise ValueError(e.format(self.min_response_count))
        self.__max_response_count = count

    @property
    def interrupts(self):
        """bool: Whether the listener should end the response collection loop immediately after
        the maximum number of responses has been collected. True by default.
        
        """
        return self.__interrupts

    @interrupts.setter
    def interrupts(self, value):
        if type(value) is bool:
            self.__interrupts = value
        else:
            raise TypeError("Property 'interrupts' must be boolean.")
    
    @property
    def response_count(self):
        """int: The number of responses collected by the listener.
        
        """
        return len(self.responses)

    @property
    def timed_out(self):
        """bool: A flag indicating if the containing :class:`ResponseCollector` timed out during
        the last collection loop before the listener was able to collect its minimum number of
        responses.

        """
        remaining = self.min_response_count - self.response_count
        return remaining > 0

    @property
    def eyetracking(self):
        """bool: Indicates whether the listener processes regular input events (e.g. mouse, 
        keyboard) or eye tracking events.
        
        """
        return self.__eyetracking
    
    @property
    def evm(self):
        # Awful hack, but needed to avoid breaking CAST for now
        return self.exp.evm


class KeyPressResponse(ResponseListener):
    """A :class:`ResponseListener` that collects key presses from the keyboard as responses, with
    the specific keys to listen for input from (and the corresponding data output associated with
    each) specified by a :attr:`key_map`.

    **ResponseCollector attribute:** 
    
    .. code-block:: python

        self.rc.keypress_listener

    **Response value:** The label of the key pressed as specified by the given :attr:`key_map`.

    **Response rt:** The time between the first refresh of the screen during the
    :meth:`ResponseCollector.collect` loop and the time when the key press was detected.

    """

    def __init__(self):
        super(KeyPressResponse, self).__init__(RC_KEYPRESS)
        self.__key_map = None

    def init(self):
        """See :meth:`ResponseListener.init`.

        """
        if not self.key_map:
            raise RuntimeError("No KeyMap configured to KeyPressResponse listener.")

    def listen(self, event_queue):
        """See :meth:`ResponseListener.listen`.

        """
        for event in event_queue:
            if event.type == SDL_KEYDOWN:
                key = event.key.keysym # keyboard button event object
                ui_request(key) # check for ui requests (ie. quit, calibrate)
                if self.key_map.validate(key.sym):
                    value = self.key_map.read(key.sym, "data")
                    rt = (self.evm.trial_time_ms - self._rc_start)
                    return Response(value, rt)
        return None

    @property
    def key_map(self):
        """dict or :obj:`KeyMap`: Specifies which keys are valid response keys, and what the data
        string for each key should be. Can be provided as a KLibs :obj:`KeyMap` object, or as a
        dict with the format::
        
            {'keyname1': 'label1', 'keyname2': 'label2'}
            
        with key names corresponding to valid SDL key names (see the 'Name' column in
        `this table <https://wiki.libsdl.org/StuartPBentley/CombinedKeyTable>`_ for a list).

        For example, if you defined the following key_map::

            self.rc.keypress_listener.key_map = {'z': "left", '/': "right"}
        
        only the 'z' and '/' keys would be watched for input and they would be recorded as 'left'
        and 'right' responses, respectively.
        
        """
        return self.__key_map

    @key_map.setter
    def key_map(self, _map):

        if type(_map) is dict:
            keycodes = []
            labels = []
            for key, label in _map.items():
                if type(key) is str:
                    keycode = SDL_GetKeyFromName(key.encode('utf8'))
                else:
                    keycode = key
                if keycode == 0:
                    raise ValueError("'{0}' is not a recognized key name.".format(key))
                keycodes.append(keycode)
                labels.append(label)
            _map = KeyMap('keypress', labels, labels, keycodes)

        elif not isinstance(_map, KeyMap):
            raise TypeError("'key_map' must be a 'KeyMap' object or a properly-formatted dict.")

        self.__key_map = _map


class AudioResponse(ResponseListener):
    """A response listener that listens for audio input above a given volume threshold.
    Intended for collecting vocal responses from a microphone.

    **ResponseCollector attribute:** 
    
    .. code-block:: python

        self.rc.audio_listener

    **Response value:** The peak loudness of the above-threshold audio sample, on a scale from 0
    to 37267.

    **Response rt:** The time between the first refresh of the screen during the
    :meth:`ResponseCollector.collect` loop and the time when the above-threshold audio sample was
    detected.

    """

    def __init__(self):
        super(AudioResponse, self).__init__(RC_AUDIO)
        self.__threshold = None
        self._stream_error = False
        if not PYAUDIO_AVAILABLE:
            e = ("The 'pyaudio' package must be installed in order to use the "
                "AudioResponse listener.")
            raise RuntimeError(e)

    def init(self):
        """See :meth:`ResponseListener.init`.

        """
        if not self.threshold:
            raise RuntimeError("A threshold must be set before audio responses can be collected.")
        self.exp.audio.stream.start()

    def listen(self, event_queue):
        """See :meth:`ResponseListener.listen`.

        """
        if self.exp.audio.stream.sample().peak >= self.threshold:
            value = self.exp.audio.stream.sample().peak
            rt = (self.evm.trial_time_ms - self._rc_start)
            return Response(value, rt)
        return None

    def cleanup(self):
        """See :meth:`ResponseListener.cleanup`.

        """
        err = self.exp.audio.reload_stream()
        if err:
            self._stream_error = True

    def reset(self):
        """See :meth:`ResponseListener.reset`.

        """
        self.responses = []
        self._stream_error = False

    @property
    def stream_error(self):
        """bool: A flag indicating whether an audio input error occurred during the last collection
        loop.
        
        If you are using an external input device to record audio (e.g. a USB Microphone) and
        the connection cuts out for an instant, the stream will continue to record but the stream
        will be completely silent, meaning that any audio responses on that trial will fail to be
        detected. You can check this flag after collection to determine if a lack of response was
        due to this problem.

        """
        return self._stream_error

    @property
    def threshold(self):
        """int: The threshold value to for collecting audio responses. Any samples with peaks
        higher than this value will be considered responses, any samples with peaks lower than this
        value will be ignored. Should be set using :meth:`klibs.KLAudio.AudioCalibrator.calibrate`.

        Raises:
            ValueError: If the threshold is not an integer between 0 and 32767.

        """
        return self.__threshold

    @threshold.setter
    def threshold(self, value):
        try:
            value = float(value)
            err = False
        except TypeError:
            err = True
        if err or not 0 < value < 37267:
            raise ValueError("Threshold must be an integer between 0 and 32767 exclusive") 
        self.__threshold = value


class MouseButtonResponse(ResponseListener):
    """A response listener that listens for presses of the mouse buttons. By default, it accepts
    any mouse button as a valid response. Optionally, a :attr:`button_map` can be provided that
    specifies which buttons to listen for input from and what their associated data labels should
    be.

    **ResponseCollector attribute:** 
    
    .. code-block:: python

        self.rc.mousebutton_listener

    **Response value:** The name of the button pressed ('left', 'right', or 'middle') if no
    :attr:`button_map` is defined, otherwise the label corresponding to the mouse button pressed. 
    If :attr:`return_coords` is True, the coordinates of the cursor at the time of 

    **Response rt:** The time between the first refresh of the screen during the
    :meth:`ResponseCollector.collect` loop and the time when the button was clicked (if 
    :attr:`on_release` is False) or when it was released (if :attr:`on_release` is True).

    """

    def __init__(self):
        super(MouseButtonResponse, self).__init__('mousebutton_listener')
        self.__event_type = SDL_MOUSEBUTTONDOWN
        self.__button_map = None
        self.__button_name_map = {1: 'left', 2: 'middle', 3: 'right'}

    def listen(self, event_queue):
        """See :meth:`ResponseListener.listen`.

        """
        for event in event_queue:
            if event.type == self.__event_type:
                b = event.button.button
                if self.__button_map:
                    if b in self.__button_map.keys():
                        value = self.__button_map[b]
                        rt = (self.evm.trial_time_ms - self._rc_start)
                        return Response(value, rt)
                else:
                    try:
                        value = self.__button_name_map[b]
                    except KeyError:
                        value = b
                    rt = (self.evm.trial_time_ms - self._rc_start)
                    return Response(value, rt)					
        return None

    @property
    def button_map(self):
        """dict or None: Specifies which mouse buttons should be considered valid responses, and
        what their corresponding data output will be.

        For example, if you defined the following button_map::

            buttonmap = {'left': "familiar", 'right': "unfamiliar"}
            self.rc.mousebutton_listener.button_map = buttonmap
        
        only the left and right mouse buttons would be watched for input and they would be recorded
        as 'familiar' and 'unfamiliar' responses, respectively.

        If no button map is specified, all mouse buttons will be considered valid responses and the
        name or number corresponding to the clicked button will be returned.
        
        """
        return self.__button_map

    @button_map.setter
    def button_map(self, _map):

        if type(_map) is not dict:
            raise TypeError('Button maps must be given as Python dictionaries.')
        if len(_map) == 0:
            raise ValueError('Button maps must contain at least one button:label pair.')

        button_map = {}
        name_to_button_id = {'left': 1, 'middle': 2, 'right': 3}
        for button, label in _map.items():
            if type(button) is str:
                try:
                    button = name_to_button_id[button]
                except KeyError:
                    err = "Mouse button names must be one of 'left', 'right', or 'middle'."
                    raise ValueError(err)
            button_map[button] = label

        self.__button_map = button_map

    @property
    def on_release(self):
        """bool: Whether presses or releases of the mouse button should be collected as responses.
        Defaults to False (i.e. on mouse button down).

        """
        return self.__event_type == SDL_MOUSEBUTTONUP

    @on_release.setter
    def on_release(self, val):
        if val == True:
            self.__event_type = SDL_MOUSEBUTTONUP
        elif val == False:
            self.__event_type = SDL_MOUSEBUTTONDOWN
        else:
            raise ValueError('Property on_release must be either True or False.')


class CursorResponse(ResponseListener, BoundarySet):
    """Listens for mouse clicks within one or more boundaries on the screen.
    
    See the documentation for the :class:`BoundarySet` class for information on how to
    add and remove boundaries from this listener.

    **ResponseCollector attribute:** 
    
    .. code-block:: python

        self.rc.cursor_listener

    **Response value:** The label of the boundary clicked, or if :attr:`return_coords` is True
    then the label along with the (x,y) coordinates of the cursor at the time of response, in the
    format ``[label, coords]``. 

    **Response rt:** The time between the first refresh of the screen during the
    :meth:`ResponseCollector.collect` loop and the time when the boundary was clicked (if 
    :attr:`on_release` is False) or when it was released (if :attr:`on_release` is True).

    Attributes:
        return_coords (bool): If True, the pixel coordinates of the cursor at the time of the
            response will be returned along with the label of the clicked boundary.


    """

    def __init__(self):
        super(CursorResponse, self).__init__('cursor_listener')
        BoundarySet.__init__(self)
        self.__event_type = SDL_MOUSEBUTTONDOWN
        self.return_coords = False

    def init(self):
        """See :meth:`ResponseListener.init`.

        """
        if len(self.boundaries) == 0:
            e = "The ClickResponse listener must contain at least one boundary to check."
            raise BoundaryError(e)
        show_cursor()

    def listen(self, event_queue):
        """See :meth:`ResponseListener.listen`.

        """
        for event in event_queue:
            if event.type == self.__event_type:
                coords = (
                    int(event.button.x * P.screen_scale_x),
                    int(event.button.y * P.screen_scale_y)
                )
                boundary = self.which_boundary(coords)
                if boundary:
                    value = [boundary, coords] if self.return_coords else boundary
                    rt = (self.evm.trial_time_ms - self._rc_start)
                    return Response(value, rt)
        return None

    def cleanup(self):
        """See :meth:`ResponseListener.cleanup`.

        """
        if not (P.development_mode and P.dm_trial_show_mouse):
            hide_cursor()

    @property
    def on_release(self):
        """bool: Whether presses or releases of the mouse button should be collected as responses.
        Defaults to False (i.e. on mouse button down).

        """
        return self.__event_type == SDL_MOUSEBUTTONUP

    @on_release.setter
    def on_release(self, val):
        if val == True:
            self.__event_type = SDL_MOUSEBUTTONUP
        elif val == False:
            self.__event_type = SDL_MOUSEBUTTONDOWN
        else:
            raise ValueError('Property on_release must be either True or False.')


class ColorWheelResponse(ResponseListener):
    """A :class:`ResponseListener` that listens for mouse button releases within the ring of a
    :obj:`ColorWheel` or :obj:`Annulus` object, and returns the angular difference between the
    location of the cursor and the location of a given target (an RGBA color or an (x,y) point
    on the screen).
    
    Useful for memory and perception research.


    **ResponseCollector attribute:** 
    
    .. code-block:: python

        self.rc.color_listener

    **Response value:** 

    +-------------------------------+---------------------------------------------------------+
    | Configuration                 | Response Value                                          |
    +===============================+=========================================================+
    |:attr:`angle_response` = True  | The angular error (in degrees) between the target and   |
    |:attr:`color_response` = False | the response on the wheel.                              |
    +-------------------------------+---------------------------------------------------------+
    |:attr:`angle_response` = False | A Tuple containing the RGBA value of the color that was |
    |:attr:`color_response` = True  | selected.                                               |
    +-------------------------------+---------------------------------------------------------+
    |:attr:`angle_response` = True  | A List containing both the angular error and the RGBA   |
    |:attr:`color_response` = True  | value of the color in the format [angle, color].        |
    +-------------------------------+---------------------------------------------------------+

    **Response rt:** The time between the first refresh of the screen during the
    :meth:`ResponseCollector.collect` loop and the time when the mouse button was released.

    Attributes:
        warp_cursor (bool): If True, the mouse cursor will be warped to the center of the response
            wheel at the start of the response period to avoid any location bias. Defaults to True.
        angle_response (bool): If True, the value of the collected :obj:`Response` will contain the
            angular difference (in degrees) between the response location and the target location. 
            Defaults to True.
        color_response (bool): If True, the value of the collected :obj:`Response` will contain the
            RGBA value of the selected colour. Will only work if the :obj:`wheel` set by 
            :meth:`set_wheel` is a :obj:`ColorWheel` object. Defauts to False.

    """

    def __init__(self):
        super(ColorWheelResponse, self).__init__(RC_COLORSELECT)
        self.__wheel = None
        self.__bounds = None
        self.__probe = None
        self.__target_loc = None
        self.warp_cursor = True
        self.angle_response = True
        self.color_response = False

    def init(self):
        """See :meth:`ResponseListener.init`.

        """
        # Do sanity checks before entering collection
        if self.__wheel == None:
            raise ValueError("No target ColorWheel or Annulus specified")
        elif isinstance(self.__wheel, Annulus) and self.color_response:
            raise ValueError("Cannot collect color responses with an Annulus target.")
        if not self.angle_response and not self.color_response:
            raise ValueError("At least one of 'angle_response' and 'color_response' must be True.")
        # Show cursor on screen and optionally warp cursor to the center of the wheel
        show_cursor()
        if self.warp_cursor:
            mouse_pos(position = self.__bounds.center)

    def listen(self, event_queue):
        """See :meth:`ResponseListener.listen`.

        """
        for e in event_queue:
            if e.type == SDL_MOUSEBUTTONUP:
                pos = (e.button.x * P.screen_scale_x, e.button.y * P.screen_scale_y)
                if not pos in self.__bounds:
                    continue
                response_angle = angle_between(pos, P.screen_c, 90, clockwise=True)
                if self.__wheel.__name__ == "ColorWheel":
                    target_color = self.__probe.fill_color
                    target_angle = self.__wheel.angle_from_color(target_color)
                else:
                    target_angle = angle_between(self.target_loc, P.screen_c, 90, clockwise=True)
                diff = target_angle - response_angle
                angle_err = diff-360 if diff > 180 else diff+360 if diff < -180 else diff
                if self.color_response:
                    color = self.__wheel.color_from_angle(response_angle)
                    value = (angle_err, color) if self.angle_response else color
                else:
                    value = angle_err
                rt = self.evm.trial_time_ms - self._rc_start
                return Response(value, rt)
        return None

    def cleanup(self):
        """See :meth:`ResponseListener.cleanup`.

        """
        if not (P.development_mode and P.dm_trial_show_mouse):
            hide_cursor()	

    def set_target(self, target):
        '''Sets the colour probe Drawbject or target location for listener, which is used to
        calculate the angular error between target and response during response collection. When
        the wheel for the listener is a Colour Wheel, a colour probe must be provided. When the
        wheel is an Annulus, a location in the form of (x, y) pixel coordinates must be provided.
        
        Note that colour probes are pass-by-refrence, meaning that you can change the fill colour
        of the probe after setting it as the target and the response collector will use whatever
        fill colour the probe has at collection time.

        Args:
            target (:obj:`Drawbject` | tuple(int,int)): A coloured shape (e.g. ellipse, asterisk)
                if using a ColorWheel for the wheel, or a tuple of (x,y) pixel coordinates
                indicating the location that the target will appear if using an Annulus for the
                wheel.

        Raises:
            ValueError: if the probe object is not a :obj:`Drawbject` or tuple.

        '''
        if isinstance(target, Drawbject):
            self.__probe = target
        elif hasattr(target, '__iter__'):
            if 0 <= target[0] <= P.screen_x and 0 <= target[1] <= P.screen_y:
                self.target_loc = target
            else:
                raise ValueError("Target location must be within the range of the screen.")
        else:
            raise ValueError("Target must either be a Drawbject or a tuple of (x,y) coordinates.")

    def set_wheel(self, wheel, location=None, registration=None):
        '''Sets the ColorWheel or Annulus object to use for response collection.

        Args:
            target (:obj:`ColorWheel` | :obj:`Annulus`): The ColorWheel or Annulus Drawbject to be
                used with the RC_COLORSELECT response collector.
            location (tuple(int, int), optional): The pixel coordinates that the target wheel will
                be blitted to during the response collection loop. Defaults to the center of the
                screen if not specified.
            registration (int, optional): The registration value between 1 and 9 that the target
                wheel will be blitted with during the response collection loop. Defaults to 5
                (center of surface) if not specified.

        Raises:
            ValueError: if the target object is not an :obj:`Annulus` or :obj:`ColorWheel`.

        '''
        if isinstance(wheel, (Annulus, ColorWheel)):
            self.__wheel = wheel
        else:
            raise ValueError("Target object must be either an Annulus or ColorWheel Drawbject.")
        # If no location or reg given, assume it's in the exact middle of the screen
        if not location:
            location = P.screen_c
        if not registration:
            registration = 5

        # Generate response boundary given registration, location and object size
        if registration in [7, 4, 1]:
            x_offset = wheel.surface_width // 2
        elif registration in [9, 6, 3]:
            x_offset = -wheel.surface_width // 2
        else:
            x_offset = 0

        if registration in [7, 8, 9]:
            y_offset = wheel.surface_width // 2
        elif registration in [1, 2, 3]:
            y_offset = -wheel.surface_width // 2
        else:
            y_offset = 0
        
        center = (location[0]+x_offset, location[1]+y_offset)
        self.__bounds = AnnulusBoundary("wheel_rc", center, wheel.radius, wheel.thickness)

    @property
    def wheel(self):
        """The :obj:`ColorWheel` or :obj:`Annulus` object being used with the listener.

        """
        return self.__wheel

    @property
    def rotation(self):
        """float: The rotation (in degrees) of the colour wheel. Should generally be set to a
        random value between 0.0 and 360.0 on each trial in order to ensure that the spatial
        locations of colours on the wheel don't bias responses.

        """
        return self.__wheel.rotation

    @rotation.setter
    def rotation(self, angle):
        self.__wheel.rotation = angle


class DrawResponse(ResponseListener, BoundarySet):
    """A response listener that collects (and optionally renders) a drawing made by the cursor
    on screen.
    
    The DrawResponse listener requires two boundaries: a :attr:`start_boundary` and a
    :attr:`stop_boundary` (they can be the same boundary). The drawing collection will start once
    the cursor leaves the start boundary, and will end once it enters the stop boundary.

    **ResponseCollector attribute:** 
    
    .. code-block:: python

        self.rc.draw_listener

    **Response value:** A :obj:`list` containing the (x,y) coordinates of all points collected
    during the drawing.

    **Response rt:** The time difference between the first and last points of the drawing.

    """

    def __init__(self):
        super(DrawResponse, self).__init__(RC_DRAW)
        BoundarySet.__init__(self)
        # Internal use variables
        self.points = []
        self.started = False
        self.stopped = False
        self.start_time = None # time of first entry into start_boundary
        self.first_sample_time = None # time of first sample outside of start_boundary
        # User-facing options
        self.start_boundary = None
        self.stop_boundary = None
        self.min_samples = 2 # minumum samples required before eligible for stop
        self.x_offset = 0
        self.y_offset = 0
        self.show_active_cursor = True
        self.show_inactive_cursor = True
        self.render_real_time = False
        self.fill = (0, 0, 0, 0)
        self.stroke_color = (255, 80, 125, 255)
        self.stroke_width = 1


    def init(self):
        """See :meth:`ResponseListener.init`.

        """
        # Do sanity checks before entering collection
        if not self.stop_boundary or not self.start_boundary:
            raise ValueError("Start and stop boundaries must be provided for draw listeners.")
        # Make cursor visible or invisible at collection start, depending on listener options
        if self.show_inactive_cursor:
            show_cursor()
        else:
            hide_cursor()


    def listen(self, event_queue=None):
        """See :meth:`ResponseListener.listen`.

        """

        mp = mouse_pos()
        if tuple(mp) in P.ignore_points_at:
            return None

        # If drawing not started, check if cursor in start boundary and start if so
        if not self.started:
            if self.within_boundary(self.start_boundary, mp):
                self.started = True
                self.start_time = self.evm.trial_time
                if self.show_active_cursor:
                    show_cursor()
                else:
                    hide_cursor()

        # If started and within stop boundary, check if stop eligible and stop if so
        elif self.within_boundary(self.stop_boundary, mp):
            if len(self.points) >= self.min_samples and not self.stopped:
                self.stopped = True
                rt = (self.points[-1][2] - self.points[0][2])
                return Response(self.points, rt)

        # Otherwise, if started and cursor not within start/stop boundaries, record drawing
        elif not self.within_boundary(self.start_boundary, mp):
            if self.first_sample_time:
                timestamp = self.evm.trial_time - self.first_sample_time
            else:
                self.first_sample_time = self.evm.trial_time
                timestamp = 0.0
            p = (mp[0] - self.x_offset, mp[1] - self.y_offset, timestamp)
            self.points.append(p)

        return None


    def reset(self):
        """See :meth:`ResponseListener.reset`.

        """
        self.responses = []
        self.points = []
        self.started = False
        self.stopped = False
        self.start_time = None
        self.first_sample_time = None


    def render_progress(self):
        """Renders the drawing so far so that it can be drawn to the screen. If less than 2 points
        have been collected or :attr:`render_real_time` is False, this returns an empty image with
        the specified :attr:`fill`.

        Returns:
            A :obj:`numpy.ndarray` equal to the size of the screen in pixels (P.screen_x_y).
        """
        test_p = aggdraw.Draw("RGBA", P.screen_x_y, self.fill)
        test_p.setantialias(True)
        if self.render_real_time and len(self.points) >= 2:
            m_str = ""
            for p in self.points:
                if m_str == "":
                    m_str = "M{0},{1}".format(p[0], p[1])
                else:
                    m_str += "L{0},{1}".format(p[0], p[1])
            s = aggdraw.Symbol(m_str)
            col = self.stroke_color
            test_p.symbol((0,0), s, aggdraw.Pen(col[:3], self.stroke_width, col[3]))
        return aggdraw_to_array(test_p)

    @property
    def active(self):
        """bool: Indicates whether a drawing is currently in progress.

        """
        return self.started and not self.stopped


class ResponseCollector(EnvAgent):
    """A container class used for collecting responses from one or more :class:`ResponseListener`
    types.

    Args:
        uses (:obj:`List` of :class:`ResponseListener` classes, optional): A list specifying the
            response listener(s) to use. See :meth:`uses` for more information.
        display_callback (:obj:`Callable` or None, optional): A callback function for redrawing the
            screen during the :meth:`collect` loop, defaults to None. See :attr:`display_callback`
            for more information.
        terminate_after (List[int, int], optional): The maximum duration of the :meth:`collect`
            loop, defaults to a timeout of 10 seconds. See :attr:`terminate_after` for more
            information.
        flip_screen (bool, optional): If True, the ResponseCollector will refresh the screen
            automatically during the :meth:`collect` loop. Defaults to False. See
            :attr:`flip_screen` for more information.

    Attributes:
        terminate_after (List[int, int]): The maximum duration of the :meth:`collect`
            loop, specified in the format ``[duration, time_unit]``, with 'duration' being a 
            positive number and 'time_unit' being one of ``TK_S`` (seconds) or ``TK_MS`` 
            (milliseconds). Defaults to a timeout of 10 seconds.
        flip_screen (bool): If True, the ResponseCollector will refresh the screen during
            :meth:`collect` immediately before entering the collection loop. If a display callback
            is set, the screen will be refreshed immediately after the display callback is called
            on every loop of collection. Defaults to False.
        end_collection_event (str): The label of a scheduled :obj:`EventManager` event that signals
            the end of the collection loop. Defaluts to None.

    """

    def __init__(self, uses=[], display_callback=None, terminate_after=[10, 0], flip_screen=False):
        super(ResponseCollector, self).__init__()

        self.__rc_index = { # For adding builtin listener types by name
            RC_AUDIO: AudioResponse,
            RC_KEYPRESS: KeyPressResponse,
            RC_COLORSELECT: ColorWheelResponse,
            RC_DRAW: DrawResponse
        }
        self.__callbacks = {
            'after_flip': [None, [], {}],
            'display': [None, [], {}],
            'before_return': [None, [], {}]
        }
        
        self.rc_start_time = None
        self.terminate_after = terminate_after
        self.end_collection_event = None

        self.display_callback = display_callback
        self.flip = flip_screen

        self.__fetch_eye_events = False
        self.__uses = [] # The object names of the ResponseListeners currently in use
        self.__name_map = {} # maps ResponseListener object names to class names
        self.listeners = {} # dict of listeners for iterating during collect()
        if len(uses):
            self.uses(uses)


    def uses(self, listeners):
        """Specifies the full list of :class:`ResponseListeners` to use during the :meth:`collect`
        loop, adding them to the ResponseCollector if they do not already exist.

        For example, to set up a ResponseCollector to listen for both audio and keypress
        responses, you would run::

            self.rc.uses([KeyPressResponse, AudioResponse])

        Once a listener has been added to a ResponseCollector, it can then be accessed and
        configured by name as an attribute of the ResponseCollector object (e.g. 
        ``self.rc.keypress_listener`` and ``self.rc.audio_listener`` for the above example,
        respectively).

        If you only wanted to collect keypress responses on some trials, you could have:::

            if self.trial_type == 'vocal_response':
                self.rc.uses([KeyPressResponse, AudioResponse])
            else:	
                self.rc.uses(KeyPressResponse)

        which would only enable the AudioResponse listener on 'vocal_response' trials.

        For legacy purposes, ResponseListeners can also be specified using the following constants:

        ================== ======================
        Constant           ResponseListener Class
        ================== ======================
        ``RC_AUDIO``       AudioResponse
        ------------------ ----------------------
        ``RC_KEYPRESS``    KeyPressResponse
        ------------------ ----------------------
        ``RC_COLORSELECT`` ColorWheelResponse
        ------------------ ----------------------
        ``RC_DRAW``        DrawResponse
        ================== ======================


        Args:
            listeners (:obj:`List` of :class:`ResponseListener` classes): A list specifying
                the :class:`ResponseListener` types to use during the :meth:`collect` loop.
        
        Raises:
            ValueError: If any of the specified listeners are not subclasses of
                :class:`ResponseListener`.

        """
        if not iterable(listeners):
            listeners = [listeners]

        self.__using = []
        self.__fetch_eye_events = False
        for l in listeners:
            if type(l) is str:
                if l not in self.__rc_index.keys():
                    raise ValueError('{0} is not a valid response type.'.format(l))
                l = self.__rc_index[l]
            try:
                if issubclass(l, ResponseListener) == False:
                    err = 'Classes passed to uses() must be subclasses of ResponseListener.'
                    raise ValueError(err)
            except TypeError:
                raise TypeError('Values passed to uses() must be either classes or strings.')

            class_name = l.__name__
            try:
                listener_name = self.__name_map[class_name]
                self.__using.append(listener_name)
            except KeyError:
                listener = l() # create listener object from listener class
                if listener.eyetracking:
                    self.__fetch_eye_events = True
                    if not P.eye_tracking:
                        err = "Eye tracking must be enabled in order to use the {0} listener."
                        raise RuntimeError(err.format(class_name))
                self.__name_map[class_name] = listener.name
                self.__using.append(listener.name)
                self.listeners[listener.name] = listener
                setattr(self, listener.name, listener)


    def using(self, listener=None):
        """Indicates which :class:`ResponseListener` types are currently in use.

        Args:
            listener (:obj:`str`, optional): The name of a listener to check the use status of. If
                no listener name is provided, the full list of in-use listeners will be returned.

        Returns:
            A :obj:`list` containing the names of the listeners currently in use, or alternatively
            a boolean indicating whether the given listener name matches the name of any listener
            being used.

        """
        if listener:
            return listener in self.__using
        else:
            return self.__using


    def collect(self):
        """Collects responses from all listeners currently in use. This function will loop over all
        the listeners in use until either:
        
        1. The maximum number of responses has been made for a listener where
           :attr:`ResponseListener.interrupts` has been set to True,

        2. The event specified by :attr:`end_collection_event` has occured, or

        3. The amount of time specified by :attr:`terminate_after` has passed since the start of
           the collection loop.


        The 'collect' loop makes use of three optional callbacks: a :attr:`display_callback`, an
        :attr:`after_flip_callback`, and a :attr:`before_return_callback`:
        
        - The **display callback** is called at the start of every pass of the collection loop.
          It is used for updating the contents of the screen while listening for responses.

        - The **after-flip callback** is called once, immediately after the first refresh of the
          screen at the beginning of the collection loop.

        - The **before-return callback** is called once, immediately after the collection loop ends
          due to an interrupting listener, an end_collection_event, or a timeout.

        The latter two are primarily intended for sending messages to devices (e.g. an EEG
        amplifier) with precise timing during the response collection loop.


        Once the collection loop has ended, the collected responses from each listener can be
        retrieved using each listener's :meth:`ResponseListener.response` method::

            # if using the AudioResponse and KeyPressResponse listeners
            self.rc.collect()
            key_response, key_rt = self.rc.keypress_listener.response()
            vocal_rt = self.rc.audio_listener.response(value=False)

        """
        if len(self.using()) == 0:
            raise RuntimeError("Nothing to collect; no response listener(s) enabled.")

        # Clear event queue and do any needed prep work for response listeners in use
        flush()
        for l in self.using():
            self.listeners[l].init()

        if callable(self.display_callback):
            self.display_callback(*self.display_args, **self.display_kwargs)
        if self.flip:
            flip()
        if callable(self.after_flip_callback):
            self.after_flip_callback(*self.after_flip_args, **self.after_flip_kwargs)
        
        # Set collection start time for calculating RTs later, enter collection loop
        self.rc_start_time = self.exp.evm.trial_time_ms
        for l in self.using():
            self.listeners[l]._rc_start = self.rc_start_time
        self.__collect()

        # before return callback
        if callable(self.before_return_callback):
            self.before_return_callback(*self.before_return_args, **self.before_return_kwargs)

        # Do any needed cleanup for response listeners and reset start time before returning
        for l in self.using():
            self.listeners[l]._rc_start = None
            self.listeners[l].cleanup()


    def __collect(self):

        collecting = True
        while collecting:

            e_queue = pump(True) # Fetch input event queue
            el_queue = self.el.get_event_queue() if self.__fetch_eye_events else None

            # Check if response collection has timed out or end collection event has occurred
            if self.end_collection_event:
                if self.exp.evm.after(self.end_collection_event):
                    break
            else:
                t = self.exp.evm.trial_time_ms
                timeout = self.terminate_after[0]
                if self.terminate_after[1] == TK_S: timeout *= 1000.0
                if t > (self.rc_start_time + timeout):
                    for listener in self.using():
                        l = self.listeners[listener]
                        if P.development_mode and l.response_count < l.min_response_count:
                            msg = "Response collection for {0} timed out after {1}s."
                            print(msg.format(l.name, timeout/1000.0))
                    break

            # Check event queue for UI requests if not already processing keypress responses
            if not self.using(RC_KEYPRESS):
                ui_request(queue=e_queue)

            # Check all active listeners for responses
            for l in self.using():
                q = el_queue if self.listeners[l].eyetracking else e_queue
                interrupt = self.listeners[l].collect(q)
                if interrupt:
                    collecting = False
                    break

            # Run display callback function, if one has been specified
            if callable(self.display_callback):
                self.display_callback(*self.display_args, **self.display_kwargs)
                if self.flip:
                    flip()


    def reset(self):
        """Resets all listeners in the collector to their pre-collection state, clearing any
        collected responses and resetting any other flags or attributes set during collection.

        Called automatically at the end of every trial for the default ``self.rc``
        ResponseCollector, but will need to be called manually for any other ResponseCollector
        objects.
        
        """
        for listener in self.listeners.values():
            listener.reset()


    # Callback setters/getters and related methods for the collect() loop

    def __set_callback(self, name, callback):
        if callback != None and not callable(callback):
            raise TypeError("Property '{0}_callback' must be a callable function.".format(name))
        self.__callbacks[name][0] = callback
    
    def __set_callback_args(self, name, args):
        if type(args) not in (list, tuple):
            raise TypeError("Property '{0}_args' must be a list or a tuple.".format(name))
        self.__callbacks[name][1] = args

    def __set_callback_kwargs(self, name, kwargs):
        if type(kwargs) is not dict:
            raise TypeError("Property '{0}_kwargs' must be a dict.".format(name))
        self.__callbacks[name][2] = kwargs


    @property
    def display_callback(self):
        """An optional function for drawing stimuli to the screen during the :meth:`collect` loop.
        If a display callback is specified, it will be run at the start of every pass of the
        collection loop.

        .. note:: If the display callback function does not call the :func:`KLGraphics.flip`
                  function itself, :attr:`flip` must be set to True for the callback to be drawn to
                  the display.
        
        """
        return self.__callbacks['display'][0]

    @display_callback.setter
    def display_callback(self, callback):
        self.__set_callback('display', callback)

    @property
    def display_args(self):
        """:obj:`list`: A list of positional arguments (\*args) to pass to the display callback
        function. See `here <https://www.agiliq.com/blog/2012/06/understanding-args-and-kwargs/>`_
        for an explanation of how \*args work in Python.

        """
        return self.__callbacks['display'][1]

    @display_args.setter
    def display_args(self, args):
        self.__set_callback_args('display', args)

    @property
    def display_kwargs(self):
        """:obj:`dict`: A list of keyword arguments (\*\*kwargs) to pass to the display callback
        function. See `here <https://www.agiliq.com/blog/2012/06/understanding-args-and-kwargs/>`_
        for an explanation of how \*\*kwargs work in Python.

        """
        return self.__callbacks['display'][2]

    @display_kwargs.setter
    def display_kwargs(self, kwargs):
        self.__set_callback_kwargs('display', kwargs)


    @property
    def after_flip_callback(self):
        """An optional callback function that is run immediately after the first flip of the screen
        (and just before the response period start time is set) within the :meth:`collect` loop.

        Can be used for sending messages or codes to external hardware (e.g. EEG amplifiers,
        eye trackers) to let them know exactly when the response period has started.
        
        """
        return self.__callbacks['after_flip'][0]

    @after_flip_callback.setter
    def after_flip_callback(self, callback):
        self.__set_callback('after_flip', callback)

    @property
    def after_flip_args(self):
        """:obj:`list`: A list of positional arguments (\*args) to pass to the after_flip callback
        function. See `here <https://www.agiliq.com/blog/2012/06/understanding-args-and-kwargs/>`_
        for an explanation of how \*args work in Python.

        """
        return self.__callbacks['after_flip'][1]

    @after_flip_args.setter
    def after_flip_args(self, args):
        self.__set_callback_args('after_flip', args)

    @property
    def after_flip_kwargs(self):
        """:obj:`dict`: A list of keyword arguments (\*\*kwargs) to pass to the after_flip callback
        function. See `here <https://www.agiliq.com/blog/2012/06/understanding-args-and-kwargs/>`_
        for an explanation of how \*\*kwargs work in Python.

        """
        return self.__callbacks['after_flip'][2]

    @after_flip_kwargs.setter
    def after_flip_kwargs(self, kwargs):
        self.__set_callback_kwargs('after_flip', kwargs)


    @property
    def before_return_callback(self):
        """An optional callback function that is run immediately after the :meth:`collect`
        collection loop ends (either due to a listener interrupting or the loop timing out).

        Can be used for sending messages or codes to external hardware (e.g. EEG amplifiers,
        eye trackers) to let them know exactly when the response period has ended.
        
        """
        return self.__callbacks['before_return'][0]

    @before_return_callback.setter
    def before_return_callback(self, callback):
        self.__set_callback('before_return', callback)

    @property
    def before_return_args(self):
        """:obj:`list`: A list of positional arguments (\*args) to pass to the before_return
        callback function.
        See `here <https://www.agiliq.com/blog/2012/06/understanding-args-and-kwargs/>`_ for an
        explanation of how \*args work in Python.

        """
        return self.__callbacks['before_return'][1]

    @before_return_args.setter
    def before_return_args(self, args):
        self.__set_callback_args('before_return', args)

    @property
    def before_return_kwargs(self):
        """:obj:`dict`: A list of keyword arguments (\*\*kwargs) to pass to the before_return
        callback function.
        See `here <https://www.agiliq.com/blog/2012/06/understanding-args-and-kwargs/>`_ for an
        explanation of how \*\*kwargs work in Python.

        """
        return self.__callbacks['before_return'][2]

    @before_return_kwargs.setter
    def before_return_kwargs(self, kwargs):
        self.__set_callback_kwargs('before_return', kwargs)
