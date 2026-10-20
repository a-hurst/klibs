# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
from sdl2.ext import cursor_hidden
from klibs.KLEyeTracking import PYLINK_AVAILABLE

from klibs.KLExceptions import EyeTrackerError
from klibs.KLConstants import (LEFT_EYE, RIGHT_EYE, BINOCULAR, EL_NO_EYES,
    FIXATION_START, FIXATION_UPDATE, FIXATION_END, GAZE_SAMPLE,
    SACCADE_START, SACCADE_END, BLINK_START, BLINK_END, 
    EL_GAZE_START, EL_GAZE_END, EL_GAZE_AVG, EL_TIME_START, EL_TIME_END,
    EL_ALL_EVENTS, EL_TRUE, EL_FALSE,
    TK_S, TK_MS)
from klibs import P
from klibs.KLInternal import now, hide_stderr
from klibs.KLUserInterface import show_cursor, hide_cursor
from klibs.KLEyeTracking.KLEyeTracker import EyeTracker, EventParser

if PYLINK_AVAILABLE:
    with hide_stderr(macos_only=True):
        from pylink import (
            openGraphicsEx, beginRealTimeMode, endRealTimeMode, flushGetkeyQueue,
            pumpDelay, msecDelay
        )
        from pylink import EyeLink as BaseEyeLink
    from .KLCustomEyeLinkDisplay import ELCustomDisplay

# NOTE: Currently no way of checking whether EyeLink connected and available without
# attempting (and failing) to connect to the tracker. Tracker can be pinged, but no 
# easy way to do that in pure Python (and ping requires admin sometimes?). EyeLink
# communication itself is via UDP.

MISSING_DATA = -32768

EYE_NAME_MAP = {
    RIGHT_EYE: 'right',
    LEFT_EYE: 'left',
    BINOCULAR: 'both',
    EL_NO_EYES: None
}

def _get_eyelink():
    # Wrapper for getting EyeLink connection and handling errors gracefully
    try:
        print("")
        return BaseEyeLink()
    except RuntimeError as e:
        if "Could not connect" in str(e):
            print("! If the EyeLink is on, ready, & connected, try turning off "
                "the Wi-Fi on this machine or restarting the EyeLink PC.\n")
        raise e

def _get_eyelink_version(s):
    # Gets the actual hardware version of the tracker based on the software
    # version number
    if "EYELINK CL" in s:
        s = s.replace("EYELINK CL", "").strip()
        try:
            tracker = "EyeLink CL"
            version = float(s)
            if int(version) in (3, 4):
                tracker = "EyeLink 1000"
            elif int(version) == 5:
                tracker = "EyeLink 1000 Plus"
            elif int(version) == 6:
                tracker = "EyeLink Portable Duo"
            return tracker + " {}".format(version)
        except ValueError:
            pass
    return s.replace("EYELINK", "EyeLink").strip()


