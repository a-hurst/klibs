__author__ = 'jono'

import abc
from klibs.KLUtilities import *
from klibs.KLAudio import AudioStream

RC_AUDIO = 'audio'
RC_KEYPRESS = 'keypress'
RC_MOUSECLICK = 'mouseclick'
RC_MOUSEDOWN = 'mousedown'
RC_MOUSEUP = 'mouseup'

class ResponseType(object):
	__name__ = None

	def __init__(self, collector):
		super(ResponseType, self).__init__()
		self.collector = collector
		self.responses = []
		self.__interrupts = False
		self.__null_response_value = NO_RESPONSE
		self.__min_response_count = 0
		self.__max_response_count = 1

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
					self.collect_response()
		if self.max_collected() and self.interrupts:
			return True
		return False

	def reset(self):
		self.responses = []

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
							self.responses.append([self.key_map.read(sdl_keysym, "data"), self.collector.response_window.elapsed()])
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
		self.__threshold = None
		self.stream = AudioStream(self.collector.experiment)
		self.threshold_valid = False
		self.calibrated = False

	def calibrate(self):
		peaks = []
		if Params.development_mode:
			self.stream.threshold = self.stream.get_ambient_level()
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
		self.threshold = min(peaks)
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
			if self.stream.sample().peak >= self.threshold:
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
						if event.key.sym == sdl2.SDLK_c:
							self.calibrate()
						else:
							self.validate()

	def collect_response(self):
		if not self.calibrated:
			raise RuntimeError("AudioResponse not ready for collection; calibration not completed.")
		if self.stream.sample().peak >= self.threshold:
			if len(self.responses) < self.min_response_count:
				self.responses.append([self.stream.sample().peak, self.collector.response_window.elapsed()])
			if self.interrupts:
				self.stream.stream.stop_stream()
				return self.responses if self.max_response_count > 1 else self.responses[0]

	def start(self):
		self.stream.init_stream()

	def stop(self):
		self.stream.kill_stream()

	@property
	def threshold(self):
		return self.__threshold

	@threshold.setter
	def threshold(self, value):
		self.__threshold = value


class MouseDownResponse(ResponseType):

	def __init__(self, *args, **kwargs):
		super(MouseDownResponse, self).__init__(*args, **kwargs)
		self.boundaries = {}

	def add_click_boundary(self, label, bounds):
		self.boundaries[label] = bounds

	def add_click_boundaries(self, boundaries):
		self.boundaries.update(boundaries)

	def within_boundary(self, position, boundary=None):
		boundaries = [boundary] if boundary else self.boundaries
		for b in boundaries:
			x_within =  position[0] in range(self.boundaries[b][0], self.boundaries[b][2])
			y_within =  position[1] in range(self.boundaries[b][1], self.boundaries[b][3])
			if x_within and y_within:
				return b
		return False

	def collect_response(self, event_queue, boundaries=None):
		for event in event_queue:
			if event.type is sdl2.SDL_MOUSEBUTTONDOWN:
				if len(self.responses) < self.min_response_count:
					boundary =  self.within_boundary([event.x, event.y], boundaries)
					if boundary:
						self.responses.append( [boundary, self.collector.response_window.elapsed()] )
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]


class MouseUpResponse(ResponseType):

	def __init__(self, *args, **kwargs):
		super(MouseUpResponse, self).__init__(*args, **kwargs)
		self.boundaries = {}

	def add_click_boundary(self, label, bounds):
		self.boundaries[label] = bounds

	def add_click_boundaries(self, boundaries):
		self.boundaries.update(boundaries)

	def within_boundary(self, position, boundary=None):
		boundaries = [boundary] if boundary else self.boundaries
		for b in boundaries:
			x_within = position[0] in range(self.boundaries[b][0], self.boundaries[b][2])
			y_within = position[1] in range(self.boundaries[b][1], self.boundaries[b][3])
			if x_within and y_within:
				return b
		return False

	def collect_response(self, event_queue, boundaries=None):
		for event in event_queue:
			if event.type is sdl2.SDL_MOUSEBUTTONUP:
				if len(self.responses) < self.min_response_count:
					boundary = self.within_boundary([event.x, event.y],  boundaries)
					if boundary:
						self.responses.append([boundary, self.collector.response_window.elapsed()])
				if self.interrupts:
					return self.responses if self.max_response_count > 1 else self.responses[0]


