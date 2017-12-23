__author__ = 'jono'

import abc
import aggdraw
from sdl2 import SDL_KEYDOWN, SDL_KEYUP, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP, SDLK_c, SDLK_v

from klibs.KLEnvironment import EnvAgent, evm
from klibs.KLExceptions import TrialException
from klibs.KLNamedObject import *
from klibs.KLConstants import (RC_AUDIO, RC_COLORSELECT, RC_DRAW, RC_KEYPRESS, RC_FIXATION, 
	RC_MOUSEDOWN, RC_MOUSEUP, RC_SACCADE, NO_RESPONSE, EL_SACCADE_START, EL_SACCADE_END,
	TIMEOUT, TK_S, TK_MS, STROKE_INNER)
from klibs import P
from klibs.KLUtilities import (pump, flush, hide_mouse_cursor, show_mouse_cursor, mouse_pos,
	full_trace, iterable, angle_between)
from klibs.KLTime import CountDown
from klibs.KLUserInterface import ui_request, any_key, key_pressed
from klibs.KLBoundary import BoundaryInspector, AnnulusBoundary
from klibs.KLGraphics import NpS, fill, flip, blit
from klibs.KLGraphics import aggdraw_to_array
from klibs.KLGraphics.KLDraw import Annulus, ColorWheel, Drawbject
from klibs.KLCommunication import message
from klibs.KLAudio import AudioStream


class ResponseType(NamedObject, EnvAgent):
	__timed_out__ = False

	def __init__(self, start_time, name=None):
		super(ResponseType, self).__init__(name)
		self.responses = []
		self.__interrupts__ = False
		self.__null_response_value__ = NO_RESPONSE
		self.__min_response_count__ = 0
		self.__max_response_count__ = 1
		self.__rc_start_time__ = start_time
		self.inactive_phases = []
		self.active_phases = []

	def clear_responses(self):
		self.responses = []

	def max_collected(self):
		return self.response_count == self.max_response_count

	def collect(self, event_queue):
		if not self.max_collected():
			try:
				self.collect_response(event_queue)
			except TypeError:
				self.collect_response()
		return self.max_collected() and self.interrupts

	def reset(self):
		self.responses = []

	def response(self, value=True, rt=True, index=0):
		if not value and not rt:
			raise ValueError("Why have you asked me to return nothing? Is this is a joke?")

		try:
			if value:
				if rt:
					return self.responses[index]
				else:
					return self.responses[index][0]
			else:
				return self.responses[index][1]
		except IndexError:
			if value:
				if rt:
					return [self.null_response, -1]
				else:
					return self.null_response
			else:
				return -1

	def response_made(self, index=0):
		if len(self.responses) >= index+1:
			return self.responses[index][0] != self.null_response
		return False

	@property
	def timed_out(self):
		return self.__timed_out__

	@timed_out.setter
	def timed_out(self, state):
		self.__timed_out__ = state == True

	@abc.abstractmethod
	def collect_response(self):
		pass

	@property
	def response_count(self):
		return len(self.responses)

	@property
	def rt_label(self):
		return "T{0}_{1}_Response_{2}".format(P.trial_number, self.name, len(self.responses) + 1)

	@property
	def null_response(self):
		return self.__null_response_value__

	@null_response.setter
	def null_response(self, response_val):
		self.__null_response_value__ = response_val

	@property
	def max_response_count(self):
		return self.__max_response_count__

	@max_response_count.setter
	def max_response_count(self, count):
		self.__max_response_count__ = count

	@property
	def min_response_count(self):
		return self.__min_response_count__

	@max_response_count.setter
	def min_response_count(self, count):
		self.__min_response_count__ = count

	@property
	def interrupts(self):
		return self.__interrupts__

	@interrupts.setter
	def interrupts(self, value):
		if type(value) is bool:
			self.__interrupts__ = value
		else:
			raise TypeError("Property 'interrupts' must be boolean.")


