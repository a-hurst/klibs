__author__ = 'j. mulle'
"""
originally by mike lawrence (github.com/mike-lawrence)
"""

import sdl2
import sdl2.ext
from sdl2 import sdlmixer
import os
import Params
from KLConstants import *

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

