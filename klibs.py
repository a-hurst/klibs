#!/usr/bin/env python
# expected usage: klibs create path/to/project 

col = {"@P": '\033[95m',  # purple
		   "@B": '\033[94m',  # blue
		   "@R": '\033[91m',  # red
		   "@T": '\033[1m',   # teal
		   "@E": '\033[0m'    # return to normal
	}
try:
	import klibs
	import imp
except ImportError:
	#  todo: add in Ross's april fools idea
	print "\n\033[91m*** Fatal Error: klibs not found ***\033[0m\n"
	print "\033[1mWhat To Do: \033[0mThe klibs python module couldn't be located; repair the path to the module or reinstall it."
	print "Perhaps you're thinking \"then what's talking to me right now?!\". Don't worry, neither you nor I have gone mad."
	print "Rather, when you typed 'klibs <name> <path>' you executed a setup script to create a new empty project."
	print "This script is invoked using the word 'klibs' as a convenience but it is *not* a part of the klibs python module"
	print "required to execute a klibs project. This script is found at /usr/local/bin/klibs, whereas klibs must be"
	print "reachable by PYTHONPATH. If you don't know what this means try simply reinstalling. If that doesn't work,"
	print "then you probably need assistance. Go find a nerd!\n"
	print "\t\033[94mMore Information:   \033[0mhttp://kleinlab.psychology.dal.ca/klibs/documentation\033[0m"
	print "\t\033[94mDownload Installer: \033[0mhttp://kleinlab.psychology.dal.ca/klibs/installer.zip\033[0m"
	print "\t\033[94mRepository:         \033[0mhttps://github.com/jmwmulle/klibs\n"
	print "\n... if the links don't work it's because Jon likely only wrote this; try: this.impetus@gmail.com!\n"
	quit()
import argparse
import os
import shutil
from subprocess import Popen, PIPE


def create(name, path):
	# Adding author details and loop to confirm before execution, was in a rush,  will return later
	# Basically got stick on feeding raw_input() into arg_parse, seems to take each letter as an argument
	# Upadte #2:  moved on to using just raw_input() until help with how to do this turns up
	# http://stackoverflow.com/questions/32659345/how-to-use-argparse-during-runtime-to-conditionally-get-further-input

	auth_parse = argparse.ArgumentParser()
	auth_parse.add_argument('name', type=str, nargs=2)
	auth_args = auth_parse.parse_args(raw_input("Provide your first and last name:").split())

	source = "/usr/local/klibs/experiment_template"
	project_path = os.path.join(path, name)

	correct = False
	while not correct:
		print "Confirm project details:"
		print "\n\033[96mPROJECT AUTHOR: \033[94m{0} {1}\033[0m\n".format(auth_args.name[0], auth_args.name[1])
		print "\n\033[96mPROJECT PATH: \033[94m{0}\033[0m\n".format(project_path)
		confirm_parser = argparse.ArgumentParser()
		confirm_parser.add_argument('confirmed',  type=str, choices=['y', 'n'])
		confirm_args = confirm_parser.parse_args(raw_input("Is this correct?").lower())
		if confirm_args.confirmed == "n":
			return create(name, path)
		correct = True
	try:
		shutil.copytree(source, project_path)
		print "\t...Project template files successfully copied to {0}".format(project_path)
		temp_exp_f = open(os.path.join(project_path, "experiment.py"), "rt")
		temp_exp = temp_exp_f.read().replace('PROJECT_NAME', name).replace('EXPERIMENTER_NAME', " ".join(auth_args.name))
		open(os.path.join(project_path, "experiment.py"), "w+").write(temp_exp)

		shutil.move(os.path.join(project_path, 'ExpAssets', 'PROJECT_NAME_schema.sql'), os.path.join(project_path, 'ExpAssets', name + '_schema.sql'))
		temp_sql_f = open(os.path.join(project_path, 'ExpAssets', name + '_schema.sql'), "rt")
		temp_sql = temp_sql_f.read().replace('PROJECT_NAME', name).replace('PROJECT_PATH', path)
		open(os.path.join(project_path, 'ExpAssets', name + '_schema.sql'), "w+").write(temp_sql)

		shutil.move(os.path.join(project_path, 'gitignore.txt'), os.path.join(project_path,".gitignore"))
		temp_sql_f = open(os.path.join(project_path,".gitignore"), "rt")
		temp_sql = temp_sql_f.read().replace('PROJECT_NAME', name)
		open(os.path.join(project_path,".gitignore"), "w+").write(temp_sql)

		print "\t...Project name '{0}' successfully applied to template files".format(name)
		print "\033[92m\nProject successfully created at: '\033[94m{0}\033[0m'".format(project_path)
	except OSError, e:
		if e.errno == 17:
			print "\033[91mError:\033[0m A directory or file already exists at '\033[94m{0}\033[0m'.".format(project_path)
		else:
			raise OSError(e)
	except Exception, e:
		print "\033[91mError: Project '{0}' not created at {1}.\033[0m".format(name, project_path)
		try:
			shutil.rmtree(project_path)
			print "\033[91mRemoved all files created at {0}\033[0m".format(project_path)
		except Exception:
			print "\033[91mUnable to remove any files created at {0}\033[0m".format(project_path)

		raise OSError(e)

