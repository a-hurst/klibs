Changelog
=========
This is a log of the latest changes and improvements to KLibs.


0.8.0a1
-------

(Unreleased)

Runtime Changes:

* KLibs now requires Python 3.7 or newer to run, dropping support for 2.7.

Fixed Bugs:

* KLibs no longer crashes on launch with Python 3.12.


0.7.7b1
-------

Released on 2023-09-28


New Features:

* Added a new module, :mod:`~klibs.KLResponseListeners`, to replace the
  ``ResponseCollector`` API for a much simpler and more Pythonic way of
  collecting common response types. The ``KLResponseCollector`` module is now
  deprecated and should not be used for future projects.
* Added :obj:`~klibs.KLText.TextStyle` to the public API, allowing easy
  on-the-fly definitions of new custom text styles as objects.
* Added a new function :func:`~klibs.KLText.add_text_style` for defining new
  font rendering styles without needing to deal with ``self.txtm`` or
  ``KLEnvironment``.
* Automatic loading of custom fonts: all valid ``.ttf`` and ``.otf`` font files
  in a project's ``ExpAssets/Resources/font`` folder are now automatically
  loaded and ready-to-use on experiment launch, removing the need to manually
  add fonts with ``txtm.add_font``. For example, if ``ComicSans.ttf`` is present
  in the experiment's font folder, you can now create a custom font style with
  ``font = "ComicSans"`` without manually loading the font.
* Added a new dict-based API, :obj:`~klibs.KLStructure.FactorSet`, for defining
  the per-trial categorical factors and their levels for the experiment.
* Added a ``released`` argument to :func:`~klibs.KLUserInterface.key_pressed`
  to optionally check for 'key released' events instead of 'key pressed' events.
* Added a new method :meth:`~klibs.KLEventInterface.EventManager.add_event` for
  a friendlier, more readable way of adding events to the trial sequencer.
* Added a convenience function :func:`~klibs.KLTime.time_msec` for getting
  timestamps in milliseconds.
* The :meth:`~klibs.KLDatabase.Database.insert` method for the
  :class:`~klibs.KLDatabase.Database` class now supports inserting multiple rows
  at once via a list of dicts (one for each row). When inserting many rows of
  data, this can offer substatial speedup over calling ``insert`` on each row
  individually.


Runtime Changes:

* The way that trials are internally generated and randomized has been changed,
  breaking random seed compatibility with older releases.
* Previously, it was possible (albeit unlikely) for a block with more than
  enough trials for a complete factor set (e.g. trial count of 24 for a factor
  set of 16) to be missing one or more possible factor combinations. This has
  now been fixed, as each block of trials is now generated individually (instead
  of being generated all at once and then split into blocks).
* The TryLink mouse-simulated eye tracker now supports performing drift correct
  by pressing the space bar in addition to clicking.
* The EyeLink camera setup image is now always scaled to a height of 480 pixels
  for a larger view and easier setup.
* Changed :func:`~klibs.KLUserInterface.any_key` to flush existing input before
  starting and require that the mouse be both clicked `and` released before
  returning to avoid registering spurious input.
* KLibs will now raise an error on launch if any required tables or columns are
  missing from the database.


API Changes:

* :func:`~klibs.KLCommunication.message` now returns the rendered text surface
  regardless of whether ``blit_txt`` is True.
* Removed legacy arguments ``flip_screen`` and ``clear_screen`` from the
  :func:`~klibs.KLCommunication.message` function.
* The default value of the ``blit_txt`` argument for
  :func:`~klibs.KLCommunication.message` has been changed from True to False,
  and has been deprecated. From now own, any message provided with a blit
  location will be blit there regardless of whether ``blit_txt`` is True.
* The :meth:`~klibs.KLEyeTracking.KLEyeTracker.drift_correct` method now
  returns the magnitude of measured drift error (in degrees).
* Added a new parameter ``P.default_line_space`` for setting a custom
  default line spacing for text rendering (defaults to ``2.0``).
* The ``register_ticket`` and ``register_tickets`` methods of
  :class:`~klibs.KLEventInterface.EventManager` are now deprecated in favour of
  ``add_event``.
* Deprecated the ``pump_events`` options for ``before`` and ``after`` in
  :class:`~klibs.KLEventInferface.EventManger`.
