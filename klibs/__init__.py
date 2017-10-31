# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

print "\n\n\033[92m*** Now loading KLIBS Environment ***\033[0m"
print "\033[32m(Note: if a bunch of SDL errors were just reported, this was expected, do not be alarmed!)\033[0m"
import logging
import warnings

import KLNamedObject
import KLEnvironment as env
import KLExceptions
import KLConstants
from KLConstants import PYAUDIO_AVAILABLE, PYLINK_AVAILABLE, SLACK_STATUS
import KLParams as P						# KLConstants
import KLKeyMap								# KLConstants
import KLLabJack							# KLParams
import KLUtilities							# KLConstants, KLParams
import KLIndependentVariable				# KLUtilities, KLNamedObject
import KLJSON_Object						# KLUtilities
import KLTrialFactory						# KLConstants, KLParams
import KLUserInterface						# KLConstants, KLParams, KLUtilities
import KLDatabase							# KLConstants, KLParams, KLUtilities
import KLTime								# KLConstants, KLParams, KLUtilities

import KLEventInterface						# KLConstants, KLParams, KLUtilities, KLUserInterface
import KLGraphics							# KLConstants, KLParams, KLUtilities
import KLDebug								# KLParams, KLGraphics
import KLBoundary							# KLConstants, KLUtilities, KLExceptions
import KLText								# KLUtilities, KLGraphics
import KLAudio								# KLConstants, KLParams, KLUtilities, KLGraphics
import KLResponseCollectors					# KLConstants, KLParams, KLUtilities, KLUserInterface, KLBoundary, KLAudio
import KLEyeLink
import KLCommunication
import KLEnvironment

try:
	# if additional classes have been defined at ExpAssets/Resources/code, load them
	import sys
	import os
	from imp import load_source
	from inspect import isclass
	sys.path.append(P.code_dir)
	for f in os.listdir(P.code_dir):
		if f[-3:] != ".py":
			if f[-3:] == ".pyc":
				os.remove( os.path.join(P.code_dir, f) )
			continue
		for k, v in load_source("*", os.path.join(P.code_dir, f)).__dict__.iteritems():
			if isclass(k):
				import k
except OSError:
	pass

from klibs.KLExperiment import Experiment
