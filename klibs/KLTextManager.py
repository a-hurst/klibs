__author__ = 'jono'
import os, math, numpy
from KLNumpySurface import NumpySurface
from PIL import ImageFont
from KLUtilities import *

from KLConstants import *
import KLParams as Params

class TextStyle(object):

	def __init__(self):
		self.font_size = Params.default_font_size
		self.color = [22, 22, 22, 255]
		self.background_color = [0, 0, 0, 0]
		self.font_name = "Arial"
		self.font_file_name = "Arial"
		self.font_extension = "ttf"
		self.line_height = 1


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

		# set a default font, using Trebuchet if not passed; Helvetica is a font suitcase in OS X, and because fuck arial
		try:
			iter(default_font)
			try:
				default_font_name, default_font_extension = default_font
				default_font_filename = default_font_name
			except ValueError:
					default_font_name, default_font_filename, default_font_extension = default_font
		except TypeError:
			default_font_name, default_font_filename, default_font_extension = ["Arial", "Arial", "ttf"]

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

	def size(self, text):  # TODO: What is this function for?
		rendering_font = ImageFont.truetype(self.default_font, self.__default_font_size)
		return rendering_font.size()

	def wrapped_text(self, text, width=None, font=None, font_size=None, color=None, bg_color=None, line_height=None):
		lines = text.split("\n")
		if width:
			pass  # test various lengths until you get a size that works, then re-populate lines
		lines_surfs = [self.render_text(line, font, font_size, color, bg_color) for line in lines ]
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

	def render_text(self, string, font=None, font_size=None, color=None, bg_color=None):
		strings  = string.split("\n")
		if len(strings) > 1:
			return self.wrapped_text(string, None, font, font_size, color, bg_color)
		if not color:
			color = self.default_color
		if not font:
			font = self.default_font
		if len(color) == 3:
			color = rgb_to_rgba(color)
		if bg_color and len(bg_color) == 3:
			bg_color = rgb_to_rgba(bg_color)
		else:
			bg_color = (0, 0, 0, 0)
		rendering_font = self.__compile_font(font_name=font, font_size=font_size, )
		glyph_bitmap = rendering_font.getmask(string, mode="L")  # L = antialiasing mode
		bitmap_as_1d_array = numpy.asarray(glyph_bitmap)
		bitmap_as_2d_array = numpy.reshape(bitmap_as_1d_array, (glyph_bitmap.size[1], glyph_bitmap.size[0]), order='C')
		rendered_text = numpy.zeros((glyph_bitmap.size[1], glyph_bitmap.size[0], 4))
		rendered_text[:, :, 0][bitmap_as_2d_array > 0] = color[0] * bitmap_as_2d_array[bitmap_as_2d_array > 0] //  255
		rendered_text[:, :, 1][bitmap_as_2d_array > 0] = color[1] * bitmap_as_2d_array[bitmap_as_2d_array > 0] //  255
		rendered_text[:, :, 2][bitmap_as_2d_array > 0] = color[2] * bitmap_as_2d_array[bitmap_as_2d_array > 0] //  255
		rendered_text[:, :, 3][bitmap_as_2d_array > 0] = color[3] * bitmap_as_2d_array[bitmap_as_2d_array > 0] // 255
		rendered_text[:, :, 0][bitmap_as_2d_array == 0] = bg_color[0]
		rendered_text[:, :, 1][bitmap_as_2d_array == 0] = bg_color[1]
		rendered_text[:, :, 2][bitmap_as_2d_array == 0] = bg_color[2]
		rendered_text[:, :, 3][bitmap_as_2d_array == 0] = bg_color[3]
		return NumpySurface(rendered_text.astype(numpy.uint8))

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
			if os.path.isfile(sys_path):
				self.fonts[font_name] = sys_path
			elif os.path.isfile(app_path):
				self.fonts[font_name] = app_path
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

	@property
	def default_font_size(self):
		return self.__default_font_size

	@default_font_size.setter
	def default_font_size(self, size):
		"""

		:param size:
		"""
		if type(size) is str:
			self.__default_font_size = self.font_sizes[size]
		elif type(size) is int:
			size = str(size) + "pt"
			self.__default_font_size = self.font_sizes[size]

	@property
	def default_font(self):
		"""

		:return:
		"""
		return self.__default_font

	@default_font.setter
	def default_font(self, font):
		"""

		:param font:
		:raise:
		"""
		self.__default_font = font

	def add_query(self, label, string):
		if type(label) is str and type(string) is str:
			self.labels[label] = string