import pytest
import mock

from klibs.KLEventInterface import EventManager, TrialEventTicket


time_tmp = 1

def mock_time():
    return time_tmp

def add_time(secs):
    global time_tmp
    time_tmp += secs


@pytest.fixture
def evm():
    events = EventManager()
    events.add_event('cue_on', 1000)
    events.add_event('cue_off', 1100)
    events.add_event('target_on', 1500)
    return events



class TestEventManager(object):

    def test_add_event(self):
        evm = EventManager()
        evm.add_event('cue_on', 1000)
        evm.add_event('cue_off', 100, after='cue_on')
        evm.add_event('target_on', 1500)
        evm.add_event('target_off', 200, after='target_on')
        # Ensure all events were added correctly
        assert evm.events['cue_on'] == 1000
        assert evm.events['cue_off'] == 1100
        assert evm.events['target_on'] == 1500
        assert evm.events['target_off'] == 1700
        # Test exception on bad relative event name
        with pytest.raises(ValueError):
            evm.add_event('sound_off', 100, after='sound_on')

    def test_register_ticket(self):
        evm = EventManager()
        # Add ticket as list
        evm.register_ticket(['cue_on', 1000])
        # Add ticket as TrialEventTicket
        evm.register_ticket(TrialEventTicket('cue_off', 1100))
        # Add multiple tickets at once
        evm.register_tickets([
            ['target_on', 1500], ['target_off', 1700]
        ])
        # Ensure all events were added correctly
        assert evm.events['cue_on'] == 1000
        assert evm.events['cue_off'] == 1100
        assert evm.events['target_on'] == 1500
        assert evm.events['target_off'] == 1700

    def test_start_stop(self, evm):
        evm.start_clock()
        with pytest.raises(RuntimeError):
            evm.start_clock()
        evm.stop_clock()
        evm.start_clock()
        evm.stop_clock()

    def test_trial_time(self, evm):
        with mock.patch("klibs.KLEventInterface.time", wraps=mock_time):
            evm.start_clock()
            add_time(1.5)
            assert evm.trial_time == 1.5
            assert evm.trial_time_ms == 1500
            add_time(0.5)
            assert evm.trial_time == 2.0
            assert evm.trial_time_ms == 2000
            evm.stop_clock()

    def test_before_after(self, evm):
        # Test sequencing of trial events
        with mock.patch("klibs.KLEventInterface.time", wraps=mock_time):
            evm.start_clock()
            assert evm.before('cue_on')
            assert not evm.after('cue_on')
            # Move forward by 1050 ms
            add_time(1.05)
            assert evm.after('cue_on')
            assert evm.before('cue_off')
            # Move forward another 200 ms
            add_time(0.2)
            assert evm.between('cue_off', 'target_on')
            # Move forward 1000 ms
            add_time(1.0)
            assert evm.after('target_on')
        # Test exceptions on bad input
        with pytest.raises(ValueError):
            assert evm.before('not_an_event')
        with pytest.raises(ValueError):
            assert evm.after('not_an_event')
        evm.stop_clock()
