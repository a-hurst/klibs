__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import re
from os.path import isfile, join, basename
import ctypes
from ctypes import byref, c_int

from sdl2.sdlttf import (TTF_OpenFont, TTF_CloseFont, TTF_RenderUTF8_Blended,
    TTF_SizeUTF8, TTF_GlyphMetrics, TTF_FontLineSkip)
from sdl2 import SDL_Color
from sdl2.ext.compat import byteify
from sdl2.ext import surface_to_ndarray, raise_sdl_err
from sdl2.ext.ttf import _ttf_init

from klibs.KLConstants import TEXT_PX, TEXT_MULTIPLE, TEXT_PT
from klibs import P
from klibs.KLEnvironment import EnvAgent
from klibs.KLUtilities import deg_to_px, utf8
from klibs.KLGraphics import rgb_to_rgba
from klibs.KLGraphics.KLNumpySurface import NumpySurface as NpS



def _split_units(s):
    # Extracts the size and unit from a given size string (e.g. '0.6deg')
    found = re.search(r"^([\d\.]+)([a-z]*)", s.lower())
    if not found:
        e = "Unable to parse unit string '{0}'."
        raise ValueError(e.format(s))
    size, unit = found.groups(1)
    return (float(size), unit)


def _size_to_pt(size, units, scale_factor=1.0):
    # Calculates the size of the font in the 'pt' units used by SDL_ttf
    size_pt = None
    if units == 'deg':
        size_pt = int(deg_to_px(size) * scale_factor)
    elif units == 'px':
        size_pt = int(size * scale_factor)
    elif units == 'pt':
        size_pt = size
    return size_pt


def _get_max_ascent(font, chars):
    # Gets the maximum ascent (baseline to top, in px) for a given string/font
    max_ascent = 0
    minX, maxX, minY, maxY, advance = c_int(0), c_int(0), c_int(0), c_int(0), c_int(0)
    for char in chars:
        TTF_GlyphMetrics(font, ord(char), 
            byref(minX), byref(maxX), byref(minY), byref(maxY), byref(advance))
        if maxY.value > max_ascent:
            max_ascent = maxY.value
    return max_ascent


def _load_font(fontpath, size_pt):
    # Loads a font at a given size and checks for any errors
    font = TTF_OpenFont(fontpath, int(size_pt))
    if not font:
        fname = basename(fontpath)
        raise_sdl_err("opening the font '{0}'".format(fname))
    return font



class TextStyle(EnvAgent):
    """A custom style to use for rendering text.

    A text style defines a specific combination of font, font size, font color, and
    line spacing to use for rendering text.

    Note that if specifying a particular font for a text style, the font must already
    exist within the klibs :obj:`~klibs.KLText.TextManager`.

    Args:
        font (str, optional): The name of the font to use when rendering text with the
            style. Defaults to ``P.default_font_name`` if not specified.
        size (str or float, optional): The font size to use when rendering text with the
            style. Defaults to ``P.default_font_size`` if not specified.
        color (tuple, optional): The RGBA font color to use when rendering text with the
            style. Defaults to ``P.default_color`` if not specified.
        line_space (float, optional): The line spacing to use when rendering multi-line
            text with the font. Defaults to ``2.0`` (double-spaced) unless a custom
            ``P.default_line_space`` has been set.

    """
    def __init__(self, font=None, size=None, color=None, line_space=None):

        # First, make sure TextManager has been initialized
        self._initialized = False
        if self.txtm is None:
            e = "KLibs runtime must be initialized before creating a text style."
            raise RuntimeError(e)

        # Initialize style defaults
        self._fontname = font if font else P.default_font_name
        self._size = size if size else P.default_font_size
        self._color = rgb_to_rgba(color) if color else P.default_color
        self._line_h = float(line_space) if line_space else P.default_line_space
        if self._line_h < 1.0:
            e = "Line spacing must be 1.0 or higher (got {0})"
            raise ValueError(e.format(self._line_h))

        # Make sure requested font actually exists within the text manager
        if self._fontname not in self.txtm.fonts.keys():
            e = "No font with the label '{0}' has been added to the KLibs TextManager."
            raise RuntimeError(e.format(self._fontname))
        self._fontpath = byteify(self.txtm.fonts[self._fontname])

        # Initialize font size and size units
        self._scale_factor = self._get_scale_factor(self._fontpath)
        self._size, self._size_units = self._validate_size(self._size)
        self._size_pt = _size_to_pt(
            self._size, self._size_units, self._scale_factor
        )

        # Load in font
        self._font_ttf = _load_font(self._fontpath, self._size_pt)
        self._initialized = True

    def __repr__(self):
        info = ""
        if self._initialized:
            info = "{0}, {1}{2}".format(self._fontname, self._size, self._size_units)
        return "klibs.TextStyle({0})".format(info)
    
    def _get_scale_factor(self, fontpath):
        # Determines the pt-to-pixels scale factor for the current font, with height
        # in px defined as the maximum ASCII character height from baseline
        # (ignoring punctuation). Allows fonts to be easily specified in px or deg.
        caps = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chars = caps + caps.lower() + "0123456789"
        testfont = _load_font(fontpath, 40)
        max_ascent = _get_max_ascent(testfont, chars)
        TTF_CloseFont(testfont)
        return 40 / float(max_ascent)

    def _validate_size(self, size):
        # Determine font size and units
        if isinstance(size, str):
            size, units = _split_units(size)
            if not len(units):
                units = P.default_font_units
        else:
            size = float(size)
            units = P.default_font_unit
        # Ensure font units are valid
        if units not in ['pt', 'px', 'deg']:
            e = "Font size units must be either 'pt', 'px', or 'deg' (got {0})"
            raise ValueError(e.format(units))
        return size, units

    @property
    def fontname(self):
        """str: The name of the font used for the style.

        """
        return self._fontname

    @property
    def color(self):
        """tuple: The ``(r, g, b, a)`` text color used for the style.

        """
        return tuple(self._color)

    @property
    def size_px(self):
        """int: The maximum character height (in pixels) for the style.
        
        """
        return int(round(self._size_pt / self._scale_factor))

    @property
    def line_space(self):
        """float: The line spacing for the style (e.g. 2.0 for double-spaced).

        """
        return self._line_h



