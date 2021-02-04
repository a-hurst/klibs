__author__ = 'Austin Hurst & Jonathan Mulle'

import os
import re
import sys
import imp
import time
import argparse
import traceback
import binascii

try:
	from klibs.KLInternal import colored_stdout as cso
	from klibs import P
except:
	print("\n\033[91m*** Fatal Error: Unable to load KLibs ***\033[0m\n\nStack Trace:")
	exc_type, exc_value, exc_traceback = sys.exc_info()
	print(traceback.print_exception(exc_type, exc_value, exc_traceback, limit=5, file=sys.stdout))
	sys.exit()

if __name__ == '__main__':
	cli()


# Utility Functions #

def err(err_string):
	cso("<red>\nError: " + err_string + "</red>\n")
	sys.exit()


def getinput(*args, **kwargs):
	try:
		return raw_input(*args, **kwargs)
	except NameError:
		return input(*args, **kwargs)


def ensure_directory_structure(dir_map, root, parents=[], create_missing=False):
	missing_dirs = []
	if dir_map is None:
		return missing_dirs
	parent_path = os.path.join(*parents) if len(parents) else ""
	for d in dir_map:
		dir_full_path = os.path.join(root, parent_path, d)
		subdirs = dir_map[d]
		if not os.path.exists(dir_full_path):
			if not create_missing:
				missing_dirs.append(dir_full_path)
			else:
				try:
					os.makedirs(dir_full_path)
				except OSError as e:
					cso("failed")
					cso(dir_map, parents)
					sys.exit()
		new_parents = [p for p in parents]
		new_parents.append(d)
		missing_dirs += ensure_directory_structure(subdirs, root, new_parents, create_missing)
	return missing_dirs


def initialize_path(path):

	# Initialize paths and switch to project directory
	path = os.path.normpath(path)
	exp_file = os.path.join(path, 'experiment.py')
	config_dir = os.path.join(path, 'ExpAssets', 'Config')
	os.chdir(path)

	# Verify required project files and folders exist
	if not os.path.exists(exp_file):
		err("no 'experiment.py' file was found in the specified directory.\n"
			"Please make sure you are in a valid KLibs project folder and try again.")
	if not os.path.isdir(config_dir):
		err("could not locate the project's required 'ExpAssets/Config' directory.\n"
			"Please make sure you are in a valid KLibs project folder and try again.")

	# Get experiment name from experiment.py file
	with open(exp_file, 'r') as f:
		name_regex = re.compile(r"\nclass\s+(\w+)\((?:klibs\.)?Experiment.*")
		exp_class_names = name_regex.findall(f.read())
	if not len(exp_class_names):
		err("could not find a valid KLibs Experiment class in 'experiment.py'.\n"
			"Please double-check the main experiment script and try again.")		
	project_name = exp_class_names[0]

	# Check Config folder for files matching experiment name
	config_project_names = [f.split("_")[0] for f in os.listdir(config_dir)]
	if not any([project_name == n for n in config_project_names]):
		err("the project name in 'experiment.py' ({0}) does not match the names of any "
			"of the project's configuration files.\n"
			"Please verify the project structure and try again.".format(project_name))
		
	return project_name


def validate_database_path(db_path, prompt=False):

	if prompt == False and not os.path.isfile(db_path):
		err("unable to locate project database at '{0}'.\nIt may have been renamed, "
			"or may not exist yet.".format(db_path))

	while not os.path.isfile(db_path):
		cso("\n<green_d>No database file was present at '{0}'.</green_d>".format(db_path))
		db_prompt = cso(
			"<green_d>You can "
			"<purple>(c)</purple>reate it, "
			"<purple>(s)</purple>upply a different path or "
			"<purple>(q)</purple>uit: </green_d>", print_string=False
		)
		response = getinput(db_prompt).lower()
		
		while response not in ['c', 's', 'q']:
			err_prompt = cso("<red>\nPlease respond with one of 'c', 's', or 'q': </red>", False)
			response = getinput(err_prompt).lower()

		if response == "c":
			open(db_path, "a").close()
		elif response == "s":
			db_path = getinput(cso("<green_d>\nGreat, where might it be?: </green_d>", False))
			db_path = os.path.normpath(db_path)
		elif response == "q":
			print("")
			sys.exit()
	
	return db_path



