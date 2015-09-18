#!/usr/bin/env python
import shutil
import os
import sys
from distutils.core import setup

# a hack until the installer is properly written
# try:
# 	open('/etc/foo.txt', 'w+')
# except IOError, e:
# 	if e.errno == 13:
# 		print >> sys.stderr, "\033[91mRoot permission required!\033[0m\nTry installing again with sudo."
# 		sys.exit(1)

try:
	import pylink

	install_packages = ['klibs']
except:
	install_packages = ['klibs']

setup(
	name='KLIBs',
	version='0.1a',
	description='A framework for building psychological experiments in Python',
	author='Jonathan Mulle & Ross Story',
	author_email='this.impetus@gmail.com',
	url='http://github.com/jmwmulle/klibs',
	packages=['klibs'],
	requires=['numpy', 'pylink']
)

# dirty hack until time is made to do this bit right via the installer
if os.path.exists("/usr/local/klibs"):
	shutil.rmtree("/usr/local/klibs")
if os.path.exists("/usr/local/bin/klibs"):
	os.remove("/usr/local/bin/klibs")
shutil.copyfile("klibs.py", "/usr/local/bin/klibs")
shutil.copymode("klibs.py", "/usr/local/bin/klibs")
os.mkdir("/usr/local/klibs")
shutil.copytree("template_temp", "/usr/local/klibs/template")