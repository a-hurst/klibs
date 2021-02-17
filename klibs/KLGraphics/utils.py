# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import numpy as np
from PIL import Image

from klibs import P

"""This module contains a few utility functions for working with graphics and rendering.

Primarily for internal use within the KLGraphics modules, as NumpySurface provides a
friendlier API for most of these, but they may come in handy in some projects.

"""


def _build_registrations(source_height, source_width):
    return ((),
        (0, -1.0 * source_height),
        (-1.0 * source_width / 2.0, -1.0 * source_height),
        (-1.0 * source_width, -1.0 * source_height),
        (0, -1.0 * source_height / 2.0),
        (-1.0 * source_width / 2.0, -1.0 * source_height / 2.0),
        (-1.0 * source_width, -1.0 * source_height / 2.0),
        (0, 0),
        (-1.0 * source_width / 2.0, 0),
        (-1.0 * source_width, 0)
    )


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


def add_alpha(array, opacity=255):
	"""Adds an alpha channel to a numpy array of an RGB image, making it an RGBA texture that can
	be drawn to the screen using :func:`~klibs.KLGraphics.blit`. If the array already has an alpha
	channel, this function will do nothing.
	
	Significantly faster than converting RGB to RGBA using Pillow as a go-between.

	Args:
		array (:obj:`numpy.ndarray`): A 3-dimensional Numpy array of an RGB or RGBA texture.
		opacity (int, optional): The opacity to set for the alpha layer, between 0 (fully
			transparent) and 255 (fully opaque) inclusive. Defaults to 255.

	Returns:
		:obj:`numpy.ndarray`: A 3-dimensional Numpy array of an RGBA texture.

	"""
	if len(array.shape) != 3 or array.shape[2] < 3 or array.dtype != np.uint8:
		raise ValueError("Argument 'array' must a Numpy array of an RGB or RGBA image.")
	if array.shape[2] == 3:
		alpha = np.full((array.shape[0], array.shape[1], 1), opacity, dtype=np.uint8)
		array = np.dstack((array, alpha))
	return array


def aggdraw_to_array(surface, preserve_mode=False):
	"""Converts an :obj:`aggdraw.Draw` object to a :obj:`numpy.ndarray` of the same size. By
	default, this will also convert the colour mode of the output to RGBA.

	Args:
		surface (:obj:`aggdraw.Draw`): The aggdraw surface to convert.
		preserve_mode (:bool:, optional): Whether to preserve the colour mode of the given surface
			instead of converting to RGBA. Defaults to False.

	Returns:
		:obj:`numpy.ndarray`: A Numpy array of the given aggdraw surface.

	"""
	# NOTE: This should be undocumented; user shouldn't have to know or care what aggdraw is
	surface_img = Image.frombytes(surface.mode, surface.size, surface.tobytes())
	if surface.mode != 'RGBA' and not preserve_mode:
		surface_img = surface_img.convert('RGBA')
	return np.asarray(surface_img)


def image_file_to_array(path):
	"""Imports an image from the specified file path. If the image is not in RGBA format, this
	function will attempt to convert it to RGBA so it can be drawn to the screen using
	:func:`~klibs.KLGraphics.blit`.

	For supported image file types, see 
	`here <https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html>`_.

	Args:
		path (:obj:`str`): A valid path to a supported image file type. Path can be absolute 
			or relative to the project's `ExpAssets/Resources/image/` folder.
	
	Returns:
		:obj:`numpy.ndarray`: A 3-dimensional Numpy array of an RGBA texture.
	
	"""
	# Check if path is relative to project's image directory
	if P.image_dir and os.path.isfile(os.path.join(P.image_dir, path)):
		path = os.path.join(P.image_dir, path)
	elif not os.path.isfile(path):
		raise IOError("Unable to locate image file at ({0})".format(path))

	img = Image.open(path)
	if img.mode != 'RGBA':
		if img.mode == 'RGB':
			return add_alpha(np.array(img))
		img = img.convert('RGBA')
	return np.array(img)
