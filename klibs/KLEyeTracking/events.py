# -*- coding: utf-8 -*-
__author__ = 'Austin Hurst'

"""This module contains classes that are used for generating eye events (e.g. fixations, saccades)
from collections of gaze coordinates. Designed for internal use by the TryLink eye tracker
simulator, but could easily be adapted for any eye tracker that provides gaze coordinates.

"""

from math import atan2, degrees

from klibs.KLConstants import (
    EL_GAZE_POS, EL_SACCADE_START, EL_SACCADE_END,
    EL_FIXATION_START, EL_FIXATION_END, EL_FIXATION_UPDATE,
    EL_BLINK_START, EL_BLINK_END
)
from klibs.KLUtilities import mean


class GazeSample(object):
    """A simulated gaze sample event. For internal use.

    Args:
        time (int): The time that the sample was recorded.
        gaze (Tuple(float, float)): The (x, y) gaze coordinates of the sample.
    
    Attributes:
        type (int): The type code of the event (i.e. ``EL_GAZE_POS``).

    """
    def __init__(self, time, gaze):
        self.type = EL_GAZE_POS
        self.time = time
        self.gaze = gaze


class EyeEvent(object):
    """A simulated eye event (e.g saccade, fixation). For internal use.

    Args:
        etype (int): The type code of the eye event (e.g. ``EL_SACCADE_END``).
        template (:obj:`EyeEventTemplate`): An eye event template object to create the
            event from.
    
    Attributes:
        type (int): The type code of the eye event.
        start_time (int): The start timestamp of the eye event, based on the eye tracker's
            internal clock.
        start_gaze (Tuple(float, float)): The (x, y) coordinates of the first sample of the
            eye event.
        end_time (int): The end timestamp of the eye event, based on the eye tracker's
            internal clock. Not present on ``EL_SACCADE_START`` or ``EL_FIXATION_START`` events.
        end_gaze (Tuple(float, float)): The (x, y) coordinates of the last sample of the
            eye event. Not present on ``EL_SACCADE_START`` or ``EL_FIXATION_START`` events.
        avg_gaze (Tuple(float, float)): The (x, y) coordinates of the average gaze of 
            all samples in the eye event. Only present on ``EL_FIXATION_END`` and 
            ``EL_FIXATION_UPDATE`` events.

    """
    def __init__(self, etype, template):
        self.type = etype
        self.start_time = template.start_time
        self.start_gaze = template.start_gaze
        if self.type in [EL_SACCADE_END, EL_FIXATION_END, EL_FIXATION_UPDATE]:
            self.end_time = template.end_time
            self.end_gaze = template.end_gaze
            if self.type != EL_SACCADE_END:
                self.avg_gaze = template.avg_gaze


class EyeEventTemplate(object):
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
        super(EyeEventTemplate, self).__init__()
        self.__start = start_time
        self.__x_samples = [start_x]
        self.__y_samples = [start_y]
        self._last_sample_time = start_time
        self.last_update = start_time

    def _add_sample(self, x, y):
        self.__x_samples.append(x)
        self.__y_samples.append(y)

    def _vector_change(self, x, y):
        if len(self.__x_samples) < 2:
            return 0.0
        a1 = (self.__x_samples[0], self.__y_samples[0])
        a2 = (self.__x_samples[1], self.__y_samples[1])
        b1 = (self.__x_samples[-1], self.__y_samples[-1])
        b2 = (x, y)
        diff = atan2(b2[1]-b1[1], b2[0]-b1[0]) - atan2(a2[1]-a1[1], a2[0]-a1[0])
        return (degrees(diff) + 180) % 360 - 180

    @property
    def _dispersion(self):
        dx = max(self.__x_samples) - min(self.__x_samples)
        dy = max(self.__y_samples) - min(self.__y_samples)
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
        min_velocity (float): The minimum change in direction for an in-progress
            saccade. If velocity falls below this value, the saccade will end and
            a fixation will start.

    """
    def __init__(self, max_dispersion=None, min_velocity=None):
        if not max_dispersion:
            max_dispersion = 15
        if not min_velocity:
            min_velocity = 4
        self.max_dispersion = max_dispersion
        self.min_velocity = min_velocity
        self.__fix = None
        self.__sacc = None
        self._events = []
        
    def reset(self):
        """Reset the generator, clearing any in-progress events.

        """
        self.__fix = None
        self.__sacc = None
        self._events = []

    def get_events(self):
        """Returns all eye events generated since this method was last called.

        Returns:
            list: A list of all new eye events.

        """
        events = self._events
        self._events = []
        return events

    def update(self, x, y, timestamp):
        """Adds a new gaze sample to the generator.
        
        Args:
            x (float): The x coordinate (in pixels) of the gaze sample.
            y (float): The y coordinate (in pixels) of the gaze sample.
            timestamp (int): The timestamp (in milliseconds) of the gaze sample.

        """
        if self.__fix:
            # Add current sample to fixation template
            self.__fix._add_sample(x, y)
            self.__fix._last_sample_time = timestamp

            # If spatial dispersion of samples surpasses threshold, end fixation
            # and start saccade
            if self.__fix._dispersion > self.max_dispersion:
                self._events.append(EyeEvent(EL_FIXATION_END, self.__fix))
                self.__fix = None
                self.__sacc = EyeEventTemplate(timestamp, x, y)
                self._events.append(EyeEvent(EL_SACCADE_START, self.__sacc))

            else:
                # If dispersion is below threshold and fixation in progress, add
                # fixation update events at regular intervals
                if timestamp > (self.__fix.last_update + 50):
                    self._events.append(EyeEvent(EL_FIXATION_UPDATE, self.__fix))
                    self.__fix.last_update = timestamp

        elif self.__sacc:
            # If mouse movement falls below velocity threshold, end saccade
            # and start fixation
            # NOTE: Not actual velocity!
            dx = x - self.__sacc.end_gaze[0]
            dy = y - self.__sacc.end_gaze[1]
            if abs(dx) < self.min_velocity and abs(dy) < self.min_velocity:
                self._events.append(EyeEvent(EL_SACCADE_END, self.__sacc))
                self.__sacc = None
                self.__fix = EyeEventTemplate(timestamp, x, y)
                self._events.append(EyeEvent(EL_FIXATION_START, self.__fix))

            # If saccade vector changes by more than 45 degrees, end saccade
            # and start a new one
            elif abs(self.__sacc._vector_change(x, y)) > 45.0:
                self._events.append(EyeEvent(EL_SACCADE_END, self.__sacc))
                self.__sacc = EyeEventTemplate(timestamp, x, y)
                self._events.append(EyeEvent(EL_SACCADE_START, self.__sacc))

            else:
                self.__sacc._add_sample(x, y)
                self.__sacc._last_sample_time = timestamp

        else:
            # If neither a fixation or saccade is in progress, start a fixation
            self.__fix = EyeEventTemplate(timestamp, x, y)
            self._events.append(EyeEvent(EL_FIXATION_START, self.__fix))
