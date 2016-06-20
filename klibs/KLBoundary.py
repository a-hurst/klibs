__author__ = 'jono'
import abc

from klibs.KLConstants import RECT_BOUNDARY, CIRCLE_BOUNDARY, ANULUS_BOUNDARY
from klibs.KLExceptions import BoundaryError
from klibs.KLUtilities import iterable, midpoint, line_segment_len


class BoundaryInspector(object):

	def __init__(self):
		self.boundaries = {}

	def add_boundary(self, label, bounds, shape):
		if shape == RECT_BOUNDARY:
			b = RectangleBoundary(label, *bounds)
		elif shape == CIRCLE_BOUNDARY:
			b = CircleBoundary(label, *bounds)
		elif shape == ANULUS_BOUNDARY:
			b = AnulusBoundary(label, *bounds)
		self.boundaries[label] = b


	def add_boundaries(self, boundaries):
		for b in boundaries:
			self.add_boundary(*b)

	def within_boundary(self, label, reference):
		if not self.boundaries[label].active:
			raise BoundaryError("Boundary '{0}' is not active for searching.".format(label)
			)
		return self.boundaries[label].within(reference)

	def within_boundaries(self, reference, labels=None):

		for l in labels if labels else self.boundaries:
			try:
				if self.boundaries[l].within(reference):
					return l
			except BoundaryError:
				if not labels:
					pass
				else:
					raise
		return False

	def remove_boundary(self, label):
		try:
			del (self.boundaries[label])
		except KeyError:
			raise KeyError("Key '{0}' not found; No such gaze boundary exists!".format(label))

	def clear_boundaries(self, preserve=[]):
		preserved = {}
		for i in preserve:
			preserved[i] = self.boundaries[i]
		self.boundaries = preserved

	def draw_boundary(self, label="*"):
		print "Warning: BoundaryInspector mixin's 'draw_boundary' method is under construction and isn't currently implemented."
		return
		from klibs.KLGraphics.KLDraw import Rectangle

		if label == "*":
			return [self.draw_boundary(l) for l in self.boundaries]
		try:
			b = self.boundaries[label]
		except KeyError:
			if shape is None:
				raise IndexError("No boundary registered with name '{0}'.".format(boundary))
			if shape not in [RECT_BOUNDARY, CIRCLE_BOUNDARY]:
				raise ValueError("Argument  'shape' must be a valid shape constant (ie. RECT, CIRCLE, etc.).")
		width = boundary[1][1] - boundary[0][1]
		height = boundary[1][0] - boundary[0][0]
		return Rectangle(width, height, [3, [255, 255, 255, 255]]).render(),

	def add_anonymous_boundary(self, bounds, shape):
		for i in range(0, len(self.boundaries)):
			label = 'anonymous_{0}'.format(i)
			if not label in self.boundaries:
				self.add_boundary(label, bounds, shape)
				return label

	def set_boundary_active(self, label):
		self.boundaries[label].active = True

	def set_boundary_inactive(self, label):
		self.boundaries[label].active = False



class Boundary(object):
	__name__ = "KLBoundary"
	__shape = None

	def __init__(self, label):
		super(Boundary, self).__init__()
		self.__label = label
		self.active = True

	@property
	def label(self):
		return

	@property
	def shape(self):
		return self.__shape

	@property
	def bounds(self):
		raise NotImplementedError

	@bounds.setter
	def bounds(self):
		raise NotImplementedError

	@abc.abstractmethod
	def within(self, reference):
		pass



class RectangleBoundary(Boundary):
	__name__ = "KLRectangleBoundary"
	__shape = RECT_BOUNDARY

	def __init__(self, label, p1, p2):
		super(RectangleBoundary, self).__init__(label)
		self.__p1 = None
		self.__p2 = None
		self.__x_range = None
		self.__y_range = None
		self.bounds = [p1, p2]
		self.__center = midpoint(*self.bounds)

	@property
	def bounds(self):
		return [self.__p1, self.__p2]

	@bounds.setter
	def bounds(self, boundary_data):
		try:
			for i in boundary_data:
				iter(i)
			self.__p1 = boundary_data[0]
			self.__p2 = boundary_data[1]
			self.__x_range = range(self.__p1[0], self.__p2[0])
			self.__y_range = range(self.__p1[1], self.__p2[1])
		except (AttributeError, IndexError):
			raise TypeError("Intialization of RectangleBoundary expects 2-item sequence of x,y pairs.")

	@property
	def p1(self):
		return self.__p1


	@property
	def p2(self):
		return self.__p2

	def within(self, reference):
		if not iterable(reference):
			raise TypeError("within() expects a 2-item sequence; either an x,y pair, or amplitude, angle pair.")
		# if all(type(i) is int for i in reference):
		# 	reference = point_pos(self.__center, reference[0], reference[1])
		return reference[0] in self.__x_range and reference[1] in self.__y_range



class CircleBoundary(Boundary):
	__name__ = "KLCircleBoundary"
	__shape = CIRCLE_BOUNDARY

	def __init__(self, label, center, radius):
		super(CircleBoundary, self).__init__(label)
		self.__r = None
		self.__center = None
		self.bounds = [center, radius]

	@property
	def bounds(self):
		return [self.__center, self.__r]

	@bounds.setter
	def bounds(self, boundary_data):
		# try:
		if not iterable(boundary_data[0]):
		# except AttributeError:
			raise ValueError("Argument 'center' expects 2-item sequence (an x,y pair).")
		try:
			if boundary_data[1] < 0:
				raise ValueError
		except (TypeError, ValueError):
			raise ValueError("Argument 'radius' must be a positive number.")
		self.__center = boundary_data[0]
		self.__r = boundary_data[1]

	@property
	def center(self):
		return self.__center


	@property
	def radius(self):
		return self.__r

	def within(self, reference):
		try:
			d_xy = line_segment_len(reference, self.__center)
		except TypeError:
			d_xy = reference
		return  d_xy < self.__r


class AnulusBoundary(Boundary):
	__name__ = "KLAnulusBoundary"
	__shape = ANULUS_BOUNDARY

	def __init__(self, label, center, inner_radius, span=None):
		super(AnulusBoundary, self).__init__(label)
		self.__r_inner = None
		self.__span_range = None
		self.__span = None
		self.__center = None
		self.bounds = [center, inner_radius, span]

	@property
	def bounds(self):
		return [self.__center, self.__r_inner, self.__r_outer, self.__span]

	@bounds.setter
	def bounds(self, boundary_data):
		try:
			iter(boundary_data[0])
		except AttributeError:
			raise ValueError("Argument 'center' expects 2-item sequence (an x,y pair).")
		try:
			for i in boundary_data[1:]:
				if boundary_data[1] < 0:
					raise ValueError
		except (TypeError, ValueError):
			raise ValueError("Argument 'radius' must be a positive number.")
			self.__center = boundary_data[0]
			self.__r_inner = boundary_data[1]
			self.__span = boundary_data[2]
			self.__span_range = range(self.__r_inner, self.__r_inner + self.__span)

	@property
	def center(self):
		return self.__center

	@property
	def span(self):
		return self.__span

	@property
	def inner_radius(self):
		return self.__r_inner

	def within(self, reference):
		d_xy = line_segment_len(reference, self.__center) if iterable(reference) else reference
		return  d_xy in self.__span_range