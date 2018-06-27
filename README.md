## ![KLibs logo](https://github.com/a-hurst/klibs/raw/testing/klibs/resources/splash.png)

KLibs is a simple-but-powerful framework for writing cognitive science experiments using Python.

The aim of this project is to handle all the low-level parts of writing an experment program for you (e.g. generating trial factors, drawing shapes, collecting demographics) so that you can focus on writing the parts of your experiment that really matter. 

KLibs also aims to make the distribution, replication, and modification of paradigms as simple and painless as possible, making it easy for you to share your work with colleagues and with the world at large. To look at some examples of projects built using KLibs, see the [Project Gallery](https://github.com/a-hurst/klibs/wiki/KLibs-Project-Gallery).


## Dependencies

In order to install KLibs on your system, the sdl2, sdl2\_ttf, sdl2\_mixer, and portaudio libraries must already be installed.

Under macOS/OS X, you can easily do this with a package manager such as [Homebrew](https://brew.sh):

```
brew install sdl2 sdl2_ttf sdl2_mixer portaudio
```

Under Debian/Ubuntu linux, the key dependencies can be installed using apt-get:

```
sudo apt-get install git python-pip libsdl2-2.0-0 libsdl2-ttf-2.0-0 libsdl2-mixer-2.0-0 portaudio19-dev
```

Under Windows, you can install the dependencies by following the [Windows installation guide](https://github.com/a-hurst/klibs/wiki/Installation-on-Windows).

You will also need the pip Python package manager to install KLibs on your system. If running 'pip --version' on your system results in a "command not found" message, you can install it by running ```sudo easy_install pip```.

KLibs requires either Python 3.3 (or newer) or Python 2.7 to run.

## Installation

After all the prerequisite libraries have been installed, you can run the following command to install KLibs and all its Python dependencies:

```
pip install git+https://github.com/a-hurst/klibs.git
```

Note that if you are using the default system-installed version of Python on macOS, you will need to preface the `pip install` command with `sudo -H` for the command to work.

If you want to use the Slack messaging feature in KLibs, you will need to install the 'slacker' package by running ```pip install slacker```.

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