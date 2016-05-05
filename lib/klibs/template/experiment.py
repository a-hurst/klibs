import klibs

__author__ = "EXPERIMENTER_NAME"

from klibs import Params

class PROJECT_NAME(klibs.Experiment):

	def __init__(self, *args, **kwargs):
		super(PROJECT_NAME, self).__init__(*args, **kwargs)

	def setup(self):
		Params.key_maps['PROJECT_NAME_response'] = klibs.KeyMap('PROJECT_NAME_response', [], [], [])

	def block(self):
		pass

	def setup_response_collector(self):
		pass

	def trial_prep(self):
		pass

	def trial(self):

		return {
			"block_num": Params.block_number,
			"trial_num": Params.trial_number
		}

	def trial_clean_up(self):
		pass

	def clean_up(self):
		pass
