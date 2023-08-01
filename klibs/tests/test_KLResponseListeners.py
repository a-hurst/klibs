import pytest

from klibs.KLGraphics import KLDraw as kld
from klibs.KLResponseListeners import (
    KeypressListener, MouseButtonListener, ColorWheelListener,
)

from eventfactory import keydown, click


class TestKeypressListener(object):

    def test_init(self):
        listener = KeypressListener({'space': 'detection'})
        with pytest.raises(TypeError):
            tst = KeypressListener(['space'])
        with pytest.raises(ValueError):
            tst = KeypressListener({})
        with pytest.raises(ValueError):
            tst = KeypressListener({'not_a_key': 'value'})

    def test_listen(self):
        listener = KeypressListener({
            'z': 'left',
            '/': 'right',
        })
        listener.init()
        # Test detection of response keys
        test_keys = [keydown('a'), keydown('z')]
        assert listener.listen(test_keys)[0] == 'left'
        test_keys = [keydown('/'), keydown('b')]
        assert listener.listen(test_keys)[0] == 'right'
        # Test that non-response keys are ignored
        test_keys = [keydown('a'), keydown('b')]
        assert not listener.listen(test_keys)
        listener.cleanup()


class TestMouseButtonListener(object):

    def test_init(self):
        listener = MouseButtonListener({'left': 'detection'})
        with pytest.raises(TypeError):
            tst = MouseButtonListener(['left'])
        with pytest.raises(ValueError):
            tst = MouseButtonListener({})
        with pytest.raises(ValueError):
            tst = MouseButtonListener({'not_a_button': 'value'})

    def test_listen(self):
        listener = MouseButtonListener({
            'left': 'same',
            'right': 'different',
        })
        listener.init()
        # Test detection of response clicks
        test_clicks = [keydown('a'), click('middle'), click('left')]
        assert listener.listen(test_clicks)[0] == 'same'
        test_clicks = [click('middle'), click('right')]
        assert listener.listen(test_clicks)[0] == 'different'
        # Test that non-response buttons are ignored
        test_clicks = [keydown('a'), click('middle')]
        assert not listener.listen(test_clicks)
        listener.cleanup()
        # Test that all buttons registered when set to 'any'
        listener = MouseButtonListener({'any': 'detection'})
        listener.init()
        assert listener.listen([click('left')])[0] == 'detection'
        assert listener.listen([click('right')])[0] == 'detection'
        assert listener.listen([click('middle')])[0] == 'detection'
        listener.cleanup()


class TestColorWheelListener(object):

    def test_init(self):
        # Test normal init
        wheel = kld.ColorWheel(600)
        listener = ColorWheelListener(wheel)
        # Test specifying custom center
        listener_c = ColorWheelListener(wheel, center=(300, 300))
        # Test error when wheel isn't a color wheel
        with pytest.raises(TypeError):
            wheel = kld.Annulus(600, thickness=100)
            tst = ColorWheelListener(wheel)

    def test_set_target(self):
        wheel = kld.ColorWheel(600)
        listener = ColorWheelListener(wheel)
        target = wheel.color_from_angle(90)
        listener.set_target(target)
        # Test error when colour not in wheel
        with pytest.raises(ValueError):
            listener.set_target((0, 0, 0))

    def test_listen(self):
        wheel = kld.ColorWheel(600, thickness=100)
        listener = ColorWheelListener(wheel, center=(300, 300))
        # Test error when trying to init before target color set
        with pytest.raises(RuntimeError):
            listener.init()
        # Set a target color for the listener and init
        target = wheel.color_from_angle(180)
        listener.set_target(target)
        listener.init()
        # Test detection of response clicks
        test_clicks = [keydown('a'), click(loc=(300, 550), release=True)]
        angle_err, resp_color, rt = listener.listen(test_clicks)
        assert resp_color == target[:3]
        assert angle_err == 0
        test_clicks = [click(loc=(50, 300), release=True)]
        angle_err, resp_color, rt = listener.listen(test_clicks)
        assert angle_err == -90
        # Test that non-responses are ignored
        test_clicks = [
            click(loc=(300, 550), release=False), # Should ignore mouse down events
            click(loc=(300, 300), release=True), # Should ignore off-wheel clicks
        ]
        assert not listener.listen(test_clicks)
        listener.cleanup()
