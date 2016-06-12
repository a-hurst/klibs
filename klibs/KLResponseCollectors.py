__author__ = 'jono'

import abc
import sdl2
from klibs.KLUtilities import *
from klibs.KLAudio import AudioStream
from klibs.KLConstants import *
from klibs.KLNumpySurface import NumpySurface
from KLNumpySurface import aggdraw_to_array
from klibs.KLDraw import Drawbject, ColorWheel
import aggdraw
from bisect import bisect
from klibs.KLMixins import BoundaryInspector


class ResponseType(object):
	__name__ = None
	__timed_out = False

	def __init__(self, collector):
		super(ResponseType, self).__init__()
		self.collector = collector
		self.responses = []
		self.__interrupts = False
		self.__null_response_value = NO_RESPONSE
		self.__min_response_count = 0
		self.__max_response_count = 1
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
				try:
					self.collect_response(event_queue)
				except TypeError:
					print full_trace()
					self.collector.experiment.quit()
					self.collect_response()
		if self.max_collected() and self.interrupts:
			return True
		return False

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
		return self.__timed_out

	@timed_out.setter
	def timed_out(self, state):
		self.__timed_out = state == True

	@property
	def name(self):
		return self.__name__

	@abc.abstractmethod
	def collect_response(self):
		pass

	@property
	def response_count(self):
		return len(self.responses)

	@property
	def rt_label(self):
		return "T{0}_{1}_Response_{2}".format(Params.trial_number, self.name, len(self.responses) + 1)

	@property
	def null_response(self):
		return self.__null_response_value

	@null_response.setter
	def null_response(self, response_val):
		self.__null_response_value = response_val

	@property
	def max_response_count(self):
		return self.__max_response_count

	@max_response_count.setter
	def max_response_count(self, count):
		self.__max_response_count = count

	@property
	def min_response_count(self):
		return self.__min_response_count

	@max_response_count.setter
	def min_response_count(self, count):
		self.__min_response_count = count

	@property
	def interrupts(self):
		return self.__interrupts

	@interrupts.setter
	def interrupts(self, value):
		if type(value) is bool:
			self.__interrupts = value
		else:
			raise TypeError("Property 'interrupts' must be boolean.")


class KeyPressResponse(ResponseType):
	__name__ = RC_KEYPRESS

	def __init__(self, collector):
		super(KeyPressResponse, self).__init__(collector)
		self.__key_map = None

	def collect_response(self, event_queue):
		if not self.key_map:
			raise RuntimeError("No KeyMap configured to KeyPressResponse listener.")
		for event in event_queue:
			if event.type == sdl2.SDL_KEYDOWN:
				key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
				sdl_keysym = key.keysym.sym

				# check for ui requests (ie. quit, pause, calibrate)
				self.collector.experiment.ui_request(key.keysym)

				if self.key_map:
					if self.key_map.validate(sdl_keysym):
						if len(self.responses) < self.min_response_count:
							self.responses.append([self.key_map.read(sdl_keysym, "data"), Params.clock.trial_time])
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
		return self.__key_map

	@key_map.setter
	def key_map(self, key_map_obj):
		from klibs.KLKeyMap import KeyMap
		try:
			key_map_obj.any_key
		except AttributeError:
			if key_map_obj is not None:
				raise TypeError("Argument 'key_map_obj' must be a KLKeyMap object.")
		self.__key_map = key_map_obj
		self.clear_responses()


