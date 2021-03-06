# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import re
import socket
from copy import copy
from time import time
from os.path import join
from threading import Thread
from sqlite3 import IntegrityError
from shutil import copyfile, copytree

from sdl2 import (SDL_PumpEvents, SDL_StartTextInput, SDL_StopTextInput,
	SDL_KEYDOWN, SDLK_ESCAPE, SDLK_BACKSPACE, SDLK_RETURN, SDLK_KP_ENTER, SDL_TEXTINPUT)

from klibs.KLConstants import (AUTO_POS, BL_CENTER, BL_TOP_LEFT, QUERY_ACTION_UPPERCASE,
	QUERY_ACTION_HASH)
import klibs.KLParams as P
from klibs.KLJSON_Object import JSON_Object, AttributeDict
from klibs.KLUtilities import pretty_list, now, pump, flush, iterable, utf8, make_hash
from klibs.KLUtilities import colored_stdout as cso
from klibs.KLDatabase import EntryTemplate
from klibs.KLRuntimeInfo import runtime_info_init
from klibs.KLGraphics import blit, clear, fill, flip
from klibs.KLUserInterface import ui_request, any_key

try:
	from slacker import Slacker
	from slacker import Error as SlackerError
	SLACKER_AVAILABLE = True
except ImportError:
	SLACKER_AVAILABLE = False


user_queries = None
default_strings = None

def alert(text):
	'''A convenience function for clearing the screen and displaying an alert message. Will
	probably be depricated soon.

	'''
	clear()
	message(text, "alert", blit_txt=True, flip_screen=True)


def collect_demographics(anonymous=False):
	'''Collects participant demographics and writes them to the 'participants' table in the
	experiment's database, based on the queries in the "demographic" section of the project's
	user_queries.json file.
	
	If P.manual_demographics_collection = True, this function should be called at some point during
	the setup() section of your experiment class. Otherwise, this function will be run
	automatically when the experiment is launched.

	Args:
		anonymous (bool, optional): If True, this function will log all of the anonymous values for
			the experiment's demographic queries to the database immediately without prompting the
			user for input.

	'''
	from klibs.KLEnvironment import exp, db

	# ie. demographic questions aren't being asked for this experiment
	if not P.collect_demographics and not anonymous: return

	# first insert required, automatically-populated fields
	demographics = EntryTemplate('participants')
	demographics.log('created', now(True))
	try:
		# columns moved to session_info in newer templates
		demographics.log("random_seed", P.random_seed)
		demographics.log("klibs_commit", P.klibs_commit)
	except ValueError: 
		pass

	# collect a response and handle errors for each question
	for q in user_queries.demographic:
		if q.active:
			# if querying unique identifier, make sure it doesn't already exist in db
			if q.database_field == P.unique_identifier:
				# TODO: fix this to work with multi-user mode
				existing = db.query("SELECT `{0}` FROM `participants`".format(q.database_field))
				while True:
					value = query(q, anonymous=anonymous)
					if utf8(value) in [utf8(val[0]) for val in existing]:
						err = ("A participant with that ID already exists!\n"
								"Please try a different identifier.")
						fill()
						blit(message(err, "alert", align='center', blit_txt=False), 5, P.screen_c)
						flip()
						any_key()
					else:
						break
			else:
				value = query(q, anonymous=anonymous)
			demographics.log(q.database_field, value)

	# typical use; P.collect_demographics is True and called automatically by klibs
	if not P.demographics_collected:
		P.participant_id = db.insert(demographics)
		P.p_id = P.participant_id
		P.demographics_collected = True
		# Log info about current runtime environment to database
		if 'session_info' in db.table_schemas.keys():
			runtime_info = EntryTemplate('session_info')
			for col, value in runtime_info_init().items():
				runtime_info.log(col, value)
			db.insert(runtime_info)
		# Save copy of experiment.py and config files as they were for participant
		if not P.development_mode:
			pid = P.random_seed if P.multi_user else P.participant_id # pid set at end for multiuser
			P.version_dir = join(P.versions_dir, "p{0}_{1}".format(pid, now(True)))
			os.mkdir(P.version_dir)
			copyfile("experiment.py", join(P.version_dir, "experiment.py"))
			copytree(P.config_dir, join(P.version_dir, "Config"))
	else:
		#  The context for this is: collect_demographics is set to false but then explicitly called later
		db.update(demographics.table, demographics.defined)

	if P.multi_session_project and not P.manual_demographics_collection:
		try:
			exp.init_session()
		except:
			pass