class TextManager(object):

    def __init__(self):
        # Initialize SDL_ttf and font/style dicts
        _ttf_init()
        self.fonts = {}
        self.styles = {}

        # Load fonts included in klibs
        self.add_font("Anonymous Pro", filename="AnonymousPro")
        self.add_font("Roboto-Medium")
        self.add_font("Hind-Medium")

        # Load additional fonts from ExpAssets/Resources/font
        self._load_user_fonts()

    def _load_user_fonts(self):
        # Pre-load all supported font files in the ExpAssets/Resources/font dir
        font_exts = ['ttf', 'otf']
        for f in os.listdir(P.exp_font_dir):
            # Skip invisible files
            if f[0] == "." or not "." in f:
                continue
            # If file extension is valid, add font to runtime
            fontname, delim, ext = f.rpartition('.')
            if ext in font_exts:
                fontpath = os.path.join(P.exp_font_dir, f)
                self.fonts[fontname] = fontpath

    def add_style(
        self, label, font_size=None, color=None, line_height=None, font_label=None
    ):
        # Legacy method for adding font styles, replaced by add_text_style
        line_space = 2.0
        if line_height:
            h, _ = _split_units(str(line_height))
            line_space = (h + 1.0) * 1.3
        self.styles[label] = TextStyle(font_label, font_size, color, line_space)


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
                        while line.decode('utf-8')[pos] != ' ' or segment_w.value > surface_width:
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

        line_pad = int(style.size_px * (style.line_space - 1.0))
        net_line_height = style.size_px + line_pad
        output = NpS(width=surface_width, height=(len(lines) * net_line_height))
        for i in range(len(lines)):
            line = lines[i]
            if len(line):
                l_surf = self.render(line, style)
            else:
                continue
            if align == "left":
                l_surf_pos = (0, i * net_line_height)
                output.blit(l_surf, location=l_surf_pos, blend=False, clip=False)
            elif align == "center":
                l_surf_pos = (surface_width/2, i * net_line_height)
                output.blit(l_surf, location=l_surf_pos, blend=False, clip=False, registration=8)
            elif align == "right":
                l_surf_pos = (surface_width, i * net_line_height)
                output.blit(l_surf, location=l_surf_pos, blend=False, clip=False, registration=9)

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

        if not isinstance(text, bytes):
            text = utf8(text).encode('utf-8')

        rendering_font = stl._font_ttf
        if max_width != None:
            w, h = ctypes.c_int(0), ctypes.c_int(0)
            TTF_SizeUTF8(rendering_font, text, ctypes.byref(w), ctypes.byref(h))
            needs_wrap = w.value > max_width
        else:
            needs_wrap = False

        if len(text.split(b"\n")) > 1 or needs_wrap:
            if align not in ["left", "center", "right"]:
                raise ValueError("Text alignment must be one of 'left', 'center', or 'right'.")
            return self.__wrap__(text, stl, rendering_font, align, max_width)

        if len(text) == 0:
            text = " "
        
        bgra_color = SDL_Color(stl.color[2], stl.color[1], stl.color[0], stl.color[3])
        rendered_text = TTF_RenderUTF8_Blended(rendering_font, text, bgra_color).contents
        surface_array = surface_to_ndarray(rendered_text)
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



def add_text_style(label, size=None, color=None, line_space=None, font=None):
    """Adds a new named text style to the klibs runtime.

    Text styles provide an easy way of rendering text different ways for different
    things. For example, if you want to define a 'title' style to render text in a
    larger font, as well as an 'error' style that renders feedback for bad responses
    in red, you could do the following::

       # Define the text styles
       add_text_style('title', size='1.0deg')
       add_text_style('error', color=(255, 0, 0))

       # Render text with the different styles
       msg_start = message("Press any key to continue.", style='title')
       msg_err = message("Incorrect!", style='error')

    Once defined, a text style can be used by name repeatedly throughout the experiment.

    The klibs runtime comes with two included fonts: 'Hind-Medium' and 'Roboto-Medium'.
    To create a text style with a different user-provided font, you can add any valid
    ``.ttf`` or ``.otf`` font file to the project's ``ExpAssets/Resources/font``
    directory and then use it by name. For example, if ``Helvetica-Bold.otf`` is
    present in the project's font folder, you can do the following::

       add_text_style('bold', size='40px', font='Helvetica-Bold')

    Args:
        label (str): The name of the new text style.
        size (str or float, optional): The font size for the text style. Defaults to
            ``P.default_font_size` if not specified.
        color (tuple, optional): The RGBA color for the text style. Defaults to
            ``P.default_color` if not specified.
        line_space (float, optional): The line spacing to use when rendering multi-line
            text with the style. Defaults to ``2.0`` (double-spaced) unless
            ``P.default_line_space`` has been set.
        font (str, optional): The font to use for the text style. Defaults to
            ``P.default_font_name` if not specified.

    """
    from klibs import env
    if env.txtm is None:
        e = "KLibs runtime must be initialized before text styles can be added."
        raise RuntimeError(e)
    env.txtm.styles[label] = TextStyle(font, size, color, line_space)
