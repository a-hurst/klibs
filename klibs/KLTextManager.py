__author__ = 'jono'
import os, math, numpy
from KLNumpySurface import NumpySurface
from PIL import ImageFont
from KLUtilities import *

from KLConstants import *
import KLParams as Params


class TextManager(object):
	asset_path = "ExpAssets"
	alert_color = (255, 0, 0, 255)
	fonts_directory_path = "/Library/Fonts"
	fonts = {}
	font_sizes = {}
	labels = {}
	monitor_x = None
	monitor_y = None
	queue = {}
	strings = {}
	window_x = None
	window_y = None
	__antialias = True
	__default_color = (0, 0, 0, 255)
	__default_input_color = (3, 118, 163, 255)
	__default_bg_color = (255, 255, 255)
	__default_font_size = None
	__default_font = None
	__print_locations = {'query': None, 'response': None, 'timeout':None }
	__default_strings = {'query': None, 'response': None, 'timeout':None }
	__default_message_duration = 1


	def __init__(self, window_dimensions, monitor_dimensions, dpi, default_font=None, default_font_size="18pt",
					asset_path=None, fonts_directory_path=None, default_query_string=None, default_response_string=None,
					default_locations=None):

		self.window_x = window_dimensions[0]
		self.window_y = window_dimensions[1]
		self.monitor_x = monitor_dimensions[0]
		self.monitor_y = monitor_dimensions[1]

		if default_response_string:
			self.default_response_string = default_response_string
		if default_query_string:
			self.default_query_string = default_query_string
		self.default_timeout_string = "Too slow!"
		self.default_timeout_location = "center"

		if type(default_locations) is list and len(default_locations) == 2:  # query & response exist by default
			self.default_query_location = default_locations[0]
			self.default_response_location = default_locations[1]
		elif type(default_locations) is dict:  # can assert an arbitrarily long number of default locations
			query_location_present = False
			response_location_present = False
			for loc in default_locations:
				if loc == "query":
					query_location_present = True
				if loc == "response":
					response_location_present = True
				if type(default_locations[loc]) is not tuple:
					raise TypeError("Values of default_locations dict keys must be coordinate tuples (ie. x,y).")
			if not query_location_present and response_location_present:
				raise ValueError("default_locations dictionary must contain, minimally, the keys 'query' and 'response'")
			self.__print_locations = default_locations

		if type(asset_path) is str and os.path.exists(asset_path):
			self.asset_path = asset_path

		if type(fonts_directory_path) is str and os.path.exists(fonts_directory_path):
			self.fonts_directory_path = fonts_directory_path

		if type(self.window_x) is int and type(dpi) is int:
			self.__build_font_sizes(dpi)
			self.default_font_size = '18pt'
		else:
			raise ValueError("dpi must be an integer")

		# set a default font, using Trebuchet if not passed; Helvetica is a font suitcase in OS X, and because fuck arial
		if type(default_font) is list:
			if len(default_font) == 2:
				default_font_name, default_font_extension = default_font
				default_font_filename = default_font_name
			elif len(default_font) == 3:
				default_font_name, default_font_filename, default_font_extension = default_font
			else:
				raise ValueError("Argument 'default_font' should be a list of length 2 or 3.")
		else:
			default_font_name, default_font_filename, default_font_extension = ["Arial", "Arial", "ttf"]

		if self.add_font(default_font_name, default_font_extension, default_font_filename):
			self.default_font = default_font_name

	def __build_font_sizes(self, dpi):
		size_list = range(3, 96)
		self.font_sizes = {}
		for num in size_list:
			key = str(num) + 'pt'
			self.font_sizes[key] = int(math.floor(1.0 / 72 * dpi * num))

	def __compile_font(self, font_name=None, font_size=None):
		# process font_size argument or assign a default
		if font_size is not None:
			if type(font_size) is str:
				font_size = self.font_sizes[font_size]
			if type(font_size) is not int:
				raise TypeError("font_size must be either a point-string (ie. 18pt) or an int describing pixel height.")
		elif self.__default_font_size:
			font_size = self.__default_font_size
		else:
			raise ValueError("font_size argument is  required or else  default_font_size must be set prior to calling.")
		if not font_name:
			font_name = self.default_font
		print self.fonts
		return ImageFont.truetype(self.fonts[font_name], font_size)

	def size(self, text):  # TODO: What is this function for?
		rendering_font = ImageFont.truetype(self.default_font, self.__default_font_size)
		return rendering_font.size()

	def wrapped_text(self, text, width=None, font=None, font_size=None, color=None, bg_color=None):
		lines = text.split("\n")
		if (width):
			pass  # test various lengths until you get a size that works, then re-populate lines
		lines_surfs = [self.render_text(line, font, font_size, color, bg_color) for line in lines ]
		text_dims = [0,0]
		print text_dims
		for line in lines_surfs:
			text_dims[0] += line.width
			text_dims[1] += line.height
		y_pos = 0
		text_surface = NumpySurface(width=text_dims[0], height=text_dims[1])
		for line in lines_surfs:
			text_surface.blit(line, position=[0, y_pos])
			y_pos += line.height

		print lines_surfs
		print text_dims


	def render_text(self, string, font=None, font_size=None, color=None, bg_color=None):
		strings  = string.split("\n")
		if len(strings) > 1:
			print strings
			return self.wrapped_text(string, None, font, font_size, color, bg_color)
		if not color:
			color = self.default_color
		if not font:
			font = self.default_font
		if len(color) == 3:
			color = rgb_to_rgba(color)
		if bg_color and len(bg_color) == 3:
			bg_color = rgb_to_rgba(bg_color)
		else:
			bg_color = (0, 0, 0, 0)
		rendering_font = self.__compile_font(font_name=font, font_size=font_size, )
		print "String immediately before render: {0}".format(string)
		print rendering_font
		glyph_bitmap = rendering_font.getmask(string, mode="L")  # L = antialiasing mode
		bitmap_as_1d_array = numpy.asarray(glyph_bitmap)
		bitmap_as_2d_array = numpy.reshape(bitmap_as_1d_array, (glyph_bitmap.size[1], glyph_bitmap.size[0]), order='C')
		rendered_text = numpy.zeros((glyph_bitmap.size[1], glyph_bitmap.size[0], 4))
		rendered_text[:, :, 0][bitmap_as_2d_array > 0] = color[0] * bitmap_as_2d_array[bitmap_as_2d_array > 0] //  255
		rendered_text[:, :, 1][bitmap_as_2d_array > 0] = color[1] * bitmap_as_2d_array[bitmap_as_2d_array > 0] //  255
		rendered_text[:, :, 2][bitmap_as_2d_array > 0] = color[2] * bitmap_as_2d_array[bitmap_as_2d_array > 0] //  255
		rendered_text[:, :, 3][bitmap_as_2d_array > 0] = color[3] * bitmap_as_2d_array[bitmap_as_2d_array > 0] // 255
		rendered_text[:, :, 0][bitmap_as_2d_array == 0] = bg_color[0]
		rendered_text[:, :, 1][bitmap_as_2d_array == 0] = bg_color[1]
		rendered_text[:, :, 2][bitmap_as_2d_array == 0] = bg_color[2]
		rendered_text[:, :, 3][bitmap_as_2d_array == 0] = bg_color[3]
		return NumpySurface(rendered_text.astype(numpy.uint8))

	def add_font(self, font_name, font_extension="ttf", font_file_name=None):
		"""

		:param font_name: Name of font; should mirror file name without extension. If not, also use font_file_name argument.
		:param font_extension: File extension of the font's file, usually, 'ttf' or 'otf'.
		:param font_file_name: Use to simply 'font name' when file name is large, ie. "Arial Black CN.ttf" => "Arial"
		:return:
		"""
		if type(font_name) is str and type(font_extension) is str:
			if type(font_file_name) is not str:
				font_file_name = ".".join([font_name, font_extension])
			else:
				font_file_name = ".".join([font_file_name, font_extension])
			sys_path = os.path.join(self.fonts_directory_path, font_file_name)
			app_path = os.path.join(self.asset_path, font_file_name)
			if os.path.isfile(sys_path):
				self.fonts[font_name] = sys_path
			elif os.path.isfile(app_path):
				self.fonts[font_name] = app_path
			else:
				e_str = "Font file '{0}' was not found in either system fonts or experiment assets directories"
				raise ImportError(e_str.format(font_file_name))
		else:
			raise TypeError("Arguments 'font' and 'font_extension' must both be strings.")
		return True

	def fetch_print_location(self, location):
		"""

		:param location: String name of stored location (defaults are 'query' and 'response'
		:return: Returns either a tuple of x, y coordinates (if location is found) or False
		"""
		if type(location) is not str:
			raise TypeError("Argument 'location' must be a string.")
		if location in self.__print_locations:
			return self.__print_locations[location]
		else:
			return False

	def fetch_string(self, string_name):
		if type(string_name) is not str:
			raise TypeError("Argument 'string_name' must be a string.")
		if string_name in self.__default_strings:
			return self.__default_strings[string_name]
		else:
			return False

	# def wrapped_text(self, text, delimiter=None, font_size=None, font=None, wrap_width=None):
	# 	render_font_name = None
	# 	render_font_size = None
	# 	if font is not None:
	# 		render_font_name = font
	# 	if font_size is not None:
	# 		render_font_size = font_size
	# 	if delimiter is None:
	# 		delimiter = "\n"
	# 	try:
	# 		if wrap_width is not None:
	# 			if type(wrap_width) not in [int, float]:
	# 				e_str = "The config option 'wrapWidth' must be an int or a float; '{0}' was passed. \
	# 						Defaulting to 80% of app width."
	# 				raise ValueError(e_str.format(repr(wrap_width)))
	# 			elif 1 > wrap_width > 0:  # assume it's a percentage of app width.
	# 				wrap_width = int(wrap_width * self.appx)
	# 			elif wrap_width > self.appx or wrap_width < 0:
	# 				e_str = "A wrapWidth of '{0}' was passed which is either too big to fit inside the app or else is\
	# 						negative (and must be positive). Defaulting to 80% of app width."
	# 				raise ValueError(e_str)
	# 			#having passed these tests, wrapWidth must now be correct
	# 		else:
	# 			wrap_width = int(0.8 * self.appx)
	# 	except ValueError as e:
	# 		print self.warn(e.message, {'class': self.__class__.__name__, 'method': 'wrapText'})
	# 		wrap_width = int(0.8 * self.appx)
	# 	render_font = self.__compile_font(render_font_name, render_font_size)
	# 	paragraphs = text.split(delimiter)
	#
	# 	render_lines = []
	# 	line_height = 0
	# 	# this loop was written by Mike Lawrence (mike.lwrnc@gmail.com) and then (slightly) modified for this program
	# 	for p in paragraphs:
	# 		word_list = p.split(' ')
	# 		if len(word_list) == 1:
	# 			render_lines.append(word_list[0])
	# 			if p != paragraphs[len(paragraphs) - 1]:
	# 				render_lines.append(' ')
	# 				line_height += render_font.get_linesize()
	# 		else:
	# 			processed_words = 0
	# 			while processed_words < (len(word_list) - 1):
	# 				current_line_start = processed_words
	# 				current_line_width = 0
	#
	# 				while (processed_words < (len(word_list) - 1)) and (current_line_width <= wrap_width):
	# 					processed_words += 1
	# 					current_line_width = render_font.size(' '.join(word_list[current_line_start:(processed_words + 1)]))[0]
	# 				if processed_words < (len(word_list) - 1):
	# 					#last word went over, paragraph continues
	# 					render_lines.append(' '.join(word_list[current_line_start:(processed_words - 1)]))
	# 					line_height = line_height + render_font.get_linesize()
	# 					processed_words -= 1
	# 				else:
	# 					if current_line_width <= wrap_width:
	# 						#short final line
	# 						render_lines.append(' '.join(word_list[current_line_start:(processed_words + 1)]))
	# 						line_height = line_height + render_font.get_linesize()
	# 					else:
	# 						#full line then 1 word final line
	# 						render_lines.append(' '.join(word_list[current_line_start:processed_words]))
	# 						line_height = line_height + render_font.get_linesize()
	# 						render_lines.append(word_list[processed_words])
	# 						line_height = line_height + render_font.get_linesize()
	# 					#at end of paragraph, check whether a inter-paragraph space should be added
	# 					if p != paragraphs[len(paragraphs) - 1]:
	# 						render_lines.append(' ')
	# 						line_height = line_height + render_font.get_linesize()
	# 	return render_lines

	@property
	def antialias(self):
		return self.__antialias

	@antialias.setter
	# @canonical
	def antialias(self, state):
		"""

		:param state:
		"""
		if type(state) is bool:
			self.__antialias = state
		else:
			raise TypeError("Argument 'state' must be boolean.")

	@property
	def default_query_location(self):
		return self.__print_locations['query']

	@default_query_location.setter
	def default_query_location(self, query_location):
		"""
		Set the default screen locations for prompts and responses
		"""
		try:
			query_iter = iter(query_location)
			self.__print_locations['query'] = query_location
		except:
			raise TypeError("query_location must be an iterable object containing a pair of x,y integers .")

	@property
	def default_response_location(self):
		return self.__print_locations['response']

	@default_response_location.setter
	def default_response_location(self, response_location):
		"""
		Set the default screen locations for prompts and responses
		"""
		try:
			response_iter = iter(response_location)
			self.__print_locations['response'] = response_location
		except:
			raise TypeError("response_location must be an iterable object containing a pair of x,y integers .")


	@property
	def default_timeout_location(self):
		return self.__print_locations['timeout']

	@default_timeout_location.setter
	def default_timeout_location(self, timeout_location):
		"""
		Set the default screen locations for prompts and responses
		"""
		try:
			timeout_iter = iter(timeout_location)
			self.__print_locations['timeout'] = timeout_location
		except:
			raise TypeError("timeout_location must be an iterable object containing a pair of x,y integers .")


	@property
	def default_query_string(self):
		return self.__default_strings['query']

	@default_query_string.setter
	def default_query_string(self, query_string):
		if type(query_string) is str:
			self.__default_strings['query'] = query_string
		else:
			raise TypeError("'query_string' must be a string.")

	@property
	def default_response_string(self):
		return self.__default_strings['response']

	@default_response_string.setter
	def default_response_string(self, response_string):
		if type(response_string) is str:
			self.__default_strings['response'] = response_string
		else:
			raise TypeError("'response_string' must be a string.")

	@property
	def default_timeout_string(self):
		return self.__default_strings['timeout']

	@default_timeout_string.setter
	def default_timeout_string(self, timeout_string):
		if type(timeout_string) is str:
			self.__default_strings['timeout'] = timeout_string
		else:
			raise TypeError("'timeout_string' must be a string.")

	@property
	def default_color(self):
		"""

		:return:
		"""
		return self.__default_color

	@default_color.setter
	def default_color(self, color):
		"""

		:param color:
		"""
		if type(color) is list:
			self.__default_color = color

	@property
	def default_input_color(self):
		"""

		:return:
		"""
		return self.__default_color

	@default_input_color.setter
	def default_input_color(self, color):
		"""

		:param color:
		"""
		if type(color) in (list, tuple):
			self.__default_input_color = color

	@property
	def default_bg_color(self):
		"""

		:return:
		"""
		return self.__default_bg_color

	@default_bg_color.setter
	def default_bg_color(self, color):
		"""

		:param color:
		"""
		if type(color) is list:
			self.__default_bg_color = color

	@property
	def default_font_size(self):
		return self.__default_font_size

	@default_font_size.setter
	def default_font_size(self, size):
		"""

		:param size:
		"""
		if type(size) is str:
			self.__default_font_size = self.font_sizes[size]
		elif type(size) is int:
			size = str(size) + "pt"
			self.__default_font_size = self.font_sizes[size]

	@property
	def default_font(self):
		"""

		:return:
		"""
		return self.__default_font

	@default_font.setter
	def default_font(self, font):
		"""

		:param font:
		:raise:
		"""
		self.__default_font = font

	def add_query(self, label, string):
		if type(label) is str and type(string) is str:
			self.labels[label] = string