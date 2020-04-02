__author__ = 'Jonathan Mulle & Austin Hurst'
from warnings import warn
from copy import copy
from collections import namedtuple
from os.path import exists
from time import time

import numpy as np
from PIL import Image
from PIL import ImageOps
import aggdraw

from math import floor, ceil
from klibs.KLConstants import *
from klibs.KLGraphics import _build_registrations
from klibs.KLUtilities import bool_to_int

e_string_type = "Argument '{0}' expected '{1}', got '{2}'."
e_string_iter = "Argument '{0}}' must be an iterable collection; {1} passed."
e_bad_behaviour_str = "Passed value for argument 'behaviour' not a recognized canvas behaviour."
e_not_rgba = "Argument '{0}' expected a container of RGB/RGBA values, or an RGBAColor object; {0} provided."

"""
These next few functions just wrap aggdraw's stupid API :S
"""
CANVAS_EXPAND = 0
CANVAS_CROP = 1
CANVAS_FIT = 2
CANVAS_STRETCH = 3

CANVAS_BEHAVIOURS = [CANVAS_EXPAND, CANVAS_CROP, CANVAS_FIT, CANVAS_STRETCH]
'''
Note: The 'shape' property of numpy arrays are given as (y,x) or (height, width); because it's the best descriptor, 
Canvas and CanvasLayer classes also use this term but defer to the more intuitive vernacular (x,y) or (width, height).
All interactions with numpy should be handled by these classes, and therefore the user-facing methods are entirely con-
sistent, but if you're reading this then it might save some confusion. 
'''


def np_shape_flip(shape_tuple):
	""" so fucking stupid """
	shape_tuple = list(shape_tuple)
	shape_tuple.reverse()
	return tuple(shape_tuple)


def canvas(width, height, mode='RGBA', background=(0, 0, 0, 0)):
	"""

	:param width:
	:param height:
	:param mode:
	:param background:
	:return:
	"""
	bg = []
	bg.append(n for n in background)
	if len(bg) == 3: bg.append(0)
	return aggdraw.Draw(mode, (width, height), tuple(background))


def ad_fill(color, opacity=255):
	"""

	:param color:
	:param opacity:
	:return:
	"""
	col = list()
	col.append(n for n in color)
	if len(col) == 4:
		opacity = col[3]
		col = col[0:2]
	else:
		col = color
	return aggdraw.Brush(tuple(col), opacity)


def ad_stroke(color, width=1, opacity=255):
	"""

	:param color:
	:param width:
	:param opacity:
	:return:
	"""
	col = list()
	col.append(n for n in color)
	if len(col) == 4:
		opacity = col[3]
		col = col[0:3]
	return aggdraw.Pen(color, width, opacity)


def grey_scale_to_alpha(source):
		"""

		:param source:
		:return: :raise TypeError:
		"""
		if type(source) is Canvas:
			source = source.render()
		elif type(source) is str:
			source = Canvas.magic_import(source)
		elif type(source) is not np.ndarray:
			raise TypeError("Argument 'mask' must be a Canvas, numpy.ndarray or a path string of an image file.")
		source[0: -1, 0: -1, 3] = source[0: -1, 0: -1, 0]
		return source


def rects_overlap(target_shape, dest_shape, origin=(0,0), registration=7, flip_shape=False):
	if flip_shape:
		target_shape = np_shape_flip(target_shape)
		dest_shape = np_shape_flip(dest_shape)
	origin = Canvas.reregister_origin(target_shape, dest_shape, registration, origin)
	try:
		assert (origin[0] + dest_shape[0] >= 0)
		assert (origin[0] < target_shape[0])
		assert (origin[1] + dest_shape[1] >= 0)
		assert (origin[1] < target_shape[1])
	except AssertionError:
		return False

	return True


def rect_containable(target_shape, dest_shape, origin=(0,0), registration=7, flip_shape=False):
	if flip_shape:
		target_shape = np_shape_flip(target_shape)
		dest_shape = np_shape_flip(dest_shape)
	origin = Canvas.reregister_origin(target_shape, dest_shape, registration, origin)
	try:
		assert (origin[0] + target_shape[0] >= dest_shape[0])
		assert (origin[1] + target_shape[1] >= dest_shape[1])
	except AssertionError:
		return False

	return True


