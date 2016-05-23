__author__ = 'jono'
import abc
from klibs.KLConstants import *
from klibs.KLUtilities import *

class Boundary(object):
	__name__ = "KLBoundary"
	__shape = None

	def __init__(self, label):
		super(Boundary, self).__init__()
		self.__label = label

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
		self.__center = midpoint(*self.bounds)
		self.__x_range = None
		self.__y_range = None
		self.bounds = [p1, p2]

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
		if all(type(i) is int for i in reference):
			reference = point_pos(self.__center, reference[0], reference[1])
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
		d_xy = line_segment_len(reference, self.__center) if iterable(reference) else reference
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