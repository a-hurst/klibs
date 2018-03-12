__author__ = 'jono'

import abc

from klibs.KLConstants import RECT_BOUNDARY, CIRCLE_BOUNDARY, ANNULUS_BOUNDARY
from klibs.KLExceptions import BoundaryError
from klibs.KLUtilities import iterable, midpoint, line_segment_len


class BoundaryInspector(object):

	def __init__(self, *args, **kwargs):
		"""

		:param args:
		:param kwargs:
		"""
		self.boundaries = {}

	def add_boundary(self, label, bounds, shape):
		"""

		:param label:
		:param bounds:
		:param shape:
		"""
		if shape == RECT_BOUNDARY:
			b = RectangleBoundary(label, *bounds)
		elif shape == CIRCLE_BOUNDARY:
			b = CircleBoundary(label, *bounds)
		elif shape == ANNULUS_BOUNDARY:
			b = AnnulusBoundary(label, *bounds)
		self.boundaries[label] = b

	def add_boundaries(self, boundaries):
		"""

		:param boundaries:
		"""
		for b in boundaries:
			self.add_boundary(*b)

	def within_boundary(self, label, reference):
		"""

		:param label:
		:param reference:
		:return: :raise BoundaryError:
		"""
		reference = [int(n) for n in reference]
		if not self.boundaries[label].active:
			raise BoundaryError("Boundary '{0}' is not active for searching.".format(label))
		return self.boundaries[label].within(reference)

	def within_boundaries(self, reference, labels=None):

		"""

		:param reference:
		:param labels:
		:return: :raise:
		"""
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
		"""

		:param label:
		:raise KeyError:
		"""
		try:
			del (self.boundaries[label])
		except KeyError:
			raise KeyError("Key '{0}' not found; No such gaze boundary exists!".format(label))

	def clear_boundaries(self, preserve=[]):
		"""

		:param preserve:
		"""
		preserved = {}
		for i in preserve:
			preserved[i] = self.boundaries[i]
		self.boundaries = preserved

	def draw_boundary(self, label="*"):
		"""

		:param label:
		:return: :raise ValueError:
		"""
		raise NotImplementedError("Boundary drawing will be implemented in a future version.")

	def add_anonymous_boundary(self, bounds, shape):
		"""

		:param bounds:
		:param shape:
		:return:
		"""
		for i in range(0, len(self.boundaries)):
			label = 'anonymous_{0}'.format(i)
			if not label in self.boundaries:
				self.add_boundary(label, bounds, shape)
				return label

	def set_boundary_active(self, label):
		"""

		:param label:
		"""
		self.boundaries[label].active = True

	def set_boundary_inactive(self, label):
		"""

		:param label:
		"""
		self.boundaries[label].active = False


class Boundary(object):
	__name__ = "KLBoundary"
	__shape__ = None

	def __init__(self, label):
		"""

		:param label:
		"""
		super(Boundary, self).__init__()
		self.__label = label
		self.active = True

	@property
	def label(self):
		"""


		:return:
		"""
		return

	@property
	def shape(self):
		"""


		:return:
		"""
		return self.__shape__

	@property
	def bounds(self):
		"""


		:raise NotImplementedError:
		"""
		raise NotImplementedError

	@bounds.setter
	def bounds(self):
		"""


		:raise NotImplementedError:
		"""
		raise NotImplementedError

	@abc.abstractmethod
	def within(self, reference):
		"""

		:param reference:
		"""
		pass