def init_default_textstyles():

	from klibs.KLEnvironment import txtm

	# default styles can't be created until screen dimensions are loaded into Params from exp.display_init()
	txtm.add_style("default", P.default_font_size, P.default_color, font_label=P.default_font_name)
	txtm.add_style("alert", P.default_font_size, P.default_alert_color, font_label=P.default_font_name)


def init_messaging():

	global user_queries
	global default_strings

	# Load the user_queries file in and store the queries in an object
	try:
		user_queries = JSON_Object(P.user_queries_file_path)
		# After loading in queries, verify that all required sections are present
		required_sections = ['default_strings', 'demographic', 'experimental']
		for req in required_sections:
			if not req in user_queries.keys():
				err = "<red>Error: user_queries.json file missing required section '{0}'.</red>"
				cso(err.format(req))
				raise ValueError()
			default_strings = user_queries.default_strings # for easy accessiblity
	except ValueError:
		raise ValueError("User queries file has at least one formatting error; cannot continue.")
	
	if P.development_mode:
		P.slack_messaging = False

	# If using slack, determine if API key/room id have been set and slack.com is reachable
	if P.slack_messaging:
		warning = None
		if SLACKER_AVAILABLE:
			if not 'SLACK_API_KEY' in os.environ:
				warning = "A Slack API key could not be found"
			elif not 'SLACK_ROOM_ID' in os.environ:
				warning = "A Slack room ID could not be found"
			else:
				try:
					socket.create_connection(("www.slack.com", 80))	
				except socket.gaierror:
					warning = "Unable to connect to slack.com"
		else:
			warning = "The 'slacker' module is not installed"

		if warning: # if slack messaging not available, print warning saying why
			print("\t* Warning: {0}. Slack messaging will not be available.".format(warning))
			P.slack_messaging = False


