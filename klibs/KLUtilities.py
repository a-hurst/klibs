# -*- coding: utf-8 -*-
__author__ = 'jono'

import math
import sys
import os
import KLParams as Params
from KLConstants import *
import datetime
import sdl2
import ctypes
import time
import datetime
import re

def absolute_position(position, destination):
	#  if pixel coordinates are supplied by accident or automatically
	if iterable(position) and all(type(i) is int for i in position): return position

	height = None
	width = None
	try:  # ie. a numpy array
		height = destination.shape[0]
		width = destination.shape[1]
	except:
		pass
	if height is None and width is None:
		try:  # ie. a NumpySurface object
			height = destination.height
			width = destination.width
		except:
			pass
	if height is None and width is None:
		try:
			iter(destination)
			if all(type(i) is int for i in [destination[0], destination[1]]):
				height = destination[1]
				width = destination[0]
		except:
			pass
	if height is None and width is None:
		try:
			height = Params.screen_y
			width = Params.screen_x
		except:
			raise TypeError("Argument 'destination' invalid; must be [x,y] iterable, numpy.ndarray or klibs.NumpySurface.")

	#  Older version of KLIBs didn't use location constants; this converts old string-style location identifiers
	if position in LEGACY_LOCATIONS: position = LEGACY_LOCATIONS[position]

	locations = {
		BL_CENTER: [width // 2, height // 2],
		BL_TOP_LEFT: [0, 0],
		BL_TOP: [width // 2, 0],
		BL_TOP_RIGHT: [width, 0],
		BL_LEFT: [0, height // 2],
		BL_RIGHT: [0, height],
		BL_BOTTOM_LEFT: [0, height],
		BL_BOTTOM: [width // 2, height],
		BL_BOTTOM_RIGHT: [width, height]
	}

	try:
		return locations[position]
	except:
		raise IndexError("Invalid position identifier.")


def arg_error_str(arg_name, given, expected, kw=True):
	if kw:
		err_string = "The keyword argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
	else:
		err_string = "The argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
	return err_string.format(arg_name, type(given), type(expected))


def bounded_by(self, pos, left, right, top, bottom):
		"""


		:param pos:
		:param left:
		:param right:
		:param top:
		:param bottom:
		:return: :raise TypeError:
		"""
		xpos = int(pos[0])
		ypos = int(pos[1])
		# todo: tighten up that series of ifs into one statement
		if all(type(val) is int for val in (left, right, top, bottom)) and type(pos) is tuple:
			if xpos > left:
				if xpos < right:
					if ypos > top:
						if ypos < bottom:
							return True
						else:
							return False
					else:
						return False
				else:
					return False
			else:
				return False
		else:
			e = "Argument 'pos' must be a tuple, others must be integers."
			raise TypeError()


def build_registrations(source_height, source_width):
	return ((),
		(0, -1.0 * source_height),
		(-1.0 * source_width / 2.0, source_height),
		(-1.0 * source_width, -1.0 * source_height),
		(0, -1.0 * source_height / 2.0),
		(-1.0 * source_width / 2.0, -1.0 * source_height / 2.0),
		(-1.0 * source_width, -1.0 * source_height / 2.0),
		(0, 0),
		(-1.0 * source_width / 2.0, 0),
		(-1.0 * source_width, 0))


def deg_to_px(deg):
	return int(deg * Params.ppd)  # todo: error checking?


def equiv(comparator, canonical):
	equivalencies = {
					"inch": ["in", "inch"],
					"inches": ["ins", "inches"],
					"cm": ["centimeter", "cm"],
					"cms": ["centimeters", "cms"],
					"CRT": ["crt", "CRT"],
					"LCD": ["lcd", "LCD"]
	}

	if canonical in equivalencies:
		return comparator in equivalencies[canonical]
	else:
		return False


def exp_file_name(file_type, participant_id=None, date=None, incomplete=False, as_string=True):
	participant_id = Params.participant_id if participant_id is None else participant_id
	file_name_str = "p{0}_{1}{2}"
	duplicate_file_name_str = "p{0}.{1}_{2}{3}"

	if date is None:
		date_query = "SELECT `created` FROM `participants` WHERE `id` = {0}".format(participant_id)
		date = Params.database.query(date_query).fetchall()[0][0][:10]
	if file_type == PARTICIPANT_FILE:
		file_extension = TF_DATA
		if incomplete:
			file_path = Params.incomplete_data_path
			file_name_str = "p{0}_{1}_incomplete.txt"
			duplicate_file_name_str = "p{0}.{1}_{2}_incomplete" + TF_DATA
		else:
			file_path = Params.data_path
	else:
		date = date[5:].replace("-", "")
		file_extension = EDF_EXT
		file_path = Params.edf_path
		file_name = file_name_str.format(participant_id, date, file_extension)
		return [file_name, os.path.join(file_path, file_name)]

	file_name = file_name_str.format(participant_id, date, file_extension)  # second format arg = date sliced from date-time
	if os.path.isfile(os.path.join(file_path, file_name)):
		unique_file = False
		append = 1
		while not unique_file:
			file_name = duplicate_file_name_str.format(participant_id, append, date)
			if not os.path.isfile(os.path.join(file_path, file_name)):
				unique_file = True
			else:
				append += 1

	return os.path.join(file_path, file_name) if as_string else [file_path, file_name]


def log(msg, priority):
	"""Log an event
	:param msg: The string to log
	:param priority: An integer from 1-10 specifying how important the event is, 1 being most critical and 10 being routine. If set to 0 it will always be printed, regardless of what the user sets verbosity to. You probably shouldn't do that.
	"""
	if priority <= Params.verbosity:
		with open(Params.log_file_path, 'a') as log_file:
			log_file.write(str(priority) + ": " + msg)
	return True


def mouse_pos(pump=True):
	if pump:
		sdl2.SDL_PumpEvents()
	x, y = ctypes.c_int(0), ctypes.c_int(0)
	sdl2.mouse.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
	return [x.value, y.value]


def hide_mouse_cursor():
	sdl2.mouse.SDL_ShowCursor(sdl2.SDL_DISABLE)
	return sdl2.SDL_PumpEvents()


def show_mouse_cursor():
	sdl2.mouse.SDL_ShowCursor(sdl2.SDL_ENABLE)
	return sdl2.SDL_PumpEvents()


def peak(v1, v2):
	if v1 > v2:
		return v1
	else:
		return v2


def pump():  # a silly wrapper because Jon always forgets the sdl2 call
	return sdl2.SDL_PumpEvents()


def pretty_join(array, whitespace=1, delimiter="'", delimit_behavior=None, prepend=None, before_last=None, each_n=None, after_first=None, append=None):
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
			output = output + whitespace
		#if beforeLast is set, print it and add whitespace
		if (n == (len(array) - 1)) and before_last is not None:
			output = output + before_last + whitespace
		# if eachN is set and the iterator is divisible by N, print an eachN and add whitespace
		if each_n is tuple:
			if len(each_n) == 2:
				if type(each_n[0]) is int:
					if n % each_n == 0:
						output = output + str(each_n[1]) + whitespace
				else:
					log_str = "Klib.prettyJoin() config parameter 'eachN[0]' must be an int, '{0}' {1} passed. {2}"
					log(log_str.format(each_n, type(each_n, 10)))
			else:
				raise ValueError("Argument 'each_n' must have length 2.")
		elif each_n is not None:
			raise TypeError("Argument 'each_n' must be a tuple of length 2.")
		# if delimiter is set to default or wrap, print a delimiter before the array item
		if delimit_behavior in ('wrap', None):
			output += delimiter
		# finally print the array item
		output = output + str(array[n]) + delimiter + whitespace
		# if afterFirst is set, print it and add whitespace
		if (n == 0) and (after_first is not None):
			output = output + after_first + whitespace
	if append is not None:
		output = output + append

	return output


def iterable(obj, exclude_strings=True):
	if exclude_strings:
		return hasattr(obj, '__iter__')
	else:
		try:
			iter(obj)
			return True
		except AttributeError:
			return False


def pt_to_px(pt_size):
	if type(pt_size) is not int:
		raise TypeError("Argument 'pt_size' must be an integer.")
	if 512 < pt_size < 2:
		raise ValueError("Argument 'pt_size' must be between 2 and 512.")
	if Params.dpi is not None:
		dpi = Params.dpi
	else:
		dpi = 96  # CRT default

	return int(math.floor(1.0 / 72 * dpi * pt_size))


def px_to_deg(length):  # length = px
	return int(length / Params.ppd)


def rgb_to_rgba(rgb):
	return rgb[0], rgb[1], rgb[2], 1


def type_str(var):
	return type(var).__name__


def bool_to_int(boolean_val):
	if boolean_val is False: return 0
	if boolean_val is True: return 1
	raise ValueError("Non-boolean value passed ('{0}')".format(type(boolean_val)))


def safe_flag_string(flags, prefix=None, uc=True):
	if prefix and type(prefix) is not str:
		e = "The keyword argument, 'prefix', must be of type 'str' but '{0}' was passed.".format(type(prefix))
		raise TypeError(e)

	if type(flags) is list:
		for i in range(0, len(flags)):
			if uc:
				flags[i] = flags[i].upper()
			else:
				flags[i] = flags[i]
			if prefix:
				flags[i] = prefix + "." + flags[i]
		flag_string = " | ".join(flags)

	else:
		raise TypeError("The 'flags' argument must be of type 'list' but '{0}' was passed.".format(type(flags)))

	return eval(flag_string)


def now(as_timestamp=False):
	time_str = time.time()
	if as_timestamp:
		try:
			time_str = datetime.datetime.fromtimestamp(time_str).strftime(as_timestamp)
		except:
			time_str = datetime.datetime.fromtimestamp(time_str).strftime('%Y-%m-%d %H:%M:%S')
	return time_str


def quit(msg=None):
	if msg:
		print msg
	print "Exiting..."
	sdl2.SDL_Quit()
	sys.exit()


class RGBCLI:
	col = {"@P": '\033[95m',  # purple
		   "@B": '\033[94m',  # blue
		   "@R": '\033[91m',  # red
		   "@T": '\033[1m',   # teal
		   "@E": '\033[0m'    # return to normal
	}

def pr(namespace, *args):
	components = []
	print namespace
	for var in args:
		element = ([name, value] for (name, value) in namespace.iteritems() if var is value)
		components.append([i for i in element])
	print components
	names =	[i[0] for i in components]
	values = [i[1] for i in components]
	print_str = ""
	for name in names:
		print_str += name + ": {" + names.index(name) + "}"
		if names.index(name) != len(names) - 1:
			print_str += ", "
	print print_str.format(*values)


def camel_to_snake(string):
	return re.sub('([a-z0-9])([A-Z])', r'\1_\2', re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)).lower()


def snake_to_camel(string):
	words = string.split('_')
	return words[0] + "".join(x.title() for x in words[1:])


def snake_to_title(string):
	words = string.split('_')
	return words[0] + "".join(x.title() for x in words)


def boolean_to_logical(value, convert_integers=False):
	if value in ["false", "False"] or value is False: return "FALSE"
	if value in ["true", "True"] or value is True: return "TRUE"
	if convert_integers is True:
		if value in [1,"1"]: return "TRUE"
		if value in [0,"0"]: return "FALSE"
	return None

