# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

from klibs.KLConstants import TK_S, TK_MS
from klibs import P
from klibs.KLNamedObject import NamedObject
from klibs.KLTime import precise_time as time
from klibs.KLUserInterface import ui_request


class TrialEventTicket(NamedObject):
	"""A ticket defining the name and onset time of an event that occurs within a trial. For use
	with the :obj:`EventManager` class.

	Args:
		label (:obj:`str`): The identfying name of the trial event (e.g. 'cue on').
		onset (int or float): The onset time of the event, relative to the start of the trial.
		unit (optional): The time unit for the onset. Can be either ``TK_S`` (seconds) or ``TK_MS``
			(milliseconds). Defaults to milliseconds.

	"""
	def __init__(self, label, onset, unit=TK_MS):
		NamedObject.__init__(self, label)

		if type(label) is not str:
			raise TypeError("Property 'label' must be a string.")

		if unit not in [TK_S, TK_MS]:
			raise TypeError("Property 'unit' must be a valid time constant.")

		if type(onset) not in [int, float] or onset < 0:
			err = "Event onset must be a number greater than zero (got {0})."
			raise TypeError(err.format(onset))
		
		self.__label = label
		self.__unit = unit
		self.__onset = onset * 1000.0 if unit == TK_S else float(onset)
		self.issued = False

	def __str__(self):
		return "klibs.TrialEventTicket(label='{0}', onset={1})".format(self.label, self.onset)

	@property
	def label(self):
		""":obj:`str`: The name of the event.

		"""
		return self.__label

	@property
	def onset(self):
		"""float: The onset (in milliseconds) of the event relative to the start of the trial.

		"""
		return self.__onset


class EventManager(object):
	"""A class for sequencing the events that will occur during a given trial, relative to the
	trial onset.

	.. note:: An EventManager object is provided globally in the KLibs runtime environment as the
	  experiment attribute ``self.evm``. This should be used instead of creating your own instance.

	The EventManager object works in two stages:
	
	First, before the start of a trial, the names and onset times of the events that should occur
	within the trial are registered with the EventManager using the :meth:`register_ticket` or
	:meth:`register_tickets` methods, e.g.::

			# Note: events[-1][1] means the onset time of the previous event in the list
			events = []
			events.append(['cue_on', 1000])
			events.append(['cue_off', events[-1][1] + 100])
			events.append(['target_on', events[-1][1] + 400])
			self.evm.register_tickets(events)

	Then, in the body of the experiment's :meth:`~.KLExperiment.trial` method, the EventManager can
	then be used to watch for those events and change behaviour when they occur::

		while self.evm.before('target_on', pump_events=True):
			fill()
			draw_stimuli()
			if self.evm.between('cue_on', 'cue_off'):
				draw_cue()
			flip()

	This is done to make it easy to group all trial event sequencing information in one place in
	your code, as well as make for simple and human-readable code within the trial body.

	"""
	def __init__(self):
		super(EventManager, self).__init__()
		self.events = {}
		self.start_time = None


	def _ensure_exists(self, label):
		# Makes sure a given event exists in the manager, raising an exception
		# if it doesn't
		try:
			self.events[label]
		except KeyError:
			err = "'{0}' does not match the name of any existing event."
			raise ValueError(err)


	def __event_issued(self, label):
		if self.events[label].issued == True:
			return True
		elif self.events[label].onset < self.trial_time_ms:
			self.events[label].issued = True
			return True
		else:
			return False

	
	def register_ticket(self, event):
		"""Registers an event with the EventManager for the upcoming trial.

		If defining an event with a :obj:`List`, it must be in the format ``[label, onset]``, 
		with 'label' being the name of the event and 'onset' being the time (in millseconds)
		after trial start that the event occurs, such as::

			self.evm.register_ticket(['target_on', 1000]) # 1000ms after trial start

		Args:
			event (:obj:`TrialEventTicket` or :obj:`List`): An event or List defining an
				event to be registered with the EventManager.

		"""
		if not isinstance(event, TrialEventTicket):
			try:
				event = TrialEventTicket(*event)
			except SyntaxError:
				raise TypeError("Argument 'event' must be a List or a TrialEventTicket.")
		self.events[event.label] = event


	def register_tickets(self, events):
		"""Registers multiple events with the EventManager for the upcoming trial.

		See also: :meth:`register_ticket`

		Args:
			events (:obj:`List`): A List of :obj:`TrialEventTicket` or :obj:`List` objects
				defining events to be registered with the EventManager. 

		"""
		for e in events:
			self.register_ticket(e)


	def before(self, label, pump_events=False):
		"""Checks if the current trial time is before a given event.

		.. warning:: Setting 'pump_events' to True will cause the input event queue to be cleared 
		  every time the method is called. Please use :func:`~.pump` manually in loops where you
		  will be processing user input.

		Args:
			label (str): The label of the event to check.
			pump_events (bool, optional): If True, a :func:`~.ui_request` is performed when this
				method is called. Defaults to False.

		Returns:
			True if the specified event has not yet occured within the trial, otherwise False.

		"""
		self._ensure_exists(label)
		if pump_events:
			ui_request()

		return not self.__event_issued(label)


	def after(self, label, pump_events=False):
		"""Checks if the current trial time is after a given event.

		.. warning:: Setting 'pump_events' to True will cause the input event queue to be cleared 
		  every time the method is called. Please use :func:`~.pump` manually in loops where you
		  will be processing user input.

		Args:
			label (str): The label of the event to check.
			pump_events (bool, optional): If True, a :func:`~.ui_request` is performed when this
				method is called. Defaults to False.

		Returns:
			True if the specified event has already occured within the trial, otherwise False.

		"""
		self._ensure_exists(label)
		if pump_events:
			ui_request()

		return self.__event_issued(label)


	def between(self, label_1, label_2):
		"""Checks if the current trial time is between two given events.

		Args:
			label_1 (str): The label of the event to check if it is currently after.
			label_2 (str): The label of the event to check if it is currently before.
		
		Returns:
			True if the current trial time is between the specified events, otherwise False.

		"""
		return self.after(label_1) and self.before(label_2)


	def start_clock(self):
		"""Starts the EventManager's trial clock. The onsets of all events registered with the
		EventManager are relative to the point in time when this method is called.

		.. note:: This method is called automatically at the start of every trial. The only time
		  you would ever need to call it manually is if you wanted to use the EventManager outside
		  of an experiment's :meth:`~.KLExperiment.trial()` method.

		Raises:
			RuntimeError: If this method is called while the trial clock is already running.

		"""
		if self.start_time != None:
			err = "The EventManger trial clock cannot be started if it is already running."
			raise RuntimeError(err)
		self.start_time = time()


	def stop_clock(self):
		"""Stops the EventManager's trial clock and clears all registered events.

		.. note:: This method is called automatically at the end of every trial. The only time
		  you would ever need to call it manually is if you wanted to use the EventManager outside
		  of an experiment's :meth:`~.KLExperiment.trial()` method.

		"""
		self.events = {}
		self.start_time = None

	@property
	def trial_time(self):
		"""float: Time in seconds since the start of the current trial. If called when the
		EventManager clock is not running (e.g. outside of a trial), this will be equal to 0.
		
		"""
		return 0.0 if self.start_time == None else (time() - self.start_time)

	@property
	def trial_time_ms(self):
		"""float: Time in milliseconds since the start of the current trial. If called when the
		EventManager clock is not running (e.g. outside of a trial), this will be equal to 0.
		
		"""
		return self.trial_time * 1000
