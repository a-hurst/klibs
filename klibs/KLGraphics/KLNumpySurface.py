__author__ = 'Jonathan Mulle & Austin Hurst'

from copy import copy

import numpy as np
from PIL import Image
from PIL import ImageOps
import aggdraw

from klibs.KLConstants import NS_BACKGROUND, NS_FOREGROUND, BL_TOP_RIGHT, BL_TOP_LEFT
from .utils import (_build_registrations, aggdraw_to_array, image_file_to_array, add_alpha,
	rgb_to_rgba)


def grey_scale_to_alpha(source):
		"""

		:param source:
		:return: :raise TypeError:
		"""
		if type(source) is NumpySurface:
			source = source.render()
		elif type(source) is str:
			source = image_file_to_array(source)
		elif type(source) is not np.ndarray:
			raise TypeError("Argument 'mask' must be a NumpySurface, numpy.ndarray or a path string of an image file.")
		source[0: -1, 0: -1, 3] = source[0: -1, 0: -1, 0]
		return source


def aggdraw_to_numpy_surface(surface):
	"""Converts an :obj:`aggdraw.Draw` object to an RGBA :obj:`~NumpySurface` of the same size.

	Args:
		surface (:obj:`aggdraw.Draw`): The aggdraw surface to convert.

	Returns:
		:obj:`~NumpySurface`: A NumpySurface of the given aggdraw surface.

	"""
	# NOTE: Legacy function, should be undocumented and eventually removed
	return NumpySurface(aggdraw_to_array(surface))


