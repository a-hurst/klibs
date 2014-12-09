#!/usr/bin/env python

from distutils.core import setup

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
