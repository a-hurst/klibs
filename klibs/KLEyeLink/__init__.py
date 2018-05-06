# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import imp
from klibs import P
try:
	imp.find_module('pylink')
	PYLINK_AVAILABLE = True
except ImportError:
	print("\t* Warning: Pylink library not found; eye tracking will not be available.")
	PYLINK_AVAILABLE = False

if PYLINK_AVAILABLE and P.eye_tracker_available:
	from .KLEyeLinkExt import EyeLinkExt
	if P.development_mode:
		print("Using PyLink")
else:
	from .KLTryLink import TryLink as EyeLinkExt
	if P.development_mode:
		print("Using TryLink")