class AudioResponse(ResponseType):
	__name__="AudioResponse"

	def __init__(self, *args, **kwargs):
		super(AudioResponse, self).__init__(*args, **kwargs)
		self.stream = AudioStream(self.collector.experiment)
		self.threshold_valid = False
		self.calibrated = False

	def calibrate(self):
		peaks = []
		if Params.development_mode and Params.dm_auto_threshold:
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
				self.collector.experiment.fill()
				self.collector.experiment.message(next_message, location=Params.screen_c, registration=5)
				self.collector.experiment.flip()
				any_key_pressed = False
				while not any_key_pressed:
					for event in sdl2.ext.get_events():
						if event.type == sdl2.SDL_KEYDOWN:
							self.collector.experiment.ui_request(event.key.keysym)
							any_key_pressed = True
		self.stream.threshold = min(peaks)
		self.validate()

	def validate(self):
		validate_counter = Params.tk.countdown(5)
		self.collector.experiment.fill()
		validation_instruction = "Ok; threshold set. To ensure it's validity, please provide one (and only one) more response."
		self.collector.experiment.message(validation_instruction, location=Params.screen_c, registration=5)
		self.collector.experiment.flip()
		self.start()
		while validate_counter.counting():
			self.collector.experiment.ui_request()
			if self.stream.sample().peak >= self.stream.threshold:
				validate_counter.finish()
				self.threshold_valid = True
		self.stop()
		if self.threshold_valid:
			validation_message = "Great, validation was successful. Press any key to continue."
		else:
			validation_message = "Validation wasn't successful. Type C to re-calibrate or V to try validation again."
		self.collector.experiment.fill()
		self.collector.experiment.message(validation_message, location=Params.screen_c, registration=5, flip=True)

		response_collected = False
		while not response_collected:
			for event in sdl2.ext.get_events():
				if event.type == sdl2.SDL_KEYDOWN:
					self.collector.experiment.ui_request(event.key.keysym)
					if self.threshold_valid:
						self.calibrated = True
						return
					else:
						print [event.key.keysym, sdl2.SDLK_c, sdl2.SDLK_v]
						if event.key.keysym.sym == sdl2.SDLK_c:
							self.calibrate()
						if event.key.keysym.sym == sdl2.SDLK_v:
							self.validate()

	def collect_response(self):
		if not self.calibrated:
			raise RuntimeError("AudioResponse not ready for collection; calibration not completed.")
		if self.stream.sample().peak >= self.stream.threshold:
			if len(self.responses) < self.min_response_count:
				self.responses.append([self.stream.sample().peak, Params.clock.trial_time])
			if self.interrupts:
				self.stop()
				return self.responses if self.max_response_count > 1 else self.responses[0]

	def start(self):
		self.stream.init_stream()

	def stop(self):
		self.stream.kill_stream()


class MouseDownResponse(ResponseType, BoundaryInspector):

	def __init__(self, *args, **kwargs):
		super(MouseDownResponse, self).__init__(*args, **kwargs)

	def collect_response(self, event_queue):
		for event in event_queue:
			if event.type is sdl2.SDL_MOUSEBUTTONDOWN:
				if len(self.responses) < self.min_response_count:
					boundary =  self.within_boundaries([event.x, event.y])
					if boundary:
						self.responses.append( [boundary, [event.x, event.y], Params.clock.trial_time] )
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]

class MouseUpResponse(ResponseType, BoundaryInspector):

	def __init__(self, *args, **kwargs):
		super(MouseUpResponse, self).__init__(*args, **kwargs)

	def collect_response(self, event_queue):
		for event in event_queue:
			if event.type is sdl2.SDL_MOUSEBUTTONUP:
				if len(self.responses) < self.min_response_count:
					boundary = self.within_boundaries([event.x, event.y])
					if boundary:
						self.responses.append([boundary, [event.x, event.y], Params.clock.trial_time])
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]


class JoystickResponse(ResponseType):
	def __init__(self):
		pass

	def collect_response(self):
		pass


class SaccadeResponse(ResponseType):
	__origin = None
	__destination = None
	include_start = True
	include_end = False

	def __init__(self, collector):
		super(SaccadeResponse, self).__init__(collector)
		self.el = self.collector.experiment.eyelink

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
					self.responses.append([True, e.getStartTime() - self.collector.tracker_time])
				if self.saccade_type == EL_SACCADE_END:
					self.responses.append([True, e.getEndTime() - self.collector.tracker_time])

	@property
	def origin(self):
		return self.el.fetch_gaze_boundary(self.__origin) if self.__origin is not None else None

	@origin.setter
	def origin(self, bounds):
		# bounds = [boundary coordinates, shape]
		self.__origin = self.el.add_gaze_boundary(bounds[0], bounds[1])

	@property
	def destination(self):
		return self.el.fetch_gaze_boundary(self.__destination) if self.__destination is not None else None

	@destination.setter
	def destination(self, bounds):
		# bounds = [boundary coordinates, shape]
		self.__destination = self.el.add_gaze_boundary(bounds[0], bounds[1])


class FixationResponse(ResponseType):
	pass


