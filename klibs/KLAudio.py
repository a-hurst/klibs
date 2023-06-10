# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import sys
import math
import time
import ctypes
from ctypes import c_uint, c_ubyte
from array import array

import numpy as np 
import sdl2.ext
from sdl2 import SDLK_c, SDLK_v
from sdl2.sdlmixer import (Mix_LoadWAV, Mix_QuickLoad_RAW, Mix_PlayChannel, Mix_PlayChannelTimed, 
    Mix_HaltChannel, Mix_Playing, Mix_VolumeChunk)

from klibs.KLEnvironment import EnvAgent
from klibs.KLConstants import AR_CHUNK_READ_SIZE, AR_CHUNK_SIZE, AR_RATE
from klibs import P
from klibs.KLInternal import hide_stderr
from klibs.KLEventQueue import pump, flush
from klibs.KLUtilities import peak
from klibs.KLTime import CountDown
from klibs.KLUserInterface import ui_request, key_pressed, any_key
from klibs.KLGraphics.KLDraw import Ellipse
from klibs.KLGraphics import fill, blit, flip
from klibs.KLCommunication import message

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    pa_stream = pyaudio.Stream
except ImportError:
    PYAUDIO_AVAILABLE = False
    pa_stream = Ellipse # so AudioStream subclassing Stream doesn't break KLAudio if no pyaudio


# TODO: This needs a heavy rewrite, both conceptually and implementation-wise


class AudioManager(object):
    """A class for initializing and configuring audio input/output during the experiment
    runtime. An instance of this is created in the experiment object when the experiment
    runtime starts, and can be accessed from within your experiment class using
    'self.audio'. As such, you should never need to create your own AudioManager object.

    Attributes:
        input (:obj:`~pyaudio.PyAudio`, None): An interface for creating/destroying audio streams
            and getting information about the host's audio hardware/APIs. See the PyAudio
            documentation for more information. If the pyaudio module is not installed, this
            attribute will be a NoneType instead.

    """
    def __init__(self):
        super(AudioManager, self).__init__()
        if not sdl2.SDL_WasInit(sdl2.SDL_INIT_AUDIO):
            sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
            sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
        self.input = None
        self.stream = None
        if PYAUDIO_AVAILABLE:
            try:
                self.input = pyaudio.PyAudio()
                self.device_name = self.input.get_default_input_device_info()['name']
                self.stream = AudioStream(self.input)
            except IOError:
                print("* Warning: Could not find a valid audio input device, audio input will "
                    "not be available.\n")
                self.input = None
                self.stream = None

    def calibrate(self):
        """Determines a threshold loudness to use for vocal responses based on sample input from
        the participant. See :obj:`~klibs.KLAudio.AudioCalibrator` for more details.

        Returns:
            int: an integer from 1 to 32767 representing the threshold value to use for vocal
                responses.

        Raises:
            RuntimeError: If using auto thresholding and the recorded ambient noise level is 0.

        """
        c = AudioCalibrator()
        return c.calibrate()
    
    def reload_stream(self):
        # PyAudio can't handle interrupted device connections (unplugging/replugging), so we need
        # to fully terminate and reopen the PyAudio instance to reconnect to an interrupted device
        if not self.stream.is_stopped():
                self.stream.stop()
        try:
            self.stream.close()
            self.stream = AudioStream(self.input)
            return False
        except IOError:
            self.input.terminate()
            self.input = pyaudio.PyAudio()
            default_device_name = self.input.get_default_input_device_info()['name']
            if default_device_name != self.device_name:
                raise RuntimeError('Audio input device disconnected mid-experiment.')
            self.stream = AudioStream(self.input)
            return True

    def shut_down(self):
        if self.input:
            try:
                if not self.stream.is_stopped():
                    self.stream.stop()
                self.stream.close()
            except IOError:
                pass
            self.input.terminate()


