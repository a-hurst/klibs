# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

import warnings
from time import time
from math import sqrt, atan, degrees

import numpy as np
from PIL import Image
import OpenGL.GL as gl
with warnings.catch_warnings():
	warnings.simplefilter("ignore")
	import sdl2

from klibs import P
from klibs.KLUtilities import absolute_position, build_registrations, pump, hide_mouse_cursor, deg_to_px
from klibs.KLConstants import *
from KLNumpySurface import NumpySurface as NpS


def aggdraw_to_numpy_surface(draw_context):
	return NpS(aggdraw_to_array(draw_context))


def aggdraw_to_array(draw_obj):
	draw_context_bytes = Image.frombytes(draw_obj.mode, draw_obj.size, draw_obj.tobytes())
	return np.asarray(draw_context_bytes)


def blit(source, registration=7, location=(0,0), position=None, flip_x=False):
		"""
		Draws passed content to the display buffer. All content that is not in already
		rendered to Numpy Array format will be rendered when it is passed to this
		function, thus it is recommended to render beforehand whenever possible to
		avoid performance issues resulting from the extra overhead.

		Args:
			source (:obj:`NumpySurface`|:obj:`Drawbject`|:obj:`numpy.array`|
				:obj:`Pillow.Image`): Image data to be buffered.
			registration (int): An integer from 1 to 9 indicating which location on the
				surface will be aligned to the location value (see manual for more info).
			location(tuple(int,int)): A tuple of x,y pixel coordinates indicating where to
				draw the object to.
			position(iter|str): (depricated) Location to draw object, in form of either
				an iterable of pixel coordiantes or a location string (e.g "center").
			flip_x (bool): If True, flips the x-axis of the passed object before drawing.
			context: (not implemented) A destination surface or display object for images
				built gradually.
		
		Raises:
			TypeError: If the 'source' object passed is not one of the accepted types.
		"""
		from KLDraw import Drawbject

		if position:
			#TODO: Purge this from within klibs once and for all
			location = position  # fixing stupid argument name, preserving backwards compatibility
			
		if isinstance(source, NpS):
			height = source.height
			width = source.width
			if source.rendered is None:
				content = source.render()
			else:
				content = source.rendered

		elif isinstance(source, Image.Image):
			# is this a good idea? will be slower in most cases than using np.asarray() on Image
			# and rendering that, since you don't need to re-render every time.
			height = source.size[1]
			width = source.size[0]
			content = source.tobytes("raw", "RGBA", 0, 1)

		elif issubclass(type(source), Drawbject):
			height = source.surface_height
			width = source.surface_width
			if source.rendered is None:
				content = source.render()
			else:
				content = source.rendered

		elif type(source) is np.ndarray:
			height = source.shape[0]
			width = source.shape[1]
			content = source

		else:
			raise TypeError("Argument 'source' must be np.ndarray, klibs.KLNumpySurface.NumpySurface, or inherit from klibs.KLDraw.Drawbect.")
		
		if any([not flip_x and P.blit_flip_x, flip_x]):
			content = np.fliplr(content)

		# configure OpenGL for blit
		gl.glEnable(gl.GL_BLEND)
		gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
		t_id = gl.glGenTextures(1)
		gl.glBindTexture(gl.GL_TEXTURE_2D, t_id)
		gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
		gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
		gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, content)
		gl.glEnable(gl.GL_TEXTURE_2D)
		gl.glBindTexture(gl.GL_TEXTURE_2D, t_id)
		gl.glBegin(gl.GL_QUADS)

		# convert english location strings to x,y coordinates of destination surface
		if type(location) is str:
			location = absolute_position(location, P.screen_x_y)
		# location[0] += P.screen_origin[0]
		# location[1] += P.screen_origin[1]
		# define boundaries coordinates of region being blit to
		x_bounds = [location[0], location[0] + width]
		y_bounds = [location[1], location[1] + height]

		# shift boundary mappings to reflect registration
		#
		# 1--2--3  Default assumes registration = 5, but if registration = 3 (top-right), X/Y would be shifted
		# 4--5--6  by the distance from the object's top-left  to it's top-right corner
		# 7--8--9  ie. Given an object of width = 3, height = 3, with registration 9 being blit to (5,5) of some
		#          surface, the default blit behavior (placing the  top-left coordinate at 5,5) would result in
		#          the top-left corner being blit to (2,2), such that the bottom-right corner would be at (5,5)
		registrations = build_registrations(height, width)

		if 0 < registration < 10:
			x_bounds[0] += int(registrations[registration][0])
			x_bounds[1] += int(registrations[registration][0])
			y_bounds[0] += int(registrations[registration][1])
			y_bounds[1] += int(registrations[registration][1])
		else:
			x_bounds[0] += int(registrations[7][0])
			x_bounds[1] += int(registrations[7][0])
			y_bounds[0] += int(registrations[7][1])
			y_bounds[1] += int(registrations[7][1])
		gl.glTexCoord2f(0, 0)
		gl.glVertex2f(x_bounds[0], y_bounds[0])
		gl.glTexCoord2f(1, 0)
		gl.glVertex2f(x_bounds[1], y_bounds[0])
		gl.glTexCoord2f(1, 1)
		gl.glVertex2f(x_bounds[1], y_bounds[1])
		gl.glTexCoord2f(0, 1)
		gl.glVertex2f(x_bounds[0], y_bounds[1])
		gl.glEnd()
		gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
		gl.glDeleteTextures([t_id])
		del t_id
		gl.glDisable(gl.GL_TEXTURE_2D)


