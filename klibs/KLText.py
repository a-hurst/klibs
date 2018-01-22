__author____ = 'jono'

from os.path import isfile, join
from math import floor
import ctypes
from ctypes import byref

from sdl2.sdlttf import (TTF_Init, TTF_OpenFont, TTF_CloseFont, TTF_RenderText_Blended,
	TTF_RenderUTF8_Solid, TTF_SizeText)
from sdl2.ext import PixelView
from sdl2 import SDL_Color
import numpy as np

from klibs.KLConstants import TEXT_PX, TEXT_MULTIPLE, TEXT_PT
from klibs import P
from klibs.KLUtilities import pt_to_px
from klibs.KLGraphics import NpS, rgb_to_rgba


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
		self.__line_height__ = 0.5
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
			return int(self.__line_height__ * self.font_size)
		else:
			return  pt_to_px(self.__line_height__)

	@line_height.setter
	def line_height(self, line_height_val):
		try:
			self.__line_height__ = line_height_val
			self.__line_height_units__ = TEXT_MULTIPLE
		except ValueError:
			self.__line_height__ = int(line_height_val[:-2])
			self.__line_height_units__ = line_height_val[-2:].upper()
			if self.__line_height_units__ not in [TEXT_PT, TEXT_PX]:
				raise ValueError(self.bad_unit_message)

	def __str__(self):
		return "klibs.KLTextManager.TextStyle ('{0}') at {1}".format(self.label, hex(id(self)))


