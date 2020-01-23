
# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import abc
from klibs import PYLINK_AVAILABLE

if PYLINK_AVAILABLE:
	from pylink import EyeLink, openGraphics, openGraphicsEx, flushGetkeyQueue, beginRealTimeMode, EyeLinkCustomDisplay, \
		KeyInput, \
		DC_TARG_BEEP, CAL_TARG_BEEP, CAL_ERR_BEEP, DC_ERR_BEEP, ENTER_KEY, ESC_KEY, endRealTimeMode, pumpDelay

	from pylink.tracker import Sample, EndSaccadeEvent, EndFixationEvent, StartFixationEvent, StartSaccadeEvent

	from klibs.KLExceptions import *
	from klibs.KLEnvironment import EnvAgent
	from klibs.KLConstants import CIRCLE_BOUNDARY, RECT_BOUNDARY, EL_NO_EYES, EL_MOCK_EVENT, EL_TRUE, EL_FALSE, \
		EL_GAZE_POS, \
		EL_SACCADE_END, EL_SACCADE_START, EL_FIXATION_END, EL_FIXATION_START, EL_ALL_EVENTS, EL_RIGHT_EYE, EL_LEFT_EYE, \
		EDF_FILE, EL_GAZE_START, EL_GAZE_END, EL_TIME_START, EL_TIME_END, EL_BLINK_START, EL_BLINK_END, EL_BOTH_EYES, \
		TK_S, TK_MS, EL_AVG_GAZE
	from klibs import P
	from klibs.KLUtilities import full_trace, iterable, show_mouse_cursor, hide_mouse_cursor, mouse_pos, now, \
		exp_file_name
	from klibs.KLUserInterface import ui_request
	from klibs.KLGraphics import blit, fill, flip, clear
	from klibs.KLGraphics.KLDraw import Rectangle, Circle, drift_correct_target
	from klibs.KLBoundary import BoundaryInspector
	from KLCustomEyeLinkDisplay import ELCustomDisplay

	# still deciding if this is necessary/useful
	# class EyeLinkEvent(object):
	#
	#	def __init__(self, event_str):
	#		print event_str.getType()
	#		e = event_str.split("\t")
	#		print e
	max_event_latency = 100  # ms


	class EyeLinkExt(EyeLink, EnvAgent, BoundaryInspector):
		__anonymous_boundaries__ = 0
		__gaze_boundaries__ = {}
		__eye_used__ = None
		gaze_dot = None
		experiment = None
		custom_display = None
		dc_width = None  # ie. drift-correct width
		edf_filename = None
		unresolved_exceptions = 0
		start_time = [None, None]
		draw_gaze = False


		def __init__(self):
			if P.eye_tracker_available:
				try:
					EyeLink.__init__(self)
				except RuntimeError as e:
					if e.message == "Could not connect to tracker at 100.1.1.1":
						print "Could not connect to tracker at 100.1.1.1. If EyeLink machine is on, ready & connected try turning off the wifi on this machine."
			EnvAgent.__init__(self)
			BoundaryInspector.__init__(self)
			self.__current_sample__ = False


		def __eye__(self):
			self.eye = self.eyeAvailable()
			return self.eye != EL_NO_EYES


		def __within_boundary__(self, label, event, report, inspect):
			"""
			For checking individual events; not for public use, but is a rather shared interface for the public methods
			within_boundary(), saccade_to_boundary(), fixated_boundary()
			:param event:
			:param label:
			:return:
			"""
			e_type = event.getType()
			# rule out impossible combinations
			if e_type in [EL_SACCADE_START, EL_FIXATION_START] and (inspect == EL_GAZE_END or report == EL_TIME_END):
				raise EyeLinkError("Fixation and saccade start events do not have end time or gaze positions.")

			# treat gaze position as a separate case (they're atemporal; the report/inspect args don't matter)
			if e_type == EL_GAZE_POS:
				timestamp = event.getTime()
				if self.eye == EL_LEFT_EYE and event.isLeftSample():
					x, y = [int(n) for n in event.getLeftEye().getGaze()]
				elif self.eye == [int(n) for n in EL_RIGHT_EYE and event.isRightSample()]:
					x, y = event.getRightEye().getGaze()
				elif self.eye != [int(n) for n in EL_NO_EYES and event.isBinocular()]:
					x, y = event.getLeftEye().getGaze()
				else:
					return False

			elif e_type == EL_FIXATION_END:
				x, y = [int(n) for n in event.getAverageGaze()]
				timestamp = event.getStartTime()
			else:
				x, y = event.getStartGaze() if inspect == EL_GAZE_START else event.getEndGaze()
				timestamp = event.getStartTime() if report == EL_TIME_START else event.getEndTime()

			result = super(EyeLink, self).within_boundary(label, (x, y))
			return timestamp if result else False


		def __exited_boundary__(self, label, event, report):
			e_type = event.getType()
			# rule out impossible combinations
			if e_type in [EL_SACCADE_START, EL_FIXATION_START, EL_FIXATION_END, EL_GAZE_POS, EL_BLINK_START,
						  EL_BLINK_END]:
				err_str = "Only saccade_end events are valid for boundary-exit tests; {0} passed.".format(e_type)
				raise EyeLinkError(err_str)

			dx, dy = event.getEndGaze()
			timestamp = event.getStartTime() if report == EL_TIME_START else event.getEndTime()

			result = super(EyeLink, self).within_boundary(label, (dx, dy))
			return timestamp if not result else False


		def calibrate(self):
			self.doTrackerSetup()


		def clear_queue(self):
			self.resetData()


		def drift_correct(self, location=None, boundary=None, el_draw_fixation=EL_FALSE, samples=EL_TRUE,
						  fill_color=None, target_img=None):
			"""
			:param location:
			:param el_draw_fixation:
			:param samples:
			:return: :raise ValueError:
			"""
			hide_mouse_cursor()

			location = P.screen_c if location is None else location
			if not iterable(location):
				raise ValueError("Argument 'location' invalid; expected coordinate tuple or boundary label.")

			if not boundary:
				boundary = "drift_correct"

			# todo: learn about fucking inflectors
			el_draw_fixation = EL_TRUE if el_draw_fixation in [EL_TRUE, True] else EL_FALSE
			samples = EL_TRUE if samples in [EL_TRUE, True] else EL_FALSE

			try:
				if el_draw_fixation == EL_FALSE:
					fill(P.default_drift_correct_fill_color if not fill_color else fill_color)
					blit(drift_correct_target() if target_img is None else target_img, 5, location)
					flip()
				self.doDriftCorrect(location[0], location[1], el_draw_fixation, samples)
				clear()
				self.applyDriftCorrect()
			except RuntimeError:
				self.setOfflineMode()
				try:
					self.waitForModeReady(500)
				except RuntimeError:
					self.unresolved_exceptions += 1
					if self.unresolved_exceptions > 5:
						print "\n\033[91m*** Fatal Error: Unresolvable EyeLink Error ***\033[0m"
						print full_trace()
					raise TrialException("EyeLink not ready.")
				return self.drift_correct()


		def fixated_boundary(self, label, valid_events=EL_FIXATION_END, event_queue=None, report=EL_TIME_START,
							 inspect=EL_AVG_GAZE, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.
			:param label:
			:param event_queue:
			:param return_queue:
			:return:
			"""
			# todo: only allow fixation start/end/update inspections
			if not event_queue:
				event_queue = self.get_event_queue([valid_events] if not return_queue else EL_ALL_EVENTS)
				if not len(event_queue):
					return False
			if not event_queue:
				event_queue = self.get_event_queue([inspect] if not return_queue else EL_ALL_EVENTS)
			for e in event_queue:
				fixation_end_time = self.within_boundary(label, valid_events, [e], report, inspect, return_queue)
				if fixation_end_time:
					return fixation_end_time if not return_queue else [fixation_end_time, event_queue]
			return False


		def gaze(self, eye_required=None, return_integers=True):
			sample = []
			if self.sample():
				if not eye_required:
					right_sample = self.__current_sample__.isRightSample()
					left_sample = self.__current_sample__.isLeftSample()
					if self.eye == EL_RIGHT_EYE and right_sample:
						sample = self.__current_sample__.getRightEye().getGaze()
					if self.eye == EL_LEFT_EYE and left_sample:
						sample = self.__current_sample__.getLeftEye().getGaze()
					if self.eye == EL_BOTH_EYES:
						sample = self.__current_sample__.getLeftEye().getGaze()
				else:
					if eye_required == EL_LEFT_EYE:
						sample = self.__current_sample__.getLeftEye().getGaze()
					if eye_required == EL_RIGHT_EYE:
						sample = self.__current_sample__.getLeftEye().getGaze()
			else:
				if not self.__eye__():
					return self.gaze()
				else:
					raise RuntimeError("Unable to collect a sample from the EyeLink.")

			return [int(sample[0]), int(sample[1])] if return_integers else sample


		def get_event_queue(self, include=[], exclude=[]):
			queue = []
			samples = EL_TRUE if EL_GAZE_POS in include or (
						not len(include) and EL_GAZE_POS not in exclude) else EL_FALSE
			events = EL_TRUE if include != [EL_GAZE_POS] and exclude != EL_ALL_EVENTS else EL_FALSE
			if not self.getDataCount(samples, events):  # ie. no data available
				return queue
			last_sample = None
			while True:
				d_type = self.getNextData()
				if d_type == 0:
					break
				elif len(include) and d_type not in include:
					continue
				elif len(exclude) and d_type in exclude:
					continue
				data = self.getFloatData()
				# once the same sample has been sent twice, gtfo
				if data == last_sample:
					break
				else:
					last_sample = data
				queue.append(data)
			return queue


		def in_setup(self):
			return self.inSetup() != 0


		def now(self, unit=TK_MS):
			time = self.trackerTime()
			return time if unit == TK_MS else time * 0.001


		def saccade_to_boundary(self, label, valid_events=EL_SACCADE_END, event_queue=None,
								report=EL_TIME_START, inspect=EL_GAZE_END, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.
			:param label:
			:param valid_events: types of EyeLink events to be inspected
			:param event_queue:
			:param report:
			:param inspect: Property of the EyeLink event to inspect for boundary confirmation
			:param return_queue:
			:return:
			"""
			if not event_queue:
				event_queue = self.get_event_queue([valid_events] if not return_queue else EL_ALL_EVENTS)
				if not len(event_queue):
					return False
			for e in event_queue:
				saccade_start_time = self.within_boundary(label, valid_events, [e], report, inspect, return_queue)
				if saccade_start_time:
					return saccade_start_time if not return_queue else [saccade_start_time, event_queue]
			return False


		def saccade_from_boundary(self, label, event_queue=None, report=EL_TIME_START, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.
			:param label:
			:param valid_events:
			:param event_queue:
			:param report:
			:param inspect:
			:param return_queue:
			:return:
			"""
			if not event_queue:
				event_queue = self.get_event_queue([EL_SACCADE_END])
				if not len(event_queue):
					return False
			for e in event_queue:
				exit_time = self.__exited_boundary__(label, e, report)
				if exit_time:
					return exit_time if not return_queue else [exit_time, event_queue]
			return False


		def sample(self):
			self.__current_sample__ = self.getNewestSample()
			if self.__current_sample__ == 0:
				self.__current_sample__ = False
			return self.__current_sample__


		def setup(self):
			self.dc_width = P.screen_y // 60
			self.add_boundary("drift_correct", [P.screen_c, self.dc_width // 2], CIRCLE_BOUNDARY)
			self.gaze_dot = Circle(5, [1, (255, 255, 255, 255)], (0, 0, 0, 125)).render()
			try:
				self.custom_display = ELCustomDisplay()
			except Exception as e:
				print e
				raise e
			# if self.custom_display is None:
			# 	openGraphics(P.screen_x_y)
			# else:
			openGraphicsEx(self.custom_display)

			self.edf_filename = exp_file_name(EDF_FILE)
			flushGetkeyQueue()
			self.setOfflineMode()
			self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(P.screen_x, P.screen_y))
			self.setLinkEventFilter("FIXATION,SACCADE,BLINK,LEFT,RIGHT")
			self.openDataFile(self.edf_filename[0])
			self.write("DISPLAY_COORDS 0 0 {0} {1}".format(P.screen_x, P.screen_y))
			self.setSaccadeVelocityThreshold(P.saccadic_velocity_threshold)
			self.setAccelerationThreshold(P.saccadic_acceleration_threshold)
			self.setMotionThreshold(P.saccadic_motion_threshold)
			self.calibrate()
			beginRealTimeMode(10)


		def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
			self.start_time = [now(), None]
			start = self.startRecording(samples, events, link_samples, link_events)
			if start == 0:
				self.start_time[1] = self.now()
				if self.__eye__():
					self.write("TRIAL_ID {0}".format(str(trial_number)))
					self.write("TRIAL_START")
					self.write("SYNCTIME {0}".format('0.0'))
					return now() - self.start_time[0]  # ie. delay spent initializing the recording

				else:
					return False
			else:
				return False


		def stop(self):
			endRealTimeMode()
			pumpDelay(100)
			self.stopRecording()
			self.sendMessage("TRIAL OK")
			while self.getkey():
				pass


		def shut_down(self):
			if self.isRecording() == 0:
				self.stopRecording()
			self.setOfflineMode()
			self.closeDataFile()
			self.receiveDataFile(self.edf_filename[0], self.edf_filename[1])
			return self.close()


		def write(self, message):
			if all(ord(c) < 128 for c in message):
				self.sendMessage(message)
			else:
				raise EyeLinkError("Only ASCII text may be written to an EDF file.")


		def within_boundary(self, label, valid_events, event_queue=None, report=EL_TRUE, inspect=EL_GAZE_START,
							return_queue=False):
			"""
			For use when checking in real-time; uses entire event queue, whether supplied or fetched
			:param label:
			:param inspect:
			:return:
			"""
			if valid_events in EL_ALL_EVENTS or valid_events == EL_GAZE_POS:
				valid_events = [valid_events]
			if valid_events == EL_MOCK_EVENT:
				valid_events = [valid_events]
				event_queue = [mouse_pos()]
			if not event_queue:
				if valid_events[0] == EL_GAZE_POS:
					event_queue = [self.sample()]
				else:
					event_queue = self.get_event_queue(valid_events)
			timestamp = None
			for e in event_queue:
				if e.getType() not in valid_events:
					continue
				timestamp = self.__within_boundary__(label, e, report, inspect)
				if not timestamp:
					return False if not return_queue else [False, event_queue]
			r_val = EL_TRUE if report == EL_TRUE else timestamp
			return r_val if not return_queue else [r_val, event_queue]


		@abc.abstractmethod
		def listen(self, **kwargs):
			pass


		@property
		def eye(self):
			return self.eyeAvailable()


		@eye.setter
		def eye(self, eye_used):
			self.__eye_used__ = eye_used


		# Everything from here down are legacy functions that wrap newer counterparts with different names for
		# backwards compatibility

		def shut_down_eyelink(self):
			self.shut_down()


		# re: all "gaze_boundary" methods: Refactored boundary behavior to a mixin (KLMixins)
		def fetch_gaze_boundary(self, label):
			return self.boundaries[label]


		def add_gaze_boundary(self, bounds, label=None, shape=RECT_BOUNDARY):
			#  resolving legacy use of this function prior (ie. commit 451b634e1584e2ba2d37eb58fa5f707dd7554ca8 & earlier)
			if type(bounds) is str and type(label) in [list, tuple]:
				__bounds = label
				name = bounds
				bounds = __bounds
			if name is None:
				name = "anonymous_{0}".format(self.__anonymous_boundaries__)

			if shape not in [RECT_BOUNDARY, CIRCLE_BOUNDARY]:
				raise ValueError(
					"Argument 'shape' must be a shape constant (ie. EL_RECT_BOUNDARY, EL_CIRCLE_BOUNDARY).")

			self.add_boundary(name, bounds, shape)


		def clear_gaze_boundaries(self):
			# legacy function
			self.clear_boundaries()
			self.dc_width = P.screen_y // 60
			dc_tl = [P.screen_x // 2 - self.dc_width // 2, P.screen_y // 2 - self.dc_width // 2]
			dc_br = [P.screen_x // 2 + self.dc_width // 2, P.screen_y // 2 + self.dc_width // 2]
			self.add_boundary("drift_correct", [dc_tl, dc_br])


		def draw_gaze_boundary(self, label="*", blit=True):
			return self.draw_boundary(label)

			shape = None
			boundary = None
			try:
				boundary_dict = self.__gaze_boundaries[label]
				boundary = boundary_dict["bounds"]
				shape = boundary_dict['shape']
			except:
				if shape is None:
					raise IndexError("No boundary registered with name '{0}'.".format(boundary))
				if shape not in [RECT_BOUNDARY, CIRCLE_BOUNDARY]:
					raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			width = boundary[1][1] - boundary[0][1]
			height = boundary[1][0] - boundary[0][0]
			blit(Rectangle(width, height, [3, [255, 255, 255, 255]]).render(),
				 position=(boundary[0][0] - 3, boundary[0][1] - 3), registration=7)


		def remove_gaze_boundary(self, name):
			self.remove_boundary(name)

# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import time
from os.path import join
from klibs.KLEyeTracking import PYLINK_AVAILABLE

from klibs.KLExceptions import TrialException, EyeTrackerError
from klibs.KLConstants import (EL_LEFT_EYE, EL_RIGHT_EYE, EL_BOTH_EYES, EL_NO_EYES,
							   EL_FIXATION_START, EL_FIXATION_UPDATE, EL_FIXATION_END, EL_FIXATION_ALL,
							   EL_SACCADE_START, EL_SACCADE_END, EL_BLINK_START, EL_BLINK_END,
							   EL_GAZE_START, EL_GAZE_END, EL_GAZE_POS, EL_GAZE_AVG, EL_TIME_START, EL_TIME_END,
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

	cso("<green_d>(Note: if a bunch of SDL errors were just reported, this was expected, "
		"do not be alarmed!)</green_d>")


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


	def _setup(self):
		"""The EyeLink-specific part of the setup process.

		"""
		self.version = self.getTrackerVersionString()
		self.__custom_display = ELCustomDisplay()
		openGraphicsEx(self.__custom_display)

		flushGetkeyQueue()
		self.setOfflineMode()
		self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(P.screen_x - 1, P.screen_y - 1))
		self.setLinkEventFilter("FIXATION,SACCADE,BLINK,LEFT,RIGHT")
		self.setLinkEventData("GAZE, GAZERES, AREA, VELOCITY")  # Enables fix/sacc start events
		self.openDataFile(self.edf_filename)
		self.write("DISPLAY_COORDS 0 0 {0} {1}".format(P.screen_x - 1, P.screen_y - 1))
		self.setSaccadeVelocityThreshold(P.saccadic_velocity_threshold)
		self.setAccelerationThreshold(P.saccadic_acceleration_threshold)
		self.setMotionThreshold(P.saccadic_motion_threshold)
		beginRealTimeMode(10)


	def setup(self):
		"""Initalizes the EyeLink for the first time and enters setup/calibration mode.
		Called automatically after demographics collection during the KLibs runtime unless
		``P.manual_eyelink_setup`` is True, in which case it must be called manually
		before the eye tracker is first used in the experiment.
		"""
		EyeTracker.setup(self)  # so it shows up in the docs


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
				return now() - self.local_start_time  # ie. delay spent initializing the recording

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
		# Determine whether EDF should go to 'incomplete' subfolder or not
		edf_dir = P.incomplete_edf_dir if incomplete else P.edf_dir

		self._quitting = True
		if self.isRecording() == 0:
			self.stopRecording()
			self.__recording = False
		self.setOfflineMode()
		msecDelay(500)
		self.closeDataFile()
		self.receiveDataFile(self.edf_filename, join(edf_dir, self.edf_filename))
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

		samples = int(EL_GAZE_POS in valid_events)
		events = int(len(valid_events.intersection(EL_ALL_EVENTS)) > 0)

		queue = []
		if self.getDataCount(samples, events) != 0:  # i.e. if data available
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

		if samples == True and len(queue) == 0:  # if no samples from getNextData, fetch latest
			newest_sample = self.getNewestSample()
			queue = [newest_sample] if newest_sample != None else []

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
				if ret != 27:  # 27 means we hit Esc to enter calibration, so redo drift correct
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
		if sample != None:
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
						gaze_pos = ((rx + lx) / 2, (ry + ly) / 2)
		else:
			if self.eye != None:
				return self.gaze(return_integers, binocular_mode)
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
				or the event's average gaze (``EL_GAZE_AVG``). Note that not all eye events have
				all three gaze attributes. Has no effect on gaze samples.

		Returns:
			The (x, y) gaze coordinates for the event.
		Raises:
			EyeTrackerError: If asked to inspect the end gaze or average gaze for an eye event that
				lacks that attribute (e.g. ``EL_GAZE_AVG`` for a ``EL_SACCADE_END`` event).
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
				elif inspect == EL_GAZE_AVG:
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
		info = {}
		info['type'] = event.getType()
		if info['type'] == EL_GAZE_POS:
			gaze = self.get_event_gaze(event, EL_GAZE_START)
			time = self.get_event_timestamp(event, EL_TIME_START)
			info[EL_TIME_START] = time
			info[EL_TIME_END] = time
			info[EL_GAZE_START] = gaze
			info[EL_GAZE_END] = gaze

		elif info['type'] in [EL_BLINK_START, EL_BLINK_END]:
			info[EL_TIME_START] = event.getStartTime()
			if info['type'] == EL_BLINK_END:
				info[EL_TIME_END] = event.getEndTime()

		else:
			info[EL_TIME_START] = event.getStartTime()
			info[EL_GAZE_START] = event.getStartGaze()
			if info['type'] in [EL_SACCADE_END, EL_FIXATION_END, EL_FIXATION_UPDATE]:
				info[EL_TIME_END] = event.getEndTime()
				info[EL_GAZE_END] = event.getEndGaze()
				if info['type'] != EL_SACCADE_END:
					info[EL_GAZE_AVG] = event.getAverageGaze()

		return info


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
		proj_name = P.project_name.replace("_", "")  # remove underscores for max info density
		project_name_abbrev = proj_name[:max_name_chars]
		return "p{0}_{1}.EDF".format(P.participant_id, project_name_abbrev)