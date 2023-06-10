# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

from klibs.KLConstants import TK_S, TK_MS
from klibs.KLNamedObject import NamedObject
from klibs.KLTime import precise_time as time
from klibs.KLUserInterface import ui_request


class TrialEventTicket(NamedObject):
    """A ticket defining the name and onset time of an event that occurs within a trial. For use
    with the :obj:`EventManager` class.

    Deprecated, do not use.

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
    """A class for defining and controlling the sequence of events in a trial.

    During a given trial of a task, there are usually `things that happen`: for
    example, a cue might appear on-screen after 1000 ms and disappear 100 ms later,
    or a target might appear after a random delay between 1500 and 3000 ms. The
    ``EventManager`` class exists to make sequencing those sorts of events within
    a trial simple and easy.
    
    First, before the trial begins, we add the names and onsets of the trial's
    events to the ``EventManager`` using the :meth:`add_event` method, e.g.::
            
            evm = EventManager()
            evm.add_event('cue_on', 1000)
            evm.add_event('cue_off', 100, after='cue_on')
            evm.add_event('target_on', 400, after='cue_off')

    Then, during the trial itself, we can use the :meth:`before`, :meth:`after`,
    and :meth:`between` methods to make decisions based on whether those events
    have occurred::

        while evm.before('target_on'):
            ui_request()
            fill()
            draw_stimuli()
            if evm.between('cue_on', 'cue_off'):
                draw_cue()
            flip()

    The klibs Experiment class provides an ``EventManager`` instance as ``self.evm``,
    so you generally won't need to create one yourself. Its trial clock is started
    automatically when ``self.trial()`` is called on each trial, and is reset
    after every trial ends.

    """
    def __init__(self):
        super(EventManager, self).__init__()
        self.events = {}
        self._issued = {}
        self.start_time = None


    def _ensure_exists(self, label):
        # Makes sure a given event exists in the manager, raising an exception
        # if it doesn't
        try:
            self.events[label]
        except KeyError:
            err = "'{0}' does not match the name of any existing event."
            raise ValueError(err.format(label))


    def add_event(self, label, onset, after=None):
        """Adds an event to the event manager.
        
        By default, the onsets of events are relative to the start of the trial
        (e.g. a 'cue_on' event with an onset of 1000 will occur 1000 ms after the
        trial begins). However, you can also define an event's onset as being
        relative to another event's onset using the optional 'after' argument
        (e.g. a 'cue_off' event occuring 100 ms after the 'cue_on' event).
        
        Args:
            label (str): The name of the event to add (e.g. 'cue_on').
            onset (int): The onset of the event (in milliseconds), relative to
                the start of the trial (by default) or another event (if 'after'
                is specified).
            after (str, optional): The name of an existing event that the onset
                is relative to. If not specified, the onset is relative to the
                start of the trial.

        """
        if after is not None:
            # If 'after' provided, 'onset' is relative to that event
            self._ensure_exists(after)
            onset = self.events[after] + onset
        self.events[label] = onset
        self._issued[label] = False

    
    def register_ticket(self, event):
        # Deprecated, use add_event instead
        if not isinstance(event, TrialEventTicket):
            try:
                event = TrialEventTicket(*event)
            except SyntaxError:
                raise TypeError("Argument 'event' must be a List or a TrialEventTicket.")
        self.add_event(event.label, event.onset)


    def register_tickets(self, events):
        # Deprecated, use add_event instead
        for e in events:
            self.register_ticket(e)


    def before(self, label, pump_events=False):
        """Checks whether a given event has yet to occur in the trial.

        Args:
            label (str): The name of the event to check.
            pump_events (bool, optional): Deprecated, should always be False.

        Returns:
            True if the specified trial event has yet to occur, otherwise False.

        """
        return not self.after(label, pump_events)


    def after(self, label, pump_events=False):
        """Checks whether a given event has occurred in the trial.

        Args:
            label (str): The name of the event to check.
            pump_events (bool, optional): Deprecated, should always be False.

        Returns:
            True if the specified trial event has already occured, otherwise False.

        """
        self._ensure_exists(label)
        if pump_events:
            ui_request()

        # If event wasn't already issued, check if it should be issued now
        if not self._issued[label]:
            if self.events[label] < self.time_elapsed:
                self._issued[label] = True

        return self._issued[label]


    def between(self, a, b):
        """Checks whether the current trial time is between two events.

        Args:
            a (str): The name of the first event.
            b (str): The name of the second event.
        
        Returns:
            True if the trial time is between events a and b, otherwise False.

        """
        return self.after(a) and self.before(b)


    def start(self):
        """Starts the EventManager's trial clock.
        
        The onsets of events added to the EventManager are relative to when this
        method is called.

        If you are using the :class:`~klibs.KLExperiment.Experiment` object's
        built-in ``self.evm``, this is called automatically at the start of
        every trial.

        """
        self.start_time = time()
        for label in self.events.keys():
            self._issued[label] = False


    def reset(self):
        """Resets the EventManger, clearing all added events.

        If you are using the :class:`~klibs.KLExperiment.Experiment` object's
        built-in ``self.evm``, this is called automatically at the end of
        every trial.

        """
        self.events = {}
        self._issued = {}
        self.start_time = None

    
    def start_clock(self):
        # Alias for backwards compatibility, will be removed soon
        self.start()


    def stop_clock(self):
        # Alias for backwards compatibility, will be removed soon
        self.reset()


    @property
    def time_elapsed(self):
        # Internal method for getting time since start() in milliseconds.
        if not self.start_time:
            return 0.0
        return (time() - self.start_time) * 1000


    @property
    def trial_time(self):
        # Gets time since start() in seconds. Deprecated, not part of public API.
        return self.time_elapsed / 1000.0


    @property
    def trial_time_ms(self):
        # Alias for backwards compatibility, not part of the public API.
        return self.time_elapsed
