#Recording Data

Chances are if you want to use the the KLibs framework to create something, you want that something to be able to record data. Like most parts of writing experiments, KLibs makes recording data from your experiment simple and straightforward. Outlined here are where KLibs stores data and in what format, how to  record responses, values, and trial details from your experiment, and how to browse and work with the data format that KLibs uses.

## The Database File

All recorded data from your experiment is saved into an SQL database file, which can be found in your experiment's __ExpAssets__ folder with the name of your KLibs project and the extension .db. For example, the database for a KLibs project entitled __posner_replication__ would be found under `ExpAssets/posner_replication.db`. KLibs also automatically saves a duplicate copy of your experiment's database in the same folder with the extension .backup after .db, in case the main database becomes corrupted or is edited accidentally while reviewing results.

To open and read the project's SQL database file, you can use the free cross-platform [DB Browser for SQLite](http://sqlitebrowser.org/) or any other program that can open SQLite Databases. Each database contains four tables by default: **events**, **logs**, **participants**, and **trials**.

### Events

_wait for jon_

### Logs

_Error/eyelink logging?_

### Participants

The participants table is where demographics for your participants are recorded (sex, age, and handedness by default), as well as the date and time of the creation of the participant's data (i.e. when they started the experiment) and the version of KLibs that was used to run the experiment for that participant. _say something about userhash and randomseed_ 

### Trials

The trials table contains the information recorded for each trial of your experiment, as well as the participant ID for the trial (corresponding to the row IDs in the **participants** table). This is where the bulk of the data from your experiment will be recorded. 

  
The number and names of variables recorded in each table are defined in the \_schema.sql file, found in the `ExpAssets/Config/` directory of your project. This file is used to generate the structure of the .db file, which must be removed 

##Defining Your Data Structure

The structure of the database for your KLibs project is defined by the `[projectname]_schema.sql` file found in the `ExpAssets/Config/` folder of your project. Whenever KLibs runs and no database file exists, it will create a new one based on the contents of this file. By defualt this database consists of four tables (discussed above), each containing some types of data that it will store. Here is the code defining the structure of the 'trials' table for a fresh KLibs experiment:

		CREATE TABLE trials (
		id integer primary key autoincrement not null,
		participant_id integer key not null,
		block_num integer not null,
		trial_num integer not null
	);

The first and last lines of this code create a table called 'trials' in the database. The four lines contained within the parentheses each name a column in the table and define what type of data that column can contain. For example, the 5th line defines a column named `trial_num`, which will contain integers, and cannot be empty (indicated by `not null`). In the vast majority of cases, column definitions are as simple as adding a comma to the end of the last line, then adding `[varaible_name] text not null` to a new line underneath it, replacing `[variable_name]` with whatever you want to name the column.

As an example, imagine you are creating a simple cueing experiment and want to record three things for each trial: the cue location, the target location, and the reaction time for these targets. To create columns for these variables in the database, you would add a line for each of them into the 'trials' table in the \_schema.sql file:
	
		CREATE TABLE trials (
		id integer primary key autoincrement not null,
		participant_id integer key not null,
		block_num integer not null,
		trial_num integer not null,
		cue_loc text not null,
		target_loc text not null,
		reaction_time text not null
	);
	
The next time you run your KLibs experiment, a new database containing the new columns you have defined should be generated automatically. Note that if a database and backup .db already exist, you will need to delete or move them elsewhere before a new database will be generated from your schema file.

## Getting Data From Your Experiment

Creating the structure of your experiment's database is important, but it isn't much use if you don't have any data to store in it. Thankfully, KLibs makes recording data from your experiment program incredibly simple. All data recording is done in the following block of code, found at the end of the `def trial(self):` section of your project's `experiment.py` file:
	
		return {
		"block_num": Params.block_number,
		"trial_num": Params.trial_number
	}

This code is run at the end of every trial of a KLibs experiment, and adds a row of values for that trial to the 'trials' table in the database. Each column defined in the database must have a corresponding definition in this code, with the exception of 'id' and 'participant_id', which are filled with values elsewhere. Each column name is followed by a variable, which is used to fill in the value for the column for the trial.

Return for a moment to the example of the simple cueing experiment in the previous section. Let's say your experiment's cue and target locations are stored in variables called `self.cue_location` and `self.target_location`, and that you are recording reaction times using the `keypress_listener.response()` function from the KLResponseCollectors module. The code to write the values for these variables to the their corresponding column in the database for each trial would look like this:

	return {
		"block_num": Params.block_number,
		"trial_num": Params.trial_number,
		"cue_loc": self.cue_loc,
		"target_loc": self.target_loc,
		"reaction_time": self.rc.keypress_listener.response(False, True) # gets RT in seconds
	}

_If everything is working properly, you should see the values of the_

##Exporting Data

The SQLite database structure used by KLibs is great for organizing your data into useful categories, but is not the easiest format work with when analyzing your data. To export your data into a more statistics-friendly format, simply run
	
	klibs export /path/to/project/folder
	
, replacing `/path/to/project/folder` with the path to the main folder of your KLibs project (the one containing **experiment.py**). If you are running KLibs on a Mac, you can type `klibs export ` into Terminal, followed by a space, and then drag your KLibs project folder in Finder to the Terminal window. Terminal should automatically fill in the path to the folder you just dragged.

Upon running the export command, KLibs will create individual tab-separated text files containing the trial data for each participant in a folder called **Data** in the `ExpAssets/` directory, which KLibs will create if it does not exist already. These files can be opened by any text editor or spreadsheet software, and can be easily read in to statistical software such as R and SPSS.