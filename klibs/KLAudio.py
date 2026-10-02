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

# NOTE: Audio input recording/monitoring functions have been removed, but may be
# re-added at a later date. SDL2 has fairly robust audio input recording support
# and I have a working prototype of some classes that use it, but it's not worth
# the trouble of fully testing and polishing and documenting when there aren't
# any projects currently in need of it!


def _init_audio():
    # Internal method for initializing audio playback
    if not sdl2.SDL_WasInit(sdl2.SDL_INIT_AUDIO):
        sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
        Mix_OpenAudio(44100, MIX_DEFAULT_FORMAT, 2, 1024)


class AudioClip(object):
    """A class for loading and playing sound files.
    
    A range of different audio formats are supported, including WAV, MP3, OGG, and FLAC.
    See the SDL_mixer documentation for a full list of supported formats.
    
    Audio files in the project's ``ExpAssets/Resources/audio`` folder can be loaded
    directly by name without providing the full path. For example, if 'ping.ogg' has
    been added to the audio folder, you can open and play it like so::

        alert = AudioClip("ping.ogg")
        alert.play()

    Args:
        clip (str): The name or path of the audio clip to load.
        volume (float, optional): The default playback volume of the clip. Defaults
            to 1.0 (max volume).

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
        return Mix_QuickLoad_RAW(
            ctypes.cast(self._buf, ctypes.POINTER(c_ubyte)), c_uint(buflen)
        )

    def play(self, loop=False):
        """Plays the audio clip.

        If the clip is already playing, this method does nothing.

        Args:
            loop (bool, optional): Whether the audio clip should loop continouously
                instead of stopping when done. Defaults to False.

        """
        if not self.playing:
            self._channel = Mix_PlayChannel(-1, self._sample, -1 if loop else 0)
            self.started = True
    
    def stop(self):
        """Stops playback of the audio clip.

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
        """float: The playback volume of the audio clip.
        
        Ranges between 0.0 (silent) and 1.0 (100% volume).

        """
        return self._volume

    @volume.setter
    def volume(self, value):
        if type(value) != float or not (0.0 <= value <= 1.0):
            e = "Volume must be a float between 0.0 and 1.0, inclusive."
            raise ValueError(e)
        self._volume = value
        Mix_VolumeChunk(self._sample, int(self._volume * 128))


class Noise(AudioClip):
    """A class for generating audio clips of random noise.

    Currently supports generating pure white noise (uniform distribution, fully random)
    and gaussian white noise (normal distrubution, less harsh).
    
    Generated noise can also be *dichotic* (i.e. stereo), where different random noise
    is generated for the left and right channels, or *non-dichotic* (i.e. mono), where
    the noise is identical in both channels.

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
        duration (int): The length of the generated noise (in milliseconds).
        color (str, optional): The type of noise to generate, can be either 'white' or
            'white_gaussian'. Defaults to 'white'.
        dichotic (bool, optional): If True, generates dichotic noise instead of
            non-dichotic noise. Defaults to False.
        volume (float, optional): The playback volume of the noise. Defaults to
            1.0 (max volume).

    """
    
    def __init__(self, duration, color="white", dichotic=False, volume=1.0):
        if color not in ('white', 'white_gaussian'):
            e = "Noise color must be either 'white' or 'white_gaussian' (got '{}')."
            raise ValueError(e.format(color))
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

    Currently supports generating sine wave tones (a.k.a. 'pure tones') as well as
    square wave tones, which have a more digital, buzz-like sound.

    Example usage::

        alerting_cue = Tone(100, frequency=2200)
        alerting_cue.play()

    Args:
        duration (int): The length of the tone (in milliseconds).
        wave_type (str, optional): The type of tone to generate, can be either 'sine'
            or 'square'. Defaults to 'sine'.
        frequency (int, optional): The frequency (in Hz) of the tone to generate.
            Defaults to 432 Hz.
        volume (float, optional): The playback volume of the tone. Defaults to
            1.0 (max volume).

    """
    
    def __init__(self, duration, wave_type='sine', frequency=432, volume=1.0):
        if wave_type not in ('sine', 'square'):
            e = "Tone wave type must be either 'sine' or 'square' (got '{}')."
            raise ValueError(e.format(wave_type))
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
