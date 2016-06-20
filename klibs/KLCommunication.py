# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'


from copy import copy

from klibs.KLConstants import *
from klibs.KLGraphics import blit, clear, fill, flip
import klibs.KLParams as P
from klibs.KLUtilities import absolute_position, now, pretty_join, sdl_key_code_to_str, pump
# from klibs.KLUserInterface import ui_request
from klibs import text_manager as tm  # note: this is a global instance of TextManager, not the class itself; see __init__.py



def alert(text, blit=True, display_for=0):
		"""
		Convenience function wrapping
		:mod:`~klibs.KLExperiment`.\ :class:`~klibs.KLExperiment.Experiment`.\ :func:`~klibs.KLExperiment.Experiment
		.message`
		``Alert_string`` is formatted as 'warning' text (ie. red, large, screen center).

		:param text: Message to display as alert.
		:type text: String
		:param blit: Return surface or :func:`~klibs.KLExperiment.Experiment.blit` automatically
		:type blit: Bool
		:param display_for: Number of seconds to display the alert message for (overrides 'any key' dismissal).
		:type display_for: Int

		"""
		# todo: instead hard-fill, "separate screen" flag; copy current surface, blit over it, reblit surf or fresh
		# todo: address the absence of default colors



		clear()
		fill(P.default_fill_color)
		message(text, "alert", blit=True, flip=True)
		if display_for > 0:
			pass
			# todo: use ui_request and timekeeper

def message(text, style=None, location=None, registration=None, blit=True, flip=False, wrap_width=None):
		"""
		``heavy_modification_planned`` ``backwards_compatibility_planned``

		Generates and optionally renders formatted text to the display.

		.. warning:: While this method supports the arguments listed, only :class:`~klibs.KLTextManager.TextStyle`
		should now be used.


		:param text: Text to be displayed.
		:type text: String
		:param style: Name of :class:`~klibs.KLTextManager.TextStyle` to be used.
		:type style: String
		:param location: X-Y coordinates where the message should be placed. Default is screen center.
		:type location: Iterable of Integers or `Location Constant`
		:param registration: Location about message surface perimeter to be placed at supplied location. Default is
		center.
		:type registration: Integer
		:param wrap_width: Maximum width (px) of text line before breaking.
		:type wrap_width: Integer
		:param blit: Toggles whether message surface is automatically :func:`~klibs.KLExperiment.Experiment.blit` to
		the display buffer.
		:type blit: Boolean
		:param flip: Toggles whether :func:`~klibs.KLExperiment.Experiment.flip` is automatically called after blit.
		:type flip: Boolean
		:return: NumpySurface or Boolean
			"""
		if not style:
			style = tm.styles['default']
		else:
			try:
				style = tm.styles[style]
			except TypeError:
				pass
		# todo: padding should be implemented as a call to resize() on message surface; but you have to fix wrap first

		render_config = {}
		message_surface = None  # unless wrap is true, will remain empty

		# process blit registration
		if location == "center" and registration is None:  # an exception case for perfect centering
			registration = 5
		if registration is None:
			registration = 7

		# process location, infer if need be; failure here is considered fatal
		if not location:
			x_offset = (P.screen_x - P.screen_x) // 2 + style.font_size
			y_offset = (P.screen_y - P.screen_y) // 2 + style.font_size
			location = (x_offset, y_offset)
		else:
			try:
				iter(location)
			except AttributeError:
				try:
					location = absolute_position(location, P.screen_x_y)
				except ValueError:
					raise ValueError("Argument 'location' must be a location constant or iterable x,y coordinate pair")

		message_surface = tm.render(text, style)
		if not blit:
			return message_surface
		else:
			blit(message_surface, registration, location)
		if flip:
			flip()

def query():
	pass
