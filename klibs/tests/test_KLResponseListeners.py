import pytest

from klibs.KLResponseListeners import KeypressListener, MouseButtonListener

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
