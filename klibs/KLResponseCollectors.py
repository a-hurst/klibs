__author__ = 'jono'

import abc
import aggdraw
from sdl2 import SDL_KEYDOWN, SDL_KEYUP, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP, SDLK_c, SDLK_v

from klibs.KLExceptions import TrialException
from  klibs.KLNamedObject import *
from klibs.KLEnvironment import EnvAgent, evm
from klibs.KLConstants import RC_AUDIO, RC_COLORSELECT, RC_DRAW, RC_KEYPRESS, RC_FIXATION, RC_MOUSEDOWN, RC_MOUSEUP, \
	RC_SACCADE, NO_RESPONSE, EL_SACCADE_START, EL_SACCADE_END, STROKE_INNER, MAX_WAIT, TIMEOUT, TK_S, TK_MS
from klibs import P
from klibs.KLUtilities import pump, full_trace, angle_between, hide_mouse_cursor, show_mouse_cursor, mouse_pos, \
	iterable, flush
from klibs.KLUserInterface import ui_request
from klibs.KLBoundary import BoundaryInspector
from klibs.KLGraphics import NpS, fill, flip, blit
from klibs.KLGraphics import aggdraw_to_array
from klibs.KLGraphics.KLDraw import ColorWheel
from klibs.KLAudio import AudioStream

class ResponseType(NamedObject, EnvAgent):
	__timed_out__ = False

	def __init__(self, name=None):
		super(ResponseType, self).__init__(name)
		self.responses = []
		self.__interrupts__ = False
		self.__null_response_value__ = NO_RESPONSE
		self.__min_response_count__ = 0
		self.__max_response_count__ = 1
		self.inactive_phases = []
		self.active_phases = []

	def clear_responses(self):
		self.responses = []

	def max_collected(self):
		return self.response_count == self.max_response_count

	def collect(self, event_queue, mouse_click_boundaries):
		if not self.max_collected():
			try:
				self.collect_response(event_queue, mouse_click_boundaries)
			except TypeError:
				self.collect_response(event_queue)
				# try:
				# except TypeError:
				# 	self.collect_response()
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

	def __init__(self):
		super(KeyPressResponse, self).__init__(RC_KEYPRESS)
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
							self.responses.append([self.key_map.read(sdl_keysym, "data"), self.evm.trial_time_ms])
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

	def __init__(self):
		super(AudioResponse, self).__init__(RC_AUDIO)
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
			message = "Provide a normal sample of your intended response."
			peaks.append( self.stream.get_peak_during(3, message) )
			if i < 2:
				next_message = "Got it; {0} more samples to collect. Press any key to continue".format(2 - i)
				fill()
				# message(next_message, location=P.screen_c, registration=5)
				flip()
				any_key_pressed = False
				while not any_key_pressed:
					for event in pump(True):
						if event.type == SDL_KEYDOWN:
							ui_request(event.key.keysym)
							any_key_pressed = True
		self.stream.threshold = min(peaks)
		self.validate()

	def validate(self):
		validate_counter = self.tk.countdown(5)
		fill()
		validation_instruction = "Ok; threshold set. To ensure it's validity, please provide one (and only one) more response."
		# message(validation_instruction, location=P.screen_c, registration=5)
		flip()
		self.start()
		while validate_counter.counting():
			ui_request()
			if self.stream.sample().peak >= self.stream.threshold:
				validate_counter.finish()
				self.threshold_valid = True
		self.stop()
		if self.threshold_valid:
			validation_message = "Great, validation was successful. Press any key to continue."
		else:
			validation_message = "Validation wasn't successful. Type C to re-calibrate or V to try validation again."
		fill()
		# message(validation_message, location=P.screen_c, registration=5, flip=True)

		response_collected = False
		while not response_collected:
			for event in pump(True):
				if event.type == SDL_KEYDOWN:
					ui_request(event.key.keysym)
					if self.threshold_valid:
						self.calibrated = True
						return
					else:
						if event.key.keysym.sym == SDLK_c:
							self.calibrate()
						if event.key.keysym.sym == SDLK_v:
							self.validate()

	def collect_response(self):
		if not self.calibrated:
			raise RuntimeError("AudioResponse not ready for collection; calibration not completed.")
		if self.stream.sample().peak >= self.stream.threshold:
			if len(self.responses) < self.min_response_count:
				self.responses.append([self.stream.sample().peak, self.evm.trial_time])
			if self.interrupts:
				self.stop()
				return self.responses if self.max_response_count > 1 else self.responses[0]

	def start(self):
		self.stream.init_stream()

	def stop(self):
		self.stream.kill_stream()


