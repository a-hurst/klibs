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
from klibs.KLUtilities import iterable, pretty_list
from klibs.KLBoundary import BoundarySet
from klibs.KLGraphics import blit, fill, flip
from klibs.KLGraphics.KLDraw import drift_correct_target

# TODO: Add way of specifying calibration type (e.g. 'HV9') in params


class EyeTracker():
    """A base eye tracker class, laying out the essential attributes and methods required for an
    eye tracker to be used with KLibs.
    
    Primarily used for defining a common and unified API for both SR Research EyeLink eye trackers
    (via pylink) and eye tracker emulation via the mouse cursor, but hopefully flexible enough to
    allow for supporting additional eye tracker brands/models in the future.

    Attributes:
        version (str): The model name and software version of the eye tracker.
        initialized (bool): A flag indicating whether :meth:`setup` has been run successfully.
        local_start_time (float): The time at which the tracker last started recording, according
            to the local computer's clock.
        tracker_start_time (float): The time at which the tracker last started recording, according
            to the eye tracker's internal clock.

    """

    def __init__(self):
        self.version = None
        self.initialized = False
        self.local_start_time = None
        self.tracker_start_time = None
        self.boundaries = BoundarySet()
        self._recording = False
        self._unresolved_exceptions = 0
        self._quitting = False
        self._el = None
        self._event_names = {
            GAZE_SAMPLE: 'gaze position',
            BLINK_START: 'blink start',
            BLINK_END: 'blink end',
            SACCADE_START: 'saccade start',
            SACCADE_END: 'saccade end',
            FIXATION_START: 'fixation start',
            FIXATION_END: 'fixation end',
            FIXATION_UPDATE: 'fixation update'
        }
        self._event_defaults = {
            GAZE_SAMPLE: [None, None],
            SACCADE_START: [EL_TIME_START, EL_GAZE_START],
            SACCADE_END: [EL_TIME_END, EL_GAZE_END],
            FIXATION_START: [EL_TIME_START, EL_GAZE_START],
            FIXATION_END: [EL_TIME_END, EL_GAZE_AVG],
            FIXATION_UPDATE: [EL_TIME_END, EL_GAZE_AVG]            
        }


    def _within_boundary(self, label, event, report, inspect):
        """Checks whether an event is within a boundary. For internal use.

        Args:
            label (str): The label of the boundary to check if the event is in, added using
                add_boundary().
            event: The eye event (e.g. saccade, fixation, gaze sample) to test against the
                given boundary.
            report: A flag indicating whether to report the start time (``EL_TIME_START``) or
                end time (``EL_TIME_END``) of the eye event.
            inspect: A flag indicating which gaze attribute of the eye event should be checked
                against the boundary: the gaze at the start of the event (``EL_GAZE_START``),
                the gaze at the end of the event (``EL_GAZE_END``), or the event's average gaze
                (``EL_GAZE_AVG``). Note that not all eye events have all three gaze attributes.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if the
            inspected region was within the specified boundary, otherwise False.

        """
        timestamp = self.get_event_timestamp(event, report)
        gaze_coords = self.get_event_gaze(event, inspect)

        result = self.boundaries.within_boundary(label, gaze_coords)
        return timestamp if result else False


    def _exited_boundary(self, label, event, report):
        """Checks whether a saccade event exited a given boundary. For internal use.

        Args:
            label (str): The label of the boundary to check if the event is in, added using
                add_boundary().
            event: The saccade-end event to test against the given boundary.
            report: A flag indicating whether to report the start time (``EL_TIME_START``) or
                end time (``EL_TIME_END``) of the saccade.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if the
            saccade exited the given boundary, otherwise False.

        """
        e_type = self.get_event_type(event)
        if e_type != SACCADE_END:
            typename = self.get_event_name(e_type)
            err = "Only saccade end events can be used for boundary exit tests ({0} given)"
            raise EyeTrackerError(err.format(typename))

        timestamp = self.get_event_timestamp(event, report)
        start_gaze = self.get_event_gaze(event, EL_GAZE_START)
        end_gaze = self.get_event_gaze(event, EL_GAZE_END)

        start_inside = self.boundaries.within_boundary(label, start_gaze)
        end_inside = self.boundaries.within_boundary(label, end_gaze)
        return timestamp if (start_inside and not end_inside) else False


    def _saccade_in_direction(self, doi, event, report):
        """Checks whether a saccade event occurred in a given direction. For internal use.

        Args:
            doi (:obj:`List` of str): The names of the direction(s) of interest to watch for
                saccades in. Both a vertical ('up' or 'down') or horizontal ('left' or 'right')
                direction of interest can be specified.
            event: The saccade-end event to check the direction of.
            report: A flag indicating whether to report the start time (``EL_TIME_START``) or
                end time (``EL_TIME_END``) of the saccade.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if the
            saccade direction matched all the given directions of interest, otherwise False.
                
        """
        e_type = self.get_event_type(event)
        if e_type != SACCADE_END:
            typename = self.get_event_name(e_type)
            err = "Only saccade end events can be used for saccade direction tests ({0} given)"
            raise EyeTrackerError(err.format(typename))
            
        sxp, syp = self.get_event_gaze(event, EL_GAZE_START)
        exp, eyp = self.get_event_gaze(event, EL_GAZE_END)
        sacc_direction = [None, None]
        sacc_direction[0] = "right" if (exp - sxp) > 0 else "left"
        sacc_direction[1] = "down"  if (eyp - syp) > 0 else "up"
        timestamp = self.get_event_timestamp(event, report)
        
        # Check if the direction(s) of interest match the direction of the saccade
        result = all(direction in sacc_direction for direction in doi)
        return timestamp if result else False


    def _setup(self):
        """The eye tracker specific part of the setup process. This, not 'setup()', should be
        overridden by any eye trackers that subclass the EyeTracker class.

        Note: within this method, self.version must be set to a string containing the name/model
        of the eye tracker.

        """
        pass


    def setup(self):
        """Initalizes and sets up the eye tracker for the first time.
        
        Called automatically after demographics collection during experiment launch unless
        ``P.manual_eyelink_setup`` is True, in which case it must be called manually
        before the eye tracker is first used in the experiment.

        """
        from klibs.KLEnvironment import db
        self._setup()
        if P.demographics_collected and 'session_info' in db.table_schemas:
                db.update('session_info', {'eyetracker': self.version})
        self.calibrate()
        self.initialized = True


    def calibrate(self):
        """Enters the calibration and setup mode for the eye tracker.
        
        If the eye tracker does not have a setup/calibration mode, this function does nothing. 

        """
        pass


    def start(self, trial_number):
        """Tells the eye tracker to start recording data.
        
        Called automatically at the start of each trial unless ``P.manual_eyelink_recording`` is
        True, in which case it must be called manually in order to start recording eye events and
        gaze position from the eye tracker. To stop recording after this method is called, use the
        :meth:`stop` method.

        Args:
            trial_number (int): The current trial number. Used to mark the start of the trial in
                the data files of eye trackers that support data markup.

        """
        self._recording = True


    def stop(self):
        """Stops recording data from the eye tracker.
        
        Called automatically at the end of each trial unless ``P.manual_eyelink_recording`` is
        True, in which case it must be called manually in order to stop recording at any point. 
        To resume recording after this method is called, use the :meth:`start` method.

        """
        self._recording = False


    def shut_down(self, incomplete=False):
        """Terminates recording and disconnects from the eye tracker, putting it into standby mode.
        Should also transfer any data files from the current session to the KLibs computer
        from the tracker (e.g. EDF files).

        Called automatically whenever KLibs exits. For internal use only.

        Args:
            incomplete (bool, optional): Whether the full session was completed before the function
                was called. If True, any tracker data files will be written to an 'incomplete'
                subfolder of the eye tracker data directory ('ExpAssets/EDF'). Defaults to False.

        """
        pass


    def get_event_queue(self, include=[], exclude=[]):
        """Fetches and returns the eye tracker's event queue, emptying it in the process.

        To avoid problems with event processing when performing multiple tests in a short interval
        (e.g. checking for fixations in multiple boundaries every iteration of a loop), you should
        use this method to retrieve the eye tracker event queue once at the start and then pass it
        to every function that inspects eye events.
        
        For example, the following code will not reliably detect saccades to the second boundary::

            while self.evm.before('cue_on'):
                draw_stimuli()
                if self.el.saccade_to_boundary('boundary1'):
                    print('saccade to boundary 1!')
                if self.el.saccade_to_boundary('boundary2'):
                    print('saccade to boundary 2!')
                flip() # refresh screen

        This is because the first call to :meth:`saccade_to_boundary` fetches and clears the eye
        event queue, meaning that the second call is only processing the saccades that have
        happened in the tiny interval since the first call. To fix this, you should fetch the
        queue once per loop::

            while self.evm.before('cue_on'):
                draw_stimuli()
                el_q = self.el.get_event_queue() # fetch queue once per loop
                if self.el.saccade_to_boundary('boundary1', event_queue=el_q):
                    print('saccade to boundary 1!')
                if self.el.saccade_to_boundary('boundary2', event_queue=el_q):
                    print('saccade to boundary 2!')
                flip() # refresh screen

        Args:
            include (:obj:`List`, optional): A list specifying the types of eye events to fetch
                from the event queue. Includes all eye event types by default, unless they are
                explicitly excluded.
            exclude (:obj:`List`, optional): A list specifying the types of eye events to exclude
                from the returned queue. Defaults to an empty list (i.e. no events excluded.)

        Returns:
            A :obj:`List` of eye events.

        """
        pass


    def clear_queue(self):
        """Clears the event queue for the eye tracker. Any uninspected eye events will be
        discarded.

        """
        pass

    
    def add_boundary(self, boundary, bounds=None, shape=None):
        """Adds a boundary to the tracker.
    
        Args:
            boundary (:obj:`~klibs.KLBoundary.Boundary`): A Boundary object to add to
                the tracker.
        
        """
        # NOTE: Not documenting further for now since I'm unsure of this API apart from
        # backwards compat
        self.boundaries.add_boundary(boundary, bounds, shape)


    def clear_boundaries(self, preserve=[]):
        """Removes all boundaries from the tracker.

        Args:
            preserve (:obj:`List`, optional): A list containing the labels of any
                boundaries that should remain in the set after the clear.

        Raises:
            KeyError: If any label does not correspond to a boundary within the set.

        """
        self.boundaries.clear_boundaries(preserve)


    def within_boundary(self, label, valid_events, event_queue=None):
        """Checks whether an eye event has occurred within a given boundary.

        This method tests the most relevant gaze attribute of each event type against
        the given boundary. The gaze coordinates inspected for each eye event type are
        listed in the follow table:

        +---------------------+-------------------------------+
        | Valid Events        | Inspected Gaze Coordinates    |
        +=====================+===============================+
        | ``GAZE_SAMPLE``     | Gaze (right eye if binocular) |
        +---------------------+-------------------------------+
        | ``SACCADE_START``   | Gaze at saccade onset         |
        +---------------------+-------------------------------+
        | ``SACCADE_END``     | Gaze at saccade end           |
        +---------------------+-------------------------------+
        | ``FIXATION_START``  | Gaze at fixation onset        |
        +---------------------+-------------------------------+
        | ``FIXATION_END``    | Average gaze during fixation  |
        +---------------------+-------------------------------+
        | ``FIXATION_UPDATE`` | Average gaze during fixation  |
        +---------------------+-------------------------------+

        If an event queue is not provided, this method will retrieve and empty the event
        queue from the tracker.

        Args:
            label (str): The label of the boundary of interest (e.g. 'fixation').
            valid_events (:obj:`List`): A list of constants indicating the event type(s)
                to process.
            event_queue (:obj:`List`, optional): A queue of eye events returned from
                :meth:`get_event_queue`.

        Returns:
            bool: True if any valid eye events fell within the boundary,
            otherwise False.

        """
        if valid_events in EL_ALL_EVENTS or valid_events == GAZE_SAMPLE:
            valid_events = [valid_events]
        if any(e in [BLINK_START, BLINK_END] for e in valid_events):
            raise ValueError("Cannot inspect the gaze coordinates of blink events.")
        if not event_queue:
            event_queue = self.get_event_queue(valid_events)

        timestamp = None
        for e in event_queue:
            if e == None or self.get_event_type(e) not in valid_events:
                continue
            e_type = self.get_event_type(e)
            _report = self._event_defaults[e_type][0]
            _inspect = self._event_defaults[e_type][1]
            timestamp = self._within_boundary(label, e, _report, _inspect)
            if timestamp:
                return True

        return False


    def fixated_boundary(self, label, valid_events=FIXATION_START, event_queue=None):
        """Checks whether a specified boundary has been fixated.

        By default, this method checks the event queue for any fixation start events
        that occurred within the boundary. However, ``FIXATION_UPDATE`` and
        ``FIXATION_END`` events can also be tested against a boundary.
        
        If an event queue is not provided, this method will retrieve and empty the event
        queue from the tracker.

        Args:
            label (str): The label of the boundary of interest (e.g. 'fixation').
            valid_events (:obj:`List`, optional): A list of constants indicating the
                fixation event type(s) to process.
            event_queue (:obj:`List`, optional): A queue of eye events returned from
                :meth:`get_event_queue`.

        Returns:
            bool: True if the boundary was fixated, otherwise False.

        """
        if not iterable(valid_events):
            valid_events = [valid_events]

        for e_type in valid_events:
            if e_type not in (FIXATION_START, FIXATION_END, FIXATION_UPDATE):
                raise ValueError("Valid events for fixated_boundary must be fixation events.")

        return self.within_boundary(label, valid_events, event_queue) 


    def saccade_to_boundary(self, label, event_queue=None):
        """Checks whether any saccades have entered a given boundary.

        For a saccade to count as entering a boundary, it must begin outside the
        boundary and end inside of it. If an event queue is not provided, this method
        will retrieve and empty the event queue from the tracker.

        Args:
            label (str): The label of the boundary of interest (e.g. 'fixation').
            event_queue (:obj:`List`, optional): A queue of eye events returned from
                :meth:`get_event_queue`.

        Returns:
            bool: True if any saccades entered the boundary, otherwise False.

        """
        if not event_queue:
            event_queue = self.get_event_queue([SACCADE_END])
        if not len(event_queue):
            return False

        for e in event_queue:
            if e == None or self.get_event_type(e) != SACCADE_END:
                continue
            started_within = self._within_boundary(label, e, EL_TIME_START, EL_GAZE_START)
            ended_within = self._within_boundary(label, e, EL_TIME_END, EL_GAZE_END)
            if ended_within and not started_within:
                return True

        return False


    def saccade_from_boundary(self, label, event_queue=None):
        """Checks whether any saccades have exited a given boundary.

        For a saccade to count as exiting a boundary, it must begin within the boundary
        and end outside of it. If an event queue is not provided, this method will
        retrieve and empty the event queue from the tracker.

        Args:
            label (str): The label of the boundary of interest (e.g. 'fixation').
            event_queue (:obj:`List`, optional): A queue of eye events returned from
                :meth:`get_event_queue`.

        Returns:
            bool: True if any saccades exited the boundary, otherwise False.

        """
        if not event_queue:
            event_queue = self.get_event_queue([SACCADE_END])
        if not len(event_queue):
            return False

        for e in event_queue:
            if e == None or self.get_event_type(e) != SACCADE_END:
                continue
            timestamp = self._exited_boundary(label, e, EL_TIME_START)
            if timestamp:
                return True

        return False


    def saccade_in_direction(self, doi, event_queue=None):
        """Checks whether any saccades have occured in a given direction.

        Valid directions include 'up', 'down', 'left', and 'right'. In addition, you
        can specify both a horizontal and vertical direction (e.g. ['left', 'up']) to
        be more specific in your direction of interest. For example::
        
            self.el.saccade_in_directon(doi=['up'])
             
        will detect any saccades that end higher on the screen than they start,
        whereas::
        
            self.el.saccade_in_directon(doi=['up', 'right'])
            
        will only detect saccades that meet that criteria *and* end further to the right
        than they start.

        If an event queue is not provided, this method will retrieve and empty the event
        queue from the tracker.

        Args:
            doi (:obj:`List` of str): The names of the direction(s) of interest. Both a
                vertical and a horizontal direction of interest can be specified.
            event_queue (:obj:`List`, optional): A queue of eye events returned from
                :meth:`get_event_queue`.

        Returns:
            bool: True if any saccades occurred in the specified direction,
            otherwise False.

        """
        if not iterable(doi): 
            doi = [doi] # if direction of interest is a string, make it a list
        
        directions = ['up', 'down', 'left', 'right']
        for direction in doi:
            if direction not in directions:
                valid_dois = pretty_list(directions, brackets='')
                err_str = "'{0}' is not a valid direction (must be one of {1})."
                raise ValueError(err_str.format(direction, valid_dois))
            
        if not event_queue:
            event_queue = self.get_event_queue([SACCADE_END])
        if not len(event_queue):
            return False

        for e in event_queue:
            if e == None or self.get_event_type(e) != SACCADE_END:
                continue
            timestamp = self._saccade_in_direction(doi, e, report)
            if timestamp:
                return True

        return False


    def drift_correct(self, location=None, target=None, fill_color=None, draw_target=True):
        """Interactively checks the accuracy of the tracker's calibration.
        
        Over the course of a session, the accuracy of an eye tracker's calibration can
        begin to drift. A Drift Correction checks for this by presenting a target on the
        screen (typically in the center) and requiring the participant to press the
        space bar while looking directly at.
        
        If the tracker's gaze position is sufficiently close to the actual target
        coordinates, the drift correction ends immediately. If the error is too large,
        however, it will prevent the participant from continuing with the task until the
        error level is acceptable (either by re-trying the drift correct or by
        recalibrating the tracker).

        On older EyeLink models (EyeLink I & II), the recorded drift is used to adjust
        the calibration for improved accuracy on future trials. On newer models
        (EyeLink 1000 and up), drift correction does not try to improve the calibration.

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
        # Initialize defaults and sanitize inputs
        target = drift_correct_target() if target is None else target
        location = P.screen_c if location is None else location
        if not iterable(location):
            raise ValueError("'location' must be a pair of (x, y) pixel coordinates.")

        # Define a function that presents the DC target (for use as a callback)
        def draw_drift_correct():
            fill(P.default_fill_color if not fill_color else fill_color)
            blit(target, 5, location)
            flip()

        # Draw the drift correct target to the screen
        if draw_target:
            draw_drift_correct()

        # Actually perform drift correct for the current tracker
        return self._drift_correct(location, draw_drift_correct)


    def _drift_correct(self, loc, target_callback):
        """Internal hardware-specific method for performing drift correction.

        This method should wait indefinitely for a successful drift check to be
        performed at the given location and return immediately once one has occurred.

        Should return the absolute magnitude of error (in degrees of visual angle).

        """
        e = "Drift correct has not been implemented for this tracker."
        raise NotImplementedError(e)


    def gaze(self, return_integers=True, binocular_mode=RIGHT_EYE):
        """Fetches the (x,y) coordinates of the participant's current gaze on the screen.

        Args:
            return_integers (bool, optional): Whether to return the gaze coordinates as integers
                or floats. Defaults to True (integers).
            binocular_mode (int, optional): Tells the function which gaze coordinates to return
                for binocular samples. Can be any of ``RIGHT_EYE`` (returns right eye gaze),
                ``LEFT_EYE`` (returns left eye gaze), or ``BINOCULAR`` (returns average gaze
                of both eyes). Defaults to ``RIGHT_EYE``.
        
        Returns:
            A :obj:`Tuple` containing the (x,y) pixel coordinates of the participant's gaze.

        """
        pass


    def now(self, unit=TK_MS):
        """Fetches the current time according to the tracker's internal clock.

        Args:
            unit (int, optional): The units in which the time should be returned. Can be either
                ``TK_S`` (seconds) or ``TK_MS`` (milliseconds). Defaults to milliseconds.

        Returns:
            float: The current tracker time in the specified time unit.

        """
        pass


    def write(self, message):
        """Writes a message to the eye tracker's local data file (if available).
        
        Args:
            message (str): The message to write to the eye tracker's data file.

        """
        pass


    def get_event_type(self, e):
        """Fetches the numeric code corresponding to an eye event's type (e.g end saccade, start
        fixation).
        
        Args:
            e: An eye event from the tracker.
        
        Returns:
            The numeric type of the event (e.g. ``SACCADE_END``, ``FIXATION_START``).

        """
        pass


    def get_event_name(self, event):
        """Fetches the human-readable name of an eye event's type.

        Args:
            event: The event or event type to retrieve the type name for.

        Returns:
            A string containing the name of the event type (e.g. 'saccade end').

        Raises:
            ValueError: If 'event' is not a recognized eye event type. 

        """
        if type(event) != int:
            event = self.get_event_type(event)
        try:
            return self._event_names[event]
        except KeyError:
            raise ValueError("'{0}' is not a recognized eye event type.".format(event))
    

    def get_event_gaze(self, event, inspect):
        """Retrieves the gaze coordinates from an eye event or gaze sample.

        Args:
            event: The eye event (e.g. saccade, fixation, gaze sample) to return the gaze
                coordinates from.
            inspect: A flag indicating the type of gaze to retrieve: the gaze at the start of
                the event (``EL_GAZE_START``), the gaze at the end of the event (``EL_GAZE_END``),
                or the event's average gaze (``EL_GAZE_AVG``). Note that not all eye events have
                all three gaze attributes. Has no effect on gaze samples.
        
        Returns:
            The (x, y) gaze coordinates for the event.

        Raises:
            EyeTrackerError: If asked to inspect the end gaze or average gaze for an eye event that
                lacks that attribute (e.g. ``EL_GAZE_AVG`` for a ``SACCADE_END`` event).

        """
        pass
        

    def get_event_timestamp(self, event, report):
        """Gets the timestamp from an eye event or gaze sample.

        Args:
            event: The eye event (e.g. saccade, fixation, gaze sample) to return the timestamp
                from.
            report: A flag indicating whether to report the start time (``EL_TIME_START``) or
                end time (``EL_TIME_END``) of the eye event. Has no effect on gaze samples,
                which do not have separate start/end times.
        
        Returns:
            The timestamp for the start or end of the event.

        Raises:
            EyeTrackerError: If asked to report the end timestamp for an eye event that only has
                a start timestamp (e.g. ``FIXATION_START``).

        """
        pass


    def get_event_info(self, event):
        """Returns all available info about an eye event or gaze sample in the form of a
        :obj:`dict`.
        
        Usage::

            q = self.el.get_event_queue() # fetch all unprocessed eye events
            for event in q:
                info = self.el.get_event_info(event)
                if info['type'] == SACCADE_END:
                    end_gaze = info[EL_GAZE_END]
                    end_time = info[EL_TIME_END]
        
        
        See the table in :meth:`within_boundary` for a list of the attributes available for each
        eye event type.

        Args:
            event: The eye event (e.g. saccade, fixation, gaze sample) to collect the attributes of.

        Returns:
            A :obj:`dict` containing the available attributes of the event, such as start/end time,
            start/end/average gaze, and type name.

        """
        pass


    @property
    def eyelink(self):
        """:obj:`pylink.EyeLink` or None: The internal EyeLink object (if connected).

        Allows access to methods provided by the``pylink.EyeLink`` class that are not
        wrapped by the klibs EyeTracker API. Note that any code accessing these methods
        will not work in mouse simulation mode or with non-EyeLink trackers, so the
        presence of an EyeLink tracker should be checked before use::

            # If using EyeLink, set all pins high on port C of analog card
            if self.el.eyelink:
                self.el.eyelink.writeIOPort(4, 255)

        If not connected to an EyeLink eye tracker, this attribute will be None.
        
        """
        return self._el


    @property
    def eye(self):
        """:obj:`str` or None: The eye(s) currently being recorded by the tracker.
        
        Can be 'left', 'right', 'both', or None (if no eye is currently available).

        """
        pass


    @property
    def in_setup(self):
        """bool: Whether the eye tracker is currently in setup/calibration mode.

        """
        pass


    @property
    def recording(self):
        """bool: Whether the eye tracker is currently recording data.

        """
        pass
