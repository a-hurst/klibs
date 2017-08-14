# klibs
A simple object-oriented framework for building experiments in cognitive psychology. Currently somewhere between an alpha and beta in terms of stability. Largely undocumented, but not for long!

## Dependencies
In order to install KLibs on your system, the sdl2, sdl2_ttf, sdl2_mixer, and portaudio libraries must already be installed.

Under macOS/OS X, you can easily do this with a package manager such as [Homebrew](https://brew.sh):

> brew install sdl2 sdl2_ttf sdl2_mixer portaudio

Under Debian/Ubuntu linux, the key dependencies can be installed using apt-get:

> sudo apt-get install python-pip libsdl2-2.0-0 libsdl2-ttf-2.0-0 libsdl2-mixer-2.0-0 portaudio

Klibs requires Python 2.7 to run, and has not yet been updated to support Python 3.x.

## Installation
After all the dependencies have been installed, you can then install klibs by running

> python setup.py install

from the Terminal in the klibs folder. 

The setup script should automatically install all the Python packages KLibs requires to run. If you want to use the Slack messaging feature in klibs, you will need to install the 'slacker' package via pip:

> pip install slacker
