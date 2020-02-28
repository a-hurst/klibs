__author__ = 'Jonathan Mulle & Austin Hurst'

from copy import copy
from collections import namedtuple
from os.path import exists

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


def add_alpha_channel(numpy_array, alpha_value=255):
	try:
		with_alpha = np.zeros((numpy_array.shape[0], numpy_array.shape[1], 4))
		with_alpha[:, :, :3] = numpy_array
		with_alpha[:, :, 3] = alpha_value
		return with_alpha
	except ValueError:
		return numpy_array
	# try:
	# 	if numpy_array.shape[2] == 3:
	# 		return numpy.insert(numpy_array, 3, alpha_value, 2)
	# 	else:
	# 		return numpy_array
	# except IndexError:
	# 	raise ValueError("Invalid data supplied; too few dimensions or wrong data type.")


def import_image_file(path):
		return add_alpha_channel(np.array(Image.open(path)))


def grey_scale_to_alpha(source):
		"""

		:param source:
		:return: :raise TypeError:
		"""
		if type(source) is Canvas:
			source = source.render()
		elif type(source) is str:
			source = import_image_file(source)
		elif type(source) is not np.ndarray:
			raise TypeError("Argument 'mask' must be a Canvas, numpy.ndarray or a path string of an image file.")
		source[0: -1, 0: -1, 3] = source[0: -1, 0: -1, 0]
		return source


def rects_overlap(target_shape, dest_shape, origin=(0, 0), registration=7):
	origin = Canvas.reregister_origin(dest_shape, origin, registration)
	try:
		assert (origin[0] + dest_shape[0] >= 0)
		assert (origin[0] < target_shape[0])
		assert (origin[1] + dest_shape[1] >= 0)
		assert (origin[1] < target_shape[1])
	except AssertionError:
		return False

	return True


Point = namedtuple('Point', ['x', 'y'])
RGBAColor = namedtuple('Color', ['red', 'green', 'blue', 'alpha'])


