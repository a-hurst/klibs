# -*- coding: utf-8 -*-
__author__ = 'j. mulle, this.impetus@gmail.com'

print "\n\n\033[92m*** Now loading KLIBS Environment ***\033[0m"
print "\033[32m(Note: if a bunch of SDL errors were just reported, this was expected, do not be alarmed!)\033[0m"
import logging

import KLNamedObject
import KLEnvironment as env
import KLExceptions
import KLConstants
from KLConstants import PYAUDIO_AVAILABLE, PYLINK_AVAILABLE
import KLParams as P						# KLConstants
import KLKeyMap								# KLConstants
import KLLabJack							# KLParams
import KLUtilities							# KLConstants, KLParams
import KLTrialFactory						# KLConstants, KLParams
import KLUserInterface						# KLConstants, KLParams, KLUtilities
import KLDatabase							# KLConstants, KLParams, KLUtilities
import KLTime							# KLConstants, KLParams, KLUtilities

import KLEventInterface						# KLConstants, KLParams, KLUtilities, KLUserInterface
import KLGraphics							# KLConstants, KLParams, KLUtilities
import KLDebug								# KLParams, KLGraphics
import KLBoundary							# KLConstants, KLUtilities, KLExceptions
import KLText						# KLUtilities, KLGraphics
import KLAudio								# KLConstants, KLParams, KLUtilities, KLGraphics
import KLResponseCollectors					# KLConstants, KLParams, KLUtilities, KLUserInterface, KLBoundary, KLAudio
import KLEyeLink
import KLCommunication
import KLEnvironment

try:
	# if additional classes have been defined at ExpAssets/Resources/code, load them
	import sys
	import os
	from imp import load_source
	from inspect import isclass
	sys.path.append(P.code_dir)
	for f in os.listdir(P.code_dir):
		if f[-3:] != ".py":
			if f[-3:] == ".pyc":
				os.remove( os.path.join(P.code_dir, f) )
			continue
		for k, v in load_source("*", os.path.join(P.code_dir, f)).__dict__.iteritems():
			if isclass(k):
				import k
except OSError:
	pass

from klibs.KLExperiment import Experiment

