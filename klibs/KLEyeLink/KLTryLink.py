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

	def __eye__(self):
		self.eye = EL_NO_EYES
		return self.eye != EL_NO_EYES

	def __within_boundary__(self, label, event, report=None, inspect=None):
		"""
		For checking individual events; not for public use, but is a rather shared interface for the public methods
		within_boundary(), saccade_to_boundary(), fixated_boundary()

		:param event:
		:param label:
		:return:
		"""
		timestamp = event.getTime()
		return timestamp if super(TryLink, self).within_boundary(label, event.getGaze()) else False

	def __exited_boundary__(self, label, event, report):
		timestamp = event.getTime()
		return timestamp if not super(TryLink, self).within_boundary(label, event.getGaze()) else False

	def calibrate(self):
		pass

	def clear_queue(self):
		pass

	def drift_correct(self, location=None, boundary=None,  el_draw_fixation=EL_TRUE, samples=EL_TRUE, fill_color=None):
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
			fill(P.default_drift_correct_fill_color if not fill_color else fill_color)
			blit(drift_correct_target(), 5, location)
			flip()
			for e in event_queue:
				if e.type == SDL_MOUSEBUTTONDOWN and super(TryLink, self).within_boundary(boundary, [e.button.x, e.button.y]):
					hide_mouse_cursor()
					return 0
					# fixated = self.within_boundary(boundary, EL_MOCK_EVENT, event_queue=event_queue)
					# if clicked:
					# 	return fixated

	def fixated_boundary(self, label, valid_events=None, inspect=EL_FIXATION_END, event_queue=None, report=None,
						 return_queue=False):
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

	def in_setup(self):
		return False

	def now(self):
		return self.evm.trial_time if self.evm.start_time else self.evm.timestamp

	def saccade_to_boundary(self, label, valid_events=None, event_queue=None,
							report=None, inspect=None, return_queue=False):
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

	def within_boundary(self, label, valid_events, event_queue=None, report=EL_TRUE, inspect=None,
						return_queue=False):
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
