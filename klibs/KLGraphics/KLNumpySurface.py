__author__ = 'Jonathan Mulle & Austin Hurst'

from copy import copy

import numpy as np
from PIL import Image
from PIL import ImageOps, ImageChops
import aggdraw

from klibs.KLConstants import NS_BACKGROUND, NS_FOREGROUND, BL_TOP_RIGHT, BL_TOP_LEFT
from .utils import (_build_registrations, aggdraw_to_array, image_file_to_array, add_alpha,
	rgb_to_rgba)



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

	def __init__(self, content=None, fg_offset=None, width=None, height=None, fill=(0,0,0,0)):

		if content is None and not (width and height):
			raise ValueError('If no content given, surface width and height must both be provided.')
		for i in (width, height):
			if i != None and int(i) < 1:
				raise ValueError('NumpySurface width and height must both be >= 1.')
		if not len(fill) in (3, 4):
			raise TypeError("Fill color must be a tuple of RGB or RGBA values.")

		self.__content = None
		self.__foreground_offset__ = None
		self.__height = None
		self.__width = None
		self.__fill = rgb_to_rgba(fill)

		self.rendered = None
		self.fg_offset = fg_offset
		self.__init_content(content)


	def __str__(self):
		return "klibs.NumpySurface, ({0} x {1}) at {2}".format(self.width, self.height, hex(id(self)))


	def __ensure_writeable__(self, layer=NS_FOREGROUND):
		if layer == NS_FOREGROUND:
			try:
				self.foreground.setflags(write=1)
			except AttributeError:
				self.__content =  np.zeros((self.width, self.height, 4))
				self.__ensure_writeable__(NS_FOREGROUND)


	def __init_content(self, new):
		from .KLDraw import Drawbject

		if new is None:
			new = Image.new('RGBA', (self.width, self.height), self.__fill)
			new_arr = np.asarray(new)
		elif isinstance(new, np.ndarray):
			new_arr = add_alpha(new)
		elif isinstance(new, NumpySurface):
			new_arr = new.content
		elif isinstance(new, Drawbject):
			new_arr = new.render()
		elif isinstance(new, Image.Image):
			if new.mode == 'RGB':
				new_arr = add_alpha(np.array(new))
			else:
				if new.mode != 'RGBA':
					new = new.convert('RGBA')
				new_arr = np.array(new)
		elif type(new).__name__ in ('str', 'unicode'):
			new_arr = image_file_to_array(new)
		elif type(new).__name__ == 'Draw': # aggdraw surface
			new_arr = aggdraw_to_array(new)
		else:
			TypeError("Invalid type for initializing a NumpySurface object.")

		self.__content = new_arr.astype(np.uint8)
		self.__update_shape()


	def __update_shape(self):
		try:
			self.__width = self.__content.shape[1]
			self.__height = self.__content.shape[0]
		except AttributeError:
			pass


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
		self.__content[y1: y2, x1: x2, :] = source

		return self


	def scale(self, size, layer=None):
		# TODO: expand this considerably;  http://pillow.readthedocs.org/en/3.0.x/reference/ImageOps.html
		if not self.has_content():
			return

		if layer == NS_FOREGROUND or layer is None:
			try:
				layer_image = Image.fromarray(self.foreground.astype(np.uint8))
				scaled_image = layer_image.resize(size, Image.ANTIALIAS)
				self.__content =  np.asarray(scaled_image)
			except AttributeError as e:
				if str(e) != "'NoneType' object has no attribute '__array_interface__'":
					raise e
			except TypeError:
				pass

		self.__update_shape()
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
				self.__content =  np.asarray(scaled_image)
			except AttributeError as e:
				if str(e) != "'NoneType' object has no attribute '__array_interface__'":
					raise e
			except TypeError:
				pass
		self.__update_shape()
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


	def mask(self, mask, registration=7, location=(0,0), complete=False, invert=True):
		"""Applies a transparency mask to the surface at a given location.
		
		If 'invert' is True (the default), the opacity of the mask is subtracted from the opacity
		of the surface, making the surface fully transparent wherever the mask is fully opaque
		(and vice versa). If 'invert' is False, this replaces the surface's transparency layer with
		the mask's alpha for the region covered by the mask.

		If an RGBA mask is provided, this function will use its alpha channel for masking. If a
		greyscale ('L') mask is provided, it will be used directly. If a mask in any other format
		is provided, the values from its first channel (e.g. 'R' for RGB, 'C' for CMYK) will be
		used.

		Args:
			mask (:obj:`NumpySurface`, :obj:`numpy.ndarray`): The image or array to use as a
				transparency mask.
			registration (int, optional): An integer from 1 to 9 indicating which location on the
				mask should be aligned to the location coordinates (see manual for more info).
			location ([int, int], optional): The (x, y) pixel coordinates on the target surface
				at which to place the mask. Defaults to (0, 0).
			complete (bool, optional): If True, the entire surface outside of the mask region
				will be made transparent. Defaults to False.				
			invert (bool, optional): Whether the alpha values in the mask region should be
				the inverse of the mask's alpha instead of the same. Defaults to True.

		"""
		from .KLDraw import Drawbject

		if type(mask) is NumpySurface:
			mask = Image.fromarray(mask.content)
		elif type(mask) is np.ndarray:
			mask = Image.fromarray(mask.astype(np.uint8))
		elif isinstance(mask, Drawbject):
			mask = mask.draw()
		elif not isinstance(mask, Image.Image):
			typename = type(mask).__name__
			raise TypeError("'{0}' is not a valid mask type.".format(typename))

		# For handling legacy code where location was second argument
		if hasattr(registration, '__iter__') and not isinstance(registration, str):
			location = registration
			registration = 7

		registration = _build_registrations(mask.height, mask.width)[registration]
		location = (int(location[0] + registration[0]), int(location[1] + registration[1]))

		# Initialize surface and mask
		surface_content = Image.fromarray(self.content)
		surface_alpha = surface_content.getchannel('A')
		if mask.mode != 'L':
			try:
				mask = mask.getchannel('A')
			except:
				mask = mask.getchannel(0)
		if invert == True:
			mask = ImageChops.invert(mask)

		# Create a new surface-sized alpha layer and place the mask on it
		mask_alpha = Image.new('L', surface_content.size, 0 if complete else 255)
		mask_alpha.paste(mask, location)

		# Merge the surface/mask alpha layers and replace surface alpha with result
		new_alpha = ImageChops.darker(surface_alpha, mask_alpha)
		surface_content.putalpha(new_alpha)
		self.__content = np.array(surface_content)

		return self


	def prerender(self):
		"""


		:return:
		"""
		return self.render()


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
			return self.__update_shape()

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
		self.__content =  self.foreground[0:fg_clip[0], 0:fg_clip[1]]

		y1 = self.fg_offset[1]
		y2 = self.foreground.shape[0]
		x1 = self.fg_offset[0]
		x2 = self.foreground.shape[1]
		new_fg[y1:y2, x1:x2, :] = self.foreground

		self.__content =  new_fg

		self.__update_shape()

		return self


	def render(self):
		"""Renders and returns the contents of the NumpySurface as an RGBA texture.

		Returns:
			:obj:`numpy.ndarray`: A 3-dimensional Numpy array of an RGBA texture.

		"""
		surftype = self.content.dtype
		self.rendered = self.content if surftype == np.uint8 else self.content.astype(np.uint8)
		return self.rendered


	@property
	def height(self):
		"""int: The current height (in pixels) of the NumpySurface.

		"""
		return self.__height


	@property
	def width(self):
		"""int: The current width (in pixels) of the NumpySurface.

		"""
		return self.__width

	
	@property
	def surface_c(self):
		"""tuple(int, int): The (x, y) coordinates of the center of the surface.

		"""
		return (int(self.width//2), int(self.height//2))
	

	@property
	def dimensions(self):
		"""tuple(int, int): The current size of the NumpySurface, in the format (width, height).

		"""
		return (self.width, self.height)


	@property
	def content(self):
		""":obj:`numpy.ndarray`: The contents of the NumpySurface.

		"""
		return self.__content


	@property
	def foreground(self):
		return self.__content


	@property
	def average_color(self):
		"""tuple of ints: The average RGBA colour of the NumpySurface.

		"""
		img = Image.fromarray(self.content.astype(np.uint8))
		return img.resize((1,1), Image.ANTIALIAS).getpixel((0,0))

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
