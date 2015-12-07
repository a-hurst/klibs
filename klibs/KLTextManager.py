__author__ = 'jono'
import os, math, numpy
from KLNumpySurface import NumpySurface
from PIL import ImageFont
from sdl2 import sdlttf
from KLUtilities import *

from KLConstants import *
import KLParams as Params


def argb_to_rgba(val):
	print val.shape
	changed = numpy.apply_along_axies(sdl2.ext.rgba_to_color, 0, val)
	print changed.shape


class TextStyle(object):

	def __init__(self, label, font_size=None, color=None, bg_color=None, line_height=None, font_label=None):
		"""

		:param label:
		:type label: String
		:param font_size:
		:type font_size: String, Int
		:param color:
		:type color: Iterable
		:param bg_color:
		:type bg_color: Iterable
		:param line_height:
		:type line_height: Int
		:param font_label:
		:type font_label: String or Iterable
		"""
		self.label = label
		self.font_size = font_size if font_size else Params.default_font_size
		self.font_label = font_label if font_label else Params.default_font_name
		self.color = rgb_to_rgba(color) if color else (22, 22, 22, 255)
		self.bg_color = rgb_to_rgba(bg_color) if bg_color else (0, 0, 0, 0)
		self.line_height = line_height if line_height else 1.5

	def __str__(self):
		return "klibs.KLTextManager.TextStyle ('{0}') at {1}".format(self.label, hex(id(self)))


class TextManager(object):
	asset_path = "ExpAssets"
	alert_color = (255, 0, 0, 255)
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


	def __init__(self):
		self.__build_font_sizes()
		self.add_font("Anonymous Pro", font_file_basename="AnonymousPro")
		self.add_font("Frutiger")
		self.add_style("debug", 16, (255, 255, 255, 255), bg_color=(0, 0, 0, 0), font_label="Anonymous Pro")
		self.add_style("default", "16pt", [22, 22, 22], font_label="Frutiger")
		sdlttf.TTF_Init()

	def __build_font_sizes(self):
		size_list = range(3, 96)
		self.font_sizes = {}
		for num in size_list:
			key = str(num) + 'pt'
			self.font_sizes[key] = int(math.floor(1.0 / 72 * Params.ppi * num))

	def __compile_font(self, font, font_size):
		# process font_size argument or assign a default
		try:
			font_size = self.font_sizes[font_size]
		except KeyError:
			if type(font_size) is not int:
				raise TypeError("Argument 'font_size' must be a string (ie. '18pt') or int describing pixel height.")

		return ImageFont.truetype(self.fonts[font], font_size)

	def add_style(self, label, font_size=None, color=None, bg_color=None, line_height=None, font_label=None):
		self.styles[label] = TextStyle(label, font_size, color, bg_color, line_height, font_label)

	def __wrap(self, text, style, width=None):
		lines = text.split("\n")
		if width:
			pass  # TODO: test various lengths until you get a size that works, then re-populate lines
		lines_surfs = []
		for line in lines:
			if len(line):
				lines_surfs.append(self.render(line, style))
		text_dims = [0,0]
		line_height = style.line_height * lines_surfs[0].height
		for line in lines_surfs:
			if line.width > text_dims[0]: text_dims[0] = line.width
			text_dims[1] += int(line_height)
		# text_surface = NumpySurface(width=text_dims[0], height=text_dims[1])
		# for line in lines_surfs:
		# 	if line.height != 0:
		# 		text_surface.blit(line, position=[0, y_pos], behavior="extend")
		# 		y_pos += line_height
		for l in lines_surfs:
			l.resize([text_dims[0], l.height])
		text_surface = numpy.concatenate([l.render() for l in lines_surfs], 0)

		# text_surface = NumpySurface( text_surface )

		return text_surface
		# return lines_surfs

	def render(self, text, style="default"):
		"""

		:param text:
		:type text: String
		:param style:
		:type style: :class:`~klibs.KLTextManager.TextStyle`
		:return:
		"""

		#  The following vars are an intermediary stage in converting TextManager to the use of style objects
		if not isinstance(style, TextStyle):
			style = self.styles[style]

		if len(text.split("\n")) > 1:
			return self.__wrap(text, style)

		if len(text) == 0:
			text = " "
		# Attempting to use SDL font rendering...
		#
		# rendering_font = sdlttf.TTF_OpenFont(self.fonts[style.font_label], 24)
		# rendered_text = sdlttf.TTF_RenderText_Blended(rendering_font, text, sdl2.SDL_Color(*style.color)).contents
		# rendered_text = numpy.asarray(rendered_text)
		# rendered_text = list(sdl2.ext.PixelView(rendered_text))
		# rendered_text = numpy.asarray(rendered_text)
		# to_rgba = numpy.vectorize(sdl2.ext.rgba_to_color)
		# rendered_text = to_rgba(rendered_text)
		# rendered_text_rgba = numpy.apply_along_axis(sdl2.ext.rgba_to_color, 0, numpy.vectorize(rendered_text))
		# print rendered_text
		# for row in rendered_text:
		# 	rgba_row = []
		# 	for col in row:
		# 		rgba = list(sdl2.ext.rgba_to_color(col))
		# 		rgba2 = rgba[1:]
		# 		rgba2.append(rgba[0])
		# 		rgba_row.append(rgba2)
		# 	rendered_text_rgba.append(rgba_row)
		# surface = NumpySurface(rendered_text.astype(numpy.uint8))

		rendering_font = self.__compile_font(style.font_label, style.font_size)
		glyph_bitmap = rendering_font.getmask(text, mode="L")  # L = antialiasing mode
		bitmap_1d = numpy.asarray(glyph_bitmap)
		bitmap_2d = numpy.reshape(bitmap_1d, (glyph_bitmap.size[1], glyph_bitmap.size[0]), order='C')
		nonzero_2d_bitmap = bitmap_2d[bitmap_2d > 0]
		rendered_text = numpy.zeros((glyph_bitmap.size[1], glyph_bitmap.size[0], 4))
		rendered_text[:, :, 0][bitmap_2d > 0] = style.color[0] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 1][bitmap_2d > 0] = style.color[1] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 2][bitmap_2d > 0] = style.color[2] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 3][bitmap_2d > 0] = style.color[3] * nonzero_2d_bitmap //  255
		rendered_text[:, :, 0][bitmap_2d == 0] = style.bg_color[0]
		rendered_text[:, :, 1][bitmap_2d == 0] = style.bg_color[1]
		rendered_text[:, :, 2][bitmap_2d == 0] = style.bg_color[2]
		rendered_text[:, :, 3][bitmap_2d == 0] = style.bg_color[3]
		surface = NumpySurface(rendered_text.astype(numpy.uint8))

		return surface if surface.width < Params.screen_x else self.__wrap(text, style, Params.screen_x - 20)

	def add_font(self, font_name, font_extension="ttf", font_file_basename=None):
		"""

		:param font_name: Reference name of font within experiment context; typically mirrors filename.
		:type font_name: String
		:param font_extension: File extension of the font's file, usually, 'ttf' or 'otf'.
		:param font_file_basename: Filename without extension of file; used when font_name does not match filename.
		:return:
		"""
		if not font_file_basename:
			font_file_basename = ".".join([font_name, font_extension])
		else:
			font_file_basename = ".".join([font_file_basename, font_extension])

		for d in Params.font_dirs:
			if os.path.isfile(os.path.join(d, font_file_basename)):
				self.fonts[font_name] = os.path.join(d, font_file_basename)
		if not font_name in self.fonts:
			raise ImportError("Font {0} not found in any expected destination.".format(font_file_basename))
		return self

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


