import pytest
import sdl2
import time

from klibs import P
from klibs.KLAudio import Tone, Noise

from conftest import with_sdl


def test_Tone(with_sdl):
    tst = Tone(100, frequency=1000, volume=0.5)

def test_Noise(with_sdl):
    tst = Noise(100, volume=0.5)