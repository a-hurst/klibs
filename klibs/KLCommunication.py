# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'


from copy import copy
from sdl2 import SDL_PumpEvents, SDL_KEYUP, SDL_KEYDOWN, SDLK_BACKSPACE, SDLK_RETURN, SDLK_KP_ENTER, SDLK_ESCAPE
from hashlib import sha1

from klibs.KLConstants import AUTO_POS,BL_CENTER, BL_TOP, BL_TOP_LEFT, BL_TOP_RIGHT, BL_LEFT, BL_RIGHT, BL_BOTTOM, \
	BL_BOTTOM_LEFT, BL_BOTTOM_RIGHT, ALL, QUERY_ACTION_HASH, DELIM_NOT_LAST, DELIM_NOT_FIRST
from klibs.KLGraphics import blit, clear, fill, flip
import klibs.KLParams as P
from klibs.KLUtilities import absolute_position, now, pretty_join, sdl_key_code_to_str, pump
from klibs.KLUserInterface import ui_request

global user_queries
global block_break_messages


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
		message(text, "alert", blit_txt=True, flip_screen=True)
		if display_for > 0:
			pass
			# todo: use ui_request and timekeeper


def collect_demographics(anonymous=False):
	from klibs.KLEnvironment import exp, db

	global user_queries

	"""
	Gathers participant demographic information and enter it into the project database.
	Should not be explicitly called; see ``P.collect_demographics``.
	:param anonymous: Toggles generation of arbitrary participant info in lieu of participant-supplied info.
	:type anonymous: Boolean
	"""

	# ie. demographic questions aren't being asked for this experiment
	if not P.collect_demographics and not anonymous: return

	if P.collect_demographics:
		if P.multi_session_project:
			id_str = query(
				"If you have already created an id for this experiment, please enter it now. Otherwise press 'return'.",
				password=True, accepted=ALL)
			if id_str:
				return exp.init_session(id_str)

	# first insert required, automatically-populated fields
	db.init_entry('participants', instance_name='ptcp', set_current=True)
	db.log("random_seed", P.random_seed)
	db.log("klibs_commit", P.klibs_commit)
	db.log('created', now(True))

	# collect a response and handle errors for each question
	for q in user_queries.demographic:
		# todo: identify errors pertaining to fields where unique values are required; optionally retry the question
		db.log(q.database_field, query(q, anonymous=anonymous))

	# typical use; P.collect_demographics is True and called automatically by klibs
	if not P.demographics_collected:
		P.participant_id = db.insert()
		P.demographics_collected = True
	else:
		#  The context for this is: collect_demographics is set to false but then explicitly called later
		db.update(P.participant_id)

	# unset the current DB entry and initialize the session for multi-session projects
	db.current(False)
	if P.collect_demographics and P.multi_session_project:
		exp.init_session()


def init_messaging():
	from klibs.KLCommunication import message
	from klibs.KLEnvironment import txtm, exp
	from klibs.KLJSON_Object import JSON_Object

	global user_queries
	global block_break_messages
	# try to create question objects (ie. JSON_Objects with expected keys) from demographics file
	try:
		user_queries = JSON_Object(P.user_queries_file_path)
	except ValueError:
		raise ValueError("User queries file has at least one formatting error; cannot continue.")

	# set default strings for communication
	for k in user_queries.default_strings:
		setattr(P, k, user_queries.default_strings[k])

	# default styles can't be created until screen dimensions are loaded into Params from exp.display_init()
	txtm.add_style("default", P.default_font_size, P.default_color, font_label="Frutiger")
	txtm.add_style("alert", P.default_font_size, P.default_alert_color, font_label="Frutiger")

	if P.pre_render_block_messages:
		for i in range(1, P.blocks_per_experiment, 1):
			msg = P.block_break_message.format(i, P.blocks_per_experiment)
			r_msg = message(msg, blit=False)
			block_break_messages.append(r_msg)


