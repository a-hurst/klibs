# -*- coding: utf-8 -*-

__author__ = 'jono'

import math
import os
import ctypes
import time
import datetime
import re
import traceback

import multiprocessing as mp
from sys import exc_info
from sdl2 import SDL_Event, SDL_PeepEvents, SDL_PumpEvents, SDL_PushEvent, SDL_FlushEvents, SDL_RegisterEvents, SDL_GetError, \
	SDL_FIRSTEVENT, SDL_LASTEVENT, SDL_MOUSEMOTION, SDL_PEEKEVENT, SDL_DISABLE, SDL_ENABLE, KMOD_LSHIFT, KMOD_RSHIFT, KMOD_CAPS
from sdl2.ext import get_events
from sdl2.mouse import SDL_ShowCursor, SDL_GetMouseState, SDL_WarpMouseGlobal, SDL_ShowCursor
from sdl2.keyboard import SDL_GetKeyName, SDL_GetModState
from subprocess import Popen, PIPE

from math import sin, cos, radians, pi, atan2, degrees, ceil

from klibs.KLConstants import BL_RIGHT, BL_LEFT, BL_BOTTOM_RIGHT, BL_BOTTOM, BL_BOTTOM_LEFT, BL_TOP, \
	BL_CENTER, BL_TOP_LEFT, BL_TOP_RIGHT, PARTICIPANT_FILE, TBL_EVENTS, TBL_LOGS, TBL_PARTICIPANTS, TBL_TRIALS, TF_DATA,\
	EDF_EXT, EDF_FILE, DATETIME_STAMP, DATA_EXT, MOD_KEYS, DELIM_NOT_FIRST, DELIM_NOT_LAST, DELIM_WRAP, TK_S, TK_MS
from klibs import P
from klibs import env

def absolute_position(position, destination):
	height = None
	width = None
	try:  # ie. a numpy array
		height = destination.shape[0]
		width = destination.shape[1]
	except AttributeError:
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
			height = P.screen_y
			width = P.screen_x
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
	except IndexError:
		raise ValueError("Invalid position identifier.")


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
	if value in ["false", "False"] or value is False: return "FALSE"
	if value in ["true", "True"] or value is True: return "TRUE"
	if convert_integers is True:
		if value in [1,"1"]: return "TRUE"
		if value in [0,"0"]: return "FALSE"
	return None


def bounded_by(pos, left, right, top, bottom):
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
		(-1.0 * source_width / 2.0, -1.0 * source_height),
		(-1.0 * source_width, -1.0 * source_height),
		(0, -1.0 * source_height / 2.0),
		(-1.0 * source_width / 2.0, -1.0 * source_height / 2.0),
		(-1.0 * source_width, -1.0 * source_height / 2.0),
		(0, 0),
		(-1.0 * source_width / 2.0, 0),
		(-1.0 * source_width, 0))


def camel_to_snake(string):
	return re.sub('([a-z0-9])([A-Z])', r'\1_\2', re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)).lower()


def chunk(items, chunk_size):
	"""Yield successive chunk-sized chunks from items."""
	for i in range(0, len(items), chunk_size):
		yield items[i:i+chunk_size]


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
		print string
	else:
		return string


def deg_to_px(deg, even=False):
	# Some things don't draw as expected unless the px value given is even.
	# If even=True, deg_to_px will round up to nearest multiple of 2.
	if even:
		px = ceil((deg * P.ppd) / 2.0) * 2
	else:
		px = deg * P.ppd
	return int(px)  # todo: error checking?


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
	participant_id = P.participant_id if participant_id is None else participant_id
	file_name_str = "p{0}_{1}{2}"
	duplicate_file_name_str = "p{0}.{1}_{2}{3}"

	if date is None:
		date_query = "SELECT `created` FROM `participants` WHERE `id` = ?"
		date = env.db.query(date_query, q_vars=tuple([participant_id]))[0][0][:10]
	if file_type == PARTICIPANT_FILE:
		file_extension = TF_DATA
		if incomplete:
			file_path = P.incomplete_data_path
			file_name_str = "p{0}_{1}_incomplete.txt"
			duplicate_file_name_str = "p{0}.{1}_{2}_incomplete" + TF_DATA
		else:
			file_path = P.data_path
	if file_type == EDF_FILE:
		file_extension = EDF_EXT
		file_path = P.edf_dir
		project_name_abbrev = P.project_name[0:len(str(participant_id)) + 2]
		file_name = file_name_str.format(participant_id, project_name_abbrev, file_extension)
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


def flush():
	pump()
	SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT)
	return


def force_quit():
	Popen(['pkill', '-f', 'python'], stdout=PIPE, stderr=PIPE).communicate()


def full_trace():
	exception_list = traceback.format_stack()
	exception_list = exception_list[:-2]
	exception_list.extend(traceback.format_tb(exc_info()[2]))
	exception_list.extend(traceback.format_exception_only(exc_info()[0], exc_info()[1]))

	exception_str = "Traceback (most recent call last):\n"
	exception_str += "".join(exception_list)
	# Removing the last \n
	return exception_str[:-1]


def hide_mouse_cursor():
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
		return hasattr(obj, '__iter__')
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
	"""Log an event
	:param msg: The string to log
	:param priority: An integer from 1-10 specifying how important the event is, 1 being most critical and 10 being routine. If set to 0 it will always be printed, regardless of what the user sets verbosity to. You probably shouldn't do that.
	"""
	if priority <= P.verbosity:
		with open(P.log_file_path, 'a') as log_file:
			log_file.write(str(priority) + ": " + msg)
	return True