# Note AudioClip is an adaption of code originally written by mike lawrence (github.com/mike-lawrence)
class AudioClip(object):
    """A class for loading and playing sound clips from files or :obj:`~numpy.ndarray` arrays. Only
    16-bit WAVE files with a sample rate of 44100Hz are currently supported, but broader
    OGG/FLAC/WAV support is planned. Multiple AudioClip objects can be played simultaneously.

    If loading a clip from a file located in the project's ``ExpAssets/Resources/audio`` folder,
    you only need to provide the name of the file. Otherwise, you need to provide the full path.

    Usage::

        alert = AudioClip("Ping.wav", volume=0.5)
        alert.play()

    Args:
        clip (str or :obj:`~numpy.ndarray`): The audio clip to load, can be either a path to a file
            or a 2-column :class:`~numpy.int16` numpy array.
        volume (float, optional): The volume of the audio clip. Defaults to 1.0 (max volume).

    """

    def __init__(self, clip, volume=1.0):
        super(AudioClip, self).__init__()
        if isinstance(clip, np.ndarray):
            self._sample = self.__array_to_sample(clip)
        else:
            self._sample = self.__file_to_sample(clip)
        self._channel = -1
        self.volume = volume
        self.started = False

    def __file_to_sample(self, filename):
        """Creates an SDL2_mixer MixChunk sample from a WAV file.
        
        """
        if filename in os.listdir(P.audio_dir):
            file_path = os.path.join(P.audio_dir, filename)
        elif os.path.isfile(filename):
            file_path = filename
        else:
            raise IOError("Unable to locate audio file at ({0})".format(filename))
        return Mix_LoadWAV(sdl2.ext.compat.byteify(file_path, "utf-8"))

    def __array_to_sample(self, arr):
        """Creates an SDL2_mixer MixChunk sample from a 2-channel 16-bit numpy array.
        
        """
        arr_bytes = arr.tostring()
        buflen = len(arr_bytes)
        self._buf = (c_ubyte * buflen).from_buffer_copy(arr_bytes)
        return Mix_QuickLoad_RAW(ctypes.cast(self._buf, ctypes.POINTER(c_ubyte)), c_uint(buflen))

    def play(self, loop=False):
        """Plays the audio clip, if it is not already playing.

        Args:
            loop (bool, optional): Whether the audio clip should play in a loop until it is
                stopped manually, or only play once. Defaults to False (play once).

        """
        if not self.playing:
            self._channel = Mix_PlayChannel(-1, self._sample, -1 if loop else 0)
            self.started = True
    
    def stop(self):
        """Stops the audio clip if it is currently playing.

        """
        if self.playing:
            Mix_HaltChannel(self._channel)

    @property
    def playing(self):
        """bool: Indicates whether the audio clip is currently playing.

        """
        return Mix_Playing(self._channel) == 1 if self.started else False

    @property
    def volume(self):
        """float: The volume of the audio clip, ranging from 0.0 (silent) to 1.0 (100% volume).

        """
        return self.__volume

    @volume.setter
    def volume(self, value):
        if type(value) != float or not (0.0 <= value <= 1.0):
            raise ValueError("Clip volume must be a float between 0.0 and 1.0, inclusive.")
        self.__volume = value
        Mix_VolumeChunk(self._sample, int(self.__volume * 128))


class Noise(AudioClip):
    """A class for generating audio clips of different types of random noise.

    Currently supports generating pure white noise (uniform distribution, fully random) or
    gaussian white noise (normal distrubution, less harsh).
    
    Generated noise can also be *dichotic* (i.e. stereo), where different random noise is
    generated for the left and right channels, or *non-dichotic* (i.e. mono), where the noise
    is identical in both channels.

    Example usage::

        background_noise = Noise(8000, volume=0.5)
        background_noise.play()

        if self.evm.before('warning_onset'):
            draw_stimuli()
        background_noise.volume = 1.0 # double loudness of noise

        if self.evm.before('warning_end'):
            draw_stimuli()
        background_noise.volume = 0.5 # return loudness to original value

    Args:
        duration (int): The milliseconds of noise to generate.
        color (str, optional): The type of noise to generate, can be either 'white' or
            'white_gaussian'. Defaults to 'white'.
        dichotic (bool, optional): If True, generates dichotic noise instead of non-dichotic
            noise. Defaults to False.
        volume (float, optional): The volume of the audio clip. Defaults to 1.0 (max volume).

    """
    
    def __init__(self, duration, color="white", dichotic=False, volume=1.0):
        self.__color = color
        noise_L = self.__generate_noise(color, duration)
        noise_R = self.__generate_noise(color, duration) if dichotic else noise_L
        super(Noise, self).__init__(np.c_[noise_L, noise_R], volume)
        
    def __generate_noise(self, color, duration):
        """Generates a single channel of random noise.
        
        """
        max_int = 2**16/2 - 1 # 32767, which is the max/min value for a signed 16-bit int
        dtype = np.int16 # Default audio format for SDL_Mixer is signed 16-bit integer
        sample_rate = 44100/2 # sample rate for each channel is 22050 kHz, so 44100 total.
        size = int((duration/1000.0)*sample_rate)
        
        if color == "white":
            arr = np.random.uniform(low=-1.0, high=1.0, size=size) * max_int
        elif color == "white_gaussian":
            arr = np.random.normal(loc=0.0, scale=0.33, size=size) * max_int
        
        return arr.astype(dtype)
        