def message(text, style=None, location=None, registration=None, blit_txt=True,
			flip_screen=False, clear_screen=False, align="left", wrap_width=None):
	r"""Renders a string of text using a given TextStyle, and optionally draws it to the display.

	Args:
		text (str): The string of text to be rendered.
		style (str, optional): The name of the :class:`~klibs.KLTextManager.TextStyle` to be used. 
			If none provided, defaults to the 'default' TextStyle.
		blit_txt (bool, optional): If True, the rendered text is drawn to the display buffer at
			the location and registration specfied using :func:`~klibs.KLGraphics.blit`. 
			Defaults to True.
		registration (int, optional): An integer from 1 to 9 indicating which location on the
			surface will be aligned to the location value (see manual for more info). Only
			required if blit_txt is True.
		location(tuple(int,int), optional): A tuple of x,y pixel coordinates indicating where to
			draw the object to. Only required if blit_txt is True.
		flip_screen (bool, optional): If True, :func:`~klibs.KLGraphics.flip` is called immediately
			after blitting and the text is displayed on the screen. Only has an effect if blit_txt
			is True. Defaults to False.
		clear_screen (bool, optional): If True, the background of the display buffer will be filled
			with the default fill colour before the text is blitted. Only has an effect if blit_txt
			is True. Defaults to False.
		align (str, optional): The justification of the text, must be one of "left", "center", or
			"right". This only has an effect if there are multiple lines (denoted by "\n") in the
			passed string of text. Defaults to "left" if not specified.
		wrap_width (int, optional): The maximum width of the message before text will wrap around
			to the next line (not currently implemented).

	Returns:
		:obj:`~klibs.KLGraphics.KLNumpySurface.NumpySurface`: A NumpySurface object that can be 
			drawn to the screen using :func:`~klibs.KLGraphics.blit`, or None if blit_txt is True.
	
	Raises:
		ValueError: If blit_txt is true and location is not a valid pair of x/y coordinates.

	"""

	#TODO: 	make sure there won't be any catastrophic issues with this first, but rearrange 'align'
	#		and 'width' so they follow 'text' and 'style'. Also, consider whether using different
	#		method entirely for blitting/flipping messages since it kind of makes this a mess.

	#TODO:	consider whether a separate 'textbox' method (with justification/width/formatting)
	#		would be appropriate, or if having it all rolled into message() is best.

	from klibs.KLEnvironment import txtm

	if not style:
		style = txtm.styles['default']
	else:
		try:
			# TODO: Informative error if requested font style doesn't exist
			style = txtm.styles[style]
		except TypeError:
			pass

	message_surface = txtm.render(text, style, align, wrap_width)
	if blit_txt == False:
		return message_surface
	else:
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
				raise ValueError("Argument 'location' must be a location constant or iterable x,y coordinate pair")
			if clear_screen:
				fill(clear_screen if iterable(clear_screen) else P.default_fill_color)
			blit(message_surface, registration, location)
			if flip_screen:
				flip()


