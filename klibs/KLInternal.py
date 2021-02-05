# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import re
import sys
import time
import traceback
from datetime import datetime
from contextlib import contextmanager

from klibs.KLConstants import DATETIME_STAMP
from klibs import P

"""A module containing functions primarily intended for internal use by KLibs.

In addition to keeping things organized, the purpose of this module is to keep simple
utility functions separate from others that require any slow or external imports (e.g.
pkg_resources, sdl2). This is so that CLI operations like ``klibs --help`` or ``klibs export``
will be quick to load and won't break if there's an issue with an external dependency.
"""

# NOTE: Should pretty_list and/or make_hash go here as well?



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


def iterable(obj, exclude_strings=True):
	"""Determines whether a variable is iterable (i.e. whether it can be iterated over in a
	'for' loop, such as a :obj:`List` or :obj:`Tuple`).

	Args:
		obj: The object to check the iterability of.
		exclude_strings (bool, optional): If True, this function will return False for strings,
			which are otherwise considered iterable in Python. Defualts to True.

	Returns:
		True if the given object is iterable (and not a string, if exclude_strings is True),
		otherwise False.

	"""
	if exclude_strings:
		return hasattr(obj, '__iter__') and not isinstance(obj, str)
	else:
		try:
			iter(obj)
			return True
		except AttributeError:
			return False


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


def load_source(filepath):
	"""Loads a ``.py`` Python source file and retrieves its attributes, returning
	them in a dictionary.

	Args:
		filepath (str): Path of the Python source file to load.

	Returns:
		dict: the names and values of the attributes of the provided source file.

	"""
	# Load Python file as a module
	mod_name = os.path.basename(filepath).strip(".py")
	if sys.version_info.major == 3:
		from importlib.util import spec_from_file_location, module_from_spec
		spec = spec_from_file_location(mod_name, filepath)
		src = module_from_spec(spec)
		spec.loader.exec_module(src)
	else:
		import imp
		src = imp.load_source(mod_name, filepath)

	# Filter out modules and internal Python stuff from imported attributes
	attributes = {}
	for key, val in vars(src).items():
		if not (key.startswith('_') or type(val).__name__ == "module"):
			attributes[key] = val

	return attributes


def package_available(name):
	"""Python 2/3 agnostic function for determining if a given package is installed.

	Args:
		name (str): Name of the Python package to search for.

	Returns:
		bool: True if the package is available, otherwise False.

	"""
	if sys.version_info.major == 3:
		from importlib.util import find_spec
	else:
		from imp import find_module as find_spec
	try:
		return find_spec(name) != None
	except (ValueError, ImportError):
		return False


def boolean_to_logical(value, convert_integers=False):
	# NOTE: Depricated, should remove once scrubbed from MixedMotionCueing
	if convert_integers and value in [0, 1, '0', '1']:
		value = bool(int(value))
	logical = utf8(value).upper()
	if logical not in ['TRUE', 'FALSE']:
		return None
	return str(logical)


def colored_stdout(string, print_string=True):
	"""Generates and optionally prints colour text to the terminal, with colours and other styles
	being specified using HTML-style open/close tags (e.g. "<red>hello</red>").

	The following styles and colours are currently supported:

	================== ====================== ======================
	Style / Colour     Style Code             ANSI Code
	================== ====================== ======================
	Red                ``red``                ``\033[91m``
	------------------ ---------------------- ----------------------
	Green              ``green``              ``\033[92m``
	------------------ ---------------------- ----------------------
	Blue               ``blue``               ``\033[94m``
	------------------ ---------------------- ----------------------
	Purple             ``purple``             ``\033[95m``
	------------------ ---------------------- ----------------------
	Cyan               ``cyan``               ``\033[96m``
	------------------ ---------------------- ----------------------
	Dark Red           ``red_d``              ``\033[31m``
	------------------ ---------------------- ----------------------
	Dark Green         ``green_d``            ``\033[32m``
	------------------ ---------------------- ----------------------
	Dark Blue          ``blue_d``             ``\033[34m``
	------------------ ---------------------- ----------------------
	Dark Purple        ``purple_d``           ``\033[35m``
	------------------ ---------------------- ----------------------
	Dark Cyan          ``cyan_d``             ``\033[36m``
	------------------ ---------------------- ----------------------
	Bold               ``bold``               ``\033[1m``
	================== ====================== ======================

	Args:
		string (str): A string to style with ANSI colour codes.
		print_string (bool, optional): If True, the string will be printed immediately after
			being formatted. Defaults to True.

	Return:
		str: The formatted output string.

	"""
	code_pattern = r"(</?[a-z_]+>)"
	codes = {
		"purple": '\033[95m',
		"purple_d": '\033[35m',
		"blue": '\033[94m',
		"blue_d": '\033[34m',
		"green": '\033[92m',
		"green_d": '\033[32m',
		"red": '\033[91m',
		"red_d": '\033[31m',
		"cyan": '\033[96m',
		"cyan_d": '\033[36m',
		"bold": '\033[1m'
	}

	out = ""
	stack = []
	for s in re.split(code_pattern, string):
		if re.match(code_pattern, s) and P.color_output:
			code = re.findall(r"</?([a-z_]+)>", s)[0]
			if not code in codes.keys():
				continue
			if s[:2] == "</":
				if code == "bold" and "bold" in stack:
					stack.remove("bold")
					out += "\033[0m"
				if len(stack) and stack[-1] == code:
					stack.pop()
				out += codes[stack[-1]] if len(stack) else "\033[0m"
			else:
				stack.append(code)
				out += codes[code]   
		else:
			out += s

	if P.color_output:
		out += "\033[0m"  # Ensure text style reset to normal at end
	
	if print_string:
		print(out)

	return out


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


@contextmanager
def hide_stderr(macos_only=False):
	"""Temporarily suppresses stderr output. Useful for hiding useless noise from
	C libraries that can't be hidden through the usual Python ways.

	Args:
		macos_only (bool, optional): If True, stderr will only be suppressed on macOS.
			Defaults to False.

	"""
	# NOTE: Check if this works on Windows
	if macos_only == False or sys.platform == "darwin":
		devnull = os.open(os.devnull, os.O_WRONLY)
		old_stderr = os.dup(2)
		os.dup2(devnull, 2)
		yield
		os.dup2(old_stderr, 2)
		os.close(devnull)
		os.close(old_stderr)
	else:
		yield


def full_trace():
	exc_type, exc_val, exc_traceback = sys.exc_info()
	exception_list = traceback.format_stack()
	exception_list = exception_list[:-2]
	exception_list.extend(traceback.format_tb(exc_traceback))
	exception_list.extend(traceback.format_exception_only(exc_type, exc_val))

	exception_str = "Traceback (most recent call last):\n"
	exception_str += "".join(exception_list)
	# Removing the last \n
	return exception_str[:-1]
	

def now(format_time=False, format_template=DATETIME_STAMP):
	t = time.time()
	return datetime.fromtimestamp(t).strftime(format_template) if format_time else t
