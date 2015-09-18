/*

******************************************************************************************
						NOTES ON HOW TO USE AND MODIFY THIS FILE
******************************************************************************************
This file is used at the beginning of your project to create the database in 
which trials and participants are stored.

As the project develops, you made to chance the number of columns, add other tables, 
or change the names/datatypes of columns that already exist.

To do this, modify the document as needed, then, in your project, instead of running

PROJECT_NAME.run()

use

PROJECT_NAME.db.rebuild()

But be warned: THIS WILL DELETE ALL YOUR CURRENT DATA. The database will be completely 
destroyed and rebuilt. If you wish to keep the data you currently have, be sure to run 
PROJECT_NAME.db.export() first. 

*/

CREATE TABLE participants (
	id integer primary key autoincrement not null,
	userhash text not null,
	random_seed text not null,
	sex text not null,
	age integer not null, 
	handedness text not null,
  	created text not null
);

CREATE TABLE trials (
	id integer primary key autoincrement not null,
	participant_id integer key not null,
	block_num integer not null,
	trial_num integer not null,
);
