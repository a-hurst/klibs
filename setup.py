#!/usr/bin/env python
import shutil
import os
import sys
from distutils.core import setup


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
try:
	shutil.rmtree("/usr/local/lib/klibs")
except:
	try:
		os.remove("/usr/local/lib/klibs")
	except:
		pass
shutil.copytree("lib/klibs", "/usr/local/lib/klibs")

try:
	os.remove("/usr/local/bin/klibs")
except:
	pass
shutil.copyfile("bin/klibs", "/usr/local/bin/klibs")
shutil.copymode("bin/klibs", "/usr/local/bin/klibs")