class ColorSelectionResponse(ResponseType, BoundaryInspector):
	__target = None
	__x_offset = None
	__y_offset = None
	__rotation = 0
	require_alpha = True
	__target_location = (0,0)
	__target_registration = 7
	angle_response = True
	color_response = False
	click_boundary = None

	def __init__(self, collector):
		super(ColorSelectionResponse, self).__init__(collector)
		super(BoundaryInspector, self).__init__()

	def collect_response(self, event_queue):
		# todo: add some logic for excluding certain colors (ie. the background color)
		for e in event_queue:
			if e.type == sdl2.SDL_MOUSEBUTTONUP:
				pos = [e.button.x, e.button.y]
				if not self.within_boundary(pos, "color ring"):
					continue
				response = angle_between(Params.screen_c, pos, self.__target.rotation)
				if len(self.responses) < self.min_response_count:
					self.responses.append([response, Params.clock.trial_time])
					if self.interrupts:
						return self.responses if self.max_response_count > 1 else self.responses[0]

	def set_target(self, surface, location=(0,0), registration=7):
		self.__target = surface
		self.__target_location = location
		self.__target_registration = registration

		if isinstance(surface, ColorWheel):
			self.rotation = surface.rotation

		try:
			surface.prerender()
		except AttributeError:
			surface = NumpySurface(surface)

		if registration in [8, 5, 2]:
			surf_offset_x = surface.width // 2
		elif registration in [9, 6, 3]:
			surf_offset_x = surface.width
		else:
			surf_offset_x = 0
		self.__x_offset = location[0] + surf_offset_x
		if registration in [4, 5, 6]:
			surf_offset_y = surface.height // 2
		elif registration in [1, 2, 3]:
			surf_offset_y = surface.height
		else:
			surf_offset_y = 0
		self.__y_offset = location[1] + surf_offset_y

	@property
	def target(self):
		return self.__target

	@property
	def target_location(self):
		return self.__target_location

	@property
	def target_registration(self):
		return self.__target_registration

	@property
	def rotation(self):
		return self.__rotation

	@rotation.setter
	def rotation(self, angle):
		self.__rotation = angle


class DrawResponse(ResponseType, BoundaryInspector):

	def __init__(self, collector):
		super(DrawResponse, self).__init__(collector)
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
		if not self.stop_boundary or not self.start_boundary:
			self.started = True

		if not self.started:
			if self.within_boundary(self.start_boundary, mp):
				self.started = True
		if self.started and not self.start_time:
			self.start_time = Params.clock.trial_time
		if self.within_boundary(self.stop_boundary, mp):
			if self.stop_eligible and not self.stopped:
				self.stopped = True
				self.responses.append([self.points, Params.clock.trial_time])
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]

		if not self.within_boundary(self.start_boundary, mp) and not self.stop_eligible and self.started:
			self.stop_eligible = True
		if self.started and not self.stopped: # and self.within_boundary(mp, self.canvas_boundary):
			timestamp = Params.clock.trial_time - self.start_time
			trial_time = Params.clock.trial_time
			try:
				if mp != self.points[-1]:
					self.points.append((mp[0] - self.x_offset, mp[1] - self.y_offset, timestamp, trial_time))
			except IndexError:
					self.points.append((mp[0] - self.x_offset, mp[1] - self.y_offset, timestamp, trial_time))

	def reset(self):
		self.responses = []
		self.points = []
		self.started = False
		self.stopped = False
		self.stop_eligible = False

	def render_progress(self):
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
		test_p = aggdraw.Draw("RGBA", Params.screen_x_y, (0,0,0,0))
		test_p.setantialias(True)
		test_p.symbol((0,0), s, aggdraw.Pen((255,80, 125), 1, 255))
		return aggdraw_to_array(test_p)

	@property
	def active(self):
		return self.started and not self.stopped


