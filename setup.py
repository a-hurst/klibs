#!/usr/bin/env python

from distutils.core import setup

setup(name='KleinlabFramework', version = '0.1', description = 'A framework for building psychological experiments in Python', author = 'Jonathan Mulle', author_email = 'this.impetus@gmail.com', url = 'git://kleinlab.psychology.dal.ca', py_modules = ['klibs'],
	  requires = ['numpy', 'pylink'],)
