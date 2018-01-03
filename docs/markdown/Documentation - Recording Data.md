# Recording Data

Flashing shapes and collecting responses is all good and fun, but they're probably not much use to you as a researcher if you can't store the data from your trials somewhere. In KLibs, all data apart from EyeLink EDF files is stored in a lightweight SQLite database, which we use for collecting data because of the flexibility and organization it allows for when recording and exporting data. Databases usually aren't that nice to work with unless you already have experience with them, so KLibs provides you with simple Python and command-line interfaces for writing and exporting data that don't require any prior knowledge of SQL to use.

## The Database File

Your project's SQLite database file can be found in your experiment's __ExpAssets__ folder with the name of your KLibs project and the extension .db. For example, the database for a KLibs project entitled __PosnerCueing__ would be found under `ExpAssets/PosnerCueing.db`. KLibs also automatically saves a backup copy of your experiment's database every time the experiment is run in the same folder with the extension .db.backup, in case the main database becomes corrupted or is edited accidentally.

To open and read your project's database, you can use the free cross-platform [DB Browser for SQLite](http://sqlitebrowser.org/) or any other program that can open SQLite Databases. Each database contains four tables by default: **events**, **logs**, **participants**, and **trials**, but you only need to concern yourself with the last two:

### Participants

The participants table is where demographics for your participants are recorded (sex, age, and handedness by default), as well as the date and time of the creation of the participant's data (i.e. when they started the experiment) and the version of KLibs that was used to run the experiment for that participant. 

The *userhash* is a unique anonymous identifier for each participant that is generated during demographics collection. If demographics collection is skipped (e.g. during development mode), one will be generated anyway.

The *random\_seed* is the seed value that Python's built-in 'random' module uses as its "seed value" when generating random values. If you want to run an experiment with the exact same order of trial factors and random values as a previous run, you can copy this value from the database and run it using `klibs run -s [random_seed]`, replacing `[random_seed]` with the 'random\_seed' stored in the database for the run you want to reproduce.

### Trials

The trials table contains the information recorded for each trial of your experiment, as well as the participant ID for the trial (corresponding to the row IDs in the **participants** table). This is where the bulk of the data from your experiment will be recorded, and is the section you will likely need to edit before you can start recording data.

## Defining Your Data Structure

The structure of the database for your KLibs project is defined by the `[projectname]_schema.sql` file found in the `ExpAssets/Config/` folder of your project. Whenever KLibs runs and no database file exists, it will create a new one based on the contents of this file. By default this database consists of four tables (discussed above), each containing the names and data types of the columns to be created within them. Here is the code defining the structure of the 'trials' table for a fresh KLibs experiment:

```sql
CREATE TABLE trials (
    id integer primary key autoincrement not null,
    participant_id integer not null references participants(id),
    block_num integer not null,
    trial_num integer not null
);
```

The first and last lines of this code create a table called 'trials' in the database. The four lines contained within the parentheses each name a column in the table and define what type of data that column can contain. For example, the 5th line defines a column named `trial_num`, which will contain integers, and cannot be empty (indicated by `not null`). In the vast majority of cases, column definitions are as simple as adding a comma to the end of the last line, then adding `[varaible_name] text not null` to a new line underneath it, replacing `[variable_name]` with whatever you want to name the column.

As an example, imagine you are creating a simple cueing experiment and want to record three things for each trial: the cue location, the target location, and the reaction time for these targets. To create columns for these variables in the database, you would add a line for each of them into the 'trials' table in the \_schema.sql file:

```sql
CREATE TABLE trials (
    id integer primary key autoincrement not null,
    participant_id integer not null references participants(id),
    block_num integer not null,
    trial_num integer not null,
    cue_loc text not null,
    target_loc text not null,
    reaction_time text not null
);
```
	
The next time you run your KLibs experiment, a new database containing the new columns you have defined should be generated automatically. Note that if a database already exists, you will need to rebuild it with the command `klibs db-rebuild` or move it elsewhere before relaunching your experiment.

## Writing to the Database

Defining the schema for your database is one half of the equation, the other is writing data to your database. You might have noticed a block of code like this at the end of the 'trial' section of your project's `experiment.py` file:

```python
	return {
		"block_num": P.block_number,
		"trial_num": P.trial_number
	}
```

When a trial in an experiment ends, it returns a Python Dict (dictionary) that must contain the names and values of all columns in the 'trials' table in the database, save for 'id' and 'participant_id' (these are filled in automatically). If this section is missing a column name or has an extra column name, it will crash your experiment with an error. Thus, after adding columns for the things you want to record at the end of each trial to the 'trials' table schema in the 'schema.sql' file, you will need to update this section of your 'experiment.py' file accordingly.

For example, after editing your schema to add the 'cue\_loc', 'target\_loc', and 'reaction\_time' columns to the 'trials' table as shown in the previous section (and rebuilding your database to reflect your additions), you would then edit your return section to look something like this:

```python
	return {
		"block_num": P.block_number,
		"trial_num": P.trial_number,
		"cue_loc": self.cue_loc,
		"target_loc": self.target_loc,
		"reaction_time": rt # value returned from ResponseCollector
	}
```

That's it! If everything worked correctly, your trial data should now be written to your database at the end of each trial. Remember that any changes to the database schema will require you to rebuild your database, causing you to lose all data recorded up to that point, so make sure to export your data and make a copy of your database somewhere safe if you ever need to add a column or table partway through data collection.

## Exporting Data

Okay, so now your data's in a database. Great. How do you get it out? The answer is by the `klibs export` command. If you're already in the root of your project folder in a terminal window, just run

```
klibs export
```

This will export the data from each participant in the 'participants' table to an individual tab-delimited text file containing all their trial data in your project's 'ExpAssets/Data/' directory. Data from participants who did not complete the full number of trials for the experiment will be automatically placed in a subfolder named 'incomplete'.

If you would prefer to export data from all participants into a single tab-delimited text file, you can instead run `klibs export --combined` or `klibs export -c` for short.

For more information on the available export options, type `klibs export --help` at the command line. 