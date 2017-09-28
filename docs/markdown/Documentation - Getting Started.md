# Getting Started

So, you want to write a cognitive psychology experiment. You've come to the right place! The KLibs framework is here to make that task a lot easier, without sacrificing the flexibility offered by writing your experiments in the Python programming language. 

## What is KLibs?
KLibs is an open-source framework for the Python programming language intended to greatly simplify the process of writing your own cognitive psychology and neuroscience experiments while retaining the flexibility and power offered by programming your own experiments.

KLibs offers many built-in functions usable right out of the box for drawing shapes, interacting with eye-tracking devices, receiving and recording responses, working in degrees of visual angle, and much more, saving you the time required to write all these functions from scratch and letting you get to the things you care about.

## Creating Your First Project
Once you have installed KLibs, creating your first project is easy: first, open a Terminal window and navigate to the directory you want to put your project (e.g. `cd ~/Documents/ExperimentCode`). Then, type `klibs create myProjectName`, replacing "myProjectName" with whatever you want to call your project. KLibs will then guide you through the short setup process of initializing your project before creating a folder with the basic building blocks of a KLibs experiment.

## The Anatomy of a KLibs Project

After running `klibs create`, you will find a new folder in the directory you ran it in with the name of your project. In this folder, you will find one file, _experiment.py_, and one folder, _ExpAssets_. 

### experiment.py

The experiment.py file contains the basic structure of an experiment, and is where you will add most of your experiment code. If you open this file, you will notice that it already contains some code:

	import klibs

	__author__ = "My Name"

	from klibs import Params

	class myProjectName(klibs.Experiment):

		def __init__(self, *args, **kwargs):
			super(myProjectName, self).__init__(*args, **kwargs)

		def setup(self):
			Params.key_maps['myProjectName_response'] = klibs.KeyMap('myProjectName_response', [], [], [])

		def block(self):
			pass

		def setup_response_collector(self):
			pass

		def trial_prep(self):
			pass

		def trial(self):

			return {
				"block_num": Params.block_number,
				"trial_num": Params.trial_number
			}

		def trial_clean_up(self):
			pass

		def clean_up(self):
			pass

All the subjections, such as `setup`, `block`, `trial_prep`, and `clean_up` all have their own purposes. We will break these down in detail later. Once you run an experiment for the first time, a second file called experiment.py__c__ will be created alongside experiment.py. This because KLibs will __c__ompile your experiment.py file each time it runs to optimize your experiment's performance. *explain that pyc files cannot be edited and that you should ignore this file for the most part. Also, does the pyc even get run, ever?*

### ExpAssets

The ExpAssets folder contains several files and folders that are key to your experiment, including a database for storing your collected data, experiment parameters, and any images, fonts, or other materials that you wish to include in your experiment:

##### myProjectName.db
This file is an SQL database of all the recorded data from an experiment. KLibs automatically creates this file when an experiment is first run, and maintains a backup copy of database entitled myProjectName.db.backup in the same folder in case the database becomes corrupted or damaged in some way.

##### .versions/
The .versions folder, which is invisible by default and must be opened either through the terminal or by using Go > Go To Folder... (⇧⌘G) in Finder, contains a version of the experiment program corresponding to each participant ID as it was at the time the participant was ran. This is useful for when you make changes to an experiment part-way through or when you need to revert to a previous version of the experiment, as you will be able to tell which participants were run with which version of the experiment.

##### Config/myProjectName_params.py
The \_params.py file serves as a configuration file for the experiment program, allowing you to easily enable and disable functions such as eye-tracking, demographics collection, practice blocks, and more. This is the file where you specify the number of trials and trials per block. You can also change properties such as the default background fill and stimulus colours for the experiment, along with default font and default font size.

##### Config/myProjectName_schema.sql

##### Config/myProjectName_messaging.csv

##### Config/myProjectName_config.csv

*no longer exists, replaced by independant_vars.py*

The \_config file is a CSV file that is used to generate trials automatically unless `Params.manual_trial_generation` is explicitly set to "TRUE" in your experiment. The first line of this file is commented out (i.e. preceeded with a "#") and does not effect the experiment. The second line contains the names of the categorical variables you wish to change between trials follwed by the ".param" prefix, such as `cue_location.param`.

### experiment.py

The experiment.py file is the core of your experiment, and where you will add most or all of your code. This file is where you add the code to include KLibs libraries, display stimuli, collect responses, and define the sequence of events on a given trial.


##### imports

The import sections is where libraries are imported for use in the experiment. To import a library from klibs, use `from klibs import Library`, replacing "Library" with the name of the KLibs library you wish to use (e.g. KLUtilities). You can then call functions from these libraries in the body of your experiment using the syntax 
	
	Library.function(arguments)

, where "Library" is the name of the library containing the function, "function" is the name of the function in that library you wish to use, and "arguments" are the arguments you want to pass to that function.   

For example, if you want to use the `deg_to_px()` function from the KLUtilities library, which converts degrees of visual angle to pixels (the standard KLibs unit of measurement), you would use

	from klibs import KLUtilities	# In the imports section of experiments.py
	...
	KLUtilities.deg_to_px(deg)	# Somewhere in the body of experiments.py

If you are going to be using functions from a library often in your experiment, you can give the library a shorthand name by adding `as lib` at the end of the import string, replacing "lib" with the shorthand name you want to give the library. For instance, the above example could be abbreviated in this was like so:
	
	from klibs import KLUtilities as util	# In the imports section of experiments.py
	...
	util.deg_to_px(deg)	# Somewhere in the body of experiments.py

##### \_\_init__

##### setup

##### block

##### setup\_response_collector

##### trial_prep

The contents of the trial_prep section are run before every trial of the experiment. Functions in this section might include clearing the screen to a default state, or preparing images or text for display on the screen.

##### trial

##### trial\_clean_up

##### clean_up


## Running KLibs

To run a KLibs experiment, simply navigate to the project folder using the terminal and run `klibs run screensize`, replacing "screensize" with the diagonal size of the monitor in inches of the current computer. For example, on a MacBook Air with a 13" display you would launch your experiment with `klibs run 13`. You will need to have a project with some content before you can run it, so you can try this out on the Posner cueing paradigm example included in KLibs.


 