def query(query_ob, anonymous=False):
	'''Asks the user a question and collects the response via the keyboard. Intended for use with
	the queries contained within a project's user_queries.json file. This function is used
	internally for collecting demographics at the start of each run, but can also be used during
	experiment runtime to collect info from participants based on the queries contained in the
	"experimental" section of the user_queries.json file.

	Args:
		query_ob (:class:`~klibs.KLJSON_Object.AttributeDict`): The object containing the query
			to present. See :obj:`~klibs.KLCommunication.user_queries` for more information.
		anonymous (bool, optional): If True, will immediately return the query object's anonymous
			value without prompting the user (used interally for P.development_mode). Defaults to
			False.
	
	Returns:
		The response to the query, coerced to the type specified by query_ob.format.type (can be
		str, int, float, bool, or None).
	
	Raises:
		ValueError: If the query object's type is not one of "str", "int", "float", "bool", or None,
			or if a query_ob.format.range value is given and the type is not "int" or "float".
		TypeError: If query_ob.accepted is specified and it is not a list of values, or if a
			query_ob.format.range is specified and it is not a two-item list.
			
	'''
	from klibs.KLEnvironment import txtm

	if anonymous:
		try:
			# Check if anon value is an EVAL statement, and if so evaluate it
			eval_statement = re.match(re.compile(u"^EVAL:[ ]*(.*)$"), query_ob.anonymous_value)
			if eval_statement:
				query_ob.anonymous_value = eval(eval_statement.group(1))
		except TypeError:
			pass
		return query_ob.anonymous_value

	f = query_ob.format
	if f.type not in ("int", "float", "str", "bool", None):
		err = "Invalid data type for query '{0}': {1}".format(query_ob.title, f.type)
		raise ValueError(err)
	
	# Set defaults for styles and positioning if not specified
	if f.styles == 'default':
		f.styles = AttributeDict({'query': 'default', 'input': 'default', 'error': 'alert'})

	locations = AttributeDict({'query': AUTO_POS, 'input': AUTO_POS, 'error': AUTO_POS})
	registrations = AttributeDict({'query': AUTO_POS, 'input': AUTO_POS, 'error': AUTO_POS})
	if f.positions == 'default':
		f.positions = AttributeDict({'locations': locations, 'registrations': registrations})
	else:
		if f.positions.locations == 'default': f.positions.locations = locations
		if f.positions.registrations == 'default': f.positions.registrations = registrations

	q_text = message(query_ob.query, f.styles.query, align='center', blit_txt=False)

	# address automatic positioning
	p = f.positions
	if p.locations.query == AUTO_POS:
		p.locations.query = [P.screen_c[0], int(0.1 * P.screen_y)]
		p.registrations.query = BL_CENTER
	for k in ['input', 'error']:
		if p.locations[k] == AUTO_POS:
			v_pad = q_text.height + 2 * txtm.styles[f.styles.query].line_height
			p.locations[k] = [P.screen_c[0], p.locations.query[1] + v_pad]
			p.registrations[k] = BL_CENTER

	# Create an informative error message for invalid responses
	accepted_responses = query_ob.accepted  # for code readability
	try:
		if accepted_responses:
			try:
				iter(accepted_responses)
				accepted_str = pretty_list(accepted_responses)
				invalid_answer_str = default_strings['invalid_answer'].format(accepted_str)
			except:
				raise TypeError("The 'accepted' key of a question must be a list of values.")
		elif f.range:
			if f.type not in ("int", "float"):
				raise ValueError("Only queries with numeric types can use the range parameter.")
			elif isinstance(f.range, list) == False or len(f.range) != 2:
				raise TypeError("Query ranges must be two-item lists, containing an upper bound "
					"and a lower bound.")
			try:
				template = default_strings['out_of_range']
			except KeyError:
				template = "Your answer must be a number between {0} and {1}, inclusive."
			invalid_answer_str = template.format(f.range[0], f.range[1])
	except:
		cso("\n<red>Error encountered while parsing query '{0}':</red>".format(query_ob.title))
		raise

	# user input loop; exited by breaking
	input_string = u''  # populated in loop below
	error_string = None
	user_finished = False

	# Clear event queue and draw query text to screen before entering input loop
	flush()
	SDL_StartTextInput()
	fill()
	blit(q_text, p.registrations.query, p.locations.query)
	flip()

	while not user_finished:
		for event in pump(True):

			if event.type == SDL_KEYDOWN:

				error_string = None # clear error string (if any) on new key event
				ui_request(event.key.keysym)
				sdl_keysym = event.key.keysym.sym

				if sdl_keysym == SDLK_ESCAPE:
					# Esc clears any existing input
					input_string = ""

				elif sdl_keysym == SDLK_BACKSPACE:
					# Backspace removes last character from input
					input_string = input_string[:-1]

				elif sdl_keysym in (SDLK_KP_ENTER, SDLK_RETURN):
					# Enter or Return check if a valid response has been made and end loop if it has
					if len(input_string) > 0:
						response = input_string
						# If type is 'int' or 'float', make sure input can be converted to that type
						if f.type == "int":
							try:
								response = int(input_string)
							except ValueError:
								error_string = "Please respond with an integer."
						elif f.type == "float":
							try:
								response = float(input_string)
							except ValueError:
								error_string = "Please respond with a number."
						# If no errors yet, check input against list of accepted values (if q has one)
						if not error_string:
							if accepted_responses:
								user_finished = response in accepted_responses
								if not user_finished:
									error_string = invalid_answer_str
							elif f.range:
								user_finished = (f.range[0] <= response <= f.range[1])
								if not user_finished:
									error_string = invalid_answer_str
							else:
								user_finished = True
					elif query_ob.allow_null is True:
						user_finished = True
					else:
						# If no input and allow_null is false, display error
						error_string = default_strings['answer_not_supplied']

			elif event.type == SDL_TEXTINPUT:

				input_string += event.text.text.decode('utf-8')
				if f.case_sensitive is False:
					input_string = input_string.lower()
				input_string = input_string.strip() # remove any trailing whitespace
			
			else:
				continue

			# If any text entered or error message encountered, render text for drawing
			if error_string:
				rendered_input = message(error_string, f.styles.error, blit_txt=False)
				input_string = ""
			elif len(input_string):
				if f.password:
					rendered_input = message(len(input_string)*'*', f.styles.input, blit_txt=False)
				else:
					rendered_input = message(input_string, f.styles.input, blit_txt=False)
			else:
				rendered_input = None

			# Draw question and any entered response to screen 
			fill()
			blit(q_text, p.registrations.query, p.locations.query)
			if rendered_input:
				loc = p.locations.error if error_string else p.locations.input
				reg = p.registrations.error if error_string else p.registrations.input
				blit(rendered_input, reg, loc)
			flip()

	# Once a valid response has been made, clear the screen
	fill()
	flip()
	SDL_StopTextInput()

	if query_ob.allow_null and len(input_string) == 0:
		return None
	elif f.type == "int":
		return int(input_string)
	elif f.type == "str":
		if f.action == QUERY_ACTION_HASH:
			return make_hash(input_string)
		elif f.action == QUERY_ACTION_UPPERCASE:
			return utf8(input_string).upper()
		else:
			return utf8(input_string)
	elif f.type == "float":
		return float(input_string)
	elif f.type == "bool":
		return input_string in f.accept_as_true
	else:
		return input_string


