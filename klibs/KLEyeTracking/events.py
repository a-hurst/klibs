# -*- coding: utf-8 -*-
__author__ = 'Austin Hurst'

"""This module contains classes that are used for generating eye events (e.g. fixations, saccades)
from collections of gaze coordinates. Designed for internal use by the TryLink eye tracker
simulator, but could easily be adapted for any eye tracker that provides gaze coordinates.

"""

from math import atan2, degrees

from klibs.KLConstants import (
    GAZE_SAMPLE, BLINK_START, BLINK_END, SACCADE_START, SACCADE_END,
    FIXATION_START, FIXATION_END, FIXATION_UPDATE,
    LEFT_EYE, RIGHT_EYE, BINOCULAR
)
from klibs.KLUtilities import mean, line_segment_len


class GazeSample():
    """A simulated gaze sample event. For internal use.

    Args:
        time (int): The time that the sample was recorded.
        gaze (Tuple(float, float)): The (x, y) gaze coordinates of the sample.
    
    Attributes:
        type (int): The type code of the event (i.e. ``GAZE_SAMPLE``).

    """
    def __init__(self, time, gaze):
        self.type = GAZE_SAMPLE
        self.time = time
        self.gaze = gaze


class EyeEvent():
    """A simulated eye event (e.g saccade, fixation). For internal use.

    Args:
        etype (int): The type code of the eye event (e.g. ``SACCADE_END``).
        template (:obj:`EyeEventTemplate`): An eye event template object to create the
            event from.
    
    Attributes:
        type (int): The type code of the eye event.
        start_time (int): The start timestamp of the eye event, based on the eye tracker's
            internal clock.
        start_gaze (Tuple(float, float)): The (x, y) coordinates of the first sample of the
            eye event.
        end_time (int): The end timestamp of the eye event, based on the eye tracker's
            internal clock. Not present on ``SACCADE_START`` or ``FIXATION_START`` events.
        end_gaze (Tuple(float, float)): The (x, y) coordinates of the last sample of the
            eye event. Not present on ``SACCADE_START`` or ``FIXATION_START`` events.
        avg_gaze (Tuple(float, float)): The (x, y) coordinates of the average gaze of 
            all samples in the eye event. Only present on ``FIXATION_END`` and 
            ``FIXATION_UPDATE`` events.

    """
    def __init__(self, etype, template):
        self.type = etype
        self.start_time = template.start_time
        if self.type not in [BLINK_START, BLINK_END]:
            self.start_gaze = template.start_gaze
        if self.type in [SACCADE_END, FIXATION_END, FIXATION_UPDATE]:
            self.end_time = template.end_time
            self.end_gaze = template.end_gaze
            if self.type != SACCADE_END:
                self.avg_gaze = template.avg_gaze
        elif self.type == BLINK_END:
            self.end_time = template.end_time


class EyeEventTemplate():
    """A template for creating eye events (e.g saccades, fixations) from collections
    of samples. For internal use.

    Args:
        start_time (int): The start time of the eye event.
        start_x (int or float): The x coordinate of the first gaze sample of the event.
        start_y (int or float): The y coordinate of the first gaze sample of the event.
    
    Attributes:
        last_update (int): For fixation update events. Indicates the time that the last
            update event was issued.

    """
    def __init__(self, start_time, start_x, start_y):
        self.__start = start_time
        self.__x_samples = [start_x]
        self.__y_samples = [start_y]
        self._last_sample_time = start_time
        self.last_update = start_time

    def add_sample(self, x, y, timestamp):
        self.__x_samples.append(x)
        self.__y_samples.append(y)
        self._last_sample_time = timestamp

    def vector_change(self, x, y):
        if len(self.__x_samples) < 2:
            return 0.0
        a1 = (self.__x_samples[0], self.__y_samples[0])
        a2 = (self.__x_samples[1], self.__y_samples[1])
        b1 = (self.__x_samples[-1], self.__y_samples[-1])
        b2 = (x, y)
        diff = atan2(b2[1]-b1[1], b2[0]-b1[0]) - atan2(a2[1]-a1[1], a2[0]-a1[0])
        return (degrees(diff) + 180) % 360 - 180

    def get_velocity(self, x, y, timestamp):
        dist = line_segment_len(self.end_gaze, (x, y))
        return abs(dist / (timestamp - self._last_sample_time))
    
    def dispersion(self, x, y):
        dx = max(self.__x_samples + [x]) - min(self.__x_samples + [x])
        dy = max(self.__y_samples + [y]) - min(self.__y_samples + [y])
        return dx + dy

    @property
    def start_time(self):
        return self.__start
    
    @property
    def end_time(self):
        return self._last_sample_time

    @property
    def start_gaze(self):
        return (self.__x_samples[0], self.__y_samples[0])
    
    @property
    def end_gaze(self):
        return (self.__x_samples[-1], self.__y_samples[-1])

    @property
    def avg_gaze(self):
        return (mean(self.__x_samples), mean(self.__y_samples))