class EyeLinkEventParser(EventParser):
    """A parser defining how to extract different data from EyeLink events.

    """
    def get_type(self, e):
        """Retrieves the type of a given event (e.g. ``BLINK_START``).
        """
        return e.getType()

    def eye(self, e):
        """Retrieves the eye for a given event.
        """
        return e.getEye()

    def timestamp(self, e):
        """Gets the timestamp (in msec) for a gaze sample.
        """
        return e.getTime()

    def left_gaze(self, e):
        """Gets the left eye (x, y) gaze coordinates for a gaze sample.
        """
        eye = e.getLeftEye()
        if eye:
            x, y = eye.getGaze()
            if int(x) != MISSING_DATA:
                return (x, y)
        return None

    def right_gaze(self, e):
        """Gets the right eye (x, y) gaze coordinates for a gaze sample.
        """
        eye = e.getRightEye()
        if eye:
            x, y = eye.getGaze()
            if int(x) != MISSING_DATA:
                return (x, y)
        return None

    def left_pupil_size(self, e):
        """Gets the left eye pupil size (arbitrary units) for a gaze sample.
        """
        eye = e.getLeftEye()
        if eye:
            ps = eye.getPupilSize()
            if int(ps) != MISSING_DATA:
                return ps
        return None

    def right_pupil_size(self, e):
        """Gets the right eye pupil size (arbitrary units) for a gaze sample.
        """
        eye = e.getRightEye()
        if eye:
            ps = eye.getPupilSize()
            if int(ps) != MISSING_DATA:
                return ps
        return None

    def start_time(self, e):
        """Gets the timestamp (in msec) for the start of the event.
        """
        return e.getStartTime()

    def end_time(self, e):
        """Gets the timestamp (in msec) for the end of the event.
        """
        return e.getEndTime()

    def start_gaze(self, e):
        """Gets the (x, y) gaze coordinates at the start of the event.
        """
        return e.getStartGaze()

    def end_gaze(self, e):
        """Gets the (x, y) gaze coordinates at the end of the event.
        """
        return e.getEndGaze()

    def avg_gaze(self, e):
        """Gets the average (x, y) gaze coordinates for the event.
        """
        return e.getAverageGaze()

    def duration(self, e):
        """Gets the total duration (in msec) for the event.
        """
        # Pylink docs say to add 4 seconds for real duration, but mentions
        # EyeLink II when it says this. Is this stil correct for newer trackers?
        return (e.getEndTime() - e.getStartTime()) + 4



