# -*- coding: utf-8 -*-
__author__ = 'jono'

from klibs.KLDraw import *
import time
import math
from klibs.KLUtilities import *
from klibs.KLDraw import *
from klibs.KLExceptions import *
from klibs.KLMixins import BoundaryInspector

try:
	from pylink import EyeLink, openGraphicsEx, flushGetkeyQueue
	PYLINK_AVAILABLE = True
except ImportError:
	print "\t* Warning: Pylink library not found; eye tracking will not be available."
	PYLINK_AVAILABLE = False

print "pylink available: {0}".format(PYLINK_AVAILABLE)
try:
	mouse = mouse_pos(True)
	if (type(x) is int for x in mouse):
		DUMMY_MODE_AVAILABLE = True
except:
	DUMMY_MODE_AVAILABLE = False

# class EyeLinkEvent(object):
#
# 	def __init__(self, event_data

if PYLINK_AVAILABLE:
	class EyeLink(EyeLink, BoundaryInspector):
		__dummy_mode = None
		__anonymous_boundaries = 0
		experiment = None
		__gaze_boundaries = {}
		custom_display = None
		dc_width = None  # ie. drift-correct width
		edf_filename = None
		unresolved_exceptions = 0
		eye = None
		start_time = [None, None]

		def __init__(self, experiment_instance):
			super(EyeLink, self).__init__()
			self.experiment = experiment_instance
			self.__current_sample = False
			if Params.eye_tracker_available:
				try:
					EyeLink.__init__(self)
				except RuntimeError as e:
					if e.message == "Could not connect to tracker at 100.1.1.1":
						print "Could not connect to tracker at 100.1.1.1. If EyeLink machine is on, ready & connected try turning off the wifi on this machine."
			if DUMMY_MODE_AVAILABLE:
				self.dummy_mode = Params.eye_tracker_available is False if self.dummy_mode is None else self.dummy_mode is True
			else:
				self.dummy_mode = False
			self.dc_width = Params.screen_y // 60
			self.add_boundary("drift_correct", [Params.screen_x, self.dc_width // 2], CIRCLE_BOUNDARY)

		def __eye(self):
			self.eye = self.eyeAvailable()
			return self.eye != EL_NO_EYES

		def calibrate(self):
			self.doTrackerSetup()

		def in_setup(self):
			return self.inSetup() != 0

		def drift_correct(self, location=None, boundary=None, el_draw_fixation=EL_TRUE, samples=EL_TRUE):
			"""

			:param location:
			:param el_draw_fixation:
			:param samples:
			:return: :raise ValueError:
			"""

			#todo: put in a special warning as the signature of this method has changed (boundary is new); ie
			# if boundary == EL_TRUE, throw an informative error
			location = Params.screen_c if location is None else location
			if not iterable(location):
				raise ValueError("Argument 'location' invalid; expected coordinate tuple or boundary label.")

			if not boundary:
				boundary = self.add_anonymous_boundary([location, self.dc_width // 2], CIRCLE_BOUNDARY)

			#todo: learn about fucking inflectors
			el_draw_fixation = EL_TRUE if el_draw_fixation in [EL_TRUE, True] else EL_FALSE
			samples = EL_TRUE if samples in [EL_TRUE, True] else EL_FALSE

			if not self.dummy_mode:
				try:
					self.doDriftCorrect(location[0], location[1], el_draw_fixation, samples)
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
			else:
				show_mouse_cursor()
				while True:
					self.experiment.ui_request()
					self.experiment.fill()
					self.experiment.blit(drift_correct_target(), 5, location)
					self.experiment.flip()
					fixated = self.within_boundary(boundary, EL_MOCK_EVENT)
					if fixated:
						hide_mouse_cursor()
						return fixated

		def gaze(self, eye_required=None, return_integers=True):
			if self.dummy_mode:
				try:
					return mouse_pos()
				except:
					raise RuntimeError("No gaze (or simulation) to report; both eye & mouse tracking unavailable.")
			sample = []
			if self.sample():
				if not eye_required:
					right_sample = self.__current_sample.isRightSample()
					left_sample = self.__current_sample.isLeftSample()
					if self.eye == EL_RIGHT_EYE and right_sample:
						sample = self.__current_sample.getRightEye().getGaze()
					if self.eye == EL_LEFT_EYE and left_sample:
						sample = self.__current_sample.getLeftEye().getGaze()
					if self.eye == EL_BOTH_EYES:
						sample = self.__current_sample.getLeftEye().getGaze()
				else:
					if eye_required == EL_LEFT_EYE:
						sample = self.__current_sample.getLeftEye().getGaze()
					if eye_required == EL_RIGHT_EYE:
						sample = self.__current_sample.getLeftEye().getGaze()
			else:
				if not self.__eye():
					return self.gaze()
				else:
					raise ValueError("Unable to collect a sample from the EyeLink.")

			return [int(sample[0]), int(sample[1])] if return_integers else sample

		def get_event_queue(self, include=[], exclude=[]):
			queue = []
			pumping = True
			while pumping:
				data = self.eyelink.getNextData()
				if data == 0:
					break
				# use only the include or exclude lists
				if len(include) and data in include:
					queue.append(self.eyelink.getFloatData())
				elif data not in exclude:
					queue.append(self.eyelink.getFloatData())
			return queue

		def now(self):
			return self.trackerTime() if not Params.development_mode else now()

		def sample(self):			
			self.__current_sample = self.getNewestSample()
			if self.__current_sample == 0:
				self.__current_sample = False
			return self.__current_sample

		def setup(self):
			if self.custom_display is None:
				self.openGraphics(Params.screen_x_y)
			else:
				openGraphicsEx(self.custom_display)
			if not self.dummy_mode:
				self.edf_filename = exp_file_name(EDF_FILE)
				flushGetkeyQueue()
				self.setOfflineMode()
				# TODO: have a default "can't connect to tracker; do you want to switch to dummy_mode" UI pop up
				# Running this with pylink installed whilst unconnected to a tracker throws: RuntimeError: Link terminated
				self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setLinkEventFilter("FIXATION,SACCADE,BLINK")
				self.openDataFile(self.edf_filename[0])
				self.write("DISPLAY_COORDS 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setSaccadeVelocityThreshold(Params.saccadic_velocity_threshold)
				self.setAccelerationThreshold(Params.saccadic_acceleration_threshold)
				self.setMotionThreshold(Params.saccadic_motion_threshold)
				self.calibrate()

		def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
			self.start_time = [now(), None]
			# ToDo: put some exceptions n here
			if self.dummy_mode: return True
			start = self.startRecording(samples, events, link_samples, link_events)
			if start == 0:
				self.start_time[1] = self.now()
				if self.__eye():
					self.write("TRIAL_ID {0}".format(str(trial_number)))
					self.write("TRIAL_START")
					self.write("SYNCTIME {0}".format('0.0'))
					return self.start_time - now()  # ie. delay spent initializing the recording

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

		def __within_boundary(self, label, event):
			"""
			For checking individual events; not for public use, but is a rather shared interface for the public methods
			within_boundary(), saccade_to_boundary(), fixated_boundary()
			:param event:
			:param label:
			:return:
			"""
			e_type = event.getType()
			if  e_type in [EL_SACCADE_START, EL_SACCADE_END, EL_FIXATION_START, EL_FIXATION_END]:
				start = [event.getStartGaze(), event.getStartPPD()]
				if e_type in [EL_SACCADE_END, EL_FIXATION_END]:
					timestamp = event.getStartTime()
				else:
					timestamp = event.getEndTime()
				end = [event.getEndGaze(), event.getEndPPD()]
				dx = (end[0][0] - start[0][0]) / ((end[1][0] + start[1][0]) / 2.0)
				dy = (end[0][1] - start[0][1]) / ((end[1][1] + start[1][1]) / 2.0)
			elif e_type == EL_GAZE_POS:
				timestamp = event.getTime()
				dx, dy = event.getGaze()
			result = super(EyeLink, self).within_boundary(label, math.sqrt(dx**2 + dy**2))
			return timestamp if result else False

		def within_boundary(self, label, inspect, event_queue=None, return_queue=False):
			"""
			For use when checking in real-time; uses entire event queue, whether supplied or fetched

			:param label:
			:param inspect:
			:return:
			"""

			if not event_queue:
				if inspect == EL_GAZE_POS:
					event_queue = [self.sample()]
				else:
					event_queue = self.el.get_event_queue(EL_ALL_EVENTS)
			for e in event_queue:
				if not self.__within_boundary(e, label, inspect):
					return False if not return_queue else [False, event_queue]
			return True if not return_queue else [True, event_queue]

		def saccade_to_boundary(self, label, inspect=EL_SACCADE_END, event_queue=None, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.

			:param label:
			:param return_queue:
			:return:
			"""
			# todo: only allow saccade start/end inspections
			if not event_queue:
				event_queue = self.el.get_event_queue([inspect] if not return_queue else EL_ALL_EVENTS)
			for e in event_queue:
				sacc_start_time = self.__within_boundary(e, label, inspect)
				if sacc_start_time:
					return sacc_start_time if not return_queue else [sacc_start_time, event_queue]
			return False

		def saccade_from_boundary(self, label, inspect=EL_SACCADE_START, event_queue=None, return_queue=False):
			"""
			Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
			In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
			impertinent.

			:param label:
			:param return_queue:
			:return:
			"""
			# todo: only allow saccade start/end inspections
			if not event_queue:
				event_queue = self.el.get_event_queue([inspect] if not return_queue else EL_ALL_EVENTS)
			for e in event_queue:
				sacc_start_time = self.__within_boundary(e, label, inspect)
				if not sacc_start_time:
					return sacc_start_time if not return_queue else [sacc_start_time, event_queue]
			return False

		def fixated_boundary(self, label, inspect=EL_FIXATION_END, event_queue=None, return_queue=False):
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
				event_queue = self.el.get_event_queue([inspect] if not return_queue else EL_ALL_EVENTS)
			for e in event_queue:
				fix_start_time = self.__within_boundary(e, label, inspect)
				if fix_start_time:
					return fix_start_time if not return_queue else [fix_start_time, event_queue]
			return False

		@abc.abstractmethod
		def listen(self, **kwargs):
			pass

		@property
		def dummy_mode(self):
			return self.__dummy_mode

		@dummy_mode.setter
		def dummy_mode(self, status):
				self.__dummy_mode = status

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
				name = "anonymous_{0}".format(self.__anonymous_boundaries)

			if shape not in [RECT_BOUNDARY, CIRCLE_BOUNDARY]:
				raise ValueError(
					"Argument 'shape' must be a shape constant (ie. EL_RECT_BOUNDARY, EL_CIRCLE_BOUNDARY).")

			self.add_boundary(name, bounds, shape)

		def clear_gaze_boundaries(self):
			# legacy function
			self.clear_boundaries()
			self.dc_width = Params.screen_y // 60
			dc_tl = [Params.screen_x // 2 - self.dc_width // 2, Params.screen_y // 2 - self.dc_width // 2]
			dc_br = [Params.screen_x // 2 + self.dc_width // 2, Params.screen_y // 2 + self.dc_width // 2]
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
			self.experiment.blit(Rectangle(width, height, [3, [255, 255, 255, 255]]).render(),
								 position=(boundary[0][0] - 3, boundary[0][1] - 3), registration=7)

		def remove_gaze_boundary(self, name):
			self.remove_boundary(name)
else:
	from klibs.KLDraw import drift_correct_target

class TryLink(BoundaryInspector):
	__dummy_mode = None
	__anonymous_boundaries = 0
	experiment = None
	__gaze_boundaries = {}
	custom_display = None
	dc_width = None  # ie. drift-correct width
	edf_filename = None
	unresolved_exceptions = 0
	eye = None
	start_time = [None, None]

	def __init__(self, experiment_instance):
		super(TryLink, self).__init__()
		self.experiment = experiment_instance
		self.__current_sample = False
		if DUMMY_MODE_AVAILABLE:
			self.dummy_mode = Params.eye_tracker_available is False if self.dummy_mode is None else self.dummy_mode is True
		else:
			self.dummy_mode = False
		self.dc_width = Params.screen_y // 60
		self.add_boundary("drift_correct", [Params.screen_c, self.dc_width // 2], CIRCLE_BOUNDARY)

	# REWRITE
	def __eye(self):
		self.eye = EL_NO_EYES
		return self.eye != EL_NO_EYES

	def calibrate(self):
		return

	# REWRITE
	def in_setup(self):
		return False

	def drift_correct(self, location=None, boundary=None,  el_draw_fixation=EL_TRUE, samples=EL_TRUE):
		"""

		:param location:
		:param el_draw_fixation:
		:param samples:
		:return: :raise ValueError:
		"""
		location = Params.screen_c if location is None else location
		if not iterable(location):
			raise ValueError("Argument 'location' invalid; expected coordinate tuple or boundary label.")

		if boundary is None:
			boundary = self.add_anonymous_boundary([location, self.dc_width // 2], CIRCLE_BOUNDARY)

		show_mouse_cursor()
		while True:
			self.experiment.ui_request()
			self.experiment.fill()
			self.experiment.blit(drift_correct_target(), 5, location)
			self.experiment.flip()
			fixated = self.within_boundary(boundary, EL_MOCK_EVENT)
			if fixated:
				hide_mouse_cursor()
				return fixated


	def gaze(self, eye_required=None, return_integers=True):
		try:
			return mouse_pos()
		except:
			raise RuntimeError("No gaze (or simulation) to report; both eye & mouse tracking unavailable.")

	def get_event_queue(self, include=[], exclude=[]):
		# todo: create an object with the same methods
		queue = []
		pumping = True
		while pumping:
			data = self.eyelink.getNextData()
			if data == 0:
				break
			# use only the include or exclude lists
			if len(include) and data in include:
				queue.append(self.eyelink.getFloatData())
			elif data not in exclude:
				queue.append(self.eyelink.getFloatData())
		return queue

	def now(self):
		return Params.clock.trial_time if Params.clock.start_time else Params.clock.timestamp

	def sample(self):
		self.__current_sample = MouseEvent()
		return self.__current_sample

	def getNextData(self):
		return MouseEvent()

	def setup(self):
		return self.calibrate()

	def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
		self.start_time = [Params.clock.timestamp, Params.clock.timestamp]
		if self.dummy_mode:
			return True
		else:
			self.write("TRIAL_ID {0}".format(str(trial_number)))
			self.write("TRIAL_START")
			self.write("SYNCTIME {0}".format('0.0'))
			return self.start_time - Params.clock.timestamp  # ie. delay spent initializing the recording

	def stop(self):
		pass

	def shut_down(self):
		return 0

	def write(self, message):
		if all(ord(c) < 128 for c in message):
			self.sendMessage(message)
		else:
			raise EyeLinkError("Only ASCII text may be written to an EDF file.")

	def __within_boundary(self, label, event):
		"""
		For checking individual events; not for public use, but is a rather shared interface for the public methods
		within_boundary(), saccade_to_boundary(), fixated_boundary()

		:param event:
		:param label:
		:return:
		"""
		timestamp = event.getTime()
		result = super(TryLink, self).within_boundary(label, event.getGaze())
		return timestamp if result else False

	def within_boundary(self, label, inspect=EL_MOCK_EVENT, event_queue=None, return_queue=False):
		"""
		For use when checking in real-time; uses entire event queue, whether supplied or fetched

		:param label:
		:param inspect:
		:return:
		"""
		result = self.__within_boundary(label, self.sample())
		return result if not return_queue else [result, event_queue]

	def saccade_to_boundary(self, label, inspect=EL_SACCADE_END, event_queue=None, return_queue=False):
		"""
		Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
		In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
		impertinent.

		:param label:
		:param return_queue:
		:return:
		"""
		# todo: only allow saccade start/end inspections
		sacc_start_time = self.__within_boundary(label, self.sample())
		if sacc_start_time:
			return sacc_start_time if not return_queue else [sacc_start_time, event_queue]
		return False

	def saccade_from_boundary(self, label, inspect=EL_SACCADE_START, event_queue=None, return_queue=False):
		"""
		Immediately returns from passed or fetched event queue the first saccade_end event in passed boundary.
		In the case of sharing an event queue, poll_events allows for retrieving eyelink events that are otherwise
		impertinent.

		:param label:
		:param return_queue:
		:return:
		"""
		# todo: only allow saccade start/end inspections
		sacc_start_time = self.__within_boundary(label, self.sample())
		if not sacc_start_time:
			return sacc_start_time if not return_queue else [sacc_start_time, event_queue]
		return False

	def fixated_boundary(self, label, inspect=EL_FIXATION_END, event_queue=None, return_queue=False):
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
		fix_start_time = self.__within_boundary(label, self.sample())
		if fix_start_time:
			return fix_start_time if not return_queue else [fix_start_time, event_queue]
		return False

	@abc.abstractmethod
	def listen(self, **kwargs):
		pass

	@property
	def dummy_mode(self):
		return self.__dummy_mode

	@dummy_mode.setter
	def dummy_mode(self, status):
		self.__dummy_mode = status

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
			name = "anonymous_{0}".format(self.__anonymous_boundaries)

		if shape not in [RECT_BOUNDARY, CIRCLE_BOUNDARY]:
			raise ValueError(
				"Argument 'shape' must be a shape constant (ie. EL_RECT_BOUNDARY, EL_CIRCLE_BOUNDARY).")

		self.add_boundary(name, bounds, shape)

	def clear_gaze_boundaries(self):
		# legacy function
		self.clear_boundaries()
		self.dc_width = Params.screen_y // 60
		dc_tl = [Params.screen_x // 2 - self.dc_width // 2, Params.screen_y // 2 - self.dc_width // 2]
		dc_br = [Params.screen_x // 2 + self.dc_width // 2, Params.screen_y // 2 + self.dc_width // 2]
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
		self.experiment.blit(Rectangle(width, height, [3, [255, 255, 255, 255]]).render(),
							 position=(boundary[0][0] - 3, boundary[0][1] - 3), registration=7)

	def remove_gaze_boundary(self, name):
		self.remove_boundary(name)

class MouseEvent(object):

	def __init__(self):
		super(MouseEvent, self).__init__()
		self.__sample = mouse_pos()
		if not Params.clock.start_time:
			self.__time = Params.clock.timestamp
		else:
			self.__time = Params.clock.trial_time

	def getGaze(self):
		return self.__sample

	def getTime(self):
		return self.__time

	def getStartTime(self):
		return self.__time

	def getEndTime(self):
		return self.__time