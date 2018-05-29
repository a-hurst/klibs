# -*- coding: utf-8 -*-
__author__ = 'jono'

import os
import re
import math
import time
import ctypes
import datetime
import traceback
from sys import exc_info
from math import sin, cos, acos, atan2, radians, pi, degrees, ceil

from sdl2 import (SDL_Event, SDL_PumpEvents, SDL_PushEvent, SDL_FlushEvents, SDL_RegisterEvents,
	SDL_PeepEvents, SDL_GetError, SDL_GetTicks,
	SDL_FIRSTEVENT, SDL_LASTEVENT, SDL_GETEVENT, SDL_MOUSEMOTION, 
	SDL_DISABLE, SDL_ENABLE, SDL_BUTTON, SDL_BUTTON_LEFT, SDL_BUTTON_RIGHT, SDL_BUTTON_MIDDLE,
	KMOD_SHIFT, KMOD_CAPS)
from sdl2.ext import get_events
from sdl2.mouse import SDL_ShowCursor, SDL_GetMouseState, SDL_WarpMouseGlobal, SDL_ShowCursor
from sdl2.keyboard import SDL_GetKeyName, SDL_GetModState

from klibs.KLConstants import (DATETIME_STAMP, DELIM_NOT_FIRST, DELIM_NOT_LAST, DELIM_WRAP, 
	TK_S, TK_MS)
from klibs import P


def arg_error_str(arg_name, given, expected, kw=True):
	if kw:
		err_string = "The keyword argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
	else:
		err_string = "The argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
	return err_string.format(arg_name, type(given), type(expected))


def angle_between(origin, p2, rotation=0, clockwise=False):
	angle = degrees(atan2(p2[1] - origin[1], p2[0] - origin[0])) + (-rotation if clockwise else rotation)
	return (angle if clockwise else -angle) % 360


def bool_to_int(boolean_val):
	if boolean_val is False: return 0
	if boolean_val is True: return 1
	raise ValueError("Non-boolean value passed ('{0}')".format(type(boolean_val)))


def boolean_to_logical(value, convert_integers=False):
	if convert_integers and value in [0, 1, '0', '1']:
		value = bool(int(value))
	logical = utf8(value).upper()
	if logical not in ['TRUE', 'FALSE']:
		return None
	return str(logical)


def bounded_by(pos, left, right, top, bottom):
	try:
		return (left < pos[0] < right and top < pos[1] < bottom)
	except TypeError:
		raise TypeError("'pos' must be [x,y] coordinates, other arguments must be numeric.")


def camel_to_snake(string):
	return re.sub('([a-z0-9])([A-Z])', r'\1_\2', re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)).lower()


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


def colored_stdout(string, print_string=True, args=[]):
	string = string.format(*args)
	end_col = re.compile(r"</([a-z_]{1,8})>")
	colors = {
			"<purple>": '\033[95m',
			"<purple_d>": '\033[35m',
			"<blue>": '\033[94m',
			"<blue_d>": '\033[34m',
			"<green>": '\033[92m',
			"<green_d>": '\033[32m',
			"<red>": '\033[91m',
			"<red_d>": '\033[31m',
			"<cyan>": '\033[96m',
			"<cyan_d>": '\033[36m',
			"<bold>": '\033[1m'
	}
	for c in colors:
		string = string.replace(c, colors[c])
	original_color = "\033[0m"
	string =  end_col.sub(original_color, string)
	if print_string:
		print(string)
	else:
		return string


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


def flush():
	"""Empties the event queue of all unprocessed input events. This should be called before
	any input-checking loops, to avoid any input events from before the loop being processed.
	
	"""
	pump()
	SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT)


def full_trace():
	exception_list = traceback.format_stack()
	exception_list = exception_list[:-2]
	exception_list.extend(traceback.format_tb(exc_info()[2]))
	exception_list.extend(traceback.format_exception_only(exc_info()[0], exc_info()[1]))

	exception_str = "Traceback (most recent call last):\n"
	exception_str += "".join(exception_list)
	# Removing the last \n
	return exception_str[:-1]


