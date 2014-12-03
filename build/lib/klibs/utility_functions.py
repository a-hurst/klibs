__author__ = 'jono'
import numpy
import sdl2
import sdl2.ext
import math
import sys

import params as Params


def absolute_position(position, destination):
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

	locations = {
		'center': [width // 2, height // 2],
		'topLeft': [0, 0],
		'top': [width // 2, 0],
		'topRight': [width, 0],
		'left': [0, height // 2],
		'right': [0, height],
		'bottomLeft': [0, height],
		'bottom': [width // 2, height],
		'bottomRight': [width, height]
	}
	try:
		return locations[position]
	except:
		raise ValueError("Argument 'position'  was not a key in the locations dict.")


def arg_error_str(arg_name, given, expected, kw=True):
	if kw:
		err_string = "The keyword argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
	else:
		err_string = "The argument, '{0}', was expected to be of type '{1}' but '{2}' was given."
	return err_string.format(arg_name, type(given), type(expected))


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


def log(msg, priority):
	"""Log an event
	:param msg: - a string to log
	:param priority: - 	an integer from 1-10 specifying how important the event is,
						1 being most critical and 10 being routine. If set to 0 it
						will always be printed, regardless of what the user sets
						verbosity to. You probably shouldn't do that.
	"""
	if priority <= Params.verbosity:
		with open(Params.log_file_path, 'a') as log_file:
			log_file.write(str(priority) + ": " + msg)
	return True


def peak(v1, v2):
	if v1 > v2:
		return v1
	else:
		return v2

def pump():  # a silly wrapper because Jon always forgets the sdl2 call
			return sdl2.SDL_PumpEvents()


def pretty_join(array, whitespace=1, delimiter="'", delimit_behavior=None, prepend=None, before_last=None, each_n=None,
				after_first=None, append=None):
	"""Automates string combination. Parameters:
	:param array: - a list of strings to be joined
	:param config: - a dict with any of the following keys:
		'prepend':
		'afterFirst':
		'beforeLast':
		'eachN':
		'whitespace':	Whitespace to place between elements. Should be a positive integer, but can be a string if the number
						is smaller than three and greater than zero. May also be the string None or False, but you should probably
						just not set it if that's what you want.
		'append':
		'delimiter':
		'delimitBehavior':
		'delimitBehaviour':
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
	return int(length / Params.ppd)    # todo: error checking?


def rgb_to_rgba(rgb):
	return rgb[0], rgb[1], rgb[2], 1  # todo: error checking?


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


def quit(msg=None):
	if msg:
		print msg
	print "Exiting..."
	sdl2.SDL_Quit()
	sys.exit()