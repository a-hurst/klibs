#!/usr/bin/env python

from distutils.core import setup

setup(
	name='KLIBs', 
	version = '0.1', 
	description = 'A framework for building psychological experiments in Python', 
	author = 'Jonathan Mulle & Ross Story', 
	author_email = 'this.impetus@gmail.com', 
	url = 'git://kleinlab.psychology.dal.ca', 
	packages=['klibs'],
	requires = ['numpy', 'pylink']
	)
