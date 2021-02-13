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
	"""A flexible object for working with images and other textures. Can be used for loading
	image files, converting images into a :func:`~klibs.KLGraphics.blit`-able format, applying
	transparency masks to images, merging multiple images into one, resizing images, and more. 

	By default, the height and width of the surface will be inferred from the input content. If
	a width and height are provided, the content will be stretched to fit the given size. If
	only one dimension is provided, the content will be scaled to that size preserving the
	aspect ratio of the image. If a surface is created without any content, both a width and
	height must be specified.

	All NumpySurface objects use the RGBA colour format, and any valid input types in other
	formats (e.g. RGB) will be coerced to RGBA when the NumpySurface is created.

	Supported input types:

	* Pillow Image (:obj:`PIL.Image.Image`)

	* RGB or RGBA Numpy array (:obj:`numpy.ndarray`)

	* Shape from :mod:`~klibs.KLGraphics.KLDraw` (:obj:`~klibs.KLGraphics.KLDraw.Drawbject`)

	* Aggdraw drawing context (:obj:`aggdraw.Draw`)

	* NumpySurface object (:obj:`~NumpySurface`)

	* A string specifying the full path to an image file

	* A string specifying the path to an image file relative to the project's 
	  `ExpAssets/Resources/image` directory

	* :obj:`NoneType` (initializes a new surface with a given width, height, and fill)

	A list of supported formats for images loaded via file path can be found
	`here <https://pillow.readthedocs.io/en/5.1.x/handbook/image-file-formats.html>`_.

	Args:
		content (optional): The image, shape, or other texture to create the surface with.
		width (int, optional): The width of the new surface.
		height (int, optional): The height of the new surface.
		fill (:obj:`tuple` or :obj:`list`, optional): The fill colour of the new surface. 
			Defaults to fully transparent.

	"""
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

		self.fg_offset = fg_offset
		self.__init_content(content)
		if content is not None and (width or height):
			self.scale(width, height)


	def __repr__(self):
		s = "<klibs.KLGraphics.NumpySurface(width={0}, height={1}) at {2}>"
		return s.format(self.width, self.height, hex(id(self)))


	def __str__(self):
		return "NumpySurface(width={0}, height={1})".format(self.width, self.height)


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


	def render(self):
		"""Renders and returns the contents of the NumpySurface as an RGBA texture.

		Returns:
			:obj:`numpy.ndarray`: A 3-dimensional RGBA array of the surface content.

		"""
		surftype = self.content.dtype
		return self.content if surftype == np.uint8 else self.content.astype(np.uint8)


	def blit(self, source, registration=7, location=(0,0), clip=True, blend=True):
		"""Draws a shape, image, or other texture at a given location on the surface.

		Valid source content types include :obj:`NumpySurface` objects, :obj:`Drawbject` shapes,
		and :obj:`numpy.ndarray` or :obj:`Pillow.Image` objects in RGBA format.

		Args:
			source: The content to draw to the surface.
			registration (int, optional): An integer from 1 to 9 indicating which point on the
				source to align to the location coordinates. Defaults to 7 (top-left corner).
			location([int, int], optional): The (x, y) pixel coordinates indicating where the 
				content should be placed on the surface. Defaults to (0, 0).
			clip (bool, optional): Whether to clip content that exceeds the bounds of the surface
				to fit instead of raising an exception. Defaults to True.
				exceed the margins of the surface, or return an error instead. Defaults to True.
			blend (bool, optional): Whether to blend the image with the existing background or
				simply replace the contents of the target region (faster). Defaults to True
				(blend source with surface).

		Raises:
			ValueError: if the source does not fit on the surface with the given registration
				and location.

		"""
		# TODO: Add reference to location/registration explanation in the docstring once it's written
		if isinstance(source, np.ndarray):
			source = add_alpha(source)
		elif isinstance(source, NumpySurface):
			source = source.render()
		else:
			try:
				source = NumpySurface(source)
				source = source.render()
			except TypeError:
				e = "'{0} is not a supported NumpySurface content format."
				raise TypeError(e.format(type(source).__name__))

		# Calculate top-left corner for source, using location, registration, & size
		source_h, source_w = (source.shape[0], source.shape[1])
		r_x, r_y = _build_registrations(source_h, source_w)[registration]
		location = (int(location[0] + r_x), int(location[1] + r_y))
		
		# Get source dimensions (sx/sy) and source bounding box on surface (cx/cy)
		sx1, sy1, sx2, sy2 = (0, 0, source_w, source_h)
		cx1, cy1, cx2, cy2 = location + (location[0] + source_w, location[1] + source_h)

		# Make sure location/registration actually place source on surface
		if cx1 > self.width or cy1 > self.height or cx2 < 0 or cy2 < 0:
			e = ("Provided blit location ({0}, {1}) and registration ({2}) place source "
				"completely outside surface bounds.")
			raise ValueError(e.format(cx1, cy1, registration))

		# If source is partly outside surface, adjust dimensions & bounding box to clip
		if clip == True:
			if cx1 < 0: sx1, cx1 = (abs(cx1), 0)
			if cy1 < 0: sy1, cy1 = (abs(cy1), 0)
			if cx2 > self.width: sx2, cx2 = (sx2 + (self.width - cx2), self.width)
			if cy2 > self.height: sy2, cy2 = (sy2 + (self.height - cy2), self.height)
		else:
			if source_h > self.height or source_w > self.width:
				e = "Source ({0}x{1}) is larger than the destination surface ({2}x{3})"
				raise ValueError(e.format(source_w, source_h, self.width, self.height))
			elif cx1 < 0 or cy1 < 0 or cx2 > self.width or cy2 > self.height:
				e = ("Provided blit location ({0}, {1}) and registration ({2}) place source "
					"partially outside surface bounds.")
				raise ValueError(e.format(cx1, cy1, registration))

		# Add source to surface, optionally blending alpha channels
		if blend == True:
			img = Image.fromarray(self.content)
			src = Image.fromarray(source[sy1:sy2, sx1:sx2, :])
			img.alpha_composite(src, (cx1, cx2))
			self.__content = np.array(img)
		else:
			self.__content[cy1:cy2, cx1:cx2, :] = source[sy1:sy2, sx1:sx2, :]

		return self


	def scale(self, width=None, height=None):
		"""Scales the surface and its contents to a given size. If only one dimension is provided,
		the contents will be scaled to that size preserving the surface's aspect ratio. If both
		height and width are provided, the surface contents will be stretched to fit.

		Args:
			width (int, optional): The width in pixels to scale the surface to.
			height (int, optional): The height in pixels to scale the surface to.

		Raises:
			ValueError: if neither height or width are provided.
		
		"""
		aspect = self.width / float(self.height)
		if width != None:
			size = (width, height) if height != None else (width, int(round(width / aspect)))
		elif height != None:
			size = (int(round(height * aspect)), height)
		else:
			raise ValueError("At least one of 'height' or 'width' must be provided.")

		img = Image.fromarray(self.content)
		self.__content = np.array(img.resize(size, Image.ANTIALIAS))
		self.__update_shape()

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
			registration (int, optional): An integer from 1 to 9 indicating which point on the
				mask to align to the location coordinates. Defaults to 7 (top-left corner).
			location ([int, int], optional): The (x, y) pixel coordinates indicating where the 
				mask should be placed on the surface. Defaults to (0, 0).
			complete (bool, optional): If True, the entire surface outside of the mask region
				will be made transparent. Defaults to False.				
			invert (bool, optional): Whether the alpha values in the mask region should be
				the inverse of the mask's alpha instead of the same. Defaults to True.

		"""
		# TODO: Add reference to location/registration explanation in the docstring once it's written
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


	def get_pixel_value(self, coords):
		"""Retrieves the RGBA colour value of a given pixel of the surface.

		Args:
			coords([int, int]): The (x, y) coordinates of the pixel to retrieve.

		Returns:
			tuple: The RGBA value of the specified pixel.

		Raises:
			ValueError: If the given coords do not correspond to a pixel on the surface.

		"""
		try:
			return tuple(self.content[coords[1]][coords[0]])
		except IndexError:
			e = "Coordinates ({0}, {1}) do not correspond to a pixel on the surface."
			raise ValueError(e.format(coords[0], coords[1]))


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
