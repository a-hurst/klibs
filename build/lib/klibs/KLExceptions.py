__author__ = 'jono'
class NullColumn(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg


class DatabaseException(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg
