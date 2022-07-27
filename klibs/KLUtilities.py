# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import re
import math
import base64
from hashlib import sha512
from math import sin, cos, acos, atan2, radians, pi, degrees, ceil

from klibs import P
from klibs.KLInternal import (
	boolean_to_logical, colored_stdout, full_trace, log, now, iterable, utf8,
	valid_coords
)
from klibs.KLEventQueue import pump, flush
from klibs.KLUserInterface import show_mouse_cursor, hide_mouse_cursor, mouse_pos, smart_sleep



def acute_angle(vertex, p1, p2):
	# this is poorly named: acute angle is any angle under 90 degrees, but this function
	# calculates the angle between the two lines (vertex -> p1) and (vertex -> p2).
	# Currently only used once in TraceLab, so can probably rename. Docs would benefit from
	# an illustration.
	v_p1 = float(line_segment_len(vertex, p1))
	v_p2 = float(line_segment_len(vertex, p2))
	p1_p2 = line_segment_len(p1, p2)
	return degrees(acos((v_p1**2 + v_p2**2 - p1_p2**2) / (2 * v_p1 * v_p2)))


def angle_between(origin, p2, rotation=0, clockwise=False):
	angle = degrees(atan2(p2[1] - origin[1], p2[0] - origin[0])) + (-rotation if clockwise else rotation)
	return (angle if clockwise else -angle) % 360


def bounded_by(pos, left, right, top, bottom):
	try:
		return (left < pos[0] < right and top < pos[1] < bottom)
	except TypeError:
		raise TypeError("'pos' must be [x,y] coordinates, other arguments must be numeric.")


def canvas_size_from_points(points, flat=False):
	"""Determines the size of the smallest canvas (e.g. Drawbject surface) required to contain a
	shape defined by a list of x,y points. 

	Args:
		points (:obj:`List`): A list of points that make up the shape to determine canvas size for.
		flat (bool): Indicates whether the list of points is nested (e.g. [(x,y), (x,y), ...]) or 
			flat (e.g. [x, y, x, y, ...]). Defaults to False (nested).

	Returns:
		A List containing the width and height (respectively) of the smallest canvas able to contain
		the shape defined by the points.

	"""
	x_points = []
	y_points = []
	if flat: # aggdraw takes flat xy lists
		for i in range(0, len(points), 2):
			x_points.append(points[i])
			y_points.append(points[i+1])
	else:
		for point in points:
			x_points.append(point[0])
			y_points.append(point[1])
	w = int(max(x_points) - min(x_points)) + 2
	h = int(max(y_points) - min(y_points)) + 2
	return [w, h]


def chunk(items, chunk_size):
	"""Yield successive chunk-sized chunks from items."""
	for i in range(0, len(items), chunk_size):
		yield items[i:i+chunk_size]


def clip(value, minimum, maximum):
	"""Restricts a numeric value to within given range.

	Args:
		value (numeric): The numeric value to be clipped.
		minimum (numeric): The lower bound of the allowable range.
		maximum (numeric): The upper bound of the allowable range.

	Returns:
		value, if value is between minimum and maximum, maximum, if value is greater than maximum,
		or minimum, if value is less than minimum.
	
	"""
	if value > maximum:
		value = maximum
	elif value < minimum:
		value = minimum
	return value


def deg_to_px(deg, even=False):
	"""Converts degrees of visual angle to pixels, based on the diagonal size of the screen in
	inches and the viewing distance from the screen (set at launch and with `P.viewing_distance`
	in the project's params.py file, respectively).

	Args:
		deg (float): The size in degrees of visual angle to convert to pixels.
		even (bool, optional): If True, returned value will be rounded to the nearest even number.

	Return:
		int: The size in pixels corresponding to the given size in degrees.

	"""
	if even:
		px = ceil((deg * P.ppd) / 2.0) * 2
	else:
		px = deg * P.ppd
	return int(px)


