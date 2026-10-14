import pytest

from klibs.KLConstants import *
from klibs.KLEyeTracking.events import EyeEventGenerator


class TestEyeEventGenerator():

    def test_init(self):
        g = EyeEventGenerator()
        g = EyeEventGenerator(max_dispersion=10, min_velocity=4)

    def test_fixations(self):
        g = EyeEventGenerator(max_dispersion=10)

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
        assert events[0].end_time == 65
        assert events[0].end_gaze == (411, 300)
        assert events[1].type == EL_SACCADE_START
        assert events[1].start_time == 65

    def test_saccades(self):
        g = EyeEventGenerator(max_dispersion=10, min_velocity=4)

        # Should produce fixation start as soon as a sample is added
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
        g.update(403, 302, 80)
        events = g.get_events()
        assert len(events) == 2
        assert events[0].type == EL_SACCADE_END
        assert events[0].end_gaze == (400, 300)
        assert events[0].end_time == 65
        assert events[1].type == EL_FIXATION_START
        assert events[1].start_time == 80