class TextManager(object):
	fonts = {}
	font_sizes = {}
	styles = {}
	__default_color__ = (0, 0, 0, 255)
	__default_bg_color__ = (255, 255, 255)
	__default_font__ = None


	def __init__(self):
		self.__build_font_sizes__()
		self.add_font("Anonymous Pro", font_file_basename="AnonymousPro")
		self.add_font("Frutiger")
		self.add_font(P.default_font_name)
		self.add_style("debug", 12, (225, 145, 85, 255), bg_color=(0, 0, 0, 0), font_label="Anonymous Pro", anti_alias=False)
		self.default_color = P.default_color
		TTF_Init()

	def __build_font_sizes__(self):
		size_list = range(3, 96)
		self.font_sizes = {}
		for num in size_list:
			key = str(num) + 'pt'
			self.font_sizes[key] = int(floor(1.0 / 72 * P.ppi * num))

	def add_style(self, label, font_size=None, color=None, bg_color=None, line_height=None, font_label=None, anti_alias=True):
		self.styles[label] = TextStyle(label, font_size, color, bg_color, line_height, font_label, anti_alias)

	def __SDLSurface_to_ndarray(self, surface):
		'''Converts an SDL_Surface object from sdl_ttf into a numpy array. Largely based on the
		   code for the pixels3d() function from sdl2.ext, but that prints a warning every time
		   it's used and rotates/mirrors the texture for some reason.
		'''
		bpp = surface.format.contents.BytesPerPixel
		strides = (surface.pitch, bpp, 1)
		srcsize = surface.h * surface.pitch
		shape = surface.h, surface.w, bpp
		pxbuf = ctypes.cast(surface.pixels, ctypes.POINTER(ctypes.c_ubyte * srcsize)).contents
		# Since it's not guaranteed that the SDL_surface will remain in memory,
		# we copy the array from that buffer to a new one for safety.
		arr = np.copy(np.ndarray(shape, np.uint8, buffer=pxbuf))
		return arr

	def __wrap__(self, text, style, rendering_font, align, width=None):
		lines = text.split("\n")
		if width:
			surface_width = width
			wrapped_lines = []
			w, segment_w, h = ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(0)
			for line in lines:
				if len(line):
					# Get width of rendered string in pixels. If wider than surface, get character
					# position in string at position nearest cutoff, move backwards until space
					# character is encountered, and then trim string up to this point, adding it
					# to wrapped_lines.
					TTF_SizeText(rendering_font, line, byref(w), byref(h))
					while w.value > surface_width:
						pos = int(surface_width/float(w.value) * len(line))
						segment = line[:pos].rstrip()
						TTF_SizeText(rendering_font, segment, byref(segment_w), byref(h))
						while line[pos] != ' ' or segment_w.value > surface_width:
							pos = pos - 1
							segment = line[:pos].rstrip()
							TTF_SizeText(rendering_font, segment, byref(segment_w), byref(h))
						wrapped_lines.append(segment)
						line = line[pos:].lstrip()
						TTF_SizeText(rendering_font, line, byref(w), byref(h))
				wrapped_lines.append(line)
			lines = wrapped_lines
		else:
			surface_width = 1
			w, h = ctypes.c_int(0), ctypes.c_int(0)
			for line in lines:
				if len(line):
					TTF_SizeText(rendering_font, line, byref(w), byref(h))
					if w.value > surface_width:
						surface_width = w.value

		#TODO: fix mis-detected height problem for some fonts (e.g. Poppins)
		net_line_height = style.font_size + style.line_height
		output = NpS(width=surface_width, height=(len(lines) * net_line_height))
		for line in lines:
			if len(line):
				l_surf = self.render(line, style)
			else:
				continue
			if align == "left":
				l_surf_pos = (0, lines.index(line) * net_line_height)
				output.blit(l_surf, location=l_surf_pos)
			elif align == "center":
				l_surf_pos = (surface_width/2, lines.index(line) * net_line_height)
				output.blit(l_surf, location=l_surf_pos, registration=8)
			elif align == "right":
				l_surf_pos = (surface_width, lines.index(line) * net_line_height)
				output.blit(l_surf, location=l_surf_pos, registration=9)
		return output

	def render(self, text, style="default", align="left", max_width=None):
		"""

		:param text:
		:type text: String
		:param style:
		:type style: :class:`~klibs.KLText.TextStyle`
		:return:
		"""
		#  The following vars are an intermediary stage in converting TextManager to the use of style objects
		if not isinstance(style, TextStyle):
			style = self.styles[style]

		text = str(text)
		rendering_font = TTF_OpenFont(self.fonts[style.font_label], style.font_size)
		if max_width != None:
			w, h = ctypes.c_int(0), ctypes.c_int(0)
			TTF_SizeText(rendering_font, text, ctypes.byref(w), ctypes.byref(h))
			needs_wrap = w.value > max_width
		else:
			needs_wrap = False

		if len(text.split("\n")) > 1 or needs_wrap:
			if align not in ["left", "center", "right"]:
				raise ValueError("Text alignment must be one of 'left', 'center', or 'right'.")
			return self.__wrap__(text, style, rendering_font, align, max_width)

		if len(text) == 0:
			text = " "
		bgra_color = [style.color[2], style.color[1], style.color[0], style.color[3]]
		if style.anti_aliased:
			rendered_text = TTF_RenderText_Blended(rendering_font, text, SDL_Color(*bgra_color)).contents
			surface_array = self.__SDLSurface_to_ndarray(rendered_text)
		else:
			rendered_text = TTF_RenderUTF8_Solid(rendering_font, text, SDL_Color(*bgra_color)).contents
			surface_array = np.asarray(PixelView(rendered_text))
			# surface_array = np.zeros((px.shape[0], px.shape[1], 4));
			# surface_array[...] = px * 255
		surface =  NpS(surface_array)
		TTF_CloseFont(rendering_font)
		return surface

	def add_font(self, font_name, font_file_basename=None):
		"""

		:param font_name: Reference name of font within experiment context; typically mirrors filename.
		:type font_name: String
		:param font_file_basename: Filename without extension of file; used when font_name does not match filename.
		:return:
		"""

		if not font_file_basename:
			font_file_basename = font_name

		for d in P.font_dirs:
			for ext in [".ttf", ".otf"]:
				path_to_font = join(d, font_file_basename + ext)
				if isfile(path_to_font):
					self.fonts[font_name] = path_to_font
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