# Actual CLI Functions #

def create(name, path):
	import shutil
	from random import choice
	from os.path import join
	from tempfile import mkdtemp
	from pkg_resources import resource_filename

	dir_structure = {
		"ExpAssets": {
			".versions": None,
			"Config": None,
			"Resources": {"audio": None, "code": None, "font": None, "image": None},
			"Local": {"logs": None},
			"Data": {"incomplete": None},
			"EDF": {"incomplete": None}
		}
	}
	template_files = [
		("schema.sql", ["ExpAssets", "Config"]),
		("independent_variables.py", ["ExpAssets", "Config"]),
		("params.py", ["ExpAssets", "Config"]),
		("user_queries.json", ["ExpAssets", "Config"]),
		("experiment.py", []),
		(".gitignore", [])
	]

	# Validate name (must be valid Python identifier)
	valid_name = re.match(re.compile(r"^[A-Za-z_]+([A-Za-z0-9_]+)?$"), name) != None
	if not valid_name:
		err("'{0}' is not a valid project name. Project names must not contain any spaces or "
			"special characters apart from '_', and cannot start with a number.".format(name))

	# Ensure destination folder 1) exists, 2) is a folder, and 3) is writeable by the current user.
	if not os.path.exists(path):
		err("The path '{0}' does not exist.\n\nPlease enter a path to a valid writeable folder and "
			"try again.".format(path))
	elif not os.path.isdir(path):
		err("The path '{0}' does not point to a valid folder.\n\nPlease enter a different path and "
			"try again.".format(path))
	elif not os.access(path, os.W_OK | os.X_OK):
		err("You do not have the permissions required to write to the folder '{0}'.\n\nPlease "
			"enter a path to a folder you have write access to and try again.".format(path))

	# Initialize project path and make sure it doesn't already exist
	project_path = join(path, name)
	if os.path.exists(project_path):
		err("Folder named '{0}' already exists in the directory '{1}'.\n\nPlease remove it or give "
			"your project a different name and try again.".format(name, path))

	# Get author name for adding to project files
	author = getinput(cso("\n<green_d>Please provide your first and last name: </green_d>", False))
	if len(author.split()) < 2:
		one_name_peeps = ["Madonna", "Prince", "Cher", "Bono", "Sting"]
		cso("<red>\nOk {0}, take it easy.</red> "
			"<green_d>First <cyan>*and*</cyan> last name. "
			"Let's try that again--you got this champ...</green_d>".format(choice(one_name_peeps)))
		return create(name, path)
	
	# Verify author name and project path before creating it
	cso("\n<green_d>*** <purple>Confirm Project Details</purple> ***</green_d>")
	cso("<cyan>Project Author:</cyan> <blue>{0} {1}</blue>".format(*author.split()))
	cso("<cyan>Project Path:</cyan> <blue>{0}</blue>\n".format(project_path))
	verified = False
	while not verified:
		query = cso(
            "<green_d>Is this correct? Answer with "
            "<purple>Y</purple>es, "
			"<purple>N</purple>o, or "
			"<purple>Q</purple>uit: </green_d>", False
        )
		response = getinput(query).lower()
		response = response[0] if len(response) > 1 else response
		if response == "y":
			verified = True
		elif response == "n":
			return create(name, path)
		elif response == "q":
			cso("\n<green_d>Fine. Be that way. But I think we both know you'll be back.</green_d>")
			sys.exit()
		else:
			cso("\n<green_d>Pardon? I didn't catch that.</green_d>\n")

	# Create temporary folder and assemble project template inside it
	tmp_path = mkdtemp(prefix='klibs_')
	tmp_dir = os.path.split(tmp_path)[1]
	ensure_directory_structure(dir_structure, tmp_path, create_missing=True)
	cso("  <cyan>...Project template folders successfully created.</cyan>")

	source_path = resource_filename('klibs', 'resources/template')
	for tf in template_files: # replace generic file names with project-specific names
		filename = tf[0] if tf[0] in [".gitignore", "experiment.py"] else "{0}_{1}".format(name, tf[0])
		template_f_path = join(source_path, tf[0] if tf[0] != ".gitignore" else "gitignore.txt")
		project_f_path = filename if len(tf[1]) == 0 else join(join(*tf[1]), filename)
		with open(template_f_path, "rt") as temp, open(join(tmp_path, project_f_path), "w+") as out:
			contents = temp.read()
			contents = contents.replace('PROJECT_NAME', name)
			contents = contents.replace('EXPERIMENTER_NAME', author)
			out.write(contents)
		cso("  <cyan>...'{0}' successfully created.</cyan>".format(project_f_path))

	# Once successfully initialized, copy template to target directory
	shutil.move(tmp_path, path)
	os.rename(join(path, tmp_dir), join(path, name))
	cso("<green_d>\nProject successfully created at:</green_d> '<blue>{0}</blue>'".format(project_path))