klog = logging.Logger()
#####################################################
#
# SDL Keycode Reference for creating KeyMaps (https://wiki.libsdl.org/SDL_Keycode)
#
# 2 = SDLK_2
# 3 = SDLK_3
# 4 = SDLK_4
# 5 = SDLK_5
# 6 = SDLK_6
# 7 = SDLK_7
# 8 = SDLK_8
# 9 = SDLK_9
# A = SDLK_a
# B = SDLK_b
# AC Back (the Back key (application control keypad)) = SDLK_AC_BACK
# AC Bookmarks (the Bookmarks key (application control keypad)) = SDLK_AC_BOOKMARKS
# AC Forward (the Forward key (application control keypad)) = SDLK_AC_FORWARD
# AC Home (the Home key (application control keypad)) = SDLK_AC_HOME
# AC Refresh (the Refresh key (application control keypad)) = SDLK_AC_REFRESH
# AC Search (the Search key (application control keypad)) = SDLK_AC_SEARCH
# AC Stop (the Stop key (application control keypad)) = SDLK_AC_STOP
# Again (the Again key (Redo)) = SDLK_AGAIN
# AltErase (Erase-Eaze) = SDLK_ALTERASE
# " = SDLK_QUOTE
# Application (the Application / Compose / Context Menu (Windows) key ) = SDLK_APPLICATION
# AudioMute (the Mute volume key) = SDLK_AUDIOMUTE
# AudioNext (the Next Track media key) = SDLK_AUDIONEXT
# AudioPlay (the Play media key) = SDLK_AUDIOPLAY
# AudioPrev (the Previous Track media key) = SDLK_AUDIOPREV
# AudioStop (the Stop media key) = SDLK_AUDIOSTOP
# \ (Located at the lower left of the return key on ISO keyboards and at the right end of the QWERTY row on ANSI keyboards. Produces REVERSE SOLIDUS (backslash) and VERTICAL LINE in a US layout, REVERSE SOLIDUS and VERTICAL LINE in a UK Mac layout, NUMBER SIGN and TILDE in a UK Windows layout, DOLLAR SIGN and POUND SIGN in a Swiss German layout, NUMBER SIGN and APOSTROPHE in a German layout, GRAVE ACCENT and POUND SIGN in a French Mac layout, and ASTERISK and MICRO SIGN in a French Windows layout.) = SDLK_BACKSLASH
# Backspace = SDLK_BACKSPACE
# BrightnessDown (the Brightness Down key) = SDLK_BRIGHTNESSDOWN
# BrightnessUp (the Brightness Up key) = SDLK_BRIGHTNESSUP
# C = SDLK_c
# Calculator (the Calculator key) = SDLK_CALCULATOR
# Cancel = SDLK_CANCEL
# CapsLock = SDLK_CAPSLOCK
# Clear = SDLK_CLEAR
# Clear / Again = SDLK_CLEARAGAIN
# , = SDLK_COMMA
# Computer (the My Computer key) = SDLK_COMPUTER
# Copy = SDLK_COPY
# CrSel = SDLK_CRSEL
# CurrencySubUnit (the Currency Subunit key) = SDLK_CURRENCYSUBUNIT
# CurrencyUnit (the Currency Unit key) = SDLK_CURRENCYUNIT
# Cut = SDLK_CUT
# D = SDLK_d
# DecimalSeparator (the Decimal Separator key) = SDLK_DECIMALSEPARATOR
# Delete = SDLK_DELETE
# DisplaySwitch (display mirroring/dual display switch, video mode switch) = SDLK_DISPLAYSWITCH
# Down (the Down arrow key (navigation keypad)) = SDLK_DOWN
# E = SDLK_e
# Eject (the Eject key) = SDLK_EJECT
# End = SDLK_END
# = = SDLK_EQUALS
# Escape (the Esc key) = SDLK_ESCAPE
# Execute = SDLK_EXECUTE
# ExSel = SDLK_EXSEL
# F = SDLK_f
# F1 = SDLK_F1
# F10 = SDLK_F10
# F11 = SDLK_F11
# F12 = SDLK_F12
# F13 = SDLK_F13
# F14 = SDLK_F14
# F15 = SDLK_F15
# F16 = SDLK_F16
# F17 = SDLK_F17
# F18 = SDLK_F18
# F19 = SDLK_F19
# F2 = SDLK_F2
# F20 = SDLK_F20
# F21 = SDLK_F21
# F22 = SDLK_F22
# F23 = SDLK_F23
# F24 = SDLK_F24
# F3 = SDLK_F3
# F4 = SDLK_F4
# F5 = SDLK_F5
# F6 = SDLK_F6
# F7 = SDLK_F7
# F8 = SDLK_F8
# F9 = SDLK_F9
# Find = SDLK_FIND
# G = SDLK_g
# ` = SDLK_BACKQUOTE
# H = SDLK_h
# Help = SDLK_HELP
# Home = SDLK_HOME
# I = SDLK_i
# Insert (insert on PC, help on some Mac keyboards (but does send code 73, not 117)) = SDLK_INSERT
# J = SDLK_j
# K = SDLK_k
# KBDIllumDown (the Keyboard Illumination Down key) = SDLK_KBDILLUMDOWN
# KBDIllumToggle (the Keyboard Illumination Toggle key) = SDLK_KBDILLUMTOGGLE
# KBDIllumUp (the Keyboard Illumination Up key) = SDLK_KBDILLUMUP
# Keypad 0 (the 0 key (numeric keypad)) = SDLK_KP_0
# Keypad 00 (the 00 key (numeric keypad)) = SDLK_KP_00
# Keypad 000 (the 000 key (numeric keypad)) = SDLK_KP_000
# Keypad 1 (the 1 key (numeric keypad)) = SDLK_KP_1
# Keypad 2 (the 2 key (numeric keypad)) = SDLK_KP_2
# Keypad 3 (the 3 key (numeric keypad)) = SDLK_KP_3
# Keypad 4 (the 4 key (numeric keypad)) = SDLK_KP_4
# Keypad 5 (the 5 key (numeric keypad)) = SDLK_KP_5
# Keypad 6 (the 6 key (numeric keypad)) = SDLK_KP_6
# Keypad 7 (the 7 key (numeric keypad)) = SDLK_KP_7
# Keypad 8 (the 8 key (numeric keypad)) = SDLK_KP_8
# Keypad 9 (the 9 key (numeric keypad)) = SDLK_KP_9
# Keypad A (the A key (numeric keypad)) = SDLK_KP_A
# Keypad & (the & key (numeric keypad)) = SDLK_KP_AMPERSAND
# Keypad @ (the @ key (numeric keypad)) = SDLK_KP_AT
# Keypad B (the B key (numeric keypad)) = SDLK_KP_B
# Keypad Backspace (the Backspace key (numeric keypad)) = SDLK_KP_BACKSPACE
# Keypad Binary (the Binary key (numeric keypad)) = SDLK_KP_BINARY
# Keypad C (the C key (numeric keypad)) = SDLK_KP_C
# Keypad Clear (the Clear key (numeric keypad)) = SDLK_KP_CLEAR
# Keypad ClearEntry (the Clear Entry key (numeric keypad)) = SDLK_KP_CLEARENTRY
# Keypad : (the : key (numeric keypad)) = SDLK_KP_COLON
# Keypad , (the Comma key (numeric keypad)) = SDLK_KP_COMMA
# Keypad D (the D key (numeric keypad)) = SDLK_KP_D
# Keypad && (the && key (numeric keypad)) = SDLK_KP_DBLAMPERSAND
# Keypad || (the || key (numeric keypad)) = SDLK_KP_DBLVERTICALBAR
# Keypad Decimal (the Decimal key (numeric keypad)) = SDLK_KP_DECIMAL
# Keypad / (the / key (numeric keypad)) = SDLK_KP_DIVIDE
# Keypad E (the E key (numeric keypad)) = SDLK_KP_E
# Keypad Enter (the Enter key (numeric keypad)) = SDLK_KP_ENTER
# Keypad = (the = key (numeric keypad)) = SDLK_KP_EQUALS
# Keypad = (AS400) (the Equals AS400 key (numeric keypad)) = SDLK_KP_EQUALSAS400
# Keypad ! (the ! key (numeric keypad)) = SDLK_KP_EXCLAM
# Keypad F (the F key (numeric keypad)) = SDLK_KP_F
# Keypad < (the Greater key (numeric keypad)) = SDLK_KP_GREATER
# Keypad # (the # key (numeric keypad)) = SDLK_KP_HASH
# Keypad Hexadecimal (the Hexadecimal key (numeric keypad)) = SDLK_KP_HEXADECIMAL
# Keypad { (the Left Brace key (numeric keypad)) = SDLK_KP_LEFTBRACE
# Keypad ( (the Left Parenthesis key (numeric keypad)) = SDLK_KP_LEFTPAREN
# Keypad > (the Less key (numeric keypad)) = SDLK_KP_LESS
# Keypad MemAdd (the Mem Add key (numeric keypad)) = SDLK_KP_MEMADD
# Keypad MemClear (the Mem Clear key (numeric keypad)) = SDLK_KP_MEMCLEAR
# Keypad MemDivide (the Mem Divide key (numeric keypad)) = SDLK_KP_MEMDIVIDE
# Keypad MemMultiply (the Mem Multiply key (numeric keypad)) = SDLK_KP_MEMMULTIPLY
# Keypad MemRecall (the Mem Recall key (numeric keypad)) = SDLK_KP_MEMRECALL
# Keypad MemStore (the Mem Store key (numeric keypad)) = SDLK_KP_MEMSTORE
# Keypad MemSubtract (the Mem Subtract key (numeric keypad)) = SDLK_KP_MEMSUBTRACT
# Keypad - (the - key (numeric keypad)) = SDLK_KP_MINUS
# Keypad * (the * key (numeric keypad)) = SDLK_KP_MULTIPLY
# Keypad Octal (the Octal key (numeric keypad)) = SDLK_KP_OCTAL
# Keypad % (the Percent key (numeric keypad)) = SDLK_KP_PERCENT
# Keypad . (the . key (numeric keypad)) = SDLK_KP_PERIOD
# Keypad + (the + key (numeric keypad)) = SDLK_KP_PLUS
# Keypad +/- (the +/- key (numeric keypad)) = SDLK_KP_PLUSMINUS
# Keypad ^ (the Power key (numeric keypad)) = SDLK_KP_POWER
# Keypad } (the Right Brace key (numeric keypad)) = SDLK_KP_RIGHTBRACE
# Keypad ) (the Right Parenthesis key (numeric keypad)) = SDLK_KP_RIGHTPAREN
# Keypad Space (the Space key (numeric keypad)) = SDLK_KP_SPACE
# Keypad Tab (the Tab key (numeric keypad)) = SDLK_KP_TAB
# Keypad | (the | key (numeric keypad)) = SDLK_KP_VERTICALBAR
# Keypad XOR (the XOR key (numeric keypad)) = SDLK_KP_XOR
# L = SDLK_l
# Left Alt (alt, option) = SDLK_LALT
# Left Ctrl = SDLK_LCTRL
# Left (the Left arrow key (navigation keypad)) = SDLK_LEFT
# [ = SDLK_LEFTBRACKET
# Left GUI (windows, command (apple), meta) = SDLK_LGUI
# Left Shift = SDLK_LSHIFT
# M = SDLK_m
# Mail (the Mail/eMail key) = SDLK_MAIL
# MediaSelect (the Media Select key) = SDLK_MEDIASELECT
# Menu = SDLK_MENU
# - = SDLK_MINUS
# Mute = SDLK_MUTE
# N = SDLK_n
# Numlock (the Num Lock key (PC) / the Clear key (Mac)) = SDLK_NUMLOCKCLEAR
# O = SDLK_o
# Oper = SDLK_OPER
# Out = SDLK_OUT
# P = SDLK_p
# PageDown = SDLK_PAGEDOWN
# PageUp = SDLK_PAGEUP
# Paste = SDLK_PASTE
# Pause (the Pause / Break key) = SDLK_PAUSE
# . = SDLK_PERIOD
# Power (The USB document says this is a status flag, not a physical key - but some Mac keyboards do have a power key.) = SDLK_POWER
# PrintScreen = SDLK_PRINTSCREEN
# Prior = SDLK_PRIOR
# Q = SDLK_q
# R = SDLK_r
# Right Alt (alt gr, option) = SDLK_RALT
# Right Ctrl = SDLK_RCTRL
# Return (the Enter key (main keyboard)) = SDLK_RETURN
# Return = SDLK_RETURN2
# Right GUI (windows, command (apple), meta) = SDLK_RGUI
# Right (the Right arrow key (navigation keypad)) = SDLK_RIGHT
# ] = SDLK_RIGHTBRACKET
# Right Shift = SDLK_RSHIFT
# S = SDLK_s
# ScrollLock = SDLK_SCROLLLOCK
# Select = SDLK_SELECT
# ; = SDLK_SEMICOLON
# Separator = SDLK_SEPARATOR
# / = SDLK_SLASH
# Sleep (the Sleep key) = SDLK_SLEEP
# Space (the Space Bar key(s)) = SDLK_SPACE
# Stop = SDLK_STOP
# SysReq (the SysReq key) = SDLK_SYSREQ
# T = SDLK_t
# Tab (the Tab key) = SDLK_TAB
# ThousandsSeparator (the Thousands Separator key) = SDLK_THOUSANDSSEPARATOR
# U = SDLK_u
# Undo = SDLK_UNDO
# Up (the Up arrow key (navigation keypad)) = SDLK_UP
# V = SDLK_v
# VolumeDown = SDLK_VOLUMEDOWN
# VolumeUp = SDLK_VOLUMEUP
# W = SDLK_w
# WWW (the WWW/World Wide Web key) = SDLK_WWW
# X = SDLK_x
# Y = SDLK_y
# Z = SDLK_z