# def render(self, text, font_path, font_size=12, color=(0, 0, 0, 255), bg_color=(0, 0, 0, 0)):
# 	rendering_font = ImageFont.truetype(font_path, font_size)
# 	glyph_bitmap = rendering_font.getmask(text, mode="L")  # L = antialiasing mode
# 	bitmap_1d = numpy.asarray(glyph_bitmap)
# 	bitmap_2d = numpy.reshape(bitmap_1d, (glyph_bitmap.size[1], glyph_bitmap.size[0]), order='C')
# 	nonzero_2d_bitmap = bitmap_2d[bitmap_2d > 0]
# 	rendered_text = numpy.zeros((glyph_bitmap.size[1], glyph_bitmap.size[0], 4))
# 	rendered_text[:, :, 0][bitmap_2d > 0] = color[0] * nonzero_2d_bitmap //  255
# 	rendered_text[:, :, 1][bitmap_2d > 0] = color[1] * nonzero_2d_bitmap //  255
# 	rendered_text[:, :, 2][bitmap_2d > 0] = color[2] * nonzero_2d_bitmap //  255
# 	rendered_text[:, :, 3][bitmap_2d > 0] = color[3] * nonzero_2d_bitmap //  255
# 	rendered_text[:, :, 0][bitmap_2d == 0] = bg_color[0]
# 	rendered_text[:, :, 1][bitmap_2d == 0] = bg_color[1]
# 	rendered_text[:, :, 2][bitmap_2d == 0] = bg_color[2]
# 	rendered_text[:, :, 3][bitmap_2d == 0] = bg_color[3]
# 	return rendered_text.astype(numpy.uint8)