def run(screen_size, path, condition, devmode, no_tracker, seed):

	cso("\n\n<green>*** Now Loading KLibs Environment ***</green>\n")

	from klibs import env
	from klibs.KLGraphics.core import display_init
	from klibs.KLDatabase import DatabaseManager
	from klibs.KLEventInterface import EventManager
	from klibs.KLText import TextManager
	from klibs.KLCommunication import init_messaging, collect_demographics, init_default_textstyles

	# Sanitize and switch to path, exiting with error if not a KLibs project directory
	project_name = initialize_path(path)

	# Create any missing project directories
	dir_structure = {
		"ExpAssets": {
			".versions": None,
			"Config": None,
			"Resources": {"audio": None, "code": None, "font": None, "image": None},
			"Local": {"logs": None},
			"Data": {"incomplete": None},
			"EDF": {"incomplete": None}}
	}

	missing_dirs = ensure_directory_structure(dir_structure, path)
	if len(missing_dirs):
		print("")
		cso("<red>Some expected or required directories for this project appear to be missing.</red>")
		while True:
			query = cso(
				"<green_d>You can "
				"<purple>(c)</purple>reate them automatically, view a "
				"<purple>(r)</purple>eport on the missing directories, or "
				"<purple>(q)</purple>uit klibs: </green_d>", False
			)
			action = getinput(query).lower()
			action = action[0] if len(action) > 1 else action # only check first letter of input
			if action == "r":
				cso("<green_d>The following expected directories were not found:</green_d>")
				for md in missing_dirs:
					cso("\t<purple>{0}</purple>".format(md))
			elif action == "c":
				ensure_directory_structure(dir_structure, path, create_missing=True)
				break
			elif action == "q":
				sys.exit()
			else:
				cso("\n<red>Please enter a valid response.</red>")

	# Set initial param values for project's context
	P.initialize_runtime(project_name, seed)
	P.database_path = validate_database_path(P.database_path, prompt=True)

	# Add ExpAssets/Resources/code to pythonpath for easy importing
	sys.path.append(P.code_dir)

	# If a condition was specified, set it in Params
	P.condition = condition

	# Import params defined in project's params file in ExpAssets/Config
	try:
		for k, v in imp.load_source("*", P.params_file_path).__dict__.items():
			setattr(P, k, v)
	except IOError:
		err("Unable to locate the experiment's '_params.py' file. Please ensure that this "
			"file exists, and that the name of the experiment folder matches the name of the "
			"Experiment class defined in 'experiment.py'.")

	# If a local params file exists, do the same:
	if os.path.exists(P.params_local_file_path) and not P.dm_ignore_local_overrides:
		for k, v in imp.load_source("*", P.params_local_file_path).__dict__.items():
			setattr(P, k, v)

	# If a condition has been specified, make sure it's a valid condition as per params.py
	if P.condition == None:
		P.condition = P.default_condition
	if P.condition != None:
		if len(P.conditions) == 0:
			err("No between-participant conditions have been defined for this experiment. "
				"You can define valid condition names in your experiment's params.py file.")
		elif P.condition not in P.conditions:
			cond_list = "', '".join(P.conditions)
			err("'{0}' is not a valid condition for this experiment (must be one of '{1}'). "
				"Please relaunch the experiment.".format(P.condition, cond_list))

	# Set some basic global Params
	if devmode:
		P.development_mode = True
		P.collect_demographics = False
	if not P.labjack_available:
		P.labjacking = False

	# Create runtime environment
	env.txtm = TextManager()
	if P.eye_tracking:
		if no_tracker is True:
			P.eye_tracker_available = False
		if P.development_mode and P.dm_show_gaze_dot:
			P.show_gaze_dot = True
		from klibs import KLEyeTracking # needs to be imported after params are read in
		try:
			env.el = KLEyeTracking.Tracker()
		except RuntimeError:
			sys.exit()
	env.db = DatabaseManager()
	env.evm = EventManager()

	try:
		# create basic text styles, load in user queries, and initialize slack (if enabled)
		init_messaging()

		# finally, import the project's Experiment class and instantiate
		experiment_file = imp.load_source(path, "experiment.py")
		experiment = getattr(experiment_file, project_name)
		env.exp = experiment()

		# create a display context if everything's gone well so far
		env.exp.window = display_init(screen_size)
		env.exp.show_logo()

		# once display size and pixels-per-degree known, initialize default text styles
		init_default_textstyles()

		# create an anonymous user if not collecting demographic information
		if not P.manual_demographics_collection:
			collect_demographics(not P.collect_demographics or P.development_mode)

		# off to the races team...
		env.exp.run()

	except Exception as e:
		print("".join(["\n"] +
			traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]) + 
			traceback.format_tb(sys.exc_info()[2])
		))
		sys.exit()


