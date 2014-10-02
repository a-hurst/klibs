__author__ = 'jono'

import sys
import os
import re


class CommandLinePalette:
	BLK = "\033[0;30m"
	BLKB = "\033[1;30m"
	RED = "\033[0;31m"
	REDB = "\033[1;31m"
	GRN = "\033[0;32m"
	GRNB = "\033[1;32m"
	YEL = "\033[0;33m"
	YELB = "\033[1;33m"
	BLU = "\033[0;34m"
	BLUB = "\033[1;34m"
	PUR = "\033[0;35m"
	PURB = "\033[1;35m"
	CYN = "\033[0;36m"
	CYNB = "\033[1;36m"
	WHT = "\033[0;37m"
	WHTB = "\033[1;37m"
	DEF = "\033[0;99m"




c = CommandLinePalette

PROMPT_STR = "{0}>>> {1}".format(c.BLU, c.DEF)

class Column:
	__name = ""
	__type = None
	__nullable = False
	__is_id = False
	__types = ["integer", "text", "real", "blob", "null"]

	def __init__(self, col_name, col_type=None, allow_null=False, is_id=False):
		self.__name = col_name
		self.__type = col_type
		self.__nullable = allow_null
		self.__is_id = is_id

	def build(self):
		pass

	@property
	def col_name(self):
		return self.__name

	@col_name.setter
	def col_name(self, name_str):
		# todo: must also check to be sure the string is *valid*
		if type(name_str) is str:
			self.__name = name_str
		else:
			raise TypeError("Column.__col_name must be a string")

	@property
	def col_type(self):
		return self.__type

	@col_type.setter
	def col_type(self, type_str):
		if type_str in self.__types:
			self.__col_type = type_str
		else:
			raise TypeError("Column.__col_type must be a string representation of a valid sqlite3 type (ie."
			                "one of 'integer','text', 'real', 'blob', 'null'")

	@property
	def allow_null(self):
		return self.__allow_null

	@allow_null.setter
	def allow_null(self, allow):
		if type(allow) is bool:
			self.__allow_null = allow
		else:
			raise TypeError("Column.__allow_null must be boolean.")

	@property
	def is_id(self):
		return self.__is_id

	@is_id.setter
	def is_id(self, status):
		if type(status) is bool:
			self.__is_id = status
		else:
			raise TypeError("Column.__is_id must be boolean.")


class Table:
	__columns = []
	__name = []
	c = CommandLinePalette

	def __init__(self, name):
		if type(name) is str:
			self.__name = name
		else:
			raise TypeError("Table.__name must be a string.")

		self.__columns.append(Column("id", "integer", False, True))

	def build(self):
		pass

	def add_column(self):
		col = None
		print "{0}Columns! Whee!".format(self.c.BLU)
		cname = ""
		ctype = ""
		cnull = False

		cnamed = False
		ctyped = False
		cnulled = False
		while not cnamed:
			print "{0}Please provide a {1}name{0} for the new column:{2}".format(self.c.WHTB, self.c.CYNB, self.c.DEF)
			cname = raw_input(PROMPT_STR)
			if alphanum(cname):
				c = Column(cname)
				cnamed = True
			else:
				# todo: provide a voluntary exit from this loop
				print "Oops, table & columns names can only contain lower-case letters or underscores. Once more!"
		print "{0}Ok. Now we have to assign the {1}{2}{0} column a {3}type{0}{4}".format(self.c.BLU, self.c.PUR, cname, self.c.CYNB, self.c.DEF)
		while not ctyped:
			print "{0}Columns must be one of {1}5{0} types, each of which corresponds to a Python basic type:{2}".format(self.c.BLU, self.c.CYNB, self.c.DEF)
			print "{0}       SQLite3  =>  Python{1}".format(self.c.WHTB, self.c.DEF)
			print "{0}({1}1{0})    {2}TEXT     {0}=> {2}str{1}, {2}unicode{3}".format(self.c.BLU, self.c.GRN, self.c.CYNB, self.c.DEF)
			print "{0}({1}2{0})    {2}INTEGER  {0}=> {2}int{1}, {2}long{3}".format(self.c.BLU, self.c.GRN, self.c.CYNB, self.c.DEF)
			print "{0}({1}3{0})    {2}REAL     {0}=> {2}float{3}".format(self.c.BLU, self.c.GRN, self.c.CYNB, self.c.DEF)
			print "{0}({1}4{0})    {2}BLOB     {0}=> {2}buffer{3}".format(self.c.BLU, self.c.GRN, self.c.CYNB, self.c.DEF)
			print "{0}({1}5{0})    {2}NULL     {0}=> {2}NONE{3}".format(self.c.BLU, self.c.GRN, self.c.CYNB, self.c.DEF)
			ctype = raw_input(PROMPT_STR)
			if ctype in ['1', '2', '3', '4', '5']:
				c.col_type = ctype
				ctyped = True
			else:
				# todo: provide a voluntary exit from this loop
				print "{0}Error: {1}Please choose a {4}number{0}. Between 1. And 5.\n\t{2}Sigh. You depress me terribly.{3}".format(self.c.RED, self.c.BLU, self.c.YEL, self.c.DEF, self.c.CYNB)
		print "{0}Great, almost done!{1}".format(self.c.BLU, self.c.DEF)
		while not cnulled:
			print "{0}When new rows are added to the table, should this column be {1}required{0}?{2}".format(self.c.BLU, self.c.RED, self.c.DEF)
			print "{0}Answer with ({1}y{0})es or ({1}n{0})o.{2}".format(self.c.BLU, self.c.GRN, self.c.DEF)
			cnull = raw_input(PROMPT_STR)
			if cnull == "y" or cnull == "n":
				c.allow_null = cnull == "y"
				cnulled = True
			else:
				# todo: provide a voluntary exit from this loop
				print "{0}Error:{1}Invalid response.\n\t{2}Yes is spelled with a \"{3}y{2}\". No is spelled with an"\
				 "\"{3}n{2}\". C'mon big guy, you can do it.{4}".format(self.c.RED, self.c.BLU, self.c.YEL, self.c.CYNB, self.c.DEF)
		self.__columns.append(c)

		return None

	@property
	def num_columns(self):
		return len(self.__columns)

	@property
	def buildable(self):
		return self.num_columns > 0



