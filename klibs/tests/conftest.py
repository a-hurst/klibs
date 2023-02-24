# -*- coding: utf-8 -*-

import sdl2
import pytest
import tempfile
from pkg_resources import resource_filename

from klibs import P


@pytest.fixture(scope='module')
def with_sdl():
    sdl2.SDL_ClearError()
    ret = sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_TIMER)
    assert sdl2.SDL_GetError() == b""
    assert ret == 0
    yield
    sdl2.SDL_Quit()
