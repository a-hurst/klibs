__author__ = 'jono'

import KLParams as Params
import abc
from KLConstants import *
from KLUtilities import *


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


class KeyPressCollector(ResponseCollector):

	def __init__(self, key_map, *args, **kwargs):
		super(KeyPressCollector, self).__init__(*args, **kwargs)
		self.key_map = key_map

	def run(self, *callback_args, **callback_kwargs):
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



