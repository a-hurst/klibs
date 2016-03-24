__author__ = 'jono'


import time
import ctypes
import sdl2

import multiprocessing
global process_pool
global process_queue

from multiprocessing import Process, Queue, Pool



# process_pool = Pool(multiprocessing.cpu_count())
process_queue = multiprocessing.Queue()


def threaded(func, *args, **kwargs):
	# global process_pool
	# global process_queue
	# process_pool.apply_async(func, args, kwargs)
	# Process(target=func, args=args, kwargs=kwargs)

	def threaded_func(*args, **kwargs):
		time.sleep(0.2)
		Process(target=func, args=[process_queue]).start()
		# global process_queue
		# global process_pool
		# kwargs['queue'] = process_queue
		# process_pool.apply_async(func, args, kwargs)
		# # p.start()
		# return p

	return threaded_func

def pump(get_events=False):  # a silly wrapper because Jon always forgets the sdl2 call
	process_queue.put(["just", "testing"])
	now = time.time()
	# while process_queue.empty():
	# 	if time.time() - now > 3:
	# 		exit()
	# 	pass
	print process_queue.get()
	print process_queue.get_nowait()
	print process_queue.get_nowait()
		# ev = sdl2.SDL_Event()
		# ev.user.code = sdl2.SDL_RegisterEvents(1)
		# print "CODE: {0}".format(ev.user.code)
		# code = ctypes.create_string_buffer(e[1])
		# ev.user.data1 = ctypes.c_void_p(id("hi mom"))
		# success = sdl2.SDL_PushEvent(ev)
		# if success == 0:
		# 	print sdl2.SDL_GetError()
		# 	exit()
	# sdl2.SDL_PumpEvents()
	# if get_events:
	# 	return sdl2.ext.get_events()


@threaded
def thread_test(queue):
	queue.put_nowait(['MAHVENTS', "MAHVENTDATAZ"])
	queue.put_nowait(['MAHVENTZ', "MAHVENTDATAS"])

# sdl2.SDL_FlushEvents(sdl2.SDL_FIRSTEVENT, sdl2.SDL_LASTEVENT)

thread_test()
# Process(target=thread_test, args=[process_queue]).start()
# time.sleep(2)
pump(True)
# eq = pump(True)
# for e in eq:
# 	print e.type
# exit()