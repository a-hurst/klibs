__author__ = 'Jonathan Mulle & Austin Hurst'

import abc
from collections import OrderedDict

from klibs.KLConstants import RECT_BOUNDARY, CIRCLE_BOUNDARY, ANNULUS_BOUNDARY
from klibs.KLExceptions import BoundaryError
from klibs.KLInternal import valid_coords, iterable
from klibs.KLUtilities import midpoint, line_segment_len

"""A module containing different types of boundaries that can you can use to see if a given point
is within a given region or not. These boundaries can be used as individual objects, or
aggregated and managed together using :class:`BoundaryInspector` class.

Only rectangle, circle, and annulus-shaped boundaries are currently available, but you can define
your own custom boundary shapes by subclassing the :class:`Boundary` object.

"""


class BoundaryInspector(object):
	"""A class for managing and inspecting multiple :class:`Boundary` objects.

	Args:
		boundaries (:obj:`List`, optional): A list of :obj:`Boundary` objects with which
			to initialize the inspector.

	"""

	def __init__(self, boundaries=[]):
		self.boundaries = OrderedDict()
		self.add_boundaries(boundaries)

	def __verify_label(self, label):
		if label not in self.boundaries.keys():
			e = "No boundary with the label '{0}' has been added to the inspector."
			raise KeyError(e.format(label))

	def add_boundary(self, boundary, bounds=None, shape=None):
		"""Adds a boundary to the inspector.
		
		For legacy purposes, boundaries can be added using the label, bounds, and shape
		arguments. Support for this is deprecated, and may be removed in a future version:

		=============== ========================== ===========================
		Boundary Type   Shape                      Bounds
		=============== ========================== ===========================
		Rectangle       ``klibs.RECT_BOUNDARY``    [(x1, y1), (x2, y2)]
		--------------- -------------------------- ---------------------------
		Circle          ``klibs.CIRCLE_BOUNDARY``  [(x, y), radius]
		--------------- -------------------------- ---------------------------
		Annulus         ``klibs.ANNULUS_BOUNDARY`` [(x, y), radius, thickness]
		=============== ========================== ===========================

		Args:
			boundary (:obj:`Boundary` or :obj:`str`): A :class:`Boundary` object to add to the
				inspector. May also be a label string if adding a boundary using the legacy method.
			bounds (:obj:`List`, optional): A List specifying the size and location of the new
				boundary (see the 'Bounds' column in the above table). For legacy use only.
			shape (:obj:`str`, optional): The type of the new boundary (see the 'Shape' column in
				the above table). For legacy use only.

		Raises:
			ValueError: If 'bounds' or 'shape' are not provided and 'boundary' is not a
				:class:`Boundary` object.
			ValueError: If 'shape' is not one of 'Rectangle', 'Circle', or 'Annulus'.
		
		"""
		if isinstance(boundary, Boundary):
			b = boundary
			label = b.label
		else:
			label = boundary
			if bounds == None or type(shape) != str:
				e = "'bounds' and 'shape' must be given if not adding an existing Boundary object."
				raise ValueError(e)	
			if shape.lower() == RECT_BOUNDARY:
				b = RectangleBoundary(label, *bounds)
			elif shape.lower() == CIRCLE_BOUNDARY:
				b = CircleBoundary(label, *bounds)
			elif shape.lower() == ANNULUS_BOUNDARY:
				b = AnnulusBoundary(label, *bounds)
			else:
				raise ValueError("'shape' must be one of 'Rectangle', 'Circle', or 'Annulus'.")
		self.boundaries[label] = b

	def add_boundaries(self, boundaries):
		"""Adds one or more boundaries to the inspector. Boundaries can either be lists in the
		format [label, bounds, shape] (see :meth:`add_boundary` for more info) or :class:`Boundary`
		objects (e.g. a :class:`RectangleBoundary`).

		Args:
			boundaries (:obj:`List`): A list containing the boundaries to add to the inspector.
		
		"""
		for b in boundaries:
			if isinstance(b, Boundary):
				self.add_boundary(b)
			else:
				self.add_boundary(*b)

	def within_boundary(self, label, p):
		"""Determines whether a given point is within a specific boundary.

		Args:
			label (:obj:`str`): The label of the boundary to inspect.
			p (:obj:`Tuple` or :obj:`List`): The (x,y) coordinates of the point to check for the
				presence of within the boundary.
		
		Returns:
			bool: True if the point falls within the boundary, otherwise False.
		
		Raises:
			KeyError: If no boundary with the given label exists within the inspector.
			ValueError: If the given point is not a valid set of (x,y) coordinates.
		
		"""
		self.__verify_label(label)
		return self.boundaries[label].within(p)

	def which_boundary(self, p, labels=None, ignore=[]):
		"""Determines which boundary (if any) a given point is within.

		Unlike :meth:`within_boundary`, which checks whether a point is within a
		`specific` boundary, this method returns the name of the boundary (if any) a
		given point is within (e.g. 'left_button'). If the point falls within multiple
		boundaries, the label of the boundary that was added most recently will be
		returned.

		By default, the point will be tested against all boundaries in the inspector.
		To check only a subset of the boundaries, you can specify the names of the
		boundaries to check using the ``labels`` argument. Conversely, you can exclude
		specific boundaries from the search using the ``ignore`` argument.

		Args:
			p (:obj:`Tuple` or :obj:`List`): The (x,y) coordinates of the point to test
				against the inspector's boundaries.
			labels (:obj:`List`, optional): A list containing the labels of the
				boundaries to inspect. Defaults to inspecting all boundaries.
			ignore (:obj:`List`, optional): A list containing the labels of any
				boundaries to ignore. Defaults to an empty list (no ignored boundaries).
		
		Returns:
			:obj:`str` or None: The label of the boundary that the point is within, or
			``None`` if the point does not fall within any boundary.
		
		Raises:
			KeyError: If any given labels do not correspond to a boundary within the inspector.
			ValueError: If the given point is not a valid set of (x,y) coordinates.
		
		"""
		if not labels:
			labels = list(self.boundaries.keys())
		if not iterable(ignore):
			ignore = [ignore]

		boundary = None
		for l in self.boundaries.keys():
			if l in ignore or not l in labels:
				continue
			self.__verify_label(l)
			if self.boundaries[l].within(p):
				boundary = l

		return boundary

	def remove_boundaries(self, labels):
		"""Removes one or more boundaries from the inspector.

		Args:
			labels (:obj:`List`): A list containing the labels of the boundaries to remove.
		
		Raises:
			KeyError: If any label does not correspond to a boundary within the inspector.
		
		"""
		if not iterable(labels): labels = [labels]
		for label in labels:
			self.__verify_label(label)
			self.boundaries.pop(label, None)

	def clear_boundaries(self, preserve=[]):
		"""Removes all boundaries from the inspector.

		Args:
			preserve (:obj:`List`, optional): A list containing the labels of any boundaries
				that should remain in the inspector after the clear.

		Raises:
			KeyError: If any given labels do not correspond to boundaries within the inspector.
		
		"""
		if not iterable(preserve):
			preserve = [preserve]
		preserved = OrderedDict()
		for label in preserve:
			self.__verify_label(label)
			preserved[label] = self.boundaries[label]
		self.boundaries = preserved

	def draw_boundaries(self, labels=None):
		"""Blits one or more boundaries to the display buffer. If no individual boundaries are
		specified, all enabled boundaries will be drawn. Must be called between
		:func:`~klibs.KLGraphics.fill` and :func:`~klibs.KLGraphics.flip` within your code for
		the boundaries to be drawn.

		NOTE: This is not currently implemented, and will raise an exception if it is used.

		Args:
			labels (:obj:`List`, optional): A list containing the labels of the boundaries to draw.
				If no labels are specified or labels == None, all enabled boundaries in the
				inspector will be drawn.
		
		"""
		raise NotImplementedError("Boundary drawing will be implemented in a future version.")

	@property
	def labels(self):
		""":obj:`List`: The names of all boundaries currently within the inspector.

		"""
		return list(self.boundaries.keys())
	


