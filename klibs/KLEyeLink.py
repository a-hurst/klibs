__author__ = 'jono'
PYLINK_AVAILABLE = False
import ctypes
from KLDraw import *

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
	print "\tPylink library found! EyeTracking available!"

	class EyeLink(pylink.EyeLink):
		__dummy_mode = None
		experiment = None
		__gaze_boundaries = {}
		custom_display = None

		def __init__(self, experiment_instance):
			self.experiment = experiment_instance
			if Params.eye_tracker_available:
				try:
					pylink.EyeLink.__init__(self)
				except RuntimeError as e:
					if e.message == "Could not connect to tracker at 100.1.1.1":
						print "Could not connect to tracker at 100.1.1.1. If EyeLink machine is on, ready & connected try turning off the wifi on this machine."
			if DUMMY_MODE_AVAILABLE:
				self.dummy_mode = Params.eye_tracker_available is False if self.dummy_mode is None else self.dummy_mode is True
			else:
				self.dummy_mode = False
			self.dc_width = Params.screen_y // 60
			dc_tl = [Params.screen_x // 2 - self.dc_width // 2, Params.screen_y // 2 - self.dc_width //2]
			dc_br = [Params.screen_x // 2 + self.dc_width // 2, Params.screen_y // 2 + self.dc_width //2]
			self.add_gaze_boundary("drift_correct", [dc_tl, dc_br])

		def __eye(self):
			self.eye = self.eyeAvailable()
			return self.eye != EL_NO_EYES

		def add_gaze_boundary(self, name, bounds, shape=RECT):  # todo: make this bad boy take more than bounding rects
			if shape not in [RECT, CIRCLE]:
				raise ValueError("Argument 'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			# TODO:  handling for when a extant boundary would be over-written
			self.__gaze_boundaries[name] = {"shape": shape, "bounds": bounds}
			return True

		def within_boundary(self, boundary, point=None, shape=None):
			debug = False
			if debug: print "within_boundary(boundary={0}, point={1}, shape={2}".format(boundary, point, shape)
			try:
				boundary_dict = self.__gaze_boundaries[boundary]
				boundary = boundary_dict["bounds"]
				shape = boundary_dict['shape']
			except:
				if shape is None:
					raise IndexError("No boundary registered with name '{0}'.".format(boundary))
				if shape not in [RECT, CIRCLE]:
					raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			if point is None:
				try:
					point = self.gaze()
				except Exception as e:
					print e.message
					print "Warning: Using mouse_pos()"
					try:
						point = mouse_pos()
					except:
						raise EnvironmentError("Nothing to track! One of either eye or mouse tracking required.")
			if shape == RECT:
				x_range = range(boundary[0][0], boundary[1][0])
				y_range = range(boundary[0][1], boundary[1][1])
				ret_val = point[0] in x_range and point[1] in y_range
				if debug: print "POINT: {0}, X_RANGE: {1}, Y_RANGE: {2}, RET_VAL:{3}".format(point, (x_range[0], x_range[-1]),(y_range[0], y_range[-1]), ret_val )
				return point[0] in x_range and point[1] in y_range

			if shape == CIRCLE:
				return boundary[0] <= math.sqrt((point[0] - boundary[1][0]) ** 2 + (point[1] - boundary[1][1]) ** 2)

		def is_gaze_boundary(self, string):
			return type(string) is str and string in self.__gaze_boundaries

		def drift_correct(self, location=None, events=EL_TRUE, samples=EL_TRUE):
			location = Params.screen_c if location is None else location
			gaze_boundary = None
			try:
				if self.is_gaze_boundary(location):
					gaze_boundary = location
				else:
					raise ValueError
			except ValueError:
				try:
					iter(location)
					dc_pad = self.dc_width // 2
					top_left = [location[0] - dc_pad, location[1] - dc_pad]
					bottom_right = [location[0] + dc_pad, location[1] + dc_pad]
					names_checked = 0
					not_unique = True
					while not_unique:
						gaze_boundary = 'custom_dc_{0}'.format(names_checked)
						not_unique = self.is_gaze_boundary(gaze_boundary)
						names_checked += 1
					self.add_gaze_boundary(gaze_boundary, [top_left, bottom_right])
				except Exception as e:
					print e.message
					raise ValueError("Argument 'location' wasn't understood; must be an x,y location or gaze boundary name.")

			events = EL_TRUE if events in [EL_TRUE, True] else EL_FALSE
			samples = EL_TRUE if samples in [EL_TRUE, True] else EL_FALSE
			if not self.dummy_mode:
				return self.doDriftCorrect(location[0], location[1], events, samples)
			else:
				def dc(dc_location, dc_gaze_boundary):
					hide_mouse_cursor()
					pump()
					self.experiment.fill()
					self.custom_display.draw_cal_target(dc_location, flip=False)
					self.experiment.track_mouse()
					self.experiment.flip()
					in_bounds = self.within_boundary(dc_gaze_boundary, self.gaze())
					return  in_bounds
				return self.experiment.listen(MAX_WAIT, OVER_WATCH, wait_callback=dc, dc_location=location, dc_gaze_boundary=gaze_boundary)

		def gaze(self, eye_required=None, return_integers=True):
			debug = False
			if debug: print "gaze(eye_required={0}, return_integers={1}".format(eye_required, return_integers)
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
				self.filename = exp_file_name(EDF_FILE)
				pylink.flushGetkeyQueue()
				self.setOfflineMode()
				self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setLinkEventFilter("SACCADE,BLINK")
				self.openDataFile(self.filename[0])
				self.sendMessage("DISPLAY_COORDS 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setSaccadeVelocityThreshold(Params.saccadic_velocity_threshold)
				self.setAccelerationThreshold(Params.saccadic_acceleration_threshold)
				self.setMotionThreshold(Params.saccadic_motion_threshold)
				self.doTrackerSetup()

		def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
			start = time.time()
			# ToDo: put some exceptions n here
			if self.dummy_mode: return True
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
			if self.eyelink.isRecording() == 0: self.eyelink.stopRecording()
			self.setOfflineMode()
			self.closeDataFile()
			self.receiveDataFile(self.file_name[0], self.file_name[1])
			return self.eyelink.close()

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
