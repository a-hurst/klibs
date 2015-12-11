__author__ = 'jono'

import abc
from klibs.KLUtilities import *
from klibs.KLAudio import AudioStream

RC_AUDIO = 'audio'
RC_KEYPRESS = 'keypress'

class ResponseType(object):
	__name__ = None

	def __init__(self, collector):
		super(ResponseType, self).__init__()
		self.collector = collector
		self.responses = []
		self.interrupt = False
		self.__null_response_value = NO_RESPONSE
		self.__min_response_count = 0
		self.__max_response_count = 1

	def clear_responses(self):
		self.responses = []

	def max_collected(self):
		return self.response_count == self.max_response_count

	def name(self):
		return self.__name__

	def collect(self):
		if not self.max_collected():
			self.__collect()
		if self.max_collected() and self.interrupt:
			self.collector.response_window.finish()

	@abc.abstractmethod
	def __collect(self):
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


class KeyPressResponse(ResponseType):
	__name__ = "KeyPress"

	def __init__(self, key_map=None, *args, **kwargs):
		super(ResponseType, self).__init__(*args, **kwargs)
		self.__key_map = None
		self.key_map = key_map

	def __collect(self):
		for event in sdl2.ext.get_events():
			if event.type == sdl2.SDL_KEYDOWN:
				key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
				sdl_keysym = key.keysym.sym

				# check for ui requests (ie. quit, pause, calibrate)
				self.experiment.ui_request(key.keysym)

				if self.key_map:
					if self.key_map.validate(sdl_keysym):
						if len(self.responses) < self.min_response_count:
							self.responses.append([self.key_map.read(sdl_keysym, "data"), Params.tk.elapsed(self.rt_label)])
						if self.interrupt:
							return self.responses if self.max_response_count > 1 else self.responses[0]
					else:
						invalid_key = True
						# todo: write adjustable behaviour for informing participants of invalid keys
						# wrong_key_message = "Please respond using '{0}'.".format(key_map.valid_keys())
						# self.alert(wrong_key_message)
						# invalid_key = False

	@property
	def key_map(self):
		return self.key_map

	@key_map.setter
	def key_map(self, key_map_obj):
		from klibs.KLKeyMap import KeyMap
		if type(key_map_obj) is not KeyMap:
			raise TypeError("Argument 'key_map_obj' must be a KLKeyMap object.")
		self.__key_map = key_map_obj
		self.clear_responses()


class AudioResponse(ResponseType):

	def __init__(self, *args, **kwargs):
		super(AudioResponse, self).__init__(*args, **kwargs)
		self.__threshold = None
		self.stream = AudioStream(self.experiment)
		self.threshold_valid = False
		self.keypress_listener = KeyPressResponse(Params.key_maps['*'],experiment=self.experiment, interrupt=True)

	def calibrate(self):
		peaks = []
		for i in range(0, 3):
			message = "Provide a normal sample of your intended response."
			peaks.append( self.stream.get_peak_during(3, message) )
			if i < 3:
				next_message = "Got it; {0} more samples to collect. Press any key to continue".format(2-i)
				self.experiment.fill()
				self.experiment.message(next_message, location=Params.screen_c, registration=5)
				self.keypress_listener
				while len(self.keypress_listener.responses) == 0:
					self.keypress_listener.collect()
		self.threshold = min(peaks)
		self.validate()

	def validate(self):
		validate_counter = Params.tk.countdown(5)
		self.keypress_listener.clear_responses()
		while validate_counter.counting():
			self.experiment.ui_request()
			self.experiment.fill()
			validation_instruction = "Ok; threshold set. To ensure it's validity, please provide one (and only one) more response."
			self.experiment.message(validation_instruction, location=Params.screen_c, registration=5)
			self.experiment.flip()
			if self.stream.sample().peak >= self.threshold:
				validate_counter.finish()
				self.threshold_valid = True
		if self.threshold_valid:
			validation_message = "Great, validation was successful. Press any key to continue."
			self.keypress_listener.key_map = Params.key_maps["*"]
		else:
			validation_message = "Validation wasn't successful. Type C to re-calibrate or V to try validation again."
			from klibs.KLKeyMap import KeyMap
			self.keypress_listener.key_map.key_map = KeyMap("",['c','v'],['c','v'],[sdl2.SDLK_c, sdl2.SDLK_v])
		self.experiment.fill()
		self.experiment.message(validation_message, location=Params.screen_c, registration=5)
		self.keypress_listener.clear_responses()
		self.keypress_listener.collect()
		if self.threshold_valid:
			return
		else:
			if self.keypress_listener.responses[0] == "c":
				self.calibrate()
			if self.keypress_listener.responses[0] == "v":
				self.validate()

	def __collect(self):
		# if not self.threshold_valid:
		# 	pass  # write an exception for this
		# sdl2.SDL_PumpEvents()
		# sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)
		#
		# if self.flip: self.experiment.flip()
		#
		# Params.tk.start(rt_label)
		# self.response_window.start()
		# while self.response_window.counting():
		# 	pump()
		# 	try:
		# 		self.callback(*self.callback_args, **self.callback_kwargs)
		# 	except TypeError:
		# 		pass
		if self.stream.sample().peak >= self.threshold:
			if len(self.responses) < self.min_response_count:
				self.responses.append([True, Params.tk.elapsed(self.rt_label)])
			if self.interrupt:
				return self.responses if self.max_response_count > 1 else self.responses[0]
		# if len(self.responses) == 0:
		# 	return [self.null_response_value, TIMEOUT]
		# else:
		# 	return self.responses if self.max_response_count > 1 else self.responses[0]

	@property
	def threshold(self):
		return self.__threshold

	@threshold.setter
	def threshold(self, value):
		self.__threshold = value


