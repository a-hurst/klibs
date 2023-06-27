__author__ = 'Austin Hurst & Jonathan Mulle'

import os
import re
import sys
import traceback

from klibs.KLInternal import load_source, full_trace
from klibs.KLInternal import colored_stdout as cso
from klibs import P


# Utility Functions #

def getinput(*args, **kwargs):
    # Python 2/3-agnostic function for getting console input.
    try:
        return raw_input(*args, **kwargs)
    except NameError:
        return input(*args, **kwargs)


def err(err_string):
    cso("<red>Error: " + err_string + "</red>\n")
    sys.exit()


def ensure_directory_structure(root, create_missing=False):

    dir_structure = {
        "ExpAssets": {
            ".versions": [],
            "Config": [],
            "Resources": ["audio", "code", "font", "image"],
            "Local": ["logs"],
            "Data": ["incomplete"],
        }
    }

    def _get_dir_paths(dir_map, root):
        paths = []
        if isinstance(dir_map, list):
            return [os.path.join(root, d) for d in dir_map]
        else:
            for d, subdirs in dir_map.items():
                dpath = os.path.join(root, d)
                paths += [dpath]
                paths += _get_dir_paths(subdirs, dpath)
        return paths

    missing_dirs = []
    for d in _get_dir_paths(dir_structure, root):
        if not os.path.isdir(d):
            d = d.replace(root, "").strip(os.path.sep)
            missing_dirs.append(d)
    
    if create_missing:
        for d in missing_dirs:
            dpath = os.path.join(root, d)
            if not os.path.isdir(dpath):
                os.makedirs(dpath)

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
    suffixes = ['_params.py', '_independent_variables.py', '_schema.sql', '_user_queries.json']
    for suffix in suffixes:
        filepath = os.path.join(config_dir, project_name + suffix)
        if not os.path.isfile(filepath):
            err("unable to locate the experiment's '{0}' file. Please ensure that the "
            "file exists, and that the first part of its name matches the name of the "
            "Experiment class defined in 'experiment.py'.".format(suffix))
        
    return project_name


def validate_database_path(db_path, prompt=False):

    if prompt == False and not os.path.isfile(db_path):
        err("unable to locate project database at '{0}'.\nIt may have been renamed, "
            "or may not exist yet.".format(db_path))

    while not os.path.isfile(db_path):
        cso("<green_d>No database file was present at '{0}'.</green_d>".format(db_path))
        db_prompt = cso(
            "<green_d>You can "
            "<purple>(c)</purple>reate it, "
            "<purple>(s)</purple>upply a different path or "
            "<purple>(q)</purple>uit: </green_d>", print_string=False
        )
        response = getinput(db_prompt).lower()
        print("")
        
        while response not in ['c', 's', 'q']:
            err_prompt = cso("<red>Please respond with one of 'c', 's', or 'q': </red>", False)
            response = getinput(err_prompt).lower()

        if response == "c":
            from klibs.KLDatabase import rebuild_database
            rebuild_database(db_path, P.schema_file_path)
        elif response == "s":
            db_path = getinput(cso("<green_d>Great, where might it be?: </green_d>", False))
            db_path = os.path.normpath(db_path)
        elif response == "q":
            sys.exit()
    
    return db_path



# Actual CLI Functions #

