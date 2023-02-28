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

@pytest.fixture(scope='module')
def with_txtm(with_sdl):
    import klibs.KLEnvironment as env
    from klibs.KLText import TextManager
    P.font_dirs = [resource_filename('klibs', 'resources/font')]
    P.exp_font_dir = tempfile.gettempdir()
    env.txtm = TextManager()
    yield
    env.txtm = None

@pytest.fixture(scope='module')
def with_text_init(with_txtm):
    import klibs.KLGraphics
    from klibs.KLGraphics.core import _set_display_params
    from klibs.KLCommunication import init_default_textstyles
    _set_display_params((1920, 1080), 21.5, 60.0)
    init_default_textstyles()
    yield