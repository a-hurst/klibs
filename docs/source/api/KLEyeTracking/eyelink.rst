EyeLink
=======

The EyeLink module allows for the use of SR Research EyeLink eye trackers to
be used with the klibs runtime.

If pylink (``sr-research-pylink``) is installed in your project's Python
environment and the ``eye_tracker_availiable`` parameter is set to True, an
instance of this class will be provided as the ``self.el`` attribute of the
Experiment object.

EyeLink trackers record eye movement and gaze data for each session in EDF data
files. The EDF recording for each session is automatically transferred to the
project's ``ExpAssets/EDF`` subfolder when the task exits (unless the task
crashes with an exception).

To avoid duplication with the :class:`~klibs.KLEyeTracking.EyeTracker` docs,
only methods with notable EyeLink-specific details are documented below:

.. autoclass:: klibs.KLEyeTracking.KLEyeLink.EyeLink
	:members: calibrate, write
