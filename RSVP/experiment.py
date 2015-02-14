__author__ = 'jono'
import klibs
from klibs import Params
import time
from PIL import Image
import sdl2
import sdl2.ext
import numpy
import math
import aggdraw
import random
from copy import copy

import resource


A = "A"
C = "C"
B = "B"
D = "D"
E = "E"
F = "F"
G = "G"
H = "H"
I = "I"
J = "J"
K = "K"
L = "L"
M = "M"
N = "N"
O = "O"
P = "P"
Q = "Q"
R = "R"
S = "S"
T = "T"
U = "U"
V = "V"
W = "W"
X = "X"
Y = "Y"
Z = "Z"

PI = math.pi
LEFT_STREAM = 0
LEFT_STREAM_STR = "LEFT"
RIGHT_STREAM = 1
RIGHT_STREAM_STR = "RIGHT"

RESP_UI_LABELS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
RESP_DATA_LABELS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
# RESP_KEYSYMS = [sdl2.SDLK_KP_0, sdl2.SDLK_KP_1, sdl2.SDLK_KP_2, sdl2.SDLK_KP_3, sdl2.SDLK_KP_4, sdl2.SDLK_KP_5,
# 				sdl2.SDLK_KP_6, sdl2.SDLK_KP_7, sdl2.SDLK_KP_8, sdl2.SDLK_KP_9]
RESP_KEYSYMS = [sdl2.SDLK_0, sdl2.SDLK_1, sdl2.SDLK_2, sdl2.SDLK_3, sdl2.SDLK_4, sdl2.SDLK_5,
				sdl2.SDLK_6, sdl2.SDLK_7, sdl2.SDLK_8, sdl2.SDLK_9]
CENTER_BOX = "center_box"
NA = "NA"

Params.screen_x = 1024
Params.screen_y = 768
Params.default_fill_color = (125, 125, 125, 255)

Params.collect_demographics = True
Params.practicing = False
Params.give_feedback = True
Params.eye_tracking = True
Params.eye_tracker_available = True
Params.instructions = False
# Params.trials = 200
Params.blocks_per_experiment = 1
Params.trials_per_block = 224
Params.practice_blocks = 0
Params.trials_per_practice_block = 0
Params.exp_meta_factors = {}
Params.exp_factors = [("target_stream", [LEFT_STREAM, RIGHT_STREAM]),
						("target_frame", [5, 6, 7, 8, 9, 10, 11]),
						("target_digit", ["2", "3", "4", "5", "6", "7", "8", "9"]),
						("cued_stream", [LEFT_STREAM, RIGHT_STREAM])]

Params.practice_block_mask = [True, True, False, True]


