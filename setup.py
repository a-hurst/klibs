#!/usr/bin/env python
import shutil
import os
import sys
from distutils.core import setup
import subprocess as sub


from tempfile import mkstemp
from shutil import move
from os import remove, close
import re


def replace(file_path, expr, subst):
	print file_path, expr, subst
	commit_exp = re.compile(expr)
	#Create temp file
	new_file_name = "{0}.temp".format(file_path)
	new_file = open(new_file_name,'w+')

	with open(file_path) as old_file:
		for line in old_file:
			if commit_exp.match(line):
				new_line = subst + "\n"
				print new_line
			else:
				new_line = line
			new_file.write(new_line)
				# if expr.match(line):
				# 	# new_file.write(line.replace('^klibs_commit = "([a-z0-9]{40})"$', subst))
				# else:
				# 	new_file.write(line)
	new_file.close()
	# Remove original file
	remove(file_path)
	# Move new file
	shutil.copy(new_file_name, file_path)
p = sub.Popen(['git', 'rev-parse', 'HEAD'],stdout=sub.PIPE,stderr=sub.PIPE)
replace("klibs/KLParams.py", '^klibs_commit = ("|\')([a-z0-9]{40})("|\')$', "klibs_commit = '{0}'".format(p.communicate()[0][:-2]))
quit()
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