class KeyPressResponse(ResponseType):

	def __init__(self, rc_start_time):
		super(KeyPressResponse, self).__init__(rc_start_time, RC_KEYPRESS)
		self.__key_map__ = None

	def collect_response(self, event_queue):
		if not self.key_map:
			raise RuntimeError("No KeyMap configured to KeyPressResponse listener.")
		for event in event_queue:
			if event.type == SDL_KEYDOWN:
				key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
				sdl_keysym = key.keysym.sym

				# check for ui requests (ie. quit, pause, calibrate)
				ui_request(key.keysym)

				if self.key_map:
					if self.key_map.validate(sdl_keysym):
						if len(self.responses) < self.min_response_count:
							self.responses.append([self.key_map.read(sdl_keysym, "data"), (self.evm.trial_time_ms - self.__rc_start_time__[0])])
						if self.interrupts:
							return self.responses if self.max_response_count > 1 else self.responses[0]
					else:
						invalid_key = True
						# todo: write adjustable behaviour for informing participants of invalid keys
						# wrong_key_message = "Please respond using '{0}'.".format(key_map.valid_keys())
						# self.alert(wrong_key_message)
						# invalid_key = False
				else:
					raise RuntimeError("No keymap has been set for this KeyPressResponse object.")

	@property
	def key_map(self):
		return self.__key_map__

	@key_map.setter
	def key_map(self, key_map_obj):
		try:
			key_map_obj.any_key
		except AttributeError:
			if key_map_obj is not None:
				raise TypeError("Argument 'key_map_obj' must be a KLKeyMap object.")
		self.__key_map__ = key_map_obj
		self.clear_responses()


class AudioResponse(ResponseType):

	def __init__(self, rc_start_time):
		super(AudioResponse, self).__init__(rc_start_time, RC_AUDIO)
		self.stream = AudioStream()
		self.threshold_valid = False
		self.calibrated = False

	def calibrate(self):
		peaks = []
		if P.development_mode and P.dm_auto_threshold:
			ambient = self.stream.get_ambient_level()
			if ambient == 0:
				raise RuntimeError("Ambient level appears to be zero; exit the anachoic chamber or restart the experiment.")
			self.stream.threshold = ambient * 5
			self.threshold_valid = True
			self.calibrated = True
			return
		for i in range(0, 3):
			msg = "Provide a normal sample of your intended response."
			peaks.append( self.stream.get_peak_during(3, msg) )
			if i < 2:
				next_message = "Got it; {0} more samples to collect. Press any key to continue".format(2 - i)
				fill()
				message(next_message, location=P.screen_c, registration=5)
				flip()
				any_key()
		self.stream.threshold = min(peaks)
		self.validate()

	def validate(self):
		instruction = "Ok, threshold set! To ensure its validity, please provide one (and only one) more response."
		fill()
		message(instruction, location=P.screen_c, registration=5)
		flip()
		self.start()
		validate_counter = CountDown(5)
		while validate_counter.counting():
			ui_request()
			if self.stream.sample().peak >= self.stream.threshold:
				validate_counter.finish()
				self.threshold_valid = True
		self.stop()

		if self.threshold_valid:
			validation_msg = "Great, validation was successful. Press any key to continue."
		else:
			validation_msg = "Validation wasn't successful. Type C to re-calibrate or V to try validation again."
		fill()
		message(validation_msg, location=P.screen_c, registration=5)
		flip()
		response_collected = False
		while not response_collected:
			q = pump(True)
			if self.threshold_valid:
				if key_pressed(queue=q):
					self.calibrated = True
					return
			else:
				if key_pressed(SDLK_c, queue=q):
					self.calibrate()
				elif key_pressed(SDLK_v, queue=q):
					self.validate()

	def collect_response(self):
		if not self.calibrated:
			raise RuntimeError("AudioResponse not ready for collection; calibration not completed.")
		if self.stream.sample().peak >= self.stream.threshold:
			if len(self.responses) < self.min_response_count:
				self.responses.append([self.stream.sample().peak, (self.evm.trial_time_ms - self.__rc_start_time__[0])])
			if self.interrupts:
				self.stop()
				return self.responses if self.max_response_count > 1 else self.responses[0]

	def start(self):
		self.stream.init_stream()

	def stop(self):
		self.stream.kill_stream()


class MouseDownResponse(ResponseType, BoundaryInspector):

	def __init__(self, rc_start_time):
		super(MouseDownResponse, self).__init__(rc_start_time, RC_MOUSEDOWN)

	def collect_response(self, event_queue):
		for event in event_queue:
			if event.type is SDL_MOUSEBUTTONDOWN:
				if len(self.responses) < self.min_response_count:
					boundary =  self.within_boundaries([event.x, event.y])
					if boundary:
						self.responses.append( [boundary, [event.x, event.y], (self.evm.trial_time_ms - self.__rc_start_time__[0])] )
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]

