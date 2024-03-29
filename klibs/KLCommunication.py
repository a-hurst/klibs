# -*- coding: utf-8 -*-
__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import re
from os.path import join
from shutil import copyfile, copytree

from sdl2 import (SDL_StartTextInput, SDL_StopTextInput,
    SDL_KEYDOWN, SDLK_ESCAPE, SDLK_BACKSPACE, SDLK_RETURN, SDLK_KP_ENTER, SDL_TEXTINPUT)

from klibs.KLConstants import (AUTO_POS, BL_CENTER, QUERY_ACTION_UPPERCASE,
    QUERY_ACTION_HASH)
import klibs.KLParams as P
from klibs.KLJSON_Object import import_json, AttributeDict
from klibs.KLEventQueue import pump, flush
from klibs.KLUtilities import pretty_list, now, utf8, make_hash
from klibs.KLUtilities import colored_stdout as cso
from klibs.KLDatabase import EntryTemplate
from klibs.KLRuntimeInfo import runtime_info_init
from klibs.KLGraphics import blit, clear, fill, flip
from klibs.KLUserInterface import ui_request, any_key
from klibs.KLText import TextStyle, add_text_style


user_queries = None
default_strings = None


def alert(text):
    '''A convenience function for clearing the screen and displaying an alert message. Will
    probably be depricated soon.

    '''
    clear()
    message(text, "alert", blit_txt=True)
    flip()


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
                existing = [utf8(pid) for pid in db.get_unique_ids()]
                while True:
                    value = query(q, anonymous=anonymous)
                    if utf8(value) in existing:
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
            if P.condition and 'condition' in runtime_info.schema.keys():
                runtime_info.log('condition', P.condition)
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


def init_default_textstyles():
    # Need to wait for screen size/DPI to be known before loading default text styles
    # in case default units are specified in degrees
    add_text_style("default", font=P.default_font_name)
    add_text_style("alert", color=P.default_alert_color, font=P.default_font_name)


def init_messaging():
    # This function should be removed somehow: user queries should be a) redone, and
    # b) loaded in with a regular function
    # Need to do in a way that won't break TraceLab
    global user_queries
    global default_strings

    # Load the user_queries file in and store the queries in an object
    try:
        user_queries = import_json(P.user_queries_file_path)
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


def message(
        text, style='default', align='left', wrap_width=None, registration=5,
        location=None, blit_txt=False
    ):
    """Renders a string of text with a given set of style/formatting parameters.

    Messages can be single or multiple lines of text. To add a line break in the
    rendered message, add a newline character (``\n``) wherever you want the split
    between lines to be. Multi-line messages can be rendered as either left-justified
    (default), right-justified, or center-aligned using the ``align`` argument. For
    example, to render three centered lines in a single message, you can do::

       msg = message("Line One\nLine Two\nLine Three", align='center')

    To render text with a different size, color, or font than the defaults set in your
    project's ``params.py`` file, first define a new text style with
    :func:`~klibs.KLText.add_text_style` and then pass its name to the ``style``
    argument::

        RED = (255, 0, 0)
        add_text_style('small_red', size='0.3deg', color=RED)
        msg = message("Small red text!", style='small_red')

    In addition to rendering text, the ``message`` function can also be used to blit
    messages directly to the screen, which can be handy if a message is only getting
    drawn to the screen once (e.g. each update of a countdown timer). This can be done
    by specifying a location (and optionally a registration) for the message.

    For example, the following two chunks of code have the same result::

       # Render, then blit
       msg = message("Hello there!")
       blit(msg, 5, P.screen_c)

       # Render and blit
       message("Hello there!", registration=5, location=P.screen_c)

    Note that unlike :func:`~klibs.KLGraphics.blit`, the default registration for
    blitted messages is 5 (i.e. center-aligned). This means that, for example, a message
    with a location of ``P.screen_c`` will be centered in the middle of the screen
    unless a different registration is manually specified.

    Args:
        text (str): The string of text to render.
        style (str or :obj:`~klibs.KLText.TextStyle`, optional): The text style to use
            for rendering the string. Defaults to the 'default' style if not specified.
        align (str, optional): The alignment method for multi-line text. Can be "left"
            (left-justified, default), "right" (right-justified), or "center".
        wrap_width (int, optional): The maximum width (in pixels) of the rendered text
            surface. If a line of text exceeds this width, it will wrap around to the
            next line. Defaults to None (no text wrapping).
        registration (int, optional): If blitting, specifies the corner or side of the
            rendered text to align to the ``location`` coordinates. Defaults to the
            center of the rendered text. See :func:`~klibs.KLGraphics.blit` for more info.
        location (tuple, optional): A tuple of (x, y) pixel coordinates. If provided,
            the message will be automatically blit to this location on the screen.
            Defaults to None (not blitted).
        blit_txt (bool, optional): Deprecated, use 'location' to indicate whether the
            text should be blitted instead.

    Returns:
        :obj:`~klibs.KLGraphics.NumpySurface`: A NumpySurface containing the rendered
        text.

    """
    # TODO: consider whether a separate 'textbox' method (with justification/width/formatting)
    #		would be appropriate, or if having it all rolled into message() is best.
    # NOTE: Bit of an API mess: if wrap_width is set and text contains any line breaks,
    #       the resulting surface will be the width specified by wrap_width regardless
    #       of whether any of the lines were long enough to be wrapped. Conversely, if
    #       wrap_width is set and the text is only one line, the surface is only the
    #       specified width if the line is long enough to be wrapped. Should either
    #       change 'wrap_width' to 'width' and guarantee output surface is the given
    #       width or change the multi-line behaviour.
    from klibs.KLEnvironment import txtm

    if not isinstance(style, TextStyle):
        if style not in txtm.styles.keys():
            e = "No text style with the name '{0}' has been added to the klibs runtime."
            raise RuntimeError(e.format(style))
        style = txtm.styles[style]

    # Render (and optionally blit) the text
    message_surface = txtm.render(text, style, align, wrap_width)
    if location is not None:
        blit(message_surface, registration, location)

    return message_surface


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
            # NOTE: Query line spacing after new TextStyle overhaul looks different
            # than before (larger spacing), should look into it
            font = txtm.styles[f.styles.query]
            v_pad = q_text.height + int(0.5 * font.line_space * font.size_px)
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


slack_warning = True

def slack_message(message):
    """Sends a message to a given Slack channel.

    Deprecated, will be removed soon.

    """
    global slack_warning
    if slack_warning:
        e = (
            "NOTE: Slack messaging has been removed from klibs. "
            "To continue to use Slack messaging in your experiment, please write "
            "your own messaging code with the Slacker library."
        )
        print("")
        print(e)
        print("")
        slack_warning = False
