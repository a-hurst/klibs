"""

The KLQueries module provides a simple set of classes for presenting queries and
collecting/validating their responses.

There are many situations where you might want to prompt a numeric, categorical, or
free-form text response from a participant. For example, in an implicit learning task
you might want to ask the participant at the end of the task whether they thought they
had noticed a repeating sequence during the experiment. If the participant responds
that they did, you might also want to prompt them to report that sequence to the best
of their memory::

    learned_q = ChoiceQuery(
        "Do you feel like you noticed a repeating sequence? (y/n)",
        choices = ['y', 'n']
    )
    seq_learned = learned_q.collect()

    seq = None
    if seq_learned == "y":
        seq_q = TextQuery(
            "Please enter the sequence to the best of your memory:",
            max_len=10, case='lower'
        )
        seq = seq_q.collect()

When a Query response is collected, the query text is presented on screen and the
user's response is rendered underneath it as it is entered on the keyboard. Once
the user presses the Return/Enter key, the response is checked to ensure it meets
the criteria defined by the query type and options (e.g. that the response matches
one of the possible response options for a ChoiceQuery). If the response is valid,
it will be returned immediately. If not, the response will be cleared and an
informative error message is presented (e.g. "Please enter one of the following
options: [ y or n ]") prompting the user to try again.

"""

import sdl2
from klibs import P
from klibs.KLInternal import iterable
from klibs.KLUtilities import make_hash, pretty_list
from klibs.KLEventQueue import flush, pump
from klibs.KLUserInterface import ui_request
from klibs.KLText import TextStyle, message, _get_text_style
from klibs.KLGraphics import fill, blit, flip


class QueryStyle():
    """Defines a custom style to use for rendering a Query.

    By default, queries will use the default text style and other aesthetics from the
    klibs runtime. This class allows for customizing the appearance of queries by
    overriding one or more of these defaults::

        q_style = QueryStyle(align='left', location=(100, 100), registration=7)
        rating_q = NumberQuery(
            "On a scale from 1 to 10, how well do you think you did?",
            min=1, max=10, style=q_style
        )

    If `location` and `registration` are not provided, queries default to being
    center-aligned and presented at the top of the screen (see the
    :func:`~klibs.KLGraphics.blit` documentation for a detailed explanation of
    these parameters).

    Additional style parameters that can be overridden include the text style, the
    text alignment, the vertical offset of the input text relative to the bottom edge
    of the query, the background fill color, and the colour to use for error text.

    Args:
        textstyle (str or :obj:`~KLText.TextStyle`): The text style (font, size, color,
            etc.) to use for rendering the Query. Defaults to the default text style.
        align (str, optional): The text alignment to use ('left', 'right', or 'center')
            for the query and input text. Defaults to center alignment.
        registration (int, optional): An integer from 1 to 9 indicating the anchor point
            on the query text to align with the given location. Defaults to the midpoint
            of the top edge.
        location (tuple, optional): A custom location in (x, y) pixel coordinates
            specifying where to draw the query text.
        input_offset (float, optional): The offset between the last line of query text
            and the rendered query input in units of line height.
        bg_color (tuple, optional): A custom background fill color to use for the query.
        err_color (tuple, optional): A custom color to use for error text if an invalid
            response is entered.

    """
    def __init__(
        self,
        textstyle='default',
        align='center',
        registration=8,
        location=None,
        input_offset=2.0,
        bg_color=None,
        err_color=None
    ):
        self.reg = registration
        self.loc = location if location else (P.screen_c[0], P.screen_y * 0.08)
        self.align = align
        self.input_offset = input_offset
        self.bg_color = bg_color
        self._init_text_styles(textstyle, err_color)

    def _validate_options(self):
        if self.input_offset < 0:
            e = "Query input offset must be a positive value."
            raise ValueError(e)

    def _init_text_styles(self, style, err_color):
        # Get the error style and input offset based on the params & text style
        if not isinstance(style, TextStyle):
            style = _get_text_style(style)
        self.style = style
        err_color = P.default_alert_color if err_color == None else err_color
        self.err = TextStyle(style.fontname, style._size, err_color)
        line_offset = style.size_px * style.line_space
        self.input_offset_px = (self.input_offset * line_offset) - style.size_px


