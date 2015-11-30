# -*- coding: utf-8 -*-
__author__ = 'j. mulle'
"""
Note AudioClip is an adaption of code originally written by mike lawrence (github.com/mike-lawrence)
"""

import sdl2
import sdl2.ext
from sdl2 import sdlmixer
import KLParams as Params
from KLConstants import *
import KLTimeKeeper as tk
import math

try:
	import pyaudio
	import wave
	from array import array
	PYAUDIO_AVAILABLE = True
except ImportError:
	PYAUDIO_AVAILABLE = False
	print "\t* Warning: Pyaudio library not found; audio recording, audio responses and audio sampling unavailable."


if Params.audio_initialized is False:
	sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
	sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
	Params.audio_initialized = True


class AudioManager(object):
	experiment = None
	listeners = {}

	def __init__(self, experiment):
		super(AudioManager, self).__init__()
		self.experiment = experiment

	def create_listener(self, name=None, threshold=AR_AUTO_THRESHOLD):
		if not PYAUDIO_AVAILABLE:
			raise RuntimeError("PyAudio module not loaded; KLAudio.AudioResponseListener not available.")
		listener = AudioResponseListener(self.experiment, threshold)
		if name:
			self.listeners[name] = listener
		return listener

	def clip(self, file_path):
		return AudioClip(file_path)


class AudioClip(object):
		default_channel = -1
		sample = None
		__playing = False
		__volume = 128
		__volume_increment = 12.8

		def __init__(self, file_path):
			super(AudioClip, self).__init__()
			self.sample = sdl2.sdlmixer.Mix_LoadWAV(sdl2.ext.compat.byteify(file_path, "utf-8"))
			self.started = False
			self.channel = self.default_channel

		def play(self, channel=-1, loops=0):
			self.channel = sdl2.sdlmixer.Mix_PlayChannel(channel, self.sample, loops)
			self.__playing = True

		def playing(self):
			if self.started:
				if sdl2.sdlmixer.Mix_Playing(self.channel):
					return True
				else:
					self.__playing = False
					return False

			return False

		def volume_up(self, steps=1):
			self.__volume += steps * self.__volume_increment
			self.__volume = int(self.volume)

		def volume_down(self, steps=1):
			self.__volume -= steps * self.__volume_increment
			self.__volume = int(self.volume)

		def mute(self, state=AUDIO_ON):
			sdlmixer.Mix_VolumeChunk(self.sample, 0 if state == AUDIO_OFF else self.__volume)
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
			sdlmixer.Mix_VolumeChunk(self.sample, self.__volume)


class AudioSample(object):

	def __init__(self, raw_sample, threshold):
		super(AudioSample, self).__init__()
		self.array = array('h', raw_sample)
		self.peak = max(self.array)
		self.trough = min(self.array)
		self.mean = sum(self.array) / len(self.array)
		self.threshold = None if threshold == AR_AUTO_THRESHOLD else threshold

	def is_below(self, threshold=None):
		return self.peak < threshold if threshold else self.threshold

	def is_above(self, threshold=None):
		return self.trough > threshold if threshold else self.threshold


class AudioResponseListener(object):
	p = None
	stream = None

	def __init__(self, experiment, threshold):
		super(AudioResponseListener, self).__init__()
		self.experiment = experiment
		self.p = pyaudio.PyAudio()
		if threshold == AR_AUTO_THRESHOLD:
			self.threshold = 3 * self.get_ambient_level()  # this is probably in adequate and should employ a log scale
		else:
			self.threshold = threshold

	def init_stream(self):
		try:
			self.stream.stop_stream()
			self.stream.close()
			self.p.terminate()
		except AttributeError:
			pass  # on first pass, no stream exists; on subsequent passes, extant stream should be stopped & overwritten
		self.p = pyaudio.PyAudio()
		self.stream = self.p.open(format=pyaudio.paInt16, channels=2, rate=AR_RATE, input=True, output=True, frames_per_buffer=AR_CHUNK_SIZE)

	def __sample(self):
		if self.stream is None:
			self.init_stream()
		try:
			try:
				return AudioSample(self.stream.read(AR_CHUNK_SIZE), self.threshold)
			except AttributeError:
				return AudioSample(self.stream.read(AR_CHUNK_SIZE), Params.AR_AUTO_THRESHOLD)
		except IOError:
			self.init_stream()
			return self.__sample()

	def get_ambient_level(self, duration=5):
		sample_period = Params.tk.countdown(duration)
		warn_period = Params.tk.countdown(3)
		warn_message = "Please remain quite while the ambient noise level is sampled. Sampling will begin in {0} seconds."
		sampling_message = "Sampling Complete In {0} Seconds"
		peaks = []
		while warn_period.counting():
			self.experiment.fill()
			self.experiment.message(warn_message.format(int(math.ceil(warn_period.remaining()))), location=Params.screen_c, registration=5)
			self.experiment.flip()

		while sample_period.counting():
			self.experiment.fill()
			self.experiment.message(sampling_message.format(int(math.ceil(sample_period.remaining())), font_size="48pt"), location=Params.screen_c, registration=5)
			peaks.append(self.__sample().peak)
			self.experiment.flip()
		return sum(peaks) / len(peaks)