def clear(color=None):
		"""
		Clears both current display and display buffer with a given color. If no color
		is specified, the value of P.default_fill_colour is used.

		Args:
			color(iter, optional): An iterable of integers representing the RGB or RGBA
				color value to be used to fill the display and display buffer (e.g.
				color=(0,0,0) to fill both with black).
		"""

		if color is None: color = P.default_fill_color
		fill(color)
		flip()
		fill(color)
		flip()


def display_init(diagonal_in):
		"""
		Creates an `SDL2 window object <http://pysdl2.readthedocs.org/en/latest/modules/sdl2ext_window.html>`_ in which the project runs.
		This is also the window object passed to :mod:`~klibs.KLELCustomDisplay`.\ :class:`~klibs.KLELCustomDisplay.ELCustomDisplay` instance.

		:param diagonal_in: The diagonal length of the monitor's viewable area.
		:type diagonal_in: Int, Float
		:raise TypeError:
		"""

		sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
		sdl2.mouse.SDL_ShowCursor(sdl2.SDL_DISABLE)
		sdl2.SDL_PumpEvents()

		display_mode = sdl2.video.SDL_DisplayMode()
		sdl2.SDL_GetCurrentDisplayMode(0, display_mode)

		P.screen_x = display_mode.w
		P.screen_y = display_mode.h
		P.screen_x_y = (P.screen_x, P.screen_y)

		P.refresh_rate = display_mode.refresh_rate
		P.refresh_time = 1000.0 / P.refresh_rate

		# todo: make this configuration process more fool-proof/klibsian/informative; probably create "display objects"
		for d in P.additional_displays:
			if d[2]:
				P.screen_x_y = list(d[1])
				P.screen_x = d[1][0]
				P.screen_y = d[1][1]

		if P.screen_origin is None:
			P.screen_origin = (0, 0)

		SCREEN_FLAGS = (
			sdl2.SDL_WINDOW_OPENGL |
			sdl2.SDL_WINDOW_SHOWN |
			sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP |
			sdl2.SDL_WINDOW_ALLOW_HIGHDPI
		)
		window = sdl2.ext.Window("experiment", P.screen_x_y, P.screen_origin, SCREEN_FLAGS)
		P.screen_diagonal_in = diagonal_in
		P.screen_c = (P.screen_x / 2, P.screen_y / 2)
		P.screen_diagonal_px = sqrt(P.screen_x**2.0 + P.screen_y**2.0)
		P.ppi = int(P.screen_diagonal_px / diagonal_in)
		P.monitor_height = P.screen_y / P.ppi # Generate this more directly?
		P.monitor_width = P.screen_x / P.ppi # Generate this more directly?
		P.screen_degrees_x = degrees(atan((2.55 * P.monitor_width / 2.0) / P.view_distance) * 2)
		P.screen_degrees_y = degrees(atan((2.55 * P.monitor_height / 2.0) / P.view_distance) * 2)
		P.pixels_per_degree = P.screen_x // P.screen_degrees_x
		P.ppd = P.pixels_per_degree  # alias for convenience


		# these next six lines essentially assert a 2d, pixel-based rendering context; copied-and-pasted from Mike!
		sdl2.SDL_GL_CreateContext(window.window)

		gl.glMatrixMode(gl.GL_PROJECTION)
		gl.glLoadIdentity()
		gl.glOrtho(0, P.screen_x, P.screen_y, 0, 0, 1)
		gl.glMatrixMode(gl.GL_MODELVIEW)
		gl.glDisable(gl.GL_DEPTH_TEST)
		pump()
		hide_mouse_cursor()
		window.show()
		P.display_initialized = True
		return window


