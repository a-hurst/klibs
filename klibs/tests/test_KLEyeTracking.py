import pytest

from klibs.KLConstants import *
from klibs.KLBoundary import RectangleBoundary
from klibs.KLEyeTracking.utils import GazeEventGenerator
from klibs.KLEyeTracking.KLTryLink import TryLink


class CustomTryLink(TryLink):

    def __init__(self):
        super(CustomTryLink, self).__init__()
        self.samples = []
        self._current_gaze = None

    def add_samples(self, samples):
        self.samples += samples

    def now(self):
        # NOTE: Need to do this in now because TryLink calls it first when
        # generating events
        if not len(self.samples):
            return 0
        x, y, timestamp = self.samples.pop(0)
        self._current_gaze = (x, y)
        return timestamp

    def gaze(self, return_integers=True, binocular_mode=RIGHT_EYE):
        return self._current_gaze



class TestGazeEventGenerator():

    def test_init(self):
        g = GazeEventGenerator()
        g = GazeEventGenerator(max_dispersion=10, min_velocity=200)

    def test_fixations(self):
        g = GazeEventGenerator(max_dispersion=10)

        # Should produce fixation start as soon as a sample is added
        g.update(400, 300, 5)
        events = g.get_events()
        assert len(events) == 1
        assert events[0].type == EL_FIXATION_START
        assert events[0].start_time == 5
        assert events[0].start_gaze == (400, 300)

        # Fixation update events should occur every 50 ms
        g.update(400, 300, 45)
        events = g.get_events()
        assert len(events) == 0
        g.update(402, 298, 60)
        events = g.get_events()
        assert len(events) == 1
        assert events[0].type == EL_FIXATION_UPDATE
        assert events[0].end_time == 60
        assert events[0].end_gaze == (402, 298)

        # Fixations should end when the dispersion criteria are met
        g.update(411, 300, 65)
        events = g.get_events()
        assert len(events) == 2
        assert events[0].type == EL_FIXATION_END
        assert events[0].start_time == 5
        assert events[0].end_time == 60
        assert events[0].end_gaze == (402, 298)
        assert events[1].type == EL_SACCADE_START
        assert events[1].start_time == 65

    def test_saccades(self):
        g = GazeEventGenerator(max_dispersion=10, min_velocity=240)

        # Test starting a saccade with a jump in movement
        g.update(400, 300, 5)
        g.update(420, 320, 20)
        events = g.get_events()
        assert len(events) == 3
        assert events[0].type == EL_FIXATION_START
        assert events[1].type == EL_FIXATION_END
        assert events[2].type == EL_SACCADE_START
        assert events[2].start_time == 20
        assert events[2].start_gaze == (420, 320)

        # Ensure saccade doesn't end until velocity drops below threshold
        g.update(430, 325, 35)
        assert not g.get_events()

        # Test that new saccade starts when angle of movement changes too much
        g.update(430, 300, 50)
        events = g.get_events()
        assert len(events) == 2
        assert events[0].type == EL_SACCADE_END
        assert events[0].start_gaze == (420, 320)
        assert events[0].end_gaze == (430, 325)
        assert events[0].end_time == 35
        assert events[1].type == EL_SACCADE_START
        assert events[1].start_gaze == (430, 300)
        assert events[1].start_time == 50

        # Fixations should end when the dispersion criteria are met
        g.update(400, 300, 65)
        g.update(403, 301, 80)
        events = g.get_events()
        assert len(events) == 2
        assert events[0].type == EL_SACCADE_END
        assert events[0].end_gaze == (400, 300)
        assert events[0].end_time == 65
        assert events[1].type == EL_FIXATION_START
        assert events[1].start_time == 80

    def test_blinks(self):
        g = GazeEventGenerator(max_dispersion=10, min_velocity=4)

        # Test starting a blink with null gaze coordinates
        g.update(400, 300, 5)
        g.update(None, None, 20)
        events = g.get_events()
        assert len(events) == 3
        assert events[0].type == EL_FIXATION_START
        assert events[1].type == EL_FIXATION_END
        assert events[2].type == EL_BLINK_START
        assert events[2].start_time == 20

        # Ensure blink continues as long as gaze is missing
        g.update(None, None, 35)
        assert not g.get_events()

        # Test that blink ends when gaze returns
        g.update(430, 300, 50)
        events = g.get_events()
        assert len(events) == 2
        assert events[0].type == EL_BLINK_END
        assert events[0].end_time == 50
        assert events[1].type == EL_FIXATION_START

        # Test that blink ends saccade events properly
        g.update(420, 320, 65)
        events = g.get_events()
        assert len(events) == 2
        assert events[0].type == EL_FIXATION_END
        assert events[1].type == EL_SACCADE_START
        g.update(None, None, 80)
        events = g.get_events()
        assert len(events) == 2
        assert events[0].type == EL_SACCADE_END
        assert events[1].type == EL_BLINK_START