class Tone(AudioClip):
    """A class for generating audio clips of different types of tones.

    Currently supports generating sine wave tones (a.k.a. 'pure tones') and square wave tones,
    which have a more digital, buzz-like sound.

    Example usage::

        alerting_cue = Tone(100, frequency=2200)
        alerting_cue.play()

    Args:
        duration (int): The milliseconds of tone to generate.
        wave_type (str, optional): The type of tone waveform to generate, can be either 'sine'
            or 'square'. Defaults to 'sine'.
        frequency (int, optional): The frequency (in Hz) of the tone to generate. Defaults to
            432 Hz.
        volume (float, optional): The volume of the audio clip. Defaults to 1.0 (max volume).

    """
    
    def __init__(self, duration, wave_type='sine', frequency=432, volume=1.0):
        self.__type = wave_type
        self.__frequency = frequency
        tone = self.__generate_tone(wave_type, frequency, duration)
        super(Tone, self).__init__(np.c_[tone, tone], volume)
    
    def __generate_tone(self, wavetype, hz, duration):
        """Generates a single channel of tone at a given frequency.
        
        """
        max_int = 2**16/2 - 1 # 32767, which is the max/min value for a signed 16-bit int
        dtype = np.int16 # Default audio format for SDL_Mixer is signed 16-bit integer
        sample_rate = 44100/2 # sample rate for each channel is 22050 kHz, so 44100 total.
        size = int((duration/1000.0)*sample_rate)
        
        if wavetype == "sine":
            arr = np.sin(np.pi * np.arange(size)/sample_rate * hz) * max_int
        elif wavetype == "square":
            arr = np.sin(np.pi * np.arange(size)/sample_rate * hz)
            arr = np.sign(arr) * max_int
        
        return arr.astype(dtype)


class AudioSample(object):
    """A sample of audio input from an AudioStream.

    Args:
        raw_sample (str): A bytestring of audio as returned by pyaudio.Sample.read() or
            AudioSample.read().
    
    Attributes:
        array (:obj:`~array.array`): A Python array object containing the data from the input sample
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
        self.mean = sum(self.array) // len(self.array)


class AudioStream(pa_stream, EnvAgent):
    """A stream of audio from the default system audio input device (usually a microphone).
    See the :obj:`~pyaudio.Stream` documentation for a full list of this class's methods and
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
        with hide_stderr(macos_only=True):
            # hide_stderr is to suppress a macOS API deprecation warning from portaudio
            pyaudio.Stream.__init__(self, PA_manager=pa_instance,
                format=pyaudio.paInt16, channels=1, rate=AR_RATE, frames_per_buffer=AR_CHUNK_SIZE,
                input=True, output=False, start=False
            )

    def sample(self):
        """Fetches the most recent audio sample from the input stream. If the stream is not already
        open when this method is called, it will open one automatically.

        Returns:
            :obj:`~KLAudio.AudioSample`: An AudioSample containing the most recent 1024 frames from
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
        return sum(peaks) / float(len(peaks))

    def get_peak_during(self, period, msg=None):
        """Determines the peak loudness value recorded over a given period. Displays a visual
        callback that shows the current input volume and the loudest peak encounteredduring the
        interval so far.
        
        Args:
            period (numeric): the number of seconds to record input for.
            msg (:obj:`~klibs.KLGraphics.KLNumpySurface.NumpySurface`, optional): a rendered message
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