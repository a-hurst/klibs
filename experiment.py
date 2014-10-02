__author__ = 'jono'
import klibs

def pr(strng):
	print strng
# el 	= klibs.EyeLink(True)

class RSVP(klibs.App):

	def setup(self):
		return True

	def block(self, block_num):
		return True

	def refresh_screen(self):
		return True

	def trial_prep(self):
		return True

	def trial(self, trial_num):
		return True

	def trial_clean_up(self):
		return True

	def cleanUp(self):
		return True

app = RSVP()
