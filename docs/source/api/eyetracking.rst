KLEyeTracking
*************

The KLEyeTracking module provides a simple unified interface for working with different kinds of
eye trackers in your experiments. All supported eye trackers make use of the same common interface
defined in the :obj:`~.KLEyeTracker.EyeTracker` class below, meaning that an experiment written
with the interface should work on any of the different types of eye trackers that KLibs supports.

Currently, KLibs has built-in support for two kinds of eye tracker: SR Research EyeLink trackers,
and a simulated eye tracker that uses mouse movements as a stand-in for gaze and gaze events,
allowing you to write and run eye-tracking experiments without a physical eye tracker
present. You can view more detailed documentation for each of these tracker types here:

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

The EyeTracker API
===================

.. automodule:: klibs.KLEyeTracking.KLEyeTracker
	:undoc-members:
	:members:
		