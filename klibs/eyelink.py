__author__ = 'jono'

try:
	import os
	import abc
	import time
	import pylink
	import params as Params
	from constants import *

	PYLINK_AVAILABLE = True

	class EyeLink(pylink.EyeLink):
		dummy_mode = False

		def __init__(self, dummy_mode=False):
			self.is_dummy_mode = dummy_mode

		def tracker_init(self, dummy_mode=False):
			if dummy_mode:
				self.is_dummy_mode = True
			pylink.flushGetkeyQueue()
			self.setOfflineMode()
			self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
			self.sendMessage("link_event_filter = SACCADE")
			self.sendMessage("link_event_data = SACCADE")
			self.sendMessage("DISPLAY_COORDS 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
			self.setSaccadeVelocityThreshold(Params.saccadic_velocity_threshold)
			self.setAccelerationThreshold(Params.saccadic_acceleration_threshold)
			self.setMotionThreshold(Params.saccadic_motion_threshold)

		def setup(self, file_name="TEST"):
			pylink.openGraphics(Params.screen_x_y)
			self.doTrackerSetup()
			self.openDataFile(file_name + EDF)
			self.filename = file_name

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

		def __eye(self):
			self.eye = self.eyeAvailable()
			return self.eye != EL_NO_EYES

		def sample(self):
			self.__current_sample = self.getNewestSample()
			return True

		def stop(self):
			self.stopRecording()

		def drift(self, location=None, events=EL_TRUE, samples=EL_TRUE, max_attempts=1):
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
				return pygame.mouse.get_pos()
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
				e = "Unable to collect a sample from the EyeLink."
				raise ValueError(e)

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
		def is_dummy_mode(self):
			return self.dummy_mode

		@is_dummy_mode.setter
		def is_dummy_mode(self, status):
			if type(status) is not bool:
				err_string = "Invalid argument provided for setting Eyelink.dummy_mode (boolean required, {0} passed."
				raise TypeError(err_string.format(type(status)))
			else:
				self.dummy_mode = True
except:
	PYLINK_AVAILABLE = False
	print "Warning: Pylink library not found; eye tracking will not be available."
