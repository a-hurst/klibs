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
# try:
# 	os.remove("/usr/local/lib/klibs/__init__.py")
# except:
# 	pass
# try:
# 	os.remove("/usr/local/lib/klibs/template/__init__.py")
# except:
# 	pass
# try:
# 	os.remove("/usr/local/lib/klibs/template/ExpAssets/__init__.py")
# except:
# 	pass
# try:
# 	os.remove("/usr/local/lib/klibs/template/ExpAssets/Config/__init__.py")
# except:
# 	pass
try:
	os.remove("/usr/local/bin/klibs")
except:
	pass
shutil.copyfile("bin/klibs", "/usr/local/bin/klibs")
shutil.copymode("bin/klibs", "/usr/local/bin/klibs")

p = sub.Popen(['git', 'rev-parse', 'HEAD'], stdout=sub.PIPE,stderr=sub.PIPE)
commit = p.communicate()[0][:-1]
open("/usr/local/lib/klibs/current_commit.txt", "w+").write(commit).close()
# old_params_file = "klibs/KLParams.py"
# new_params_file = "klibs/KLParams.tmp"
# new_file = open(new_params_file, "w+")
# commit_exp = re.compile("^klibs_commit = '(.*)'$")
# with open(old_params_file) as of:
# 	for line in of:
# 		new_file.write("klibs_commit = '{0}'\n".format(commit) if commit_exp.match(line) else line)
# new_file.close()
# shutil.copymode(old_params_file, new_params_file)
# os.rename(old_params_file, "klibs/__KLParams.py")
# os.rename(new_params_file, old_params_file)

if copy_git:
	print "Copying git to \"/usr/local/lib/klibs/klibs_git\". This may take a minute or two..."
	shutil.copytree(os.path.dirname(os.path.realpath(__file__)), "/usr/local/lib/klibs/klibs_git", True)

