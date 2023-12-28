## ![KLibs logo](https://github.com/a-hurst/klibs/raw/testing/klibs/resources/splash.png)

KLibs is a simple-but-powerful framework for writing cognitive science experiments using Python.

The aim of this project is to handle all the low-level parts of writing an experment program for you (e.g. generating trial factors, drawing shapes, collecting demographics) so that you can focus on writing the parts of your experiment that really matter. 

KLibs also aims to make the distribution, replication, and modification of paradigms as simple and painless as possible, making it easy for you to share your work with colleagues and with the world at large. To look at some examples of projects built using KLibs, see the [Project Gallery](https://github.com/a-hurst/klibs/wiki/KLibs-Project-Gallery).


## Dependencies

The only dependencies needed to install KLibs on macOS, Windows, and most Linux distros are Git and a supported version of Python. KLibs requires Python 3.7 (or newer) run.

You will also need the pip Python package manager to install KLibs on your system. If running 'pip --version' on your system results in a "command not found" message, you can install it using the [official instructions](https://pip.pypa.io/en/stable/installing/#installing-with-get-pip-py).

In order to use the optional AudioResponse response collector or to interface with an SR Research EyeLink eye tracker, you will need to install some [additional dependencies](https://github.com/a-hurst/klibs/wiki/Installing-Optional-Dependencies).


## Installation

After all the prerequisites have been installed, you can run the following command to install KLibs and all its Python dependencies:

```
pip install git+https://github.com/a-hurst/klibs.git
```


## Usage

Installing KLibs will install the `klibs` command-line utility, which is used for creating, running, and exporting data from KLibs experiments:

```
$ klibs --help
usage: klibs (create | run | export | update | db-rebuild | hard-reset) [-h]

The command-line interface for the KLibs framework.

optional arguments:
  -h, --help            show this help message and exit

commands:
    create              Create a new project template
    run                 Run a KLibs experiment
    export              Export data to ExpAssets/Data/
    update              Update KLibs to the newest available version
    db-rebuild          Delete and rebuild the database
    hard-reset          Delete all collected data
```

For more detailed information on using KLibs, see the [project Wiki](https://github.com/a-hurst/klibs/wiki).
