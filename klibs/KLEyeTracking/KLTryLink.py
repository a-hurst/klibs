# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

from klibs.KLExceptions import EyeTrackerError
from klibs.KLConstants import (LEFT_EYE, RIGHT_EYE, BINOCULAR,
    FIXATION_START, FIXATION_UPDATE, FIXATION_END, GAZE_SAMPLE,
    SACCADE_START, SACCADE_END, BLINK_START, BLINK_END, 
    EL_GAZE_START, EL_GAZE_END, EL_GAZE_AVG, EL_TIME_START, EL_TIME_END,
    EL_ALL_EVENTS, EL_TRUE, EL_FALSE,
    TK_S, TK_MS)
from klibs import P
from klibs.KLUtilities import now, line_segment_len, px_to_deg
from klibs.KLBoundary import CircleBoundary
from klibs.KLEventQueue import pump, flush
from klibs.KLUserInterface import (
    ui_request, mouse_pos, mouse_clicked, key_pressed, show_cursor, hide_cursor
)
from klibs.KLEyeTracking.KLEyeTracker import EyeTracker, EventParser
from klibs.KLEyeTracking.utils import GazeEventGenerator

from sdl2 import SDL_GetTicks, SDL_Delay
from sdl2.ext import cursor_hidden, mouse_button_state


class MouseSample():
    """A simulated gaze sample event. For internal TryLink use.

    Args:
        time (int): The time that the sample was recorded.
        gaze (Tuple(float, float)): The (x, y) gaze coordinates of the sample.
    
    Attributes:
        type (int): The type code of the event (i.e. ``GAZE_SAMPLE``).

    """
    def __init__(self, time, gaze):
        self.type = GAZE_SAMPLE
        self.time = time
        self.gaze = gaze


class TryLinkEventParser(EventParser):
    """A parser defining how to extract data from simulated tracker events.

    """
    def get_type(self, e):
        """Retrieves the type of a given event (e.g. ``BLINK_START``).
        """
        return e.type

    def eye(self, e):
        """Retrieves the eye for a given event.
        """
        return RIGHT_EYE

    def timestamp(self, e):
        """Gets the timestamp (in msec) for a gaze sample.
        """
        return e.time

    def left_gaze(self, e):
        """Gets the left eye (x, y) gaze coordinates for a gaze sample.
        """
        return None

    def right_gaze(self, e):
        """Gets the right eye (x, y) gaze coordinates for a gaze sample.
        """
        return e.gaze

    def left_pupil_size(self, e):
        """Gets the left eye pupil size (arbitrary units) for a gaze sample.
        """
        return None

    def right_pupil_size(self, e):
        """Gets the right eye pupil size (arbitrary units) for a gaze sample.
        """
        return 2000

    def start_time(self, e):
        """Gets the timestamp (in msec) for the start of the event.
        """
        return e.start_time

    def end_time(self, e):
        """Gets the timestamp (in msec) for the end of the event.
        """
        return e.end_time

    def start_gaze(self, e):
        """Gets the (x, y) gaze coordinates at the start of the event.
        """
        return e.start_gaze

    def end_gaze(self, e):
        """Gets the (x, y) gaze coordinates at the end of the event.
        """
        return e.end_gaze

    def avg_gaze(self, e):
        """Gets the average (x, y) gaze coordinates for the event.
        """
        return e.avg_gaze

    def duration(self, e):
        """Gets the total duration (in msec) for the event.
        """
        return e.end_time - e.start_time


