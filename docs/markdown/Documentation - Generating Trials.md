# Generating Trials

_Note: Since the event of IndependentVariables.py, most of this will have to be rewritten_

To simplify the process of creating a sequence of trials for an experiment, KLibs has a built-in feature called TrialFactory that generates a randomized list of trials for a given number of varaibles and conditions.

## Number of Blocks and Trials per Block

The number of blocks and trials per block of you experiment are set in the `[projectname]_params.py` file, found in the `ExpAssets/Config/` directory of your project. 

_Maybe make this a general params section_

## Defining Your Conditions

On every launch, TrialFactory will generate a random series of trials based on the contents of the file `ExpAssets/Config/[projectname]_config.csv`, replacing "[projectname]" with the name you gave your KLibs project. By default, the \_config.csv file looks like this:

	# Config file for [projectname]
	column_1.param, column_2.param, trial_count
	factor_1,factor_3,,
	factor_2,factor_4,,

The second row of the file contains the names of the varaibles used in the experiment. The rows below contain the factors corresponding to these variables. Note that the values in each row are separated by commas: this is how the file breaks up its information into columns and determines which factors correspond to which variables. Let's look at what a \_config.csv might look like for a simple Posner cueing paradigm:

	# Config file for posner_cueing
	cue_location.param, target_location.param, soa_interval.param
	left,left,200,
	right,right,400,
	center,,800

In this config file, we have defined three variables: cue location, target location, and stimulus onset asynchrony (interval between onset of cue and target). The cue location varaible has three factors (left, right, and center), the target location variable has two (left and right), and the stimulus onset asynchrony variable has three (200 ms, 400 ms, and 800 ms). 

*Note the two commas with nothing between them on the last line: this is how an empty field is indicated in a .csv file. In this case, it indicates to TrialFactory that there is no third factor for target location.*

*mention that you can weight factors using square brackets*

On launch, TrialFactory generates a full list of the possible different combinations of factors as many times as it can until the number of trials matches the number of trials per block (defined in \_params.py). If the number of trials given is not an exact multiple of the number of the possible combinations of factors in the config file, KLibs will fill in the remainder by generating a full list of possible trials  and sampling randomly from it without replacement. For example, a Posner cueing experiment with the \config.csv above would require 18 trials to run through every possible combination of cue location, target location, and soa once. If this experiment was run with 30 trials per block, TrialFactory would generate a full set of 18 trials, then generate a second full set and select 12 of them without replacement to add to the other 18. The order of trials is shuffled randomly before each run of the experiment.


### Using Your Variables

Using the variable values randomly shuffled for you by TrialFactory is as easy as calling the varaible by `self.[varaiablename]` in the trial_prep or trial section of your project's __experiment.py__ file. The values for these variables will change automatically on every trial of the experiment. Variables generated from the \_config.csv are all stored as string values, meaning you cannot use them directly in place of integers (i.e. numbers) or local variable names. One way to use your trial variables in your experiment is with **if else** statements. For example, if your experiment has a target and you want it to appear on the left on some trials and right on others and your target location variable in \_config.csv is called "target_loc.param", you could use the following code in `trial_prep`:
	
	self.target_location = self.left if self.target_loc == "left" else self.right

Dealing with integers is somewhat easier: you can use the `int()` function on your variable to convert the string (e.g. "400") into an actual integer (e.g. 400). For example, if you wanted the interval between your cue and target to vary from trial to trial between the three interval lengths listed in the example \_config.csv above, you would use `int(self.soa_interval)` in place of a static number to specify the interval length.

## Dealing With Continuous Variables

While many of the variables used in cognitive psychology experiments can be broken into distinct factors, such as "left"/"right", "remember"/"know", "100 ms/900 ms", etc., other variables are able to 