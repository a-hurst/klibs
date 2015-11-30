import os
import numpy
from copy import copy
from PIL import Image
from PIL import ImageOps
from KLUtilities import *
from KLConstants import *
import aggdraw

"""
These next few functions just wrap aggdraw's stupid API :S
"""


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


def from_aggdraw_context(draw_context):
	"""

	:param draw_context:
	:return:
	"""
	draw_context_bytes = Image.frombytes(draw_context.mode, draw_context.size, draw_context.tostring())
	return NumpySurface(numpy.asarray(draw_context_bytes))


def add_alpha_channel(numpy_array, alpha_value=255):
	# todo: stop throwing an error when there's an empty array
	if len(numpy_array[2][0]) == 3:
		return numpy.insert(numpy_array, 3, alpha_value, 2)
	else:
		return numpy_array


def import_image_file(path):
		return add_alpha_channel(numpy.array(Image.open(path)))


class NumpySurface(object):
	# todo: save states! save diffs between operations! so cool and unnecessary!
	# todo: default alpha value for render

	def __init__(self, foreground=None, background=None, fg_offset=None, bg_offset=None, width=None, height=None):
		self.__foreground = None
		self.__foreground_offset = None
		self.__foreground_mask = None
		self.__foreground_unmask = None
		self.__fg_mask_position = None
		self.__background = None
		self.__background_offset = None
		self.__background_mask = None
		self.__background_unmask = None
		self.__bg_mask_position = None
		self.__height = None
		self.__width = None
		self.__bg_color = None
		self.__prerender = None
		self.bg = None
		self.fg = None
		self.bg_offset = None
		self.fg_offset = None
		self.width = width
		self.height = height

		self.init_bg_offsets(fg_offset, bg_offset)
		self.init_layers(foreground, background)
		self.init_canvas()

	def init_bg_offsets(self, fg_position, bg_position):
		# do positions first in case a resize is required during bg & fg processing
		if fg_position is not None:
			try:
				iter(fg_position)
				self.__foreground_offset = fg_position
			except:
				raise ValueError("Argument 'fg_position' must be None or iterable x, y coordinates.")
		else:
			self.__foreground_offset = (0, 0)

		if bg_position is not None:
			try:
				iter(bg_position)
				self.__background_offset = bg_position
			except:
				raise ValueError("Argument 'bg_position' must be None or iterable x, y coordinates.")
		else:
			self.__background_offset = (0, 0)

		# just some aliases to shorten lines later (render, resize, etc.)
		self.bg = self.__background
		self.fg = self.__foreground
		self.bg_offset = self.__background_offset
		self.fg_offset = self.__foreground_offset

	def init_layers(self, foreground, background):
		if background is not None:
			try:
				self.background = add_alpha_channel(background)
			except AttributeError:
				self.layer_from_file(background, True, self.fg_offset)
			except TypeError:
				background = numpy.asarray(Image.frombytes(background.mode, background.size, background.tostring()))
				self.background = add_alpha_channel(background)

		if foreground is not None:
			self.foreground = add_alpha_channel(foreground)
			try:
				self.foreground = add_alpha_channel(foreground)
			except AttributeError:
				self.layer_from_file(foreground, True, self.fg_offset)
			except TypeError:
				try:
					foreground.render()  # if it renders, it's a KLDraw.Drawbject, which returns a Numpy
					foreground = foreground.surface
				except AttributeError:
					pass
				foreground = numpy.asarray(Image.frombytes(foreground.mode, foreground.size, foreground.tostring()))
				self.foreground = add_alpha_channel(foreground)

	def init_canvas(self):
		if all([self.background, self.foreground, self.width, self.height]) is None:
			self.foreground = numpy.zeroes((1,1,4))
			self.background = numpy.zeroes((1,1,4))
		else:
			if self.foreground is None:
				try:
					fg_width = self.background.shape[1] if self.background.shape[1] > self.width else self.width
				except AttributeError:
					fg_width = self.width
				try:
					fg_height = self.background.shape[0] if self.background.shape[0] > self.height else self.height
				except AttributeError:
					fg_height = self.height

				self.foreground = numpy.zeros((fg_height, fg_width, 4))
			if self.background is None:
				try:
					bg_width = self.foreground.shape[1] if self.foreground.shape[1] > self.width else self.width
				except AttributeError:
					bg_width = self.width
				try:
					bg_height = self.foreground.shape[0] if self.foreground.shape[0] > self.height else self.height
				except AttributeError:
					bg_height = self.height

				self.background = numpy.zeros((bg_height, bg_width, 4))
		self.__update_shape()

	def __str__(self):
		return "klibs.NumpySurface, ({0} x {1}) at {2}".format(self.width, self.height, hex(id(self)))

	def blit(self, source, layer=NS_FOREGROUND, registration=7, position=(0, 0), behavior=None):
		# todo: implement layer logic here
		"""

		:param source:
		:param layer:
		:param registration:
		:param position:
		:raise ValueError:
		"""
		source_height = None
		source_width = None

		try:
			source = source.render()
		except:
			pass
		try:
			source = add_alpha_channel(source)
		except:
			raise TypeError("Argument 'source' must be either of klibs.NumpySurface or numpy.ndarray.")
		source_height = source.shape[0]
		source_width = source.shape[1]

		# convert english location strings to x,y coordinates of destination surface
		if type(position) is str:
			position = absolute_position(position, self)

		registration = build_registrations(source_height, source_width)[registration]
		position = (position[0] + registration[0], position[1] + registration[1])

		# don't attempt the blit if source can't fit
		if behavior is None:
			if source_height > self.height or source_width > self.width:
				raise ValueError("Source is larger than destination in one or more dimensions.")
			elif source_height + position[1] > self.height or source_width + position[0] > self.width:
				raise ValueError("Source cannot be blit to position; destination bounds exceeded.")
		x1 = position[0]
		x2 = position[0] + source_width
		y1 = position[1]
		y2 = position[1] + source_height
		# print "Position: {0}: ".format(position)
		# print "Blit Coords: {0}: ".format([y1,y2,x1,x2])

		self.__ensure_writeable(layer)
		# todo: find out why this won't accept a 3rd dimension (ie. color)
		if behavior == "resize":
			if source_width > self.width: self.resize([self.height, source_width])
			if source_height > self.height: self.resize([self.width, source_height])
		# todo: make a "clip" behavior
		# print "ForegroundShape: {0}, SourceShape: {1}".format(self.foreground.shape, source.shape)
		blit_region = self.foreground[y1: y2, x1: x2]
		# print "Blit_region of fg: {0}".format(blit_region.shape)
		if layer == NS_FOREGROUND:
			self.foreground[y1: y2, x1: x2] = source
		else:
			self.background[y1: y2, x1: x2] = source

	def __ensure_writeable(self, layer=NS_FOREGROUND):
		if layer == NS_FOREGROUND:
			try:
				self.foreground.setflags(write=1)
			except AttributeError:
				self.foreground = numpy.zeros((self.width, self.height, 4))
				self.__ensure_writeable(NS_FOREGROUND)
		else:
			try:
				self.background.setflags(write=1)
			except AttributeError:
				self.background = numpy.zeros((self.width, self.height, 4))
				self.__ensure_writeable(NS_BACKGROUND)

	def __fetch_layer(self, layer):
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

	def scale(self, size, layer=None):
		# TODO: expand this considerably;  http://pillow.readthedocs.org/en/3.0.x/reference/ImageOps.html
		if not self.has_content():
			return

		if layer == NS_FOREGROUND or layer is None:
			try:
				layer_image = Image.fromarray(self.foreground)
				scaled_image = ImageOps.fit(layer_image, size)
				self.foreground = numpy.asarray(scaled_image)
			except AttributeError as e:
				if e.message != "'NoneType' object has no attribute '__array_interface__'":
					raise e
			except TypeError:
				pass

		if layer == NS_BACKGROUND or layer is None:
			try:
				layer_image = Image.fromarray(self.background)
				scaled_image = ImageOps.fit(layer_image, size)
				self.background = numpy.asarray(scaled_image)
			except AttributeError as e:
				if e.message != "'NoneType' object has no attribute '__array_interface__'":
					raise e
			except TypeError:
				pass

		self.resize(size)

	def layer_from_file(self, image, layer=NS_FOREGROUND, position=None):
		# todo: better error handling; check if the file has a valid image extension, make sure path is a valid type
		"""

		:param image:
		:param layer:
		:param position:
		:return: :raise TypeError:
		"""
		image_content = add_alpha_channel(numpy.array(Image.open(image)))

		if layer == NS_FOREGROUND:
			self.foreground = image_content
		elif layer == NS_BACKGROUND:
			self.background = image_content
		else:
			TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")

		self.__update_shape()  # only needed if resize not called; __update_shape called at the end of resize

		return True

	def position_in_layer_bounds(self, position, layer=None):
		"""

		:param position:
		:param layer:
		:return: :raise ValueError:
		"""
		layer = NS_FOREGROUND if type(layer) is None else layer
		target = self.__fetch_layer(layer)
		try:
			position_iter = iter(position)
			if layer == NS_FOREGROUND:
				target = self.foreground
			elif layer == NS_BACKGROUND:
				target = self.background
			else:
				raise TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")
		except:
			raise ValueError("Argument 'position' must be an iterable representation of  x, y coordinates.")

		return position[0] < target.shape[1] and position[1] < target.shape[0]

	def region_in_layer_bounds(self, region, offset=0, layer=NS_FOREGROUND):
		"""

		:param region:
		:param offset:
		:param layer:
		:return: :raise TypeError:
		"""
		bounding_coords = [0, 0, 0, 0]  # ie. x1, y1, x2, y2
		target = self.__fetch_layer(layer)
		if type(offset) is int:
			offset = (offset, offset)
		elif type(offset) in (tuple, list) and len(offset) == 2 and all(type(i) is int and i > 0 for i in offset):
			bounding_coords[0] = offset[0]
			bounding_coords[1] = offset[1]

		if type(region) is NumpySurface:
			bounding_coords[2] = region.width + offset[0]
			bounding_coords[3] = region.height + offset[1]
		elif type(region) is numpy.ndarray:
			bounding_coords[2] = region.shape[1] + offset[0]
			bounding_coords[3] = region.shape[0] + offset[1]
		else:
			raise TypeError("Argument 'region' must be either a numpy.ndarray or a klibs.NumpySurface object.")
		in_bounds = True
		for coord in bounding_coords:
			in_bounds = self.position_in_layer_bounds(coord)

		return in_bounds

	def get_pixel_value(self, location, layer=NS_FOREGROUND):
		"""

		:param location:
		:param layer:
		:return:
		"""
		if self.position_in_layer_bounds(location, layer):
			return self.__fetch_layer(layer)[location[1]][location[0]]
		else:
			return False

	def grey_scale_to_alpha(self, img):
		"""

		:param img:
		:return: :raise TypeError:
		"""
		if type(img) is NumpySurface:
			img = img.render()
		elif type(img) is str:
			img = import_image_file(img)
		elif type(img) is not numpy.ndarray:
			raise TypeError("Argument 'mask' must be a NumpySurface, numpy.ndarray or a path string of an image file.")
		img[0: -1, 0: -1, 3] = img[0: -1, 0: -1, 0]
		return img

	def has_content(self):
		return False if self.foreground is None and self.background is None else True

	def mask(self, mask, position=[0,0], grey_scale=False, layer=NS_FOREGROUND, auto_truncate=True):  # YOU ALLOW NEGATIVE POSITIONING HERE
		"""

		:param mask:
		:param position:
		:param grey_scale:
		:param layer:
		:param auto_truncate:
		:raise ValueError:
		"""
		if type(mask) is NumpySurface:
			mask = mask.render()
		elif type(mask) is str:
			mask = import_image_file(mask)
		elif type(mask) is not numpy.ndarray:
			raise TypeError("Argument 'mask' must be a NumpySurface, numpy.ndarray or a path string of an image file.")
		if grey_scale:
			mask = self.grey_scale_to_alpha(mask)
		if layer == NS_FOREGROUND:
			self.__foreground_unmask = copy(self.foreground)
			self.__foreground_mask = mask
			self.__ensure_writeable(NS_FOREGROUND)
			if auto_truncate:
				try:
					iter(position)
					position = [position[0], position[1]]
				except AttributeError:
					print "Argument 'position' must be iterable set of polar coordinates."
				new_pos = [0, 0]
				mask_x1 = 0
				mask_x2 = 0
				mask_y1 = 0
				mask_y2 = 0
				# make sure position isn't impossible (ie. not off right-hand or bottom edge)
				if position[0] >= 0:
					if (mask.shape[0] + position[1]) > self.foreground.shape[0]:
						mask_x1 = self.foreground.shape[0] - position[1]
					else:
						mask_x1 = 0
					if mask.shape[1] + position[0] > self.foreground.shape[1]:
						mask_x2 = self.foreground.shape[1] - position[0]
					else:
						mask_x2 = mask.shape[1] + position[0]
					new_pos[0] = position[0]
				else:
					mask_x1 = abs(position[0])
					if abs(position[0]) + mask.shape[1] > self.foreground.shape[1]:
						mask_x2 = self.foreground.shape[1] + abs(position[0])
					else:
						mask_x2 = self.foreground.shape[1] - (abs(position[0]) + mask.shape[1])
					new_pos[0] = 0


				if position[1] >= 0:
					mask_y1 = position[1]
					if mask.shape[0] + position[1] > self.foreground.shape[0]:
						mask_y2 = self.foreground.shape[0] - position[1]
					else:
						mask_y2 = mask.shape[0] + position[1]
					new_pos[1] = position[1]
				else:
					mask_y1 = abs(position[1])
					if abs(position[1]) + mask.shape[0] > self.foreground.shape[0]:
						mask_y2 = self.foreground.shape[0] + abs(position[1])
					else:
						mask_y2 = self.foreground.shape[0] - (abs(position[1]) + mask.shape[0])
					new_pos[1] = 0

				mask = mask[mask_y1: mask_y2, mask_x1: mask_x2]
				position = new_pos

			elif self.region_in_layer_bounds(mask, position, NS_FOREGROUND):
				self.__fg_mask_position = position
			else:
				raise ValueError("Mask falls outside of layer bounds; reduce size or reposition.")

			alpha_map = numpy.ones(mask.shape[:-1]) * 255 - mask[..., 3]
			fg_x1 = position[0]
			fg_x2 = alpha_map.shape[1] + position[0]
			fg_y1 = position[1]
			fg_y2 = alpha_map.shape[0] + position[1]
			pump()
			flat_map = alpha_map.flatten()
			flat_fg = self.foreground[fg_y1: fg_y2, fg_x1: fg_x2, 3].flatten()
			zipped_arrays = zip(flat_map, flat_fg)
			flat_masked_region = numpy.asarray([min(x, y) for x, y in zipped_arrays])
			masked_region = flat_masked_region.reshape(alpha_map.shape)
			self.foreground[fg_y1: fg_y2, fg_x1: fg_x2, 3] = masked_region

	def prerender(self):
		"""


		:return:
		"""
		return self.render(True)

	def resize(self, dimensions=None, fill=(0, 0, 0, 0)):
		# todo: add "extend" function, which wraps this
		"""

		:param dimension:
		:param fill: Transparent by default, can be any rgba value
		:return:
		"""
		try:
			fill = rgb_to_rgba(fill)
		except [AttributeError, IndexError]:
			raise ValueError("Argument fill must be a rgb or rgba color iterable.")

		if dimensions is None:
			return self.__update_shape()

		# create some empty arrays of the new dimensions and ascertain clipping values if needed
		try:
			new_fg = numpy.zeros((dimensions[1], dimensions[0], 4))  # ie. new foreground
			fg_clip = [	new_fg.shape[0] - (self.fg_offset[1] + self.foreground.shape[0]),
						new_fg.shape[1] - (self.fg_offset[0] + self.foreground.shape[1]) ]
			for clip in fg_clip:
				if clip >= 0:
					fg_clip[fg_clip.index(clip)] = self.foreground.shape[fg_clip.index(clip)]
			new_bg = numpy.zeros((dimensions[1], dimensions[0], 4))
			bg_clip = [new_bg.shape[0] - (self.bg_offset[1] + self.background.shape[0]),
					   new_bg.shape[1] - (self.bg_offset[0] + self.background.shape[1])]
			for clip in bg_clip:
				if clip >= 0:
					index = bg_clip.index(clip)
					offset_index = 0 if index == 1 else 1
					bg_clip[index] = self.background.shape[index] + self.bg_offset[offset_index]
		except [AttributeError, IndexError]:
			raise ValueError("Argument dimensions must be a an iterable integer pair (height x width) ")

		# apply clipping if needed
		self.foreground = self.foreground[0:fg_clip[0], 0:fg_clip[1]]
		self.background = self.background[0:bg_clip[0], 0:bg_clip[1]]

		# insert old background and foreground into their positions on new arrays
		y1 = self.bg_offset[1]
		y2 = self.background.shape[0]
		x1 = self.bg_offset[0]
		x2 = self.background.shape[1]
		new_bg[y1: y2, x1: x2 ] = self.background

		y1 = self.fg_offset[1]
		y2 = self.foreground.shape[0]
		x1 = self.fg_offset[0]
		x2 = self.foreground.shape[1]
		new_fg[y1:y2, x1:x2] = self.foreground

		self.foreground = new_fg
		self.background = new_bg

		self.__update_shape()

	def render(self, prerendering=False):
		# todo: add functionality for not using a copy, ie. permanently render
		"""

		:param prerendering:
		:return: :raise ValueError:
		"""
		if self.__prerender is not None and prerendering is False:
			return self.__prerender
		render_surface = None
		if self.background is None and self.foreground is None:
			raise ValueError('Nothing to render; NumpySurface has been initialized but not content has been added.')
		if self.background is None:
			render_surface = copy(self.foreground)
		else:  # flatten background and foreground together
			render_surface = numpy.zeros((self.height, self.width, 4))
			bg_x1 = self.__background_offset[0]
			bg_x2 = bg_x1 + self.background.shape[1]
			bg_y1 = self.__background_offset[1]
			bg_y2 = bg_y1 + self.background.shape[0]

			fg_x1 = self.__foreground_offset[0]
			fg_x2 = fg_x1 + self.foreground.shape[1]
			fg_y1 = self.__foreground_offset[1]
			fg_y2 = fg_y1 + self.foreground.shape[0]

			render_surface[bg_y1: bg_y2, bg_x1: bg_x2] = self.background
			render_surface[fg_y1: fg_y2, fg_x1: fg_x2] = self.foreground

		if prerendering:
			self.__prerender = render_surface
			return True
		else:
			return render_surface

	def __update_shape(self):
		for surface in [self.foreground, self.background]:
			try:
				if self.width < surface.shape[1]:
					self.width = surface.shape[1]
				if self.height < surface.shape[0]:
					self.height = surface.shape[0]
			except AttributeError:
				pass

		return True

	@property
	def height(self):
		return self.__height

	@height.setter
	def height(self, height_value):
		if type(height_value) is int and height_value > 0:
			self.__height = height_value
		else:
			self.__height = 0

	@property
	def width(self):
		return self.__width

	@width.setter
	def width(self, width_value):
		if type(width_value) is int and width_value > 0:
			self.__width = width_value  # todo: extend a numpy array with empty pixels?
		else:
			self.__width = 0

	@property
	def foreground(self):
		return self.__foreground

	@foreground.setter
	def foreground(self, foreground_content):
		if foreground_content.shape[1] > self.width:
			self.width = foreground_content.shape[1]
		if foreground_content.shape[0] > self.height:
			self.height = foreground_content.shape[0]
		self.__foreground = foreground_content

	@property
	def background(self):
		return self.__background

	@background.setter
	def background(self, background_content):
		if type(background_content) is numpy.ndarray:
			# todo: foreground needs to be resized to background size if this happens
			if background_content.shape[1] > self.width:
				self.width = background_content.shape[1]
			if background_content.shape[0] > self.height:
				self.height = background_content.shape[0]
			self.__background = background_content
		elif type(background_content) is tuple and len(background_content) in (3, 4):
			raise TypeError("NumpySurface.background must be a numpy.ndarray; set color with NumpySurface.background_color")
		else:
			raise TypeError("NumpySurface.background must be a numpy.ndarray.")

	@property
	def background_color(self):
		return self.__bg_color

	@background_color.setter
	def background_color(self, color):
		if type(color) is tuple and len(color) in (3, 4):
			if len(color) == 3:
				color[3] = 255
			self.__bg_color = color
		else:
			raise TypeError("NumpySurface.background_color must be a tuple of integers (ie. rgb or rgba color value).")

	@property
	def dimensions(self):
		return [self.width, self.height]