class Canvas(object):
	# todo: save states! save diffs between operations! so cool and unnecessary!
	# todo: default alpha value for render
	# todo: fg/bg dichotomy stupid and unwieldy; just use indexed layers

	def __init__(self, height, width):
		try:
			all([type(dimension) is int for dimension in [height, width]])
		except AssertionError:
			raise ValueError("Both 'height' and 'width' argument must be integers.")
		self._height = None
		self._width = None
		self._bg_color__ = None
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

	def _fetch_layer(self, layer):
		if layer == NS_FOREGROUND:
			if self.foreground is not None:
				return self.foreground
			else:
				raise ValueError("klibs.NS_FOREGROUND given for 'layer' argument, but foreground attribute is not set.")
		elif layer == NS_BACKGROUND:
			if self.background is not None:
				return self.background
			else:
				raise ValueError("klibs.NS_BACKGROUND given for 'layer' argument, but background attribute is not set.")
		else:
			raise TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")

	@staticmethod
	def reregister_origin(shape, origin, registration):
		origin = list(origin)
		if registration in [8, 5, 2]:
			origin[0] += floor(shape[0] / 2)
		elif registration in [9, 6, 3]:
			origin[0] += shape[0]
		if registration in [4, 5, 6]:
			origin[1] += floor(shape[1] / 2)
		elif registration in [1, 2, 3]:
			origin[1] += shape[1]
		return int(origin[0]), int(origin[1])

	@staticmethod
	def magic_import(source):
		# first test for an extant numpy array
		try:
			assert(type(source) is np.ndarray)
			data = source
		except AssertionError:
			try:
				exists(source)
				data = add_alpha_channel(np.array(Image.open(source)))
			except IOError:
				raise IOError("Cannot identify image data in file '{0}'".format(source))
			except TypeError:
				try:
					data = source.render()
				except AttributeError:
					raise TypeError("Cannot identify image data from source.")

		return data.astype(np.float)


	@staticmethod
	def add_alpha_channel(data, alpha_value=255):
		data = Canvas.magic_import(data)

		try:
			with_alpha = np.zeros((data.shape[0], data.shape[1], 4))
			with_alpha[:, :, :3] = data
			with_alpha[:, :, 3] = alpha_value
			return with_alpha
		except ValueError:
			return data


	@staticmethod
	def crop(size, data, origin=(0, 0), registration=BL_TOP_LEFT):
		"""
			Crops either entire Canvas object (if not data is provided) or passed data (a Canvas, NumpySurface, ndarray,
			path to image file, or aggdraw canvas) to provided size starting at provided origin.

			If crop would have no effect (ie. size is outside of canvas bounds given origin) a warning is thrown.

			If data is provided, a cropped version is returned. Otherwise the canvas object returns itself to allow
			method chaining.
			"""

		if type(data) is Canvas:
			data.__layers = [l.crop(size, origin) for l in data.__layers]
			return data

		data = Canvas.magic_import(data)
		origin = Canvas.reregister_origin(data[1], origin)

		try:
			assert(rects_overlap(size, (data.shape[1], data.shape[0]), origin, registration))
		except AssertionError:
			raise Warning("Canvas.crop() had no effect as the region to be masked is outside the image bounds.")

		try:
			assert(size[0] < data.shape[1] or size[1] < data.shape[0])
		except AssertionError:
			raise Warning("Canvas.crop() had no effect as the output size is larger than ")

		return (data[origin[1]:-1, origin[0]:-1, 4])[0:size[1], 0:size[0], 4]


	def add_layer(self, content, origin=(0, 0), z_index=None, name='layer_{0}', registration=BL_TOP_LEFT):
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

		content = self.magic_import(content)
		name = 'layer_{0}'.format(self.layer_count) if name is None else name

		if (z_index == self.layer_count):
			self._layers.append(CanvasLayer(name, self, content))

		return self._update_shape()

	def write(self, source, layer, registration=BL_TOP_LEFT, location=(0, 0), behaviour=CANVAS_EXPAND):
		# todo: implement layer logic here
		"""

		:param source:
		:param layer:
		:param registration:
		:param location:
		:raise ValueError:
		"""
		# try:
		# 	source.foreground = source.foreground.astype(np.uint8)
		# 	source = source.render()
		# except AttributeError:
		# 	pass
		# try:
		# 	source = add_alpha_channel(source)
		# except:
		# 	raise TypeError("Argument 'source' must be either of klibs.Canvas or numpy.ndarray.")
		source = self.magic_import(source)

		source_height = source.shape[0]
		source_width = source.shape[1]

		registration = _build_registrations(source_height, source_width)[registration]
		location = (int(location[0] + registration[0]), int(location[1] + registration[1]))

		# don't attempt the blit if source can't fit
		if behaviour is None:
			if source_height > self.height or source_width > self.width:
				e_msg = "Source ({0} x {1}) is larger than destination ({2} x {3})".format(source_width, source_height, self.width, self.height)
				raise ValueError(e_msg)
			elif source_height + location[1] > self.height or source_width + location[0] > self.width:
				raise ValueError("Source cannot be blit to location; destination bounds exceeded.")
		x1 = location[0]
		x2 = location[0] + int(source_width)
		y1 = location[1]
		y2 = location[1] + int(source_height)
		# print "Position: {0}: ".format(location)
		# print "Blit Coords: {0}: ".format([y1,y2,x1,x2])

		self._ensure_writeable(layer)
		# todo: find out why this won't accept a 3rd dimension (ie. color)
		if behaviour == "resize":
			if source_width > self.width: self.resize([self.height, source_width])
			if source_height > self.height: self.resize([self.width, source_height])
		# todo: make a "clip" behaviour
		# print "ForegroundShape: {0}, SourceShape: {1}".format(self.foreground.shape, source.shape)
		blit_region = self.foreground[y1: y2, x1: x2, :]
		# print "Blit_region of fg: {0}".format(blit_region.shape)
		if layer == NS_FOREGROUND:
			self.foreground[y1: y2, x1: x2, :] = source
		else:
			self.background[y1: y2, x1: x2] = source

		return self

	def scale(self, size, layer=None):
		# TODO: expand this considerably;  http://pillow.readthedocs.org/en/3.0.x/reference/ImageOps.html
		if self.empty:
			raise Warning("Scale operation not performed as no layers were found to have content.")

		for layer in self._layers:
			layer.scale(size)
		self.resize(size)

		return self

	def rotate(self, angle, layer=None):
	# TODO: expand this considerably;  http://pillow.readthedocs.org/en/3.0.x/reference/ImageOps.html
		if not self.has_content:
			return

		if layer == NS_FOREGROUND or layer is None:
			try:
				layer_image = Image.fromarray(self.foreground.astype(np.uint8))
				scaled_image = layer_image.Image.rotate(angle, Image.ANTIALIAS)
				self.foreground = np.asarray(scaled_image)
			except AttributeError as e:
				if str(e) != "'NoneType' object has no attribute '__array_interface__'":
					raise e
			except TypeError:
				pass
		self._update_shape()
		return self

	def get_pixel_value(self, location, layer=NS_FOREGROUND):
		"""

		:param location:
		:param layer:
		:return:
		"""
		if self.location_in_layer_bounds(location, layer):
			return self._fetch_layer(layer)[location[1]][location[0]]
		else:
			return False

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
			raise Warning('Canvas {0} was smaller after resize; some clipping has occurred.')
		for layer in self._layers:
			layer.resize(size, registration)

		return self

	def render(self, prerendering=False):
		# todo: add functionality for not using a copy, ie. permanently render
		"""

		:param prerendering:  Legacy argument; left in for backwards compatibility
		:return: :raise ValueError:
		"""

		if self.empty:
			raise ValueError('Nothing to render; Canvas has been initialized but no layer content has been added.')

		render_surface = np.zeros((self.height, self.width, 4), dtype=np.float)
		self.render_steps = []
		if len(self._layers) is 1:
			self.rendered = self._layers[0].content.astype(np.uint8)
		else:
			passes = 0
			for l in self._layers:
				passes += 1
				# get the regions to be composited
				fg = l.render()
				l_x1, l_y1 = l.origin
				l_x2 = l_x1 + fg.shape[1]
				l_y2 = l_y1 + fg.shape[0]
				bg = copy(render_surface[l_y1: l_y2, l_x1: l_x2]).astype(np.float)
				self.render_steps.append([bg, 'render_surface composite region'])
				self.render_steps.append([fg, l.name])
				# Extract the RGB channels
				fg_rgb = fg[..., :3]
				bg_rgb = bg[..., :3]

				# Extract the alpha channels and normalise to range 0.1
				fg_alpha = fg[..., 3] / 255.0
				bg_alpha = bg[..., 3] / 255.0

				# Work out resultant alpha channel
				comp_alpha = bg_alpha + fg_alpha * (1 - bg_alpha)

				# Work out resultant RGB
				fg_serialized = fg_rgb * fg_alpha[..., np.newaxis]
				bg_serialized = bg_rgb * bg_alpha[..., np.newaxis]
				# comp_rgb = (bg_serialized + fg_serialized * (1 - bg_alpha[..., np.newaxis])) / comp_alpha[..., np.newaxis]
				comp_rgb = (bg_rgb * bg_alpha[..., np.newaxis] + fg_rgb * fg_alpha[..., np.newaxis] * (1 - bg_alpha[..., np.newaxis])) / comp_alpha[..., np.newaxis]
				# Merge RGB and alpha (scaled back up to 0..255) back into single image
				# composite = np.dstack((comp_rgb, comp_alpha * 255)).astype(np.uint8)
				composite = np.dstack((comp_rgb, comp_alpha * 255)).astype(np.uint8)

				render_surface[l_y1: l_y2, l_x1: l_x2] = composite
				self.render_steps.append([copy(render_surface), 'render_surface, pass {0}'.format(passes)])

			self.rendered = render_surface.astype(np.uint8)
		return self.rendered

	def _update_shape(self):
		for l in self._layers:
			try:
				if self._width < l.width:
					self._width = l.width
					update_layers = True
				if self._height < l.height:
					self._height = l.height
					update_layers = True
			except AttributeError:
				pass
		try:
			if update_layers:
				for l in self._layers:
					l.reshape(self.shape, 5, self.layer_add_behaviour)
		except NameError:
			pass

		return self


	@property
	def height(self):
		return self._height


	@property
	def width(self):
		return self._width


	@property
	def shape(self):
		return [self.width, self.height]

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

	def __init__(self, name, canvas, content, origin=(0,0)):
		super(CanvasLayer, self).__init__()
		self.name = name
		self.canvas = canvas
		self._origin = origin
		self._position = (0, 0)
		self._opacity = 1.0
		self._content = content
		self._mask = None
		self._mask_origin = None
		self._render = None
		self._z_index = 1
		self._visible = True
		self._writeable = False
		self._canvas_scale_behaviour = True
		self._bg_fill = RGBAColor(0, 0, 0, 0)

		if self.width < self.canvas.width or self.height < self.canvas.height:
			self.reshape(self.canvas.shape)

	def __str__(self):
		return "klibs.KLGraphics.CanvasLayer, ('{0}', {1} x {2}) at {3}".format(self.name, self.width, self.height, hex(id(self)))

	def render(self):
		if not self._visible:
			return np.zeros([self.height, self.width,4])

		self._apply_mask()

		return self._render.astype(np.float)

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

	def rotate(self):
		pass

	def write(self, data, registration=7, location=(0, 0)):
		self._write_check()
		data = Canvas.magic_import(data)
		# ok, first make sure data falls on canvas


	def reshape(self, shape, registration=7, behaviour=CANVAS_EXPAND):
		if list(self.shape) == list(shape):
			return
		print 'reshaping {0} from {1} to {2}'.format(self.name, self.shape, shape)
		# create some empty arrays of the new dimensions and ascertain clipping values if needed
		output = np.zeros((shape[1], shape[0], 4), dtype=np.float)  # ie. new foreground
		if behaviour == CANVAS_EXPAND:
			x1, y1 = Canvas.reregister_origin(shape, (0, 0), registration)
			x2 = x1 + self.shape[0]
			y2 = y1 + self.shape[1]
			print type(self._content), x1, x2, y1, y2
			output[y1:y2, x1:x2] = self._content

		self._content = output


	@property
	def content(self):
		return self._content

	@property
	def opacity(self):
		pass

	@property
	def position(self):
		return self._position


	@property
	def position(self, coords):
		try:
			iter(coords)
			assert(all([type(d) is int for d in coords]))
			self._position = coords
		except TypeError:
				raise TypeError(e_string_iter.format("Coords", type(coords)))

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
			raise Warning("Mask data was not set because passed content and layer contents do not overlap.")

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
		return [self._content.shape[1], self._content.shape[0]]