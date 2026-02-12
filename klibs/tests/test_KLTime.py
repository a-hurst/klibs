import pytest
import mock

from klibs.KLTime import CountDown, Stopwatch


time_tmp = 1

def mock_time():
    return time_tmp

def add_time(secs):
    global time_tmp
    time_tmp += secs



class TestCountDown(object):

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_init(self, mock_time):
        # Test default creation
        tst = CountDown(1.0)
        assert tst.duration == 1.0
        assert tst.counting() == True

        # Test init without starting
        tst = CountDown(2.0, start=False)
        assert tst.duration == 2.0
        assert tst.counting() == False

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_start(self, mock_time):
        # Test starting a countdown that already exists
        tst = CountDown(1.0, start=False)
        assert tst.counting() == False
        tst.start()
        assert tst.counting() == True

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_counting(self, mock_time):
        # Test that counting ends when duration has elapsed
        tst = CountDown(1.0)
        assert tst.counting() == True
        add_time(1.1)
        assert tst.counting() == False

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_elapsed_remaining(self, mock_time):
        # Test basic checking of elapsed time
        tst = CountDown(1.0)
        add_time(0.4)
        assert pytest.approx(tst.elapsed()) == 0.4
        assert pytest.approx(tst.remaining()) == 0.6

        # Make sure elapsed stops when countdown finishes
        add_time(1.5)
        assert pytest.approx(tst.elapsed()) == 1.0
        assert pytest.approx(tst.remaining()) == 0.0

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_pause_resume(self, mock_time):
        # Test that pausing stops countdown
        tst = CountDown(1.0)
        add_time(0.5)
        assert pytest.approx(tst.elapsed()) == 0.5
        assert tst.counting() == True
        assert tst.paused == False
        tst.pause()
        add_time(1.0)
        assert pytest.approx(tst.elapsed()) == 0.5
        assert tst.counting() == False
        assert tst.paused == True

        # Test that resuming unpauses the countdown
        tst.resume()
        add_time(0.1)
        assert pytest.approx(tst.elapsed()) == 0.6
        assert tst.counting() == True
        assert tst.paused == False

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_add(self, mock_time):
        # Test adding/removing elapsed time from countdown
        tst = CountDown(3.0)
        add_time(0.5)
        assert pytest.approx(tst.elapsed()) == 0.5
        tst.add(0.2)
        assert pytest.approx(tst.elapsed()) == 0.7
        tst.add(-0.5)
        assert pytest.approx(tst.elapsed()) == 0.2

        # Test that adding time never goes beyond duration
        tst.add(10.0)
        assert pytest.approx(tst.elapsed()) == 3.0
        
        # Test that subtracting time never goes below zero
        tst.add(-5.0)
        assert pytest.approx(tst.elapsed()) == 0


class TestStopwatch(object):

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_init(self, mock_time):
        # Test default creation
        tst = Stopwatch()
        assert tst.started == True

        # Test init without starting
        tst = Stopwatch(start=False)
        assert tst.started == False

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_start(self, mock_time):
        # Test starting a countdown that already exists
        tst = Stopwatch(start=False)
        assert tst.started == False
        tst.start()
        assert tst.started == True

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_elapsed(self, mock_time):
        # Test basic checking of elapsed time
        tst = Stopwatch()
        add_time(0.4)
        assert pytest.approx(tst.elapsed()) == 0.4

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_pause_resume(self, mock_time):
        # Test that pausing stops the clock
        tst = Stopwatch()
        add_time(0.5)
        assert tst.paused == False
        assert pytest.approx(tst.elapsed()) == 0.5
        
        tst.pause()
        add_time(1.0)
        assert tst.paused == True
        assert pytest.approx(tst.elapsed()) == 0.5

        # Test that resuming unpauses the clock
        tst.resume()
        add_time(0.1)
        assert tst.paused == False
        assert pytest.approx(tst.elapsed()) == 0.6

    @mock.patch("klibs.KLTime.precise_time", wraps=mock_time)
    def test_add(self, mock_time):
        # Test adding time to & removing time from stopwatch
        tst = Stopwatch()
        add_time(0.5)
        assert pytest.approx(tst.elapsed()) == 0.5
        tst.add(0.1)
        assert pytest.approx(tst.elapsed()) == 0.6
        tst.add(-0.5)
        assert pytest.approx(tst.elapsed()) == 0.1