def create(name, path):
    import shutil
    from random import choice
    from os.path import join
    from tempfile import mkdtemp
    from pkg_resources import resource_filename

    template_files = [
        ("schema.sql", ["ExpAssets", "Config"]),
        ("independent_variables.py", ["ExpAssets", "Config"]),
        ("params.py", ["ExpAssets", "Config"]),
        ("user_queries.json", ["ExpAssets", "Config"]),
        ("experiment.py", []),
        (".gitignore", [])
    ]

    # TODO: Prompt user if project involves eye tracking & configure params accordingly

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
    author = getinput(cso("<green_d>Please provide your first and last name: </green_d>", False))
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
            return
        else:
            cso("\n<green_d>Pardon? I didn't catch that.</green_d>\n")

    # Create temporary folder and assemble project template inside it
    tmp_path = mkdtemp(prefix='klibs_')
    tmp_dir = os.path.split(tmp_path)[1]
    ensure_directory_structure(tmp_path, create_missing=True)
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

    # Ensure the specified screen size is valid
    if screen_size <= 0:
        err("Invalid screen size '{0}'. Size must be the diagonal size of the screen\n"
            "in inches (e.g. 'klibs run 24' for a 24-inch screen).".format(screen_size))

    cso("\n<green>*** Now Loading KLibs Environment ***</green>\n")

    # Suppresses possible pysdl2-dll warning message on import
    import shutil
    import warnings
    with warnings.catch_warnings():	
        warnings.simplefilter("ignore")
        import sdl2

    from klibs import P
    from klibs import env
    from klibs.KLGraphics.core import display_init
    from klibs.KLDatabase import DatabaseManager
    from klibs.KLText import TextManager
    from klibs.KLCommunication import init_messaging, collect_demographics, init_default_textstyles

    # Sanitize and switch to path, exiting with error if not a KLibs project directory
    project_name = initialize_path(path)

    # create any missing project directories
    missing_dirs = ensure_directory_structure(path)
    if len(missing_dirs):
        cso("<red>Some expected or required directories for this project appear to be missing.</red>")
        while True:
            query = cso(
                "<green_d>You can "
                "<purple>(c)</purple>reate them automatically, view a "
                "<purple>(r)</purple>eport on the missing directories,\nor "
                "<purple>(q)</purple>uit klibs: </green_d>", False
            )
            action = getinput(query).lower()
            action = action[0] if len(action) > 1 else action # only check first letter of input
            if action == "r":
                cso("\n<green_d>The following required directories were not found:</green_d>")
                for md in missing_dirs:
                    cso("<purple> - {0}</purple>".format(md))
            elif action == "c":
                ensure_directory_structure(path, create_missing=True)
                break
            elif action == "q":
                return
            else:
                cso("\n<red>Please enter a valid response.</red>")
            print("")

    # set initial param values for project's context
    P.initialize_runtime(project_name, seed)
    P.database_path = validate_database_path(P.database_path, prompt=True)

    # Add ExpAssets/Resources/code to pythonpath for easy importing
    sys.path.append(P.code_dir)

    # If a condition was specified, set it in Params
    P.condition = condition

    # import params defined in project's local params file in ExpAssets/Config
    try:
        for k, v in load_source(P.params_file_path).items():
            setattr(P, k, v)
    except IOError:
        err("Unable to locate the experiment's '_params.py' file. Please ensure that this "
            "file exists, and that the name of the experiment folder matches the name of the "
            "Experiment class defined in 'experiment.py'.")

    # if a local params file exists, do the same:
    if os.path.exists(P.params_local_file_path) and not P.dm_ignore_local_overrides:
        for k, v in load_source(P.params_local_file_path).items():
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

    # set some basic global Params
    if devmode:
        P.development_mode = True
        P.collect_demographics = False
    #TODO: check if current commit matches experiment.py and warn user if not

    # Back up database before starting the session
    shutil.copy(P.database_path, P.database_backup_path)

    # create runtime environment
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
            return
    env.db = DatabaseManager(
        P.database_path, P.database_local_path if P.multi_user else None
    )

    try:
        # create basic text styles and load in user queries
        init_messaging()

        # finally, import the project's Experiment class and instantiate
        experiment = load_source("experiment.py")[project_name]
        env.exp = experiment()

        # create a display context if everything's gone well so far
        env.exp.window = display_init(screen_size, P.allow_hidpi)
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


def export(path, table=None, combined=False, join=None):
    from klibs import P
    from klibs.KLDatabase import DatabaseManager

    # Sanitize and switch to path, exiting with error if not a KLibs project directory
    project_name = initialize_path(path)
    cso("\n<green>*** Exporting data from {0} ***</green>\n".format(project_name))

    # set initial param values for project's context
    P.initialize_paths(project_name)

    # ensure that 'Data' and 'Data/incomplete' directories exist, creating if missing
    if not os.path.isdir(P.incomplete_data_dir):
        os.makedirs(P.incomplete_data_dir)

    # import params defined in project's local params file in ExpAssets/Config
    for k, v in load_source(P.params_file_path).items():
        setattr(P, k, v)
    multi_file = combined != True

    # Validate database path and export
    P.database_path = validate_database_path(P.database_path)
    DatabaseManager(P.database_path).export(table, multi_file, join)