class Query():
    """An abstract base class for queries.

    Query objects present simple prompts to users and collect/validate their
    responses.

    Args:
        q (str or list): The text of the query to present to the participant. Can
            be a string or a list of strings.
        style (:obj:`~QueryStyle`, optional): Optional aesthetic overrides defining the
            appearance and location of the query.

    """
    def __init__(self, q, style=None):
        self.q = "\n".join(q) if iterable(q) else q
        self.style = style if style else QueryStyle()
        self._q_msg = message(self.q, self.style.style, self.style.align)
        self._input_loc, self._input_reg = self._get_input_position(self.style)
        self.password = False

    def _format_input(self, resp):
        # Takes the current query input and formats/sanitizes it
        return resp
        
    def _validate_response(self, resp):
        # Checks whether the response is valid for the current query,
        # returning an error string to be displayed if not
        return None
    
    def _format_response(self, resp):
        # Applies any final formatting to the response before returning it
        return resp

    def _get_input_position(self, style):
        # Given query location/registration/size, get bottom-left corner
        y_offset, x_offset = (0, 0)

        if style.reg >= 7:
            y_offset = self._q_msg.height
        elif style.reg >= 4:
            y_offset = self._q_msg.height / 2

        if style.reg % 3 == 0:
            x_offset = -self._q_msg.width / 2
        elif style.reg % 3 == 1:
            x_offset = self._q_msg.width / 2

        q_bcx = style.loc[0] + x_offset
        q_bcy = style.loc[1] + y_offset
        if style.align == "center":
            input_x = q_bcx
            input_reg = 8
        elif style.align == "left":
            input_x = int(q_bcx - self._q_msg.width / 2)
            input_reg = 7
        elif style.align == "right":
            input_x = int(q_bcx + self._q_msg.width / 2)
            input_reg = 9

        input_y = q_bcy + style.input_offset_px
        return (input_x, input_y), input_reg

    def _render(self, userinput, err=None):
        # Renders the query and any current input/error to the screen
        if err:
            resp_msg = message(err, self.style.err)
        else:
            if self.password:
                userinput = len(userinput) * '*'
            resp_msg = message(userinput, self.style.style)

        fill(self.style.bg_color)
        blit(self._q_msg, self.style.reg, self.style.loc)
        blit(resp_msg, self._input_reg, self._input_loc)
        flip()

    def collect(self):
        """Presents the query and collects a response.

        This method draws the query to the screen and waits for the user to
        enter a response using the keyboard. The user's text input will be shown
        under the query as it is entered.

        Responses are submitted by pressing the Enter (or Return) key. The response
        will be validated once submitted. If the response is invalid, error text
        explaining how to respond correctly will be presented and will remain on
        screen until the user begins entering another response.

        Returns:
            The collected response.

        """
        err = None
        resp = ""
        self._render(resp)

        flush()
        sdl2.SDL_StartTextInput()
        while True:
            for event in pump():

                if event.type == sdl2.SDL_TEXTINPUT:
                    resp += event.text.text.decode('utf-8')
                    resp = self._format_input(resp)
                    self._render(resp, err)

                elif event.type == sdl2.SDL_KEYDOWN:
                    ui_request(event.key.keysym)
                    key = event.key.keysym.sym

                    # If escape pressed, clear all existing input
                    if key == sdl2.SDLK_ESCAPE:
                        resp = ""

                    # If backspace pressed, remove last character
                    elif key == sdl2.SDLK_BACKSPACE:
                        resp = resp[:-1]

                    # If Enter/Return pressed, check the response and either return
                    # if valid or display an error if not
                    elif key in (sdl2.SDLK_KP_ENTER, sdl2.SDLK_RETURN):
                        err = self._validate_response(resp)
                        if not err:
                            sdl2.SDL_StopTextInput()
                            return self._format_response(resp)

                    # Whenever a key is pressed, redraw the screen
                    self._render(resp, err)
                    if err:
                        resp = ""
                        err = None
        