* Renamed :class:`~klibs.KLEventInferface.EventManger`'s ``start_clock`` and
  ``stop_clock`` methods to ``start`` and ``reset``, respectively.
* Deprecated the ``trial_time`` and ``trial_time_ms`` attributes for
  :class:`~klibs.KLEventInferface.EventManger`. Measuring durations within a
  trial should be done with :mod:`~klibs.KLTime` functions/classes instead.
* Removed the :class:`~klibs.KLEventInferface.EventManger` instance from
  KLEnvironment and :class:`~klibs.KLEnvironment.EnvAgent`. The global
  ``EventManager`` instance for the Experiment object (``self.evm``) is now a
  regular attribute.
* Removed the Slack messaging system and its functions, which should be in its
  own self-contained .py file instead of KLibs itself.
* Changed :func:`~klibs.KLEventQueue.pump()` to always return the contents of
  the input event queue, deprecating the ``return_events`` argument.
* The ``KLDatabase.EntryTemplate`` class has been deprecated in favour of
  the :meth:`~klibs.KLDatabase.insert` method, which now handles null columns
  correctly.


Fixed Bugs:

* Fixed ``klibs export`` with older databases (regression in 0.7.6a1).
* Updated EyeLink camera setup code to work correctly with latest Pylink.
* Fixed detection of Windows 11 in KLRuntimeInfo.
* Fixed a bug that prevented repeated identical lines of text from being
  rendered within the same message.


0.7.6b1
-------

Released on 2022-12-01.


New Features:

* Greatly improved runtime info detection for Linux, adding proper distro
  and release number detection. Overall OS name and version detection cleaned
  up and improved across platforms.
* :class:`~klibs.KLGraphics.NumpySurface` objects now support blitting with
  alpha blending, which is enabled by default. To use the old (and slightly
  faster) method of overwriting existing alpha during blit, you can set the new
  `blend` argument to `False`.
* :class:`~klibs.KLGraphics.NumpySurface` objects now support clipping during
  blit, which is enabled by default. This allows for blitting images that
  exceed the bounds of the surface, which would previously result in an error.
* Blank :class:`~klibs.KLGraphics.NumpySurface` objects can now be created by
  specifying a given height, width, and fill color.
* Greatly expanded the :meth:`~klibs.KLGraphics.NumpySurface.mask` method for
  NumpySurface objects, allowing mask inversion, the use of greyscale masks,
  specifying a registration for the mask location, and more.
* The :meth:`~klibs.KLGraphics.NumpySurface.blit` and
  :meth:`~klibs.KLGraphics.NumpySurface.mask` methods of the NumpySurface class
  now support the same wide array of source formats as the NumpySurface class
  itself.
* Added a new :meth:`klibs.KLGraphics.NumpySurface.copy` method that allows
  creating a copy of a NumpySurface that won't be modified by future changes to
  the original.
* Added a new :meth:`klibs.KLGraphics.NumpySurface.trim` method that allows
  automatic trimming of any transparent pixels surrounding the surface content.
* Added new :meth:`~klibs.KLGraphics.NumpySurface.flip_left`,
  :meth:`~klibs.KLGraphics.NumpySurface.flip_right`,
  :meth:`~klibs.KLGraphics.NumpySurface.flip_x`, and
  :meth:`~klibs.KLGraphics.NumpySurface.flip_y` method to the NumpySurface class
  for fast 90-degree rotation and mirroring along the axes, respectively.
* Added new :attr:`~klibs.KLGraphics.NumpySurface.dimensions` and
  :attr:`~klibs.KLGraphics.NumpySurface.surface_c` attributes to the
  NumpySurface class for retrieving the current dimensions and midpoint of a
  surface, respectively.
* Significantly improved the speed of the ``klibs`` command line interface.
* Added proper print methods for all built-in :obj:`~klibs.KLBoundary.Boundary`
  types.
* Added a new argument ``ignore`` to the
  :meth:`~klibs.KLBoundary.BoundarySet.which_boundary` method of the
  ``BoundarySet`` class, allowing easy exclusion of specific boundaries
  from the search and replacing the functionality of the now-removed
  ``disable_boundaries`` and ``enable_boundaries`` methods.
