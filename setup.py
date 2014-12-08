#!/usr/bin/env python

from distutils.core import setup

try:
	import pylink
	install_packages = ['klibs']
except:
	install_packages = ['klibs', 'klibs.pylink']

setup(
	name='KLIBs', 
	version = '0.1', 
	description = 'A framework for building psychological experiments in Python', 
	author = 'Jonathan Mulle & Ross Story', 
	author_email = 'this.impetus@gmail.com', 
	url = 'git://kleinlab.psychology.dal.ca', 
	packages=install_packages,
	requires = ['numpy', 'pylink']
	)
