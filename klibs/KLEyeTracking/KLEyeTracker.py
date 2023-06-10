# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

from klibs.KLExceptions import EyeTrackerError
from klibs.KLConstants import (EL_LEFT_EYE, EL_RIGHT_EYE, EL_BOTH_EYES, EL_NO_EYES,
    EL_FIXATION_START, EL_FIXATION_UPDATE, EL_FIXATION_END, EL_FIXATION_ALL,
    EL_SACCADE_START, EL_SACCADE_END, EL_BLINK_START, EL_BLINK_END, 
    EL_GAZE_START, EL_GAZE_END, EL_GAZE_POS, EL_GAZE_AVG, EL_TIME_START, EL_TIME_END,
    EL_ALL_EVENTS, EL_TRUE, EL_FALSE,
    TK_S, TK_MS)
from klibs import P
from klibs.KLUtilities import iterable, pretty_list
from klibs.KLBoundary import BoundaryInspector
from klibs.KLGraphics import blit, fill, flip


class EyeTracker(BoundaryInspector):
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
        BoundaryInspector.__init__(self)
        self.version = None
        self.initialized = False
        self.local_start_time = None
        self.tracker_start_time = None
        self.__recording = False
        self._unresolved_exceptions = 0
        self._quitting = False
        self._eye_names = {
            EL_RIGHT_EYE: 'right',
            EL_LEFT_EYE: 'left',
            EL_BOTH_EYES: 'both',
            EL_NO_EYES: None
        }
        self._event_names = {
            EL_GAZE_POS: 'gaze position',
            EL_BLINK_START: 'blink start',
            EL_BLINK_END: 'blink end',
            EL_SACCADE_START: 'saccade start',
            EL_SACCADE_END: 'saccade end',
            EL_FIXATION_START: 'fixation start',
            EL_FIXATION_END: 'fixation end',
            EL_FIXATION_UPDATE: 'fixation update'
        }
        self._event_defaults = {
            EL_GAZE_POS: [None, None],
            EL_SACCADE_START: [EL_TIME_START, EL_GAZE_START],
            EL_SACCADE_END: [EL_TIME_END, EL_GAZE_END],
            EL_FIXATION_START: [EL_TIME_START, EL_GAZE_START],
            EL_FIXATION_END: [EL_TIME_END, EL_GAZE_AVG],
            EL_FIXATION_UPDATE: [EL_TIME_END, EL_GAZE_AVG]            
        }


    def __within_boundary__(self, label, event, report, inspect):
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

        result = BoundaryInspector.within_boundary(self, label, gaze_coords)
        return timestamp if result else False


    def __exited_boundary__(self, label, event, report):
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
        if e_type != EL_SACCADE_END:
            typename = self.get_event_name(e_type)
            err = "Only saccade end events can be used for boundary exit tests ({0} given)"
            raise EyeTrackerError(err.format(typename))

        timestamp = self.get_event_timestamp(event, report)
        start_gaze = self.get_event_gaze(event, EL_GAZE_START)
        end_gaze = self.get_event_gaze(event, EL_GAZE_END)

        start_inside = BoundaryInspector.within_boundary(self, label, start_gaze)
        end_inside = BoundaryInspector.within_boundary(self, label, end_gaze)
        return timestamp if (start_inside and not end_inside) else False


    def __saccade_in_direction__(self, doi, event, report):
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
        if e_type != EL_SACCADE_END:
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
        self.__recording = True


    def stop(self):
        """Stops recording data from the eye tracker.
        
        Called automatically at the end of each trial unless ``P.manual_eyelink_recording`` is
        True, in which case it must be called manually in order to stop recording at any point. 
        To resume recording after this method is called, use the :meth:`start` method.

        """
        self.__recording = False


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


    def within_boundary(self, label, valid_events, event_queue=None, report=None, inspect=None):
        """Checks whether a fixation, saccade, or gaze sample has occured within the specified
        boundary since the last time the eye event queue was fetched.

        By default, this method tests the most useful gaze attribute of each event against the
        given boundary. This means that ``EL_GAZE_START`` is inspected for saccade and fixation 
        start events, ``EL_GAZE_END`` is inspected for saccade end events, and ``EL_GAZE_AVG``
        is inspected for fixation update and fixation end events. You can manually specify which
        gaze attribute to use for boundary testing with the 'inspect' argument.

        The valid event constants for this function, along with their supported 'inspect' and
        'report' flag values, are listed in the table below:

        +------------------------+-------------------------------------+--------------------+
        | Valid Events           | Inspect Values                      | Report Values      |
        +========================+=====================================+====================+
        | ``EL_GAZE_POS``        | N/A                                 | N/A                |
        +------------------------+-------------------------------------+--------------------+
        | ``EL_SACCADE_START``   | ``EL_GAZE_START``                   | ``EL_TIME_START``  |
        +------------------------+-------------------------------------+--------------------+
        | ``EL_SACCADE_END``     | ``EL_GAZE_START``, ``EL_GAZE_END``  | ``EL_TIME_START``, |
        |                        |                                     | ``EL_TIME_END``    |
        +------------------------+-------------------------------------+--------------------+
        | ``EL_FIXATION_START``  | ``EL_GAZE_START``                   | ``EL_TIME_START``  |
        +------------------------+-------------------------------------+--------------------+
        | ``EL_FIXATION_END``    | ``EL_GAZE_START``, ``EL_GAZE_AVG``, | ``EL_TIME_START``, |
        |                        | ``EL_GAZE_END``                     | ``EL_TIME_END``    |
        +------------------------+-------------------------------------+--------------------+
        | ``EL_FIXATION_UPDATE`` | ``EL_GAZE_START``, ``EL_GAZE_AVG``, | ``EL_TIME_START``, |
        |                        | ``EL_GAZE_END``                     | ``EL_TIME_END``    |
        +------------------------+-------------------------------------+--------------------+

        Note that gaze samples (``EL_GAZE_POS``) represent the gaze at a single point in time
        and thus have no start or end, so they are not affected by the values of the 'inspect'
        and 'report' flags.

        Args:
            label (str): The label of the boundary to check for events in, added using
                add_boundary().
            valid_events (:obj:`List`): A list of constants indicating the event type(s) to
                process.
            event_queue (:obj:`List`, optional): A queue of events returned from
                :meth:`get_event_queue` to inspect for the eye events. If no event queue is
                provided, the eye event queue will be fetched and processed, emptying it in
                the process.
            report (optional): A flag indicating whether to report the start time
                (``EL_TIME_START``) or end time (``EL_TIME_END``) of the event. Defaults to
                end time for all events except fixation start and saccade start.
            inspect (optional): A flag indicating which gaze attribute of events should be
                checked against the boundary: the gaze at the start of the event
                (``EL_GAZE_START``), the gaze at the end of the event (``EL_GAZE_END``), or
                the events's average gaze (``EL_GAZE_AVG``). Defaults to inspecting start gaze
                for fixation/saccade start events, average gaze for fixation update/end events, and
                end gaze for saccade end events.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if a
            valid event in the queue was within the specified boundary, otherwise False.

        """
        if valid_events in EL_ALL_EVENTS or valid_events == EL_GAZE_POS:
            valid_events = [valid_events]
        if any(e in [EL_BLINK_START, EL_BLINK_END] for e in valid_events):
            raise ValueError("Cannot inspect the gaze coordinates of blink events.")
        if not event_queue:
            event_queue = self.get_event_queue(valid_events)

        timestamp = None
        for e in event_queue:
            if e == None or self.get_event_type(e) not in valid_events:
                continue
            e_type = self.get_event_type(e)
            # if inspect or report not given, default to most reasonable option
            _report = report if report else self._event_defaults[e_type][0]
            _inspect = inspect if inspect else self._event_defaults[e_type][1]
            timestamp = self.__within_boundary__(label, e, _report, _inspect)
            if timestamp:
                return timestamp

        return False


    def fixated_boundary(self, label, valid_events=EL_FIXATION_START, event_queue=None,
                                                    report=None, inspect=None):
        """Checks whether a specified boundary has been fixated since the last time the eye
        event queue was fetched.

        By default, this method tests the most useful gaze attribute of each event against the
        given boundary. This means that ``EL_GAZE_START`` is inspected for fixation start events
        and ``EL_GAZE_AVG`` is inspected for fixation update and fixation end events. You can
        manually specify which gaze attribute to use for boundary testing with the 'inspect'
        argument.

        The valid event constants for this function, along with their supported 'inspect' and
        'report' flag values, are listed in the table below:

        +------------------------+-------------------------------------+--------------------+
        | Valid Events           | Inspect Values                      | Report Values      |
        +========================+=====================================+====================+
        | ``EL_FIXATION_START``  | ``EL_GAZE_START``                   | ``EL_TIME_START``  |
        +------------------------+-------------------------------------+--------------------+
        | ``EL_FIXATION_UPDATE`` | ``EL_GAZE_START``, ``EL_GAZE_AVG``, | ``EL_TIME_START``, |
        |                        | ``EL_GAZE_END``                     | ``EL_TIME_END``    |
        +------------------------+-------------------------------------+--------------------+
        | ``EL_FIXATION_END``    | ``EL_GAZE_START``, ``EL_GAZE_AVG``, | ``EL_TIME_START``, |
        |                        | ``EL_GAZE_END``                     | ``EL_TIME_END``    |
        +------------------------+-------------------------------------+--------------------+

        Args:
            label (str): The label of the boundary to check if the event is in, added using
                add_boundary().
            valid_events (:obj:`List`, optional): A list of constants indicating the fixation
                event type(s) to process. Defaults to fixation start events. 
            event_queue (:obj:`List`, optional): A queue of events returned from
                :meth:`get_event_queue` to inspect for the fixation events. If no event queue
                is provided, the eye event queue will be fetched and processed, emptying it in
                the process.
            report (optional): A flag indicating whether to report the start time
                (``EL_TIME_START``) or end time (``EL_TIME_END``) of the fixation.
            inspect (optional): A flag indicating which gaze attribute of the fixation should be
                checked against the boundary: the gaze at the start of the fixation
                (``EL_GAZE_START``), the gaze at the end of the fixation (``EL_GAZE_END``), or
                the fixation's average gaze (``EL_GAZE_AVG``). Defaults to inspecting start gaze
                for fixation start events and average gaze for fixation update/end events.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if a
            valid fixation event in the queue was within the specified boundary, otherwise False.

        """
        if not iterable(valid_events):
            valid_events = [valid_events]

        for e_type in valid_events:
            if e_type not in EL_FIXATION_ALL:
                raise ValueError("Valid events for fixated_boundary must be fixation events.")

        return self.within_boundary(label, valid_events, event_queue, report, inspect) 


    def saccade_to_boundary(self, label, event_queue=None, report=EL_TIME_END):
        """Checks whether any saccades have entered a given boundary since the last time the
        eye event queue was fetched.

        Args:
            label (str): The label of the boundary to check if the saccade entered, added using
                add_boundary().
            event_queue (:obj:`List`, optional): A queue of events returned from
                :meth:`get_event_queue` to inspect for saccade end events. If no event queue
                is provided, the eye event queue will be fetched and processed, emptying it in
                the process.
            report (optional): A flag indicating whether to report the start time
                (``EL_TIME_START``) or end time (``EL_TIME_END``) of the saccade.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if a
            saccade in the queue started outside and ended inside the boundary, otherwise False.

        """
        if not event_queue:
            event_queue = self.get_event_queue([EL_SACCADE_END])
        if not len(event_queue):
            return False

        for e in event_queue:
            if e == None or self.get_event_type(e) != EL_SACCADE_END:
                continue
            started_within = self.__within_boundary__(label, e, EL_TIME_START, EL_GAZE_START)
            ended_within = self.__within_boundary__(label, e, report, EL_GAZE_END)
            if ended_within and not started_within:
                timestamp = ended_within
                return timestamp

        return False


    def saccade_from_boundary(self, label, event_queue=None, report=EL_TIME_END):
        """Checks whether any saccades have exited a given boundary since the last time the
        eye event queue was fetched.

        Args:
            label (str): The label of the boundary to check if the saccade exited, added using
                add_boundary().
            event_queue (:obj:`List`, optional): A queue of events returned from
                :meth:`get_event_queue` to inspect for saccade end events. If no event queue
                is provided, the eye event queue will be fetched and processed, emptying it in
                the process.
            report (optional): A flag indicating whether to report the start time
                (``EL_TIME_START``) or end time (``EL_TIME_END``) of the saccade.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if a
            saccade in the queue started inside and ended outside the boundary, otherwise False.

        """
        if not event_queue:
            event_queue = self.get_event_queue([EL_SACCADE_END])
        if not len(event_queue):
            return False

        for e in event_queue:
            if e == None or self.get_event_type(e) != EL_SACCADE_END:
                continue
            timestamp = self.__exited_boundary__(label, e, report)
            if timestamp:
                return timestamp

        return False


    def saccade_in_direction(self, doi, event_queue=None, report=EL_TIME_START):
        """Checks whether any saccades have occured in a given direction since the last time the
        eye event queue was fetched.

        Valid directions include 'up', 'down', 'left', and 'right'. In addition, you can specify
        both a horizontal and vertical direction (e.g. ['left', 'up']) to be more specific in your
        direction of interest. For example::
        
             self.el.saccade_in_directon(doi=['up'])
             
        will detect any saccades that end higher on the screen than they start, whereas::
        
            self.el.saccade_in_directon(doi=['up', 'right'])
            
        will only detect saccades that meet that criteria *and* end further to the right than they
        start.

        Args:
            doi (:obj:`List` of str): The names of the direction(s) of interest to watch for
                saccades in. Both a vertical ('up' or 'down') or horizontal ('left' or 'right')
                direction of interest can be specified.
            event_queue (:obj:`List`, optional): A queue of events returned from
                :meth:`get_event_queue` to inspect for saccade end events. If no event queue
                is provided, the eye event queue will be fetched and processed, emptying it in
                the process.
            report (optional): A flag indicating whether to report the start time
                (``EL_TIME_START``) or end time (``EL_TIME_END``) of the saccade.

        Returns:
            The timestamp of the start or end of the event (see the 'report' argument) if a
            saccade in the queue occurred in a direction of interest, otherwise False.

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
            event_queue = self.get_event_queue([EL_SACCADE_END])
        if not len(event_queue):
            return False

        for e in event_queue:
            if e == None or self.get_event_type(e) != EL_SACCADE_END:
                continue
            timestamp = self.__saccade_in_direction__(doi, e, report)
            if timestamp:
                return timestamp

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


    def gaze(self, return_integers=True, binocular_mode=EL_RIGHT_EYE):
        """Fetches the (x,y) coordinates of the participant's current gaze on the screen.

        Args:
            return_integers (bool, optional): Whether to return the gaze coordinates as integers
                or floats. Defaults to True (integers).
            binocular_mode (int, optional): Tells the function which gaze coordinates to return
                for binocular samples. Can be any of ``EL_RIGHT_EYE`` (returns right eye gaze),
                ``EL_LEFT_EYE`` (returns left eye gaze), or ``EL_BOTH_EYES`` (returns average gaze
                of both eyes). Defaults to ``EL_RIGHT_EYE``.
        
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
            The numeric type of the event (e.g. ``EL_END_SACCADE``, ``EL_START_FIXATION``).

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
                lacks that attribute (e.g. ``EL_GAZE_AVG`` for a ``EL_SACCADE_END`` event).

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
                a start timestamp (e.g. ``EL_FIXATION_START``).

        """
        pass


    def get_event_info(self, event):
        """Returns all available info about an eye event or gaze sample in the form of a
        :obj:`dict`.
        
        Usage::

            q = self.el.get_event_queue() # fetch all unprocessed eye events
            for event in q:
                info = self.el.get_event_info(event)
                if info['type'] == EL_SACCADE_END:
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
    def eye(self):
        """:obj:`str` or None: The eye(s) currently being recorded by the tracker. Can be 'left',
        'right', 'both', or None (if no eye is currently available).

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
