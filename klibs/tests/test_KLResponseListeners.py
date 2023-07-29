import pytest

from klibs.KLResponseListeners import KeypressListener

from eventfactory import keydown


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
        assert listener.listen(test_keys).value == 'left'
        test_keys = [keydown('/'), keydown('b')]
        assert listener.listen(test_keys).value == 'right'
        # Test that non-response keys are ignored
        test_keys = [keydown('a'), keydown('b')]
        assert not listener.listen(test_keys)
        listener.cleanup()
