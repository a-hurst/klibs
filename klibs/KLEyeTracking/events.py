# -*- coding: utf-8 -*-
__author__ = 'Austin Hurst'

"""This module contains classes that are used for generating eye events (e.g. fixations, saccades)
from collections of gaze coordinates. Designed for internal use by the TryLink eye tracker
simulator, but could easily be adapted for any eye tracker that provides gaze coordinates.

"""

from math import atan2, degrees

from klibs.KLConstants import EL_GAZE_POS, EL_SACCADE_END, EL_FIXATION_END, EL_FIXATION_UPDATE
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
