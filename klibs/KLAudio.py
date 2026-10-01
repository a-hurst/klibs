# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import ctypes
from ctypes import c_uint, c_ubyte

import numpy as np
import sdl2
import sdl2.ext
from sdl2.sdlmixer import (
    Mix_OpenAudio, Mix_LoadWAV, Mix_QuickLoad_RAW, Mix_PlayChannel,
    Mix_HaltChannel, Mix_Playing, Mix_VolumeChunk, MIX_DEFAULT_FORMAT,
)

from klibs import P



def _init_audio():
    # Internal method for initializing audio playback
    if not sdl2.SDL_WasInit(sdl2.SDL_INIT_AUDIO):
        sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
        Mix_OpenAudio(44100, MIX_DEFAULT_FORMAT, 2, 1024)


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
            self._sample = self._array_to_sample(clip)
        else:
            self._sample = self._file_to_sample(clip)
        self._channel = -1
        self.volume = volume
        self.started = False

    def _file_to_sample(self, filename):
        """Creates an SDL2_mixer MixChunk sample from a WAV file.
        
        """
        if filename in os.listdir(P.audio_dir):
            file_path = os.path.join(P.audio_dir, filename)
        elif os.path.isfile(filename):
            file_path = filename
        else:
            raise IOError("Unable to locate audio file at ({0})".format(filename))
        return Mix_LoadWAV(sdl2.ext.compat.byteify(file_path, "utf-8"))

    def _array_to_sample(self, arr):
        """Creates an SDL2_mixer MixChunk sample from a 2-channel 16-bit numpy array.
        
        """
        arr_bytes = arr.tobytes()
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
        return self._volume

    @volume.setter
    def volume(self, value):
        if type(value) != float or not (0.0 <= value <= 1.0):
            raise ValueError("Clip volume must be a float between 0.0 and 1.0, inclusive.")
        self._volume = value
        Mix_VolumeChunk(self._sample, int(self._volume * 128))


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
        self._color = color
        noise_L = self._generate_noise(color, duration)
        noise_R = self._generate_noise(color, duration) if dichotic else noise_L
        super(Noise, self).__init__(np.c_[noise_L, noise_R], volume)
        
    def _generate_noise(self, color, duration):
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
        self._type = wave_type
        self._frequency = frequency
        tone = self._generate_tone(wave_type, frequency, duration)
        super(Tone, self).__init__(np.c_[tone, tone], volume)
    
    def _generate_tone(self, wavetype, hz, duration):
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
