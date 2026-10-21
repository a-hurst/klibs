# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

from klibs import P
from klibs.KLInternal import package_available
from .KLEyeTracker import EyeTracker
from .KLTryLink import TryLink
from .events import EyeEvent, GazeSample

PYLINK_AVAILABLE = package_available('pylink')


def _get_eyetracker():
    """Returns an available eye tracker implementation.

    For internal use only.

    """
    if PYLINK_AVAILABLE and P.eye_tracker_available:
        if P.development_mode:
            print("* Pylink available, attempting to use EyeLink eye tracker...\n")
        from .KLEyeLink import EyeLink
        return EyeLink()
    else:
        if P.eye_tracker_available:
            print("* Warning: Pylink library not installed, falling back to TryLink\n")
        elif P.development_mode:
            print("* Using TryLink mouse simulation\n")
        return TryLink()
