__author__ = 'Austin Hurst & Jonathan Mulle'

import os
import sys
import argparse
import traceback
import binascii

try:
    from klibs import P
    from klibs import cli
except:
    print("\n\033[91m*** Fatal Error: Unable to load KLibs ***\033[0m\n\nStack Trace:")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print(traceback.print_exception(exc_type, exc_value, exc_traceback, limit=5, file=sys.stdout))
    sys.exit()



# The function that gets run when klibs is launched from the command line

def _check_ansi_support():
    # Checks whether the current terminal supports ANSI color sequences
    supported = False
    term_type = os.getenv('TERM')
    if term_type:
        supported = ('color' in term_type)
    # Newer versions of cmd.exe in Windows 10 support ANSI colors
    elif sys.platform == "win32":
        supported = sys.getwindowsversion().build >= 18363
    return supported


def klibs_main():

    sys.dont_write_bytecode = True # suppress creation of useless .pyc files
    P.color_output = _check_ansi_support()

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
        dest='command', title='commands',
        metavar='                                    ' # fixes indentation issue
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

    update_parser = subparsers.add_parser('update', formatter_class=CustomHelpFormatter,
        help='Update KLibs to the latest available version',
        usage='klibs update [-b <branch>] [-h]'
    )
    update_parser.add_argument('-b', '--branch', nargs="?", type=str, metavar="name",
        help=("The branch of the a-hurst/klibs repository from which to update KLibs. "
        "Installs the latest stable release if not specified.")
    )

    rebuild_parser = subparsers.add_parser('db-rebuild',
        help='Delete and rebuild the database',
        usage='klibs db-rebuild [path] [-h]'
    )
    rebuild_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str,
        help=("Path to the directory containing the KLibs project. "
        "Defaults to current working directory.")
    )

    reset_parser = subparsers.add_parser('hard-reset',
        help='Delete all collected data',
        usage='klibs hard-reset [path] [-h]'
    )
    reset_parser.add_argument('path', default=os.getcwd(), nargs="?", type=str,
        help=("Path to the directory containing the KLibs project. "
        "Defaults to current working directory.")
    )

    # Load the provided command and arguments, printing usage info if none given
    args = vars(parser.parse_args())
    cmd = args.pop("command", None)
    if not cmd:
        parser.print_usage()
        return

    # Actually run the requested command
    commands = {
        "create": cli.create,
        "run": cli.run,
        "export": cli.export,
        "db-rebuild": cli.rebuild_db,
        "hard-reset": cli.hard_reset,
        "update": cli.update,
    }
    print("") # Add a blank line before any CLI output
    commands[cmd](**args)
    print("") # Add a blank line after any CLI output


if __name__ == '__main__':
    klibs_main()
