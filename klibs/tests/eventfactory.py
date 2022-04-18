"""Functions for simulating various SDL2 input events."""
import sdl2
from ctypes import byref


# Helper functions

def _mousebutton_flag(button):
    buttons = {
        'left': sdl2.SDL_BUTTON_LEFT,
        'right': sdl2.SDL_BUTTON_RIGHT,
        'middle': sdl2.SDL_BUTTON_MIDDLE
    }
    if not button in buttons.keys():
        raise ValueError("'{0}' is not a valid mouse button.".format(str(key)))
    return buttons[button]

def _keysym_attrs(key, mod=None):

    if type(key) is str:
        keycode = sdl2.SDL_GetKeyFromName(key.encode('utf8'))
        if keycode == 0:
            raise ValueError("'{0}' is not a recognized key name.".format(key))
    else:
        keycode = key

    mods = {
        'ctrl': sdl2.KMOD_CTRL, 'shift': sdl2.KMOD_SHIFT,
        'alt': sdl2.KMOD_ALT, 'meta': sdl2.KMOD_GUI
    }
    if mod:
        if type(mod) is str and mod in mods.keys():
            modval = mods[mod]
        elif type(mod) is int:
            modval = mod
        else:
            raise ValueError("'mod' must be a string or int.")
    else:
        modval = 0

    return (keycode, modval)


# SDL_Event simulation functions

def keydown(key, mod = None):
    keycode, modval = _keysym_attrs(key, mod)
    e = sdl2.SDL_Event()
    e.type = sdl2.SDL_KEYDOWN
    e.key.type = sdl2.SDL_KEYDOWN
    e.key.keysym.sym = keycode
    e.key.keysym.mod = modval
    return e

def keyup(key, mod = None):
    keycode, modval = _keysym_attrs(key, mod)
    e = sdl2.SDL_Event()
    e.type = sdl2.SDL_KEYUP
    e.key.type = sdl2.SDL_KEYUP
    e.key.keysym.sym = keycode
    e.key.keysym.mod = modval
    return e

def click(button = 'right', loc = (0, 0), release = False):
    etype = sdl2.SDL_MOUSEBUTTONUP if release else sdl2.SDL_MOUSEBUTTONDOWN
    e = sdl2.SDL_Event()
    e.type = etype
    e.button.type = etype
    e.button.x, e.button.y = loc
    e.button.button = _mousebutton_flag(button)
    return e

def textinput(char):
    e = sdl2.SDL_Event()
    e.type = sdl2.SDL_TEXTINPUT
    e.text.type = sdl2.SDL_TEXTINPUT
    e.text.text = char.encode('utf-8')
    return e

def queue_event(e):
    ret = sdl2.SDL_PushEvent(byref(e))
    if ret != 1:
        raise ValueError("Unable to add event to queue.")