class ResponseCollector(object):
	callback = None
	__experiment = None
	__callback_args = []
	__callback_kwargs = {}
	__max_wait = None
	__null_response_value = None
	__min_response_count = None
	__max_response_count = None
	__uses = []
	__interrupt = None
	response_window = None
	responses = []
	listeners = {}

	def __init__(self, experiment, display_callback=None, max_wait=MAX_WAIT, null_response=NO_RESPONSE, response_count=[0,1], flip=True, interrupt=True):
		super(ResponseCollector, self).__init__()
		if display_callback and not hasattr(display_callback, 'call'):
			raise ValueError("Argument 'callback_function' must be callable.")
		self.__max_wait = max_wait
		self.__null_response_value = null_response
		self.__min_response_count = response_count[0]
		self.__max_response_count = response_count[1]
		self.interrupt = interrupt
		self.experiment = experiment
		self.callback = display_callback
		self.flip = flip

		# individual assignment for easy configuring in experiment.setup()
		self.response_window = Params.tk.countdown(self.max_wait, False)
		self.audio_listener = AudioResponse(self)

		# dict of listeners for iterating during collect()
		self.keypress_listener = KeyPressResponse(self)
		self.listeners['audio'] = self.audio_listener
		self.listeners['keypress'] = self.keypress_listener

	def uses(self, listeners):
		try:
			iter(listeners)
		except TypeError:
			listeners = [listeners]
		for l in listeners:
			try:
				self.__uses[l] = True
			except KeyError:
				raise ValueError('{0} is not a valid response type.'.format(l))

	def response_count(self, listener=None):
		count = 0
		if listener:
			return self.listeners[listener].response_count
		for l in self.uses:
			count += self.listeners[l].response_count

	def collect(self):
		#  enter the loop with a cleared event queue
		sdl2.SDL_PumpEvents()
		sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)

		if self.audio_response and not self.audio_response.calibrated:
			raise RuntimeError("AudioResponse not ready for collection; calibration not completed.")

		if self.flip: self.experiment.flip()
		self.response_window.start()
		while self.response_window.counting():

			# check for responses of all types that have been assigned in self.uses
			if not self.uses[RC_KEYPRESS]:  # done automatically by keypress responder
				self.experiment.ui_request()
			if self.response_count() == self.max_response_count and self.interrupt:
				self.response_window.finish()
			for l in self.uses:
				if self.uses[l] and self.response_window.counting():  # if response_window.finish() called, stop
					self.listeners[l].collect()
			try:
				self.callback(*self.callback_args, **self.callback_kwargs)
			except TypeError:
				pass

		for l in self.uses:
			if self.uses[l]:
				if not self.response_count(l):
					self.listeners[l].responses.append( [l.null_response_value, TIMEOUT])
				else:
					while self.response_count(l) < self.listeners[l].min_response_count:
						self.listeners[l].responses.append( [l.null_response_value, TIMEOUT])

	@property
	def experiment(self):
		return self.__experiment

	@experiment.setter
	def experiment(self, exp_obj):
		from klibs.KLExperiment import Experiment
		if type(exp_obj) is not Experiment:
			raise TypeError("Argument 'experiment' must be a KLExperiment.Experiment object.")
		self.__experiment = exp_obj

	@property
	def max_wait(self):
		return self.__max_wait

	@max_wait.setter
	def max_wait(self, duration):
		self.__max_wait = duration

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
	def callback_args(self):
		return self.__callback_args

	@callback_args.setter
	def callback_args(self, args_list):
		if type(args_list) is not (list, tuple):
			raise TypeError('Args list must be either a list or a tuple')
		self.__callback_args = args_list

	@property
	def callback_kwargs(self):
		return self.__callback_kwargs

	@callback_args.setter
	def callback_kwargs(self, args_dict):
		if type(args_dict) is not dict:
			raise TypeError('The args_dict must be a dictionary.')
		self.__callback_args = args_dict

	@property
	def response(self):
		return self.responses[0]

	@property
	def interrupt(self):
		return self.__interrupt

	@interrupt.setter
	def interrupt(self, value):
		if type(value) is bool:
			self.interrupt = value
		else:
			raise TypeError("Argument 'interrupt' must be boolean.")




