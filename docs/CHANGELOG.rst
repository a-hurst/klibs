Changelog
=========
This is a log of the latest changes and improvements to KLibs.

0.7.6a1
-------

Released on XXXX-XX-XX.


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
* Improved the loading speed of the ``klibs`` command line.
* Added proper print methods for all built-in :obj:`~klibs.KLBoundary.Boundary`
  types.
* Added a new argument ``ignore`` to the
  :meth:`~klibs.KLBoundary.BoundaryInspector.which_boundary` method of the
  ``BoundaryInspector`` class, allowing easy exclusion of specific boundaries
  from the search and replacing the functionality of the now-removed
  ``disable_boundaries`` and ``enable_boundaries`` methods.
* Added a new ``boundaries`` argument to the
  :obj:`~klibs.KLBoundary.BoundaryInspector` class to allow initializing an
  inspector with a given set of boundaries.
* Added a new :attr:`~klibs.KLBoundary.BoundaryInspector.labels` attribute to
  the ``BoundaryInspector`` class to easily retrieve the names of all
  boundaries currently within the inspector.
* Added support for using Python's ``in`` operator with
  :obj:`~klibs.KLBoundary.Boundary` objects (e.g. ``if point in circle``
  instead of ``if circle.within(point)``).
* :obj:`~klibs.KLBoundary.Boundary` objects can now be relocated by setting
  their ``center`` attribute to a set of pixel coordinates.


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
* :obj:`~klibs.KLBoundary.BoundaryInspector` methods now raise ``KeyError``
  exceptions instead of ``BoundaryError`` exceptions when given a boundary label
  that does not exist within the inspector.
* Removed the ``enable_boundaries`` and ``disable_boundaries`` methods as well
  as the ``active_boundaries`` attribute from the 
  :obj:`~klibs.KLBoundary.BoundaryInspector` class.
* Removed the convoluted ``bounds`` getter/setter attribute from all
  :obj:`~klibs.KLBoundary.Boundary` subclasses.


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
