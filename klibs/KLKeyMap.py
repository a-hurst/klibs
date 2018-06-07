__author__ = 'jono'

"""This module provides an object type for mapping different SDL Keycodes to human-readable names.
At one point in time, it was used for creating global keymaps that mapped different letters/symbols
to their corresponding keycodes across the KLibs experiment runtime, but currently it is only used
for specifying accepted keys and their corresponding data output labels for the
:class:`KeyPressResponse` response listener in :class:`ResponseCollector` objects.

Because keypress response maps can now be specified using a simple dict, the KeyMap class is only
really required for legacy code and for validating dict key maps internally.

"""


class KeyMap(object):
	"""An object that maps SDL Keycodes to human-readable names for UI input and data output.
	Primarily for use with the :class:`KeyPressResponse` response listener in a
	:class:`ResponseCollector` object. The 'ui_labels', 'data_labels', and 'keycodes' arguments
	must all be iterables of identical length.

	For example,::

		k = KeyMap('response', ['z', '/'], ['left', 'right'], [sdl2.SDLK_z, sdl2.SDLK_SLASH])
	
	would create a keymap with the 'SDLK_z' keycode mapped to the UI label 'z' and the data label
	'left', and the 'SDLK_SLASH' keycode mapped to the UI label '/' and the data label 'right'.

	Args:
		name (str): The name of the KeyMap object. Not currently used for anything.
		ui_labels (:obj:`List`): A list of strings corresponding to the list of keycodes provided
			in the 'keycodes' argument. Not currently used for anything.
		data_labels (:obj:`List`): A list of strings corresponding to the list of keycodes provided
			in the 'keycodes' argument. Specifies the output strings to use for different keycodes
			by :class:`ResponseCollector` objects.
		keycodes (:obj:`List`): A list of SDL Keycodes to map to the labels provided by 'ui_labels'
			and 'data_labels'. A complete list of valid keycodes can be found in the following
			table: https://wiki.libsdl.org/SDL_Keycode
		
	Attributes:
		name (str): The name of the KeyMap object. Not currently used for anything.
	
	Raises:
		ValueError: If there are any duplicate labels or keycodes in the lists provided.
		TypeError: If the lengths of 'ui_labels', 'data_labels', and 'keycodes' mismatch.
		TypeError: If any of the elements of 'ui_labels', 'data_labels', and 'keycodes' are of	
			the wrong data type.

	"""

	def __init__(self, name, ui_labels, data_labels, keycodes):

		if type(name) is not str:
			raise TypeError("KeyMap name must be a string.")

		self._ui_label_map = {}
		self._data_label_map = {}
		self.name = name
		self.__register(ui_labels, data_labels, keycodes)


	def __register(self, ui_labels, data_labels, keycodes):
		"""Validates and registers keycodes with their corresponding UI and data labels within
		the keymap. For internal use only: once a KeyMap has been created, it cannot be extended
		or modified.

		"""
		length = len(ui_labels)
		for l in [ui_labels, data_labels, keycodes]:
			if len(l) != length:
				raise TypeError("All list arguments must contain the same number of elements.")
			if len(set(l)) != length:
				raise ValueError("Label and keycode lists cannot contain duplicate items.")
			if isinstance(l, str) or not hasattr(l, '__iter__'):
				raise TypeError("'ui_labels', 'data_labels', and 'keycodes' must be iterable.")

		if not all(type(code) is int for code in keycodes):
			raise TypeError("All elements of 'keycodes' must be valid SDL2 Keycodes.")
		if not all(type(label) is str for label in ui_labels):
			raise TypeError("All elements of 'ui_labels' must be strings.")
		if not all(type(label) in (int, str) for label in data_labels):
			raise TypeError("All elements of 'data_labels' must be integers or strings.")
		
		for i in range(0, length):
			self._ui_label_map[keycodes[i]] = ui_labels[i]
			self._data_label_map[keycodes[i]] = data_labels[i]


	def validate(self, keycode):
		"""Checks if a keycode has a mapping within the KeyMap.

		Args:
			keycode (int): The SDL Keycode to check for the presence of within the KeyMap.
		
		Returns:
			bool: True if the keycode exists in the KeyMap, otherwise False.

		Raises:
			TypeError: If the keycode is not an int (i.e. not a valid keycode).

		"""
		if type(keycode) is not int:
			raise TypeError("SDL Keycodes must be of type 'int'.")

		return keycode in self._ui_label_map.keys()
			

	def read(self, keycode, label="ui"):
		"""Returns the label mapped to a given keycode.

		Args:
			keycode (int): The SDL Keycode to return the mapped label for.
			label (str, optional): The type of label (UI or data) to return. Must be one of
				'ui' or 'data'. Defaults to 'ui' if not specified.
		
		Returns:
			str: The label mapped to the given keycode.

		Raises:
			ValueError: If the keycode does not exist within the KeyMap.

		"""
		if label.lower() not in ["ui", "data"]:
			raise ValueError("'label' must be either 'ui' or 'data.")
		
		if self.validate(keycode):
			return self._ui_label_map[keycode] if label == "ui" else self._data_label_map[keycode]
		else:
			e = "The KeyMap '{0}' has no mapping for the keycode '{1}'"
			raise ValueError(e.format(self.name, keycode))
