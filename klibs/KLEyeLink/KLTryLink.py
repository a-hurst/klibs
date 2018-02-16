# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

from klibs.KLEnvironment import EnvAgent
from klibs.KLExceptions import EyeLinkError
from klibs.KLConstants import (CIRCLE_BOUNDARY, RECT_BOUNDARY, EL_NO_EYES, EL_MOCK_EVENT, EL_TRUE,
	EL_GAZE_POS, EL_SACCADE_END, EL_SACCADE_START, EL_FIXATION_END, EL_ALL_EVENTS, EL_TIME_START,
	TK_S, TK_MS)
from klibs import P
from klibs.KLUtilities import (angle_between, iterable, mouse_pos, show_mouse_cursor,
	hide_mouse_cursor, pump)
from klibs.KLBoundary import BoundaryInspector
from klibs.KLGraphics import fill, blit, flip
from klibs.KLGraphics.KLDraw import drift_correct_target
from klibs.KLUserInterface import ui_request

from sdl2 import SDL_MOUSEBUTTONDOWN, SDL_GetTicks
from math import atan2, radians
import abc


class TryLink(EnvAgent, BoundaryInspector):
	__anonymous_boundaries__ = 0
	__gaze_boundaries__ = {}
	custom_display = None
	version = "TryLink"
	dc_width = None  # ie. drift-correct width
	edf_filename = None
	unresolved_exceptions = 0
	start_time = [None, None]
	initialized = False
	__recording__ = False
	__eye_used__ = None
	last_mouse_pos = None
	last_mouse_time = None
	mouse_event_queue = []

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

	def __exited_boundary__(self, label, event, report=None):
		timestamp = event.getTime()
		return timestamp if not super(TryLink, self).within_boundary(label, event.getGaze()) else False

	def __saccade_in_direction__(self, doi, event, report):
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
		pass

	def clear_queue(self):
		self.mouse_event_queue = []

	def drift_correct(self, location=None, boundary=None, el_draw_fixation=EL_TRUE, samples=EL_TRUE, fill_color=None, target_img=None):
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
			if el_draw_fixation == EL_TRUE:
					fill(P.default_fill_color if not fill_color else fill_color)
					blit(drift_correct_target() if target_img is None else target_img, 5, location)
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
		"""
		The TryLink get_event_queue functions aims to roughly emulate the functionality of its EyeLinkExt 
		counterpart, which is to retrieve any gaze events in the EyeLink queue that haven't been retreived yet.
		As a stand-in for actual gaze, we check for SDL_MOUSEMOTION events every time pump() is called and add
		and that have occured to a queue named mouse_event_queue in the TryLink object. This function iterates
		over the SDL_MOUSEMOTION events in that queue, returning EL_SACCADE_END and EL_FIXATION_END MouseEvent
		objects.

		When there are two or more events in the mouse_event_queue, this function iterates over them, comparing
		each event to the one that follows it to see whether

		a) the difference between the positions is greater than a threshold (3 pixels in any direction)
		b) the time between the current mouse motion and the next one is greater than two screen refreshes, and
		c) the difference in angle between the current mouse motion and the next one is greater than 45 degrees.

		If a) is false, the function skips over the next event in sequence, and b) and c) are not checked.

		If b) is true, an end saccade event and an end fixation event are both added to the output queue. If c) is 
		true, only an end saccade event is added to the output queue. In both cases, a position marker is moved up
		the list to the position of the next MOUSEMOTION event, so that older events aren't part of future
		fixations or saccades. After iterating over all events in the mouse_event_queue, all events that have been
		part of a fixation or saccade are removed from the queue.
		"""

		#TODO: since some event types can be enabled/disabled manually on the eyelink, make
		#common interface for both EyeLinkExt and TryLink whereby events can be enabled/disabled
		#in params. (?)

		queue = []
		samples = True if EL_GAZE_POS in include or (not len(include) and EL_GAZE_POS not in exclude) else False
		events = True if include != [EL_GAZE_POS] and exclude != EL_ALL_EVENTS else False

		mouse_queue_length = len(self.mouse_event_queue)
		if mouse_queue_length == 0:
			return queue
		elif mouse_queue_length == 1:
			if samples:
				queue.append(MouseEvent())
		else:
			if samples:
				queue.append(MouseEvent())
			if events:
				start_pos = 0
				offset = 0
				for i in range(0, mouse_queue_length-1):
					e_first = self.mouse_event_queue[start_pos].motion
					e = self.mouse_event_queue[i-offset].motion
					e_next = self.mouse_event_queue[i+1].motion
					event_types = []

					if abs(e_next.x-e.x) < 4 and abs(e_next.y-e.y) < 4:
						offset += 1
					elif (e_next.timestamp-e.timestamp) > (P.refresh_time * 2 + 1):
						# if two adjacent mouse motion events are separated by more than two flips,
						# treat e as the end of a saccade, e_next as the start of a saccade, and 
						# the interval between them as a fixation.
						event_types.append(EL_SACCADE_END)
						event_types.append(EL_FIXATION_END)
					
					else:
						dot_product = e.xrel*e_next.xrel + e.yrel*e_next.yrel
						determinant = e.xrel*e_next.yrel + e.yrel*e_next.xrel
						angle = atan2(determinant, dot_product)
						threshold = radians(45) # greater than 45 degrees difference means new saccade
						if not (threshold >= angle >= -threshold):
							event_types.append(EL_SACCADE_END)
					
					# Filter events returned based on include/exclude criteria
					if len(event_types): # if any events have occured this loop
						# update the starting event and reset the offset value before next loop
						start_pos = i+1
						offset = 0
						for d_type in event_types:
							if len(include) and d_type not in include:
								continue
							if len(exclude) and d_type in exclude:
								continue
							if d_type == EL_SACCADE_END:
								if P.development_mode:
									print "saccade: {0},{1} to {2},{3}".format(e_first.x-e_first.xrel, e_first.y-e_first.yrel, e.x, e.y)
								queue.append(MouseEvent(start_event=e_first, end_event=e, el_type=EL_SACCADE_END))
							elif d_type == EL_FIXATION_END:
								if P.development_mode:
									print "fixation: {0}".format(e_next.timestamp-e.timestamp)
								queue.append(MouseEvent(start_event=e, end_event=e_next, el_type=EL_FIXATION_END))
						


				
				self.mouse_event_queue = self.mouse_event_queue[start_pos:] # empty mouse event queue up to start position
		return queue

	def getNextData(self):
		e = MouseEvent()
		e.start_pos = self.last_mouse_pos
		e.start_time = self.last_mouse_time
		self.last_mouse_pos = e.getGaze()
		self.last_mouse_time = e.getStartTime()
		return e

	def in_setup(self):
		return False

	def now(self, unit=TK_MS):
		time = float(SDL_GetTicks())
		return time if unit == TK_MS else time * 0.001

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
		sacc_start_time = self.__exited_boundary__(label, self.sample())
		if sacc_start_time:
			return sacc_start_time if not return_queue else [sacc_start_time, event_queue]
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
		self.__current_sample__ = MouseEvent()
		return self.__current_sample__

	def setup(self):
		self.dc_width = P.screen_y // 60
		self.add_boundary("drift_correct", [P.screen_c, self.dc_width // 2], CIRCLE_BOUNDARY)
		self.calibrate()
		self.initialized = True

	def start(self, trial_number, samples=EL_TRUE, events=EL_TRUE, link_samples=EL_TRUE, link_events=EL_TRUE):
		self.__recording__ = True
		self.mouse_event_queue = []
		self.start_time = [self.evm.timestamp, self.evm.timestamp]
		self.write("TRIAL_ID {0}".format(str(trial_number)))
		self.write("TRIAL_START")
		self.write("SYNCTIME {0}".format('0.0'))
		return self.evm.timestamp - self.start_time[0] # ie. delay spent initializing the recording

	def stop(self):
		self.__recording__ = False

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

	@property
	def eye(self):
		return self.eyeAvailable()

	@eye.setter
	def eye(self, eye_used):
		self.__eye_used__ = eye_used

	@property
	def recording(self):
		return self.__recording__

	def getNewestSample(self):
		return self.sample()

	def sendMessage(self, msg):
		pass

	def eyeAvailable(self):
		return 1

class MouseEvent(EnvAgent):

	def __init__(self, start_event=None, end_event=None, el_type=EL_GAZE_POS):
		super(MouseEvent, self).__init__()
		
		self.__type__ = el_type
		if start_event:
			if not end_event:
				end_event = start_event
			if el_type == EL_SACCADE_END:
				self.__sample__     = (end_event.x, end_event.y)
				self.__time__       = end_event.timestamp
				self.__start_pos__  = (start_event.x - start_event.xrel, start_event.y - start_event.yrel)
				self.__start_time__ = start_event.timestamp - P.refresh_time
			elif el_type == EL_FIXATION_END:
				self.__sample__     = (end_event.x-end_event.xrel, end_event.y-end_event.yrel)
				self.__time__       = end_event.timestamp - P.refresh_time
				self.__start_pos__  = (start_event.x, start_event.y)
				self.__start_time__ = start_event.timestamp
			else:
				raise EyeLinkError("Only EL_SACCADE_END and EL_FIXATION_EVENT types have been implemented yet.")

		else:
			self.__sample__     = mouse_pos()
			self.__time__       = float(SDL_GetTicks())
			self.__start_pos__  = None
			self.__start_time__ = None

	def getType(self):
		return self.__type__

	def getGaze(self):
		return self.__sample__

	def getEndGaze(self):
		return self.__sample__

	def getStartGaze(self):
		return self.__start_pos__ if self.__start_pos__ else self.__sample__

	def getTime(self):
		return self.__time__

	def getStartTime(self):
		return self.__start_time__ if self.__start_time__ else self.__time__

	def getEndTime(self):
		return self.__time__

	def getEye(self):
		return 1 #right eye, because that's the value of TryLink's self.el.eye

	def isRightSample(self):
		return 1

	def isLeftSample(self):
		return 1

	def getFloatData(self):
		return self

	@property
	def start_pos(self):
		return self.__start_pos__

	@start_pos.setter
	def start_pos(self, pos):
		self.__start_pos__ =  pos

	@property
	def start_time(self):
		return self.__start_time__

	@start_time.setter
	def start_time(self, time):
		self.__start_time__ = time