def getinput(*args, **kwargs):
	# python-agnostic function for getting console input. Saves us from requring 'future'
	# or 'six' compatibility package (for now, anyway).
	try:
		return raw_input(*args, **kwargs)
	except NameError:
		return input(*args, **kwargs)


def hide_mouse_cursor():
	"""Hides the mouse cursor if it is currently shown. Otherwise, this function does nothing.
	
	"""
	SDL_ShowCursor(SDL_DISABLE)


def img(name, sub_dirs=None):
	if sub_dirs:
		sub_dirs = os.path.join(*sub_dirs)
		return os.path.join(P.image_dir, sub_dirs, name)
	return os.path.join(P.image_dir, name)


def indices_of(element, container, identity_comparison=False):
	if identity_comparison:
		return [i for i, x in enumerate(container) if x is element]
	else:
		return [i for i, x in enumerate(container) if x == element]


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


def iterable(obj, exclude_strings=True):
	if exclude_strings:
		return hasattr(obj, '__iter__') and not isinstance(obj, str)
	else:
		try:
			iter(obj)
			return True
		except AttributeError:
			return False


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


def list_dimensions(target, dim=0):
	"""
	Tests if testlist is a list and how many dimensions it has
	returns -1 if it is no list at all, 0 if list is empty
	and otherwise the dimensions of it
	http://stackoverflow.com/questions/15985389/python-check-if-list-is-multidimensional-or-one-dimensional, u: bunkus
	"""
	if isinstance(target, list):
		return dim if not len(target) else list_dimensions(target[0], dim + 1)
	else:
		return -1 if dim == 0 else dim


def log(msg, priority):
	"""Writes a message to a log file (Note: the way logging in KLibs is handled will probably get
	rewritten soon, so I'd advise against using this).

	Args:
		msg (:obj:`str`): The message to record to the log file.
		priority (int): An integer from 1-10 specifying how important the event is, 1 being most
			critical and 10 being routine. If set to 0 it will always be printed, regardless of
			what the user sets verbosity to. You probably shouldn't do that.

	"""
	if priority <= P.verbosity:
		with open(P.log_file_path, 'a') as log_file:
			log_file.write(str(priority) + ": " + msg)


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


def mouse_pos(pump_event_queue=True, position=None, return_button_state=False):
	"""Returns the current coordinates of the mouse cursor, or alternatively warps the
	position of the cursor to a specific location on the screen.

	Args:
		pump_event_queue (bool, optional): Pumps the SDL2 event queue. See documentation
			for pump() for more information. Defaults to True.
		position (None or iter(int,int), optional): The x,y pixel coordinates to warp
			the cursor to if desired. Defaults to None.
		return_button_state (bool, optional): If True, return the mouse button currently
			being pressed (if any) in addition to the current cursor coordinates. Defaults
			to False.

	Returns:
		A 2-element Tuple containing the x,y coordinates of the cursor as integer values.
		If position is not None, this will be the coordinates the cursor was warped to.
		If return_button_state is True, the function returns a 3-element Tuple containing
		the x,y coordinates of the cursor and the mouse button state (left pressed = 1,
		right pressed = 2, middle pressed = 3, none pressed = 0).

	"""
	if pump_event_queue:
		SDL_PumpEvents()
	if not position:
		x, y = ctypes.c_int(0), ctypes.c_int(0)
		button_state = SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
		if return_button_state:
			if (button_state & SDL_BUTTON(SDL_BUTTON_LEFT)): pressed = 1
			elif (button_state & SDL_BUTTON(SDL_BUTTON_RIGHT)): pressed = 2
			elif (button_state & SDL_BUTTON(SDL_BUTTON_MIDDLE)): pressed = 3
			else: pressed = 0
			return (x.value, y.value, pressed)
		else:
			return (x.value, y.value)
	else:
		x, y = [int(n) for n in position]
		SDL_WarpMouseGlobal(x, y)
		return position


def mouse_angle(pump_event_queue=True, reference=None, rotation=0, clockwise=False):
	if pump_event_queue:
		SDL_PumpEvents()
	if reference is None:
		reference = P.screen_c
	return angle_between(reference, mouse_pos(), rotation, clockwise)


