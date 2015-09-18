__author__ = "EXPERIMENTER_NAME"

import klibs
from klibs import Params

"""
 Below are some commonly required additional libraries; uncomment as needed.

""" 
# import os
# import time
# from PIL import Image
# import sdl2
# import sdl2.ext
# import numpy
# import math
# import aggdraw
# import random

Params.default_fill_color = (100, 100, 100, 255)

Params.debug_level = 0
Params.collect_demographics = False
Params.practicing = True
Params.eye_tracking = True
Params.eye_tracker_available = False

Params.blocks_per_experiment = 2
Params.trials_per_block = 5
Params.practice_blocks_per_experiment = 3
Params.trials_per_practice_block = 3


class PROJECT_NAME(klibs.App):

	def __init__(self, *args, **kwargs):
		super(PROJECT_NAME, self).__init__(*args, **kwargs)

	def setup(self):
		Params.key_maps['PROJECT_NAME_response'] = klibs.KeyMap('PROJECT_NAME_response', [], [], [])

	def block(self, block_num):
		pass

	def trial_prep(self, *args, **kwargs):
		self.db.init_entry('trials')

	def trial(self, trial_factors, trial_num):

		return {}

	def trial_clean_up(self, *args, **kwargs):
		pass

	def clean_up(self):
		pass

app = PROJECT_NAME("PROJECT_NAME").run()