def message(text, style=None, location=None, registration=None, blit_txt=True, flip_screen=False, wrap_width=None):
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
	:param blit_txt: Toggles whether message surface is automatically :func:`~klibs.KLExperiment.Experiment
	.blit` to
	the display buffer.
	:type blit_txt: Boolean
	:param flip_screen: Toggles whether :func:`~klibs.KLExperiment.Experiment.flip` is automatically called after
	blit.
	:type flip_screen: Boolean
	:return: NumpySurface or Boolean
		"""

	from klibs.KLEnvironment import txtm

	if not style:
		style = txtm.styles['default']
	else:
		try:
			style = txtm.styles[style]
		except TypeError:
			pass
	# todo: padding should be implemented as a call to resize() on message surface; but you have to fix wrap first

	# process blit registration
	if location == "center" and registration is None:  # an exception case for perfect centering
		registration = BL_CENTER
	if registration is None:
		registration = BL_TOP_LEFT

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

	message_surface = txtm.render(text, style)
	if not blit_txt:
		return message_surface
	else:
		blit(message_surface, registration, location)
	if flip_screen:
		flip()


def query(query_ob, anonymous=False):
	from klibs.KLEnvironment import txtm

	if anonymous:
		return query_ob.anonymous_value

	input_string = ''  # populated in loop below
	error_string = None


	f = query_ob.format
	if f.type in ("int", "float", "str", "bool"):
		f.type = eval(f.type)
	elif f.type is None:
		pass
	else:
		e_msg = "Invalid data type for query '{0}'".format(query_ob.title)
		raise ValueError(e_msg)
	p = f.positions
	q_text = message(query_ob.query, f.styles.query, blit_txt=False)

	# address automatic positioning
	if p.locations.query == AUTO_POS:
		p.locations.query =  [P.screen_c[0], int(0.1 * P.screen_y)]
		p.registrations.query = BL_CENTER

	if p.locations.input == AUTO_POS:
		v_pad = q_text.height + 2 * txtm.styles[f.styles.query].line_height
		p.locations.input =  [P.screen_c[0], p.locations.query[1] + v_pad]
		p.registrations.input = BL_CENTER

	# define this to save typing it out repeatedly blow
	def blit_question(input_text=None):
		fill()
		blit(q_text, p.registrations.query, p.locations.query)
		try:
			blit(input_text, p.registrations.input, p.locations.input)
		except TypeError:
			pass  # ie. input_text=None
		flip()

	# create an accepted answers string to present to user
	if query_ob.accepted:
		try:
			iter(query_ob.accepted)
			accepted_str = pretty_join(query_ob.accepted, delimiter=",", delimit_behaviors=[DELIM_NOT_LAST],
									   wrap_each="'", before_last='or', prepend='[ ', append=']')
			invalid_answer_string = P.invalid_answer.format(accepted_str)

		except:
			raise TypeError("The 'accepted' key of a question object must be an array/list (JSON/Python).")

	blit_question()

	# user input loop; exited by breaking
	SDL_PumpEvents()
	user_finished = False

	while not user_finished:
		input_surface = None
		for event in pump(True):
			if event.type !=  SDL_KEYDOWN:
				continue
			ui_request(event.key.keysym)

			# reset error and input strings if an error has been displayed
			error_string = None

			key = event.key  # keyboard button event object (https://wiki.libsdl.org/SDL_KeyboardEvent)
			sdl_keysym = key.keysym.sym

			# handle deletions
			if sdl_keysym == SDLK_BACKSPACE:
				input_string = input_string[:-1]

			# handle user indicating that they're finished
			if sdl_keysym in (SDLK_KP_ENTER, SDLK_RETURN):  # ie. if enter or return
				if len(input_string):
					if f.type == "int":
						try:
							input_string = int(input_string)
						except ValueError:
							error_string = "Please respond with an integer."
					elif f.type == "float":
						try:
							input_string = float(input_string)
						except ValueError:
							error_string = "Please respond with a number."
					if not error_string:
						if query_ob.accepted:   # to make the accepted list work, there's a lot of checking yet to do
							user_finished = input_string in query_ob.accepted
							if not user_finished:
								error_string = invalid_answer_string
						else:
							user_finished = True
				else:
					error_string = P.no_answer_string

				if error_string:
					input_surface = message(error_string, f.styles.error, blit_txt=False)
					input_string = ""

			# escape erases the user input
			if sdl_keysym == SDLK_ESCAPE:
				input_string = ""
				input_surface = None

			if sdl_key_code_to_str(sdl_keysym):
				input_string += sdl_key_code_to_str(sdl_keysym)
				if f.case_sensitive is False:
					input_string = input_string.lower()

			# remove trailing whitespace
			input_string = str(input_string).strip()

			if not input_surface:
				if f.password:
					input_surface = message(len(input_string) * '*', f.styles.input, blit_txt=False)
				else:
					input_surface = message(input_string, f.styles.input, blit_txt=False)

			blit_question(input_text=input_surface)

	fill()
	flip()
	if f.type is int:
		return int(input_string)
	elif f.type is str:
		if f.action == QUERY_ACTION_HASH:
			return sha1(str(input_string)).hexdigest()
		else:
			return str(input_string)
	elif f.type is float:
		return float(input_string)
	elif f.type is bool:
		return input_string in f.accept_as_true
	else:
		return input_string