def export(path, table=None, combined=False, join=None):
	from klibs.KLDatabase import DatabaseManager

	# Sanitize and switch to path, exiting with error if not a KLibs project directory
	project_name = initialize_path(path)

	# Set initial param values for project's context
	P.initialize_paths(project_name)

	# Ensure that 'Data' and 'Data/incomplete' directories exist, creating if missing
	if not os.path.isdir(P.incomplete_data_dir):
		os.makedirs(P.incomplete_data_dir)

	# Import params defined in project's local params file in ExpAssets/Config
	for k, v in imp.load_source("*", P.params_file_path).__dict__.items():
		setattr(P, k, v)
	multi_file = combined != True

	# Validate database path and export
	P.database_path = validate_database_path(P.database_path)
	DatabaseManager().export(table, multi_file, join)


def rebuild_db(path):
	from klibs.KLDatabase import DatabaseManager

	# Sanitize and switch to path, exiting with error if not a KLibs project directory
	project_name = initialize_path(path)

	# Set initial param values for project's context
	P.initialize_paths(project_name)

	# Import params defined in project's local params file in ExpAssets/Config
	for k, v in imp.load_source("*", P.params_file_path).__dict__.items():
		setattr(P, k, v)

	# Validate database path and rebuild
	P.database_path = validate_database_path(P.database_path)
	DatabaseManager().rebuild()


def hard_reset(path):
	import shutil
	from os.path import join
	from klibs.KLInternal import iterable

	# Sanitize and switch to path, exiting with error if not a KLibs project directory
	project_name = initialize_path(path)

	# Set initial param values for project's context
	P.initialize_paths(project_name)

	reset_prompt = cso(
		"\n<red>Warning: doing a hard reset will delete all collected data, "
		"all logs, all copies of experiment.py and Config files in the .versions folder "
		"that previous participants were run with, and reset the project's database. "
		"Are you sure you want to continue?</red> (Y/N): ", False
	)
	if getinput(reset_prompt).lower() == "y":
		for d in ['Data', 'EDF', '.versions', ('Local', 'logs')]:
			if iterable(d):
				d = join(*d)
			try:
				shutil.rmtree(join(path, "ExpAssets", d))
			except OSError:
				pass
		for f in [P.database_path, P.database_backup_path]:
			if os.path.isfile(f):
				os.remove(f)
		os.makedirs(join(path, "ExpAssets", "Data", "incomplete"))
		os.makedirs(join(path, "ExpAssets", "EDF", "incomplete"))
		os.mkdir(join(path, "ExpAssets", "Local", "logs"))
		os.mkdir(join(path, "ExpAssets", ".versions"))
	print("")


