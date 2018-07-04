# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import time
from os.path import join
from klibs.KLEyeTracking import PYLINK_AVAILABLE

from klibs.KLExceptions import TrialException, EyeTrackerError
from klibs.KLConstants import (EL_LEFT_EYE, EL_RIGHT_EYE, EL_BOTH_EYES, EL_NO_EYES,
	EL_FIXATION_START, EL_FIXATION_UPDATE, EL_FIXATION_END, EL_FIXATION_ALL,
	EL_SACCADE_START, EL_SACCADE_END, EL_BLINK_START, EL_BLINK_END, 
	EL_GAZE_START, EL_GAZE_END, EL_GAZE_POS, EL_AVG_GAZE, EL_TIME_START, EL_TIME_END,
	EL_ALL_EVENTS, EL_TRUE, EL_FALSE,
	TK_S, TK_MS, CIRCLE_BOUNDARY, RECT_BOUNDARY)
from klibs import P
from klibs.KLUtilities import full_trace, iterable, hide_mouse_cursor, mouse_pos, now
from klibs.KLUtilities import colored_stdout as cso
from klibs.KLUserInterface import ui_request
from klibs.KLGraphics import blit, fill, flip, clear
from klibs.KLGraphics.KLDraw import drift_correct_target
from klibs.KLEyeTracking.KLEyeTracker import EyeTracker

if PYLINK_AVAILABLE:
	from pylink import (openGraphicsEx, flushGetkeyQueue, pumpDelay,
		beginRealTimeMode, endRealTimeMode, msecDelay)
	from pylink import EyeLink as BaseEyeLink
	from .KLCustomEyeLinkDisplay import ELCustomDisplay