#
# def query(query=None, password=False, font=None, font_size=None, color=None, locations=None, registration=5, return_type=None, accepted=None):
# 		"""
# 		``relocation_planned`` ``backwards_compatibility_planned``
#
# 		Convenience function for collecting participant input with real-time visual feedback.
#
# 		Presents a string (ie. a question or response instruction) to the participant. Then listens for keyboard input
# 		and displays the participant's response on screen in real time.
#
# 		Experiment.query() makes two separate calls to Experiment.message(), which allows for query text and response
# 		text to be formatted independently. All of the formatting arguments can optionally be length-2 lists of the
# 		usual parameters, where the first element would be applied to the query string and the second to the response.
# 		If normal formatting values are supplied, they are applied to both the query and response text.
#
# 		:param query: A string of text to present to the participant usually a question or instruction about desired input.
# 		:param password: When true participant input will appear on screen in asterisks, though real key presses are recorded.
# 		:param font: See Experiment.message()
# 		:param font_size: See Experiment.message()
# 		:param color: See Experiment.message()
# 		:param locations:
# 		:param registration:
# 		:param return_type:
# 		:param accepted:
# 		:return: boolean
# 		:raise TypeError:
#
#
# 		**Example**
#
#
# 		The following::
#
# 			question = "What is your name?"
# 			font = "Helvetica"
# 			sizes = [24,16]
# 			colors = [rgb(0,0,0), rgb(255,0,0)]
# 			query(question, font=font_name, font_size=sizes, color=colors)
#
#
# 		Produces this formatting structure:
#
# 			+----------+-------------+---------+-----------+
# 			|**string**|**font size**|**color**| **font**  |
# 			+----------+-------------+---------+-----------+
# 			| query    |     24pt    | black   | Helvetica |
# 			+----------+-------------+---------+-----------+
# 			| response |   16pt      | red     | Helvetica |
# 			+----------+-------------+---------+-----------+
#
# 		*Note: As with Experiment.message() <#message_def> this method will eventually accept a TextStyle object
# 		instead of the formatting arguments currently implemented.*
#
# 		"""
# 		# TODO: 'accepted' might be better as a KLKeyMap object? Or at least more robust than a list of letters?
#
# 		input_config = [None, None, None, None]  # font, font_size, color, bg_color
# 		query_config = [None, None, None, None]
# 		vertical_padding = None
# 		input_location = None
# 		query_location = None
# 		query_registration = 8
# 		input_registration = 2
#
# 		# build config argument(s) for __render_text()
# 		# process the possibility of different query/input font sizes
# 		if font_size is not None:
# 			if type(font_size) is (tuple or list):
# 				if len(font_size) == 2:
# 					input_config[1] = tm.font_sizes[font_size[0]]
# 					query_config[1] = tm.font_sizes[font_size[1]]
# 					vertical_padding = query_config[1]
# 					if input_config[1] < query_config[1]:  # smallest  size =  vertical padding from midline
# 						vertical_padding = input_config[1]
# 			else:
# 				input_config[1] = tm.font_sizes[font_size]
# 				query_config[1] = tm.font_sizes[font_size]
# 				vertical_padding = tm.font_sizes[font_size]
# 		else:
# 			input_config[1] = tm.default_font_size
# 			query_config[1] = tm.default_font_size
# 			vertical_padding = tm.default_font_size
#
# 		if registration is not None:
# 			if type(registration) is (tuple or list):
# 				input_registration = registration[0]
# 				query_registration = registration[1]
# 			else:
# 				input_registration = registration
# 				query_registration = registration
#
# 		# process the (unlikely) possibility of different query/input fonts
# 		if type(font) is tuple and len(font) == 2:
# 			input_config[0] = font[0]
# 			query_config[0] = font[1]
# 		elif type(font) is str:
# 			input_config[0] = font
# 			query_config[0] = font
# 		# else:
# 		# 	input_config[0] = tm.default_font
# 		# 	query_config[0] = tm.default_font
#
# 		# process the possibility of different query/input colors
# 		if color is not None:
# 			if len(color) == 2 and all(isinstance(col, tuple) for col in color):
# 				input_config[2] = color[0]
# 				query_config[2] = color[1]
# 			else:
# 				input_config[2] = color
# 				query_config[2] = color
# 		else:
# 			input_config[2] = P.default_response_color
# 			query_config[2] = P.default_input_color
#
# 		# process locations
# 		generate_locations = False
# 		if locations is not None:
# 			if None in (locations.get('query'), locations.get('input')):
# 				query_location = tm.fetch_print_location('query')
# 				input_location = tm.fetch_print_location('response')
# 			else:
# 				query_location = locations['query']
# 				input_location = locations['input']
# 		else:
# 			generate_locations = True
# 		# infer locations if not provided (ie. center y, pad x from screen midline) create/ render query_surface
# 		# Note: input_surface not declared until user input received, see while loop below
# 		query_surface = None
# 		# if query is None:
# 		# 	query = tm.fetch_string('query')
#
# 		if query:
# 			query_surface = tm.render_text(query, *query_config)
# 		else:
# 			raise ValueError("A default query string was not set and argument 'query' was not provided")
#
# 		query_baseline = (P.screen_y // 2) - vertical_padding
# 		input_baseline = (P.screen_y // 2) + vertical_padding
# 		horizontal_center = P.screen_x // 2
# 		if generate_locations:
# 			query_location = [horizontal_center, query_baseline]
# 			input_location = [horizontal_center, input_baseline]
#
# 		fill(P.default_fill_color)
# 		blit(query_surface, query_registration, query_location)
# 		flip()
#
# 		# todo: split this into query_draw() [above code] and query_listen() [remaining code]
# 		input_string = ''  # populated in loop below
# 		user_finished = False  # True when enter or return are pressed
# 		no_answer_string = 'Please provide an answer.'
# 		invalid_answer_string = None
# 		error_string = None
# 		if accepted:
# 			try:
# 				iter(accepted)
# 				accepted_str = pretty_join(accepted, delimiter=",", before_last='or', prepend='[ ', append=']')
# 				invalid_answer_string = 'Your answer must be one of the following: {0}'.format(accepted_str)
# 			except:
# 				raise TypeError("Argument 'accepted' must be iterable.")
# 		while not user_finished:
# 			sdl2.SDL_PumpEvents()
# 			for event in pump(True):
# 				if event.type not in [sdl2.SDL_KEYUP, sdl2.SDL_KEYDOWN]:
# 					continue
# 				ui_request(event.key.keysym)
# 				if event.type == sdl2.SDL_KEYUP:  # don't fetch letter on both events
# 					continue
# 				if error_string:
# 					error_string = None
# 					input_string = ''
# 				key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
# 				sdl_keysym = key.keysym.sym
#
# 				fill()
# 				blit(query_surface, query_registration, query_location)
#
# 				if sdl_keysym == sdl2.SDLK_BACKSPACE:  # ie. backspace
# 					input_string = input_string[:-1]
#
# 				if sdl_keysym in (sdl2.SDLK_KP_ENTER, sdl2.SDLK_RETURN):  # ie. if enter or return
# 					if len(input_string) or accepted == ALL:
# 						if accepted:   # to make the accepted list work, there's a lot of checking yet to do
# 							if input_string in accepted or accepted == ALL:
# 								user_finished = True
# 							else:
# 								error_string = invalid_answer_string
# 						else:
# 							user_finished = True
# 					else:
# 						error_string = no_answer_string
# 					if error_string:
# 						error_config = copy(input_config)
# 						error_config[2] = tm.alert_color
# 						input_surface = tm.render_text(error_string, *error_config)
# 						input_string = ""
# 				if sdl_keysym == sdl2.SDLK_ESCAPE:  # if escape, erase the string
# 					input_string = ""
# 					input_surface = None
#
# 				if sdl_key_code_to_str(sdl_keysym):
# 					input_string += sdl_key_code_to_str(sdl_keysym)
# 				render_str = len(input_string) * '*' if password else input_string
# 				if not error_string:  # if error_string, input_surface already created with different config.
# 					try:
# 						input_surface = tm.render_text(render_str, *input_config)
# 					except (IndexError, ValueError):
# 						input_surface = None
# 				if input_surface:
# 					blit(input_surface, input_registration, input_location)
# 				flip()
# 					# else:
# 					# 	pass  # until a key-up event occurs, could be a ui request (ie. quit, pause, calibrate)
# 		fill()
# 		flip()
# 		if return_type in (int, str):
# 			if return_type is int:
# 				return int(input_string)
# 			if return_type is str:
# 				return str(input_string)
# 		else:
# 			return input_string