def update(branch='default'):
	import logging
	import pip
	try:
		from pip import main as pip_main
	except ImportError:
		from pip._internal import main as pip_main

	# Avoid unnecessary terminal clutter by suppressing alerts for non-upgraded dependencies
	class pipFilter(logging.Filter):
		def filter(self, record):
			return not record.getMessage().startswith('Requirement not upgraded')
	try:
		pip.req.req_set.logger.addFilter(pipFilter())
	except AttributeError:
		pip_logger = logging.getLogger('pip._internal.operations.prepare')
		pip_logger.addFilter(pipFilter())

	#TODO: This should really be able to compare the version/commit/origin of the current KLibs
	#install and the one about to be installed to make sure you can't unintentionally overwrite
	#a newer local version or install from a different branch.
	git_repo_short = 'github.com/a-hurst'
	git_repo = 'https://{0}/klibs.git'.format(git_repo_short)
	if branch != 'default':
		git_repo += "@{0}".format(branch)
	
	update_cmd = 'install -U git+{0}#egg=klibs --upgrade-strategy only-if-needed'.format(git_repo)
	update_prompt = cso(
		"\n<green_d>Updating will replace the current install of KLibs with the most "
		"recent commit of the <purple>{0}</purple> branch of <purple>'{1}'</purple>. "
		"Are you sure you want to continue? (Y/N): </green_d>".format(branch, git_repo_short),
		False
	)
	if getinput(update_prompt).lower() == "y":
		print("")
		cso("<green_d>Updating klibs to latest commit from {0}...</green_d>".format(git_repo_short))
		try:
			pip_main(update_cmd.split(' '))
		except OSError:
			cso("<red>Root permissions required to reinstall klibs.</red>")
			sys.exit()
	else:
		print("")
		sys.exit()


