# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'
import warnings
import numpy as np

with warnings.catch_warnings():
	warnings.simplefilter("ignore")
	import sdl2
	from PIL import Image
	import OpenGL.GL as gl
	warnings.simplefilter("default")

from math import sqrt, atan, degrees
from os.path import isfile
from klibs import P
from klibs.KLUtilities import absolute_position, build_registrations, pump, hide_mouse_cursor, deg_to_px
from klibs.KLConstants import *
from KLDraw import Drawbject, FixationCross, Circle
from KLNumpySurface import NumpySurface as NpS

# populated on first call to flip() if needed
global tracker_dot

def aggdraw_to_numpy_surface(draw_context):
	"""

	:param draw_context:
	:return:
	"""
	return NpS(aggdraw_to_array(draw_context))


def aggdraw_to_array(draw_obj):
	try:
		draw_context_bytes = Image.frombytes(draw_obj.mode, draw_obj.size, draw_obj.tostring())  # old aggdraw
	except Exception:
		draw_context_bytes = Image.frombytes(draw_obj.mode, draw_obj.size, draw_obj.tobytes()) # new aggdraw
	return np.asarray(draw_context_bytes)


def argb32_to_rgba(np_array):
		"""Converts an integer value to a Color, assuming the integer
		represents a 32-bit RGBBA value.
		"""
		out =  np.zeros((np_array.shape[0], np_array.shape[1], 4))
		out[...,3] = ((np_array & 0xFF000000) >> 24)
		out[...,0] = ((np_array & 0x00FF0000) >> 16)
		out[...,1] = ((np_array & 0x0000FF00) >> 8)
		out[...,2] = ((np_array & 0x000000FF))

		return out


def blit(source, registration=7, location=(0,0), position=None):
		"""
		Draws passed content to display buffer.

		:param source: Image data to be buffered.
		:type source: :class:`~klibs.KLNumpySurface.NumpySurface`, :class:`~klibs.KLDraw.Drawjbect`, Numpy Array, `PIL.Image <http://pillow.readthedocs.org/en/3.0.x/reference/Image.html>`_
		:param registration: Location on perimeter of surface that will be aligned to position (see manual for more information).
		:type registration: Int
		:param position: Location on screen to place source, either pixel coordinates or location string (ie. "center", "top_left")
		:type position: String, Iterable
		:param context: ``NOT IMPLEMENTED`` A destination surface or display object for images built gradually.

		:raise TypeError:
		"""

		if position:
			location = position  # fixing stupid argument name, preserving backwards compatibility
		if isinstance(source, NpS):
			height = source.height
			width = source.width
			if source.rendered is None:
				content = source.render()
			else:
				content = source.rendered

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
		elif type(source) is str and isfile(source):
			return blit(NpS(source), registration, location, position)
		else:
			raise TypeError("Argument 'source' must be np.ndarray, klibs.KLNumpySurface.NumpySurface, or inherit from klibs.KLDraw.Drawbect.")

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
		Clears current display and display buffer with supplied color or else P.default_fill_color.

		:param color:
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

		import Tkinter
		root = Tkinter.Tk()
		P.screen_x = root.winfo_screenwidth()
		P.screen_y = root.winfo_screenheight()
		P.screen_x_y = (P.screen_x, P.screen_y)
		sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
		sdl2.mouse.SDL_ShowCursor(sdl2.SDL_DISABLE)
		sdl2.SDL_PumpEvents()
		window = sdl2.ext.Window("experiment", P.screen_x_y, (0, 0), SCREEN_FLAGS)
		P.screen_diagonal_in = diagonal_in
		P.screen_c = (P.screen_x / 2, P.screen_y / 2)

		P.diagonal_px = sqrt(P.screen_x**2.0  + P.screen_y**2.0)
		P.ppi = int(P.diagonal_px / diagonal_in)
		P.monitor_x = P.screen_x / P.ppi
		P.monitor_y = P.screen_y / P.ppi
		P.screen_degrees_x = degrees(atan((2.55 * P.monitor_x / 2.0) / P.view_distance) * 2)
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


def draw_fixation(location=BL_CENTER, size=None, stroke=None, color=None, fill_color=None, flip=False):
		"""
		Creates and renders a FixationCross (see :mod:`~klibs.KLDraw` inside an optional background circle at provided or
		default location.

		:param location: X-Y Location of drift correct target; if not provided, defaults to screen center.
		:type location: Interable of Integers or `Relative Location Constant`
		:param size: Width and height in pixels of fixation cross.
		:type size: Integer
		:param stroke: Width in pixels of the fixation cross's horizontal & vertical bars.
		:type stroke: Integer
		:param color: Color of fixation cross as rgb or rgba values (ie. (255, 0, 0) or (255, 0, 0, 125).
		:type color: Iterable of Integers
		:param fill_color: Color of background circle as iterable rgb or rgba values; default is None.
		:type color: Iterable of Integers
		:param flip: Toggles automatic flipping of display buffer, see :func:`~klibs.KLExperiment.Experiment.flip``.
		"""

		if not size: size = deg_to_px(P.fixation_size)
		if not stroke: stroke = size // 5
		cross = FixationCross(size, stroke, color, fill_color).draw()
		blit(cross, 5, absolute_position(location))
		if flip: flip()


def fill(color=None, context=None):
	"""
	Clears display buffer to a single color.

	:param color:
	:param context:
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
	Transfers content of draw buffer to current passed SDL2 window object or window attribute of current
	 :mod:`~klibs.KLExperiment` instance.

	:raises: ValueError
	"""
	from klibs.KLEnvironment import exp, el
	global tracker_dot

	if P.development_mode and P.el_track_gaze and P.eye_tracking and P.in_trial:
		try:
			tracker_dot
		except NameError:
			tracker_dot = Circle(8, stroke=[2, (255,255,255)], fill=(255,0,0)).render()
		try:
			blit(tracker_dot, 5, el.gaze())
		except RuntimeError:
			pass

	if exp:
		exp.before_flip()
	if not window:
		try:
			window = exp.window.window
		except AttributeError:
			raise ValueError("flip requires an sdl2.window object when called outside of experiment runtime.")
	sdl2.SDL_GL_SwapWindow(window)


def rgb_to_rgba(rgb):
	return tuple(rgb) if len(rgb) == 4 else tuple([rgb[0], rgb[1], rgb[2], 255])