def interpolated_path_len(points):
	# where points is a list of coordinate tuples
	path_len = 0
	for i in range(0, len(points)):
		try:
			p1 = [1.0 * points[i][0], 1.0 * points[i][1]]
			p2 = [1.0 * points[i + 1][0], 1.0 * points[i + 1][1]]
			path_len += line_segment_len(p1, p2)
		except IndexError:
			p1 = [1.0 * points[i][0], 1.0 * points[i][1]]
			p2 = [1.0 * points[0][0], 1.0 * points[0][1]]
			path_len += line_segment_len(p1, p2)
	return path_len


def linear_intersection(line_1, line_2):
	# first establish if lines are given as absolute lengths or origins and angles
	l1_xy = None
	l2_xy = None
	try:
		if not all(iterable(p) for p in line_1 + line_2):
			# allow for rotation and clockwise arguments to be passed
			l1_xy = (line_1[0], point_pos(line_1[0], 9999999, *line_1[1:]))
			l2_xy = (line_2[0], point_pos(line_2[0], 9999999, *line_2[1:]))
	except AttributeError:
		raise ValueError("Expected each line to be either 2 x,y pairs or and x,y pair and an radial description.")
	d_x = (l1_xy[0][0] - l1_xy[1][0], l2_xy[0][0] - l2_xy[1][0])
	d_y = (l1_xy[0][1] - l1_xy[1][1], l2_xy[0][1] - l2_xy[1][1])

	def determinant(a, b):
		return a[0] * b[1] - a[1] * b[0]

	div = determinant(d_x, d_y)

	if not div:
		raise Exception('Supplied lines do not intersect.')
	d = (determinant(*l1_xy[0:2]), determinant(*l2_xy[0:2]))
	return (determinant(d, d_x) / div, determinant(d, d_y) / div)


def line_segment_len(a, b):
	"""Determines the distance between two points on a 2D plane (e.g. the distance
	between two pairs of x,y pixel coordinates).

	Args:
		a (iter(x, y)): An iterable containing a single pair of x,y coordinates.
		b (iter(x, y)): An iterable containing a single pair of x,y coordinates.

	Returns:
		The distance between points a and b.

	"""
	dy = b[1] - a[1]
	dx = b[0] - a[0]
	return math.sqrt(dy**2 + dx**2)


def make_hash(x, n_bytes=16):
	"""Produces a hash string for a given input, with the length of the hash string being
	determined by the number of bytes (more bytes = longer string).

	Hashes are encoded with SHA-512 and converted to strings using base64 encoding. The
	number of requested bytes must be an integer between 1 and 64. 

	Args:
		x: The number, string, or other object to hash. Must be coercible to a string.
		n_bytes (optional): The number of bytes to use from the hash.

	Returns:
		A string object containing the generated hash.

	"""
	s = utf8(x)
	h = sha512(s.encode('utf-8')).digest()[:n_bytes]
	encoded = base64.b64encode(h, altchars=b"_-")
	return str(encoded.decode('utf-8').strip('='))