Point = namedtuple('Point', ['x', 'y'])
RGBAColor = namedtuple('Color', ['red', 'green', 'blue', 'alpha'])


class Canvas(object):
	# TODO: wrap relevant pillow methods http://pillow.readthedocs.org/en/3.0.x/reference/ImageOps.html
	# TODO: make a 'chainable' decorator that returns the canvas object to make  jquery-style methods

	def __init__(self, height, width, background=None):
		try:
			all([type(dimension) is int for dimension in [height, width]])
		except AssertionError:
			raise ValueError("Both 'height' and 'width' arguments must be integers.")
		self._height = None
		self._width = None
		self._background = None
		self.background = background
		self.rendered = None
		self._width = height
		self._height = width
		self._layers = []
		self._layer_add_behaviour = CANVAS_EXPAND


	def __str__(self):
		return "klibs.Canvas, ({0} x {1}) at {2}".format(self.width, self.height, hex(id(self)))

	def _ensure_writeable(self, layer=NS_FOREGROUND):
		if layer == NS_FOREGROUND:
			try:
				self.foreground.setflags(write=1)
			except AttributeError:
				self.foreground = np.zeros((self.width, self.height, 4))
				self._ensure_writeable(NS_FOREGROUND)
		else:
			try:
				self.background.setflags(write=1)
			except AttributeError:
				self.background = np.zeros((self.width, self.height, 4))
				self._ensure_writeable(NS_BACKGROUND)

	def fetch_layer(self, layer):
		try:
			assert(type('layer') is str)
		except AssertionError:
			raise TypeError("fetch_layer() retrieves layers by name; str expected but {0} provided.".format(type(layer)))
		for l in self._layers:
			if l.name == layer:
				return l
		raise ValueError("No layer with name '{0}' exists in this Canvas object.".format(layer))

	@staticmethod
	def reregister_origin(target_shape, dest_shape, registration, origin=(0, 0), flip_shape=False):
		'''
		Relocates an assumed origin for placing the top-left corner of target_shape onto dest_shape to appropriate
		position on dest_shape given registration.

		:param target_shape:
		:param dest_shape:
		:param origin:
		:param registration:
		:param flip_shape:
		:return:
		'''
		if flip_shape:
			target_shape = np_shape_flip(target_shape)
			dest_shape = np_shape_flip(dest_shape)
		origin = list(origin)
		d_x = target_shape[0] - dest_shape[0]
		d_y = target_shape[1] - dest_shape[1]
		if registration in [8, 5, 2]:
			origin[0] += floor(d_x / 2.0)
		elif registration in [9, 6, 3]:
			origin[0] += d_x
		if registration in [4, 5, 6]:
			origin[1] += floor(d_y / 2)
		elif registration in [1, 2, 3]:
			origin[1] += d_y
		return Point(int(origin[0]), int(origin[1]))

	@staticmethod
	def magic_import(source):
		# first test for an extant numpy array
		try:
			assert(type(source) is np.ndarray)
			data = source
		except AssertionError:
			try:
				exists(source)
				data = Canvas.add_alpha_channel(np.array(Image.open(source)), skip_import=True)
			except IOError:
				raise IOError("Cannot identify image data in file '{0}'".format(source))
			except TypeError:
				try:
					data = source.render()
				except AttributeError:
					raise TypeError("Cannot identify image data from source.")

		return data.astype(np.float)

	@staticmethod
	def add_alpha_channel(data, alpha_value=255, skip_import=False):
		data = Canvas.magic_import(data)

		try:
			with_alpha = np.zeros((data.shape[0], data.shape[1], 4))
			with_alpha[:, :, :3] = data
			with_alpha[:, :, 3] = alpha_value
			return with_alpha
		except ValueError:
			return data


	def crop(self, shape, origin=(0,0), data=None):
		"""
			Crops either entire Canvas object (if not data is provided) or passed data (a Canvas, NumpySurface, ndarray,
			path to image file, or aggdraw canvas) to provided size starting at provided origin.

			If crop would have no effect (ie. size is outside of canvas bounds given origin) a warning is thrown.

			If data is provided, a cropped version is returned. Otherwise the canvas object returns itself to allow
			method chaining.
			"""
		if data is None:
			target_shape = self.shape
		else:
			data = Canvas.magic_import(data)
			target_shape = (data.shape[1], data.shape[0])
		try:
			assert(rects_overlap(shape, (target_shape[1], target_shape[0]), origin, BL_TOP_LEFT))
		except AssertionError:
			warn("Canvas.crop() had no effect as the region to be masked is outside the image bounds.")

		try:
			assert(shape[0] < target_shape[1] or shape[1] < target_shape[0])
		except AssertionError:
			warn("Canvas.crop() had no effect as the output size is larger than ")

		if data is None:
			for l in self._layers:
				l.crop(shape, origin)
			self._width, self._height = shape
			return self

		return (data[origin[1]:-1, origin[0]:-1, :])[0:shape[1], 0:shape[0], :]

	def add_layer(self, content, origin=(0, 0), z_index=None, name='layer_{0}', registration=BL_TOP_LEFT):
		print content, origin
		z_index = z_index if z_index is not None else self.layer_count
		name = name.format(len(self._layers))  # does nothing if any other string is passed
		try:
			assert(type(name) is str)
		except AssertionError:
			raise TypeError("Argument 'name' must be a string or None; {0} provided.".format(type(name)))

		try:
			assert(z_index <= self.layer_count)
		except AssertionError:
			raise IndexError("Assigned z-index does not exist (too few layers).")
		try:
			assert(type(z_index) is int)
		except AssertionError:
			raise IndexError("Argument 'z_index' must be an integer or None; {0} provided.".format(type(z_index)))

		content = Canvas.magic_import(content)
		name = 'layer_{0}'.format(self.layer_count) if name is None else name
		origin = Canvas.reregister_origin(np_shape_flip(content.shape), self.shape, registration, origin)
		try:
			if (z_index == self.layer_count):
				l = CanvasLayer(name, self, content,origin, registration)
				self._layers.append(l)
		except ValueError as e:
			raise e

		return self._update_shape()


	def scale(self, size):
		# todo: incorporate for individual layers
		if self.empty:
			warn("Scale operation not performed as no layers were found to have content.")

		for layer in self._layers:
			layer.scale(size)
		self.resize(size)

		return self

	def rotate(self, angle, layer=None):
		if self.empty:
			return

		if layer is None:
			for l in self._layers:
				l.rotate(angle)
		self._update_shape()

		return self


	def resize(self, size, registration=BL_TOP_LEFT):
		"""
		Changes the size of the canvas (and all layers) to new size; does NOT scale content. If size is larger than it
		had previously been, newly created pixels will have the layer's fill color.

		:param size:
		:param fill: Transparent by default, can be any rgba value
		:return:
		"""
		try:
			assert(size[0] <= self.width)
			assert(size[1] <= self.height)
		except AssertionError:
			warn('Canvas {0} was smaller after resize; some clipping has occurred.')
		for layer in self._layers:
			layer.resize(size, registration)

		return self

	def render(self):
		# todo: add functionality for not using a copy, ie. permanently render
		"""

		:param prerendering:  Legacy argument; left in for backwards compatibility
		:return: :raise ValueError:
		"""
		start = time()
		if self.empty:
			raise ValueError('Nothing to render; Canvas has been initialized but no layer content has been added.')

		render_surface = np.zeros((self.height, self.width, 4), dtype=np.float)
		if len(self._layers) is 1:
			self.rendered = self._layers[0].content.astype(np.uint8)
		else:
			# This bit composites layers from the "top" "down", as in last-in-first-out, where
			for i in range(self.layer_count, 0, -1):
				l = self._layers[i-1]
				if i == self.layer_count:
					render_surface[0: self.shape[1], 0: self.shape[0]] = l.render()
					continue
				# get the regions to be composited
				else:
					bg = Image.fromarray(l.render().astype(np.uint8))
					fg = Image.fromarray(copy(render_surface[0: self.shape[1], 0: self.shape[0]]).astype(np.uint8))
					render_surface[0: self.shape[1], 0: self.shape[0]] = Image.alpha_composite(bg, fg)

			self.rendered = render_surface.astype(np.uint8)
		elapsed = time() - start
		if elapsed > 0.04:
			warn('Canvas took {0}ms to render.'.format(elapsed))
		return self.rendered

	def _update_shape(self):
		for l in self._layers:
			try:
				self._width = l.width + l.origin[0] if self._width < (l.width + l.origin[0]) else self._width
				self._height = l.height + l.origin[1] if self._height < (l.height + l.origin[1]) else self._height
			except AttributeError:
				pass
		try:
			for l in self._layers:
				l.reshape(self.shape, self.layer_add_behaviour)
		except NameError:
			pass

		return self

	@property
	def shape(self):
		return (self.width, self.height)

	@property
	def height(self):
		return self._height


	@property
	def width(self):
		return self._width


	@property
	def shape(self):
		return (self.width, self.height)

	@property
	def layers(self):
		return self._layers

	@property
	def layer_count(self):
		return len(self._layers)

	@property
	def empty(self):
		return all([layer.content is None for layer in self._layers])

	@property
	def layer_add_behaviour(self):
		return self._layer_add_behaviour


	@layer_add_behaviour.setter
	def layer_add_behaviour(self, behaviour):
		try:
			assert(behaviour in [CANVAS_EXPAND, CANVAS_CROP, CANVAS_FIT, CANVAS_STRETCH])
			self._layer_add_behaviour = behaviour
		except AssertionError:
			raise ValueError(e_bad_behaviour_str)