class RectangleBoundary(Boundary):
	__name__ = "KLRectangleBoundary"
	__shape__ = RECT_BOUNDARY

	def __init__(self, label, p1, p2):
		"""

		:param label:
		:param p1:
		:param p2:
		"""
		super(RectangleBoundary, self).__init__(label)
		self.__p1 = None
		self.__p2 = None
		self.bounds = [p1, p2]
		self.__center = midpoint(*self.bounds)

	@property
	def bounds(self):
		"""

		:return:
		"""
		return [self.__p1, self.__p2]

	@bounds.setter
	def bounds(self, boundary_data):
		try:
			for i in boundary_data:
				iter(i)
			self.__p1 = boundary_data[0]
			self.__p2 = boundary_data[1]
		except (AttributeError, IndexError):
			raise TypeError("Intialization of RectangleBoundary expects 2-item sequence of x,y pairs.")

	@property
	def p1(self):
		"""

		:return:
		"""
		return self.__p1


	@property
	def p2(self):
		"""

		:return:
		"""
		return self.__p2

	def within(self, reference):
		"""

		:param reference:
		:return: :raise TypeError:
		"""
		if not iterable(reference):
			raise TypeError("within() expects a 2-item sequence; either an x,y pair, or amplitude, angle pair.")
		return self.__p1[0] <= reference[0] <= self.__p2[0] and self.__p1[1] <= reference[1] <= self.__p2[1]



class CircleBoundary(Boundary):
	__name__ = "KLCircleBoundary"
	__shape__ = CIRCLE_BOUNDARY

	def __init__(self, label, center, radius):
		"""

		:param label:
		:param center:
		:param radius:
		"""
		super(CircleBoundary, self).__init__(label)
		self.__r__ = None
		self.__c__ = None
		self.bounds = [center, radius]

	@property
	def bounds(self):
		"""


		:return:
		"""
		return [self.__c__, self.__r__]

	@bounds.setter
	def bounds(self, boundary_data):
		# try:
		"""

		:param boundary_data:
		:raise ValueError:
		"""
		if not iterable(boundary_data[0]):
		# except AttributeError:
			raise ValueError("Argument 'center' expects 2-item sequence (an x,y pair).")
		try:
			if boundary_data[1] < 0:
				raise ValueError
		except (TypeError, ValueError):
			raise ValueError("Argument 'radius' must be a positive number.")
		self.__c__ = boundary_data[0]
		self.__r__ = boundary_data[1]

	@property
	def center(self):
		"""


		:return:
		"""
		return self.__c__


	@property
	def radius(self):
		"""


		:return:
		"""
		return self.__r__

	def within(self, reference):
		"""

		:param reference:
		:return:
		"""
		try:
			d_xy = line_segment_len(reference, self.__c__)
		except TypeError:
			d_xy = reference
		return  d_xy < self.__r__


class AnnulusBoundary(Boundary):
	__name__ = "KLAnnulusBoundary"
	__shape__ = ANNULUS_BOUNDARY

	def __init__(self, label, center, radius, thickness):
		"""

		:param label:
		:param center:
		:param radius:
		:param thickness:
		"""
		super(AnnulusBoundary, self).__init__(label)
		self.__r_inner__ = None
		self.__r_outer__ = None
		self.__span_range__ = None
		self.__span__ = None
		self.__center__ = None
		self.bounds = [center, radius, thickness]

	@property
	def bounds(self):
		"""


		:return:
		"""
		return [self.__center__, self.__r_inner__, self.__r_outer__, self.__span__]

	@bounds.setter
	def bounds(self, boundary_data):
		"""

		:param boundary_data:
		:raise ValueError:
		"""
		try:
			iter(boundary_data[0])
		except AttributeError:
			raise ValueError("Argument 'center' expects 2-item sequence (an x,y pair).")
		try:
			for i in boundary_data[1:]:
				if i < 0: raise ValueError
		except (TypeError, ValueError):
			raise ValueError("Argument 'radius' must be a positive number.")

		self.__center__ = boundary_data[0]
		self.__r_outer__ = int(boundary_data[1])
		self.__span__ = int(boundary_data[2])
		self.__r_inner__ = self.__r_outer__ - self.__span__
		self.__span_range__ = range(self.__r_inner__, self.__r_outer__)

	@property
	def center(self):
		"""


		:return:
		"""
		return self.__center__

	@property
	def span(self):
		"""


		:return:
		"""
		return self.__span__

	@property
	def inner_radius(self):
		"""


		:return:
		"""
		return self.__r_inner__

	@property
	def outer_radius(self):
		"""


		:return:
		"""
		return self.__r_outer__

	def within(self, reference):
		"""

		:param reference:
		:return:
		"""
		d_xy = line_segment_len(reference, self.__center__) if iterable(reference) else reference
		return  int(d_xy) in self.__span_range__