def now(format_time=False, format_template=DATETIME_STAMP):
	return datetime.datetime.fromtimestamp(time.time()).strftime(format_template) if format_time else time.time()


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


def pump(return_events=False):

	"""Pumps the SDL2 event queue and appends its contents to the EventManager log.
	 The SDL2 event queue contains SDL_Event objects representing keypresses, mouse
	 movements, mouse clicks, and other input events that have occured since last
	 check.

	 Pumping the SDL2 event queue clears its contents, so be careful of calling it
	 (or functions that call it implicitly) multiple times in the same loop, as it
	 may result in unexpected problems watching for input (e.g if you have two
	 functions checking for mouse clicks within two different boundaries and both
	 call pump(), the second one will only return True if a click within that boundary
	 occurred within the sub-millisecond interval between the first and second functions.)
	 To avoid these problems, you can manually fetch the queue once per loop and pass its
	 contents to each of the functions in the loop inspecting user input.

	Args:
		return_events (bool): If true, returns the contents of the SDL2 event queue.

	Returns:
		A list of SDL_Event objects, if return_events=True. Otherwise, the return 
		value is None.

	"""
	from klibs.KLEnvironment import evm
	while not evm.clock_sync_queue.empty():
		event = evm.clock_sync_queue.get()
		# put event into the SDL event queue
		sdl_event = SDL_Event()
		sdl_event.type = SDL_RegisterEvents(1)
		success = SDL_PushEvent(sdl_event)

		# store the event (along with it's data) in the EventManager's log
		event.append(sdl_event.type)
		evm.log_trial_event(*event)

		if success == 0: raise RuntimeError(SDL_GetError())
	# except AttributeError:
	#	pass  # for when called before evm initialized
	SDL_PumpEvents()

	# If we are using TryLink, check the SDL event queue after every pump and append any
	# mouse motion events to the TryLink event queue, where they can be used as a stand-in
	# for saccades.
	from klibs.KLEnvironment import el
	from klibs.KLEyeLink.KLTryLink import TryLink
	if isinstance(el, TryLink):
		while el.recording:
			evarray = (SDL_Event * 10)()
			ptr = ctypes.cast(evarray, ctypes.POINTER(SDL_Event))
			ret = SDL_PeepEvents(ptr, 10, SDL_GETEVENT, SDL_MOUSEMOTION, SDL_MOUSEMOTION)
			if ret <= 0:
				break
			el.mouse_event_queue += list(evarray)[:ret]
			if ret < 10:
				break

	if return_events:
		return get_events()


def pretty_join(array, whitespace=1, delimiter="'", delimit_behaviors=None, wrap_each=None,
					prepend=None, before_last=None, each_n=None, after_first=None, append=None):
	"""Automates string combination. Parameters:
	:param array: A list of strings to be joined
	:param config: A dict with any of the following keys:

	**Config Keys**

	+-------------------+---------------------------------------------------------------------------------------------------+
	| **Key**           |     **Description**                                                                               |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| prepend           |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| afterFirst        |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| beforeLast        |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| eachN             |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| whitespace        | Whitespace to place between elements. Should be a positive integer, but can be a string if the    |
	|                   | number is smaller than three and greater than zero. May also be the string None or False, but     |
	|                   | you should probably just not set it if that's what you want.                                      |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| append            |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| delimiter         |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| delimitBehavior   |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+
	| delimitBehaviour  |      [coming]                                                                                     |
	+-------------------+---------------------------------------------------------------------------------------------------+

	"""
	ws = str()
	for n in range(whitespace):
		ws += ' '
	whitespace = ws

	output = ''
	if prepend is not None:
		output = prepend
	for n in range(len(array)):
		#if after first iteration, print whitespace
		if n > 1:
			output += whitespace
		#if beforeLast is set, print it and add whitespace
		if (n == (len(array) - 1)) and before_last is not None:
			output += before_last + whitespace
		# if eachN is set and the iterator is divisible by N, print an eachN and add whitespace
		if each_n is tuple:
			if len(each_n) == 2:
				if type(each_n[0]) is int:
					if n % each_n == 0:
						output += str(each_n[1]) + whitespace
				else:
					log_str = "Klib.prettyJoin() config parameter 'eachN[0]' must be an int, '{0}' {1} passed. {2}"
					print(log_str.format(each_n, type(each_n, 10)))
			else:
				raise ValueError("Argument 'each_n' must have length 2.")
		elif each_n is not None:
			raise TypeError("Argument 'each_n' must be a tuple of length 2.")

		# if delimiter is set to default or wrap, print a delimiter before the array item
		if DELIM_WRAP in delimit_behaviors:
			output += delimiter

		# finally print the array item
		if wrap_each:
			output += wrap_each + str(array[n]) + wrap_each
		else:
			output += str(array[n])
		if n == 1 and DELIM_NOT_FIRST in delimit_behaviors:
			output += whitespace
		elif n == len(array) - 1 and DELIM_NOT_LAST in delimit_behaviors:
			pass
		elif n == len(array) - 2 and DELIM_NOT_LAST in delimit_behaviors:
			output += delimiter
		else:
			output += delimiter + whitespace

		# if after_first is set, print it and add whitespace
		if (n == 0) and (after_first is not None):
			output += after_first + whitespace
	if append is not None:
		output += append

	return output


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


