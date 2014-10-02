CREATE TABLE participants (
	id integer primary key autoincrement not null,
	userhash text not null, 
	gender text not null, 
	age integer not null, 
	handedness text not null,
	created text not null,
	modified text not null --not implemented yet (ie. it is set equal to created at creation but no modification logic exists in Klibs
);

CREATE TABLE trials (
	id integer primary key autoincrement not null,
	participant_id integer key not null,
	block_num integer not null,
	trial_num integer not null,
	practicing integer not null,
	t_stream text not null,
	t_char text not null,
	t_pos integer not null,
	init_by text not null,
	cued text not null,
	rt real not null, -- reaction time
  response integer not null
);
