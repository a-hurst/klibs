import klibs

__author__ = "EXPERIMENTER_NAME"

from klibs import Params

class PROJECT_NAME(klibs.Experiment):

	def __init__(self, *args, **kwargs):
		super(PROJECT_NAME, self).__init__(*args, **kwargs)

	def setup(self):
		Params.key_maps['PROJECT_NAME_response'] = klibs.KeyMap('PROJECT_NAME_response', [], [], [])

	def block(self, block_num):
		pass

	def setup_response_collector(self, trial_factors):
		pass

	def trial_prep(self, trial_factors):
		pass

	def trial(self, trial_factors):

		return {
			"block_num": Params.block_number,
			"trial_num": Params.trial_number
		}

	def trial_clean_up(self, trial_id, trial_factors):
		pass

	def clean_up(self):
		pass