class Boundary(object):
	"""A base class defining the required attributes and functions of a Boundary object. You will
	only need to use this class if you want to create your own custom Boundary type. Otherwise, you
	can use the existing :class:`RectangleBoundary`, :class:`CircleBoundary`, and
	:class:`AnnulusBoundary` classes instead.

	Args:
		label (:obj:`str`): An informative label to use for the boundary.

	"""

	def __init__(self, label):
		super(Boundary, self).__init__()
		self.__label = label

	def __repr__(self):
		s = "<klibs.KLBoundary.{0} at {1}>"
		return s.format(self.__str__, hex(id(self)))

	def __str__(self):
		return "Boundary()"

	def __contains__(self, p):
 		return self.within(p)

	@property
	def label(self):
		return self.__label

	@property
	def bounds(self):
		raise NotImplementedError

	@bounds.setter
	def bounds(self, boundary):
		raise NotImplementedError

	@abc.abstractmethod
	def within(self, p):
		pass



class RectangleBoundary(Boundary):
	"""A rectangular :obj:`Boundary` object. Can be used to determine whether a point is within a
	given rectangular region on a surface (e.g. the screen).
	
	Args:
		label (:obj:`str`): An informative label to use for the boundary.
		p1 (:obj:`Tuple`): The (x,y) coordinates of the top-left corner of the boundary.
		p2 (:obj:`Tuple`): The (x,y) coordinates of the bottom-right corner of the boundary.

	"""
	__name__ = "RectangleBoundary"

	def __init__(self, label, p1, p2):
		super(RectangleBoundary, self).__init__(label)
		self.__p1 = None
		self.__p2 = None
		self.bounds = [p1, p2]
		self.__center = midpoint(*self.bounds)

	def __str__(self):
		return "RectangleBoundary(p1={0}, p2={1})".format(str(self.p1), str(self.p2))

	@property
	def bounds(self):
		""":obj:`List`: A list containing the top-left (p1) and bottom-right (p2) x,y coordinates
		that define the boundary rectangle, in the format [p1, p2].

		Raises:
			ValueError: If the value is not a list in the format [p1, p2].
			ValueError: If p1 or p2 are not Tuples or contain non-numeric values.
			ValueError: If the bottom-right coordinates are above or to the left of the top-left
				coordinates.

		"""
		return [self.__p1, self.__p2]

	@bounds.setter
	def bounds(self, boundary):
		try:
			x1, y1 = boundary[0]
			x2, y2 = boundary[1]
		except (IndexError, ValueError, TypeError):
			raise ValueError("Rectangle boundaries must be given in the format [p1, p2].")

		if not all([valid_coords(p) for p in boundary]):
			raise ValueError("'p1' and 'p2' must both be valid (x,y) coordinates.")

		if x1 >= x2 or y1 >= y2:
			raise ValueError("'p1' must be above and to the left of 'p2'.")

		self.__p1 = tuple(boundary[0])
		self.__p2 = tuple(boundary[1])

	@property
	def p1(self):
		""":obj:`Tuple`: The (x,y) coordinates of the top-left corner of the boundary rectangle.

		"""
		return self.__p1

	@property
	def p2(self):
		""":obj:`Tuple`: The (x,y) coordinates of the bottom-right corner of the boundary rectangle.

		"""
		return self.__p2

	@property
	def center(self):
		""":obj:`Tuple`: The (x,y) coordinates of the center of the boundary rectangle.

		"""
		return self.__center

	def within(self, p):
		"""Determines whether a given point is within the boundary.

		Args:
			p (:obj:`Tuple` or :obj:`List`): The (x,y) coordinates of the point to check for the
				presence of within the boundary.
		
		Returns:
			bool: True if the point falls within the boundary, otherwise False.
		
		Raises:
			ValueError: If the given point is not a valid set of (x,y) coordinates.
		
		"""
		if not valid_coords(p):
			raise ValueError("The given value must be a valid set of (x,y) coordinates.")
			
		return (self.__p1[0] <= p[0] <= self.__p2[0]) and (self.__p1[1] <= p[1] <= self.__p2[1])



