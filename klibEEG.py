import parallel, thread, time
from functools import wraps

P = parallel.Parallel()


def threaded(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread.start_new_thread(func, *args, **kwargs)
    return wrapper

@threaded
def send_code(code):
            P.setData(code)  # send the event code
            time.sleep(0.006)  # sleep 6 ms
            P.setData(0)  # send a code to clear the register
            time.sleep(0.01)  # sleep 10 ms