class MouseDownResponse(ResponseType, BoundaryInspector):

	def __init__(self):
		super(MouseDownResponse, self).__init__(RC_MOUSEDOWN)

	def collect_response(self, event_queue):
		for event in event_queue:
			if event.type is SDL_MOUSEBUTTONDOWN:
				if len(self.responses) < self.min_response_count:
					boundary =  self.within_boundaries([event.x, event.y])
					if boundary:
						self.responses.append( [boundary, [event.x, event.y], self.evm.trial_time] )
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]

class MouseUpResponse(ResponseType, BoundaryInspector):

	def __init__(self):
		super(MouseUpResponse, self).__init__(RC_MOUSEUP)

	def collect_response(self, event_queue):
		for event in event_queue:
			if event.type is SDL_MOUSEBUTTONUP:
				if len(self.responses) < self.min_response_count:
					boundary = self.within_boundaries([event.x, event.y])
					if boundary:
						self.responses.append([boundary, [event.x, event.y], self.evm.trial_time])
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]


class JoystickResponse(ResponseType):
	def __init__(self):
		pass

	def collect_response(self):
		pass


class SaccadeResponse(ResponseType):
	__origin__ = None
	__destination__ = None
	include_start = True
	include_end = False

	def __init__(self):
		super(SaccadeResponse, self).__init__(RC_SACCADE)

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

	def __init__(self):
		super(FixationResponse, self).__init__(RC_FIXATION)


class ColorSelectionResponse(ResponseType, BoundaryInspector):
	__target__ = None
	__x_offset__ = None
	__y_offset__ = None
	__rotation__ = 0
	__target_location__ = (0,0)
	__target_registration__ = 7
	require_alpha = True
	angle_response = True
	color_response = False
	click_boundary = None

	def __init__(self):
		ResponseType.__init__(self, RC_COLORSELECT)
		BoundaryInspector.__init__(self)
		# self.__name__ = RC_COLORSELECT  # done manually due to inheritance conflicts

	def collect_response(self, event_queue):
		# todo: add some logic for excluding certain colors (ie. the background color)
		for e in event_queue:
			if e.type == SDL_MOUSEBUTTONUP:
				pos = [e.button.x, e.button.y]
				if not self.within_boundary("color ring", pos):
					continue
				response = angle_between(P.screen_c, pos, self.__target__.rotation)
				if len(self.responses) < self.min_response_count:
					self.responses.append([response, self.evm.trial_time])
					if self.interrupts:
						return self.responses if self.max_response_count > 1 else self.responses[0]

	def set_target(self, surface, location=(0,0), registration=7):
		self.__target__ = surface
		self.__target_location__ = location
		self.__target_registration__ = registration

		if isinstance(surface, ColorWheel):
			self.rotation = surface.rotation

		try:
			surface.prerender()
		except AttributeError:
			surface = NpS(surface)

		if registration in [8, 5, 2]:
			surf_offset_x = surface.width // 2
		elif registration in [9, 6, 3]:
			surf_offset_x = surface.width
		else:
			surf_offset_x = 0
		self.__x_offset__ = location[0] + surf_offset_x
		if registration in [4, 5, 6]:
			surf_offset_y = surface.height // 2
		elif registration in [1, 2, 3]:
			surf_offset_y = surface.height
		else:
			surf_offset_y = 0
		self.__y_offset__ = location[1] + surf_offset_y

	@property
	def target(self):
		return self.__target__

	@property
	def target_location(self):
		return self.__target_location__

	@property
	def target_registration(self):
		return self.__target_registration__

	@property
	def rotation(self):
		return self.__rotation__

	@rotation.setter
	def rotation(self, angle):
		self.__rotation__ = angle


