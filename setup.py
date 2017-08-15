#!/usr/bin/env python

from setuptools import setup, find_packages
from os import remove, close, path
import sys
import subprocess as sub
import shutil

copy_git = True
if "--no-git-copy" in sys.argv:
    copy_git = False
    sys.argv.remove("--no-git-copy")

install_packages = ['klibs']

setup(
	name='KLIBs',
	version='0.1a',
	description='A framework for building psychological experiments in Python',
	author='Jonathan Mulle',
	author_email='this.impetus@gmail.com',
	url='http://github.com/jmwmulle/klibs',
	packages=['klibs', 'klibs/KLGraphics', 'klibs/KLEyeLink'],
	python_requires='>=2.7, <3',
	install_requires=[
		'numpy', 
		'pysdl2',
		'Pillow',
		'aggdraw>=1.2',
		'PyOpenGL',
		'PyAudio'
	],
	dependency_links=[
		'https://github.com/pytroll/aggdraw/tarball/master#egg=aggdraw-1.2.1'
	]

)


# dirty hack until time is made to do this bit right via the installer

try:
    os.remove("/usr/local/bin/klibs")
except:
    pass
shutil.copyfile("bin/klibs", "/usr/local/bin/klibs")
shutil.copymode("bin/klibs", "/usr/local/bin/klibs")

try:
	shutil.rmtree("/usr/local/lib/klibs")
except:
	try:
		os.remove("/usr/local/lib/klibs")
	except:
		pass
shutil.copytree("lib/klibs", "/usr/local/lib/klibs")


p = sub.Popen(['git', 'rev-parse', 'HEAD'], stdout=sub.PIPE,stderr=sub.PIPE)
commit = p.communicate()[0][:-1]
open("/usr/local/lib/klibs/current_commit.txt", "w+").write(commit)

if copy_git:
	print "Copying git to \"/usr/local/lib/klibs/klibs_git\". This may take a minute or two..."
	shutil.copytree(path.dirname(path.realpath(__file__)), "/usr/local/lib/klibs/klibs_git", True)