class CircleBoundary(Boundary):
	"""A circle :obj:`Boundary` object. Can be used to determine whether a point is within a
	given circular region on a surface (e.g. the screen).
	
	Args:
		label (:obj:`str`): An informative label to use for the boundary.
		center (:obj:`Tuple`): The (x,y) coordinates of the center of the circle.
		radius (int or float): The radius of the circle.

	"""
	__name__ = "CircleBoundary"

	def __init__(self, label, center, radius):
		super(CircleBoundary, self).__init__(label)
		self.__c = None
		self.__r = None
		self.bounds = [center, radius]

	def __str__(self):
		return "CircleBoundary(center={0}, radius={1})".format(str(self.center), self.radius)

	@property
	def bounds(self):
		""":obj:`List`: A list containing the center coordinates (c) and radius (r) of the circle
		that defines the boundary, in the format [c, r].

		Raises:
			ValueError: If the value is not a list in the format [center, radius].
			ValueError: If 'c' is not a valid pair of (x,y) coordinates.
			ValueError: If the given radius is not a number greater than zero.

		"""
		return [self.__c, self.__r]

	@bounds.setter
	def bounds(self, boundary):
		try:
			center, radius = boundary
		except (ValueError, TypeError):
			raise ValueError('Circle boundaries must be given in the format [center, radius].')

		self.center = center
		self.radius = radius

	@property
	def center(self):
		""":obj:`Tuple`: The (x,y) coordinates of the center of the boundary circle.
		
		Raises:
			ValueError: If the given value is not a valid pair of (x,y) coordinates.

		"""
		return self.__c

	@center.setter
	def center(self, coords):
		if valid_coords(coords):
			self.__c = tuple(coords)
		else:
			raise ValueError("The center must be a valid set of (x,y) coordinates.")

	@property
	def radius(self):
		"""int or float: The radius of the boundary circle.
		
		Raises:
			ValueError: If the given radius is not a number greater than zero.

		"""
		return self.__r

	@radius.setter
	def radius(self, r):
		if type(r) in [int, float] and r > 0:
			self.__r = r
		else:
			raise ValueError("The boundary radius must be a number greater than zero.")

	def within(self, p):
		"""Determines whether a given point is within the boundary.

		Args:
			p (:obj:`Tuple` or :obj:`List`): The (x,y) coordinates of the point to check for the
				presence of within the boundary.
		
		Returns:
			bool: True if the point falls within the boundary, otherwise False.
		
		Raises:
			ValueError: If the given point is not a valid set of (x,y) coordinates.
		
		"""
		if not valid_coords(p):
			raise ValueError("The given value must be a valid set of (x,y) coordinates.")

		return line_segment_len(p, self.__c) <= self.__r