class Database:
	__tables = []
	__name = []
	c = CommandLinePalette

	def __init__(self, name):
		if type(name) is str:
			self.__name = name
		else:
			raise TypeError("Database.__name must be a string.")

	def build(self):
		pass

	def add_table(self):
		tdone = False
		tnamed = False
		t = None
		while not tnamed:
			print "{0}Sure! Care to furnish me with a {2}name {0}for this shiny new table?{1}".format(self.c.BLU, self.c.DEF, self.c.CYNB)
			tname = raw_input(PROMPT_STR)
			if alphanum(tname):
				t = Table(tname)
				tnamed = True
			else:
				# todo: provide a voluntary exit from this loop
				print "Oops, table & columns names can only contain lower-case letters or underscores. Once more!"
		print "{0}Great. You can ({2}a{0})dd columns immediately  or else ({2}s{0})kip this for now.{1}".format(self.c.BLU, self.c.DEF, self.c.GRN)
		add_cols = raw_input(PROMPT_STR)
		if add_cols == "a":
			while not tdone:
				t.add_column()
				print "{2}Success!{0} Do you need to ({1}a{0})dd another or shall we ({1}s{0})ave this table for now?{3}".format(self.c.BLU, self.c.GRN, self.c.GRNB, self.c.DEF)
				next = raw_input(PROMPT_STR)
				if next == "s":
					tdone = True
		self.__tables.append(t)
		return True

	@property
	def num_tables(self):
		return len(self.__tables)

	@property
	def buildable(self):
		if self.num_tables == 0:
			return False
		for t in self.__tables:
			if not t.buildable:
				return False
		return True



def alphanum(test_str):
	valid_chars = "_abcdefghijklmnopqrstuvwxyz"
	for c in test_str:
		if c not in valid_chars:
			return False
	return True


def get_fdir(fname_str):
	fdir = ""
	fdir_ok = False
	complaints = [
		"Sorry, that appears to be an invalid destinaton. Care to try a real one?",
		"Riiight, right, I mean I would put it there if only that were an actual location...",
		"Err, maybe I should have clarified; please choose a destination \033[0;31mon your hard drive\033[0;34m.",
		"You're just having a go at me, aren't you?",
		"You do realize that we're not in a negotiating position; right?  \n\t I mean, these are canned responses...",
		"Oh your mother must be so proud.",
		"-________________________________-",
		"We are not amused. Neither are we able to put your file anywhere. \n\tI do have indexing to do, ya know.",
		"I'll give you a hint, the answer/looks/something/like/this",
		"\"Just be a CRON job like your father,\" she told me, but did I listen? Sigh.",
		"No one's home; but a sign on the door reads, \"You can't lose if you don't play.\" Go figure."
	]
	first_attempt = True
	attempts = -1
	non_attempts = 0
	while not fdir_ok:
		if not os.path.exists(fdir):
			if attempts > 10:
				print "{0}Well that takes it. I'm going to stream Netflix directly to the video card and sulk.".format(
					c.YEL)
				exit()
			if not fdir and attempts > 0:
				if non_attempts == 0:
					print "\t{0}Nowhere. The file should go nowhere. Cute.".format(c.YEL)
					non_attempts += 1
					attempts -= 1
				else:
					print "\t{0}I'm not going to reward non-behavior with clever, if biting, sarcasm.\n\t At least give me something to make fun of you for.".format(
						c.YEL)
					attempts -= 1
			elif attempts > -1:
				print "{0}\t{1}".format(c.YEL, complaints[attempts])
			print "{0}Please provide a destination for '{1}{2}.sql{0}':{3} ".format(c.BLU, c.CYNB, fname_str, c.DEF)
			fdir = raw_input(PROMPT_STR)
			attempts += 1
		else:
			fdir_ok = True
			if attempts == -1:
				print "\t{0}Great stuff. Thanks. Let's build some schema!\n{1}".format(c.YEL, c.DEF)
			if attempts == 0:
				print "\t{0}I knew you had it in you. Ok! Let's get started!\n{1}".format(c.YEL, c.DEF)
			if attempts > 0:
				attempt = None
				if attempts == 1:
					attempt = str(attempts) + "nd"
				elif attempts == 2:
					attempt = str(attempts) + "rd"
				else:
					attempt = str(attempts) + "th"
				print "\t{0}Phewf. Ok. {1} time's the charm, right? ...You sure you're up for this?{2}\n".format(c.YEL,
				                                                                                                 attempt,
				                                                                                                 c.DEF)

	return fdir