class NumberQuery(Query):
    """Collects a numeric response from the user.

    NumberQueries ensure that the response is a valid number (specifically an
    integer unless ``decimal`` is True) and falls within the allowed range. If
    the user submits a non-numeric or out-of-range response, an error message
    reiterating the response requirements will be shown, prompting the user to
    try again::

        rating_q = NumberQuery(
            "Please enter a number between 1 and 7"
            min=1, max=7
        )
        rating = rating_q.collect()

    Args:
        q (str or list): The text of the query to present to the participant. Can
            be a string or a list of strings.
        min (float, optional): The lowest response allowed. Defaults to 0.
        max (float, optional): The highest response allowed. Defaults to 1000.
        decimal (bool, optional): Whether decimal numbers (e.g. 7.5) should be allowed
            as responses. Defaults to False (integers only).
        allow_blank (bool, optional): Whether blank responses should be allowed.
            Defaults to False.
        style (:obj:`~QueryStyle`, optional): Optional aesthetic overrides defining the
            appearance and location of the query.

    """
    def __init__(self, q, min=0, max=1000, decimal=False, allow_blank=False, style=None):
        super(NumberQuery, self).__init__(q, style)
        self.min = min
        self.max = max
        self.float = decimal
        self.allow_blank = allow_blank
        self._validate_options()

    def collect(self):
        """Presents the query and collects a numeric response.
        
        Returns as soon as a valid response has been submitted.

        Returns:
            The number (int or float) entered by the user.
        
        """
        return super(NumberQuery, self).collect()
        
    def _validate_options(self):
        if self.max < self.min:
            raise ValueError("Maximum value must be larger than minimum value.")
        
    def _format_input(self, s):
        s = s.strip()
        return s
        
    def _validate_response(self, resp):
        err = None
        # If allow null and empty response, accept automatically
        if self.allow_blank and resp == "":
            return None
        # Make sure response is a valid number
        try:
            resp = float(resp) if self.float else int(resp) 
        except ValueError:
            err = "Please respond with a whole number."
            if self.float:
                err = err.replace("whole ", "")
            return err
        # Make sure response is within the specified range
        if resp < self.min or resp > self.max:
            err = "Please respond with a number between {} and {}, inclusive."
            err = err.format(self.min, self.max)
        return err
        
    def _format_response(self, resp):
        if resp == "":
            return None
        elif self.float:
            return float(resp)
        return int(resp)


class ChoiceQuery(Query):
    """Collects a multiple-choice response from the user.

    ChoiceQueries ensure that the response matches one of the possible response
    options, prompting the user to try again they enter an invalid response::

        cond_q = ChoiceQuery(
            "Please enter the condition to use for this participant:",
            choices=["A", "B", "C"], case="upper"
        )
        condition = cond_q.collect()

    ChoiceQueries are not case sensitive, meaning that a response of 'a' will
    still match with (and return) 'A' if it exists as a response option. For
    aesthetic purposes you can enforce that user input is rendered in upper case,
    lower case, or title case, but this will not affect the returned string.

    Args:
        q (str or list): The text of the query to present to the user. Can
            be a string or a list of strings.
        choices (list): The list of possible response options.
        case (str, optional): The case to use when rendering user input, can be
            'upper', 'lower', 'title', or None. Defaults to None.
        style (:obj:`~QueryStyle`, optional): Optional aesthetic overrides defining the
            appearance and location of the query.

    """
    def __init__(self, q, choices, case=None, style=None):
        super(ChoiceQuery, self).__init__(q, style)
        self.choices = choices
        self.case = case
        self._validate_options()

    def collect(self):
        """Presents the query and collects a multiple-choice response.

        Returns as soon as a valid response has been submitted.

        Returns:
            str: The choice entered by the user.
        
        """
        return super(ChoiceQuery, self).collect()

    def _validate_options(self):
        # Make sure at least two response options and convert to strings if necessary
        if not iterable(self.choices) or len(self.choices) < 2:
            e = "Choice queries must have at least two response options."
            raise RuntimeError(e)
        # Ensure case is a valid value
        if self.case and self.case not in ['lower', 'upper', 'title']:
            e = "Query case must be either 'lower', 'upper', 'title', or None."
            raise RuntimeError(e)
        self.choices = [str(choice) for choice in self.choices]

    def _format_input(self, s):
        s = s.lstrip().strip("\n")
        if self.case == 'upper':
            s = s.upper()
        elif self.case == 'lower':
            s = s.lower()
        elif self.case == 'title':
            s = s.title()
        return s

    def _validate_response(self, resp):
        err = None
        # Check if response matches a valid option
        if resp.lower() not in [c.lower() for c in self.choices]:
            opts = pretty_list(self.choices)
            err = "Please respond with one of the following options: " + opts
        return err

    def _format_response(self, resp):
        # Always return chosen option exactly, ignoring case of response
        for choice in self.choices:
            if choice.lower() == resp.lower():
                resp = choice
        return resp


