# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

class NullColumn(Exception):
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class DatabaseException(Exception):
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class TrialException(Exception):
	"""If raised within the body of a :meth:`~klibs.KLExperiment.Experiment.trial`, the trial
	will end immediately without recording data and the trial factors for that trial will be
	re-shuffled into the remaining trials in the block.

	"""
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class EyeTrackerError(Exception):
	"""Raised when a problem relating to an :obj:`~klibs.KLEyeTracking.KLEyeTracker.EyeTracker`
	object or the misuse of eye event inspect/report types is encountered.

	"""
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class BoundaryError(Exception):
	"""Raised when a problem relating to the use of :obj:`~klibs.KLBoundary.Boundary` objects
	within a :obj:`~klibs.KLBoundary.BoundaryInspector` is encountered.

	"""
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class EventError(Exception):
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message
