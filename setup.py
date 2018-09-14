#!/usr/bin/env python

import os
from setuptools import setup
import subprocess as sub
import shutil

# Get the git hash for the current KLibs commit
cmd = b'git rev-parse --verify HEAD'.split(b' ')
commit = sub.check_output(cmd).rstrip(b'\n')
with open('klibs/resources/current_commit.txt', 'wb+') as f:
	f.write(commit)
	
	
install_packages = ['klibs']

setup(
	name='KLibs',
	version='0.7.5a1',
	description='A framework for building psychological experiments in Python',
	author='Jonathan Mulle & Austin Hurst',
	author_email='mynameisaustinhurst@gmail.com',
	url='http://github.com/a-hurst/klibs',
	packages=['klibs', 'klibs/KLGraphics', 'klibs/KLEyeTracking'],
	include_package_data=True,
	entry_points = {'console_scripts': ['klibs = klibs.__main__:cli']},
	python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*',
	install_requires=[
		'numpy>=1.8.0rc1', 
		'pysdl2>=0.9.0',
		'Pillow>=3.0.0,!=5.1.0',
		'aggdraw>1.2.0',
		'PyOpenGL>=3.1.0',
		'PyAudio>=0.2.9'
	]

)

# Remove current_commit.txt after install to avoid messing with git
os.remove('klibs/resources/current_commit.txt')
