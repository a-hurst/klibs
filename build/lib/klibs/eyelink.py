__author__ = 'jono'

try:
	import os
	import abc
	import time
	import pylink
	import params as Params
	import sdl2
	from constants import *
	from utility_functions import *

	try:
		from pymouse import PyMouse

		DUMMY_MODE_AVAILABLE = True
	except ImportError:
		DUMMY_MODE_AVAILABLE = False

	PYLINK_AVAILABLE = True

	class EyeLink(pylink.EyeLink):
		__dummy_mode = None
		__app_instance = None
		__gaze_boundaries = {}

		def __init__(self, app_instance):
			self.__app_instance = app_instance

			if DUMMY_MODE_AVAILABLE:
				self.dummy_mode = Params.eye_tracker_available if self.dummy_mode is None else self.dummy_mode is True
			else:
				self.dummy_mode = False

		def __eye(self):
			self.eye = self.eyeAvailable()
			return self.eye != EL_NO_EYES

		def add_gaze_boundary(self, name, bounds, shape=RECT):  # todo: make this bad boy take more than bounding rects
			if shape not in [RECT, CIRCLE]:
				raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			self.__gaze_boundaries[name] = {"shape": shape, "bounds": bounds}
			return True

		def within_boundary(self, boundary, point=None, shape=None):
			try:
				boundary_dict = self.__gaze_boundaries[boundary]
				print boundary_dict
				boundary = boundary_dict["bounds"]
				shape = boundary_dict['shape']
			except:
				if shape is None:
					raise IndexError("No boundary registered with given name.")
				if shape not in [RECT, CIRCLE]:
					raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			if point is None:
				if self.dummy_mode:
					point = mouse_pos()
				else:
					point = self.gaze()
			if shape == RECT:
				x_range = range(boundary[0][0], boundary[1][0])
				y_range = range(boundary[0][1], boundary[1][1])
				return point[0] in x_range and point[1] in y_range
			if shape == CIRCLE:
				return boundary[0] <= math.sqrt((point[0] - boundary[1][0]) ** 2 + (point[1] - boundary[1][1]) ** 2)

		def drift_correct(self, location=None, events=EL_TRUE, samples=EL_TRUE, max_attempts=1):
			location = Params.screen_c if location is None else location
			attempts = 1
			result = None
			try:
				iter(location)
			except:
				raise ValueError("Argument 'location' wasn't understood; must be a x, y location.")

			if events == EL_TRUE:
				if samples == EL_TRUE:
					result = self.doDriftCorrect(location[0], location[1], 1, 1)
				else:
					result = self.doDriftCorrect(location[0], location[1], 1, 0)
			elif samples:
				result = self.doDriftCorrect(location[0], location[1], 0, 1)
			else:
				result = self.el.doDriftCorrect(location[0], location[1], 0, 0)
			# if attempts < maxAttempts:
			# 	return self.drift(loc, events, samples, maxAttempts-1)
			# else:
			# 	return False
			# if result == 27 and attempts < maxAttempts:
			# 	return self.drift(loc, events, samples, maxAttempts-1)
			# elif result == 27 and attempts > maxAttempts:
			# 	return False
			# else:
			# 	return True
			return True

		def gaze(self, eye_required=None):
			if self.dummy_mode:
				return self.mouse_pos()
			if self.sample():
				if not eye_required:
					right_sample = self.__current_sample.isRightSample()
					left_sample = self.__current_sample.isLeftSample()
					if self.eye == EL_RIGHT_EYE and right_sample:
						return self.__current_sample.getRightEye().getGaze()
					if self.eye == EL_LEFT_EYE and left_sample:
						gaze = self.__current_sample.getLeftEye().getGaze()
						print gaze
						return gaze
					if self.eye == EL_BOTH_EYES:
						return self.__current_sample.getLeftEye().getGaze()
				else:
					if eye_required == EL_LEFT_EYE:
						return self.__current_sample.getLeftEye().getGaze()
					if eye_required == EL_RIGHT_EYE:
						return self.__current_sample.getLeftEye().getGaze()
			else:
				raise ValueError("Unable to collect a sample from the EyeLink.")

		def sample(self):
			self.__current_sample = self.getNewestSample()
			return True

		def setup(self):
			self.doTrackerSetup()
			self.filename = exp_file_name(EDF_FILE)
			self.openDataFile()

		def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
			# ToDo: put some exceptions n here
			start = self.startRecording(samples, events, link_samples, link_events)
			if start == 0:
				if self.__eye():
					self.sendMessage("TRIAL_ID {0}".format(str(trial_number)))
					self.sendMessage("TRIAL_START")
					self.sendMessage("SYNCTIME {0}".format('0.0'))
					return True
				else:
					return False
			else:
				return False

		def stop(self):
			self.stopRecording()

		def tracker_init(self):
			if not self.dummy_mode:
				pylink.flushGetkeyQueue()
				self.setOfflineMode()
				self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.sendMessage("link_event_filter = SACCADE")
				self.sendMessage("link_event_data = SACCADE")
				self.sendMessage("DISPLAY_COORDS 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setSaccadeVelocityThreshold(Params.saccadic_velocity_threshold)
				self.setAccelerationThreshold(Params.saccadic_acceleration_threshold)
				self.setMotionThreshold(Params.saccadic_motion_threshold)
				return True
			return True

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
				self.__dummy_mode = True
except:
	PYLINK_AVAILABLE = False
	print "Warning: Pylink library not found; eye tracking will not be available."