class RSVP(klibs.Experiment):
	frame_rate = 0.16  # ms
	relative_box_width = 1.5  # degrees of visual angle
	relative_box_spacing = 2.2
	relative_font_size = 0.7
	box_width = None  # px
	box_spacing = None
	font_size = None
	stream_chars = [A, C, D, E, F, G, H, J, K, L, M, M, N, P, Q, R, S, T, U, V, W, X, Y, Z]

	# drawing & graphics Params
	white = (255, 255, 255, 255)
	box_pen = None  # ie. the aggdraw pen to draw the location boxes with, assigned in setup
	box_stroke_width = 2  # px
	cued_box_stroke_width = None  # set to double box_stroke_width in setup
	box = None

	# trial vars
	left_stream_chars = []
	right_stream_chars = []
	left_boxes = []
	right_boxes = []
	center_box = None
	frames_shown = 0
	frame_start = 0
	response_string = "Presented digit?"

	def __init__(self, *args, **kwargs):
		print resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
		klibs.Experiment.__init__(self, *args, **kwargs)

	def setup(self):
		print resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
		Params.key_maps['rsvp_response'] = klibs.KeyMap('rsvp_response', RESP_UI_LABELS, RESP_KEYSYMS, RESP_DATA_LABELS)
		self.cued_box_stroke_width = 4 * self.box_stroke_width
		self.box_pen = aggdraw.Pen(self.white, self.box_stroke_width)
		self.cued_box_pen = aggdraw.Pen(self.white, self.cued_box_stroke_width)
		self.box_width = klibs.deg_to_px(self.relative_box_width)
		self.box_spacing = klibs.deg_to_px(self.relative_box_spacing)
		self.box_bounds = self.box_width + self.cued_box_stroke_width
		self.font_size = klibs.deg_to_px(self.relative_font_size)
		self.left_box_loc = (Params.screen_c[0] - ((1.5 * self.box_width) + self.box_spacing), Params.screen_c[1])
		self.right_box_loc = (Params.screen_c[0] + ((0.5 * self.box_width) + self.box_spacing), Params.screen_c[1])
		center_upper_left = [Params.screen_c[0] - self.box_width // 2, Params.screen_c[1] - self.box_width // 2]
		center_lower_right = [Params.screen_c[0] + self.box_width // 2, Params.screen_c[1] + self.box_width // 2]
		print Params.collect_demographics
		if Params.collect_demographics:
			self.collect_demographics()
		self.eyelink.add_gaze_boundary(CENTER_BOX, [center_upper_left, center_lower_right])
		self.eyelink.setup()

	def block(self, block_num):
		pass

	def trial_prep(self, *args, **kwargs):
		self.database.init_entry('trials')

		left_stream_chars = copy(self.stream_chars)
		right_stream_chars = copy(self.stream_chars)
		random.shuffle(left_stream_chars)
		random.shuffle(right_stream_chars)
		self.left_stream_chars = []
		self.right_stream_chars = []
		last_left_char = None
		for i in range(0, 15):
			klibs.pump()
			right_char_chosen = False
			left_stream_char = left_stream_chars.pop()
			self.left_stream_chars.append(left_stream_char)
			while not right_char_chosen:
				right_stream_char = right_stream_chars.pop()
				if right_stream_char in (left_stream_char, last_left_char):
					right_stream_chars.append(right_stream_char)
					random.shuffle(right_stream_chars)
				else:
					right_char_chosen = True
					last_left_char = left_stream_char
					self.right_stream_chars.append(right_stream_char)

		self.drift_correct()
		self.left_boxes = []
		self.right_boxes = []
		self.center_box = self.box_surface()
		self.frames_shown = 0
		self.frame_start = time.time()

	def trial(self, trial_factors, trial_num):
		print resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
		self.eyelink.start(trial_num)
		target_stream = trial_factors[1]
		target_frame = trial_factors[2]
		target_digit = trial_factors[3]
		cued_stream = trial_factors[4]

		for i in range(0, 15):
			right_box = self.box_surface(self.right_stream_chars.pop())
			left_box = self.box_surface(self.left_stream_chars.pop())
			if target_frame == i:
				if target_stream == LEFT_STREAM:
					left_stream_char = target_digit
					left_box = self.box_surface(left_stream_char, True)
				else:
					right_stream_char = target_digit
					right_box = self.box_surface(right_stream_char, True)
			self.left_boxes.append(left_box)
			self.right_boxes.append(right_box)

		in_bounds = True
		while in_bounds and self.frames_shown < 15:
			in_bounds = self.eyelink.within_boundary(CENTER_BOX)
			if time.time() - self.frame_start >= self.frame_rate:
				klibs.pump()
				self.frame_start = time.time()
				self.fill()
				self.blit(self.left_boxes.pop(), 4, self.left_box_loc)
				self.blit(self.right_boxes.pop(), 4, self.right_box_loc)
				self.blit(self.center_box, 5, Params.screen_c)
				self.flip()
				self.frames_shown += 1
		if in_bounds is True:
			self.fill()
			self.message(self.response_string, font_size="48pt", color=self.white, location="center")
			response = self.listen(klibs.MAX_WAIT, "rsvp_response")
		else:
			self.fill()
			self.message("Eye movement out of bounds!", color=(255, 0, 0, 255), location="center", flip=True)
			time.sleep(1)
			response = [NA, -1]

		if response[0] == NA:
			response_correct = NA
		else:
			response_correct = "true" if response[0] == target_digit else "false"
			if Params.give_feedback:
				self.fill()
				if response_correct == "true":
					self.message("Correct!", color=(0, 255, 0, 255), location="center")
				else:
					self.message("Answer was: {0}".format(target_digit), color=(255, 0, 0, 255), location="center")
				self.listen(1)

		return {
			"trial_num": self.trial_number,
			"block_num": self.block_number,
			"cued_stream": LEFT_STREAM_STR if cued_stream == LEFT_STREAM else RIGHT_STREAM_STR,
			"target_stream": LEFT_STREAM_STR if target_stream == LEFT_STREAM else RIGHT_STREAM_STR,
			"target_digit": target_digit,
			"target_frame": str(target_frame),
			"response": response[0],
			"response_correct": response_correct,
			"response_time": response[1]
		}

	def box_loop(self):

		return self.box_loop() if self.frames_shown < 15 else True

	def trial_clean_up(self, *args, **kwargs):
		pass

	def clean_up(self):
		pass

	def box_surface(self, char=None, cue_box=False):
		draw_context = aggdraw.Draw("RGBA", (self.box_bounds, self.box_bounds), (0,0,0,0) )
		pen = self.box_pen if cue_box is False else self.cued_box_pen
		draw_context.rectangle((self.cued_box_stroke_width, self.box_width, self.box_width,
								self.cued_box_stroke_width), pen)
		draw_context_bytes = Image.frombytes(draw_context.mode, draw_context.size, draw_context.tostring())
		if char:
			char_surf = self.text_layer.render_text(char, "Arial", self.font_size, self.white)
			box_surf = klibs.NumpySurface(numpy.asarray(draw_context_bytes))
			box_surf.blit(char_surf, registration=5, position="center")
			return box_surf
		else:
			return klibs.NumpySurface(numpy.asarray(draw_context_bytes))

print resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
app = RSVP('rsvp_replication').run ()  # use me to run participants
# app = RSVP('rsvp_replication').database.export()  # use me to export your dataz
