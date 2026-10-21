TryLink
=======

The TryLink module provides an :class:`~klibs.KLEyeTracking.EyeTracker`
implementation using mouse movements to simulate eye movements. For testing and
developing eye tracking experiments without access to real hardware.

In addition to simulating gaze position using the cursor position, TryLink also
generates simulated fixation and saccade events. Blink events are also simulated
when the mouse button is held down if ``dm_click_to_blink`` is enabled in the
project's params file.

TryLink simulation is used by default unless the ``sr-research-pylink`` package
is installed, or if ``eye_tracking`` is True but ``eye_tracker_availiable`` is
False in the project's params file. In addition, TryLink simulation can also be
forced by adding the flag ``-ELx`` to the ``klibs run`` command when launching
an experiment.

To avoid duplication with the :class:`~klibs.KLEyeTracking.EyeTracker` docs,
only methods with notable TryLink-specific details are documented below:

.. autoclass:: klibs.KLEyeTracking.TryLink
	:members: calibrate, drift_correct, gaze, write
