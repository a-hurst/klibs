__author__ = 'Jonathan Mulle & Austin Hurst'

from copy import copy

import numpy as np
from PIL import Image
from PIL import ImageOps
import aggdraw

from klibs.KLConstants import NS_BACKGROUND, NS_FOREGROUND, BL_TOP_RIGHT, BL_TOP_LEFT
from klibs.KLGraphics import _build_registrations


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
		if type(source) is NumpySurface:
			source = source.render()
		elif type(source) is str:
			source = import_image_file(source)
		elif type(source) is not np.ndarray:
			raise TypeError("Argument 'mask' must be a NumpySurface, numpy.ndarray or a path string of an image file.")
		source[0: -1, 0: -1, 3] = source[0: -1, 0: -1, 0]
		return source


class NumpySurface(object):
	# todo: save states! save diffs between operations! so cool and unnecessary!
	# todo: default alpha value for render
	# todo: fg/bg dichotomy stupid and unwieldy; just use indexed layers

	def __init__(self, foreground=None, background=None, fg_offset=None, bg_offset=None, width=None, height=None):
		self.__foreground__ = None
		self.__foreground_offset__ = None
		self.__foreground_mask__ = None
		self.__foreground_unmask__ = None
		self.__fg_mask_pos__ = None
		self.__background__ = None
		self.__background_offset__ = None
		self.__background_mask__ = None
		self.__background_unmask__ = None
		self.__bg_mask_location__ = None
		self.__height__ = None
		self.__width__ = None
		self.__bg_color__ = None
		self.rendered = None
		self.bg = None
		self.fg = None
		self.bg_offset = None
		self.fg_offset = None
		self.width = width
		self.height = height
		self.fg_offset = fg_offset
		self.bg_offset = bg_offset
		self.foreground = foreground
		self.background = background
		self.layers = {NS_FOREGROUND: self.__foreground__, NS_BACKGROUND:self.__background__}
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
		else:
			try:
				self.background.setflags(write=1)
			except AttributeError:
				self.background = np.zeros((self.width, self.height, 4))
				self.__ensure_writeable__(NS_BACKGROUND)

	def __fetch_layer__(self, layer):
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

	def init_canvas(self):
		if all(i is None for i in [self.background, self.foreground, self.width, self.height]):
			self.foreground = np.zeros((1,1,4))
			self.background = np.zeros((1,1,4))
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
				self.foreground = np.zeros((fg_height, fg_width, 4))

			if self.background is None:
				try:
					bg_width = self.foreground.shape[1] if self.foreground.shape[1] > self.width else self.width
				except AttributeError:
					bg_width = self.width
				try:
					bg_height = self.foreground.shape[0] if self.foreground.shape[0] > self.height else self.height
				except AttributeError:
					bg_height = self.height

				self.background = np.zeros((bg_height, bg_width, 4))
		self.__update_shape__()

	def average_color(self, layer=None):
		# nope, doesn't work; were working it out with Ross but then you couldn't finish
		try:
			px = self.rendered if not layer else self.layers[layer]
			iter(px)
		except TypeError:
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
			source = add_alpha_channel(source)
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
		if layer == NS_FOREGROUND:
			self.foreground[y1: y2, x1: x2, :] = source
		else:
			self.background[y1: y2, x1: x2] = source

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
		#
		# if layer == NS_BACKGROUND or layer is None:
		# 	try:
		# 		layer_image = Image.fromarray(self.background.astype(np.uint8))
		# 		scaled_image = layer_image.resize(size, Image.ANTIALIAS)
		# 		self.foreground = np.asarray(scaled_image)
		# 	except AttributeError as e:
		# 		if e.message != "'NoneType' object has no attribute '__array_interface__'":
		# 			raise e
		# 	except TypeError:
		# 		pass

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

	def layer_from_file(self, image, layer=NS_FOREGROUND, location=None):
		# todo: better error handling; check if the file has a valid image extension, make sure path is a valid type
		"""

		:param image:
		:param layer:
		:param location:
		:return: :raise TypeError:
		"""
		image_content = add_alpha_channel(np.array(Image.open(image)))

		if layer == NS_FOREGROUND:
			self.foreground = image_content
		elif layer == NS_BACKGROUND:
			self.__set_background__(image_content)
		else:
			TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")

		self.__update_shape__()  # only needed if resize not called; __update_shape called at the end of resize
		return self

	def location_in_layer_bounds(self, location, layer=None):
		"""

		:param location:
		:param layer:
		:return: :raise ValueError:
		"""
		layer = NS_FOREGROUND if type(layer) is None else layer
		target = self.__fetch_layer__(layer)
		try:
			location_iter = iter(location)
			if layer == NS_FOREGROUND:
				target = self.foreground
			elif layer == NS_BACKGROUND:
				target = self.background
			else:
				raise TypeError("Argument 'layer' must be either NS_FOREGROUND (ie. 1) or NS_BACKGROUND (ie. 0).")
		except:
			raise ValueError("Argument 'location' must be an iterable representation of  x, y coordinates.")

		return location[0] < target.shape[1] and location[1] < target.shape[0]

	def region_in_layer_bounds(self, region, offset=0, layer=NS_FOREGROUND):
		"""

		:param region:
		:param offset:
		:param layer:
		:return: :raise TypeError:
		"""
		bounding_coords = [0, 0, 0, 0]  # ie. x1, y1, x2, y2
		target = self.__fetch_layer__(layer)
		if type(offset) is int:
			offset = (offset, offset)
		elif type(offset) in (tuple, list) and len(offset) == 2 and all(type(i) is int and i > 0 for i in offset):
			bounding_coords[0] = offset[0]
			bounding_coords[1] = offset[1]

		if type(region) is NumpySurface:
			bounding_coords[2] = region.width + offset[0]
			bounding_coords[3] = region.height + offset[1]
		elif type(region) is np.ndarray:
			bounding_coords[2] = region.shape[1] + offset[0]
			bounding_coords[3] = region.shape[0] + offset[1]
		else:
			raise TypeError("Argument 'region' must be either a numpy.ndarray or a klibs.NumpySurface object.")
		in_bounds = True
		for coord in bounding_coords:
			in_bounds = self.location_in_layer_bounds(coord)

		return in_bounds

	def get_pixel_value(self, location, layer=NS_FOREGROUND):
		"""

		:param location:
		:param layer:
		:return:
		"""
		if self.location_in_layer_bounds(location, layer):
			return self.__fetch_layer__(layer)[location[1]][location[0]]
		else:
			return False

	def has_content(self):
		return False if self.foreground is None and self.background is None else True

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
			mask = import_image_file(mask)
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

			elif self.region_in_layer_bounds(mask, location, NS_FOREGROUND):
				self.__fg_mask_pos__ = location
			else:
				raise ValueError("Mask falls outside of layer bounds; reduce size or relocation.")

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

		from klibs.KLGraphics import rgb_to_rgba
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

			new_bg = np.zeros((dimensions[1], dimensions[0], 4))
			bg_clip = [new_bg.shape[0] - (self.bg_offset[1] + self.background.shape[0]),
					   new_bg.shape[1] - (self.bg_offset[0] + self.background.shape[1])]
			for clip in bg_clip:
				if clip >= 0:
					index = bg_clip.index(clip)
					offset_index = 0 if index == 1 else 1
					bg_clip[index] = self.background.shape[index] + self.bg_offset[offset_index]
		except (AttributeError, IndexError):
			raise ValueError("Argument dimensions must be a an iterable integer pair (height x width) ")

		# apply clipping if needed
		self.foreground = self.foreground[0:fg_clip[0], 0:fg_clip[1]]
		self.background = self.background[0:bg_clip[0], 0:bg_clip[1]]

		# insert old background and foreground into their positions on new arrays
		y1 = self.bg_offset[1]
		y2 = self.background.shape[0]
		x1 = self.bg_offset[0]
		x2 = self.background.shape[1]
		new_bg[y1: y2, x1: x2, :] = self.background

		y1 = self.fg_offset[1]
		y2 = self.foreground.shape[0]
		x1 = self.fg_offset[0]
		x2 = self.foreground.shape[1]
		new_fg[y1:y2, x1:x2, :] = self.foreground

		self.foreground = new_fg
		self.background = new_bg

		# self.__update_shape()

		return self

	def render(self, prerendering=False):
		# todo: add functionality for not using a copy, ie. permanently render
		"""

		:param prerendering:  Legacy argument; left in for backwards compatibility
		:return: :raise ValueError:
		"""

		if self.background is None and self.foreground is None:
			raise ValueError('Nothing to render; NumpySurface has been initialized but not content has been added.')
		if self.background is None:
			render_surface = copy(self.foreground)
		else:  # flatten background and foreground together
			render_surface = np.zeros((self.height, self.width, 4))
			bg_x1 = self.__background_offset__[0]
			bg_x2 = bg_x1 + self.background.shape[1]
			bg_y1 = self.__background_offset__[1]
			bg_y2 = bg_y1 + self.background.shape[0]

			fg_x1 = self.__foreground_offset__[0]
			fg_x2 = fg_x1 + self.foreground.shape[1]
			fg_y1 = self.__foreground_offset__[1]
			fg_y2 = fg_y1 + self.foreground.shape[0]

			render_surface[bg_y1: bg_y2, bg_x1: bg_x2] = self.background
			render_surface[fg_y1: fg_y2, fg_x1: fg_x2] = self.foreground

		self.rendered = render_surface.astype(np.uint8)
		return self.rendered

	def __update_shape__(self):
		for surface in [self.foreground, self.background]:
			try:
				if self.width < surface.shape[1]:
					self.width = surface.shape[1]
				if self.height < surface.shape[0]:
					self.height = surface.shape[0]
			except AttributeError:
				pass

		return True

	def __set_foreground__(self, foreground_content=None):
		if foreground_content.shape[1] > self.width:
			self.width = foreground_content.shape[1]
		if foreground_content.shape[0] > self.height:
			self.height = foreground_content.shape[0]
		self.__foreground__ = foreground_content
		self.fg = self.__foreground__  # convenience alias

	def __set_background__(self, background_content):
		if background_content.shape[1] > self.width:
			self.width = background_content.shape[1]
		if background_content.shape[0] > self.height:
			self.height = background_content.shape[0]
		self.__background__ = background_content
		self.bg = self.__background__  # convenience alias

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
		from klibs.KLGraphics import aggdraw_to_array
		if foreground_content is None:
			self.__foreground__ = None
			self.fg = self.__foreground__
			return
		try:
			fg_array = add_alpha_channel(foreground_content)  # ie. numpy.ndarray
		except AttributeError:
			try:
				self.layer_from_file(foreground_content, True, self.fg_offset)  # ie. path (string)
				return
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
	def background(self):
		return self.__background__

	@background.setter
	def background(self, background_content):
		from klibs.KLGraphics import aggdraw_to_array
		if background_content is None:
			self.__background__ = None
			self.bg = self.__background__
			return
		try:
			bg_array = add_alpha_channel(background_content)  # ie. numpy.ndarray
		except AttributeError:
			try:
				self.layer_from_file(background_content, True, self.bg_offset)  # ie. path (string)
				return
			except AttributeError:
				try:
					bg_array = background_content.background  # ie. KLNumpySurface.NumpySurface
				except AttributeError:
					try:
						bg_array = background_content.render().background  # ie. KLDraw.Drawbject
					except AttributeError:
						try:
							bg_array = aggdraw_to_array(background_content)
						except:
							raise TypeError("Invalid type for initializing a NumpySurface layer.")
		if bg_array.shape[1] > self.width:
			self.width = bg_array.shape[1]
		if bg_array.shape[0] > self.height:
			self.height = bg_array.shape[0]
		self.__background__ = bg_array
		self.bg = self.__background__  # convenience alias

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

	@property
	def bg_offset(self):
		return self.__background_offset__

	@bg_offset.setter
	def bg_offset(self, offset):
		try:
			iter(offset)
			self.__background_offset__ = offset
		except TypeError:
			if offset is None:
				self.__background_offset__ = (0, 0)
			else:
				raise ValueError("Background and foreground offsets must be iterable.")

