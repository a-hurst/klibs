# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import ctypes
from time import time
from math import sqrt, atan, degrees

import sdl2
from sdl2.ext.common import raise_sdl_err
import OpenGL.GL as gl
import numpy as np
from PIL import Image

from klibs import P
from klibs.KLTime import precise_time

from .utils import _build_registrations, rgb_to_rgba, image_file_to_array, add_alpha
from .KLNumpySurface import aggdraw_to_numpy_surface, NumpySurface
from .KLDraw import Drawbject


# This module contains the core functions for drawing things to the screen.

def _init_fullscreen(display, hidpi=False):

    # Get the current non-HIDPI resolution and refresh rate of the display
    display_mode = sdl2.SDL_DisplayMode()
    ret = sdl2.SDL_GetCurrentDisplayMode(display, display_mode)
    if ret != 0:
        raise_sdl_err("getting the current display mode")
    screen_xy = (display_mode.w, display_mode.h)

    # Create the SDL window object and configure it properly for OpenGL
    window_flags = (
        sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP |
        sdl2.SDL_WINDOW_OPENGL
    )
    if hidpi:
        window_flags = window_flags | sdl2.SDL_WINDOW_ALLOW_HIGHDPI
    window = sdl2.ext.Window(P.project_name, screen_xy, flags=window_flags)
    sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE)
    sdl2.SDL_GL_CreateContext(window.window)

    # Get actual pixel resolution for the window
    res_x, res_y = (ctypes.c_int(0), ctypes.c_int(0))
    sdl2.SDL_GL_GetDrawableSize(
        window.window, ctypes.byref(res_x), ctypes.byref(res_y)
    )
    res = (res_x.value, res_y.value)

    # Parse and validate refresh rate
    screen_hz = float(display_mode.refresh_rate)
    if screen_hz == 0:
        screen_hz = 60.0
        print(" - Warning: Unable to detect your monitor's refresh rate, defaulting to 60Hz")
    elif screen_hz == 59:
        screen_hz = 59.94 # fix for some Windows monitors

    return (window, res, screen_hz)


