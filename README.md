## ![KLibs logo](https://github.com/a-hurst/klibs/raw/austin_bugfixes/klibs/resources/splash.png)

KLibs is a simple-but-powerful object oriented framework for building experiments in cognitive psychology, written in the Python language. 

The aim of this project is to provide a simple framework for the writing of experiments that is as quick and simple as it is powerful and flexible. Currently somewhere between an alpha and beta in terms of stability. Largely undocumented, but not for long!

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

You will also need the pip Python package manager to install KLibs on your system. If running 'pip --version' on your system results in a "command not found" message, you can install it by running ```sudo easy_install pip```.

KLibs requires Python 2.7 to run, and has not yet been updated to support Python 3.x.

## Installation

After all the prerequisite libraries have been installed, you can run the following command to install KLibs and all its Python dependencies:

```
pip install git+https://github.com/a-hurst/klibs.git --process-dependency-links
```

Note that if you are using the default system-installed version of Python on macOS, you will need to preface the `pip install` command with `sudo -H` for the command to work.

If you want to use the Slack messaging feature in KLibs, you will need to install the 'slacker' package by running ```pip install slacker```.
