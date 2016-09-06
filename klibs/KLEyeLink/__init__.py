# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

from klibs import PYLINK_AVAILABLE

if PYLINK_AVAILABLE:
	from pylink import EyeLink, openGraphicsEx, flushGetkeyQueue, beginRealTimeMode, EyeLinkCustomDisplay, KeyInput, \
		DC_TARG_BEEP, CAL_TARG_BEEP, CAL_ERR_BEEP, DC_ERR_BEEP, ENTER_KEY, ESC_KEY
	from pylink.tracker import Sample, EndSaccadeEvent, EndFixationEvent, StartFixationEvent, StartSaccadeEvent
	from KLEyeLinkExt import EyeLinkExt
	from KLCustomEyeLinkDisplay import ELCustomDisplay
else:
	from KLTryLink import TryLink as EyeLinkExt