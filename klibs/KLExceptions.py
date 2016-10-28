# -*- coding: utf-8 -*-
__author__ = 'jono'
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
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class GazeBoundaryError(Exception):
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class EyeLinkError(Exception):
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class BoundaryError(Exception):
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message

class EventError(Exception):
	def __init__(self, msg):
		self.message = msg

	def __str__(self):
		return self.message