def update():
	"""
	So this generally works, but with a number of provisions, not the least of which being that the user has to have permissions
	to execute git at /usr/local
	 Generally, this just needs to be a lot more robust.
	 You're using Popen() because it lets you get stdout, whereas subprocess.call() only provides a returncode
	"""
	print "Update isn't currently supported. It's coming in a later update of KLIBs. For now, you can do this manually simply by cloning the git repository (https://www.github.com/jmwmulle/klibs) and re-installing."
	return
	p = Popen(['git', '-C', '/usr/local/klibs/klibs_git', 'pull'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
	output, err = p.communicate()
	print output
	print err
	#
	# 	rc = p.returncode

def run(path, screen_size, random_seed):
	if random_seed == -1: random_seed = None
	name = os.path.split(path)[-1]
	os.chdir(path)
	experiment = imp.load_source(path, "experiment.py")
	app = getattr(experiment, name)
	app(name, screen_size, random_seed=random_seed).run()


def export(path):
	name = os.path.split(path)[-1]
	os.chdir(path)
	experiment = imp.load_source(path, "experiment.py")
	app = getattr(experiment, name)
	app(name, 1, export=True)



parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(title='subcommands',
								   description='Valid arguments: create, update, run, export',
								   help='additional help')

create_parser = subparsers.add_parser('create')
create_parser.add_argument('name', type=str)
create_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str, help='[If CREATE] Path where new project should be created; if empty, project will attempt to be created in current working directory.')
create_parser.set_defaults(func=create)

update_parser = subparsers.add_parser('update')
update_parser.set_defaults(func=update)


run_parser = subparsers.add_parser('run')
run_parser.add_argument('screen_size', type=int, help='The diagonal size of the screen in inches on which the experiment is being run. This is used to calculate degrees of visual angle.')
run_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str, help='Path to directory containing the KLIBs project. Parent folder must be the project name.')
run_parser.add_argument('random_seed', default=-1, nargs="?", type=int, help="Providing a random seed will allow an experiment to continue from it's previously completed state." )
#run_parser.add_argument('testing', default=-1, nargs="?", type=str, help="Providing a random seed will allow an experiment to continue from it's previously completed state." )
run_parser.set_defaults(func=run)


export_parser = subparsers.add_parser('export')
export_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str, help='Path to directory containing the KLIBs project. Parent folder must be the project name.')
export_parser.set_defaults(func=export)

args = vars(parser.parse_args())

# try:
# args = vars(args)
arg_dict = {}
for key in args:
	if key != "func": arg_dict[key] = args[key]
args["func"](**arg_dict)
	#
	# args.func(*args)
# except AttributeError:
# 	args.func()
