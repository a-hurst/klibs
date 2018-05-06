__author____ = 'jono'

from os.path import isfile, join
from math import floor
import ctypes
from ctypes import byref, c_int

from sdl2.sdlttf import (TTF_Init, TTF_OpenFont, TTF_CloseFont, TTF_RenderUTF8_Blended,
	TTF_SizeUTF8, TTF_GlyphMetrics)
from sdl2 import SDL_Color
import numpy as np

from klibs.KLConstants import TEXT_PX, TEXT_MULTIPLE, TEXT_PT
from klibs import P
from klibs.KLUtilities import deg_to_px, px_to_deg
from klibs.KLGraphics import NpS, rgb_to_rgba


class TextStyle(object):

	__font = None
	__fontpath = None
	scale_factor = 1.0

	def __init__(self, label, fontpath, font_size=None, color=None, bg_color=None, line_height=None, font_label=None):

		self._font_size = None
		self._line_height = 0.5
		self.__font_size_units = P.default_font_unit
		self.__line_height_units = '*' # multiple of font size
		self.__fontpath = fontpath.encode('utf-8')
		self.label = label
		self.scale_factor = self._get_scale_factor()
		self.font_size = font_size if font_size else P.default_font_size
		self.font_label = font_label if font_label else P.default_font_name
		self.color = rgb_to_rgba(color) if color else P.default_color
		self.bg_color = rgb_to_rgba(bg_color) if bg_color else (0, 0, 0, 0)

		if line_height:
			self.line_height = line_height

		# Load in font
		self.__font = TTF_OpenFont(self.__fontpath, self._font_size)
	
	def _get_scale_factor(self):
		'''Determines the scale factor between the font in pt units and the max character height
		from baseline (ignoring accents and punctuation) in pixels. Used for rendering a font at
		a known size in pixels.
		'''
		max_ascent = 0
		minX, maxX, minY, maxY, advance = c_int(0), c_int(0), c_int(0), c_int(0), c_int(0)
		caps = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
		chars = caps + caps.lower() + "0123456789"
		testfont = TTF_OpenFont(self.__fontpath, 40)
		for char in chars:
			TTF_GlyphMetrics(testfont, ord(char), 
				byref(minX), byref(maxX), byref(minY), byref(maxY), byref(advance))
			if maxY.value > max_ascent:
				max_ascent = maxY.value
		TTF_CloseFont(testfont)
		return 40 / float(max_ascent)

	@property
	def font(self):
		return self.__font

	@property
	def font_size(self):
		if self.__font_size_units == 'px':
			return int(self._font_size / self.scale_factor)
		elif self.__font_size_units == 'deg':
			return px_to_deg(int(self._font_size / self.scale_factor))
		else:
			return self._font_size
	
	@font_size.setter
	def font_size(self, size):
		if isinstance(size, str):
			unit = ''.join([i for i in size if not (i.isdigit() or i == '.')])
			if len(unit):
				if unit not in ['pt', 'px', 'deg']:
					raise ValueError("Font size unit must be either 'pt', 'px', or 'deg'")
				self.__font_size_units = unit
				size = float(''.join([i for i in size if (i.isdigit() or i == '.')]))
			else:
				size = float(size)
		if self.__font_size_units == 'px':
			self._font_size = int(size * self.scale_factor)
		elif self.__font_size_units == 'deg':
			self._font_size = int(deg_to_px(size) * self.scale_factor)
		else:
			self._font_size = int(size)
		TTF_CloseFont(self.__font)
		self.__font = TTF_OpenFont(self.__fontpath, self._font_size)

	@property
	def line_height(self):
		if self.__line_height_units == '*':
			return int(self._line_height * self._font_size)
		else:
			return int(self._line_height)
			
	@line_height.setter
	def line_height(self, height):
		if isinstance(height, str):
			unit = ''.join([i for i in height if not (i.isdigit() or i == '.')])
			if len(unit):
				if unit not in ['px', '*']:
					raise ValueError("Line height unit must be either 'px' or '*' (multiple)")
				self.__line_height_units = unit
				height = float(''.join([i for i in height if i.isdigit()]))
			else:
				height = float(height)
		self._line_height = height

	def __str__(self):
		return "klibs.KLTextManager.TextStyle ('{0}') at {1}".format(self.label, hex(id(self)))