def slack_message(message):
	"""Sends a given message to a channel in a user-defined Slack group. This can be used for
	keeping updated on a participant's progress through blocks during a session, for allowing
	participants to call you into the experiment room by pressing a certain key, or for being
	notified of runtime problems (e.g. significant EyeLink drift) as soon as they happen.
	To avoid annoying your co-workers while testing/debugging experiments, messages sent through
	this command will be printed to the terminal instead of being sent to the channel while in
	development mode.

	To use this feature, you must first have a Slack team set up, a channel that you want messages
	sent to, and a Slack bot that will write your messages to that channel. To create a Slack bot
	for your team, go to 'Manage > Custom Integrations > Bots > Add Configuration' on your team's
	Slack page and configure your bot with a name.
	
	For security reasons, it's a bad idea to include your Slack API key (the unique id that lets
	you control your Slack bot) directly in your code, and it also makes your experiment programs
	harder to share with others if you do. To avoid these problems, the Slack messaging feature
	looks for two environment variables on the computer it's being run on:

	- SLACK_API_KEY: Should be set to the unique API key for your team's Slack bot.
	- SLACK_ROOM_ID: Should be set to the name of the channel you want messages from that
		computer to be posted to (e.g. '#room1').
		
	If you have multiple experiment rooms, it's a good idea to have separate Slack channels (and
	thus separate 'SLACK_ROOM_ID's) for each of them.

	The parameter 'slack_messaging' must be set to True in order for messages to be sent to
	Slack. If this parameter is set to False, this function will do nothing.

	Args:
		message (str): the message to be sent to the Slack channel.

	"""
	
	def slack_msg_thread(_api_key, _message, _channel):
		# Actually sends the message to the channel, run in a separate thread using Thread().
		try:
			slack = Slacker(_api_key)
			slack.chat.post_message(_channel, _message, as_user="true:")
		except SlackerError as e:
			cso("<red>Warning: Unable to send message '{0}' to channel '{1}', "
				"problem encountered with Slack API.</red>".format(_message, _channel))
			print("Exception encoutered: {0}".format(str(e)))
		
	if P.slack_messaging:
		api_key = os.environ['SLACK_API_KEY']
		channel = os.environ['SLACK_ROOM_ID']
		if channel[0] != '#': # if no leading hashtag, append one so it works anyway
			channel = '#{0}'.format(channel)
		# The post_message function can take > 1 second to return, so we run it in a separate
		# thread to avoid delaying the whole experiment whenever it's called.
		msg_thread = Thread(target=slack_msg_thread, args=(api_key, str(message), channel,))
		msg_thread.start()
	else:
		if P.development_mode:
			print("Slack message: {0}".format(message))
		
