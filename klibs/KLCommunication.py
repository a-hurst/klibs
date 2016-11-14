# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'


from copy import copy
from sdl2 import SDL_PumpEvents, SDL_KEYUP, SDL_KEYDOWN, SDLK_BACKSPACE, SDLK_RETURN, SDLK_KP_ENTER, SDLK_ESCAPE
from hashlib import sha1

from klibs.KLConstants import AUTO_POS,BL_CENTER, BL_TOP, BL_TOP_LEFT, BL_TOP_RIGHT, BL_LEFT, BL_RIGHT, BL_BOTTOM, \
	BL_BOTTOM_LEFT, BL_BOTTOM_RIGHT, ALL, QUERY_ACTION_HASH
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

	# ###################################################
	# if anonymous:
	# 	name = P.anonymous_username
	# else:
	#
	#
	#
	# 	name_query_string = query(
	# 		'What is your full name, banner number or e-mail address? \nYour answer will be encrypted and cannot be read later.',
	# 		password=True)
	# 	name_hash = sha1(name_query_string)
	# 	name = name_hash.hexdigest()
	# self.db.log('userhash', name)
	#
	# # names must be unique; returns True if unique, False otherwise
	# if self.db.is_unique('participants', 'userhash', name):
	# 	try:
	# 		for q in P.demographic_questions:
	# 			if anonymous:
	# 				self.db.log(q[0], q[4])
	# 			else:
	# 				self.db.log(q[0], query(q[1], accepted=q[2], return_type=q[3]))
	# 	except AttributeError:
	# 		if anonymous:
	# 			sex = "m" if now() % 2 > 0  else "f"
	# 			handedness = "a"
	# 			age = 0
	# 		else:
	# 			sex_str = "What is your sex? \nAnswer with:  (m)ale,(f)emale"
	# 			sex = query(sex_str, accepted=('m', 'M', 'f', 'F'))
	# 			handedness_str = "Are right-handed, left-handed or ambidextrous? \nAnswer with (r)ight, (l)eft or (a)mbidextrous."
	# 			handedness = query(handedness_str, accepted=('r', 'R', 'l', 'L', 'a', 'A'))
	# 			age = query('What is  your age?', return_type='int')
	# 			self.db.log('sex', sex)
	# 			self.db.log('handedness', handedness)
	# 			self.db.log('age', age)
	# 	self.db.log('created', now(True))
	# 	if not P.demographics_collected:
	# 		P.participant_id = self.db.insert()
	# 		P.demographics_collected = True
	# 	else:
	# 		#  The context for this is: collect_demographics is set to false but then explicitly called later
	# 		self.db.update(P.participant_id)
	# else:
	# 	retry = query('That participant identifier has already been used. Do you wish to try another? (y/n) ')
	# 	if retry == 'y':
	# 		self.collect_demographics()
	# 	else:
	# 		self.fill()
	# 		message("Thanks for participating!", location=P.screen_c)
	# 		any_key()
	# 		self.quit()
	# self.db.current(False)
	# if P.collect_demographics and P.multi_session_project:
	# 	self.init_session()


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
	print style, style.font_size
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
	p = f.positions
	print f.styles.query
	q_text = message(query_ob.query, f.styles.query)

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
		blit(q_text, p.locations.query, p.registrations.query)
		try:
			blit(input_text, p.locations.input, p.registrations.input)
		except TypeError:
			pass  # ie. input_text=None
		flip()

	# create an accepted answers string to present to user
	if query_ob.accepted:
		try:
			iter(query_ob.accepted)
			accepted_str = pretty_join(query_ob.accepted, delimiter=",", before_last='or', prepend='[ ', append=']')
			invalid_answer_string = P.invalid_answer_string.format(accepted_str)
		except:
			raise TypeError("The 'accepted' key of a question object must be an array/list (JSON/Python).")

	# user input loop; exited by breaking
	while True:
		input_surface = None
		SDL_PumpEvents()
		for event in pump(True):
			if event.type is not SDL_KEYDOWN:
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
					if query_ob.accepted:   # to make the accepted list work, there's a lot of checking yet to do
						user_finished = input_string in query_ob.accepted
						if not user_finished:
							error_string = invalid_answer_string
					else:
						break
				else:
					error_string = P.no_answer_string

				if error_string:
					input_surface = message(error_string, f.styles.error)
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
			input_string = input_string.strip()

			if f.password:
				input_surface = message(len(input_string) * '*', f.style.input)

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

#
# 		# todo: split this into query_draw() [above code] and query_listen() [remaining code]