class MouseUpResponse(ResponseType, BoundaryInspector):

	def __init__(self, rc_start_time):
		super(MouseUpResponse, self).__init__(rc_start_time, RC_MOUSEUP)

	def collect_response(self, event_queue):
		for event in event_queue:
			if event.type is SDL_MOUSEBUTTONUP:
				if len(self.responses) < self.min_response_count:
					boundary = self.within_boundaries([event.x, event.y])
					if boundary:
						self.responses.append([boundary, [event.x, event.y], (self.evm.trial_time_ms - self.__rc_start_time__[0])])
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]


class JoystickResponse(ResponseType):
	def __init__(self, rc_start_time):
		pass

	def collect_response(self):
		pass


class SaccadeResponse(ResponseType):
	__origin__ = None
	__destination__ = None
	include_start = True
	include_end = False

	def __init__(self, rc_start_time):
		super(SaccadeResponse, self).__init__(rc_start_time, RC_SACCADE)

	def collect_response(self):
		for e in self.el.get_event_queue([self.el.eyelink.ENDSACC]):
			origin_ok = True
			destination_ok = True
			if self.origin:
				origin_ok = self.el.within_boundary(self.origin, e.getStartGaze())
			if self.destination:
				destination_ok = self.el.within_boundary(self.destination, e.getEndGaze())
			if origin_ok and destination_ok:
				if self.saccade_type == EL_SACCADE_START:
					self.responses.append([True, e.getStartTime() - self.el.now()])
				if self.saccade_type == EL_SACCADE_END:
					self.responses.append([True, e.getEndTime() - self.el.now()])

	@property
	def origin(self):
		return self.el.fetch_gaze_boundary(self.__origin__) if self.__origin__ is not None else None

	@origin.setter
	def origin(self, bounds):
		# bounds = [boundary coordinates, shape]
		self.__origin__ = self.el.add_gaze_boundary(bounds[0], bounds[1])

	@property
	def destination(self):
		return self.el.fetch_gaze_boundary(self.__destination__) if self.__destination__ is not None else None

	@destination.setter
	def destination(self, bounds):
		# bounds = [boundary coordinates, shape]
		self.__destination__ = self.el.add_gaze_boundary(bounds[0], bounds[1])


class FixationResponse(ResponseType):

	def __init__(self, rc_start_time):
		super(FixationResponse, self).__init__(rc_start_time, RC_FIXATION)


