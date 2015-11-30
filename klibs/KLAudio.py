# -*- coding: utf-8 -*-
__author__ = 'j. mulle'
"""
originally by mike lawrence (github.com/mike-lawrence)
"""

import sdl2
import sdl2.ext
from sdl2 import sdlmixer
import KLParams as Params
from KLConstants import *
import KLTimeKeeper as tk
try:
	import pyaudio
	import wave
	from array import array
except ImportError:
	print "\t* Warning: Pyaudio library not found; audio recording and sampling unavailable."


if Params.audio_initialized is False:
	sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
	sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
	Params.audio_initialized = True


class AudioClip(object):
		default_channel = -1
		sample = None
		__playing = False
		__volume = 128
		__volume_increment = 12.8

		def __init__(self, file_path):
			self.sample = sdl2.sdlmixer.Mix_LoadWAV(sdl2.ext.compat.byteify(file_path, "utf-8"))
			self.started = False

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
				self.volume += steps * self.__volume_increment
				self.volume = int(self.volume)

		def volume_down(self, steps=1):
			self.volume -= steps * self.__volume_increment
			self.volume = int(self.volume)

		def volume(self, volume_value):
			if type(volume_value) is float and volume_value > 1:
				self.__volume = 128 * volume_value
				return True

			if type(volume_value) is int and volume_value <= 128:
				self.__volume = volume_value
				return True

			return False  # todo: if you re-introduce warnings, one should go here

		def mute(self, state=ON):
			if state in (ON, OFF):
				self.__set_volume(state)
				return True

			return False

		def __set_volume(self, value=None):
			sdlmixer.Mix_VolumeChunk(self.sample, self.__volume if value is None else value)
			return True


class AudioSample(object):

	def __init__(self, raw_sample):
		print raw_sample
		self.array = array('h', raw_sample)
		self.peak = max(self.array)


class AudioResponse(object):
	p = None
	stream = None

	def __init__(self):
		self.p = pyaudio.PyAudio()

	def init_stream(self):
		try:
			self.stream.stop_stream()
			self.stream.close()
			self.p.terminate()
		except:
			pass
		self.p = pyaudio.PyAudio()
		self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=AR_RATE, input=True, output=True, frames_per_buffer=AR_CHUNK_SIZE)

	def __sample(self):
		if self.stream is None:
			self.init_stream()
		try:
			return AudioSample(self.stream.read(AR_CHUNK_SIZE))
		except IOError:
			self.init_stream()
			return self.__sample()

	def get_ambient_level(self, duration=5):
		sample_period = tk.CountDown(duration)
		peaks = []
		while sample_period.counting():
			peaks.append(self.__sample().peak)
		print peaks
		return sum(peaks) / len(peaks)