class TextQuery(Query):
    """Collects a free-form text response from the user.

    TextQueries provide minimal restrictions on user responses, ensuring only
    that the response is between the minimum and maximum character count. If the
    minimum character count is 0, then empty responses will be allowed::

        seq_q = TextQuery(
            "If you feel like you learned a sequence, please enter it now:",
            min_length=0, max_length=10, case='upper'
        )
        sequence = seq_q.collect()


    For aesthetic or input normalization purposes, you can specify the case of the
    response (lower case, upper case, or title case). If specified, all input will
    be rendered and returned in that case.

    Args:
        q (str or list): The text of the query to present to the user. Can
            be a string or a list of strings.
        min_length (int, optional): The minimum character count. Defaults to 1.
        max_length (int, optional): The maximum character count. Defaults to 50.
        case (str, optional): The case to use when formatting the user input. Can be
            'upper', 'lower', 'title', or None.
        password (bool, optional): If True, user input will be rendered as asterisks
            for the purpose of privacy. Defaults to False.
        style (:obj:`~QueryStyle`, optional): Optional aesthetic overrides defining the
            appearance and location of the query.

    """
    def __init__(
            self, q, min_length=1, max_length=50, case=None, password=False, style=None
        ):
        super(TextQuery, self).__init__(q, style)
        self.min_l = min_length
        self.max_l = max_length
        self.case = case
        self.password = password
        self._validate_options()

    def collect(self):
        """Presents the query and collects a freeform text response.
        
        Returns as soon as a valid response has been submitted.

        Returns:
            str: The response entered by the user.
        
        """
        return super(TextQuery, self).collect()
        
    def _validate_options(self):
        if self.min_l > self.max_l:
            raise ValueError("Maximum response length must be larger than the minimum.")
        if self.case and self.case not in ['lower', 'upper', 'title']:
            e = "Query case must be either 'lower', 'upper', 'title', or None."
            raise RuntimeError(e)
        
    def _format_input(self, s):
        s = s.lstrip().strip("\n")
        if self.case == 'upper':
            s = s.upper()
        elif self.case == 'lower':
            s = s.lower()
        elif self.case == 'title':
            s = s.title()
        return s
        
    def _validate_response(self, resp):
        err = None
        # Check if response is too long or short
        if self.min_l == self.max_l and len(resp) != self.min_l:
            err = "Your response must be {} characters long.".format(self.min_l)
        elif len(resp) < self.min_l or len(resp) > self.max_l:
            err = "Your response must be between {} and {} characters long."
            err = err.format(self.min_l, self.max_l)
        return err
        
    def _format_response(self, resp):
        if self.case == 'upper':
            resp = resp.upper()
        elif self.case == 'lower':
            resp = resp.lower()
        elif self.case == 'title':
            resp = resp.title()
        return resp