def get_fname():
	fname_ok = False
	fname_str = None
	while not fname_ok:
		print "{0}Please choose a filename for the schema (I'll add the {3}.sql{0} extension for you)." \
		      "\nRemember to avoid using the following characters:'{1}:\/\\{0}'\nAlternatively, you may " \
		      "({1}q{0})uit.{2}".format(c.WHT, c.GRNB, c.DEF, c.CYNB)
		print "{0}Schema file name:{1}".format(c.BLU, c.DEF)
		fname_str = raw_input(PROMPT_STR)
		if fname_str == "q":
			print "{0}\tFine. I didn't want to play with you either.{1}".format(c.YEL, c.DEF)
			exit()
		bad_chars = re.search("([\:\\/])", fname_str)
		if not bad_chars:
			return fname_str


# -----------------------------------------------=[ SCRIPT STARTS ]=-------------------------------------------------- #



fname = ""
fdir = ""
fpath = ""
f = None

structure = Database(fname.rstrip(".sql"))

# 01. Present introductory text & description
print "\n\n"
print "{0}                 *******************************".format(c.WHTB)
print "{0}                 * {1}       SchemaStreama'       {2}*".format(c.WHTB, c.PURB, c.WHTB)
print "{0}                 *******************************\n{1}".format(c.WHTB, c.DEF)
print "{0}This utility will help you build simple SQL schemas for use with SQLite3,\nand specifically Python's SQLite3" \
      "module. Type ({1}?{0}) at any time for assistance.\n{2}".format(c.WHT, c.GRN, c.DEF)
if len(sys.argv) == 1:
	fname = str(get_fname())
	fdir = get_fdir(fname)

if len(sys.argv) == 2:
	fname = sys.argv[1].rstrip(".sql")
	fdir = get_fdir(fname)

if len(sys.argv) == 3:
	fname = sys.argv[1]
	fdir = sys.argv[2]

fpath = os.path.join(fdir, fname + ".sql")

# todo: confirm path with user before evaluating
# 02. Verify that the newly created path exists and is writable, then create the database class
if os.path.exists(fpath):
	print "The file '{0}' exists. You may (o)verwrite it or (q)uit.".format(fpath)
	overwrite = raw_input(PROMPT_STR)
	if overwrite == "o":
		f = open(fpath, "w+")
	elif overwrite == "q":
		print "\tFair enough; until next time, fare stranger.{0}".format(c.DEF)
		exit()
	else:
		print "\tAll you had to do was pick the letter 'o' or the letter 'q'. I can't work under these conditions;\
		I'll be in my trailer."
		exit()

db = Database(fname.rstrip(".sql"))

# 03. Enter table construction loop
print "{0}Now to create some tables. Names can include a-z, A-Z and the underscore character only.{1}".format(c.BLU,
                                                                                                              c.DEF)
done = False
while not done:
	print "{3}Select one:{0} \n\t({1}a{0})dd a table \n\t({1}e{0})dit a table \n\t({1}d{0})elete a table"\
	 "\n\t({1}r{0})eview the schema \n\t({1}b{0})uild the schema \n\t({1}q{0})uit{2}".format(
		c.BLU, c.GRNB, c.DEF, c.WHTB)
	user_action = raw_input(PROMPT_STR)
	if user_action == "q":
		print "{0}\tPEACE SON.{1}".format(c.YEL, c.DEF)
		quit()
	elif user_action == "b":
		if not structure.buildable:
			print "{0}Error:{1}You must create at least one table with at least one column to build a schema. {2}\tI can't" \
			      " do everything, you know.{3}".format(c.RED, c.BLU, c.YEL, c.DEF)
		else:
			structure.build()
	elif user_action == "e":
		if structure.num_tables == 0:
			print "{0}No tables to edit!\n{1}I think that's called putting the card before the horse...{2}".format(c.BLU,
			                                                                                                       c.YEL,c.DEF)
	else:
		db.add_table()


exit()