## ![KLibs logo](https://github.com/a-hurst/klibs/raw/austin_bugfixes/klibs/resources/splash.png)

KLibs is a simple-but-powerful object oriented framework for building experiments in cognitive psychology, written in the Python language. 

The aim of this project is to provide a simple framework for the writing of experiments that is as quick and simple as it is powerful and flexible. Currently somewhere between an alpha and beta in terms of stability. Largely undocumented, but not for long!

## Dependencies

In order to install KLibs on your system, the sdl2, sdl2\_ttf, sdl2\_mixer, and portaudio libraries must already be installed.

Under macOS/OS X, you can easily do this with a package manager such as [Homebrew](https://brew.sh):

> brew install sdl2 sdl2\_ttf sdl2\_mixer portaudio

Under Debian/Ubuntu linux, the key dependencies can be installed using apt-get:

> sudo apt-get install git libsdl2-2.0-0 libsdl2-ttf-2.0-0 libsdl2-mixer-2.0-0 portaudio19-dev

You will also need the pip Python package manager to install klibs on your system. If running 'pip --version' on your system results in a "command not found" message, you can install it by running

> sudo easy\_install pip

Klibs requires Python 2.7 to run, and has not yet been updated to support Python 3.x.

## Installation

After all the dependencies have been installed, you can then install klibs by running

> pip install . --process-dependency-links

from the Terminal while in the klibs folder. The setup script should automatically install all the Python packages KLibs requires to run. Note that if you are using the default system-installed version of Python on macOS, you will need to preface the `pip install` command with `sudo -H` for the command to work.

If you want to use the Slack messaging feature in klibs, you will need to install the 'slacker' package via pip:

> pip install slacker