class NumpySurface(object):

	def __init__(self, foreground=None, fg_offset=None, width=None, height=None):
		self.__content = None
		self.__foreground__ = None
		self.__foreground_offset__ = None
		self.__foreground_mask__ = None
		self.__foreground_unmask__ = None
		self.__height__ = None
		self.__width__ = None
		self.__bg_color__ = None
		self.rendered = None
		self.fg = None
		self.fg_offset = None
		self.width = width
		self.height = height
		self.fg_offset = fg_offset
		self.foreground = foreground
		self.init_canvas()

	def __str__(self):
		return "klibs.NumpySurface, ({0} x {1}) at {2}".format(self.width, self.height, hex(id(self)))

	def __ensure_writeable__(self, layer=NS_FOREGROUND):
		if layer == NS_FOREGROUND:
			try:
				self.foreground.setflags(write=1)
			except AttributeError:
				self.foreground = np.zeros((self.width, self.height, 4))
				self.__ensure_writeable__(NS_FOREGROUND)

	def init_canvas(self):
		if all(i is None for i in [self.foreground, self.width, self.height]):
			self.foreground = np.zeros((1,1,4))
		else:
			self.foreground = np.zeros((self.height, self.width, 4))
		self.__update_shape__()

	def average_color(self):
		px = self.render()
		px_count = px.shape[0] * px.shape[1]
		new_px = px.reshape((px_count,4))
		print(new_px.shape)

	def blit(self, source, layer=NS_FOREGROUND, registration=7, location=(0, 0), behavior=None):
		# todo: implement layer logic here
		"""

		:param source:
		:param layer:
		:param registration:
		:param location:
		:raise ValueError:
		"""
		try:
			source.foreground = source.foreground.astype(np.uint8)
			source = source.render()
		except AttributeError:
			pass
		try:
			source = add_alpha(source)
		except:
			raise TypeError("Argument 'source' must be either of klibs.NumpySurface or numpy.ndarray.")

		source_height = source.shape[0]
		source_width = source.shape[1]

		registration = _build_registrations(source_height, source_width)[registration]
		location = (int(location[0] + registration[0]), int(location[1] + registration[1]))

		# don't attempt the blit if source can't fit
		if behavior is None:
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

		self.__ensure_writeable__(layer)
		# todo: find out why this won't accept a 3rd dimension (ie. color)
		if behavior == "resize":
			if source_width > self.width: self.resize([self.height, source_width])
			if source_height > self.height: self.resize([self.width, source_height])
		# todo: make a "clip" behavior
		# print "ForegroundShape: {0}, SourceShape: {1}".format(self.foreground.shape, source.shape)
		blit_region = self.foreground[y1: y2, x1: x2, :]
		# print "Blit_region of fg: {0}".format(blit_region.shape)
		self.foreground[y1: y2, x1: x2, :] = source

		return self

	def scale(self, size, layer=None):
		# TODO: expand this considerably;  http://pillow.readthedocs.org/en/3.0.x/reference/ImageOps.html
		if not self.has_content():
			return

		if layer == NS_FOREGROUND or layer is None:
			try:
				layer_image = Image.fromarray(self.foreground.astype(np.uint8))
				scaled_image = layer_image.resize(size, Image.ANTIALIAS)
				self.foreground = np.asarray(scaled_image)
			except AttributeError as e:
				if str(e) != "'NoneType' object has no attribute '__array_interface__'":
					raise e
			except TypeError:
				pass

		self.__update_shape__()
		# self.resize(size)

		return self

	def rotate(self, angle, layer=None):
	# TODO: expand this considerably;  http://pillow.readthedocs.org/en/3.0.x/reference/ImageOps.html
		if not self.has_content():
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
		self.__update_shape__()
		return self

	def get_pixel_value(self, location, layer=NS_FOREGROUND):
		"""

		:param location:
		:param layer:
		:return:
		"""
		try:
			return self.foreground[location[1]][location[0]]
		except IndexError:
			return False

	def has_content(self):
		return False if self.foreground is None else True

	def mask(self, mask, location=[0,0], grey_scale=False, layer=NS_FOREGROUND, auto_truncate=True):  # YOU ALLOW NEGATIVE POSITIONING HERE
		"""

		:param mask:
		:param location:
		:param grey_scale:
		:param layer:
		:param auto_truncate:
		:raise ValueError:
		"""
		if type(mask) is NumpySurface:
			mask = mask.render()
		elif type(mask) is str:
			mask = image_file_to_array(mask)
		elif type(mask) is not np.ndarray:
			raise TypeError("Argument 'mask' must be a NumpySurface, numpy.ndarray or a path string of an image file.")
		if grey_scale:
			mask = grey_scale_to_alpha(mask)
		if layer == NS_FOREGROUND:
			self.__foreground_unmask__ = copy(self.foreground)
			self.__foreground_mask__ = mask
			self.__ensure_writeable__(NS_FOREGROUND)
			if auto_truncate:
				try:
					iter(location)
					location = [location[0], location[1]]
				except AttributeError:
					print("Argument 'location' must be iterable set of polar coordinates.")
				new_pos = [0, 0]
				mask_x1 = 0
				mask_x2 = 0
				mask_y1 = 0
				mask_y2 = 0
				# make sure location isn't impossible (ie. not off right-hand or bottom edge)
				if location[0] >= 0:
					if (mask.shape[0] + location[1]) > self.foreground.shape[0]:
						mask_x1 = self.foreground.shape[0] - location[1]
					else:
						mask_x1 = 0
					if mask.shape[1] + location[0] > self.foreground.shape[1]:
						mask_x2 = self.foreground.shape[1] - location[0]
					else:
						mask_x2 = mask.shape[1] + location[0]
					new_pos[0] = location[0]
				else:
					mask_x1 = abs(location[0])
					if abs(location[0]) + mask.shape[1] > self.foreground.shape[1]:
						mask_x2 = self.foreground.shape[1] + abs(location[0])
					else:
						mask_x2 = self.foreground.shape[1] - (abs(location[0]) + mask.shape[1])
					new_pos[0] = 0


				if location[1] >= 0:
					mask_y1 = location[1]
					if mask.shape[0] + location[1] > self.foreground.shape[0]:
						mask_y2 = self.foreground.shape[0] - location[1]
					else:
						mask_y2 = mask.shape[0] + location[1]
					new_pos[1] = location[1]
				else:
					mask_y1 = abs(location[1])
					if abs(location[1]) + mask.shape[0] > self.foreground.shape[0]:
						mask_y2 = self.foreground.shape[0] + abs(location[1])
					else:
						mask_y2 = self.foreground.shape[0] - (abs(location[1]) + mask.shape[0])
					new_pos[1] = 0

				mask = mask[mask_y1: mask_y2, mask_x1: mask_x2]
				location = new_pos

			alpha_map = np.ones(mask.shape[:-1]) * 255 - mask[..., 3]
			fg_x1 = location[0]
			fg_x2 = alpha_map.shape[1] + location[0]
			fg_y1 = location[1]
			fg_y2 = alpha_map.shape[0] + location[1]
			flat_map = alpha_map.flatten()
			flat_fg = self.foreground[fg_y1: fg_y2, fg_x1: fg_x2, 3].flatten()
			zipped_arrays = zip(flat_map, flat_fg)
			flat_masked_region = np.asarray([min(x, y) for x, y in zipped_arrays])
			masked_region = flat_masked_region.reshape(alpha_map.shape)
			self.foreground[fg_y1: fg_y2, fg_x1: fg_x2, 3] = masked_region

	def prerender(self):
		"""


		:return:
		"""
		return self.render(True)

	def resize(self, dimensions=None, registration=BL_TOP_LEFT, fill=[0, 0, 0, 0]):
		# todo: add "extend" function, which wraps this
		"""

		:param dimensions:
		:param fill: Transparent by default, can be any rgba value
		:return:
		"""

		try:
			fill = rgb_to_rgba(fill)
		except (AttributeError, IndexError):
			raise ValueError("Argument fill must be a rgb or rgba color iterable.")

		if dimensions is None:
			return self.__update_shape__()

		# create some empty arrays of the new dimensions and ascertain clipping values if needed
		try:
			new_fg = np.zeros((dimensions[1], dimensions[0], 4))  # ie. new foreground
			fg_clip = [	new_fg.shape[0] - (self.fg_offset[1] + self.foreground.shape[0]),
						new_fg.shape[1] - (self.fg_offset[0] + self.foreground.shape[1]) ]
			for clip in fg_clip:
				axis = fg_clip.index(clip)
				if clip >= 0:
					fg_clip[axis] = self.foreground.shape[axis] + self.fg_offset[axis]
		except (AttributeError, IndexError):
			raise ValueError("Argument dimensions must be a an iterable integer pair (height x width) ")

		# apply clipping if needed
		self.foreground = self.foreground[0:fg_clip[0], 0:fg_clip[1]]

		y1 = self.fg_offset[1]
		y2 = self.foreground.shape[0]
		x1 = self.fg_offset[0]
		x2 = self.foreground.shape[1]
		new_fg[y1:y2, x1:x2, :] = self.foreground

		self.foreground = new_fg

		# self.__update_shape()

		return self

	def render(self, prerendering=False):
		# todo: add functionality for not using a copy, ie. permanently render
		"""

		:param prerendering:  Legacy argument; left in for backwards compatibility
		:return: :raise ValueError:
		"""

		if self.foreground is None:
			raise ValueError('Nothing to render; NumpySurface has been initialized but not content has been added.')
		else:
			render_surface = copy(self.foreground)

		self.rendered = render_surface.astype(np.uint8)
		return self.rendered

	def __update_shape__(self):
		for surface in [self.foreground]:
			try:
				if self.width < surface.shape[1]:
					self.width = surface.shape[1]
				if self.height < surface.shape[0]:
					self.height = surface.shape[0]
			except AttributeError:
				pass

	@property
	def height(self):
		return self.__height__

	@height.setter
	def height(self, height_value):
		try:
			if int(height_value) > 0:
				self.__height__ = int(height_value)
			else:
				raise ValueError
		except (ValueError, TypeError):
			self.__height__ = 0

	@property
	def width(self):
		return self.__width__

	@width.setter
	def width(self, width_value):
		try:
			if int(width_value) > 0:
				self.__width__ = int(width_value)
			else:
				raise ValueError
		except (ValueError, TypeError):
			self.__width__ = 0

	@property
	def foreground(self):
		return self.__foreground__

	@foreground.setter
	def foreground(self, foreground_content):
		if foreground_content is None:
			self.__foreground__ = None
			self.fg = self.__foreground__
			return
		try:
			fg_array = add_alpha(foreground_content)  # ie. numpy.ndarray
		except AttributeError:
			try:
				fg_array = image_file_to_array(foreground_content) # ie. path (string)
			except AttributeError:
				try:
					fg_array = foreground_content.foreground  # ie. KLNumpySurface.NumpySurface
				except AttributeError:
					try:
						fg_array = foreground_content.render()  # ie. KLDraw.Drawbject
					except AttributeError:
						try:
							fg_array = aggdraw_to_array(foreground_content)
						except:
							raise TypeError("Invalid type for initializing a NumpySurface layer.")
		if fg_array.shape[1] > self.width:
			self.width = fg_array.shape[1]
		if fg_array.shape[0] > self.height:
			self.height = fg_array.shape[0]
		self.__foreground__ = fg_array
		self.fg = self.__foreground__  # convenience alias

	@property
	def background_color(self):
		return self.__bg_color__

	@background_color.setter
	def background_color(self, color):
		if type(color) is tuple and len(color) in (3, 4):
			if len(color) == 3:
				color[3] = 255
			self.__bg_color__ = color
		else:
			raise TypeError("NumpySurface.background_color must be a tuple of integers (ie. rgb or rgba color value).")

	@property
	def dimensions(self):
		return [self.width, self.height]

	@property
	def fg_offset(self):
		return self.__foreground_offset__

	@fg_offset.setter
	def fg_offset(self, offset):
		try:
			iter(offset)
			self.__foreground_offset__ = offset
		except TypeError:
			if offset is None:
				self.__foreground_offset__ = (0, 0)
			else:
				raise ValueError("Background and foreground offsets must be iterable.")
