__author__ = 'jono'

import abc
from libexec.klibs.KLUtilities import *
from libexec.klibs.KLAudio import AudioStream

class ResponseCollector(object):
	callback = None

	def __init__(self, experiment, display_callback=None, max_wait=MAX_WAIT, null_response=NO_RESPONSE, response_count=[0,1], flip=True, interrupt=False):
		super(ResponseCollector, self).__init__()
		if display_callback and not hasattr(display_callback, 'call'):
			raise ValueError("Argument 'callback_function' must be callable.")
		self.experiment = experiment
		self.callback = display_callback
		self.__callback_args = []
		self.__callback_kwargs = {}
		self.__max_wait = max_wait
		self.__null_response_value = null_response
		self.__min_response_count = response_count[0]
		self.__max_response_count = response_count[1]
		self.flip = flip
		self.__interrupt = interrupt
		self.response_window = Params.tk.countdown(self.max_wait, False)

		self.responses = []

	def uses(self, interfaces):
		pass

	@abc.abstractmethod
	def run(self, *callback_args, **callback_kwargs):
		pass

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


class ResponseType(object):

	def __init__(self):
		super(ResponseType, self).__init__()

	@abc.abstractmethod
	def collect(self):
		pass

class KeyPressResponse(ResponseType):

	def __init__(self, key_map, *args, **kwargs):
		super(KeyPressCollector, self).__init__(*args, **kwargs)
		self.key_map = key_map

	def collect(self, *callback_args, **callback_kwargs):
		#  enter the loop with a cleared event queue
		sdl2.SDL_PumpEvents()
		sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)

		if self.flip: self.experiment.flip()

		rt_label = "Trial_{0}_KeyPress_Response".format(Params.trial_number)
		Params.tk.start(rt_label)
		self.response_window.start()
		while self.response_window.counting():
			pump()
			try:
				self.callback(*self.callback_args, **self.callback_kwargs)
			except TypeError:
				pass
			for event in sdl2.ext.get_events():
				if event.type == sdl2.SDL_KEYDOWN:
					key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
					sdl_keysym = key.keysym.sym
					key_name = sdl2.keyboard.SDL_GetKeyName(sdl_keysym)

					# check for ui requests (ie. quit, pause, calibrate)
					self.experiment.ui_request(key.keysym)

					if self.key_map.validate(sdl_keysym):
						if len(self.responses) < self.min_response_count:
							self.responses.append([self.key_map.read(sdl_keysym, "data"), Params.tk.elapsed(rt_label)])
						if self.interrupt:
							return self.responses if self.max_response_count > 1 else self.responses[0]
					else:
						invalid_key = True
						# todo: write adjustable behaviour for informing participants of invalid keys
						# wrong_key_message = "Please respond using '{0}'.".format(key_map.valid_keys())
						# self.alert(wrong_key_message)
						# invalid_key = False
		if len(self.responses) == 0:
			return [self.null_response_value, TIMEOUT]
		else:
			return self.responses if self.max_response_count > 1 else self.responses[0]


class AudioResponseCollector(ResponseCollector):

	def __init__(self, *args, **kwargs):
		super(AudioResponseCollector, self).__init__(*args, **kwargs)
		self.__threshold = None
		self.stream = AudioStream(self.experiment)
		self.threshold_valid = False

	def calibrate(self):
		peaks = []
		for i in range(0, 3):
			message = "Provide a normal sample of your intended response."
			peaks.append( self.stream.get_peak_during(3, message) )
			if i < 3:
				next_message = "Got it; {0} more samples to collect. Press any key to continue".format(2-i)
				self.experiment.fill()
				self.experiment.message(next_message, location=Params.screen_c, registration=5)
				any_key = KeyPressCollector(Params.key_maps['*'],experiment=self.experiment, interrupt=True)
				any_key.run()
		self.threshold = min(peaks)
		self.validate()

	def validate(self):
		validate_counter = Params.tk.countdown(5)
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
			key_map = Params.key_maps["*"]
		else:
			validation_message = "Validation wasn't successful. Type C to re-calibrate or V to try validation again."
			from libexec.klibs.KLKeyMap import KeyMap
			key_map = KeyMap("",['c','v'],['c','v'],[sdl2.SDLK_c, sdl2.SDLK_v])
		advance = KeyPressCollector(key_map, experiment=self.experiment, interrupt=True)
		self.experiment.fill()
		self.experiment.message(validation_message, location=Params.screen_c, registration=5)
		response = advance.run()
		if self.threshold_valid:
			return
		else:
			if response[0] == "c":
				self.calibrate()
			if response[0] == "v":
				self.validate()

	def collect(self):
		if not self.threshold_valid:
			pass  # write an exception for this
		sdl2.SDL_PumpEvents()
		sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)

		if self.flip: self.experiment.flip()

		rt_label = "Trial_{0}_Audio_Response".format(Params.trial_number)
		Params.tk.start(rt_label)
		self.response_window.start()
		while self.response_window.counting():
			pump()
			try:
				self.callback(*self.callback_args, **self.callback_kwargs)
			except TypeError:
				pass
			if self.stream.sample().peak >= self.threshold:
				if len(self.responses) < self.min_response_count:
					self.responses.append([True, Params.tk.elapsed(rt_label)])
				if self.interrupt:
					return self.responses if self.max_response_count > 1 else self.responses[0]
		if len(self.responses) == 0:
			return [self.null_response_value, TIMEOUT]
		else:
			return self.responses if self.max_response_count > 1 else self.responses[0]

	@property
	def threshold(self):
		return self.__threshold

	@threshold.setter
	def threshold(self, value):
		self.__threshold = value