class EyeLink(EyeTracker):
    """A connection to an SR Research EyeLink eye tracker, providing a friendly interface to the
    pylink API along with a pretty setup/calibration display.
    
    If pylink is installed in your project's Python environment and ``P.eye_tracker_availiable``
    is set to True in a project that makes use of eye tracking, an instance of this class will be
    provided as the attribute ``self.el`` of the Experiment object.

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
        self._el = _get_eyelink()
        self._custom_display = None
        self._recording = False
        self._unresolved_exceptions = 0
        self._quitting = False
        self._parser = EyeLinkEventParser()
        self.version = None
        self.initialized = False


    def _setup(self):
        """The EyeLink-specific part of the setup process.
        
        """
        v = self._el.getTrackerVersionString()
        self.version = _get_eyelink_version(v)
        self._custom_display = ELCustomDisplay(self)
        openGraphicsEx(self._custom_display)

        flushGetkeyQueue()
        self._el.setOfflineMode()
        x_adj, y_adj = (P.screen_x - 1, P.screen_y - 1)
        self._el.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(x_adj, y_adj))
        self._el.setLinkEventFilter("FIXATION,SACCADE,BLINK,LEFT,RIGHT")
        self._el.setLinkEventData("GAZE, GAZERES, AREA, VELOCITY") # Enables fix/sacc start events
        self._el.openDataFile(self.edf_filename)
        self.write("DISPLAY_COORDS 0 0 {0} {1}".format(x_adj, y_adj))
        self._el.setSaccadeVelocityThreshold(P.saccadic_velocity_threshold)
        self._el.setAccelerationThreshold(P.saccadic_acceleration_threshold)
        self._el.setMotionThreshold(P.saccadic_motion_threshold)
        beginRealTimeMode(10)


    def _check_connection(self):
        # Ensures that the tracker connection is still alive
        if not self._el.isConnected():
            e = "Unexpectedly lost the connection to the EyeLink"
            raise RuntimeError(e)


    def setup(self):
        """Initalizes the EyeLink for the first time and enters setup/calibration mode.

        Called automatically after demographics collection during the KLibs runtime unless
        ``P.manual_eyelink_setup`` is True, in which case it must be called manually
        before the eye tracker is first used in the experiment.

        """
        EyeTracker.setup(self) # so it shows up in the docs


    def calibrate(self):
        """Enters the calibration and setup mode for the EyeLink.

        """
        self._el.doTrackerSetup()


    def start(self, trial_number):
        self.local_start_time = now()
        start = self._el.startRecording(EL_TRUE, EL_TRUE, EL_TRUE, EL_TRUE)
        if start == 0:
            self.tracker_start_time = self.now()
            self._recording = True
            if self.eye != None:
                self.write("TRIAL_ID {0}".format(str(trial_number)))
                self.write("TRIAL_START")
                self.write("SYNCTIME {0}".format('0.0'))
                return now() - self.local_start_time # ie. delay spent initializing the recording

            else:
                return False
        else:
            return False


    def stop(self):
        """Stops recording data from the eye tracker. 
                
        Called automatically at the end of each trial unless ``P.manual_eyelink_recording`` is
        True, in which case it must be called manually in order to stop recording at any point. 
        To resume recording after this method is called, use the :meth:`start` method.

        """
        endRealTimeMode()
        pumpDelay(100)
        self._el.stopRecording()
        self._recording = False
        self._el.sendMessage("TRIAL OK")
        flushGetkeyQueue()


    def shut_down(self, incomplete=False):
        """Terminates recording and disconnects from the eye tracker, putting it into standby mode.

        Will also transfer the EDF file for the current session from the tracker to the project's
        ``ExpAssets/EDF`` folder (or its ``incomplete`` subfolder, if incomplete = True).

        Called automatically whenever KLibs exits. For internal use only.

        Args:
            incomplete (bool, optional): Whether the full session was completed before the function
                was called. If True, the EDF file for the session will be written to an 'incomplete'
                subfolder of the eye tracker data directory ('ExpAssets/EDF'). Defaults to False.

        """
        # Determine destination path for EDF (creating parent folder if needed)
        if P.development_mode:
            edf_dir = P.devmode_edf_dir
        else:
            edf_dir = P.incomplete_edf_dir if incomplete else P.edf_dir
        if not os.path.isdir(edf_dir):
            os.makedirs(edf_dir)
        edf_path = os.path.join(edf_dir, self.edf_filename)

        self._quitting = True
        if self._el.isRecording() == 0:
            self._el.stopRecording()
            self._recording = False
        self._el.setOfflineMode()
        msecDelay(500)
        self._el.closeDataFile()
        self._el.receiveDataFile(self.edf_filename, edf_path)
        return self._el.close()


    def _get_tracker_events(self, events, samples=False):
        """Internal method for retrieving eye events from the tracker.

        Args:
            events (list): A list of the desired event types to retrieve.
            samples (bool): Whether gaze samples should be returned in addition to other
                event types.

        Returns:
            list: A list of tracker-specific events.

        """
        queue = []
        get_samples = int(samples)
        get_events = int(len(events.intersection(EL_ALL_EVENTS)) > 0)

        # If any data waiting, process it all
        any_samples = self._el.getDataCount(1, 0)
        if self._el.getDataCount(get_samples, get_events) != 0:
            last_event = None
            while True:
                e_type = self._el.getNextData()
                if e_type == 0:
                    break
                elif e_type not in valid_events:
                    continue
                event = self._el.getFloatData()
                # If same event sent twice, stop immediately
                if event == last_event:
                    break
                last_sample = data
                queue.append(data)
        
        # If no gaze samples from getNextData, append latest sample
        if samples and not any_samples:
            s = self._el.getNewestSample()
            if s != None:
                queue.append(s)

        return queue


    def get_event_queue(self, include=[], exclude=[]):
        """Fetches and returns the EyeLink's event queue, emptying it in the process.

        Args:
            include (:obj:`List`, optional): A list specifying the types of eye events to fetch
                from the event queue. Includes all eye event types by default, unless they are
                explicitly excluded.
            exclude (:obj:`List`, optional): A list specifying the types of eye events to exclude
                from the returned queue. Defaults to an empty list (i.e. no events excluded.)

        Returns:
            A :obj:`List` of eye events.

        """
        return EyeTracker.get_event_queue(self, include, exclude) # so it shows up in the docs


    def clear_queue(self):
        """Clears the event queue for the eye tracker. Any uninspected eye events will be
        discarded.

        """
        self._el.resetData()


    def _drift_correct(self, loc, target_callback):
        """Internal hardware-specific method for performing drift correction.

        """
        mouse_hidden = cursor_hidden()
        hide_cursor()

        done = False
        while not done:
            self._check_connection()
            target_callback() # redraws drift correct on screen
            try:
                ret = self._el.doDriftCorrect(loc[0], loc[1], EL_FALSE, EL_TRUE)
            except RuntimeError as e:
                # If error is that escape has been pressed, just do drift correct again
                if "Escape" in str(e):
                    continue
                # If drift correct doesn't work, try again after setting tracker to
                # offline mode
                self._el.setOfflineMode()
                self._el.waitForModeReady(500)
                ret = self._el.doDriftCorrect(loc[0], loc[1], EL_FALSE, EL_TRUE)

            # If Esc was hit to recalibrate during drift correct, redo drift correct
            if ret != 27:
                done = True

        # Get the magnitude of the drift correct error (if available)
        drift = -1.0
        drift_msg = self._el.getCalibrationMessage()
        if drift_msg[:5] == "drift":
            drift = float(drift_msg.split(" ")[1])

        # Apply the drift correct (if possible) and reset cursor visibility
        self._el.applyDriftCorrect()
        if not mouse_hidden:
            show_cursor()
        
        return drift


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

        Raises:
            RuntimeError: If neither eye is currently available for recording.

        """
        sample = self._el.getNewestSample()
        if sample is not 0:
            if sample.isRightSample():
                gaze_pos = sample.getRightEye().getGaze()
            elif sample.isLeftSample():
                gaze_pos = sample.getLeftEye().getGaze()
            elif sample.isBinocular():
                if binocular_mode == RIGHT_EYE:
                    gaze_pos = sample.getRightEye().getGaze()
                elif binocular_mode == LEFT_EYE:
                    gaze_pos = sample.getLeftEye().getGaze()
                elif binocular_mode == BINOCULAR:
                    rx, ry = sample.getRightEye().getGaze()
                    lx, ly = sample.getLeftEye().getGaze()
                    # if either eye is missing, use good eye instead of averaging
                    if int(lx) == MISSING_DATA:
                        gaze_pos = (rx, ry)
                    elif int(rx) == MISSING_DATA:
                        gaze_pos = (lx, ly)
                    else:
                        gaze_pos = ( (rx+lx)/2, (ry+ly)/2 )
        else:
            if self.eye != None:
                return self.gaze(return_integers, binocular_mode)
            else:
                raise RuntimeError("Unable to collect a sample from the EyeLink.")

        return tuple(int(p) for p in gaze_pos) if return_integers else gaze_pos


    def now(self):
        """Fetches the current time according to the tracker's internal clock.

        Returns:
            float: The current tracker time (in milliseconds).

        """
        return self._el.trackerTime()


    def write(self, message):
        """Writes a message to the EyeLink EDF file. Unicode characters are supported.
        
        Args:
            message (str): The message to write to the eye tracker's data file.

        """
        self._el.sendMessage(message)


    @property
    def eye(self):
        """str or None: The eye(s) currently being recorded by the tracker. Can be 'left', 'right',
        'both', or None (if no eye is currently available).

        """
        return EYE_NAME_MAP[self._el.eyeAvailable()]
    

    @property
    def in_setup(self):
        """bool: Whether the EyeLink is currently in setup/calibration mode.

        """
        return self._el.inSetup() != 0


    @property
    def recording(self):
        """bool: Whether the eye tracker is currently recording data.

        """
        return self._recording


    @property
    def edf_filename(self):
        """str: The filename of the EDF file for the current participant, generated automatically
        from the participant number and the project name. Can be at most 8 characters (excluding
        the '.EDF' file extension).

        """
        # EDFs require DOS-style short file names so we need to make sure name <= 8 chars
        max_name_chars = 8 - (len(str(P.participant_id)) + 2)
        proj_name = P.project_name.replace("_", "") # remove underscores for max info density
        project_name_abbrev = proj_name[:max_name_chars]
        return "p{0}_{1}.EDF".format(P.participant_id, project_name_abbrev)