def fill(color=None, context=None):
	"""
	Fills the display buffer with a single RGB or RGBA color. If no color is specified,
	the value of P.default_fill_colour is used.

	Args:
		color(iter, optional): An iterable of integers representing the RGB or RGBA
				color value to be used to fill the display buffer (e.g. color=(0,0,0)
				to fill the buffer with black).
		context: (Not implemented) The id of the display context to fill.

	"""

	# todo: consider adding sdl2's "area" argument, to fill a subset of the surface
	if color is None:
		color = P.default_fill_color

	if len(color) == 3:
		color = rgb_to_rgba(color)

	gl_color = [0] * 4
	for i in range(0, 4):
		gl_color[i] = 0 if color[i] == 0 else color[i] / 255.0
	gl.glClearColor(gl_color[0], gl_color[1], gl_color[2], gl_color[3])
	gl.glClear(gl.GL_COLOR_BUFFER_BIT)


def flip(window=None):
	"""
	Displays the contents of the display buffer on the screen. Because the screen is only
	redrawn at certain intervals (every 16.7 ms for a typical 60 Hz LCD), this function
	will not return until the next redraw event occurs. 
	
	When in development mode, this function will print a warning in the console if the 
	screen takes longer than a single refresh to redraw. If this occurs often, it might
	indicate an issue with your graphics driver or display computer and suggests that
	you shouldn't rely on that setup for timing-sensitive experiments.

	For more information on how drawing works in KLibs, please refer to the documentation
	page explaining the graphics system.

	Args:
		window (sdl2.window, optional): The SDL2 window to flip. Should only be specified
			manually if called outside of a KLibs expriment runtime.
	
	Raises:
		ValueError: If called outside of an experiment runtime and no window is specified.

	"""
	from klibs.KLEnvironment import exp

	if exp:
		exp.before_flip()

	if not window:
		try:
			window = exp.window.window
		except AttributeError:
			raise ValueError("flip requires an sdl2.window object when called outside of experiment runtime.")

	# Note: On some systems, redrawing the screen will sometimes take longer than expected (up to 100ms in some cases). 
	# Since this is obviously a problem for timing-sensitive research, we time how long each flip takes, and print
	# a warning whenever it takes longer than expected (with threshold of 1ms).
	flip_start = time()
	sdl2.SDL_GL_SwapWindow(window)
	flip_time = (time() - flip_start) * 1000 # convert to ms
	if P.development_mode:
		if flip_time > (P.refresh_time + 1):
			print "Warning: Screen refresh took %.2f ms (expected %.2f ms)" % (flip_time, P.refresh_time)


def rgb_to_rgba(rgb):
	"""Converts a 3-element RGB iterable to a 4-element RGBA tuple. If a 4-element RGBA
	iterable is passed it is coerced to a tuple and returned, making the function safe
	for use when the input might be either an RGB or RGBA value.

	Args:
		rgb(iter): A 3 or 4 element RGB(A) iterable to convert.
	
	Returns:
		Tuple[r, g, b, a]: A 4-element RGBA tuple.
	"""
	return tuple(rgb) if len(rgb) == 4 else tuple([rgb[0], rgb[1], rgb[2], 255])