class DrawResponse(ResponseType, BoundaryInspector):

	def __init__(self):
		super(DrawResponse, self).__init__(RC_DRAW)
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
				try:
					self.responses.append([self.points, self.points[-1][2] - self.points[0][2]])
				except IndexError:
					raise TrialException("Too few points.")
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]

		# don't allow checking for stopped condition until started and outside of start boundary
		self.stop_eligible = not self.within_boundary(self.start_boundary, mp) and self.started
		if self.stop_eligible:
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
	__max_wait = None
	__null_response_value__ = None
	__min_response_count__ = None
	__max_response_count__ = None
	__interrupt__ = None
	__uses__ = None
	callbacks = {}
	listeners = None
	response_window = None
	end_collection_event = None
	responses = {}
	post_flip_tk_label = None
	terminate_after = 10  # seconds

	def __init__(self, display_callback=None, response_window=MAX_WAIT, null_response=NO_RESPONSE, response_count=[0,1],\
				 flip=True):
		super(ResponseCollector, self).__init__()
		self.__response_window__ = response_window
		self.__null_response_value__ = null_response
		self.__min_response_count__ = response_count[0]
		self.__max_response_count__ = response_count[1]
		self.__uses__ = {RC_AUDIO:False,
					   RC_KEYPRESS:False,
					   RC_MOUSEUP:False,
					   RC_MOUSEDOWN:False,
					   RC_FIXATION:False,
					   RC_SACCADE:False,
					   RC_COLORSELECT: False,
					   RC_DRAW: False
					   }
		self.response_countdown = None
		self.responses = {RC_AUDIO:[], RC_KEYPRESS:[]}
		self.display_callback = display_callback
		self.flip = flip

		# individual assignment for easy configuring in experiment.setup()
		self.audio_listener = AudioResponse()
		self.keypress_listener = KeyPressResponse()
		self.mousedown_listener = MouseDownResponse()
		self.mouseup_listener = MouseUpResponse()
		self.fixation_listener = FixationResponse()
		self.color_listener = ColorSelectionResponse()
		self.draw_listener = DrawResponse()

		# dict of listeners for iterating during collect()
		self.listeners = NamedInventory()
		self.listeners.add([self.audio_listener, self.keypress_listener, self.fixation_listener, self.mousedown_listener,\
						   self.mouseup_listener, self.color_listener, self.draw_listener])

		# todo: require that an eyelink object be passed to the rc before these are initiated
		# self.listeners[RC_SACCADE] = self.saccade_listener
		# self.saccade_listener = SaccadeResponse(self)

	def uses(self, listeners):
		"""
		Toggles available listeners on or off.
		:param listeners:
		:raise ValueError:
		"""
		if not iterable(listeners): listeners = [listeners]
		for l in listeners:
			try:
				self.__uses__[l] = True
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

	def collect(self, mouseclick_boundaries=None):
		"""
		The collection loop runs all supplied callbacks in sequence and collects responses from in-use listeners.

		:param mouseclick_boundaries:
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

		# the actual response collection loop
		self.__collect__(mouseclick_boundaries)

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
		self.response_countdown = None

	def __collect__(self, mouseclick_boundaries):
		while True:
			'''if P.development_mode and not self.end_collection_event:
				try:
					t = self.evm.trial_time
					if self.terminate_after[1] == TK_MS: t *= 1000
					if t > self.terminate_after[0]:
						print "Broke due to force timeout."
						break
				except TypeError:
					pass'''
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
			interrupt = False
			for l in self.using():
				interrupt = self.listeners[l].collect(e_queue, mouseclick_boundaries)
			if interrupt:
				break

			# display callback
			try:
				self.display_callback(*self.display_args, **self.display_kwargs)
			except TypeError:
				self.display_callback(*self.display_args)
			except KeyError:
				pass
		hide_mouse_cursor()

	def reset(self):
		for l in self.listeners:
			self.listeners[l.name].reset()

	def disable(self, listener):
		self.__uses__[listener] = False

	def enable(self, listener):
		self.__uses__[listener] = True

	def enabled(self):
		en = []
		for l in self.listeners:
			if self.__uses__[l.name]:
				en.append(l.name)
		return en

	@property
	def response_window(self):
		return self.__response_window__

	@response_window.setter
	def response_window(self, duration):
		self.__response_window__ = duration

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



