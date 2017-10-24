# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'
import warnings
import math

with warnings.catch_warnings():
	warnings.simplefilter("ignore")
	import sdl2.ext
	from sdl2.sdlmixer import Mix_LoadWAV, Mix_PlayChannel, Mix_Playing, Mix_HaltChannel, Mix_VolumeChunk
	warnings.simplefilter("default")


from klibs.KLConstants import AR_CHUNK_READ_SIZE, AR_CHUNK_SIZE, AR_AUTO_THRESHOLD, AR_RATE, AR_THRESHOLD, AUDIO_ON, \
	AUDIO_OFF
import klibs.KLParams as P
from klibs.KLUtilities import pump, flush
from klibs.KLUserInterface import ui_request
from klibs.KLGraphics.KLDraw import Circle
from klibs.KLGraphics import fill, blit, flip

from klibs import PYAUDIO_AVAILABLE

if PYAUDIO_AVAILABLE:
	import pyaudio
	from array import array



if P.audio_initialized is False:
	sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
	sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
	P.audio_initialized = True


class AudioManager(object):
	listeners = {}

	def __init__(self):
		"""


		"""
		super(AudioManager, self).__init__()

	# def create_listener(self, name=None, threshold=AR_AUTO_THRESHOLD):
	# 	if not PYAUDIO_AVAILABLE:
	# 		raise RuntimeError("PyAudio module not loaded; KLAudio.AudioResponseListener not available.")
	# 	listener = AudioResponseListener(, threshold)
	# 	if name:
	# 		self.listeners[name] = listener
	# 	return listener

	def clip(self, file_path):
		"""

		:param file_path:
		:return:
		"""
		return AudioClip(file_path)


# Note AudioClip is an adaption of code originally written by mike lawrence (github.com/mike-lawrence)
class AudioClip(object):
		default_channel = -1
		sample = None
		__playing = False
		__volume = 128
		__volume_increment = 12.8

		def __init__(self, file_path):
			"""

			:param file_path:
			"""
			super(AudioClip, self).__init__()
			self.sample = Mix_LoadWAV(sdl2.ext.compat.byteify(file_path, "utf-8"))
			self.started = False
			self.channel = self.default_channel

		def play(self, channel=-1, loops=0):
			"""

			:param channel:
			:param loops:
			"""
			self.channel = Mix_PlayChannel(channel, self.sample, loops)
			self.__playing = True

		def playing(self):
			"""


			:return:
			"""
			if self.started:
				if Mix_Playing(self.channel):
					return True
				else:
					self.__playing = False
					return False

			return False
		
		def stop(self):
			if self.playing:
				Mix_HaltChannel(self.channel)
				self.__playing = False

		def volume_up(self, steps=1):
			"""

			:param steps:
			"""
			self.__volume += steps * self.__volume_increment
			self.__volume = int(self.volume)

		def volume_down(self, steps=1):
			"""

			:param steps:
			"""
			self.__volume -= steps * self.__volume_increment
			self.__volume = int(self.volume)

		def mute(self, state=AUDIO_ON):
			"""

			:param state:
			:return:
			"""
			Mix_VolumeChunk(self.sample, 0 if state == AUDIO_OFF else self.__volume)
			return False

		@property
		def volume(self):
			return self.__volume

		@volume.setter
		def volume(self, volume_value):
			if type(volume_value) is float and volume_value < 1:
				self.__volume = 128 * volume_value
			elif type(volume_value) is int and volume_value <= 128:
				self.__volume = volume_value
			else:
				raise ValueError("Provide either an integer between 1 and 128 or a float between 0 and 1.")
			Mix_VolumeChunk(self.sample, self.__volume)


class AudioSample(object):

	def __init__(self, raw_sample, threshold):
		"""

		:param raw_sample:
		:param threshold:
		"""
		super(AudioSample, self).__init__()
		self.array = array('h', raw_sample)
		self.peak = max(self.array)
		self.trough = min(self.array)
		self.mean = sum(self.array) / len(self.array)
		self.threshold = None if threshold == AR_AUTO_THRESHOLD else threshold

	def is_below(self, threshold=None):
		"""

		:param threshold:
		:return:
		"""
		return self.peak < threshold if threshold else self.threshold

	def is_above(self, threshold=None):
		"""

		:param threshold:
		:return:
		"""
		return self.trough > threshold if threshold else self.threshold


class AudioStream(object):
	p = None
	stream = None

	def __init__(self, threshold=1):
		"""

		:param threshold:
		"""
		super(AudioStream, self).__init__()
		self.p = pyaudio.PyAudio()
		self.threshold = 1
		# if threshold == AR_AUTO_THRESHOLD:
		# 	self.threshold = 3 * self.get_ambient_level()  # this is probably inadequate and should employ a log scale
		# else:
		# 	self.threshold = threshold

	def sample(self):
		"""


		:return:
		"""
		if not self.stream:
			self.init_stream()
		# try:

		chunk = self.stream.read(AR_CHUNK_SIZE, False)
		sample = AudioSample(chunk, self.threshold)

		return sample
		# except AttributeError:
		# 	return AudioSample(self.stream.read(AR_CHUNK_SIZE), P.AR_AUTO_THRESHOLD)

	def init_stream(self):
		"""


		"""
		try:
			self.kill_stream()
		except (AttributeError, IOError) as e:
			pass  # on first pass, no stream exists; on subsequent passes, extant stream should be stopped & overwritten

		self.p = pyaudio.PyAudio()
		self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=AR_RATE, input=True, output=True, \
															  frames_per_buffer=AR_CHUNK_SIZE)

	def kill_stream(self):
			self.stream.stop_stream()
			self.stream.close()
			self.p.terminate()

	def get_ambient_level(self, period=1):

		"""

		:param period:
		:return:
		"""
		sample_period = P.tk.countdown(period)
		warn_message = "Please remain quite while the ambient noise level is sampled. Sampling will begin in 3 seconds."
		sampling_message = "Sampling Complete In {0} Seconds"
		peaks = []

		fill()
		#message(warn_message, location=P.screen_c, registration=5)
		flip()
		sample_period.start_clock()
		#message(sampling_message.format(int(math.ceil(sample_period.remaining())), font_size="48pt"), location=P.screen_c, registration=5)

		while sample_period.counting():
			ui_request()
			peaks.append(self.sample().peak)

		return sum(peaks) / len(peaks)

	def get_peak_during(self, period=3, message=None):
		"""

		:param period:
		:param message:
		:return:
		"""
		# initial_diameter = int(P.screen_x * 0.05)
		local_peak = 0
		pump()
		flush()

		sample_period = P.tk.countdown(period)
		first_flip_rest = False
		if message:
			pass
			#message = .message(message, location=P.screen_c, registration=5, blit=False)
		if not self.stream:
			self.init_stream()
		self.init_stream()
		while sample_period.counting():
			sample = self.sample().peak
			ui_request()
			fill()
			if sample > local_peak:
				local_peak = sample
			peak_circle = int((local_peak * P.screen_x * 0.9) / 65000)
			sample_circle = int((sample * P.screen_x * 0.9) / 65000)
			if peak_circle < 5:
				peak_circle = 5
			if sample_circle < 5:
				sample_circle = 5
			if message:
				blit(message, position=[25,25], registration=7)
			blit(Circle(peak_circle, fill=[255, 145, 0]), position=P.screen_c, registration=5)
			blit(Circle(sample_circle, fill=[84, 60, 182]), position=P.screen_c, registration=5)
			flip()
			if not first_flip_rest:
				sample_period.start_clock()
				first_flip_rest = True
		self.kill_stream()

		return local_peak









