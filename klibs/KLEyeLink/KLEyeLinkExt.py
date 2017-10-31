# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import abc
from klibs import PYLINK_AVAILABLE

if PYLINK_AVAILABLE:
	from pylink import (EyeLink, openGraphicsEx, flushGetkeyQueue, pumpDelay,
		beginRealTimeMode, endRealTimeMode)

	from klibs.KLExceptions import *
	from klibs.KLEnvironment import EnvAgent
	from klibs.KLConstants import (EL_LEFT_EYE, EL_RIGHT_EYE, EL_BOTH_EYES, EL_NO_EYES,
		EL_SACCADE_START, EL_SACCADE_END, EL_FIXATION_START, EL_FIXATION_END, EL_FIXATION_ALL,
		EL_BLINK_START, EL_BLINK_END, EL_GAZE_START, EL_GAZE_END, EL_GAZE_POS, EL_AVG_GAZE,
		EL_TIME_START, EL_TIME_END, EL_MOCK_EVENT, EL_ALL_EVENTS, EL_TRUE, EL_FALSE, EDF_FILE,
		TK_S, TK_MS, CIRCLE_BOUNDARY, RECT_BOUNDARY)
	from klibs import P
	from klibs.KLUtilities import (full_trace, iterable, hide_mouse_cursor, mouse_pos, now,
		exp_file_name)
	from klibs.KLUserInterface import ui_request
	from klibs.KLGraphics import blit, fill, flip, clear
	from klibs.KLGraphics.KLDraw import Rectangle, Circle, drift_correct_target
	from klibs.KLBoundary import BoundaryInspector
	from KLCustomEyeLinkDisplay import ELCustomDisplay

	# still deciding if this is necessary/useful
	#class EyeLinkEvent(object):
	#
	#	def __init__(self, event_str):
	#		print event_str.getType()
	#		e = event_str.split("\t")
	#		print e
	max_event_latency = 100 #  ms



	class EyeLinkExt(EyeLink, EnvAgent, BoundaryInspector):
		__anonymous_boundaries__ = 0
		__gaze_boundaries__ = {}
		__eye_used__ = None
		gaze_dot = None
		experiment = None
		custom_display = None
		version = None
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
			if inspect == EL_AVG_GAZE and e_type not in [EL_FIXATION_END, EL_FIXATION_UPDATE]:
				raise EyeLinkError("Average gaze can only be inspected for fixation update/end events.")

			# treat gaze position as a separate case (they're atemporal; the report/inspect args don't matter)
			if e_type == EL_GAZE_POS:
				timestamp = event.getTime()
				if self.eye == EL_LEFT_EYE and event.isLeftSample():
					x, y = [int(n) for n in event.getLeftEye().getGaze()]
				elif self.eye == EL_RIGHT_EYE and event.isRightSample():
					x, y = [int(n) for n in event.getRightEye().getGaze()]
				elif self.eye != EL_NO_EYES and event.isBinocular():
					x, y = [int(n) for n in event.getLeftEye().getGaze()]
				else:
					return False
			else:
				if inspect == EL_GAZE_START:
					x, y = [int(n) for n in event.getStartGaze()]
				elif inspect == EL_GAZE_END:
					x, y = [int(n) for n in event.getEndGaze()]
				elif inspect == EL_AVG_GAZE:
					x, y = [int(n) for n in event.getAverageGaze()]
				timestamp = event.getStartTime() if report == EL_TIME_START else event.getEndTime()

			result = super(EyeLink, self).within_boundary(label, (x, y))
			return timestamp if result else False

		def __exited_boundary__(self, label, event, report):
			e_type = event.getType()
			# rule out impossible combinations
			if e_type != EL_SACCADE_END:
				err_str = "Only saccade_end events are valid for boundary-exit tests; {0} passed.".format(e_type)
				raise EyeLinkError(err_str)

			x1, y1 = [int(n) for n in event.getStartGaze()]
			x2, y2 = [int(n) for n in event.getEndGaze()]
			timestamp = event.getStartTime() if report == EL_TIME_START else event.getEndTime()

			start_in_boundary = super(EyeLink, self).within_boundary(label, (x1, y1))
			end_in_boundary   = super(EyeLink, self).within_boundary(label, (x2, y2))
			return timestamp if (start_in_boundary and not end_in_boundary) else False

		def __saccade_in_direction__(self, doi, event, report):
			e_type = event.getType()
			# rule out impossible combinations
			if e_type in [EL_SACCADE_START, EL_FIXATION_START, EL_FIXATION_END, EL_GAZE_POS, EL_BLINK_START, EL_BLINK_END]:
				err_str = "Only saccade_end events are valid for boundary-exit tests; {0} passed.".format(e_type)
				raise EyeLinkError(err_str)
				
			sacc_direction = [None, None]
			sxp, syp = event.getStartGaze()
			exp, eyp = event.getEndGaze()
			
			sacc_direction[0] = "right" if (exp - sxp) > 0 else "left"
			sacc_direction[1] = "down"  if (eyp - syp) > 0 else "up"
			
			timestamp = event.getStartTime() if report == EL_TIME_START else event.getEndTime()
			
			# Check if the direction(s) of interest match the direction of the saccade
			result = all(direction in sacc_direction for direction in doi)
			return timestamp if result else False

		def calibrate(self):
			self.doTrackerSetup()

		def clear_queue(self):
			self.resetData()

		def drift_correct(self, location=None, boundary=None, el_draw_fixation=EL_TRUE, samples=EL_TRUE, fill_color=None, target_img=None):
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

			#todo: learn about fucking inflectors
			el_draw_fixation = EL_TRUE if el_draw_fixation in [EL_TRUE, True] else EL_FALSE
			samples = EL_TRUE if samples in [EL_TRUE, True] else EL_FALSE

			try:
				if el_draw_fixation == EL_TRUE:
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

		def fixated_boundary(self, label, valid_events=EL_FIXATION_START, event_queue=None, report=EL_TIME_START,
							 inspect=None, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first valid fixation event in the passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.

			By default, this function checks whether the start coordinates of any EL_FIXATION_START events in the event
			queue are within the specified boundary. 

			The inspect argument can be used to specify which coordinates to test against the boundary. EL_GAZE_START
			uses the gaze at the start of the fixation, EL_GAZE_END uses the gaze at the end of the fixation, and 
			EL_AVG_GAZE uses the average gaze across the fixation. Only EL_GAZE_START is available for EL_FIXATION_START
			events, and attempting to use any other inspect type with EL_FIXATION_EVENT in valid_events will result in
			an EyeLinkError exception. If no inspect type is specified, the function will inspect start gaze for
			EL_FIXATION_START events and average gaze for EL_FIXATION_END and EL_FIXATION_UPDATE events.

			:param label:
			:param event_queue:
			:param report:
			:param inspect: 
			:param return_queue:
			:return:
			"""
			if not iterable(valid_events):
				valid_events = [valid_events]
			for e_type in valid_events:
				if e_type not in EL_FIXATION_ALL:
					raise EyeLinkError("Valid events for fixated_boundary must be fixation events.")
				elif e_type == EL_FIXATION_START and inspect == EL_AVG_GAZE:
					raise EyeLinkError("Only EL_GAZE_START can be inspected for EL_FIXATION_START events.")

			if not event_queue:
				event_queue = self.get_event_queue(valid_events if not return_queue else EL_ALL_EVENTS)
				if not len(event_queue):
					return False
			for e in event_queue:
				if e.getType() not in valid_events: # if passed queue, skip events with types not in valid_events
					continue
				if not inspect: # if inspect not given, default to start for start events and average for others
					if e.getType() == EL_FIXATION_START:
						result = self.__within_boundary__(label, e, report, EL_GAZE_START)
					else:
						result = self.__within_boundary__(label, e, report, EL_AVG_GAZE)
				else:
					result = self.__within_boundary__(label, e, report, inspect)
				if result:
					return result if not return_queue else [result, event_queue]
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
			samples = EL_TRUE if EL_GAZE_POS in include or (not len(include) and EL_GAZE_POS not in exclude) else EL_FALSE
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

		def saccade_to_boundary(self, label, event_queue=None, report=EL_TIME_END, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.

			:param label:
			:param event_queue:
			:param report:
			:param return_queue:
			:return:
			"""
			if not event_queue:
				event_queue = self.get_event_queue([EL_SACCADE_END] if not return_queue else EL_ALL_EVENTS)
				if not len(event_queue):
					return False
			for e in event_queue:
				if e.getType() != EL_SACCADE_END:
					continue
				timestamp = self.__within_boundary__(label, e, report, EL_GAZE_END)
				if timestamp:
					return timestamp if not return_queue else [timestamp, event_queue]
			return False

		def saccade_from_boundary(self, label, event_queue=None, report=EL_TIME_END, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.

			:param label:
			:param event_queue:
			:param report:
			:param return_queue:
			:return:
			"""
			if not event_queue:
				event_queue = self.get_event_queue([EL_SACCADE_END] if not return_queue else EL_ALL_EVENTS)
				if not len(event_queue):
					return False
			for e in event_queue:
				if e.getType() != EL_SACCADE_END:
					continue
				timestamp = self.__exited_boundary__(label, e, report)
				if timestamp:
					return timestamp if not return_queue else [timestamp, event_queue]
			return False

		def saccade_in_direction(self, doi, event_queue=None, report=EL_TIME_START, return_queue=False):
			"""
			Checks for any saccades in the direction(s) of interest, returning immediately if one is encountered.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.

			:param doi: direction of interest, either as a single string or list of strings
			:param event_queue:
			:param report:
			:param return_queue:
			:return:
			"""
			if isinstance(doi, basestring): 
				doi = [doi] # if direction of interest is a string, make it a list
				
			for direction in doi:
				if direction not in ['up', 'down', 'left', 'right']:
					err_str = "'{0}' is not a valid direction. Valid directions are 'up', 'down', 'left', and 'right'.".format(direction)
					raise EyeLinkError(err_str)
				
			if not event_queue:
				event_queue = self.get_event_queue([EL_SACCADE_END])
				if not len(event_queue):
					return False
			for e in event_queue:
				exit_time = self.__saccade_in_direction__(doi, e, report)
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

			self.version = self.getTrackerVersion()
			openGraphicsEx(self.custom_display)	

			self.edf_filename = exp_file_name(EDF_FILE)
			flushGetkeyQueue()
			self.setOfflineMode()
			self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(P.screen_x-1, P.screen_y-1))
			self.setLinkEventFilter("FIXATION,SACCADE,BLINK,LEFT,RIGHT")
			self.setLinkEventData("GAZE, GAZERES, AREA, VELOCITY") # Need to specify manually for start events to work right
			self.openDataFile(self.edf_filename[0])
			self.write("DISPLAY_COORDS 0 0 {0} {1}".format(P.screen_x-1, P.screen_y-1))
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
