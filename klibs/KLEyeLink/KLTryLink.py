# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import abc
from sdl2 import SDL_MOUSEBUTTONDOWN
from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import EyeLinkError
from klibs.KLConstants import CIRCLE_BOUNDARY, RECT_BOUNDARY, EL_NO_EYES, EL_MOCK_EVENT, EL_TRUE, EL_SACCADE_END,\
	EL_SACCADE_START, EL_FIXATION_END, TK_S, TK_MS
from klibs import P
from klibs.KLUtilities import iterable, mouse_pos, show_mouse_cursor, hide_mouse_cursor, pump
from klibs.KLBoundary import BoundaryInspector
from klibs.KLGraphics import fill, blit, flip
from klibs.KLGraphics.KLDraw import drift_correct_target
from klibs.KLUserInterface import ui_request


class TryLink(EnvAgent, BoundaryInspector):
	__dummy_mode__ = None
	__anonymous_boundaries__ = 0
	__gaze_boundaries__ = {}
	experiment = None
	custom_display = None
	dc_width = None  # ie. drift-correct width
	edf_filename = None
	unresolved_exceptions = 0
	eye = None
	start_time = [None, None]

	def __init__(self):
		EnvAgent.__init__(self)
		BoundaryInspector.__init__(self)
		self.__current_sample__ = False
		self.dummy_mode = P.eye_tracker_available is False if self.dummy_mode is None else self.dummy_mode is True

	# REWRITE
	def __eye__(self):
		self.eye = EL_NO_EYES
		return self.eye != EL_NO_EYES

	def __within_boundary__(self, label, event):
		"""
		For checking individual events; not for public use, but is a rather shared interface for the public methods
		within_boundary(), saccade_to_boundary(), fixated_boundary()

		:param event:
		:param label:
		:return:
		"""
		timestamp = event.getTime()
		return timestamp if super(TryLink, self).within_boundary(label, event.getGaze()) else False

	def calibrate(self):
		pass
	# REWRITE

	def clear_queue(self):
		pass

	def drift_correct(self, location=None, boundary=None,  el_draw_fixation=EL_TRUE, samples=EL_TRUE):
		"""

		:param location:
		:param el_draw_fixation:
		:param samples:
		:return: :raise ValueError:
		"""
		location = P.screen_c if location is None else location
		if not iterable(location):
			raise ValueError("Argument 'location' invalid; expected coordinate tuple or boundary label.")

		if boundary is None:
			boundary = "drift_correct"

		show_mouse_cursor()
		while True:
			event_queue = pump(True)
			ui_request(queue=event_queue)
			fill()
			blit(drift_correct_target(), 5, location)
			flip()
			for e in event_queue:
				if e.type == SDL_MOUSEBUTTONDOWN and super(TryLink, self).within_boundary(boundary, [e.button.x, e.button.y]):
					hide_mouse_cursor()
					return 0
					# fixated = self.within_boundary(boundary, EL_MOCK_EVENT, event_queue=event_queue)
					# if clicked:
					# 	return fixated

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
		fix_start_time = self.__within_boundary__(label, self.sample())
		if fix_start_time:
			return fix_start_time if not return_queue else [fix_start_time, event_queue]
		return False

	def in_setup(self):
		return False

	def gaze(self, eye_required=None, return_integers=True):
		try:
			return mouse_pos()
		except:
			raise RuntimeError("No gaze (or simulation) to report; both eye & mouse tracking unavailable.")

	def get_event_queue(self, include=[], exclude=[]):
		# todo: create an object with the same methods
		return [MouseEvent()]

	def getNextData(self):
		return MouseEvent()

	def now(self, unit=TK_S):
		if unit == TK_MS:
			return self.evm.trial_time_ms if self.evm.start_time else self.evm.timestamp
		return self.evm.trial_time if self.evm.start_time else self.evm.timestamp

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
		sacc_start_time = self.__within_boundary__(label, self.sample())
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
		sacc_start_time = self.__within_boundary__(label, self.sample())
		if not sacc_start_time:
			return sacc_start_time if not return_queue else [sacc_start_time, event_queue]
		return False

	def sample(self):
		self.__current_sample__ = MouseEvent()
		return self.__current_sample__

	def setup(self):
		self.dc_width = P.screen_y // 60
		self.add_boundary("drift_correct", [P.screen_c, self.dc_width // 2], CIRCLE_BOUNDARY)
		return self.calibrate()

	def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
		self.start_time = [self.evm.timestamp, self.evm.timestamp]
		if self.dummy_mode:
			return True
		else:
			self.write("TRIAL_ID {0}".format(str(trial_number)))
			self.write("TRIAL_START")
			self.write("SYNCTIME {0}".format('0.0'))
			return self.evm.timestamp - self.start_time[0] # ie. delay spent initializing the recording

	def stop(self):
		pass

	def shut_down(self):
		return 0

	def write(self, message):
		if all(ord(c) < 128 for c in message):
			pass
		else:
			raise EyeLinkError("Only ASCII text may be written to an EDF file.")

	def within_boundary(self, label, inspect=EL_MOCK_EVENT, event_queue=None, return_queue=False):
		"""
		For use when checking in real-time; uses entire event queue, whether supplied or fetched

		:param label:
		:param inspect:
		:return:
		"""
		result = self.__within_boundary__(label, self.sample())
		return result if not return_queue else [result, event_queue]

	@abc.abstractmethod
	def listen(self, **kwargs):
		pass

	@property
	def dummy_mode(self):
		return self.__dummy_mode__

	@dummy_mode.setter
	def dummy_mode(self, status):
		self.__dummy_mode__ = status

	# Everything from here down are legacy functions that wrap newer counterparts with different names for
	# backwards compatibility

	def shut_down_eyelink(self):
		pass

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

	def draw_gaze_boundary(self, label="*"):
		return self.draw_boundary(label)

		shape = None
		boundary = None
		try:
			boundary_dict = self.__gaze_boundaries__[label]
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

class MouseEvent(EnvAgent):

	def __init__(self):
		super(MouseEvent, self).__init__()
		self.__sample__ = mouse_pos()
		if not self.evm.start_time:
			self.__time__ = self.evm.timestamp
		else:
			self.__time__ = self.evm.trial_time

	def getGaze(self):
		return self.__sample__

	def getTime(self):
		return self.__time__

	def getStartTime(self):
		return self.__time__

	def getEndTime(self):
		return self.__time__
