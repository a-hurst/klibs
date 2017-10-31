# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

from klibs import PYLINK_AVAILABLE
from klibs import P

if PYLINK_AVAILABLE and P.eye_tracker_available:
	from KLEyeLinkExt import EyeLinkExt
	from KLCustomEyeLinkDisplay import ELCustomDisplay
	if P.development_mode:
		print "Using PyLink"
else:
	from KLTryLink import TryLink as EyeLinkExt
	if P.development_mode:
		print "Using TryLink"