class EyeLink(BaseEyeLink, EyeTracker):
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
		if P.eye_tracker_available:
			print("")
			try:
				BaseEyeLink.__init__(self)
			except RuntimeError as e:
				if "Could not connect" in str(e):
					print("! If the EyeLink is on, ready, & connected, try turning off "
						"the Wi-Fi on this machine or restarting the EyeLink PC.\n")
				raise e
		EyeTracker.__init__(self)
		self.__custom_display = None
		self.__recording = False
		self._unresolved_exceptions = 0
		self._quitting = False
		self.version = None
		self.initialized = False


	def setup(self):
		"""Initalizes the EyeLink for the first time and enters setup/calibration mode.

		Called automatically after demographics collection during the KLibs runtime unless
		``P.manual_eyelink_setup`` is True, in which case it must be called manually
		before the eye tracker is first used in the experiment.

		"""		
		self.version = self.getTrackerVersion()
		self.__custom_display = ELCustomDisplay()
		openGraphicsEx(self.__custom_display)	

		flushGetkeyQueue()
		self.setOfflineMode()
		self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(P.screen_x-1, P.screen_y-1))
		self.setLinkEventFilter("FIXATION,SACCADE,BLINK,LEFT,RIGHT")
		self.setLinkEventData("GAZE, GAZERES, AREA, VELOCITY") # Enables fix/sacc start events
		self.openDataFile(self.edf_filename)
		self.write("DISPLAY_COORDS 0 0 {0} {1}".format(P.screen_x-1, P.screen_y-1))
		self.setSaccadeVelocityThreshold(P.saccadic_velocity_threshold)
		self.setAccelerationThreshold(P.saccadic_acceleration_threshold)
		self.setMotionThreshold(P.saccadic_motion_threshold)
		self.calibrate()
		beginRealTimeMode(10)
		self.initialized = True


	def calibrate(self):
		"""Enters the calibration and setup mode for the EyeLink.

		"""
		self.doTrackerSetup()


	def start(self, trial_number):
		self.local_start_time = now()
		start = self.startRecording(EL_TRUE, EL_TRUE, EL_TRUE, EL_TRUE)
		if start == 0:
			self.tracker_start_time = self.now()
			self.__recording = True
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
		self.stopRecording()
		self.__recording = False
		self.sendMessage("TRIAL OK")
		flushGetkeyQueue()


	def shut_down(self):
		"""Terminates recording and disconnects from the eye tracker, putting it into standby mode.

		Will also transfer the EDF file for the current session from the tracker to the project's
		``ExpAssets/EDF`` folder.

		Called automatically whenever KLibs exits. For internal use only.

		"""
		self._quitting = True
		if self.isRecording() == 0:
			self.stopRecording()
			self.__recording = False
		self.setOfflineMode()
		msecDelay(500)
		self.closeDataFile()
		self.receiveDataFile(self.edf_filename, join(P.edf_dir, self.edf_filename))
		return self.close()


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
		
		if len(include):
			valid_events = set(include)
		elif len(exclude):
			valid_events = set(EL_ALL_EVENTS + [EL_GAZE_POS]).difference(exclude)
		else:
			valid_events = set(EL_ALL_EVENTS + [EL_GAZE_POS])

		samples = EL_GAZE_POS in valid_events
		events = len(valid_events.intersection(EL_ALL_EVENTS)) > 0

		queue = []
		if self.getDataCount(samples, events) == 0:  # ie. no data available
			return queue
		last_sample = None
		while True:
			d_type = self.getNextData()
			if d_type == 0:
				break
			elif d_type not in valid_events:
				continue
			data = self.getFloatData()
			# once the same sample has been sent twice, gtfo
			if data == last_sample:
				break
			else:
				last_sample = data
			queue.append(data)
		return queue


	def clear_queue(self):
		"""Clears the event queue for the eye tracker. Any uninspected eye events will be
		discarded.

		"""
		self.resetData()


	def drift_correct(self, location=None, target=None, fill_color=None, draw_target=True):
		"""Checks the accuracy of the EyeLink's calibration by presenting a fixation stimulus
		and requiring the participant to press the space bar while looking directly at it. If
		there is a large difference between the gaze location at the time the key was pressed
		and the true location of the fixation, it indicates that there has been drift in the
		calibration.

		On older EyeLink models (EyeLink I & II), the recorded drift is used to adjust the
		calibration for improved accuracy on future trials. On recent models (EyeLink 1000 and
		up), drift corrections will *check* for drift and prompt the participant to try again
		if the drift is large, but they do not affect the tracker's calibration.

		Args:
			location (Tuple(int, int), optional): The (x,y) pixel coordinates where the drift
				correct target should be located. Defaults to the center of the screen.
			target: A :obj:`Drawbject` or other :func:`KLGraphics.blit`-able shape to use as
				the drift correct target. Defaults to a circular :func:`drift_correct_target`.
			fill_color: A :obj:`List` or :obj:`Tuple` containing an RGBA colour to use for the
				background for the drift correct screen. Defaults to the value of
				``P.default_fill_color``.
			draw_target (bool, optional): A flag indicating whether the function should draw
				the drift correct target itself (True), or whether it should leave it to the
				programmer to draw the target before :meth:`drift_correct` is called (False). 
				Defaults to True.

		Raises:
			TrialException: If repeated EyeLink errors are encountered while attempting to
				perform the drift correct.

		"""
		hide_mouse_cursor()

		target = drift_correct_target() if target is None else target
		draw_target = EL_TRUE if draw_target in [EL_TRUE, True] else EL_FALSE
		location = P.screen_c if location is None else location
		if not iterable(location):
			raise ValueError("'location' must be a pair of (x,y) pixel coordinates.")

		try:
			while True:
				if draw_target == EL_TRUE:
					fill(P.default_fill_color if not fill_color else fill_color)
					blit(target, 5, location)
					flip()
				ret = self.doDriftCorrect(location[0], location[1], draw_target, EL_TRUE)
				if ret != 27: # 27 means we hit Esc to enter calibration, so redo drift correct
					break
			if draw_target == EL_TRUE:
				fill(P.default_fill_color if not fill_color else fill_color)
				flip()
			return self.applyDriftCorrect()
		except RuntimeError:
			try:
				self.setOfflineMode()
			except RuntimeError:
				self._unresolved_exceptions += 1
				if self._unresolved_exceptions > 5:
					cso("\n<red>*** Fatal Error: Unresolvable EyeLink Error ***</red>")
					print(full_trace())
					self._unresolved_exceptions = 0
					raise TrialException("EyeLink not ready.")
			return self.drift_correct(location, target, fill_color, draw_target)


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

		Raises:
			RuntimeError: If neither eye is currently available for recording.

		"""
		sample = self.getNewestSample()
		if sample != 0:
			if sample.isRightSample():
				gaze_pos = sample.getRightEye().getGaze()
			elif sample.isLeftSample():
				gaze_pos = sample.getLeftEye().getGaze()
			elif sample.isBinocular():
				if binocular_mode == EL_RIGHT_EYE:
					gaze_pos = sample.getRightEye().getGaze()
				elif binocular_mode == EL_LEFT_EYE:
					gaze_pos = sample.getLeftEye().getGaze()
				elif binocular_mode == EL_BOTH_EYES:
					rx, ry = sample.getRightEye().getGaze()
					lx, ly = sample.getLeftEye().getGaze()
					# if either eye is missing, use good eye instead of averaging
					if int(lx) == -32768:
						gaze_pos = (rx, ry)
					elif int(rx) == -32768:
						gaze_pos = (lx, ly)
					else:
						gaze_pos = ( (rx+lx)/2, (ry+ly)/2 )
		else:
			if self.eye != None:
				return self.gaze()
			else:
				raise RuntimeError("Unable to collect a sample from the EyeLink.")

		return tuple(int(p) for p in gaze_pos) if return_integers else gaze_pos


	def now(self, unit=TK_MS):
		"""Fetches the current time according to the tracker's internal clock.

		Args:
			unit (int, optional): The units in which the time should be returned. Can be either
				``TK_S`` (seconds) or ``TK_MS`` (milliseconds). Defaults to milliseconds.

		Returns:
			float: The current tracker time in the specified time unit.

		"""
		time = self.trackerTime()
		return time * 0.001 if unit == TK_S else time


	def write(self, message):
		"""Writes a message to the EyeLink EDF file. Unicode characters are supported.
		
		Args:
			message (str): The message to write to the eye tracker's data file.

		"""
		self.sendMessage(message)


	def get_event_type(self, e):
		"""Fetches the numeric code corresponding to an eye event's type (e.g end saccade, start
		fixation).
		
		Args:
			e: An eye event from the tracker.
		
		Returns:
			The numeric type of the event (e.g. ``EL_END_SACCADE``, ``EL_START_FIXATION``).

		"""
		return e.getType()


	def get_event_gaze(self, event, inspect):
		"""Retrieves the gaze coordinates from an eye event or gaze sample.

		Args:
			event: The eye event (e.g. saccade, fixation, gaze sample) to return the gaze
				coordinates from.
			inspect: A flag indicating the type of gaze to retrieve: the gaze at the start of
				the event (``EL_GAZE_START``), the gaze at the end of the event (``EL_GAZE_END``),
				or the event's average gaze (``EL_AVG_GAZE``). Note that not all eye events have
				all three gaze attributes. Has no effect on gaze samples.
		
		Returns:
			The (x, y) gaze coordinates for the event.

		Raises:
			EyeTrackerError: If asked to inspect the end gaze or average gaze for an eye event that
				lacks that attribute (e.g. ``EL_AVG_GAZE`` for a ``EL_SACCADE_END`` event).

		"""
		if event.getType() == EL_GAZE_POS:
			if event.isLeftSample():
				coords = event.getLeftEye().getGaze()
			elif event.isRightSample():
				coords = event.getRightEye().getGaze()
			elif event.isBinocular():
				coords = event.getRightEye().getGaze()
			else:
				return None
		else:
			try:
				if inspect == EL_GAZE_START:
					coords = event.getStartGaze()
				elif inspect == EL_GAZE_END:
					coords = event.getEndGaze()
				elif inspect == EL_AVG_GAZE:
					coords = event.getAverageGaze()
			except AttributeError:
				typename = self.get_event_name(event.type)
				err = "Cannot inspect {0} for {1} events."
				raise EyeTrackerError(err.format(inspect, typename))

		return coords


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
		if event.getType() == EL_GAZE_POS:
			return event.getTime()
		else:
			try:
				return event.getStartTime() if report == EL_TIME_START else event.getEndTime()
			except AttributeError:
				typename = self.get_event_name(event.type)
				err = "Cannot report {0} for {1} events."
				raise EyeTrackerError(err.format(report, typename))


	@property
	def eye(self):
		"""str or None: The eye(s) currently being recorded by the tracker. Can be 'left', 'right',
		'both', or None (if no eye is currently available).

		"""
		return self._eye_names[self.eyeAvailable()]
	

	@property
	def in_setup(self):
		"""bool: Whether the EyeLink is currently in setup/calibration mode.

		"""
		return self.inSetup() != 0


	@property
	def recording(self):
		"""bool: Whether the eye tracker is currently recording data.

		"""
		return self.__recording


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
