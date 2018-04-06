# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import os
import sys
import warnings
import math
import time
from array import array

with warnings.catch_warnings():
	warnings.simplefilter("ignore")
	import sdl2.ext
	from sdl2 import SDLK_c, SDLK_v
	from sdl2.sdlmixer import (Mix_LoadWAV, Mix_PlayChannel, Mix_Playing, Mix_HaltChannel, 
		Mix_VolumeChunk)

from klibs.KLEnvironment import EnvAgent
from klibs.KLConstants import AR_CHUNK_READ_SIZE, AR_CHUNK_SIZE, AR_RATE
from klibs import P
from klibs.KLUtilities import pump, flush, peak
from klibs.KLTime import CountDown
from klibs.KLUserInterface import ui_request, key_pressed, any_key
from klibs.KLGraphics.KLDraw import Ellipse
from klibs.KLGraphics import fill, blit, flip
from klibs.KLCommunication import message

try:
	import pyaudio
	PYAUDIO_AVAILABLE = True
except ImportError:
	PYAUDIO_AVAILABLE = False


class AudioManager(object):
	"""A class for initializing and configuring audio input/output during the experiment
	runtime. An instance of this is created in the experiment object when the experiment
	runtime starts, and can be accessed from within your experiment class using
	'self.audio'. As such, you should never need to create your own AudioManager object.

	Attributes:
		input (:obj:`pyaudio.PyAudio`, None): An interface for creating/destroying audio streams
			and getting information about the host's audio hardware/APIs. See the PyAudio
			documentation for more information. If the pyaudio module is not installed, this
			attribute will be a NoneType instead.

	"""
	def __init__(self):
		super(AudioManager, self).__init__()
		if not sdl2.SDL_WasInit(sdl2.SDL_INIT_AUDIO):
			sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
			sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
		if PYAUDIO_AVAILABLE:
			self.input = pyaudio.PyAudio()
			self.stream = AudioStream(self.input)
		else:
			print("\t* Warning: PyAudio library not found; audio input will not be available.")
			self.input = None
			self.stream = None

	def calibrate(self):
		"""Determines a threshold loudness to use for vocal responses based on sample input from
		the participant. See :obj:`KLAudio.AudioCalibrator` for more details.

		Returns:
			int: an integer from 1 to 32767 representing the threshold value to use for vocal
				responses.

		Raises:
			RuntimeError: If using auto thresholding and the recorded ambient noise level is 0.

		"""
		c = AudioCalibrator()
		return c.calibrate()
	
	def reload_stream(self):
		# experimental, to hopefully fix a bug where audio responses randomly stop working
		if not self.stream.is_stopped():
			self.stream.stop()
		self.stream.close()
		time.sleep(0.005) # hopefully this prevents "Bad Device" errors.
		self.stream = AudioStream(self.input)

	def shut_down(self):
		if not self.stream.is_stopped():
			self.stream.stop()
		self.stream.close()
		self.input.terminate()


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
			self.sample = Mix_LoadWAV(sdl2.ext.compat.byteify(file_path, "utf-8"))

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
	"""A sample of audio input from an AudioStream.

	Args:
		raw_sample (str): A bytestring of audio as returned by pyaudio.Sample.read() or
			AudioSample.read().
	
	Attributes:
		array (:obj:`array.array`): A Python array object containing the data from the input sample
			in signed 16-bit ('h') format.
		peak (int): The highest value in the sample (maximum is 32767).
		trough (int): The lowest value in the sample (minimum is -32768).
		mean (int): The average value in the sample.

	"""
	def __init__(self, raw_sample):
		super(AudioSample, self).__init__()
		self.array = array('h', raw_sample)
		self.peak = max(self.array)
		self.trough = min(self.array)
		self.mean = sum(self.array) / len(self.array)


