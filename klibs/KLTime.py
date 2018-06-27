# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

from time import time


class CountDown(object):

	"""A timer that counts down to 0 for a given duration. Can be paused, reset, extended,
	and checked for time remaining or elapsed, making it flexible and useful for many different
	situations.

	Args:
		duration(float): The duration in seconds that the timer should count down for.
		start(bool, optional): Whether to start the countdown immediately upon creation. Defaults
			to True.

	Attributes:
		duration(float): The duration that the timer is set to count down for.
		started(bool): Whether the countdown timer has been started yet.
		paused(bool): The current pause state of the countdown timer.
	
	Raises:
		ValueError: if the duration specified is not a positive real number.

	"""
	__started = 0
	__pause_time = 0.0
	__flex = 0.0 # for add() and finish() 
	__paused = False
	__duration = 0

	def __init__(self, duration, start=True):
		super(CountDown, self).__init__()
		self.duration = duration
		self.reset(start)

	def start(self):
		"""Starts the countdown if it has not started already.

		Raises:
			RuntimeError: If called after the countdown has already been started.

		"""
		if not self.started:
			self.__started = time()
			self.__paused = False
		else:
			err = "Cannot start CountDown that's already started (use reset method instead)."
			raise RuntimeError(err)

	def counting(self):
		"""Indicates whether the timer is currently counting down or not.

		Returns:
			bool: False if the countdown is paused or has finished, otherwise True.

		"""
		if self.paused:
			return False
		else:
			return self.remaining() != 0

	def reset(self, start=True):
		"""Resets the countdown so it starts back at the original duration.
		
		Args:
			start(bool, optional): If True, the countdown will immediately start again after
				resetting. If False, the countdown will be reset into a paused state. Defaults
				to True.
				
		"""
		self.__started = 0
		self.__pause_time = 0.0
		self.__flex = 0.0
		if start:
			self.start()
		else:
			self.pause()

	def finish(self):
		"""Ends the countdown by jumping the time remaining directly to zero.

		"""
		self.__flex += self.remaining()

	def add(self, delta):
		"""Add an amount of time to (or subtract an amount from) the elapsed time of the countdown.
		Note that a CountDown's time elapsed is clipped such that it can be no less than zero and 
		no larger than the timer's set duration: for example, 'self.add(-100)' when 5 seconds has
		elapsed in the CountDown will only reduce the elapsed time to 0, and 'self.add(100)' when
		the CountDown's duration is 8 seconds will only increase the elapsed time to 8. 
		
		Args:
			delta(float): The number of seconds to add to the countdown timer. Can be a positive
				or negative number.

		"""
		if (self.elapsed() + delta) < 0:
			# ensure subtraction will never result in negative duration
			delta = 0 - self.elapsed()
		elif delta >= self.remaining():
			# end timer if duration added is greater than time remaining
			delta = self.remaining()
		self.__flex += delta

	def pause(self):
		"""Pauses the countdown if it is not already paused. The countdown can later be resumed
		with the resume() method. Does nothing if the timer is already paused.

		"""
		if not self.paused:
			self.__paused = time()

	def resume(self):
		"""Unpauses the countdown if it is currently paused. Does nothing if it is not paused.

		"""
		if self.paused:
			self.__pause_time += time() - self.__paused
			self.__paused = False

	def remaining(self):
		"""Returns the amount of time remaining in the countdown (in seconds). Will return 0 if the
		countdown has ended.

		"""
		return self.duration - self.elapsed()

	def elapsed(self):
		"""Returns the amount of time elapsed in the countdown (in seconds). If the countdown has
		finished, the value returned will be equal to the countdown duration (e.g. 2.5 for a
		finished countdown with a duration of 2.5 seconds)

		"""
		if not self.started:
			t = self.__flex
		elif self.paused:
			t = (self.__paused + self.__flex) - (self.__started + self.__pause_time)
		else:
			t = (time() + self.__flex) - (self.__started + self.__pause_time)
		return t if t < self.duration else self.duration

	@property
	def started(self):
		return self.__started is not 0

	@property
	def paused(self):
		return self.__paused is not False
	
	@property
	def duration(self):
		return self.__duration
	
	@duration.setter
	def duration(self, value):
		try:
			self.__duration = float(value)
		except ValueError:
			raise ValueError("Duration must be a positive real number.")
		if value <= 0:
			err = ("Authorization Denied: negative and null duration privileges restricted to "
				"user dr_who.")
			raise ValueError(err)
		


class Stopwatch(object):

	"""A timer that counts upwards and can be paused, resumed, and reset, just like a stopwatch.

	Args:
		start(bool, optional): Whether to start the stopwatch immediately upon creation. Defaults
			to True.

	Attributes:
		started(bool): Whether the stopwatch timer has been started yet.
		paused(bool): The current pause state of the stopwatch timer.
	
	"""
	__started = 0
	__pause_time = 0.0
	__flex = 0.0 # for add()
	__paused = False

	def __init__(self, start=True):
		super(Stopwatch, self).__init__()
		if start: self.start()

	def start(self):
		"""Starts the stopwatch if it has not started already.

		Raises:
			RuntimeError: If called after the stopwatch has already been started.

		"""
		if self.__started == 0:
			self.__started = time()
			self.__paused = False
		else:
			err = "Cannot start Stopwatch that's already started (use reset method instead)."
			raise RuntimeError(err)

	def reset(self, start=True):
		"""Resets the stopwatch so it starts back at zero.
		
		Args:
			start(bool, optional): If True, the stopwatch will immediately start again after
				resetting. If False, the stopwatch will be reset into a paused state. Defaults
				to True.

		"""
		self.__started = 0
		self.__pause_time = 0.0
		self.__flex = 0.0
		if start:
			self.start()
		else:
			self.pause()

	def add(self, duration):
		"""Add an amount of time to (or subtract an amount from) the stopwatch timer.
		
		Args:
			duration(float): The number of seconds to add to the stopwatch timer. Can be a positive
				or negative number.

		"""
		self.__flex += duration

	def pause(self):
		"""Pauses the stopwatch if it is not already paused. The stopwatch can later be resumed
		with the resume() method. Does nothing if the timer is already paused.

		"""
		if not self.paused:
			self.__paused = time()

	def resume(self):
		"""Unpauses the stopwatch if it is currently paused. Does nothing if the timer is not
		paused.

		"""
		if self.paused:
			self.__pause_time += time() - self.__paused
			self.__paused = False

	def elapsed(self):
		"""Returns the amount of time elapsed on the stopwatch (in seconds).

		"""
		if self.__started == 0:
			return self.__flex
		elif self.paused:
			return (self.__paused + self.__flex) - (self.__started + self.__pause_time)
		else:
			return (time() + self.__flex) - (self.__started + self.__pause_time)			

	@property
	def started(self):
		return self.__started is not 0

	@property
	def paused(self):
		return self.__paused is not False 