class TryLink(EyeTracker):
    """A simulated eye tracker, using the position and movements of the mouse cursor as a stand-in
    for gaze position and saccades/fixations. Used for developing, testing, and demoing experiments
    that require an eye tracker without the need to have eye tracking hardware present.

    TryLink simulation is used by default if the 'pylink' Python package is not installed, or if
    ``P.eye_tracking`` is True but ``P.eye_tracker_availiable`` is False. In addition, TryLink
    simulation can be forced by adding the flag ``-ELx`` to the ``klibs run`` command when
    launching an experiment.

    For more general and comprehensive documentation, see the :class:`~.EyeTracker` class.

    Attributes:
        version (str): The model name and software version of the eye tracker.
        initialized (bool): A flag indicating whether :meth:`setup` has been run successfully.
        local_start_time (float): The time at which the tracker last started recording, according
            to the local computer's clock.
        tracker_start_time (float): The time at which the tracker last started recording, according
            to the eye tracker's internal clock.

    """

    def __init__(self):
        EyeTracker.__init__(self)
        self.version = None
        self.initialized = False
        self.local_start_time = None
        self.tracker_start_time = None
        self._recording = False
        self._generator = GazeEventGenerator()
        self._parser = TryLinkEventParser()


    def _setup(self):
        """The mouse simulation specific part of the setup process.
        
        """
        self.version = "TryLink 0.1a"


    def setup(self):
        EyeTracker.setup(self) # so it shows up in the docs


    def calibrate(self):
        """Enters the calibration and setup mode for the eye tracker. Does nothing in TryLink mode. 

        """
        pass


    def start(self, trial_number):
        """Starts recording simulated eye events from the mouse cursor.
        
        Called automatically at the start of each trial unless ``P.manual_eyelink_recording`` is
        True, in which case it must be called manually in order to start recording eye events and
        gaze position from the eye tracker. To stop recording after this method is called, use the
        :meth:`stop` method.

        Args:
            trial_number (int): The current trial number. Used to mark the start of the trial in
                the data files of eye trackers that support data markup.

        """
        self.local_start_time = now()
        self._recording = True
        self.tracker_start_time = self.now()
        return 0


    def stop(self):
        """Stops recording simulated eye events from the mouse cursor.
        
        Called automatically at the end of each trial unless ``P.manual_eyelink_recording`` is
        True, in which case it must be called manually in order to stop recording at any point.
        To resume recording after this method is called, use the :meth:`start` method.

        """
        self._generator.reset()
        self._recording = False


    def shut_down(self, incomplete=False):
        """Terminates recording and disconnects from the eye tracker, putting it into standby mode.
        Should also transfer any data files from the current session to the KLibs computer
        from the tracker (e.g. EDF files). Does nothing when using TryLink simulation.

        Called automatically whenever KLibs exits. For internal use only.

        Args:
            incomplete (bool, optional): Whether the full session was completed before the function
                was called. Has no effect in TryLink simulation mode. Defaults to False.

        """
        self.stop()
        return 0


    def _get_tracker_events(self, events, samples=False):
        """Internal method for retrieving eye events from the tracker.

        Args:
            events (list): A list of the desired event types to retrieve.
            samples (bool): Whether gaze samples should be returned in addition to other
                event types.

        Returns:
            list: A list of tracker-specific events.

        """
        timestamp = self.now()
        x, y = self.gaze()
        mouse_clicked = mouse_button_state().any_pressed
        blink = P.dm_click_to_blink and mouse_clicked
        if blink:
            # Simulate blink if mouse button pressed
            x, y = (None, None)

        queue = []
        self._generator.update(x, y, timestamp)
        for e in self._generator.get_events():
            if e.type in events:
                queue.append(e)
        if samples and not blink:
            # NOTE: Check whether tracker sends gaze samples during blinks
            queue.append(MouseSample(timestamp, (x, y)))

        return queue


    def get_event_queue(self, include=[], exclude=[]):
        """Fetches and returns the eye tracker's event queue, emptying it in the process. 
        
        In TryLink simulation mode, this uses some fancy voodoo with mouse cursor movement to
        produce eye events, allowing you to write and test your eye tracking code on any computer
        without needing physical access to an eye tracker itself.

        Returns:
            A :obj:`List` of simulated eye events.

        """
        return EyeTracker.get_event_queue(self, include, exclude) # so it shows up in the docs


    def clear_queue(self):
        """Clears the event queue for emulated eye events. Any uninspected eye events will be
        discarded.

        """
        self._generator.reset()


    def _drift_correct(self, loc, target_callback):
        """Internal hardware-specific method for performing drift correction.

        This implementation allows for mouse clicks as well as space bar presses
        for performing drift corrections.

        """
        flush()
        mouse_hidden = cursor_hidden()
        show_cursor()

        space_pressed = False
        dist_px = 0.0  # magnitude of drift correct error (in pixels)
        dc_boundary = CircleBoundary('dc_target', loc, P.screen_y // 30)
        done = False
        while not done:
            SDL_Delay(2) # required for pump() to reliably return mousebuttondown events
            q = pump(True)
            ui_request(queue=q)
            mouse_xy = mouse_pos(False)
            if mouse_xy in dc_boundary:
                if mouse_clicked(released=True, queue=q):
                    dist_px = line_segment_len(mouse_xy, loc)
                    done = True
                elif key_pressed(' ', queue=q):
                    space_pressed = True
                elif key_pressed(' ', released=True, queue=q):
                    # Ignore key release unless we also logged the key press
                    # (prevents trial ended by space press from skipping DC)
                    if space_pressed:
                        dist_px = line_segment_len(mouse_xy, loc)
                        done = True

        if mouse_hidden:
            hide_cursor()

        return round(px_to_deg(dist_px), 2)


    def gaze(self, return_integers=True, binocular_mode=RIGHT_EYE):
        """Fetches the (x,y) coordinates of the participant's current gaze on the screen. In
        TryLink mode, this fetches the current coordinates of the mouse cursor.

        Args:
            return_integers (bool, optional): Whether to return the gaze coordinates as integers
                or floats. Defaults to True (integers).
            binocular_mode (int, optional): Tells the function which gaze coordinates to return
                for binocular samples. Can be any of ``RIGHT_EYE`` (returns right eye gaze),
                ``LEFT_EYE`` (returns left eye gaze), or ``BINOCULAR`` (returns average gaze
                of both eyes). Defaults to ``RIGHT_EYE``. In TryLink mode, this has no effect.
        
        Returns:
            A :obj:`Tuple` containing the (x,y) pixel coordinates of the participant's gaze.

        """
        gaze_pos = mouse_pos()
        return gaze_pos if return_integers else tuple(float(p) for p in gaze_pos)


    def now(self):
        """Fetches the current time according to the tracker's internal clock.

        Returns:
            float: The current tracker time (in milliseconds).

        """
        return float(SDL_GetTicks())


    def write(self, message):
        """Writes a message to the eye tracker's data file. In TryLink mode, this method
        does nothing.
        
        Args:
            message (str): The message to write to the eye tracker's data file.

        """
        pass


    @property
    def eye(self):
        """str or None: The eye(s) currently being recorded by the tracker. Can be 'left', 'right',
        'both', or None (if no eye is currently available). Always the right eye in TryLink mode.

        """
        return 'right'


    @property
    def in_setup(self):
        """bool: Whether the eye tracker is currently in setup/calibration mode.
        
        Always False when using TryLink simulation.

        """
        return False


    @property
    def recording(self):
        """bool: Whether the eye tracker is currently recording data.

        """
        return self._recording
        