class AudioStream(pyaudio.Stream, EnvAgent):
	"""A stream of audio from the default system audio input device (usually a microphone).
	See the :obj:`pyaudio.Stream` documentation for a full list of this class's methods and
	attributes.

	Args:
		threshold (int, optional): A threshold value for comparing sample peaks and means to.
			Defaults to 1.

	"""
	def __init__(self, pa_instance, threshold=1):
		if not PYAUDIO_AVAILABLE:
			raise RuntimeError("The PyAudio module is not installed; audio input is not available.")
		EnvAgent.__init__(self)
		self.threshold = threshold
		# Due to using a depricated macOS API, portaudio will print a warning everytime it's called.
		# The following lines suppress this error.
		devnull = os.open(os.devnull, os.O_WRONLY)
		old_stderr = os.dup(2)
		sys.stderr.flush()
		os.dup2(devnull, 2)
		os.close(devnull)
		pyaudio.Stream.__init__(self, PA_manager=pa_instance,
			format=pyaudio.paInt16, channels=1, rate=AR_RATE, frames_per_buffer=AR_CHUNK_SIZE,
			input=True, output=False, start=False
		)
		os.dup2(old_stderr, 2)
		os.close(old_stderr)

	def sample(self):
		"""Fetches the most recent audio sample from the input stream. If the stream is not already
		open when this method is called, it will open one automatically.

		Returns:
			:obj:`KLAudio.AudioSample`: An AudioSample containing the most recent 1024 frames from
				the input stream.
		"""
		if not self.is_active():
			self.start()
		chunk = self.read(AR_CHUNK_SIZE, False)
		sample = AudioSample(chunk)
		return sample

	def start(self):
		"""Starts the input stream. If the stream is already active, calling this method will
		restart it.
		"""
		if self.is_active():
			self.stop()
		self.start_stream()
	
	def stop(self):
		"""Stops the input stream. To prevent conflicts between AudioStreams and conserve system
		resources, you should call this whenever you are done using a stream.
		"""
		self.stop_stream()


