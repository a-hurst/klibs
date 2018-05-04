__author__ = 'jono'

import io
import re
import json


class AttributeDict(dict):
	'''A Python dictionary that lets you access items like you would object attributes.
	For example, the AttributeDict d = {'one': 1, 'two': 2}, you could get the value of 'one'
	through either d['one'] or d.one.
	'''
	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value


class JSON_Object(object):
	'''A class for importing JSON objects such that you can access their attributes the same way
	you would a Python object. For example, if you imported a .json file with the following
	contents:

	:: json

		{
		"study_words": [
			{"word":"cognition", "syllables":3, "type":"noun"},
			{"word":"experimental", "syllables":5, "type":"verb"}
			],
		"foil_words": [
			{"word":"cognitive", "syllables":3, "type":"adjective"},
			{"word":"experiment", "syllables":4, "type":"noun"}
			]
		}

	you could then import and access its contents like this::

		wordbank_path = os.path.join('path', 'to', 'wordbank.json')
		wordbank = JSON_Object(wordbank_path)
		print(wordbank.study_words)
		for word in wordbank.study_words:
			print(word.word, word.syllables, word.type)

	Alternatively, you could access the objects' contents like you would a Python dictonary::

		for word in wordbank['foil_words']:
			print(word['word'], word['syllables'], word['type'])
	
	Note that all objects and variable names in the imported JSON file must be valid Python
	object attribute names (i.e. no spaces, periods, special characters, etc.), and will result
	in a ValueError during import if an invalid attribute name is encountered.

	'''

	def __init__(self, json_file_path):
		self.file_path = json_file_path
		try:
			json_file = io.open(self.file_path, encoding='utf-8')
			json_dict = json.load(json_file, object_hook=self.__objectify)
			for key in json_dict:
				setattr(self, key, json_dict[key])
		except ValueError:
			raise ValueError("JSON file is poorly formatted. Please check syntax.")
	
	def __objectify(self, dict_obj):
		# Check if JSON object name is a valid Python class attribute name
		valid_attr_name = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,30}|(__.*__)")
		for key in dict_obj.keys():
			if re.match(valid_attr_name, key) == None:
				print(u"Error: '{0}' is not a valid Python class attribute name ".format(key) +
					u"(try removing special characters).\n")
				raise RuntimeError("Error encountered loading json_object")
		return AttributeDict(dict_obj)