def midpoint(p1, p2):
	return int((p1[0]+p2[0])/2), int((p1[1]+p2[1])/2)


def mean(values, as_int=False):
	mean_val = sum(values) / len(values)
	return mean_val if not as_int else int(mean_val)


def mouse_pos(pump_event_queue=True, position=None):
	if pump_event_queue:
		SDL_PumpEvents()
	if not position:
		x, y = ctypes.c_int(0), ctypes.c_int(0)
		SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
		return [x.value, y.value]
	else:
		SDL_WarpMouseGlobal(*position)
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
	if v1 > v2:
		return v1
	else:
		return v2


def point_pos(origin, amplitude, angle, rotation=0, clockwise=False):
	try:
		origin = tuple(origin)
		angle += rotation
		theta_rad = radians((angle if clockwise else -angle) % 360)
		return (int(origin[0] + (amplitude * cos(theta_rad))), int(origin[1] + (amplitude * sin(theta_rad))))
	except Exception as e:
		print "point_pos() error"
		print origin, amplitude, angle, rotation, type(origin), type(amplitude), type(angle), type(rotation)
		raise


def pump(return_events=False):
	from klibs.KLEnvironment import evm
	# try:
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
	# 	pass  # for when called before evm initialized
	SDL_PumpEvents()

	# If we are using TryLink, check the SDL event queue after every pump and append any
	# mouse motion events to the TryLink event queue, where they can be used as a stand-in
	# for saccades.
	from klibs.KLEnvironment import el
	from klibs.KLEyeLink.KLTryLink import TryLink
	if isinstance(el, TryLink):
		while self.el.recording:
			evarray = (SDL_Event * 10)()
			ptr = ctypes.cast(evarray, ctypes.POINTER(SDL_Event))
			ret = SDL_PeepEvents(ptr, 10, SDL_PEEKEVENT, SDL_MOUSEMOTION, SDL_MOUSEMOTION)
			if ret <= 0:
				break
			el.mouse_event_queue += list(evarray)[:ret]
			if ret < 10:
				break

	if return_events:
		return get_events()


def pretty_join(array, whitespace=1, delimiter="'", delimit_behaviors=None, wrap_each=None, prepend=None, before_last=None, each_n=None, after_first=None, append=None):
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
					log(log_str.format(each_n, type(each_n, 10)))
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
			pass
		else:
			output += delimiter + whitespace

		# if after_first is set, print it and add whitespace
		if (n == 0) and (after_first is not None):
			output += after_first + whitespace
	if append is not None:
		output += append

	return output


def pt_to_px(pt_size):
	if type(pt_size) is not int:
		raise TypeError("Argument 'pt_size' must be an integer.")
	if 512 < pt_size < 2:
		raise ValueError("Argument 'pt_size' must be between 2 and 512.")
	# dpi = 96  # CRT default

	return int(math.floor(1.0 / 72 * P.ppi * pt_size))


def px_to_deg(length):  # length = px
	return int(length / P.ppd)


def show_mouse_cursor():
	SDL_ShowCursor(SDL_ENABLE)
	return pump()


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


def sdl_key_code_to_str(sdl_keysym):
	key_name = SDL_GetKeyName(sdl_keysym).replace("Keypad ", "")
	if key_name in MOD_KEYS:  # TODO: probably use sdl keysyms as keys instead of key_names
		return False
	if key_name == "Space":
		return " "
	if SDL_GetModState() not in (KMOD_LSHIFT, KMOD_RSHIFT, KMOD_CAPS):
		key_name = key_name.lower()
	return key_name if len(key_name) == 1 else False  # to cover all keys that aren't alphanumeric or handled here


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


def threaded(func):
	def threaded_func(*args, **kwargs):
		p = mp.Process(target=func, args=args, kwargs=kwargs)
		p.start()
		return p
	return threaded_func


def type_str(var):
	return type(var).__name__


def unicode_to_str(content):
		"""

		:param content:
		:return:
		"""
		import unicodedata

		if type(content) is unicode:
			# convert string to ascii
			converted = unicodedata.normalize('NFKD', content).encode('ascii','ignore')

			# convert JS booleans to Python booleans
			if converted in ("true", "false"):
				converted = converted == "true"

		# elif type(content) in (list, dict):
		elif iterable(content):
			#  manage dicts first
			try:
				converted = {}  # converted output for this level of the data
				for k in content:
					v = content[k]  # ensure the keys are ascii strings
					if type(k) is unicode:
						k = unicode_to_str(k)
					if type(v) is unicode:
						converted[k] = unicode_to_str(v)
					elif iterable(v):
						converted[k] = unicode_to_str(v)
					else:
						converted[k] = v

			except (TypeError, IndexError):
				converted = []
				for i in content:
					if type(i) is unicode:
						converted.append(unicode_to_str(i))
					elif iterable(i):
						converted.append(unicode_to_str(i))
					else:
						converted.append(i)

		else:
			# assume it's numeric
			return content
		return converted


def smart_sleep(interval, units=TK_MS):
	from klibs.KLUserInterface import ui_request
	from time import time
	if units == TK_MS:
		interval *= .001
	start = time()
	while time() - start < interval:
		ui_request()


def acute_angle(vertex, p1, p2):
	v_p1 = line_segment_len(vertex, p1)
	v_p2 = line_segment_len(vertex, p2)
	p1_p2 = line_segment_len(p1, p2)
	return degrees(acos((v_p1**2 + v_p2**2 - p1_p2**2) / (2 * v_p1 * v_p2)))
