__author__ = 'jono'
PYLINK_AVAILABLE = False
import ctypes

try:
	import os
	import abc
	import time
	import pylink
	import KLParams as Params
	import sdl2
	from KLConstants import *
	from KLUtilities import *

	try:
		mouse = mouse_pos(True)
		if (type(x) is int for x in mouse):
			DUMMY_MODE_AVAILABLE = True
	except ImportError:
		DUMMY_MODE_AVAILABLE = False

	PYLINK_AVAILABLE = True
	print "Pylink library found! EyeTracking available!"

	class KLEyeLink(pylink.EyeLink):
		__dummy_mode = None
		__app_instance = None
		__gaze_boundaries = {}
		custom_display = None

		def __init__(self):
			try:
				pylink.EyeLink.__init__(self)
			except:
				Params.eye_tracker_available = False
			if DUMMY_MODE_AVAILABLE:
				self.dummy_mode = Params.eye_tracker_available is False if self.dummy_mode is None else self.dummy_mode is True
			else:
				self.dummy_mode = False
			dc_width = Params.screen_y // 60
			dc_tl = [Params.screen_x // 2 - dc_width // 2, Params.screen_y // 2 - dc_width //2]
			dc_br = [Params.screen_x // 2 + dc_width // 2, Params.screen_y // 2 + dc_width //2]
			self.add_gaze_boundary("drift_correct", [dc_tl, dc_br])

		def __eye(self):
			self.eye = self.eyeAvailable()
			return self.eye != EL_NO_EYES

		def add_gaze_boundary(self, name, bounds, shape=RECT):  # todo: make this bad boy take more than bounding rects
			if shape not in [RECT, CIRCLE]:
				raise ValueError("Argument 'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			self.__gaze_boundaries[name] = {"shape": shape, "bounds": bounds}
			return True

		def within_boundary(self, boundary, point=None, shape=None):
			try:
				boundary_dict = self.__gaze_boundaries[boundary]
				boundary = boundary_dict["bounds"]
				shape = boundary_dict['shape']
			except:
				if shape is None:
					raise IndexError("No boundary registered with given name.")
				if shape not in [RECT, CIRCLE]:
					raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			if point is None:
				try:
					point = self.gaze()
				except:
					try:
						point = mouse_pos()
					except:
						raise EnvironmentError("Nothing to track! One of either eye or mouse tracking required.")
			if shape == RECT:
				x_range = range(boundary[0][0], boundary[1][0])
				y_range = range(boundary[0][1], boundary[1][1])
				return point[0] in x_range and point[1] in y_range
			if shape == CIRCLE:
				return boundary[0] <= math.sqrt((point[0] - boundary[1][0]) ** 2 + (point[1] - boundary[1][1]) ** 2)

		def drift_correct(self, location=None, events=EL_TRUE, samples=EL_TRUE):
			location = Params.screen_c if location is None else location
			try:
				iter(location)
			except:
				raise ValueError("Argument 'location' wasn't understood; must be a x, y location.")

			events = EL_TRUE if events in [EL_TRUE, True] else EL_FALSE
			samples = EL_TRUE if samples in [EL_TRUE, True] else EL_FALSE
			if not self.dummy_mode:
				drift_correct_result = self.doDriftCorrect(location[0], location[1], events, samples)
			else:
				drift_correct_result = False
				while not drift_correct_result:
					drift_correct_result = self.within_boundary('drift_correct', self.gaze())

			return drift_correct_result

		def gaze(self, eye_required=None, return_integers=True):
			if self.dummy_mode:
				try:
					return mouse_pos()
				except:
					raise EnvironmentError("No gaze (or simulation) to report; both eye & mouse tracking unavailable.")
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
				raise ValueError("Unable to collect a sample from the EyeLink.")

			return [int(sample[0]), int(sample[1])] if return_integers else sample

		def sample(self):
			self.__current_sample = self.getNewestSample()
			return self.__current_sample

		def setup(self):
			if self.custom_display is None:
				self.openGraphics(Params.screen_x_y)
			else:
				pylink.openGraphicsEx(self.custom_display)
			if not self.dummy_mode:
				pylink.flushGetkeyQueue()
				self.setOfflineMode()
				self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setLinkEventFilter("SACCADE,BLINK")
				self.filename = exp_file_name(EDF_FILE)
				self.openDataFile(self.filename)
				self.sendMessage("DISPLAY_COORDS 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setSaccadeVelocityThreshold(Params.saccadic_velocity_threshold)
				self.setAccelerationThreshold(Params.saccadic_acceleration_threshold)
				self.setMotionThreshold(Params.saccadic_motion_threshold)
				self.doTrackerSetup()

		def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
			start = time.time()
			# ToDo: put some exceptions n here
			start = self.startRecording(samples, events, link_samples, link_events)
			if start == 0:
				if self.__eye():
					self.sendMessage("TRIAL_ID {0}".format(str(trial_number)))
					self.sendMessage("TRIAL_START")
					self.sendMessage("SYNCTIME {0}".format('0.0'))
					return start - time.time()  # ie. delay spent initializing the recording
				else:
					return False
			else:
				return False

		def stop(self):
			self.stopRecording()

		def shut_down_eyelink(self):
			self.stopRecording()
			self.setOfflineMode()
			time.sleep(0.5)
			self.closeDataFile()  # tell eyelink to close_data_file()
			self.receiveDataFile(self.filename, Params.edf_path + self.filename)  # copy pa.EDF
			self.close()

		@abc.abstractmethod
		def listen(self, **kwargs):
			pass

		@property
		def dummy_mode(self):
			return self.__dummy_mode

		@dummy_mode.setter
		def dummy_mode(self, status):
				self.__dummy_mode = status
except:
	print "Warning: Pylink library not found; eye tracking will not be available."
