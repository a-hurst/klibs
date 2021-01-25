#!/usr/bin/env python

import os
from setuptools import setup
from distutils.spawn import find_executable
import subprocess as sub


# If installing from GitHub, get the git hash for the current KLibs commit

commit_file = os.path.join('klibs', 'resources', 'current_commit.txt')
source_install = False

if not os.path.isfile(commit_file):

	source_install = True
	if not find_executable('git'):
		e = "You must have Git installed in order to install KLibs from GitHub"
		raise RuntimeError(e)
	
	cmd = 'git rev-parse --verify HEAD'.split(' ')
	commit = sub.check_output(cmd, universal_newlines=True).strip()
	with open(commit_file, 'w+') as f:
		f.write(commit)
	
	
install_packages = ['klibs']

setup(
	name='KLibs',
	version='0.7.5a9',
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
		'pysdl2>=0.9.7',
		'pysdl2-dll>=2.0.10',
		'Pillow>=3.0.0,!=5.1.0',
		'aggdraw>1.2.0',
		'PyOpenGL>=3.1.0'
	],
	extras_require={
		'AudioResponse': ['PyAudio>=0.2.9']
	}
)


# Remove current_commit.txt after install to avoid messing with git

if source_install and os.path.exists(commit_file):
	os.remove(commit_file)