class AudioCalibrator(EnvAgent):

	def __init__(self):
		super(AudioCalibrator, self).__init__()
		self.stream = None
		self.threshold = None
		self.threshold_valid = False

	def calibrate(self):
		"""Determines the loudness threshold for vocal responses based on sample input from the
		participant. 
		
		During calibration, input levels are monitored during three 3-second intervals in which 
		participants are asked to make a single vocal response. After all three samples are
		collected, the threshold is set to the smallest peak value of the three samples, and the
		participant is prompted to make one more response to see if it passes the threshold.
		If it does, calibration is complete and will end after any key is pressed. If it doesn't,
		the participant will be notified that calibration wasn't sucessful and will be prompted to
		press 'c' to calibrate again, or 'v' to try validation again.

		As a convenience for programmers writing and testing experiments using audio input, if
		KLibs is in development mode and the Params option 'dm_auto_threshold' is set to True, this
		calibration process will be skipped for a quicker one requiring no user input. In this
		mode, the ambient room noise is recorded for one second after a countdown, and the
		threshold is then set to be five times the average peak volume from that interval.
		This will not work if your microphone does not pick up any ambient room noise.

		Returns:
			int: an integer from 1 to 32767 representing the threshold value to use for vocal
				responses.

		Raises:
			RuntimeError: If using auto thresholding and the recorded ambient noise level is 0.
		"""
		if not self.stream:
			self.stream = self.exp.audio.stream
		if P.development_mode and P.dm_auto_threshold:
			ambient = self.get_ambient_level()
			if ambient == 0:
				e = ("Ambient level appears to be zero, increase the gain on your microphone or "
					 "disable auto-thresholding.")
				raise RuntimeError(e)
			elif ambient*5 > 32767:
				e = ("Ambient noise level too high to use auto-thresholding. Reduce the gain on "
					 "your microphone or try and reduce the noise level in the room.")
				raise RuntimeError(e)
			self.threshold = ambient * 5
		else:
			peaks = []
			for i in range(0, 3):
				msg = "Provide a normal sample of your intended response."
				peaks.append( self.get_peak_during(3, msg) )
				if i < 2:
					s = "" if i==1 else "s" # to avoid "1 more samples"
					next_message = (
						"Got it! {0} more sample{1} to collect. "
						"Press any key to continue".format(2 - i, s)
					)
					fill()
					message(next_message, location=P.screen_c, registration=5)
					flip()
					any_key()
			self.threshold = min(peaks)
			self.__validate()
		return self.threshold

	def __validate(self):
		instruction = ("Okay, threshold set! "
					   "To ensure its validity, please provide one (and only one) more response.")
		fill()
		message(instruction, location=P.screen_c, registration=5)
		flip()
		self.stream.start()
		validate_counter = CountDown(5)
		while validate_counter.counting():
			ui_request()
			if self.stream.sample().peak >= self.threshold:
				validate_counter.finish()
				self.threshold_valid = True
		self.stream.stop()

		if self.threshold_valid:
			validation_msg = "Great, validation was successful! Press any key to continue."
		else:
			validation_msg = ("Validation wasn't successful. "
							  "Type C to re-calibrate or V to try validation again.")
		fill()
		message(validation_msg, location=P.screen_c, registration=5)
		flip()
		selection_made = False
		while not selection_made:
			q = pump(True)
			if self.threshold_valid:
				if key_pressed(queue=q):
					return
			else:
				if key_pressed(SDLK_c, queue=q):
					self.calibrate()
				elif key_pressed(SDLK_v, queue=q):
					self.__validate()

	def get_ambient_level(self, period=1):
		"""Determines the average ambient noise level from the input stream over a given period.
		Gives a 3-second countdown before starting to help the user ensure they are quiet.
		
		Args:
			period (numeric, optional): The number of seconds to record input for. Defaults to one
				second.

		Returns:
			int: The average of the peaks of all samples recorded during the period.

		"""
		warn_msg = ("Please remain quiet while the ambient noise level is sampled. "
					"Sampling will begin in {0} second{1}.")
		peaks = []

		wait_period = CountDown(3)
		while wait_period.counting():
			ui_request()
			fill()
			remaining = int(math.ceil(wait_period.remaining()))
			s = "" if remaining == 1 else "s" # to avoid "1 seconds"
			message(warn_msg.format(remaining, s), location=P.screen_c, registration=5)
			flip()
		
		self.stream.start()
		fill()
		flip()
		sample_period = CountDown(period)
		while sample_period.counting():
			ui_request()
			peaks.append(self.stream.sample().peak)
		self.stream.stop()
		return sum(peaks) / len(peaks)

	def get_peak_during(self, period, msg=None):
		"""Determines the peak loudness value recorded over a given period. Displays a visual
		callback that shows the current input volume and the loudest peak encounteredduring the
		interval so far.
		
		Args:
			period (numeric): the number of seconds to record input for.
			msg (:obj:`KLGraphics.KLNumpySurface.NumpySurface`, optional): a rendered message
				to display in the top-right corner of the screen during the sampling loop.

		Returns:
			int: the loudest peak of all samples recorded during the period.

		"""
		local_peak = 0
		last_sample = 0
		if msg:
			msg = message(msg, blit_txt=False)
		
		flush()
		self.stream.start()
		sample_period = CountDown(period+0.05)
		while sample_period.counting():
			ui_request()
			sample = self.stream.sample().peak
			if sample_period.elapsed() < 0.05:
				# Sometimes 1st or 2nd peaks are extremely high for no reason, so ignore first 50ms
				continue
			if sample > local_peak:
				local_peak = sample
			sample_avg = (sample + last_sample) / 2
			peak_circle = peak(5, int((local_peak/32767.0) * P.screen_y*0.8))
			sample_circle = peak(5, int((sample_avg/32767.0) * P.screen_y*0.8))
			last_sample = sample
			
			fill()
			blit(Ellipse(peak_circle, fill=[255, 145, 0]), location=P.screen_c, registration=5)
			blit(Ellipse(sample_circle, fill=[84, 60, 182]), location=P.screen_c, registration=5)
			if msg:
				blit(msg, location=[25,25], registration=7)
			flip()
		self.stream.stop()
		return local_peak