import time
import thread

try:
	import parallel
	PARRALELL_AVAILABLE = True

	class EEG(object):
		def __init__(self):
			self.p =  parallel.Parallel()

		def threaded(self, func):
			@wraps(func)
			def wrapper(*args, **kwargs):
				thread.start_new_thread(func, *args, **kwargs)
				return wrapper

		@threaded
		def send_code(self, code):
				self.p.setData(code)  # send the event code
				time.sleep(0.006)  # sleep 6 ms
				self.p.setData(0)  # send a code to clear the register
				time.sleep(0.01)  # sleep 10 ms
except:
	PARRALELL_AVAILABLE = False
	print "Warning: Parallel library not found; EEG messaging will not be available."