class CanvasLayer(object):

	def __init__(self, name, canvas, content, origin, registration):
		super(CanvasLayer, self).__init__()
		self.name = name
		self.canvas = canvas
		self._origin = origin
		self._opacity = 1.0
		self._raw_content = content	 # original passed data, independent of canvas shape
		self._content = None  # content placed in an np array with shape matching the canvas
		self._mask = None
		self._mask_origin = None
		self._render = None
		self._z_index = 1
		self._visible = True
		self._writeable = False
		self._canvas_scale_behaviour = True
		self._registration = registration
		self._bg_fill = RGBAColor(0, 0, 0, 0)

		self._init_content()

	def _init_content(self):
		raw_shape = list(self._raw_content.shape)
		raw_shape[0] += self.origin[1]
		raw_shape[1] += self.origin[0]
		width = raw_shape[1] if self.canvas.width < raw_shape[1] else self.canvas.width
		height = raw_shape[0] if self.canvas.height < raw_shape[0] else self.canvas.height
		self._content = np.zeros([height, width, 4])
		c_x1, c_y1 = self.origin
		c_x2 = c_x1 + self._raw_content.shape[1]
		c_y2 = c_y1 + self._raw_content.shape[0]
		self._content[c_y1:c_y2, c_x1:c_x2, :] = self._raw_content
		print "layer '{0}' init shape: {1}".format(self.name, self._content.shape)

	def __str__(self):
		return "klibs.KLGraphics.CanvasLayer, ('{0}', {1} x {2}) at {3}".format(self.name, self.width, self.height, hex(id(self)))

	def render(self):
		if not self._visible:
			return np.zeros([self.height, self.width,4])

		self._apply_mask()
		self._render = self._render.astype(np.float)
		if self.opacity < 1:
			self._render = self._render * np.full((self.shape[1], self.shape[0], 4), [1.0, 1.0, 1.0, self.opacity])
		return self._render

	def _apply_mask(self):
		content = copy(self._content)
		if self._mask is None:
			self._render = content
			return
		alpha_map = np.ones(self._mask.shape[:-1]) * 255 - self._mask[..., 3]
		mo_x1 = self._mask_origin[0]
		mo_x2 = alpha_map.shape[1] + self._mask_origin[0]
		mo_y1 = self._mask_origin[1]
		mo_y2 = alpha_map.shape[0] + self._mask_origin[1]
		flat_alpha_map = alpha_map.flatten()
		flat_content = content[mo_y1: mo_y2, mo_x1: mo_x2, 3].flatten()
		zipped_arrays = zip(flat_alpha_map, flat_content)
		flat_masked_region = np.asarray([min(x, y) for x, y in zipped_arrays])
		masked_region = flat_masked_region.reshape(alpha_map.shape)
		content[mo_y1: mo_y2, mo_x1: mo_x2, 3] = masked_region
		self._render = content

	def _write_check(self):
		if not self._writeable:
			raise RuntimeError("Operation not permitted; CanvasLayer object '{0}' not writeable.".format(self.name))

	def crop(self, shape, origin):
		self._content = (self._content[origin[1]:, origin[0]:, :])[0:shape[1], 0:shape[0], :]

	def move(self):
		pass

	def fill(self, color):
		pass

	def clear(self):
		pass

	def scale(self, size):
		if self._content is None:
			return
		self._content = Image.fromarray(self._content.astype(np.uint8)).resize(size, Image.ANTIALIAS)

	def flip_x(self):
		pass

	def flip_y(self):
		pass

	def invert(self):
		pass

	def rotate(self, angle):
		np_content = Image.fromarray(self._content.astype(np.uint8))
		rotated = np_content.rotate(angle)
		self._content = np.asarray(rotated)
		self.canvas._update_shape()

	def write(self, data, registration=7, location=(0,0)):
		self._write_check()
		data = Canvas.magic_import(data)
		# ok, first make sure data falls on canvas


	def reshape(self, shape, behaviour=CANVAS_EXPAND):
		if tuple(shape) == self.shape: return
		print 'reshaping {0} from {1} to {2}'.format(self.name, self.shape, shape)
		# create some empty arrays of the new dimensions and ascertain clipping values if needed
		output = np.zeros((shape[1], shape[0], 4), dtype=np.float)  # ie. new foreground
		if behaviour == CANVAS_EXPAND:
			x1, y1 = self.origin
			x2 = x1 + self.width
			y2 = y1 + self.height
			print x1,x2, y1, y2
			output[y1:y2, x1:x2] = self._content

		self._content = output


	@property
	def content(self):
		return self._content

	@property
	def opacity(self):
		return self._opacity

	@opacity.setter
	def opacity(self, value):
		try:
			if value in [0,1]: # just giving users a break for having skipped a decimal
				self._opacity = float(value)
			else:
				assert(type(value) is float and 0.0 <= value <= 1.0)
				self._opacity = value
		except AssertionError:
			raise ValueError("Opacity must be greater than or equal to 0.0 and less than or equal to 1.0")

	@property
	def visible(self):
		return self._visible

	@visible.setter
	def visible(self, val):
		try:
			assert(type(val) is bool)
			self._visible = val
		except AssertionError:
			raise TypeError(e_string_type.format('visible', 'bool', type(val)))

	@property
	def writeable(self):
		return self._writeable

	@writeable.setter
	def writeable(self, val):
		try:
			assert(type(val) is bool)
			self._content.setflags(write=bool_to_int(val))

			def _ensure_writeable__(self, layer=NS_FOREGROUND):
				if layer == NS_FOREGROUND:
					try:
						self.foreground.setflags(write=1)
					except AttributeError:
						self.foreground = np.zeros((self.width, self.height, 4))
						self._ensure_writeable(NS_FOREGROUND)
				else:
					try:
						self.background.setflags(write=1)
					except AttributeError:
						self.background = np.zeros((self.width, self.height, 4))
						self._ensure_writeable(NS_BACKGROUND)
			self._writeable = val
		except AssertionError:
			raise TypeError(e_string_type.format('writable', 'bool', type(val)))

	@property
	def canvas_scale_behaviour(self):
		return self._canvas_scale_behaviour


	@canvas_scale_behaviour.setter
	def canvas_scale_behaviour(self, behaviour):
		try:
			assert (behaviour in CANVAS_BEHAVIOURS)
			self._canvas_scale_behaviour = behaviour
		except AssertionError:
			raise TypeError(e_bad_behaviour_str)

	@property
	def name(self):
		return self._name

	@name.setter
	def name(self, val):
		try:
			assert (type(val) is str)
			self._name = val
		except AssertionError:
			raise TypeError(e_string_type.format('name', 'str', type(val)))

	@property
	def mask(self):
		return self._mask

	@mask.setter
	def mask(self, mask_data):
		"""
		1) test if mask falls on layer
		2) create an empty np array of layer size
		3) math out the fraction of the mask that falls on the later
		4) merge the mask to the np array

		"""
		content, registration, location = mask_data
		content = Canvas.magic_import(content)
		if rects_overlap(content, self.content, location, registration):
			self._mask = content
		else:
			warn("Mask data was not set because passed content and layer contents do not overlap.")

	@property
	def origin(self):
		return self._origin


	@property
	def height(self):
		return self._content.shape[0]


	@property
	def width(self):
		return self._content.shape[1]


	@property
	def shape(self):
		return (self._content.shape[1], self._content.shape[0])

	@property
	def registration(self):
		return self._registration