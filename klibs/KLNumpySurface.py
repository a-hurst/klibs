import os
import numpy
from copy import copy
from PIL import Image
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
	pr("@T\tcol: {0}, opacity:{1}".format(col, opacity))
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

class NumpySurface(object):
	# todo: save states! save diffs between operations! so cool and unnecessary!
	# todo: default alpha value for render

	def __init__(self, foreground=None, background=None, fg_position=None, bg_position=None, width=None, height=None):
		self.__foreground = None
		self.__foreground_position = None
		self.__foreground_mask = None
		self.__foreground_unmask = None
		self.__fg_mask_position = None
		self.__background = None
		self.__background_position = None
		self.__background_mask = None
		self.__background_unmask = None
		self.__bg_mask_position = None
		self.__height = None
		self.__width = None
		self.__bg_color = None
		self.__prerender = None
		self.bg = None
		self.fg = None
		self.bg_xy = None
		self.fg_xy = None

		if width:
			self.width = width
		if height:
			self.height = height

		# do positions first in case a resize is required during bg & fg processing
		if fg_position is not None:
			if type(fg_position) is tuple:
				if len(fg_position) == 2 and all(type(i) is int for i in fg_position):
					self.__foreground_position = fg_position
				else:
					raise ValueError("Both indices of argument 'fg_position' must be positive integers.")
			else:
				raise TypeError("Argument 'fg_position' must be a tuple of length 2 or NoneType.")
		else:
			self.__foreground_position = (0, 0)

		if bg_position is not None:
			if type(bg_position) is tuple:
				if len(bg_position) == 2 and all(type(i) is int for i in bg_position):
					self.__background_position = bg_position
				else:
					raise ValueError("Both indices of argument 'bg_position' must be positive integers.")
			else:
				raise TypeError("Argument 'bg_position' must be a tuple of length 2 or NoneType.")
		else:
			self.__background_position = (0, 0)

		# just some aliases to shorten lines later (render, resize, etc.)
		self.bg = self.__background
		self.fg = self.__foreground
		self.bg_xy = self.__background_position
		self.fg_xy = self.__foreground_position

		if background is not None:  # process bg first to cut down on resizing since bg is probably > fg
			if type(background) is numpy.ndarray:
				self.background = self.__ensure_alpha_channel(background)
			elif type(background) is str:  # assume it's a path to an image file
				self.layer_from_file(background, False, bg_position)
			else:
				raise TypeError("Argument 'background' must be either a string (path to image) or a numpy.ndarray.")

		if foreground is not None:
			try:
				self.foreground = self.__ensure_alpha_channel(foreground)
			except AttributeError:
				self.layer_from_file(foreground, True, fg_position)

			# elif type(foreground) is str:  # assume it's a path to an image file
			# else:
				# raise TypeError("Argument 'foreground' must be either a string (path to image) or a numpy.ndarray.")

	def __str__(self):
		return "klibs.NumpySurface, ({0} x {1}) at {2}".format(self.width, self.height, hex(id(self)))

	def blit(self, source, layer=NS_FOREGROUND, registration=7, position=(0, 0)):
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
			source = self.__ensure_alpha_channel(source)
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
		if source_height > self.height or source_width > self.width:
			raise ValueError("Source is larger than destination in one or more dimensions.")
		elif source_height + position[1] > self.height or source_width + position[0] > self.width:
			raise ValueError("Source cannot be blit to position; destination bounds exceeded.")
		x1 = position[0]
		x2 = position[0] + source_width
		y1 = position[1]
		y2 = position[1] + source_height

		self.__ensure_writeable(layer)
		# todo: find out why this won't accept a 3rd dimension (ie. color)
		if layer == NS_FOREGROUND:
			self.foreground[y1: y2, x1: x2] = source
		else:
			self.background[y1: y2, x1: x2] = source

	def __ensure_alpha_channel(self, numpy_array, alpha_value=255):
		if len(numpy_array[2][0]) == 3:
			return numpy.insert(numpy_array, 3, alpha_value, 2)
		else:
			return numpy_array

	def __ensure_writeable(self, layer=NS_FOREGROUND):
		if layer == NS_FOREGROUND:
			self.foreground.setflags(write=1)
		else:
			self.background.setflags(write=1)

	def layer_from_file(self, image, layer=NS_FOREGROUND, position=None):
		# todo: better error handling; check if the file has a valid image extension, make sure path is a valid type
		"""

		:param image:
		:param layer:
		:param position:
		:return: :raise TypeError:
		"""
		image_content = self.__ensure_alpha_channel(numpy.array(Image.open(image)))

		if layer == NS_FOREGROUND:
			self.foreground = image_content
		elif layer == NS_BACKGROUND:
			self.background = image_content
		else:
			TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")

		self.__update_shape()  # only needed if resize not called; __update_shape called at the end of resize

		return True

	def __import_image_file(self, path):
			return self.__ensure_alpha_channel(numpy.array(Image.open(path)))

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

	# def __truncate(self, surface, position, layer=NS_FOREGROUND):
	# 	width = 0
	# 	height = 0
		#
		# destination[position]

	def grey_scale_to_alpha(self, img):
		"""

		:param img:
		:return: :raise TypeError:
		"""
		if type(img) is NumpySurface:
			img = img.render()
		elif type(img) is str:
			img = self.__import_image_file(img)
		elif type(img) is not numpy.ndarray:
			raise TypeError("Argument 'mask' must be a NumpySurface, numpy.ndarray or a path string of an image file.")
		img[0: -1, 0: -1, 3] = img[0: -1, 0: -1, 0]
		return img

	def mask(self, mask, position, grey_scale=False, layer=NS_FOREGROUND, auto_truncate=True):  # YOU ALLOW NEGATIVE POSITIONING HERE
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
			mask = self.__import_image_file(mask)
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
					iter_pos = iter(position)
					position = [position[0], position[1]]
				except:
					print "Argument 'position' must be iterable set of polar coordinates."
				# layer_yx = self.foreground.shape
				# mask_height = self.foreground.shape[0] - mask.shape[0] + -1 * position[1]
				# mask_width = self.foreground.shape[1] - mask.shape[1] + -1 * position[0]

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

				# mask = mask[mask_y1: mask_y2, mask_x1: mask_x2]
				position = new_pos
				pr("\t@TMask Shape: {0}, Position: {1}, FG Shape: {2}".format(mask.shape, position, self.foreground.shape), 2)

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
			self.foreground[fg_y1: fg_y2, fg_x1: fg_x2, 3] = numpy.asarray([min(x, y) for x, y in
																			zip(alpha_map.flatten(),
																				self.foreground[fg_y1: fg_y2,
																				fg_x1: fg_x2, 3].flatten())]).reshape(alpha_map.shape)

	def prerender(self):
		"""


		:return:
		"""
		return self.render(True)

	def resize(self, dimensions, fill=(0, 0, 0, 0)):
		# todo: add "extend" function, which wraps this
		"""

		:param dimension:
		:param fill: Transparent by default, can be any rgba value
		:return:
		"""
		print "Resize[dimensions]: {0}".format(dimensions)
		if type(fill) is tuple:
			if len(fill) in (3, 4) and all(type(color) is int for color in fill):
				if len(fill) == 3:
					fill = rgb_to_rgba(fill)
			else:
				raise ValueError("All indices of argument 'fill' must be integers between 0 and 255.")
		else:
			raise TypeError("Argument 'fill' must be a tuple of either length 3 or 4.")
		if type(dimensions) is tuple and len(dimensions) == 2:
			if int in (type(dimensions[0]), type(dimensions[1])):
				if type(dimensions[0]) is True:
					dimensions[0] = dimensions[1]
				if type(dimensions[0]) is False:
					dimensions[0] = self.width
				if type(dimensions[1]) is True:
					dimensions[1] = dimensions[0]
				if type(dimensions[1]) is False:
					dimensions[1] = self.height
			else:
				raise ValueError("Both indices of argument 'dimensions' cannot be boolean; at least 1 integer required.")
		else:
			raise ValueError("Argument 'dimensions' must be a tuple of length 2. ")

		# create some empty arrays of the new dimensions
		nfg = numpy.zeros((dimensions[0], dimensions[1], 4))  # ie. new foreground
		nbg = numpy.zeros((dimensions[0], dimensions[1], 4))

		# if resize is called during __init__ (b/c both bg & fg != None), bg or fg dims.  may be missing, so use (0,0)
		# positions, though (ie. bg_xy and fg_xy) are set before surfaces are loaded in __init__ so will be ok
		ofg_wh = None  # ie. old foreground width & height
		obg_wh = None
		if self.background is None:
			obg_wh = nbg.shape
		else:
			obg_wh = self.background.shape
		if self.foreground is None:
			ofg_wh = nfg.shape
		else:
			ofg_wh = self.background.shape

		# insert old background and foreground into their positions on new arrays
		if self.background is None:
			self.background = nbg
		print self.bg_xy
		print obg_wh
		nbg[self.bg_xy[0]: self.bg_xy[0] + obg_wh[0], self.bg_xy[1]: self.bg_xy[1] + obg_wh[1]] = self.background
		self.background = nbg

		if self.fg is None:
			self.foreground = nfg
		nfg[self.fg_xy[1]: self.fg_xy[1] + ofg_wh[0], self.fg_xy[1]: self.fg_xy[1] + ofg_wh[1]] = self.foreground
		self.foreground = nfg

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
			bg_x1 = self.__background_position[0]
			bg_x2 = bg_x1 + self.background.shape[1]
			bg_y1 = self.__background_position[1]
			bg_y2 = bg_y1 + self.background.shape[0]

			fg_x1 = self.__foreground_position[0]
			fg_x2 = fg_x1 + self.foreground.shape[1]
			fg_y1 = self.__foreground_position[1]
			fg_y2 = fg_y1 + self.foreground.shape[0]
			print self.foreground
			render_surface[bg_y1: bg_y2, bg_x1: bg_x2] = self.background
			render_surface[fg_y1: fg_y2, fg_x1: fg_x2] = self.foreground

		if prerendering:
			self.__prerender = render_surface
			return True
		else:
			return render_surface

	def __update_shape(self):
		if type(self.foreground) is numpy.ndarray:
			if type(self.background) is numpy.ndarray:
				if self.foreground.shape[1] > self.background.shape[1]:
					self.width = self.foreground.shape[1]
				else:
					self.width = self.background.shape[1]
				if self.foreground.shape[0] > self.background.shape[0]:
					self.height = self.foreground.shape[0]
				else:
					self.height = self.background.shape[0]
			else:
				self.width = self.foreground.shape[1]
				self.height = self.foreground.shape[0]
		elif type(self.background) is numpy.ndarray:
			self.width = self.background.shape[1]
			self.height = self.background.shape[0]
		else:
			self.width = 0
			self.height = 0

		return True

	@property
	def height(self):
		return self.__height

	@height.setter
	def height(self, height_value):
		if type(height_value) is int > 0:
			self.__height = height_value
		else:
			raise TypeError("NumpySurface.height must be a positive integer.")

	@property
	def width(self):
		return self.__width

	@width.setter
	def width(self, width_value):
		if type(width_value) is int > 0:
			self.__width = width_value  # todo: extend a numpy array with empty pixels?
		else:
			raise TypeError("NumpySurface.width must be a positive integer.")

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