def _set_display_params(res, size_in, hz):

    # Set basic display properties
    P.screen_x = res[0]
    P.screen_y = res[1]
    P.screen_c = (P.screen_x // 2, P.screen_y // 2)
    P.screen_x_y = (P.screen_x, P.screen_y)

    # Set refresh rate/time
    P.refresh_rate = hz
    P.refresh_time = 1000.0 / P.refresh_rate

    # Get conversion factor for pixels to degrees of visual angle based on viewing distance,
    # screen resolution, and given diagonal screen size
    P.screen_diagonal_in = size_in
    P.screen_diagonal_px = sqrt(P.screen_x ** 2.0 + P.screen_y ** 2.0)
    P.ppi = P.screen_diagonal_px / size_in
    P.monitor_height = P.screen_y / P.ppi
    P.monitor_width = P.screen_x / P.ppi
    P.screen_degrees_x = degrees(2 * atan((2.54 * P.monitor_width / 2.0) / P.view_distance))
    P.screen_degrees_y = degrees(2 * atan((2.54 * P.monitor_height / 2.0) / P.view_distance))
    P.pixels_per_degree = P.screen_x / P.screen_degrees_x
    P.ppd = P.pixels_per_degree # alias for convenience


def display_init(diagonal_in, hidpi):
    """Initializes the display and rendering backend, calculating and assigning the values
    of runtime KLParams variables related to the screen (e.g. P.screen_c, P.refresh_rate,
    P.pixels_per_degree). Called by 'klibs run' on launch, for internal use only.
    
    Args:
        diagonal_in (float): The size of the monitor in diagonal inches (e.g. 13 for a
            13-inch MacBook Pro).

    """
    if os.name == 'nt':
        # Set video driver explicitly on Windows to avoid misdetection problems
        os.environ['SDL_VIDEODRIVER'] = 'windows'
        # Allow better HIDPI handling on Windows (requires SDL >= 2.24)
        sdl2.SDL_SetHint(b"SDL_WINDOWS_DPI_AWARENESS", b"permonitor")
        
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    sdl2.SDL_PumpEvents()

    # Create a fullscreen window at the current resolution, get display info
    window, res, hz = _init_fullscreen(display=0, hidpi=hidpi)

    # Set up the OpenGL context for the window
    ret = sdl2.SDL_GL_SetSwapInterval(1) # enforce vsync
    if ret != 0:
        print(" - Warning: Vsync unsupported, experiment timing may be off")
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    gl.glOrtho(0, res[0], res[1], 0, 0, 1)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glDisable(gl.GL_DEPTH_TEST)
    # Set the blend mode for OpenGL
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    # Enable 2D texturing
    gl.glEnable(gl.GL_TEXTURE_2D)

    # Update display properties & and pixels-per-degree in KLParams
    _set_display_params(res, diagonal_in, hz)

    # Get scaling factor for HiDPI displays
    P.screen_scale_x = res[0] / float(window.size[0])
    P.screen_scale_y = res[1] / float(window.size[1])

    # Clear the SDL event queue and return the window object
    sdl2.SDL_PumpEvents()
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


def blit(source, registration=7, location=(0,0), flip_x=False):
        """
        Draws passed content to the display buffer. All content that is not in already
        rendered to Numpy Array format will be rendered when it is passed to this
        function, thus it is recommended to render beforehand whenever possible to
        avoid performance issues resulting from the extra overhead.

        Valid source content types include :obj:`NumpySurface` objects, :obj:`Drawbject` shapes,
        and :obj:`numpy.ndarray` or :obj:`Pillow.Image` objects in RGBA format.

        Args:
            source: Image data to draw to the display buffer.
            registration (int): An integer from 1 to 9 indicating which location on the
                surface will be aligned to the location value (see manual for more info).
            location(tuple(int,int)): A tuple of x,y pixel coordinates indicating where to
                draw the object to.
            flip_x (bool): If True, flips the content along its x-axis before drawing to
                the display buffer.
        
        Raises:
            TypeError: If the 'source' object passed is not one of the accepted types.

        """
        # TODO: Add reference to location/registration explanation in the docstring once it's written
        if isinstance(source, NumpySurface):
            height = source.height
            width = source.width
            content = source.render()

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
            raise TypeError("source must be an ndarray, NumpySurface, or be a KLibs Drawbject.")
        
        if any([not flip_x and P.blit_flip_x, flip_x]):
            content = np.fliplr(content)

        # Create and initialize OpenGL texture from source
        # TODO: Add support for texture caching
        gl.glEnable(gl.GL_TEXTURE_2D)
        t_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, t_id)
        gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE, content
        )

        # location[0] += P.screen_origin[0]
        # location[1] += P.screen_origin[1]
        # define boundaries coordinates of region being blit to
        x_bounds = [location[0], location[0] + width]
        y_bounds = [location[1], location[1] + height]

        # shift boundary mappings to reflect registration
        #
        # 7--8--9  Default assumes registration = 7, meaning that the top-left corner of the
        # 4--5--6  texture is aligned to the pixel coordinates given by 'location'. Alignment
        # 1--2--3  of the texture with the coordinates can be changed by choosing a different
        #          anchor point from 1 to 9, as illustrated in the diagram to the left.

        try:
            x_offset, y_offset = _build_registrations(height, width)[registration]
        except IndexError:
            raise ValueError("Registration must be an integer between 1 and 9 inclusive")

        x_bounds[0] += int(x_offset)
        x_bounds[1] += int(x_offset)
        y_bounds[0] += int(y_offset)
        y_bounds[1] += int(y_offset)

        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        gl.glTexCoord2f(0, 0)
        gl.glVertex2f(x_bounds[0], y_bounds[0])
        gl.glTexCoord2f(0, 1)
        gl.glVertex2f(x_bounds[0], y_bounds[1])
        gl.glTexCoord2f(1, 0)
        gl.glVertex2f(x_bounds[1], y_bounds[0])
        gl.glTexCoord2f(1, 1)
        gl.glVertex2f(x_bounds[1], y_bounds[1])
        gl.glEnd()

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glDeleteTextures([t_id])
        del t_id
        gl.glDisable(gl.GL_TEXTURE_2D)


def flip():
    """Displays the contents of the display buffer on the screen. Because the screen is
    only redrawn at certain intervals (every 16.7 ms for a typical 60 Hz LCD), this function
    will not return until the next redraw event occurs. 
    
    When in development mode, this function will print a warning in the console if the 
    screen takes longer than a single refresh to redraw. If this occurs often, it might
    indicate an issue with your graphics driver or display computer and suggests that
    you shouldn't rely on that setup for timing-sensitive experiments.

    For more information on how drawing works in KLibs, please refer to the documentation
    page explaining the graphics system.

    """
    from klibs.KLEnvironment import exp

    if exp:
        exp.before_flip()

    try:
        window = exp.window.window
    except AttributeError:
        raise ValueError("flip() cannot be called outside of the KLibs experiment runtime.")

    # Note: On some systems, redrawing the screen will sometimes take longer than expected (up to
    # 100ms in some cases). Since this is obviously a problem for timing-sensitive research, we
    # time how long each flip takes, and print a warning whenever it takes longer than expected
    # (with a threshold of 1ms).
    flip_start = precise_time()
    sdl2.SDL_GL_SwapWindow(window)
    flip_time = (precise_time() - flip_start) * 1000 # convert to ms
    if P.development_mode:
        if flip_time > (P.refresh_time + 1):
            warn = "Warning: Screen refresh took {0} ms (expected {1} ms)"
            print(warn.format("%.2f"%flip_time, "%.2f"%P.refresh_time))


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