class TestTryLink():

    def test_init(self):
        tst = TryLink()

    def test_get_event_queue(self):
        tst = CustomTryLink()
        # Start recording and check for gaze sample + start fixation
        tst.start(1)
        tst.add_samples([(400, 300, 0)])
        events = tst.get_event_queue()
        assert len(events) == 2
        sample, start_fix = (None, None)
        for e in events:
            if tst.get_event_type(e) == GAZE_SAMPLE:
                sample = e
            elif tst.get_event_type(e) == FIXATION_START:
                start_fix = e
        assert sample
        assert start_fix

    def test_within_boundary(self):
        bounds = RectangleBoundary('test', (500, 400), (600, 500))
        tst = CustomTryLink()
        tst.add_boundary(bounds)
        # Start recording and make sure boundary not counted as fixated
        tst.start(1)
        tst.add_samples([(400, 300, 0)])
        events = tst.get_event_queue()
        assert len(events) > 0
        assert not tst.within_boundary('test', GAZE_SAMPLE, event_queue=events)
        # Saccade to just outside boundary and re-test
        tst.add_samples([
            (401, 301, 10), (499, 400, 20)
        ])
        while len(tst.samples):
            # Needs to be called once per sample
            events = tst.get_event_queue() 
        assert not tst.within_boundary('test', GAZE_SAMPLE, event_queue=events)
        # Drift gaze inside boundary and re-test
        tst.add_samples([(501, 401, 30)])
        events = tst.get_event_queue()
        assert tst.within_boundary('test', GAZE_SAMPLE, event_queue=events)

    def test_fixated_boundary(self):
        bounds = RectangleBoundary('test', (500, 400), (600, 500))
        tst = CustomTryLink()
        tst.add_boundary(bounds)
        # Start recording and make sure boundary not counted as fixated
        tst.start(1)
        tst.add_samples([(400, 300, 0)])
        events = tst.get_event_queue(include=[FIXATION_START])
        assert len(events) == 1
        assert not tst.fixated_boundary('test', event_queue=events)
        # Saccade to boundary and re-test
        tst.add_samples([
            (401, 301, 10), (550, 440, 20), (551, 439, 30)
        ])
        while len(tst.samples):
            # Needs to be called once per sample
            events = tst.get_event_queue() 
        assert tst.fixated_boundary('test', event_queue=events)

    def test_saccade_to_boundary(self):
        bounds = RectangleBoundary('test', (500, 400), (600, 500))
        tst = CustomTryLink()
        tst.add_boundary(bounds)
        # Start recording and make sure no saccade detected
        tst.start(1)
        tst.add_samples([(400, 300, 0)])
        events = tst.get_event_queue()
        assert len(events) > 0
        assert not tst.saccade_to_boundary('test', event_queue=events)
        # Saccade from boundary and re-test
        tst.add_samples([
            (401, 301, 10), (420, 320, 20), (550, 440, 30), (551, 439, 40)
        ])
        while len(tst.samples):
            # Needs to be called once per sample
            events = tst.get_event_queue() 
        assert tst.saccade_to_boundary('test', event_queue=events)

    def test_saccade_from_boundary(self):
        bounds = RectangleBoundary('fixation', (380, 280), (420, 320))
        tst = CustomTryLink()
        tst.add_boundary(bounds)
        # Start recording and make sure no saccade detected
        tst.start(1)
        tst.add_samples([(400, 300, 0)])
        events = tst.get_event_queue()
        assert len(events) > 0
        assert not tst.saccade_from_boundary('fixation', event_queue=events)
        # Saccade from boundary and re-test
        tst.add_samples([
            (401, 301, 10), (420, 320, 20), (550, 440, 30), (551, 439, 40)
        ])
        while len(tst.samples):
            # Needs to be called once per sample
            events = tst.get_event_queue() 
        assert tst.saccade_from_boundary('fixation', event_queue=events)

