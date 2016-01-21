# -*- coding: utf-8 -*-
__author__ = 'jono'

from klibs.KLDraw import *
import time
import math
from klibs.KLUtilities import *
from klibs.KLDraw import *
try:
	import pylink
	PYLINK_AVAILABLE = True
except ImportError:
	print "\t* Warning: Pylink library not found; eye tracking will not be available."
	PYLINK_AVAILABLE = False

try:
	mouse = mouse_pos(True)
	if (type(x) is int for x in mouse):
		DUMMY_MODE_AVAILABLE = True
except:
	DUMMY_MODE_AVAILABLE = False


if PYLINK_AVAILABLE:
	class EyeLink(pylink.EyeLink):
		__dummy_mode = None
		experiment = None
		__gaze_boundaries = {}
		custom_display = None
		dc_width = None  # ie. drift-correct width
		edf_filename = None

		def __init__(self, experiment_instance):
			self.experiment = experiment_instance
			self.__current_sample = False
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
			self.clear_gaze_boundaries()

		def __eye(self):
			self.eye = self.eyeAvailable()
			return self.eye != EL_NO_EYES

		def calibrate(self):
			self.doTrackerSetup()

		def fetch_gaze_boundary(self, name=None):
			return self.__gaze_boundaries[name] if name is not None else self.__gaze_boundaries

		def add_gaze_boundary(self, name, bounds, shape=EL_RECT_BOUNDARY):
			if shape not in [EL_RECT_BOUNDARY, EL_CIRCLE_BOUNDARY]:
				raise ValueError("Argument 'shape' must be a shape constant (ie. EL_RECT_BOUNDARY, EL_CIRCLE_BOUNDARY).")
			# TODO:  handling for when a extant boundary would be over-written
			self.__gaze_boundaries[name] = {"shape": shape, "bounds": bounds}
			return True

		def clear_gaze_boundaries(self):
			self.__gaze_boundaries = {}
			self.dc_width = Params.screen_y // 60
			dc_tl = [Params.screen_x // 2 - self.dc_width // 2, Params.screen_y // 2 - self.dc_width //2]
			dc_br = [Params.screen_x // 2 + self.dc_width // 2, Params.screen_y // 2 + self.dc_width //2]
			self.add_gaze_boundary("drift_correct", [dc_tl, dc_br])
		
		def draw_gaze_boundary(self, name="*", blit=True):
			shape = None
			boundary = None
			try:
				boundary_dict = self.__gaze_boundaries[name]
				boundary = boundary_dict["bounds"]
				shape = boundary_dict['shape']
			except:
				if shape is None:
					raise IndexError("No boundary registered with name '{0}'.".format(boundary))
				if shape not in [EL_RECT_BOUNDARY, EL_CIRCLE_BOUNDARY]:
					raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			width = boundary[1][1] - boundary[0][1]
			height = boundary[1][0] - boundary[0][0]
			self.experiment.blit(Rectangle(width, height, [3, [255,255,255,255]]).render(), position=(boundary[0][0] - 3,boundary[0][1] -3) , registration=7)

		def remove_gaze_boundary(self, name):
			try:
				del(self.__gaze_boundaries[name])
			except KeyError:
				raise KeyError("Key '{0}' not found; No such gaze boundary exists!".format(name))

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
				if shape not in [EL_RECT_BOUNDARY, EL_CIRCLE_BOUNDARY]:
					raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
			if point is None:
				try:
					point = self.gaze()
				except ValueError as e:
					return False

			if shape == EL_RECT_BOUNDARY:
				x_range = range(boundary[0][0], boundary[1][0])
				y_range = range(boundary[0][1], boundary[1][1])
				ret_val = point[0] in x_range and point[1] in y_range
				return point[0] in x_range and point[1] in y_range

			if shape == EL_CIRCLE_BOUNDARY:
				r = (boundary[1][0] - boundary[0][0]) // 2
				center = (boundary[0][0] + r, boundary[0][1] + r)
				d_x = point[0] - center[0]
				d_y = point[1] - center[1]
				center_point_dist = math.sqrt(d_x**2 + d_y**2)
				print "r: {0}, center: {1}, d_x: {2}, d_y: {3}, cpt: {4}, \n boundary: {5}, point: {6}".format(r, center, d_x, d_y, center_point_dist, boundary, point)
				return center_point_dist <= r

		def is_gaze_boundary(self, string):
			return type(string) is str and string in self.__gaze_boundaries

		def drift_correct(self, location=None, events=EL_TRUE, samples=EL_TRUE):
			"""

			:param location:
			:param events:
			:param samples:
			:return: :raise ValueError:
			"""
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
				self.doDriftCorrect(location[0], location[1], events, samples)
				return self.applyDriftCorrect()
			else:
				def dc(dc_location, dc_gaze_boundary):
					hide_mouse_cursor()
					pump()
					self.experiment.fill()
					self.experiment.track_mouse()
					self.custom_display.draw_cal_target(dc_location, flip=False)
					self.experiment.flip()
					in_bounds = self.within_boundary(dc_gaze_boundary, self.gaze())
					return  in_bounds
				return self.experiment.listen(MAX_WAIT, OVER_WATCH, wait_callback=dc, dc_location=location, dc_gaze_boundary=gaze_boundary)

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

		def sample(self):			
			self.__current_sample = self.getNewestSample()
			if self.__current_sample == 0:
				self.__current_sample = False
			return self.__current_sample

		def setup(self):
			if self.custom_display is None:
				self.openGraphics(Params.screen_x_y)
			else:
				pylink.openGraphicsEx(self.custom_display)
			if not self.dummy_mode:
				self.edf_filename = exp_file_name(EDF_FILE)
				pylink.flushGetkeyQueue()
				self.setOfflineMode()
				# TODO: have a default "can't connect to tracker; do you want to switch to dummy_mode" UI pop up
				# Running this with pylink installed whilst unconnected to a tracker throws: RuntimeError: Link terminated
				self.sendCommand("screen_pixel_coords = 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setLinkEventFilter("FIXATION,SACCADE,BLINK")
				self.openDataFile(self.edf_filename[0])
				self.sendMessage("DISPLAY_COORDS 0 0 {0} {1}".format(Params.screen_x, Params.screen_y))
				self.setSaccadeVelocityThreshold(Params.saccadic_velocity_threshold)
				self.setAccelerationThreshold(Params.saccadic_acceleration_threshold)
				self.setMotionThreshold(Params.saccadic_motion_threshold)
				self.calibrate()

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
			if self.isRecording() == 0: 
				self.stopRecording()
			self.setOfflineMode()
			self.closeDataFile()
			self.receiveDataFile(self.edf_filename[0], self.edf_filename[1])
			return self.close()

		@abc.abstractmethod
		def listen(self, **kwargs):
			pass

		@property
		def dummy_mode(self):
			return self.__dummy_mode

		@dummy_mode.setter
		def dummy_mode(self, status):
				self.__dummy_mode = status