class EyeEventGenerator():
    """Internal class for generating eye events from gaze samples.

    Currently only used for TryLink, but could be adapted to any eye tracker that
    reports (x, y) screen coordinates.

    Args:
        max_dispersion (float): The maximum vertical or horizontal dispersion of
            samples to result in a saccade start/fixation end.
        min_velocity (float): The minimum velocity (in pixels per second) for an
            ongoing saccade. If velocity drops below this threshold the saccade will
            end and a new fixation will begin.

    """
    def __init__(self, max_dispersion=None, min_velocity=None):
        if not max_dispersion:
            max_dispersion = 15
        if not min_velocity:
            min_velocity = 240
        self.max_dispersion = max_dispersion
        self.min_velocity = min_velocity / 1000.0
        self.in_fixation = False
        self.in_saccade = False
        self.in_blink = False
        self._current = None
        self._events = []
        
    def reset(self):
        """Reset the generator, clearing any in-progress events.

        """
        self.in_fixation = False
        self.in_saccade = False
        self.in_blink = False
        self._current = None
        self._events = []

    def get_events(self):
        """Returns all eye events generated since this method was last called.

        Returns:
            list: A list of all new eye events.

        """
        events = self._events
        self._events = []
        return events

    def _start_saccade(self, new):
        # Start a new saccade, ending any current saccade or fixation
        if self.in_saccade:
            self._events.append(EyeEvent(SACCADE_END, self._current))
        elif self.in_fixation:
            self._events.append(EyeEvent(FIXATION_END, self._current))
        self._current = new
        self._events.append(EyeEvent(SACCADE_START, new))
        self.in_blink = False
        self.in_fixation = False
        self.in_saccade = True

    def _start_fixation(self, new):
        # Start a new fixation, ending any current saccade or blink
        if self.in_saccade:
            self._events.append(EyeEvent(SACCADE_END, self._current))
        elif self.in_blink:
            self._events.append(EyeEvent(BLINK_END, self._current))
        self._current = new
        self._events.append(EyeEvent(FIXATION_START, new))
        self.in_blink = False
        self.in_saccade = False
        self.in_fixation = True

    def _start_blink(self, new):
        # Start a new blink, ending any current saccade or fixation
        if self.in_saccade:
            self._events.append(EyeEvent(SACCADE_END, self._current))
        elif self.in_fixation:
            self._events.append(EyeEvent(FIXATION_END, self._current))
        self._current = new
        self._events.append(EyeEvent(BLINK_START, new))
        self.in_saccade = False
        self.in_fixation = False
        self.in_blink = True

    def update(self, x, y, timestamp):
        """Adds a new gaze sample to the generator.
        
        Args:
            x (float): The x coordinate (in pixels) of the gaze sample.
            y (float): The y coordinate (in pixels) of the gaze sample.
            timestamp (int): The timestamp (in milliseconds) of the gaze sample.

        """
        blink = (x is None or y is None)

        if self.in_blink:
            self._current.add_sample(x, y, timestamp)
            # If eye no longer missing, start a fixation event
            if not blink:
                fix = EyeEventTemplate(timestamp, x, y)
                self._start_fixation(fix)

        elif blink and not self.in_blink:
            # If eye missing and it wasn't before, start a blink event
            b = EyeEventTemplate(timestamp, x, y)
            self._start_blink(b)

        elif self.in_fixation:
            # If spatial dispersion of samples surpasses threshold, end fixation
            # and start saccade
            if self._current.dispersion(x, y) > self.max_dispersion:
                s = EyeEventTemplate(timestamp, x, y)
                self._start_saccade(s)

            else:
                # Add current sample to fixation template
                self._current.add_sample(x, y, timestamp)

                # If dispersion is below threshold and fixation in progress, add
                # fixation update events at regular intervals
                if timestamp > (self._current.last_update + 50):
                    self._events.append(EyeEvent(FIXATION_UPDATE, self._current))
                    self._current.last_update = timestamp

        elif self.in_saccade:
            # If mouse movement falls below velocity threshold, end saccade
            # and start fixation
            v = self._current.get_velocity(x, y, timestamp)
            if v < self.min_velocity:
                fix = EyeEventTemplate(timestamp, x, y)
                self._start_fixation(fix)

            # If saccade vector changes by more than 45 degrees, end saccade
            # and start a new one
            elif abs(self._current.vector_change(x, y)) > 45.0:
                s = EyeEventTemplate(timestamp, x, y)
                self._start_saccade(s)

            else:
                self._current.add_sample(x, y, timestamp)

        else:
            # If neither a fixation or saccade is in progress, start a fixation
            fix = EyeEventTemplate(timestamp, x, y)
            self._start_fixation(fix)
