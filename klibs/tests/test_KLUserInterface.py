# -*- coding: utf-8 -*-

import pytest
import sdl2
import time

from klibs import P
from klibs import TK_S, TK_MS
from klibs import KLUserInterface as ui
from klibs.KLBoundary import RectangleBoundary

from conftest import with_sdl
from eventfactory import click, keydown, keyup, queue_event

# NOTE: missing tests for any_key and konami_code


# Fixtures and helpers

class UIRequestTester(object):

    def __init__(self):
        self.command = None
        self.initialized = True

    def quit(self):
        self.command = 'quit'

    def calibrate(self):
        self.command = 'calibrate'


# Actual tests

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


def test_mouse_clicked(with_sdl):

    # Initialize fake experiment class in environment
    from klibs import env
    env.exp = UIRequestTester()
    
    # Test basic functionality
    test_clicks = [click('left'), click('middle'), click('right', release=True)]
    assert ui.mouse_clicked(queue=test_clicks) == True
    assert ui.mouse_clicked('left', queue=test_clicks) == True
    assert ui.mouse_clicked('middle', queue=test_clicks) == True
    assert ui.mouse_clicked('right', queue=test_clicks) == False
    assert ui.mouse_clicked('left', released=True, queue=test_clicks) == False
    assert ui.mouse_clicked('right', released=True, queue=test_clicks) == True

    # Test with provided boundaries
    test_clicks2 = [click('left'), click('left', loc=(200, 200))]
    test_bounds = RectangleBoundary('test', (100, 100), (300, 300))
    test_bounds2 = RectangleBoundary('test', (300, 300), (500, 500))
    assert ui.mouse_clicked(within=test_bounds, queue=test_clicks2) == True
    assert ui.mouse_clicked('left', within=test_bounds, queue=test_clicks2) == True
    assert ui.mouse_clicked('left', within=test_bounds2, queue=test_clicks2) == False

    # Test without providing queue as argument
    queue_event(test_clicks[0])
    assert ui.mouse_clicked('left') == True
    assert ui.mouse_clicked('left') == False  # queue should be flushed after first call

    # Test intercepting of ui request commands
    quit_test = [click('left'), keydown('q', mod='ctrl')]
    ui.mouse_clicked('left', queue=quit_test)
    assert env.exp.command == 'quit'

    # Test edge cases
    assert ui.mouse_clicked(queue=[]) == False
    assert ui.mouse_clicked('left', queue=[]) == False
    assert ui.mouse_clicked('left', queue=[keyup('a')]) == False
    with pytest.raises(ValueError):
        ui.mouse_clicked('nope', queue=test_clicks)
    with pytest.raises(TypeError):
        ui.mouse_clicked(within=test_clicks, queue=test_clicks)


@pytest.mark.skip("not implemented")
def test_konami_code(with_sdl):
    pass


def test_get_clicks(with_sdl):

    # Initialize fake experiment class in environment
    from klibs import env
    env.exp = UIRequestTester()
    
    # Test basic functionality
    test_clicks = [
        click('left', loc=(10, 20)), click('left', loc=(30, 20)),
        click('middle', loc=(100, 100)), click('right', loc=(45, 432), release=True)
    ]
    assert ui.get_clicks(queue=test_clicks) == [(10, 20), (30, 20), (100, 100)]
    assert ui.get_clicks('left', queue=test_clicks) == [(10, 20), (30, 20)]
    assert ui.get_clicks('middle', queue=test_clicks) == [(100, 100)]
    assert ui.get_clicks('right', queue=test_clicks) == []
    assert ui.get_clicks('left', released=True, queue=test_clicks) == []
    assert ui.get_clicks('right', released=True, queue=test_clicks) == [(45, 432)]

    # Test without providing queue as argument
    queue_event(test_clicks[0])
    assert ui.get_clicks('left') == [(10, 20)]
    assert ui.get_clicks('left') == []  # queue should be flushed after first call

    # Test intercepting of ui request commands
    quit_test = [click('left'), keydown('q', mod='ctrl')]
    ui.get_clicks('left', queue=quit_test)
    assert env.exp.command == 'quit'

    # Test edge cases
    assert ui.get_clicks(queue=[]) == []
    assert ui.get_clicks('left', queue=[]) == []
    assert ui.get_clicks('left', queue=[keyup('a')]) == []
    with pytest.raises(ValueError):
        ui.get_clicks('nope', queue=test_clicks)


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

    
def test_smart_sleep(with_sdl):

    # Initialize fake experiment class in environment
    from klibs import env
    env.exp = UIRequestTester()

    # Queue a quit event and see if smart_sleep catches it
    queue_event(keydown('q', mod='ctrl'))
    start = time.time()
    ui.smart_sleep(1, units=TK_MS) # 1 millisecond
    duration = time.time() - start
    assert duration < 0.002
    assert env.exp.command == 'quit'

    # Test units of seconds
    env.exp.command = None
    start = time.time()
    ui.smart_sleep(0.001, units=TK_S) # 1 millisecond
    duration = time.time() - start
    assert duration < 0.002
    assert env.exp.command == None