def show_mouse_cursor():
	"""Unhides the mouse cursor if it is currently hidden. Otherwise, this function does nothing.

	"""
	SDL_ShowCursor(SDL_ENABLE)


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


def sdl_key_code_to_str(sdl_keysym):
	key_name = SDL_GetKeyName(sdl_keysym).replace(b"Keypad ", b"")
	key_name = str(key_name.decode('utf-8')) # for py3k compatibility
	if key_name == "Space":
		return " "
	if not any(SDL_GetModState() & mod for mod in [KMOD_CAPS, KMOD_SHIFT]):
		# if not holding Shift or Caps Lock isn't on, make letter lower case.
		key_name = key_name.lower()
	return key_name if len(key_name) == 1 else False # if key is not alphanumeric


def snake_to_camel(string):
	words = string.split('_')
	return words[0] + "".join(x.title() for x in words[1:])


def snake_to_title(string):
	words = string.split('_')
	return words[0] + "".join(x.title() for x in words)


def str_pad(string, str_len, pad_char=" ", pad_dir="r"):
	pad_len = str_len - len(string)
	if pad_len < 1:
		raise ValueError("Desired string length shorter current string.")
	padding = "".join([pad_char] * pad_len)
	return string+padding if pad_dir == "r" else padding+string


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


def type_str(var):
	"""Returns the type name of a variable as a string (e.g. 'int' if the passed variable is
	an int).
	
	Args:
		var: The variable to determine the type of.

	Returns:
		str: The name of the passed variable's type.

	"""
	return type(var).__name__


def utf8(x):
	'''A Python 2/3 agnostic function for converting things to unicode strings. Equivalent to
	unicode() in Python 2 and str() in Python 3.
	
	Args:
		x: The number, string, or other object to convert to unicode.
	
	Returns:
		unicode or str: a unicode string in Python 2, and a regular (unicode) string in Python 3.
	
	'''
	try:
		return unicode(x)
	except NameError:
		return str(x)


def valid_coords(coords):
	"""Checks whether a variable is a valid pair of (x,y) coordinates.
	
	Args:
		coords: The variable to check for being a valid pair of coordinates.
	
	Returns:
		bool: True if coords is a two-item iterable (e.g. a List or Tuple) that contains only
			ints or floats, otherwise False.
	
	"""
	try:
		return len(coords) == 2 and all([type(i) in [int, float] for i in coords])
	except TypeError:
		return False

		
def smart_sleep(interval, units=TK_MS):
	from klibs.KLUserInterface import ui_request
	from time import time
	if units == TK_MS:
		interval *= .001
	start = time()
	while time() - start < interval:
		ui_request()


def acute_angle(vertex, p1, p2):
	v_p1 = float(line_segment_len(vertex, p1))
	v_p2 = float(line_segment_len(vertex, p2))
	p1_p2 = line_segment_len(p1, p2)
	return degrees(acos((v_p1**2 + v_p2**2 - p1_p2**2) / (2 * v_p1 * v_p2)))