* Added a new ``boundaries`` argument to the
  :obj:`~klibs.KLBoundary.BoundarySet` class to allow initializing a boundary
  set with a given set of boundaries.
* Added a new :attr:`~klibs.KLBoundary.BoundarySet.labels` attribute to
  the ``BoundarySet`` class to easily retrieve the names of all
  boundaries currently within the set.
* Added support for using Python's ``in`` operator with
  :obj:`~klibs.KLBoundary.Boundary` objects (e.g. ``if point in circle``
  instead of ``if circle.within(point)``).
* :obj:`~klibs.KLBoundary.Boundary` objects can now be relocated by setting
  their ``center`` attribute to a set of pixel coordinates.
* :obj:`~klibs.KLBoundary.RectangleBoundary` objects now have ``height`` and
  ``width`` attributes.
* Replaced an unnecessary runtime warning about PyAudio on launch (regardless of
  whether the project required audio input) with a ``RuntimeError`` if trying to
  collect an :class:`~klibs.KLResponseCollectors.AudioResponse` without PyAudio.
* Raise an error instead of entering the missing database prompt when trying to
  export data or rebuild the database for a project without a database file.
* ``klibs update`` now installs the latest GitHub release of KLibs instead of
  the latest commit from the default branch.
* ``EDF`` folder is no longer created by default for new projects. It is now
  created only if needed when saving data from an eye tracking experiment.
* Added a new function :func:`~klibs.KLUserInferface.mouse_clicked` to easily
  check a given input event queue for clicks and releases of mouse buttons,
  similar to :func:`~klibs.KLUserInferface.key_pressed` for the keyboard. 
* Added a new function :func:`~klibs.KLUserInferface.get_clicks` to easily
  fetch the (x, y) coordinates of any mouse clicks in a given input event queue.
* Added :meth:`~klibs.KLDatabase.Database.select` and
  :meth:`~klibs.KLDatabase.Database.delete` methods to the 
  :class:`~klibs.KLDatabase.Database` class.
* Added optional Retina support for macOS, which is now enabled by default for
  new projects. It can be enabled or disabled using the ``allow_hidpi`` flag in
  an experiment's ``params.py`` file.
* Enabled HiDPI support on Windows 10, allowing experiments to run at the true
  desktop resolution (e.g. 1920x1080) instead of the scaled desktop resolution
  (e.g. 1600x900).
* Added export logging to prevent re-exporting identical data files when
  repeatedly calling ``klibs export`` for a project. With this change,
  duplicate data files (e.g. ``p1.2022-11-19_1.txt`` and
  ``p1.2022-11-19_2.txt``) will only occur if the database is rebuilt,
  and new data is collected and exported that results in an identical file name
  to an existing data file from before the rebuild. These changes do not affect
  single-file (``klibs export -c``) exporting.


API Changes:

* The initalization arguments for the :class:`~klibs.KLGraphics.NumpySurface`
  class have been heavily revised, removing all arguments related to foreground
  and background layers and adding a new argument specifying a default surface
  fill.
* Removed the `rendered`, `foreground`, and `background` attributes from
  the :class:`~klibs.KLGraphics.NumpySurface` class, as NumpySurface objects
  no longer require rendering or have any concept of layers. To access the
  contents of a surface's underlying Numpy array, use the new `content`
  attribute instead.
* All :class:`~klibs.KLGraphics.NumpySurface` arguments related to layers have
  been removed.
* The :meth:`~klibs.KLGraphics.NumpySurface.scale` method for NumpySurface
  objects now accepts height and width as separate arguments instead of a tuple,
  allowing users to specify a single dimension and scale preserving the aspect
  ratio of the surface.
* The :attr:`~klibs.KLGraphics.NumpySurface.average_color` of a NumpySurface is
  now an attribute instead of a method.
* The ``rgb`` and ``const_lum`` colorspaces have been renamed to
  ``COLORSPACE_RGB`` and ``COLORSPACE_CONST``, respectively. They can still be
  accessed by their original names for backwards compatibility.
* The :mod:`~klibs.KLGraphics` module now exports the names of its submodules'
  most common functions and classes. This means you typically no longer need to
  specify a submodule when importing from :mod:`~klibs.KLGraphics` (e.g.
  ``from klibs.KLGraphics import NumpySurface`` instead of
  ``from klibs.KLGraphics.KLNumpySurface import NumpySurface``).