class ColorSelectionResponse(ResponseType):
	__wheel__ = None
	__bounds__ = None
	__probe__ = None
	target_loc = None
	warp_cursor = True
	angle_response = True
	color_response = False

	__first_loop__ = True

	def __init__(self, rc_start_time):
		super(ColorSelectionResponse, self).__init__(rc_start_time, RC_COLORSELECT)

	def collect_response(self, event_queue):
		if self.__wheel__ == None:
			raise ValueError("No target ColorWheel or Annulus specified")
		elif isinstance(self.__wheel__, Annulus) and self.color_response:
			raise ValueError("Cannot collect color responses with an Annulus target.")
		if not self.angle_response and not self.color_response:
			raise ValueError("At least one of 'angle_response' and 'color_response' must be True.")

		# If first loop of RC and warp_cursor enabled, warp cursor to middle of wheel
		if self.warp_cursor and self.__first_loop__:
			mouse_pos(position=self.__bounds__.center)
			self.__first_loop__ = False

		for e in event_queue:
			if e.type == SDL_MOUSEBUTTONUP:
				pos = [e.button.x, e.button.y]
				if not self.__bounds__.within(pos):
					continue
				response_angle = angle_between(pos, P.screen_c, 90, clockwise=True)
				if self.__wheel__.__name__ == "ColorWheel":
					target_color = self.__probe__.fill_color
					target_angle = self.__wheel__.angle_from_color(target_color)
				else:
					target_angle = angle_between(self.target_loc, P.screen_c, 90, clockwise=True)
				diff = target_angle - response_angle
				angle_err = diff-360 if diff > 180 else diff+360 if diff < -180 else diff
				if self.color_response:
					color = self.__wheel__.color_from_angle(response_angle)
					response = (angle_err, color) if self.angle_response else color
				else:
					response = angle_err

				if len(self.responses) < self.min_response_count:
					rt = self.evm.trial_time_ms - self.__rc_start_time__[0]
					self.responses.append([response, rt])
					if self.interrupts:
						return self.responses if self.max_response_count > 1 else self.responses[0]
	
	def set_target(self, target):
		'''Sets the colour probe Drawbject or target location for listener, which is used to
		calculate the angular error between target and response during response collection. When
		the wheel for the listener is a Colour Wheel, a colour probe must be provided. When the
		wheel is an Annulus, a location in the form of (x, y) pixel coordinates must be provided.
		
		Note that colour probes are pass-by-refrence, meaning that you can change the fill colour
		of the probe after setting it as the target and the response collector will use whatever
		fill colour the probe has at collection time.

		Args:
			target (:obj:`Drawbject`|tuple(int,int)): A coloured shape (e.g. ellipse, asterisk)
				if using a ColorWheel for the wheel, or a tuple of (x,y) pixel coordinates
				indicating the location that the target will appear if using an Annulus for the
				wheel.

		Raises:
			ValueError: if the probe object is not a :obj:`Drawbject` or tuple.

		'''
		if isinstance(target, Drawbject):
			self.__probe__ = target
		elif hasattr(target, '__iter__'):
			if 0 <= target[0] <= P.screen_x and 0 <= target[1] <= P.screen_y:
				self.target_loc = target
			else:
				raise ValueError("Target location must be within the range of the screen.")
		else:
			raise ValueError("Target must either be a Drawbject or a tuple of (x,y) coordinates.")


	def set_wheel(self, wheel, location=None, registration=None):
		'''Sets the ColorWheel or Annulus object to use for response collection.

		Args:
			target (:obj:`ColorWheel`|:obj:`Annulus`): The ColorWheel or Annulus Drawbject to be
				used with the RC_COLORSELECT response collector.
			location (tuple(int, int), optional): The pixel coordinates that the target wheel will
				be blitted to during the response collection loop. Defaults to the center of the
				screen if not specified.
			registration (int, optional): The registration value between 1 and 9 that the target
				wheel will be blitted with during the response collection loop. Defaults to 5
				(center of surface) if not specified.

		Raises:
			ValueError: if the target object is not an :obj:`Annulus` or :obj:`ColorWheel`.

		'''
		if isinstance(wheel, (Annulus, ColorWheel)):
			self.__wheel__ = wheel
		else:
			raise ValueError("Target object must be either an Annulus or ColorWheel Drawbject.")
		# If no location or reg given, assume it's in the exact middle of the screen
		if not location:
			location = P.screen_c
		if not registration:
			registration = 5

		# Generate response boundary given registration, location and object size
		if registration in [7, 4, 1]:
			x_offset = wheel.surface_width // 2
		elif registration in [9, 6, 3]:
			x_offset = -wheel.surface_width // 2
		else:
			x_offset = 0

		if registration in [7, 8, 9]:
			y_offset = wheel.surface_width // 2
		elif registration in [1, 2, 3]:
			y_offset = -wheel.surface_width // 2
		else:
			y_offset = 0
		
		center = (location[0]+x_offset, location[1]+y_offset)
		self.__bounds__ = AnnulusBoundary("wheel_rc", center, wheel.radius, wheel.thickness)

	@property
	def wheel(self):
		return self.__wheel__

	@property
	def rotation(self):
		return self.__wheel__.rotation

	@rotation.setter
	def rotation(self, angle):
		self.__wheel__.rotation = angle


