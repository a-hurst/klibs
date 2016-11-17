__author____ = 'jono'
from numpy import asarray, zeros, concatenate
from PIL import ImageFont
from sdl2.sdlttf import TTF_Init, TTF_OpenFont, TTF_CloseFont, TTF_RenderText_Blended, TTF_RenderUTF8_Solid
from sdl2.ext import PixelView
from sdl2 import SDL_Color
from math import floor
from os.path import isfile, join

from klibs import P
from klibs.KLConstants import TEXT_PX, TEXT_MULTIPLE, TEXT_PT
from klibs.KLUtilities import pt_to_px
from klibs.KLGraphics import NpS, rgb_to_rgba, argb32_to_rgba

class TextStyle(object):


	#todo: render_size(str, width)
	def __init__(self, label, font_size=None, color=None, bg_color=None, line_height=None, font_label=None, anti_alias=True):
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
		self.bad_unit_message = "A valid size unit was not provided; please express size as either an integer or as \
		pixels/points (ie. '12pt' or '12px')."
		self.__font_size__ = None
		self.__font_size_units__ = TEXT_PT
		self.__line_height__ = 1.5
		self.__line_height_units__ = TEXT_MULTIPLE
		self.label = label
		self.font_size = font_size if font_size else P.default_font_size
		self.font_label = font_label if font_label else P.default_font_name
		self.color = rgb_to_rgba(color) if color else (22, 22, 22, 255)
		self.bg_color = rgb_to_rgba(bg_color) if bg_color else (0, 0, 0, 0)
		self.anti_aliased = anti_alias
		if line_height:
			self.line_height = line_height


	@property
	def font_size(self):
		return self.__font_size__

	@font_size.setter
	def font_size(self, size):
		try:
			self.__font_size__ = int(size)
			self.__font_size_units__ = TEXT_PX
		except ValueError:
			self.__font_size__ = int(size[:-2])
			self.__font_size_units__ = size[-2:].upper()
			if self.__font_size_units__ not in [TEXT_PX, TEXT_PT]:
				raise ValueError(self.bad_unit_message)

	@property
	def line_height(self):
		if self.__line_height_units__ == TEXT_PX:
			return self.__line_height__
		elif self.__line_height_units__ == TEXT_MULTIPLE:
			return self.__line_height__ * self.font_size
		else:
			return  pt_to_px(self.__line_height__)

	@line_height.setter
	def line_height(self, line_height_val):
		try:
			self.__line_height__ = int(line_height_val)
			self.__line_height_units__ = TEXT_MULTIPLE
		except ValueError:
			self.__line_height__ = int(line_height_val[:-2])
			self.__line_height_units__ = line_height_val[-2:].upper()
			if self.__line_height_units__ not in [TEXT_PT, TEXT_PX]:
				raise ValueError(self.bad_unit_message)

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
	__default_color__ = (0, 0, 0, 255)
	__default_input_color__ = (3, 118, 163, 255)
	__default_bg_color__ = (255, 255, 255)
	__default_font_size__ = None
	__default_font__ = None
	__default_message_duration__ = 1


	def __init__(self):
		self.__build_font_sizes__()
		self.add_font("Anonymous Pro", font_file_basename="AnonymousPro")
		self.add_font("Frutiger")
		self.add_style("debug", 12, (225, 145, 85, 255), bg_color=(0, 0, 0, 0), font_label="Anonymous Pro", anti_alias=False)
		self.default_font_size = P.default_font_size
		self.default_color = P.default_color
		TTF_Init()

	def __build_font_sizes__(self):
		size_list = range(3, 96)
		self.font_sizes = {}
		for num in size_list:
			key = str(num) + 'pt'
			self.font_sizes[key] = int(floor(1.0 / 72 * P.ppi * num))

	def __compile_font__(self, font, font_size):
		# process font_size argument or assign a default
		try:
			font_size = self.font_sizes[font_size]
		except KeyError:
			if type(font_size) is not int:
				raise TypeError("Argument 'font_size' must be a string (ie. '18pt') or int describing pixel height.")

		return ImageFont.truetype(self.fonts[font], font_size)

	def add_style(self, label, font_size=None, color=None, bg_color=None, line_height=None, font_label=None, anti_alias=True):
		self.styles[label] = TextStyle(label, font_size, color, bg_color, line_height, font_label, anti_alias)

	def __wrap__(self, text, style, width=None):
		lines = text.split("\n")
		if width:
			pass  # TODO: test various lengths until you get a size that works, then re-populate lines
		net_line_height = style.font_size + style.line_height
		output = NpS(width=1, height=(len(lines) * net_line_height))
		for line in lines:
			if len(line):
				l_surf = self.render(line, style, True)
			else:
				l_surf = NpS(width=1, height=net_line_height)
			if l_surf.width > output.width:
				output.resize((l_surf.width, output.height))
			l_surf_pos = (0, lines.index(line) * net_line_height)
			output.blit(l_surf, position=l_surf_pos)
		return output

	def render(self, text, style="default", max_width=None, from_wrap=False):
		"""

		:param text:
		:type text: String
		:param style:
		:type style: :class:`~klibs.KLText.TextStyle`
		:return:
		"""
		text = str(text)
		#  The following vars are an intermediary stage in converting TextManager to the use of style objects
		if not isinstance(style, TextStyle):
			style = self.styles[style]

		if len(text.split("\n")) > 1:
			return self.__wrap__(text, style)

		if len(text) == 0:
			text = " "
		rendering_font = TTF_OpenFont(self.fonts[style.font_label], style.font_size)
		if style.anti_aliased:
			rendered_text = TTF_RenderText_Blended(rendering_font, text, SDL_Color(*style.color)).contents
			px = asarray(PixelView(rendered_text))
			surface_array = argb32_to_rgba(px)
		else:
			rendered_text = TTF_RenderUTF8_Solid(rendering_font, text, SDL_Color(*style.color)).contents
			surface_array = asarray(PixelView(rendered_text))
			# surface_array = zeros((px.shape[0], px.shape[1], 4));
			# surface_array[...] = px * 255
		if not from_wrap:
			surface =  NpS(surface_array)
		else:
			surface =  NpS(surface_array)
			#surface = surface_array
			#return surface if surface.shape[1] < P.screen_x else self.__wrap__(text, style, P.screen_x - 20)
		TTF_CloseFont(rendering_font)
		return surface if surface.width < P.screen_x else self.__wrap__(text, style, P.screen_x - 20)

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

		for d in P.font_dirs:
			if isfile(join(d, font_file_basename)):
				self.fonts[font_name] = join(d, font_file_basename)
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
			self.__default_color__ = color

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
			self.__default_input_color__ = color

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
			self.__default_bg_color__ = color

	@property
	def default_font(self):
		"""

		:return:
		"""
		return self.__default_bg_color

	@default_bg_color.setter
	def default_font(self, color):
		"""

		:param color:
		"""
		if type(color) is list:
			self.__default_bg_color__ = color

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