#===================== SDL2 event codes
#
# SDL_FIRSTEVENT => 0
# SDL_QUIT => 256
# SDL_APP_TERMINATING => 257
# SDL_APP_LOWMEMORY => 258
# SDL_APP_WILLENTERBACKGROUND => 259
# SDL_APP_DIDENTERBACKGROUND => 260
# SDL_APP_WILLENTERFOREGROUND => 261
# SDL_APP_DIDENTERFOREGROUND => 262
# SDL_WINDOWEVENT => 512
# SDL_SYSWMEVENT => 513
# SDL_KEYDOWN => 768
# SDL_KEYUP => 769
# SDL_TEXTEDITING => 770
# SDL_TEXTINPUT => 771
# SDL_MOUSEMOTION => 1024
# SDL_MOUSEBUTTONDOWN => 1025
# SDL_MOUSEBUTTONUP => 1026
# SDL_MOUSEWHEEL => 1027
# SDL_JOYAXISMOTION => 1536
# SDL_JOYBALLMOTION => 1537
# SDL_JOYHATMOTION => 1538
# SDL_JOYBUTTONDOWN => 1539
# SDL_JOYBUTTONUP => 1540
# SDL_JOYDEVICEADDED => 1541
# SDL_JOYDEVICEREMOVED => 1542
# SDL_CONTROLLERAXISMOTION => 1616
# SDL_CONTROLLERBUTTONDOWN => 1617
# SDL_CONTROLLERBUTTONUP => 1618
# SDL_CONTROLLERDEVICEADDED => 1619
# SDL_CONTROLLERDEVICEREMOVED => 1620
# SDL_CONTROLLERDEVICEREMAPPED => 1621
# SDL_FINGERDOWN => 1792
# SDL_FINGERUP => 1793
# SDL_FINGERMOTION => 1794
# SDL_DOLLARGESTURE => 2048
# SDL_DOLLARRECORD => 2049
# SDL_MULTIGESTURE => 2050
# SDL_CLIPBOARDUPDATE => 2304
# SDL_DROPFILE => 4096
# SDL_RENDER_TARGETS_RESET => 8192
# SDL_RENDER_DEVICE_RESET => 8193
# SDL_USEREVENT => 32768
# SDL_LASTEVENT => 65535

# SDL2 MOD KEYS

# KMOD_NONE = 0
# KMOD_LSHIFT = 1
# KMOD_RSHIFT = 2
# KMOD_LCTRL = 64
# KMOD_RCTRL = 128
# KMOD_LALT = 256
# KMOD_RALT = 512
# KMOD_LGUI = 1024   left command
# KMOD_RGUI = 2048   right command
# KMOD_NUM = 4096
# KMOD_CAPS = 8192
# KMOD_MODE = 16384
# KMOD_RESERVED = 32768

#####################################################