# the function that gets run when klibs is launched from the command line
def cli(): 

	sys.dont_write_bytecode = True # suppress creation of useless .pyc files

	term_type = os.getenv('TERM') # make sure the terminal supports colour before enabling cso
	if term_type and 'color' in term_type:
		P.color_output = True

	class CustomHelpFormatter(argparse.HelpFormatter):
		# default argparse help formatting is kind of a mess, so we override some things
		def _format_action_invocation(self, action):
			if not action.option_strings or action.nargs == 0:
				return argparse.HelpFormatter._format_action_invocation(self, action)
			default = action.dest.upper()
			args_string = self._format_args(action, default)
			return ', '.join(action.option_strings) + ' ' + args_string

		def _format_args(self, action, default_metavar):
			get_metavar = self._metavar_formatter(action, default_metavar)
			if action.nargs is None:
				result = '%s' % get_metavar(1)
			elif action.nargs == '?':
				result = '<%s>' % get_metavar(1)
			elif action.nargs == '*':
				result = '[%s,...]' % get_metavar(1)
			elif action.nargs == '+':
				result = '<%s,...>' % get_metavar(1)
			elif action.nargs == 'A...':
				result = '...'
			elif action.nargs == '...':
				result = '%s ...' % get_metavar(1)
			else:
				formats = ['%s' for _ in range(action.nargs)]
				result = ' '.join(formats) % get_metavar(action.nargs)
			return result

	parser = argparse.ArgumentParser(
	    description='The command-line interface for the KLibs framework.',
        usage='klibs (create | run | export | update | db-rebuild | hard-reset) [-h]',
		formatter_class=CustomHelpFormatter,
        epilog="For help on how to use a specific command, try 'klibs (command) --help'."
	)
	subparsers = parser.add_subparsers(
		title='commands', metavar='                                    ' # fixes indentation issue
	)

	create_parser = subparsers.add_parser('create', 
		help='Create a new project template',
        usage='klibs create <name> [path] [-h]'
    )
	create_parser.add_argument('name', type=str,
		help=("The name of the new project. This will be used for the folder name, the class name "
		"in experiment.py, and the prefixes of various project files. "
		"Must be a valid Python variable name.")
	)
	create_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str,
		help=("The path where the new project should be created. "
		"Defaults to current working directory.")
	)
	create_parser.set_defaults(func=create)

	run_parser = subparsers.add_parser('run', formatter_class=CustomHelpFormatter,
		help='Run a KLibs experiment',
		usage='klibs run <screen_size> [path] [-d -ELx -c <condition> -s <seed>] [-h]'
	)
	run_parser.add_argument('screen_size', type=float,
		help=("The diagonal size in inches of the screen on which the experiment is being run. "
		"Used to calculate degrees of visual angle during experiment runtime.")
	)
	run_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str,
		help=("Path to the directory containing the KLibs project. "
		"Defaults to current working directory.")
	)
	run_parser.add_argument('-d', '--devmode', action="store_true",
		help=("Enables development mode, which skips demographics collection and turns on "
		"several debugging features.")
	)
	run_parser.add_argument('-c', '--condition', nargs="?", type=str, metavar="c",
		help=("If the experiment has between-participant conditions, allows the user "
		"to specify which condition to run.")
	)
	run_parser.add_argument('-ELx', '--no_tracker', action="store_true",
		help=("Signals the absence of a connected eye tracker. "
		"Does nothing for non-eyetracking experiments.")
	)
	run_parser.add_argument('-s', '--seed', type=int, nargs="?", metavar="seed",
		default=int(binascii.b2a_hex(os.urandom(4)), 16), # a random 9/10 digit int
		help=("The seed to use for random number generation during the KLibs runtime. "
		"Defaults to a random integer.")
	)
	# todo: verbose mode should accept a value, and then logging should be incrementally verbose
	#run_parser.add_argument('-v', '--verbose', action="store_true",
	#	help="Logs extra klibs debug information to the terminal."
	#)
	run_parser.set_defaults(func=run)

	export_parser = subparsers.add_parser('export', formatter_class=CustomHelpFormatter,
		help='Export data to ExpAssets/Data/',
		usage='klibs export [path] [-c] [-t <primary_table>] [-j <table1,...>] [--help]'
	)
	export_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str, metavar="path",
		help=("Path to the directory containing the KLibs project. "
		"Defaults to current working directory.")
	)
	export_parser.add_argument('-t', '--table', nargs="?", type=str, metavar="table",
		help=("Specify the primary table to join with the participants table during export. "
		"Defaults to the 'trials' table unless otherwise specified.")
	)
	export_parser.add_argument('-c', '--combined', action="store_true",
		help=("Export data to a single file instead of individual files for each participant. "
		"Default is individual files.")
	)
	export_parser.add_argument('-j', '--join', nargs="+", type=str, metavar="t1",
		help=("Additional tables to be joined to the data output. "
		"Only 'participant' and 'data' tables are joined by default.")
	)
	export_parser.set_defaults(func=export)

	update_parser = subparsers.add_parser('update',
		help='Update KLibs to the newest available version',
		usage='klibs update [branch] [-h]'
	)
	update_parser.add_argument('branch', default='default', nargs="?", type=str,
		help=("The branch of the KLibs GitHub repository from which to install the latest version. "
		"The default branch is used if none is specified.")
	)
	update_parser.set_defaults(func=update)

	rebuild_parser = subparsers.add_parser('db-rebuild',
		help='Delete and rebuild the database',
		usage='klibs db-rebuild [path] [-h]'
	)
	rebuild_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str,
		help=("Path to the directory containing the KLibs project. "
		"Defaults to current working directory.")
	)
	rebuild_parser.set_defaults(func=rebuild_db)

	reset_parser = subparsers.add_parser('hard-reset',
		help='Delete all collected data',
		usage='klibs hard-reset [path] [-h]'
	)
	reset_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str,
		help=("Path to the directory containing the KLibs project. "
		"Defaults to current working directory.")
	)
	reset_parser.set_defaults(func=hard_reset)

	args = vars(parser.parse_args())


	arg_dict = {}
	for key in args:
		if key != "func": arg_dict[key] = args[key]

	args["func"](**arg_dict)