class DrawResponse(ResponseType, BoundaryInspector):

	def __init__(self, rc_start_time):
		super(DrawResponse, self).__init__(rc_start_time, RC_DRAW)
		BoundaryInspector.__init__(self)
		self.points = []
		self.stop_boundary = None
		self.start_boundary = None
		self.started = False
		self.start_time = None
		self.stopped = False
		self.stop_eligible = False
		self.image = None
		self.max_x = 0
		self.max_y = 0
		self.stroke = [1, (0,0,0,255), STROKE_INNER]
		self.fill = None
		self.show_active_cursor = True
		self.show_inactive_cursor = True
		self.canvas_size = None
		self.canvas_boundary = None
		self.origin = None
		self.x_offset = 0
		self.y_offset = 0
		self.min_samples = 2
		self.render_real_time = False
		self.first_sample_time = None  # start time begins when landing on origin; first sample collected on departure

	def collect_response(self, event_queue=None):
		# assert cursor visibility (or not)
		if not self.started or self.stopped:
			if self.show_inactive_cursor:
				show_mouse_cursor()
			else:
				hide_mouse_cursor()
		if self.started and not self.stopped:
			if self.show_active_cursor:
				show_mouse_cursor()
			else:
				hide_mouse_cursor()

		mp = mouse_pos()

		# if there are no boundaries for initation and completion, start immediately
		if not self.stop_boundary or not self.start_boundary:
			self.started = True

		# if boundaries, test for initiation condition
		if not self.started:
			if self.within_boundary(self.start_boundary, mp):
				self.started = True
				self.start_time = self.evm.trial_time

		# if boundaries, test for completion condition
		if self.within_boundary(self.stop_boundary, mp):
			if self.stop_eligible and not self.stopped:
				self.stopped = True
				self.responses.append([self.points, self.points[-1][2] - self.points[0][2]])
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]

		# don't allow checking for stopped condition until started and outside of start boundary
		self.drawing = not self.within_boundary(self.start_boundary, mp) and self.started
		if self.drawing:
			try:
				timestamp = self.evm.trial_time - self.first_sample_time
			except TypeError:
				self.first_sample_time = self.evm.trial_time
				timestamp = 0.0
			p = [mp[0] - self.x_offset, mp[1] - self.y_offset]
			if tuple(p) in P.ignore_points_at:
				return
			p.append(timestamp)
			try:
				# don't repeat points
				if mp != self.points[-1]:
					self.points.append(tuple(p))
			except IndexError:
				self.points.append(tuple(p))

		self.stop_eligible = self.drawing and len(self.points)>=self.min_samples

	def reset(self):
		self.responses = []
		self.points = []
		self.started = False
		self.stopped = False
		self.stop_eligible = False
		self.start_time = None

	def render_progress(self):
		if not self.render_real_time:
			return False
		if not self.started:
			return False
		if len(self.points) < 2:
			return False
		m_str = ""
		for p in self.points:
			if m_str == "":
				m_str = "M{0},{1}".format(p[0], p[1])
			else:
				m_str += "L{0},{1}".format(p[0], p[1])
		s = aggdraw.Symbol(m_str)
		test_p = aggdraw.Draw("RGBA", P.screen_x_y, (0,0,0,0))
		test_p.setantialias(True)
		test_p.symbol((0,0), s, aggdraw.Pen((255,80, 125), 1, 255))
		return aggdraw_to_array(test_p)

	@property
	def active(self):
		return self.started and not self.stopped


