`klibs.KLEyeTracking` - Working with eye trackers
*************************************************

The KLEyeTracking module provides a simple unified interface for working with different kinds of
eye trackers in your experiments. All supported eye trackers make use of the same common interface
defined in the :obj:`~.KLEyeTracker.EyeTracker` class below, meaning that an experiment written
with the interface should work on any of the different types of eye trackers that KLibs supports.

Currently, KLibs has built-in support for two kinds of eye tracker: SR Research EyeLink trackers,
and a simulated eye tracker that uses mouse movements as a stand-in for gaze and gaze events,
allowing you to write and run eye-tracking experiments without a physical eye tracker
present. Relevant details about each tracker type are provided here:

.. toctree::
    :maxdepth: 1
    
    EyeLink <KLEyeTracking/eyelink>
    Mouse Simulation <KLEyeTracking/trylink>

Using the EyeTracker Module
===========================

To use an eye tracker in your experiment, you must first set the parameter ``eyetracking`` to
True in the project's ``params.py`` file. Once this has been set, you are then able to access
the eye tracker and its functions through the experiment attribute ``self.el``. KLibs will
default to using the mouse-simulated eye tracker unless the parameter ``eyetracker_available``
is also set to True, in which case it will default to using an attached hardware eye tracker if
one is available. In order to use a physical EyeLink eye tracker, the EyeLink Developer's Kit and
the 'pylink' Python module for your OS must be installed.

Setting Up The Eye Tracker
--------------------------

By default, the initial setup for the eye tracker will be run just after launching your experiment,
immediately after demographics collection (if it is enabled). For EyeLink eye trackers, this
includes camera setup and calibration/validation. If you want eye tracker setup to be run at a
later point in your experiment you can set the parameter ``manual_eyelink_setup`` to True, in
which case setup will be run whenever ``self.el.setup()`` is called within your experiment code.

Interfacing With The Eye Tracker
--------------------------------

In order to record data from an eye tracker, it needs to be in recording mode. By default, KLibs
starts eye tracker recording just before the start of every trial, and stops recording at the end
of every trial, meaning that in most cases, all you need to worry about is calling the functions
needed to interact with the eye tracker during each trial of your experiment. If you want to use
the eye tracker outside of a trial for whatever reason, you will need to manually call 
``self.el.start()`` to start recording and ``self.el.stop()`` to stop it in order to do so.
Additionally, if you want to disable automatic starting and stopping of the eye tracker and do all
recording manually, you can set the parameter ``manual_eyelink_recording`` to True in your
project's ``params.py`` file.

Understanding The Event Queue
-----------------------------

During eye tracking, a number of different eye events can occur. A participant
might make a saccade from one location to another, fixate a stimulus for a given
duration, or blink in a critical period. When these events occur, they are
logged and placed in a queue so that they can be retrieved and inspected for
events of interest (e.g. a saccade away from fixation).

The eye event queue is retrieved using the EyeTracker's
:meth:`~klibs.KLEyeTracking.EyeTracker.get_event_queue` method, which returns a
list of :obj:`~klibs.KLEyeTracking.events.EyeEvent` objects. A table of the
different event types and their corresponding type constants is provided below:

+---------------------+---------------------------------------------------+
| Event Type          | Event Class                                       |
+=====================+===================================================+
| ``GAZE_SAMPLE``     | :obj:`~klibs.KLEyeTracking.events.GazeSample`     |
+---------------------+---------------------------------------------------+
| ``FIXATION_START``  | :obj:`~klibs.KLEyeTracking.events.FixationStart`  |
+---------------------+---------------------------------------------------+
| ``FIXATION_END``    | :obj:`~klibs.KLEyeTracking.events.FixationEnd`    |
+---------------------+---------------------------------------------------+
| ``FIXATION_UPDATE`` | :obj:`~klibs.KLEyeTracking.events.FixationUpdate` |
+---------------------+---------------------------------------------------+
| ``SACCADE_START``   | :obj:`~klibs.KLEyeTracking.events.SaccadeStart`   |
+---------------------+---------------------------------------------------+
| ``SACCADE_END``     | :obj:`~klibs.KLEyeTracking.events.SaccadeEnd`     |
+---------------------+---------------------------------------------------+
| ``BLINK_START``     | :obj:`~klibs.KLEyeTracking.events.BlinkStart`     |
+---------------------+---------------------------------------------------+
| ``BLINK_END``       | :obj:`~klibs.KLEyeTracking.events.BlinkEnd`       |
+---------------------+---------------------------------------------------+

To avoid problems with event processing when performing multiple tests in a 
short interval (e.g. checking for fixations in multiple boundaries every
iteration of a loop), you should use this method to retrieve the eye tracker
event queue once at the start and then pass it to every function that inspects
eye events.

For example, the following code will not reliably detect saccades to the second
boundary:

.. code-block:: python

    while self.evm.before('cue_on'):
        draw_stimuli()
        if self.el.saccade_to_boundary('boundary1'):
            print('saccade to boundary 1!')
        if self.el.saccade_to_boundary('boundary2'):
            print('saccade to boundary 2!')
        flip() # refresh screen

This is because the first call to :meth:`saccade_to_boundary` fetches and clears
the eye event queue, meaning that the second call is only processing the
saccades that have happened in the tiny interval since the first call. To fix
this, you should fetch the queue once per loop:

.. code-block:: python

    while self.evm.before('cue_on'):
        draw_stimuli()
        el_q = self.el.get_event_queue() # fetch queue once per loop
        if self.el.saccade_to_boundary('boundary1', event_queue=el_q):
            print('saccade to boundary 1!')
        if self.el.saccade_to_boundary('boundary2', event_queue=el_q):
            print('saccade to boundary 2!')
        flip() # refresh screen


The EyeTracker API
===================

.. autoclass:: klibs.KLEyeTracking.EyeTracker
	:members:
		