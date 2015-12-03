__author__ = 'jono'
import os, math, numpy
from KLNumpySurface import NumpySurface
from PIL import ImageFont
from KLUtilities import *

from KLConstants import *
import KLParams as Params

class TextStyle(object):

	def __init__(self, label, font_size=None, color=None, bg_color=None, line_height=None, font=None):
		if font:
			try:
				iter(font)
			except AttributeError:
				font = [font, font, "ttf"]
		self.font_size = font_size if font_size else Params.default_font_size
		self.color = rgb_to_rgba(color) if color else [22, 22, 22, 255]
		self.bg_color = rgb_to_rgba(bg_color) if bg_color else [0, 0, 0, 0]
		self.font_name = font[0] if font else Params.default_font_name
		self.font_extension = font[2] if font else "ttf"
		self.font_file_name = "{0}.{1}".format(font[1] if font else Params.default_font_name, self.font_extension)
		self.line_height = line_height if line_height else 1
		self.label = label


class TextManager(object):
	asset_path = "ExpAssets"
	alert_color = (255, 0, 0, 255)
	fonts_directory_path = "/Library/Fonts"
	fonts = {}
	font_sizes = {}
	labels = {}
	monitor_x = None
	monitor_y = None
	queue = {}
	strings = {}
	window_x = None
	window_y = None
	default_font_size = None
	styles = {}
	legacy_styles_count = 0
	__default_color = (0, 0, 0, 255)
	__default_input_color = (3, 118, 163, 255)
	__default_bg_color = (255, 255, 255)
	__default_font_size = None
	__default_font = None
	__default_message_duration = 1


	def __init__(self, default_font=None, default_font_size="18pt", fonts_directory_path=None):
		if fonts_directory_path:
			self.fonts_directory_path = fonts_directory_path

		self.__build_font_sizes()
		self.default_font_size = default_font_size
		self.add_font("Anonymous Pro", font_file_name="AnonymousPro")
		self.add_style("debug panel", "12pt", [255, 255, 255], ["Anonymous Pro", "AnonymousPro", "ttf"])

		try:
			iter(default_font)
			try:
				default_font_name, default_font_extension = default_font
				default_font_filename = default_font_name
			except ValueError:
					default_font_name, default_font_filename, default_font_extension = default_font
		except TypeError:
			default_font_name, default_font_filename, default_font_extension = ["Frutiger", "Frutiger", "ttf"]

		self.add_font(default_font_name, default_font_extension, default_font_filename, True)

	def __build_font_sizes(self):
		size_list = range(3, 96)
		self.font_sizes = {}
		for num in size_list:
			key = str(num) + 'pt'
			self.font_sizes[key] = int(math.floor(1.0 / 72 * Params.ppi * num))

	def __compile_font(self, font_name=None, font_size=None):
		# process font_size argument or assign a default
		if font_size is not None:
			if type(font_size) is str:
				font_size = self.font_sizes[font_size]
			if type(font_size) is not int:
				raise TypeError("font_size must be either a point-string (ie. 18pt) or an int describing pixel height.")
		elif self.__default_font_size:
			font_size = self.__default_font_size
		else:
			raise ValueError("font_size argument is  required or else  default_font_size must be set prior to calling.")
		if not font_name:
			font_name = self.default_font
		return ImageFont.truetype(self.fonts[font_name], font_size)

	def size(self, text, style=None):
		"""
		Returns the height in pixels of a single line of text using the provided style
		:param text:
		:return:
		"""
		rendering_font = ImageFont.truetype(self.default_font, self.__default_font_size)
		return rendering_font.size()

	def add_style(self, label, font_size=None, color=None, bg_color=None, line_height=None, font=None):
		self.styles[label] = TextStyle(font_size, color, bg_color, line_height, font)

	def __wrap(self, text, style, width=None):
		lines = text.split("\n")
		if width:
			pass  # test various lengths until you get a size that works, then re-populate lines
		lines_surfs = [self.render(line, style) for line in lines ]
		text_dims = [0,0]
		for line in lines_surfs:
			if line.width > text_dims[0]: text_dims[0] = line.width
			if line_height is None: line_height = 1.5 * line.height
			text_dims[1] += int(line_height)
		y_pos = 0
		text_surface = NumpySurface(width=text_dims[0], height=text_dims[1])
		for line in lines_surfs:
			text_surface.blit(line, position=[0, y_pos], behavior="extend")
			y_pos += line_height

		return text_surface

	def render(self, string, style):
		"""

		:param string:
		:param style:
		:return:
		"""

		#  The following vars are an intermediary stage in converting TextManager to the use of style objects
		if not isinstance(style, TextStyle):
			style = self.styles[style]

		font = ".".join([style.font_file_name, style.font_extension])
		font_size = style.font_size
		strings  = string.split("\n")
		if len(strings) > 1:
			return self.__wrap(string, style)
		rendering_font = self.__compile_font(font_name=style.font_name, font_size=style.font_size, )
		glyph_bitmap = rendering_font.getmask(string, mode="L")  # L = antialiasing mode
		bitmap_as_1d_array = numpy.asarray(glyph_bitmap)
		bitmap_as_2d_array = numpy.reshape(bitmap_as_1d_array, (glyph_bitmap.size[1], glyph_bitmap.size[0]), order='C')
		nonzero_2d_bitmap = bitmap_as_2d_array[bitmap_as_2d_array > 0]
		rendered_text = numpy.zeros((glyph_bitmap.size[1], glyph_bitmap.size[0], 4))
		rendered_text[:, :, 0][bitmap_as_2d_array > 0] = style.color[0] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 1][bitmap_as_2d_array > 0] = style.color[1] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 2][bitmap_as_2d_array > 0] = style.color[2] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 3][bitmap_as_2d_array > 0] = style.color[3] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 0][bitmap_as_2d_array == 0] = style.bg_color[0]
		rendered_text[:, :, 1][bitmap_as_2d_array == 0] = style.bg_color[1]
		rendered_text[:, :, 2][bitmap_as_2d_array == 0] = style.bg_color[2]
		rendered_text[:, :, 3][bitmap_as_2d_array == 0] = style.bg_color[3]
		surface = NumpySurface(rendered_text.astype(numpy.uint8))
		return surface if surface.width < Params.screen_x else self.__wrap(string, style, Params.screen_x - 20)

	def add_font(self, font_name, font_extension="ttf", font_file_name=None, make_default=False):
		"""

		:param font_name: Name of font; should mirror file name without extension. If not, also use font_file_name argument.
		:param font_extension: File extension of the font's file, usually, 'ttf' or 'otf'.
		:param font_file_name: Use to simply 'font name' when file name is large, ie. "Arial Black CN.ttf" => "Arial"
		:return:
		"""
		if type(font_name) is str and type(font_extension) is str:
			if type(font_file_name) is not str:
				font_file_name = ".".join([font_name, font_extension])
			else:
				font_file_name = ".".join([font_file_name, font_extension])
			sys_path = os.path.join(self.fonts_directory_path, font_file_name)
			app_path = os.path.join(Params.asset_path, font_file_name)
			klibs_path = os.path.join(Params.klibs_path, font_file_name)
			if os.path.isfile(sys_path):
				self.fonts[font_name] = sys_path
			elif os.path.isfile(app_path):
				self.fonts[font_name] = app_path
			elif os.path.isfile(klibs_path):
				self.fonts[font_name] = klibs_path
			else:
				e_str = "Font file '{0}' was not found in either system fonts or experiment assets directories"
				raise ImportError(e_str.format(font_file_name))
		else:
			raise TypeError("Arguments 'font' and 'font_extension' must both be strings.")
		self.default_font = font_name
		return True

	@property
	def default_color(self):
		"""

		:return:
		"""
		return self.__default_color

	@default_color.setter
	def default_color(self, color):
		"""

		:param color:
		"""
		if type(color) is list:
			self.__default_color = color

	@property
	def default_input_color(self):
		"""

		:return:
		"""
		return self.__default_color

	@default_input_color.setter
	def default_input_color(self, color):
		"""

		:param color:
		"""
		if type(color) in (list, tuple):
			self.__default_input_color = color

	@property
	def default_bg_color(self):
		"""

		:return:
		"""
		return self.__default_bg_color

	@default_bg_color.setter
	def default_bg_color(self, color):
		"""

		:param color:
		"""
		if type(color) is list:
			self.__default_bg_color = color



	"""
		Legacy functions to map old code to new functions and/or function signatures
	"""
	# font_size = None, color = None, background_color = None, line_height = None, font = None):
	def render_text(self, string, font=None, font_size=None, color=None, bg_color=None):
		if font:
			try:
				font = self.fonts[font]
			except KeyError:
				pass
		style_name = "legacy_style_{0}".format(self.legacy_styles_count)
		style_object = TextStyle(style_name, font_size, color, bg_color, 1, font)

		# don't add a new style if it exists
		if style_object in self.styles.values():
			for l, s in self.styles.items():
				if style_object == s:
					style = l
		else:
			self.styles[style_name] =  style_object
			self.legacy_styles_count += 1
			style = style_name
		self.render(string, style)

	def wrapped_text(self, strings, width=None, font=None, font_size=None, color=None, bg_color=None, line_height=None):
		if font:
			font = font.split(".")
			font = [font[0], font[0], font[1]]
		style_name = "legacy_style_{0}".format(self.legacy_styles_count)
		style_object = TextStyle(font_size, color, bg_color, 1, font, line_height)

		# don't add a new style if it exists
		if style_object in self.styles.values():
			for l, s in self.styles.items():
				if style_object == s:
					style = l
		else:
			self.styles[style_name] = style_object
			self.legacy_styles_count += 1
			style = style_name
		self.__wrap(strings, style, width)