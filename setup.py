#!/usr/bin/env python

from setuptools import setup
from os import remove, close, path
import subprocess as sub
import shutil

# Get the git hash for the current KLibs commit
cmd = 'git rev-parse --verify HEAD'.split(' ')
commit = sub.check_output(cmd).rstrip('\n')
with open('klibs/resources/current_commit.txt', 'w+') as f:
	f.write(commit)
	
# Remove old lib folder if present
old_lib = '/usr/local/lib/klibs'
if path.isdir(old_lib):
	try:
		shutil.rmtree(old_lib)
	except:
		try:
			remove(old_lib)
		except:
			print "/nUnable to remove old lib folder at {0}. You can remove it manually " \
				  "using 'sudo rm -rf {0}'\n".format(old_lib)
	

install_packages = ['klibs']

setup(
	name='KLibs',
	version='0.7.0a4',
	description='A framework for building psychological experiments in Python',
	author='Jonathan Mulle & Austin Hurst',
	author_email='this.impetus@gmail.com',
	url='http://github.com/a-hurst/klibs',
	packages=['klibs', 'klibs/KLGraphics', 'klibs/KLEyeLink'],
	include_package_data=True,
	entry_points = {'console_scripts': ['klibs = klibs.__main__:cli']},
	python_requires='>=2.7, <3',
	install_requires=[
		'numpy>=1.8.0rc1', 
		'pysdl2>=0.9.0',
		'Pillow>=3.0.0',
		'aggdraw>1.2.0',
		'PyOpenGL>=3.1.0',
		'PyAudio>=0.2.9'
	]

)

# Remove current_commit.txt after install to avoid messing with git
remove('klibs/resources/current_commit.txt')