def midpoint(p1, p2):
	"""Determines the midpoint between two points on a plane (e.g. between two pixels on a screen).
	
	Args:
		p1 (:obj:`Tuple`): The first of the two points.
		p2 (:obj:`Tuple`): The second of the two points.

	Returns:


	"""
	return (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2


def mean(values):
	"""Calculates the mean of a list (or other iterable) of numeric values.

	Args:
		values (:obj:`List`): A List (or other iterable) containing intergers and/or floats.
	
	Returns:
		float: The mean of all values in the 'values' iterable.

	"""
	return sum(values) / float(len(values))


def peak(v1, v2):
	"""Returns the greater of two values.

	Args:
		v1 (numeric): The first value to be compared.
		v2 (numeric): The second value to be compared.

	Returns:
		The greater of the two values. If both values are equal, v2 is returned.

	"""
	if v1 > v2:
		return v1
	else:
		return v2


def point_pos(origin, amplitude, angle, rotation=0, clockwise=False, return_int=True):
	"""Determine the location of a point on a 2D surface given an origin point, a distance, and
	an angle.

	[would benefit from an illustration]

	Args:
		origin (:obj:`Tuple`): The origin point that the returned point will be relative to.
		amplitude (int or float): The distance between the origin point and the point to be
			returned.
		rotation (float): The angle between the origin point and the point to be returned.
		clockwise (bool, optional): Whether the rotation value is clockwise or not. Defaults to
			False.
		return_int (bool, optional): Whether the returned coordinates should be ints (useful for
			pixels) or floats (most other use-cases). Defaults to True (i.e. returns ints).
	
	Returns:
		:obj:`Tuple`: A 2-item Tuple containing the (x,y) coordinates of the calculated point.
	
	"""
	try:
		origin = tuple(origin)
		angle += rotation
		theta_rad = radians((angle if clockwise else -angle) % 360)
		x_pos = origin[0] + (amplitude * cos(theta_rad))
		y_pos = origin[1] + (amplitude * sin(theta_rad))
		if return_int:
			x_pos = int(x_pos)
			y_pos = int(y_pos)
		return (x_pos, y_pos)
	except Exception:
		err = "point_pos error (start: {0}, amp: {1}, ang: {2}, rot: {3})"
		print(err.format(origin, amplitude, angle, rotation))
		raise


def pretty_list(items, sep=',', space=' ', before_last='or', brackets='[]', pad=True):
	"""Takes an iterable (e.g. a :obj:`List`) and creates a nicely-formatted string from its
	contents. Useful for creating a list of possible options or responses to show to participants.
	
	For example, the :obj:`tuple` ``(1, 2, 'a', 'b')`` would be outputted as ``[ 1, 2, a, or b ]``
	using the default settings.
	
	Args:
		sep (str, optional): The character that separates elements in the list. Defaults to comma.
		space (str, optional): The space between elements of the list. Defaults to a single space.
		before_last (str, optional): A string to add before the last item of the list. Defaults to
			'or'.
		brackets (str, optional): A string containing the characters to use for brackets around
			the list, e.g. '[]' or '<>'. If empty, no brackets will be used. Defaults to '[]'.
		pad (bool, optional): Whether to put a space between the list items and the containing
			brackets. Defaults to True.
	
	Returns:
		A formatted string.
	
	"""
	
	items = [str(item) for item in items]
 
	if len(items) > 1:
		
		if before_last:
			items[-1] = before_last + space + items[-1]
		delim = space if len(items) == 2 and before_last else (sep + space)
		joined = delim.join(items)
	
	else:
		joined = ''.join(items)
	
	if brackets:
		prepend = brackets[0]+space if pad else brackets[0]
		append = space+brackets[1] if pad else brackets[1]
		return prepend+joined+append
	else:
		return joined


def px_to_deg(px):
	"""Converts pixels to degrees of visual angle, based on the diagonal size of the screen in
	inches and the viewing distance from the screen (set at launch and with `P.viewing_distance`
	in the project's params.py file, respectively).

	Args:
		px (int): The size in pixels to be converted to degrees of visual angle.

	Return:
		float: The size in degrees corresponding to the given size in pixels.

	"""
	return float(px) / P.ppd


def rotate_points(points, origin, angle, clockwise=True, flat=False):
	"""Rotates a list of x,y points around an origin point in 2d coordinate space.

	Args:
		points (:obj:`List`): The list of points to rotate.
		origin (iter(x, y)): The x,y coordinates of the point to rotate the given points around.
		angle (numeric): The angle in degrees by which to rotate the points around the origin.
		clockwise(bool): Whether to rotate the points clockwise or counterclockwise. Defaults to
			True (clockwise).
		flat (bool): Indicates whether the list of points is nested (e.g. [(x,y), (x,y), ...]) or 
			flat (e.g. [x, y, x, y, ...]). Defaults to False (nested).

	Returns:
		A List of rotated points in the format specified by flat (i.e. the translated
		points will be nested if flat=False and flat if flat=True).

	"""
	rad_angle = radians((angle if clockwise else -angle) % 360)
	rotated = []
	if flat: # aggdraw takes flat xy lists
		for i in range(0, len(points), 2):
			dx = points[i] - origin[0]
			dy = points[i+1] - origin[1]
			rx = origin[0] + cos(rad_angle) * dx - sin(rad_angle) * dy
			ry = origin[1] + sin(rad_angle) * dx + cos(rad_angle) * dy
			# values rounded to 12 decimal places to avoid 0.99999999999...
			rotated += [round(rx, 12), round(ry, 12)]
	else:
		for point in points:
			dx = point[0] - origin[0]
			dy = point[1] - origin[1]
			rx = origin[0] + cos(rad_angle) * dx - sin(rad_angle) * dy
			ry = origin[1] + sin(rad_angle) * dx + cos(rad_angle) * dy
			rotated.append((round(rx, 12), round(ry, 12)))
	return rotated


def scale(coords, canvas_size, target_size=None, scale=True, center=True):
	"""Scales and/or centers pixel coordinates intended for use at a given resolution to a
	smaller or larger resolution, maintaining aspect ratio.
	
	For example, if an animation was written based on the pixel coordinates of a 1920x1080 display
	and you wanted to be able to use it on screens with smaller or larger resolutions, you could
	use this function to scale its coordinates to fit the screen based on its height and width in
	pixels. If the target size is larger or a different aspect ratio than the canvas (original)
	size, you can also optionally translate coordinates so that they are centered in the middle of
	the screen.
	
	This function should only be used when expressing your layout in degrees of visual angle 
	or fractions of screen height/width is impossible or impractical.

	Args:
		coords (tuple): The (x,y) coordinates to scale.
		canvas_size (tuple): The size in pixels of the original surface.
		target_size (tuple, optional): The size in pixels of the intended output surface. Defaults
			to the current screen resolution (P.screen_x_y).
		scale (bool, optional): If True, the input coordinates will be scaled to target_size.
		center (bool, optional): If True, and target_size is larger canvas_size or has a different
			aspect ratio, the input coordinates will be translated so that the they are aligned to
			the center of the target surface and not the upper-left corner.

	Returns:
		tuple: The scaled (x,y) coordinates.

	"""
	x,y = coords
	if tuple(canvas_size) == P.screen_x_y:
		return coords
	if not target_size:
		target_size = P.screen_x_y if scale else canvas_size
	if scale:
		canvas_size = [float(i) for i in canvas_size]
		target_size = [float(i) for i in target_size]
		canvas_ratio = canvas_size[0]/canvas_size[1]
		target_ratio = target_size[0]/target_size[1]
		if target_ratio > canvas_ratio:
			target_size[0] = target_size[1]*canvas_ratio
		elif target_ratio < canvas_ratio:
			target_size[1] = target_size[0]/canvas_ratio
		x = int( (x/canvas_size[0])*target_size[0] )
		y = int( (y/canvas_size[1])*target_size[1] )
	
	if center:
		x = x + int(P.screen_x/2 - (target_size[0]/2))
		y = y + int(P.screen_y/2 - (target_size[1]/2))
	return (x,y)


def translate_points(points, delta, flat=False):
	"""Translates a list of x,y points in 2d coordinate space.

	Args:
		points (:obj:`List`): The list of points to translate.
		delta (iter(dx, dy)): An iterable containing the dx and dy values to translate all
			points by.
		flat (bool): Indicates whether the list of points is nested (e.g. [(x,y), (x,y), ...]) or 
			flat (e.g. [x, y, x, y, ...]). Defaults to False (nested).

	Returns:
		A List of points translated by delta in the format specified by flat (i.e. the translated
		points will be nested if flat=False and flat if flat=True).

	"""
	translated = []
	if flat: # aggdraw takes flat xy lists
		for i in range(0, len(points), 2):
			dx = points[i] + delta[0]
			dy = points[i+1] + delta[1]
			translated += [dx, dy]
	else:
		for point in points:
			dx = point[0] + delta[0]
			dy = point[1] + delta[1]
			translated.append((dx, dy))
	return translated