class AnnulusBoundary(Boundary):
	"""An annulus :obj:`Boundary` object. Can be used to determine whether a point is within a
	ring-shaped region on a surface (e.g. the screen).
	
	Args:
		label (:obj:`str`): An informative label to use for the boundary.
		center (:obj:`Tuple`): The (x,y) coordinates of the center of the annulus.
		radius (int or float): The outer radius of the annulus.
		thickness (int or float): The thickness of the annulus.

	"""
	__name__ = "AnnulusBoundary"

	def __init__(self, label, center, radius, thickness):
		super(AnnulusBoundary, self).__init__(label)
		self.__center = None
		self.__r_outer = None
		self.__thickness = None
		self.bounds = [center, radius, thickness]

	def __str__(self):
		s = "AnnulusBoundary(center={0}, radius={1}, thickness={2})"
		return s.format(str(self.center), self.outer_radius, self.thickness)

	@property
	def bounds(self):
		""":obj:`List`: A list containing the center coordinates (c), outer radius (r), and
		thickness (t) of the annulus that defines the boundary, in the format [c, r, t].

		Raises:
			ValueError: If the value is not a list in the format [center, radius, thickness].
			ValueError: If 'c' is not a valid pair of (x,y) coordinates.
			ValueError: If the given radius and thickness are not numbers greater than zero,
				or if the thickness is equal to or greater than the radius in size.

		"""
		return [self.__center, self.__r_outer, self.__thickness]

	@bounds.setter
	def bounds(self, boundary):
		try:
			center, radius, thickness = boundary
		except (ValueError, TypeError):
			msg = 'Annulus boundaries must be given in the format [center, radius, thickness].'
			raise ValueError(msg)
		
		if not valid_coords(center):
			raise ValueError("The center must be a valid set of (x,y) coordinates.")
		
		if type(radius) not in [int, float] or radius <= 0:
			raise ValueError("The boundary radius must be a number greater than zero.")
		if type(thickness) not in [int, float] or thickness <= 0:
			raise ValueError("The boundary thickness must be a number greater than zero.")
		if thickness >= radius:
			raise ValueError("The boundary thickness must be smaller than its radius.")

		self.__center = tuple(center)
		self.__r_outer = radius
		self.__thickness = thickness

	@property
	def center(self):
		""":obj:`Tuple`: The (x,y) coordinates of the center of the boundary annulus.

		"""
		return self.__center

	@property
	def thickness(self):
		"""int or float: The width of the ring of the boundary annulus.

		"""
		return self.__thickness

	@property
	def inner_radius(self):
		"""int or float: The inner radius of the annulus boundary (i.e. outer radius - thickness).

		"""
		return self.__r_outer - self.__thickness

	@property
	def outer_radius(self):
		"""int or float: The outer radius of the annulus boundary.

		"""
		return self.__r_outer

	def within(self, p):
		"""Determines whether a given point is within the boundary.

		Args:
			p (:obj:`Tuple` or :obj:`List`): The (x,y) coordinates of the point to check for the
				presence of within the boundary.
		
		Returns:
			bool: True if the point falls within the boundary, otherwise False.
		
		Raises:
			ValueError: If the given point is not a valid set of (x,y) coordinates.
		
		"""
		if not valid_coords(p):
			raise ValueError("The given value must be a valid set of (x,y) coordinates.")

		return self.inner_radius <= line_segment_len(p, self.__center) <= self.outer_radius
