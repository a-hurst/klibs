#!/usr/bin/env python
import shutil
import os
import sys
from distutils.core import setup

try:
	import pylink
	install_packages = ['klibs']
except ImportError:
	install_packages = ['klibs']

setup(
	name='KLIBs',
	version='0.1a',
	description='A framework for building psychological experiments in Python',
	author='Jonathan Mulle',
	author_email='this.impetus@gmail.com',
	url='http://github.com/jmwmulle/klibs',
	packages=['klibs']
)

# dirty hack until time is made to do this bit right via the installer
# if os.path.exists("/usr/local/klibs"):
# 	shutil.rmtree("/usr/local/klibs")
# shutil.copytree("lib/klibs", "/usr/local/klibs")
# if os.path.exists("/usr/local/bin/klibs"):
# 	os.remove("/usr/local/bin/klibs")
# shutil.copyfile("bin/klibs", "/usr/local/bin/klibs")
# shutil.copymode("bin/klibs", "/usr/local/bin/klibs")
# os.mkdir("/usr/local/klibs")
# os.mkdir("/usr/local/klibs/font")
# shutil.copyfile("lib/klibs/splash.png", "/usr/local/klibs/splash.png")
# shutil.copymode("lib/klibs/splash.png", "/usr/local/klibs/splash.png")
# shutil.copyfile("lib/klibs/font/AnonymousPro.ttf", "/usr/local/klibs/font/AnonymousPro.ttf")
# shutil.copymode("lib/font/AnonymousPro.ttf", "/usr/local/klibs/font/AnonymousPro.ttf")
# shutil.copyfile("lib/font/Frutiger.ttf", "/usr/local/klibs/font/Frutiger.ttf")
# shutil.copymode("lib/font/Frutiger.ttf", "/usr/local/klibs/font/Frutiger.ttf")
# shutil.copytree("lib/template", "/usr/local/klibs/template")
# shutil.copymode("lib/template", "/usr/local/klibs/template")