class ResponseCollector(object):
	__experiment = None
	__max_wait = None
	__null_response_value = None
	__min_response_count = None
	__max_response_count = None
	__interrupt = None
	__uses = None
	tracker_time = None
	callbacks = {}
	listeners = {}
	response_window = None
	end_collection_event = None
	responses = {}
	post_flip_tk_label = None
	terminate_after = 10  # seconds

	def __init__(self, experiment, display_callback=None, response_window=MAX_WAIT, null_response=NO_RESPONSE, response_count=[0,1], flip=True):
		super(ResponseCollector, self).__init__()
		self.__response_window = response_window
		self.__null_response_value = null_response
		self.__min_response_count = response_count[0]
		self.__max_response_count = response_count[1]
		self.__uses = {RC_AUDIO:False,
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
		self.experiment = experiment
		self.flip = flip

		# individual assignment for easy configuring in experiment.setup()
		self.audio_listener = AudioResponse(self)
		self.keypress_listener = KeyPressResponse(self)
		self.mousedown_listener = MouseDownResponse(self)
		self.mouseup_listener = MouseUpResponse(self)
		self.saccade_listener = SaccadeResponse(self)
		self.fixation_listener = FixationResponse(self)
		self.color_listener = ColorSelectionResponse(self)
		self.draw_listener = DrawResponse(self)

		# dict of listeners for iterating during collect()
		self.listeners[RC_AUDIO] = self.audio_listener
		self.listeners[RC_KEYPRESS] = self.keypress_listener
		self.listeners[RC_SACCADE] = self.saccade_listener
		self.listeners[RC_FIXATION] = self.fixation_listener
		self.listeners[RC_MOUSEDOWN] = self.mousedown_listener
		self.listeners[RC_MOUSEUP] = self.mouseup_listener
		self.listeners[RC_COLORSELECT] = self.color_listener
		self.listeners[RC_DRAW] = self.draw_listener

	def uses(self, listeners):
		if not iterable(listeners):
			listeners = [listeners]
		for l in listeners:
			try:
				self.__uses[l] = True
			except KeyError:
				raise ValueError('{0} is not a valid response type.'.format(l))

	def using(self, listener=None):
		if not listener:
			in_use = []
			for l in self.__uses:
				if self.using(l):
					in_use.append(l)
			return in_use
		if iterable(listener):
			in_use = []
			for l in self.__uses:
				in_use.append(self.using(l))
 			return in_use
		return self.__uses[listener]

	def response_count(self, listener=None):
		count = 0
		if listener:
			return self.listeners[listener].response_count
		for l in self.uses:
			count += self.listeners[l].response_count
		return count

	def collect(self, mouseclick_boundaries=None):
		if len(self.enabled()) == 0:
			raise RuntimeError("Nothing to collect; no response listener(s) enabled.")
		# enter the loop with a cleared event queue
		pump()
		sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)

		# before flip callback
		try:
			self.before_flip_callback(*self.before_flip_args, **self.before_flip_kwargs)
		except TypeError:
			self.before_flip_callback(*self.before_flip_args)
		except KeyError:
			pass

		if self.using(RC_AUDIO):
			self.audio_listener.start()
		if self.using(RC_MOUSEDOWN) or self.using(RC_MOUSEUP) or self.using(RC_COLORSELECT):
			show_mouse_cursor()
		if self.flip:
			self.experiment.flip()
			Params.tk.sample("ResponseCollectionFlip")
			if self.post_flip_tk_label:
				Params.tk.stop(self.post_flip_tk_label)
			try:
				self.after_flip_callback(*self.after_flip_args, **self.after_flip_kwargs)
			except TypeError:
				self.after_flip_callback(*self.after_flip_args)
			except KeyError:
				pass

		# the actual response collection loop
		self.__collect(mouseclick_boundaries)

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

	def __collect(self, mouseclick_boundaries):
		self.tracker_time = self.experiment.eyelink.now() if Params.eye_tracker_available else -1
		while True:
			if Params.development_mode and not self.end_collection_event:
				try:
					t = self.experiment.clock.trial_time
					if self.terminate_after[1] == TK_MS: t *= 1000
					if t > self.terminate_after[0]:
						print "Broke due to force timeout."
						break
				except TypeError:
					pass
			event_queue = pump(True)
			for e in event_queue:
				if e.type in Params.process_queue_data:
					if Params.process_queue_data[e.type].label == self.end_collection_event:
						break
			if not self.using(RC_KEYPRESS):  # else ui_requests are handled automatically by all keypress responders
				self.experiment.ui_request(event_queue)

			# get responses for all active listeners
			interrupt = False
			for l in self.using():
				interrupt = self.listeners[l].collect(event_queue, mouseclick_boundaries)
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
			self.listeners[l].reset()

	def disable(self, listener):
		self.__uses[listener] = False

	def enable(self, listener):
		self.__uses[listener] = True

	def enabled(self):
		en = []
		for l in self.listeners:
			if self.__uses[l]:
				en.append(l)
		return en

	@property
	def experiment(self):
		return self.__experiment

	@experiment.setter
	def experiment(self, exp_obj):
		# from klibs.KLExperiment import Experiment
		# if type(super(exp_obj)) is not Experiment:
		# 	print super(exp_obj)
		# 	raise TypeError("Argument 'experiment' must be a KLExperiment.Experiment object.")
		self.__experiment = exp_obj

	@property
	def response_window(self):
		return self.__response_window

	@response_window.setter
	def response_window(self, duration):
		self.__response_window = duration

	@property
	def null_response_value(self):
		return self.__null_response_value

	@null_response_value.setter
	def null_response_value(self, value):
		self.__null_response_value = value

	@property
	def max_response_count(self):
		return self.__max_response_count

	@max_response_count.setter
	def max_response_count(self, count):
		self.__max_response_count = count

	@property
	def min_response_count(self):
		return self.__min_response_count

	@max_response_count.setter
	def min_response_count(self, count):
		self.__min_response_count = count

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