* Removed the broken and problematic ``rotate`` method from the
  :class:`~klibs.KLGraphics.NumpySurface` class. For rotating images at anything
  other than 90-degree angles, please use the ``Image`` class from the Pillow
  library instead.
* :class:`~klibs.KLJSON_Object.KLJSON_Object` has been deprecated in favour of a
  new JSON import function, :func:`~klibs.KLJSON_Object.import_json`.
* Standardized built-in :obj:`~klibs.KLBoundary.Boundary` types to always use
  tuples for storing/returning (x, y) pixel coordinates.
* Removed the legacy ``shape`` attribute from :obj:`~klibs.KLBoundary.Boundary`
  (use ``isinstance`` to check boundary types instead).
* Renamed ``BoundaryInspector`` to :obj:`~klibs.KLBoundary.BoundarySet` to
  better represent its purpose.
* :obj:`~klibs.KLBoundary.BoundarySet` methods now raise ``KeyError``
  exceptions instead of ``BoundaryError`` exceptions when given a boundary label
  that does not exist within the set.
* Removed the ``enable_boundaries`` and ``disable_boundaries`` methods as well
  as the ``active_boundaries`` attribute from the 
  :obj:`~klibs.KLBoundary.BoundarySet` class.
* Removed the convoluted ``bounds`` getter/setter attribute from all
  :obj:`~klibs.KLBoundary.Boundary` subclasses.
* :obj:`~klibs.KLBoundary.RectangleBoundary` objects no longer raise an error
  if ``p2`` is above or to the left of ``p1`` and instead swaps the x and y
  values such that ``p1`` is always the top-leftmost coordinate.
* Moved the :func:`~klibs.KLEventQueue.pump` and
  :func:`~klibs.KLEventQueue.flush` to a new module :mod:`klibs.KLEventQueue`.
  For legacy code, these functions can still be imported from
  :mod:`klibs.KLUtilities`.
* Renamed the :func:`show_mouse_cursor` and :func:`hide_mouse_cursor` functions
  to :func:`~klibs.KLUserInterface.show_cursor` and
  :func:`~klibs.KLUserInterface.hide_cursor`, respectively, and moved them to
  the :mod:`klibs.KLUserInterface` module. For legacy code, both functions can
  still be imported by their old names from :mod:`klibs.KLUtilities`.
* Moved the :func:`~klibs.KLUserInterface.mouse_pos` and
  :func:`~klibs.KLUserInterface.smart_sleep` functions to the 
  :mod:`klibs.KLUserInterface` module. For legacy code, these functions can
  still be imported from :mod:`klibs.KLUtilities`.
* Removed deprecated legacy functions :func:`arg_error_str`,
  :func:`bool_to_int`, :func:`camel_to_snake`, :func:`indices_of`,
  :func:`list_dimensions`, :func:`mouse_angle`, :func:`sdl_key_code_to_str`,
  :func:`snake_to_camel`, :func:`snake_to_title`, :func:`str_pad`, :func:`log`,
  and :func:`type_str` from the :mod:`klibs.KLUtilities` module.
* ``P.trial_id`` now starts at 1 and increments for every trial, regardless of
  whether it's recycled (useful for keeping in sync with EDF 'blocks').


Fixed Bugs:

* Fixed a bug in :class:`~klibs.KLJSON_Object.JSON_Object` where importing a
  JSON file with a key less than 3 characters would raise an exception.
* Fixed a bug that prevented :func:`~klibs.KLUserInterface.key_pressed` from
  reliably catching quit events.
* Fixed runtime info detection on macOS Big Sur and later.
* Rewrote the broken NumpySurface `scale` method to be usable.
* Improved reliability of checks in :class:`~klibs.KLJSON_Object.KLJSON_Object`
  that verify all JSON keys are valid Python attribute names.
* Fixed a bug preventing projects with underscores in their name from opening.
* Removed dependency on the deprecated ``imp`` module for Python 3, removing
  a runtime warning.
* Fixed :meth:`~klibs.KLBoundary.BoundarySet.clear_boundaries` to always
  keep preserved boundaries in the same order as they were added.
* Fixed suppression of colorized console output on terminals that don't support
  it.
* Fixed display stretching and mouse warping on MacBooks with a notch.
