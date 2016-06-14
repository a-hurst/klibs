__author__ = 'jono'

from KLBoundary import *
from KLExceptions import BoundaryError
# class KLBoundary  will inherit from KLObject


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

