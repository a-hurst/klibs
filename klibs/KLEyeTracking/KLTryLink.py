# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

from time import monotonic_ns

from klibs.KLExceptions import EyeTrackerError
from klibs.KLConstants import (LEFT_EYE, RIGHT_EYE, BINOCULAR,
    FIXATION_START, FIXATION_UPDATE, FIXATION_END, GAZE_SAMPLE,
    SACCADE_START, SACCADE_END, BLINK_START, BLINK_END)
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
        return 2000 if e.gaze else None

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
    """A mouse-based simulated eye tracker for task development and testing.

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


    def calibrate(self):
        """Enters the calibration and setup mode for the eye tracker.
        
        Does nothing in TryLink mode. 

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
        """Terminates recording and disconnects from the eye tracker.

        Called automatically whenever KLibs exits. For internal use only.

        Args:
            incomplete (bool, optional): Whether the full session was completed.
                Defaults to False.

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
        if samples:
            gaze = None if blink else (x, y)
            queue.append(MouseSample(timestamp, gaze))

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
        """Clears the event queue for emulated eye events.
        
        Any uninspected eye events will be discarded.

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


    def drift_correct(self, location=None, target=None, fill_color=None, draw_target=True):
        """Interactively checks the accuracy of the tracker's calibration.
        
        In TryLink mode, drift correct targets are presented on screen exactly as
        they are with real hardware. To perform a drift correct in TryLink mode, move
        the mouse cursor to the midpoint of the drift correct target and either press
        the space bar or click the mouse.

        Args:
            location (tuple, optional): The (x, y) pixel coordinates at which to draw
                the drift correct target. Defaults to the center of the screen.
            target (optional): A :obj:`Drawbject` or other stimulus texture to use as
                the drift correct target. Defaults to a circular target.
            fill_color (tuple, optional): The fill colour to use for the background of
                the drift correct screen. Defaults to ``P.default_fill_color``.
            draw_target (bool, optional): If True, this method will draw and present the
                drift correct target when called. If False it will not draw the target,
                allowing the use of custom drift correct screens. Defaults to True.

        Returns:
            float: The magnitude of the measured drift (in degrees of visual angle).

        """
        return EyeTracker.drift_correct(self, location, target, fill_color, draw_target)


    def gaze(self, return_integers=True, binocular_mode=RIGHT_EYE):
        """Fetches the (x,y) coordinates of the participant's gaze on the screen.
        
        In TryLink mode, this fetches the current coordinates of the mouse cursor.

        Args:
            return_integers (bool, optional): Whether to return the gaze coordinates as
                integers or floats. Defaults to True (integers).
            binocular_mode (int, optional): Tells the function which gaze coordinates
                to return for binocular samples. In TryLink mode, this has no effect.
        
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
        return float(monotonic_ns() / 1000000)


    def write(self, message):
        """Writes a message to the eye tracker's data file.
        
        Does nothing in TryLink mode.
        
        Args:
            message (str): The message to write to the eye tracker's data file.

        """
        pass


    @property
    def eye(self):
        """str: The eye(s) currently being recorded by the tracker.
        
        Always 'right' in TryLink mode.

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
        