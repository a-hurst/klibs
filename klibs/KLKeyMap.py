__author__ = 'jono'


class KeyMap(object):
	def __init__(self, name, ui_labels, data_labels, sdl_keysyms):
		self.__any_key = None
		self.map = [[], [], []]  # ui_labels, data_labels, sdl_keysyms
		if type(name) is str:
			self.name = name
		else:
			raise TypeError("Argument 'name' must be a string.")

		self.__register(ui_labels, data_labels, sdl_keysyms)

	def __str__(self):
		map_string = ""
		for list in self.map:
			map_string += "["
			for key in list:
				map_string += str(key)
			map_string += "],"
		return map_string[0:len(map_string) - 1]  # drop trailing comma

	def __register(self, ui_labels, data_labels, sdl_keysyms, ):
		length = len(ui_labels)
		self.any_key = not length

		if any(len(key_arg) != length for key_arg in [ui_labels, sdl_keysyms, data_labels]):
			raise TypeError("Arguments 'ui_labels', 'sdl_keysyms' and 'data_labels' must  the same number of elements.")

		try:
			for key_arg in [ui_labels, sdl_keysyms, data_labels]:
				iterable = iter(key_arg)
		except TypeError:
			raise TypeError("Arguments 'ui_labels', 'sdl_keysyms' and 'data_labels' must be iterable.")

		if all(type(name) is str for name in ui_labels):
			self.map[0] = ui_labels
		else:
			raise TypeError("All elements of 'ui_labels' argument of a KeyMap object must be of type 'str'.")

		if all(type(i) in (int, str) for i in data_labels):
			self.map[1] = data_labels
		else:
			raise TypeError("All elements of 'data_labels' must be of type 'int' or 'str'.")

		if all(type(sdl_keysym) in (int, str) for sdl_keysym in sdl_keysyms):
			self.map[2] = sdl_keysyms
		else:
			raise TypeError("All elements of 'sdl_keysyms' argument must be of an SDL2_KeyCode Value.")

	def validate(self, sdl_keysym):
		if type(sdl_keysym) is int:
			if sdl_keysym in self.map[2]:
				return True
			elif self.any_key:
				return True
			else:
				return False
		else:
			raise TypeError(self.arg_error_str("sdl_keysym", type(sdl_keysym), "int", False))

	def read(self, sdl_keysym, format="ui"):
		if self.any_key:
			return True

		if format == "ui":
			format = 0
		elif format == "data":
			format = 1
		else:
			raise ValueError("Argument 'format' must be either 'ui' or 'data.")

		if type(sdl_keysym) is int:
			if sdl_keysym in self.map[2]:
				return self.map[format][self.map[2].index(sdl_keysym)]
			else:
				raise ValueError("The requested sdl_keysym was not found in the KeyMap '{0}'".format(self.name))
		else:
			raise TypeError("Argument 'sdl_keysym' must be an integer corresponding to an SDL_KeySym value")

	def valid_keys(self):
		if len(self.map[0]) > 0:
			return ", ".join(self.map[0])
		elif self.any_key:
			return "ANY_KEY_ACCEPTED"
		else:
			return None

	@property
	def any_key(self):
		return self.__any_key

	@any_key.setter
	def any_key(self, value):
		if type(value) is bool:
			self.__any_key = value
		else:
			raise TypeError("KeyMap.any_key must be a boolean value.")