class JoystickResponse(ResponseType):
	def __init__(self):
		pass

	def collect_response(self):
		pass


class ResponseCollector(object):
	__experiment = None
	__max_wait = None
	__null_response_value = None
	__min_response_count = None
	__max_response_count = None
	__interrupt = None
	__uses = None
	callbacks = {}
	listeners = {}
	response_window = None
	responses = {}
	post_flip_tk_label = None

	def __init__(self, experiment, display_callback=None, response_window=MAX_WAIT, null_response=NO_RESPONSE, response_count=[0,1], flip=True):
		super(ResponseCollector, self).__init__()
		self.__response_window = response_window
		self.__null_response_value = null_response
		self.__min_response_count = response_count[0]
		self.__max_response_count = response_count[1]
		self.__uses = {RC_AUDIO:False, RC_KEYPRESS:False, RC_MOUSEUP:False, RC_MOUSEDOWN:False}
		self.responses = {RC_AUDIO:[], RC_KEYPRESS:[]}
		self.display_callback = display_callback
		self.experiment = experiment
		self.flip = flip

		# individual assignment for easy configuring in experiment.setup()
		self.audio_listener = AudioResponse(self)
		self.keypress_listener = KeyPressResponse(self)
		self.mousedown_listener = MouseDownResponse(self)
		self.mouseup_listener = MouseUpResponse(self)

		# dict of listeners for iterating during collect()
		self.listeners[RC_AUDIO] = self.audio_listener
		self.listeners[RC_KEYPRESS] = self.keypress_listener
		# self.listeners[RC_MOUSEDOWN] = self.mousedown_listener
		# self.listeners[RC_MOUSEUP] = self.mouseup_listener

	def uses(self, listeners):
		if type(listeners) not in [list, tuple]:
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

		return self.__uses[listener]

	def response_count(self, listener=None):
		count = 0
		if listener:
			return self.listeners[listener].response_count
		for l in self.uses:
			count += self.listeners[l].response_count
		return count

	def collect(self, mouseclick_boundaries=None):
		# enter the loop with a cleared event queue
		sdl2.SDL_PumpEvents()
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
		if self.flip:
			self.experiment.flip()
			Params.tk.sample("ResponseCollectionFlip")
			if self.post_flip_tk_label:
				Params.tk.stop(self.post_flip_tk_label)
		self.response_window.start()

		while self.response_window.counting():
			event_queue = pump(True)
			if not self.using(RC_KEYPRESS):  # else ui_requests are handled automatically by all keypress responders
				self.experiment.ui_request(event_queue)

			# get responses for all active listeners
			interrupt = False
			for l in self.using():
				interrupt = self.listeners[l].collect(event_queue, mouseclick_boundaries)
			if interrupt:
				Params.tk.start('exiting')
				break
			# display callback
				try:
					self.display_callback(*self.display_args, **self.display_kwargs)
				except TypeError:
					self.display_callback(*self.display_args)
				except KeyError:
					pass
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
				listener.responses.append( [listener.null_response, TIMEOUT])
		if self.using(RC_AUDIO):
			self.audio_listener.stop()

	def reset(self):
		for l in self.listeners:
			self.listeners[l].reset()

	def disable(self, listener):
		self.__uses[listener] = False

	def enable(self, listener):
		self.__uses[listener] = True

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
		self.__response_window = Params.tk.countdown(duration, TK_MS)

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



