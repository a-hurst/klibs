import pytest
import sdl2
import time

from klibs import P
from klibs.KLAudio import Tone, Noise

from conftest import with_sdl


def test_Tone(with_sdl):
    # Test init with different arguments
    tst1 = Tone(100, frequency=1000, volume=0.5)
    tst2 = Tone(100, 'square')
    with pytest.raises(ValueError):
        Tone(100, 'supersaw')

    # Test getting/setting volume
    assert tst1.volume == 0.5
    tst1.volume = 0.1
    assert tst1.volume == 0.1

    # Test basic playback
    assert tst1.playing == False
    tst1.play()
    assert tst1.playing == True
    tst1.stop()
    assert tst1.playing == False


def test_Noise(with_sdl):
    # Test init with different arguments
    tst1 = Noise(100, dichotic=True, volume=0.5)
    tst2 = Noise(100, color='white_gaussian')
    with pytest.raises(ValueError):
        Noise(100, color='magenta')

    # Test getting/setting volume
    assert tst1.volume == 0.5
    tst1.volume = 0.1
    assert tst1.volume == 0.1

    # Test basic playback
    assert tst1.playing == False
    tst1.play()
    assert tst1.playing == True
    tst1.stop()
    assert tst1.playing == False