class ResponseCollector(EnvAgent):
	__null_response_value__ = None
	__min_response_count__ = None
	__max_response_count__ = None
	end_collection_event = None

	def __init__(self, uses=[], display_callback=None, terminate_after=[10, TK_S], null_response=NO_RESPONSE,
				 response_count=[0,1], flip_screen=False):

		super(ResponseCollector, self).__init__()
		self.__null_response_value__ = null_response
		self.__min_response_count__ = response_count[0]
		self.__max_response_count__ = response_count[1]
		self.__rc_index__ = {
			RC_AUDIO		:AudioResponse,
			RC_KEYPRESS		:KeyPressResponse,
			RC_MOUSEUP		:MouseDownResponse,
			RC_MOUSEDOWN	:MouseUpResponse,
			RC_FIXATION		:FixationResponse,
			RC_SACCADE		:SaccadeResponse,
			RC_COLORSELECT	:ColorSelectionResponse,
			RC_DRAW			:DrawResponse
		}
		self.__uses__ = {
			RC_AUDIO		:False,
			RC_KEYPRESS		:False,
			RC_MOUSEUP		:False,
			RC_MOUSEDOWN	:False,
			RC_FIXATION		:False,
			RC_SACCADE		:False,
			RC_COLORSELECT	:False,
			RC_DRAW			:False
		}
		self.rc_start_time = [None] # in list so it can be passed by reference to ResponseListeners
		self.terminate_after = terminate_after
		self.callbacks = {} 
		self.display_callback = display_callback
		self.has_display_callback = False
		self.display_args = []
		self.display_kwargs = {}
		self.flip = flip_screen

		# dict of listeners for iterating during collect()
		self.listeners = NamedInventory()
		if len(uses):
			self.uses(uses)

	def uses(self, listeners):
		"""
		Toggles available listeners on or off.
		:param listeners:
		:raise ValueError:
		"""
		if not iterable(listeners): listeners = [listeners]
		for l in listeners:
			try:
				self.__uses__[l]  = True
				self.listeners.add(self.__rc_index__[l](self.rc_start_time))
			except KeyError:
				raise ValueError('{0} is not a valid response type.'.format(l))

	def using(self, listener=None):
		"""
		Returns either a complete list of currently in-use listeners, or, if a list of possible listeners is supplied,
		which of them is active.

		:param listener:
		:return:
		"""
		if not listener:
			in_use = []
			for l in self.__uses__:
				if self.using(l):
					in_use.append(l)
			return in_use
		if iterable(listener):
			in_use = []
			for l in self.__uses__:
				in_use.append(self.using(l))
 			return in_use
		return self.__uses__[listener]

	def response_count(self, listener=None):
		"""
		Returns the total number of responses made so far (or since the last call to collect()); if a listener is
		supplied, returns only the number of responses collected by that listener.

		:param listener:
		:return:
		"""
		count = 0
		if listener:
			return self.listeners[listener].response_count
		for l in self.uses:
			count += self.listeners[l].response_count
		return count

	def collect(self):
		"""
		The collection loop runs all supplied callbacks in sequence and collects responses from in-use listeners.
		:raise RuntimeError:
		"""
		if len(self.enabled()) == 0:
			raise RuntimeError("Nothing to collect; no response listener(s) enabled.")

		# enter the loop with a cleared event queue
		flush()

		# before flip callback
		try:
			self.before_flip_callback(*self.before_flip_args, **self.before_flip_kwargs)
		except TypeError:
			self.before_flip_callback(*self.before_flip_args)
		except KeyError:
			pass

		# do any preparatory work for listeners to be used during the collection loop
		if self.using(RC_AUDIO): self.audio_listener.start()
		if self.using(RC_MOUSEDOWN) or self.using(RC_MOUSEUP) or self.using(RC_COLORSELECT): show_mouse_cursor()

		if self.flip:
			flip()
			try:
				self.after_flip_callback(*self.after_flip_args, **self.after_flip_kwargs)
			except TypeError:
				self.after_flip_callback(*self.after_flip_args)
			except KeyError:
				pass

		# Check if there is a display callback
		self.has_display_callback = callable(self.display_callback)
		
		# If there is no display callback, response period start is immediately before collection starts
		if not self.has_display_callback:
			self.rc_start_time[0] = self.evm.trial_time_ms # the only element in list, which is used for mutability only

		# the actual response collection loop
		self.__collect__()

		# before return callback
		try:
			self.before_return_callback(*self.before_return_args, **self.before_return_kwargs)
		except TypeError:
			self.before_return_callback(*self.before_return_args)
		except KeyError:
			pass

		for l in self.using():
			listener = self.listeners[l]
			while listener.response_count < listener.min_response_count:
				if listener.max_response_count == 1:
					listener.timed_out = True
				listener.responses.append([listener.null_response, TIMEOUT])
		if self.using(RC_AUDIO):
			self.audio_listener.stop()
		self.rc_start_time[0] = None # Reset before next trial

	def __collect__(self):
		first_loop = True
		while True:
			if not self.end_collection_event:
				try:
					t = self.evm.trial_time_ms
					timeout = self.terminate_after[0]
					if self.terminate_after[1] == TK_S: timeout *= 1000.0
					if t > (self.rc_start_time[0] + timeout):
						print "Broke due to force timeout."
						break
				except TypeError:
					pass
			e_queue = pump(True)

			# after pumping issued trial events will be registered with the evm
			try:
				if self.evm.after(self.end_collection_event):
					break
			except ValueError:
				pass  # if end_collection_event is None

			if not self.using(RC_KEYPRESS):  # else ui_requests are handled automatically by all keypress responders
				ui_request(queue=e_queue)

			# get responses for all active listeners
			if self.rc_start_time[0]: # Only start collecting once a start time value has been set
				interrupt = False
				for l in self.using():
					interrupt = self.listeners[l].collect(e_queue)
				if interrupt:
					break

			# display callback
			if self.has_display_callback:
				try:
					self.display_callback(*self.display_args, **self.display_kwargs)
				except TypeError:
					self.display_callback(*self.display_args)
				except KeyError:
					pass
			
			if self.flip:
				flip()

			# If there is a display callback, response period start is immediately after flip of first loop
			if first_loop:
				if self.has_display_callback: # if there is a display callback, start of response period is immediately after first flip
					self.rc_start_time[0] = self.evm.trial_time_ms # the only element in list, which is used for mutability only
				first_loop = False

		hide_mouse_cursor()

	def reset(self):
		# Clear all listeners and set all use flags to False
		# (is this really the best way to do this? Or should rc objects persist across experiment?)
		self.listeners = NamedInventory()
		for k in self.__uses__.keys():
			self.__uses__[k] = False
		#for l in self.listeners:
		#	self.listeners[l.name].reset()

	def disable(self, listener): # is this needed anymore?
		self.__uses__[listener] = False

	def enable(self, listener):
		self.__uses__[listener] = True
		self.listeners.add(self.__rc_index__[l](self.rc_start_time))

	def enabled(self):
		en = []
		for l in self.listeners:
			if self.__uses__[l.name]:
				en.append(l.name)
		return en

	# Use properties as nice aliases for response listeners in self.listeners

	def __get_listener__(self, listener):
		try:
			return self.listeners[listener]
		except KeyError:
			raise ValueError("'{0}' listener is not currently in use.".format(listener))

	@property
	def audio_listener(self):
		return self.__get_listener__(RC_AUDIO)
	@property
	def keypress_listener(self):
		return self.__get_listener__(RC_KEYPRESS)
	@property
	def mousedown_listener(self):
		return self.__get_listener__(RC_MOUSEDOWN)
	@property
	def mouseup_listener(self):
		return self.__get_listener__(RC_MOUSEUP)
	@property
	def fixation_listener(self):
		return self.__get_listener__(RC_FIXATION)
	@property
	def color_listener(self):
		return self.__get_listener__(RC_COLORSELECT)
	@property
	def draw_listener(self):
		return self.__get_listener__(RC_DRAW)



	@property
	def null_response_value(self):
		return self.__null_response_value__

	@null_response_value.setter
	def null_response_value(self, value):
		self.__null_response_value__ = value

	@property
	def max_response_count(self):
		return self.__max_response_count__

	@max_response_count.setter
	def max_response_count(self, count):
		self.__max_response_count__ = count

	@property
	def min_response_count(self):
		return self.__min_response_count__

	@max_response_count.setter
	def min_response_count(self, count):
		self.__min_response_count__ = count

	@property
	def display_callback(self):
		return self.callbacks['display'][0]

	@display_callback.setter
	def display_callback(self, callback):
		cb_method = callback
		cb_args = []
		cb_kwargs = {}
		if not hasattr(callback, '__call__'):
			try:
				iter(callback)
				if type(callback[1]) in (list, tuple):
					cb_args = callback[1]
				else:
					raise TypeError("Index 1 of property 'callback' must be a list or None.")
				try:
					if type(callback[2]) is dict:
						cb_kwargs = callback[2]
					else:
						if type(callback[2]) is not None:
							raise TypeError("Index 2 of property 'callback' must be a dict or None.")
				except IndexError:
					pass
			except TypeError:
				if callback is not None:
					raise TypeError("Property 'display_callback' must be a function or list of function and supporting arguments.")
		try:
			self.callbacks['display'][0] = cb_method
		except KeyError:
			self.callbacks['display'] = [cb_method, cb_args, cb_kwargs]

	@property
	def display_args(self):
		return self.callbacks['display'][1]

	@display_args.setter
	def display_args(self, args_list):
		if type(args_list) not in (list, tuple):
			raise TypeError("Property 'args_list' must be either a list or a tuple.")
		self.callbacks['display'][1] = args_list

	@property
	def display_kwargs(self):
		if self.callbacks['display'][2] == {}:
			return {}
		else:
			self.callbacks['display'][2]

	@display_args.setter
	def display_kwargs(self, kwargs_list):
		if type(kwargs_list) is not dict:
			raise TypeError("Property 'display_kwargs' must be a dict.")
		self.callbacks['display'][2] = kwargs_list

	@property
	def before_flip_callback(self):
		return self.callbacks['before_flip'][0]

	@before_flip_callback.setter
	def before_flip_callback(self, callback):
		cb_method = callback
		cb_args = []
		cb_kwargs = {}
		if not hasattr(callback, '__call__'):
			try:
				iter(callback)
				if type(callback[1]) in (list, tuple):
					cb_args = callback[1]
				else:
					raise TypeError("Index 1 of property 'callback' must be a list or None.")
				try:
					if type(callback[2]) is dict:
						cb_kwargs = callback[2]
					else:
						if callback[2] is not None:
							raise TypeError("Index 2 of property 'callback' must be a dict or None.")
				except IndexError:
					pass
			except AttributeError:
				raise TypeError(
					"Property 'before_flip_callback' must be a function or list of function and supporting arguments.")
		try:
			self.callbacks['before_flip'][0] = cb_method
		except KeyError:
			self.callbacks['before_flip'] = [cb_method, cb_args, cb_kwargs]

	@property
	def before_flip_args(self):
		return self.callbacks['before_flip'][1]

	@before_flip_args.setter
	def before_flip_args(self, args_list):
		if type(args_list) not in (list, tuple):
			raise TypeError("Property 'args_list' must be either a list or a tuple.")
		self.callbacks['before_flip'][1] = args_list

	@property
	def before_flip_kwargs(self):
		return self.callbacks['before_flip'][2]

	@before_flip_args.setter
	def before_flip_kwargs(self, kwargs_list):
		if type(kwargs_list) is not dict:
			raise TypeError("Property 'kwargs_list' must be a dict.")
		self.callbacks['before_flip'][2] = kwargs_list

	@property
	def after_flip_callback(self):
		return self.callbacks['after_flip'][0]

	@after_flip_callback.setter
	def after_flip_callback(self, callback):
		cb_method = callback
		cb_args = []
		cb_kwargs = {}
		if not hasattr(callback, '__call__'):
			try:
				iter(callback)
				if type(callback[1]) in (list, tuple):
					cb_args = callback[1]
				else:
					raise TypeError("Index 1 of property 'callback' must be a list or None.")
				try:
					if type(callback[2]) is dict:
						cb_kwargs = callback[2]
					else:
						if callback[2] is not None:
							raise TypeError("Index 2 of property 'callback' must be a dict or None.")
				except IndexError:
					pass
			except AttributeError:
				raise TypeError(
					"Property 'after_flip_callback' must be a function or list of function and supporting arguments.")
		try:
			self.callbacks['after_flip'][0] = cb_method
		except KeyError:
			self.callbacks['after_flip'] = [cb_method, cb_args, cb_kwargs]

	@property
	def after_flip_args(self):
		return self.callbacks['after_flip'][1]

	@after_flip_args.setter
	def after_flip_args(self, args_list):
		if type(args_list) not in (list, tuple):
			raise TypeError("Property 'args_list' must be either a list or a tuple.")
		self.callbacks['after_flip'][1] = args_list

	@property
	def after_flip_kwargs(self):
		return self.callbacks['after_flip'][2]

	@after_flip_args.setter
	def after_flip_kwargs(self, kwargs_list):
		if type(kwargs_list) is not dict:
			raise TypeError("Property 'kwargs_list' must be a dict.")
		self.callbacks['after_flip'][2] = kwargs_list

	@property
	def before_return_callback(self):
		return self.callbacks['before_return'][0]

	@before_return_callback.setter
	def before_return_callback(self, callback):
		cb_method = callback
		cb_args = []
		cb_kwargs = {}
		if not hasattr(callback, '__call__'):
			try:
				iter(callback)
				if type(callback[1]) in (list, None):
					cb_args = callback[1]
				else:
					raise TypeError("Index 1 of property 'callback' must be a list or None.")
				try:
					if type(callback[2]) is dict:
						cb_kwargs = callback[2]
					else:
						if type(callback[2]) is not None:
							raise TypeError("Index 2 of property 'callback' must be a dict or None.")
				except IndexError:
					pass
			except AttributeError:
				raise TypeError(
					"Property 'before_return_callback' must be a function or list of function and supporting arguments.")
		try:
			self.callbacks['before_return'][0] = cb_method
		except KeyError:
			self.callbacks['before_return'] = [cb_method, cb_args, cb_kwargs]

	@property
	def before_return_args(self):
		return self.callbacks['before_return'][1]

	@before_return_args.setter
	def before_return_args(self, args_list):
		if type(args_list) not in (list, tuple):
			raise TypeError('Args list must be either a list or a tuple')
		self.callbacks['before_return'][1] = args_list

	@property
	def before_return_kwargs(self):
		return self.callbacks['before_return'][2]

	@before_return_args.setter
	def before_return_kwargs(self, args_list):
		if type(args_list) is not dict:
			raise TypeError('Args list must be either a list or a tuple')
		self.callbacks['before_return'][2] = args_list