def rebuild_db(path):
    from klibs import P
    from klibs.KLDatabase import rebuild_database

    # Sanitize and switch to path, exiting with error if not a KLibs project directory
    project_name = initialize_path(path)

    # set initial param values for project's context
    P.initialize_paths(project_name)

    # import params defined in project's local params file in ExpAssets/Config
    for k, v in load_source(P.params_file_path).items():
        setattr(P, k, v)

    # Validate database path and rebuild
    P.database_path = validate_database_path(P.database_path)
    try:
        rebuild_database(P.database_path, P.schema_file_path)
        cso("Database successfully rebuilt! Please make sure to update experiment.py\n"
            "to reflect any changes you might have made to tables or column names.")
    except Exception as e:
        exc_txt = traceback.format_exc().split("\n")[-2]
        schema_filename = os.path.basename(P.schema_file_path)
        err = (
            "<red>Syntax error encountered in database schema ('{0}'):</red>\n\n"
            "  {1}\n\n"
            "<red>Please double-check the file's formatting and try again.</red>"
        )
        cso(err.format(schema_filename, exc_txt))


def hard_reset(path):
    import shutil

    # Sanitize and switch to path, exiting with error if not a KLibs project directory
    project_name = initialize_path(path)

    # Initialize file paths for the project & list ones to remove/rebuild
    P.initialize_paths(project_name)
    reset_files = [P.database_path, P.database_backup_path]
    reset_dirs = [
        P.incomplete_data_dir, P.incomplete_edf_dir, P.logs_dir, P.versions_dir
    ]

    reset_prompt = cso(
        "<red>Warning: doing a hard reset will delete all collected data, "
        "all logs, all copies of experiment.py and Config files in the .versions folder "
        "that previous participants were run with, and reset the project's database. "
        "Are you sure you want to continue?</red> (Y/N): ", False
    )
    if getinput(reset_prompt).lower() != "y":
        return
    
    # Remove and replace folders to reset
    for d in reset_dirs:
        if os.path.isdir(d):
            shutil.rmtree(d)
    ensure_directory_structure(path, create_missing=True)

    # Remove (but don't replace) files to reset
    for f in reset_files:
        if os.path.isfile(f):
            os.remove(f)
    
    cso("\nProject reset successfully.")


def update(branch=None):
    import subprocess as sub

    git_repo = 'a-hurst/klibs'
    if branch:
        url = 'https://github.com/{0}.git@{1}'.format(git_repo, branch)
        cmd = ['pip', 'install', '-U', 'git+{0}#egg=klibs'.format(url)]
        msg1 = "most recent commit\nfrom the <purple>{0}</purple> branch of"
        msg1 = msg1.format(branch)
        msg2 = "commit from '{0}'".format(branch)
    else:
        url = "https://github.com/{0}/releases/latest/download/klibs.tar.gz"
        cmd = ['pip', 'install', url.format(git_repo)]
        msg1 = "latest release\nfrom"
        msg2 = "release from '{0}'".format(git_repo)

    update_prompt = cso(
        "<green_d>Updating will replace the current install of KLibs with the "
        "{0} <purple>'{1}'</purple></green_d>.\n\n"
        "Are you sure you want to continue? (Y/N): ".format(msg1, git_repo),
        False
    )
    if getinput(update_prompt).lower() != "y":
        return

    # Set environment variable to avoid pip update warnings & run update command
    cso("\n<green_d>Updating to the latest {0}...</green_d>\n".format(msg2))
    env = os.environ.copy()
    env['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    p = sub.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, env=env)
    p.communicate()

    # Indicate whether update succeeded
    if p.returncode != 0:
        cso("\n<red>Errors encountered during KLibs update.</red>")
    else:
        cso("\n<green_d>Update completed successfully!</green_d>")