class TextManager(object):

	fonts = {}
	styles = {}
	__default_color__ = (0, 0, 0, 255)
	__default_bg_color__ = (255, 255, 255)


	def __init__(self):
		self.add_font("Anonymous Pro", filename="AnonymousPro")
		self.add_font("Frutiger")
		self.add_font(P.default_font_name)
		self.default_color = P.default_color
		TTF_Init()


	def add_style(self, label, font_size=None, color=None, bg_color=None, line_height=None, font_label=None):
		if not font_label:
			font_label = P.default_font_name
		fontpath = self.fonts[font_label]
		self.styles[label] = TextStyle(label, fontpath, font_size, color, bg_color, line_height, font_label)


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
		arr = np.copy(np.ndarray(shape, np.uint8, buffer=pxbuf, strides=strides))
		return arr


	def __wrap__(self, text, style, rendering_font, align, width=None):
		lines = text.split(b"\n")
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
					TTF_SizeUTF8(rendering_font, line, byref(w), byref(h))
					while w.value > surface_width:
						pos = int(surface_width/float(w.value) * len(line))
						segment = line[:pos].rstrip()
						TTF_SizeUTF8(rendering_font, segment, byref(segment_w), byref(h))
						while line[pos] != ' ' or segment_w.value > surface_width:
							pos = pos - 1
							segment = line[:pos].rstrip()
							TTF_SizeUTF8(rendering_font, segment, byref(segment_w), byref(h))
						wrapped_lines.append(segment)
						line = line[pos:].lstrip()
						TTF_SizeUTF8(rendering_font, line, byref(w), byref(h))
				wrapped_lines.append(line)
			lines = wrapped_lines
		else:
			surface_width = 1
			w, h = ctypes.c_int(0), ctypes.c_int(0)
			for line in lines:
				if len(line):
					TTF_SizeUTF8(rendering_font, line, byref(w), byref(h))
					if w.value > surface_width:
						surface_width = w.value

		#TODO: fix mis-detected height problem for some fonts (e.g. Poppins)
		net_line_height = style._font_size + style.line_height
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
		"""Renders a string of text to a surface that can then be presented on the screen using
		:func:`~klibs.KLGraphics.blit`.

		Args:
			text (str or numeric): The string or number to be rendered.
			style (str, optional): The label of the text style with which the font should be 
				rendered. Defaults to the "default" text style if none is specified.
			align (str, optional): The text justification to use when rendering multi-line
				text. Can be 'left', 'right', or 'center' (defaults to 'left').
			max_width (int, optional): The maximum line width for the rendered text. Lines longer
				than this value will be wrapped automatically. Defaults to None.

		Returns:
			:obj:`~klibs.KLGraphics.KLNumpySurface.NumpySurface`: a NumpySurface object containing
				the rendered text.

		"""
		
		stl = style if isinstance(style, TextStyle) else self.styles[style]
		
		try:
			is_unicode = isinstance(text, unicode)
		except NameError: # 'unicode' doesn't exist in python 3
			is_unicode = isinstance(text, str)

		if not isinstance(text, bytes):
			if is_unicode == False:
				text = str(text)
			text = text.encode('utf-8')

		rendering_font = stl.font
		if max_width != None:
			w, h = ctypes.c_int(0), ctypes.c_int(0)
			TTF_SizeUTF8(rendering_font, text, ctypes.byref(w), ctypes.byref(h))
			needs_wrap = w.value > max_width
		else:
			needs_wrap = False

		if len(text.split(b"\n")) > 1 or needs_wrap:
			if align not in ["left", "center", "right"]:
				raise ValueError("Text alignment must be one of 'left', 'center', or 'right'.")
			return self.__wrap__(text, style, rendering_font, align, max_width)

		if len(text) == 0:
			text = " "
		
		bgra_color = SDL_Color(stl.color[2], stl.color[1], stl.color[0], stl.color[3])
		rendered_text = TTF_RenderUTF8_Blended(rendering_font, text, bgra_color).contents
		surface_array = self.__SDLSurface_to_ndarray(rendered_text)
		surface = NpS(surface_array)
		return surface


	def add_font(self, name, filename=None):
		"""Adds a font to the Text Manager, so it can be used for creating text styles.

		Args:
			name (str): The name of the font being added. 
			filename (str, optional): The filename of the font, excluding the file extension. If
				the filename of the font is the same as the name you want to use for it, you do not
				have to provide this argument.
		
		Raises:
			IOError: If no font with the given filename and the extention '.ttf' or '.otf' can be
				found in the project's or system's font directories.

		"""
		
		def getfontpath(filename):
			for d in P.font_dirs:
				for ext in [".ttf", ".otf"]:
					path = join(d, filename + ext)
					if isfile(path):
						return path
			return None # if no matching file found

		if not filename:
			filename = name

		fontpath = getfontpath(filename)
		if fontpath:
			self.fonts[name] = fontpath
		else:
			raise IOError("Font '{0}' not found in any expected destination.".format(filename))


	@property
	def default_color(self):
		return self.__default_color__

	@default_color.setter
	def default_color(self, color):
		if type(color) is list:
			self.__default_color__ = color

	@property
	def default_bg_color(self):
		return self.__default_bg_color__

	@default_bg_color.setter
	def default_bg_color(self, color):
		if type(color) is list:
			self.__default_bg_color__ = color
