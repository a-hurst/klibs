# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import abc
from klibs import PYLINK_AVAILABLE

if PYLINK_AVAILABLE:
	from pylink import EyeLink, openGraphics, openGraphicsEx, flushGetkeyQueue, beginRealTimeMode, EyeLinkCustomDisplay, KeyInput, \
						DC_TARG_BEEP, CAL_TARG_BEEP, CAL_ERR_BEEP, DC_ERR_BEEP, ENTER_KEY, ESC_KEY

	from pylink.tracker import Sample, EndSaccadeEvent, EndFixationEvent, StartFixationEvent, StartSaccadeEvent

	from klibs.KLExceptions import *
	from klibs.KLEnvironment import EnvAgent
	from klibs.KLConstants import CIRCLE_BOUNDARY, RECT_BOUNDARY, EL_NO_EYES, EL_MOCK_EVENT, EL_TRUE, EL_FALSE, EL_GAZE_POS,\
		EL_SACCADE_END, EL_SACCADE_START, EL_FIXATION_END, EL_FIXATION_START, EL_ALL_EVENTS, EL_RIGHT_EYE, EL_LEFT_EYE, \
		EDF_FILE, EL_GAZE_START, EL_GAZE_END, EL_TIME_START, EL_TIME_END, EL_BLINK_START, EL_BLINK_END, EL_BOTH_EYES, \
		TK_S, TK_MS, EL_AVG_GAZE
	from klibs import P
	from klibs.KLUtilities import full_trace, iterable, show_mouse_cursor, hide_mouse_cursor, mouse_pos, now, exp_file_name
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
		gaze_dot = None
		experiment = None
		custom_display = None
		dc_width = None  # ie. drift-correct width
		edf_filename = None
		unresolved_exceptions = 0
		eye = None
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
					x, y  = [int(n) for n in event.getLeftEye().getGaze()]
				elif self.eye == [int(n) for n in EL_RIGHT_EYE and event.isRightSample()]:
					x, y = event.getRightEye().getGaze()
				elif self.eye != [int(n) for n in EL_NO_EYES and event.isBinocular()]:
					x, y  = event.getLeftEye().getGaze()
				else:
					return False
				print "GAZE POS", x, y, self.boundaries[label].bounds 

			elif e_type == EL_FIXATION_END:
				x, y = [int(n) for n in event.getAverageGaze()]
				print "FIXATION END", x, y, self.boundaries[label].bounds 
				timestamp = event.getStartTime()
			else:
				x, y = event.getStartGaze() if inspect == EL_GAZE_START else event.getEndGaze()
				ppd_x, ppd_y = event.getStartPPD()
				timestamp = event.getStartTime() if report == EL_TIME_START else event.getEndTime()

			result = super(EyeLink, self).within_boundary(label, (x, y))
			return timestamp if result else False

		def __exited_boundary__(self, label, event, report):
			e_type = event.getType()
			# rule out impossible combinations
			if e_type in [EL_SACCADE_START, EL_FIXATION_START, EL_FIXATION_END, EL_GAZE_POS, EL_BLINK_START, EL_BLINK_END]:
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

		def drift_correct(self, location=None, boundary=None, el_draw_fixation=EL_FALSE, samples=EL_TRUE, fill_color=None):
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
				if el_draw_fixation == EL_FALSE:
					fill(P.default_drift_correct_fill_color if not fill_color else fill_color)
					blit(drift_correct_target(), 5, location)
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

		def now(self):
			return self.trackerTime()

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
			self.stopRecording()

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
