# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import os
import sys
import warnings
import math
from array import array

with warnings.catch_warnings():
	warnings.simplefilter("ignore")
	import sdl2.ext
	from sdl2.sdlmixer import (Mix_LoadWAV, Mix_PlayChannel, Mix_Playing, Mix_HaltChannel, 
		Mix_VolumeChunk)

from klibs.KLEnvironment import EnvAgent
from klibs.KLConstants import AR_CHUNK_READ_SIZE, AR_CHUNK_SIZE, AR_RATE
from klibs import P
from klibs.KLUtilities import pump, flush, peak
from klibs.KLTime import CountDown
from klibs.KLUserInterface import ui_request
from klibs.KLGraphics.KLDraw import Ellipse
from klibs.KLGraphics import fill, blit, flip
from klibs.KLCommunication import message

try:
	import pyaudio
	PYAUDIO_AVAILABLE = True
except ImportError:
	print "\t* Warning: PyAudio library not found; audio input will not be available."
	PYAUDIO_AVAILABLE = False



class AudioManager(object):

	def __init__(self):
		super(AudioManager, self).__init__()
		if not sdl2.SDL_WasInit(sdl2.SDL_INIT_AUDIO):
			sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
			sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
		if PYAUDIO_AVAILABLE:
			self.input = pyaudio.PyAudio()
		else:
			self.input = None

	def open(self, *args, **kwargs):
		if not PYAUDIO_AVAILABLE:
			raise RuntimeError("The PyAudio module is not installed; audio input is not available.")
		return self.input.open(*args, **kwargs)


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

		def mute(self):
			Mix_VolumeChunk(self.sample, 0)

		def unmute(self):
			Mix_VolumeChunk(self.sample, self.__volume)

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
		self.threshold = threshold

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


class AudioStream(EnvAgent):
	stream = None

	def __init__(self, threshold=1):

		super(AudioStream, self).__init__()
		self.threshold = 1


	def sample(self):

		if not self.stream:
			self.init_stream()

		chunk = self.stream.read(AR_CHUNK_SIZE, False)
		sample = AudioSample(chunk, self.threshold)

		return sample


	def init_stream(self):

		try:
			self.kill_stream()
		except (AttributeError, IOError) as e:
			pass  # on first pass, no stream exists; on subsequent passes, extant stream should be stopped & overwritten
		
		# Due to using a depricated macOS API, portaudio will print a warning everytime it's called.
		# The following lines suppress this error.
		devnull = os.open(os.devnull, os.O_WRONLY)
		old_stderr = os.dup(2)
		sys.stderr.flush()
		os.dup2(devnull, 2)
		os.close(devnull)
		self.stream = self.exp.audio.open(
			format=pyaudio.paInt16, channels=1, rate=AR_RATE,
			input=True, output=True, frames_per_buffer=AR_CHUNK_SIZE
		)
		os.dup2(old_stderr, 2)
		os.close(old_stderr)

	def kill_stream(self):
		self.stream.stop_stream()
		self.stream.close()

	def get_ambient_level(self, period=1):
		
		warn_msg = ("Please remain quite while the ambient noise level is sampled. "
					"Sampling will begin in {0} seconds.")
		peaks = []

		wait_period = CountDown(3)
		while wait_period.counting():
			ui_request()
			fill()
			remaining = int(math.ceil(wait_period.remaining()))
			message(warn_msg.format(remaining), location=P.screen_c, registration=5)
			flip()
		
		fill()
		flip()
		sample_period = CountDown(period)
		while sample_period.counting():
			ui_request()
			peaks.append(self.sample().peak)

		return sum(peaks) / len(peaks)

	def get_peak_during(self, period=3, msg=None):

		local_peak = 0
		last_sample = 0
		if msg:
			msg = message(msg, blit_txt=False)
		
		flush()
		self.init_stream()
		self.sample() # eat first part of stream to avoid
		sample_period = CountDown(period+0.05)
		while sample_period.counting():
			ui_request()
			sample = self.sample().peak
			if sample_period.elapsed() < 0.05:
				# Sometimes 1st or 2nd peaks are extremely high for no reason, so ignore first 50ms
				continue
			if sample > local_peak:
				local_peak = sample
			sample_avg = (sample + last_sample) / 2
			peak_circle = peak(5, int((local_peak*P.screen_x*0.9) / 65000))
			sample_circle = peak(5, int((sample_avg*P.screen_x*0.9) / 65000))
			last_sample = sample
			
			fill()
			blit(Ellipse(peak_circle, fill=[255, 145, 0]), location=P.screen_c, registration=5)
			blit(Ellipse(sample_circle, fill=[84, 60, 182]), location=P.screen_c, registration=5)
			if msg:
				blit(msg, location=[25,25], registration=7)
			flip()
		self.kill_stream()

		return local_peak
