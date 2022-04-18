# -*- coding: utf-8 -*-

import pytest
import sdl2
import time

from klibs import P
from klibs import TK_S, TK_MS
from klibs import KLUserInterface as ui
from klibs.KLBoundary import RectangleBoundary

from eventfactory import click, keydown, keyup, queue_event

# NOTE: missing tests for any_key and konami_code


@pytest.fixture(scope='module')
def with_sdl():
    sdl2.SDL_ClearError()
    ret = sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_TIMER)
    assert sdl2.SDL_GetError() == b""
    assert ret == 0
    yield
    sdl2.SDL_Quit()


class UIRequestTester(object):

    def __init__(self):
        self.command = None
        self.initialized = True

    def quit(self):
        self.command = 'quit'

    def calibrate(self):
        self.command = 'calibrate'



@pytest.mark.skip("not implemented")
def test_any_key(with_sdl):
    pass


def test_key_pressed(with_sdl):

    # Initialize fake experiment class in environment
    from klibs import env
    env.exp = UIRequestTester()

    # Test basic functionality
    pressed_ab = [keydown('a'), keydown('b')]
    assert ui.key_pressed(queue=pressed_ab) == True
    assert ui.key_pressed('a', queue=pressed_ab) == True
    assert ui.key_pressed(sdl2.SDLK_a, queue=pressed_ab) == True
    assert ui.key_pressed('b', queue=pressed_ab) == True
    assert ui.key_pressed('z', queue=pressed_ab) == False

    # Test without providing queue as argument
    queue_event(pressed_ab[0])
    assert ui.key_pressed('a') == True
    assert ui.key_pressed('a') == False  # queue should be flushed after first call

    # Test intercepting of ui request commands
    quit_test = [keydown('a'), keydown('q', mod='ctrl')]
    ui.key_pressed('a', queue=quit_test)
    assert env.exp.command == 'quit'

    # Test edge cases
    assert ui.key_pressed(queue=[]) == False
    assert ui.key_pressed('a', queue=[]) == False
    assert ui.key_pressed('a', queue=[keyup('a')]) == False
    assert ui.key_pressed('a', queue=[click()]) == False
    with pytest.raises(ValueError):
        ui.key_pressed('nope', queue=pressed_ab)


@pytest.mark.skip("not implemented")
def test_konami_code(with_sdl):
    pass


def test_ui_request(with_sdl):
    
    # Initialize fake experiment and eye tracker classes in environment
    from klibs import env
    env.exp = UIRequestTester()
    env.el = UIRequestTester()
    P.eye_tracking = True

    # Initialize sets of test event queues
    normal_keys = [keydown('q'), keyup('q'), keydown('c'), click('left')]
    quit_cmd = [keydown('q', mod='meta')]
    quit_ctrl = [keydown('q', mod='ctrl')]
    calibrate_ctrl = [keydown('c', mod='ctrl')]
    quit_keysym = quit_ctrl[0].key.keysym
    not_quit = keydown('q', mod='ctrl')
    not_quit.type = sdl2.SDL_MOUSEBUTTONDOWN
    
    # Test parsing commands without execution
    assert ui.ui_request(queue=normal_keys, execute=False) == False
    assert ui.ui_request(queue=quit_cmd, execute=False) == 'quit'
    assert ui.ui_request(queue=quit_ctrl, execute=False) == 'quit'
    assert ui.ui_request(queue=calibrate_ctrl, execute=False) == 'el_calibrate'
    assert ui.ui_request(quit_keysym, execute=False) == 'quit'

    # Test execution of quit commands in environment
    assert ui.ui_request(queue=normal_keys) == False
    ui.ui_request(queue=quit_cmd)
    assert env.exp.command == 'quit'
    env.exp.command = None
    ui.ui_request(queue=quit_ctrl)
    assert env.exp.command == 'quit'
    env.exp.command = None

    # Test execution of calibrate commands in environment
    ui.ui_request(queue=calibrate_ctrl)
    assert env.el.command == 'calibrate'
    env.el.command = None
    env.el.initialized = False
    ui.ui_request(queue=calibrate_ctrl)
    assert env.el.command == None

    # Test edge cases
    assert ui.ui_request(queue=[]) == False
    assert ui.ui_request(queue=[not_quit], execute=False) == False
    with pytest.raises(TypeError):
        ui.ui_request(normal_keys, queue=[])
