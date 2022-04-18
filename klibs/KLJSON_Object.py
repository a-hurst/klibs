__author__ = 'Jonathan Mulle & Austin Hurst'

import io
import re
import json


class AttributeDict(dict):
	"""A Python dictionary that lets you access items like you would object attributes.
	For example, for the following AttributeDict::
	
		 d = {'one': 1, 'two': 2}
	
	you could get the value of 'one' through either d['one'] or d.one.
	
	"""
	def __getattr__(self, key):
		return self[key]

	def __setattr__(self, key, value):
		self[key] = value


class JSON_Object(AttributeDict):
	"""A class for importing JSON objects such that you can access their attributes the same way
	you would a Python object. For example, if you imported a .json file with the following
	contents:
	
	.. code-block:: json

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

		# import the JSON file to a JSON_Object
		wordbank_path = os.path.join('path', 'to', 'wordbank.json')
		wordbank = JSON_Object(wordbank_path)

		# access the elements of the JSON_Object as object attributes
		for word in wordbank.study_words:
			print(word.word, word.syllables, word.type)


	Alternatively, you could access the objects' contents like you would a Python dictonary::

		for word in wordbank['foil_words']:
			print(word['word'], word['syllables'], word['type'])
	

	Note that all objects and variable names in the imported JSON file must be valid Python
	object attribute names (i.e. no spaces, periods, special characters, etc.), and will result
	in a ValueError during import if an invalid attribute name is encountered.

	Args:
		json_file_path (:obj:`str`): The path of the JSON file to import.

	"""

	def __init__(self, json_file_path):
		try:
			json_file = io.open(json_file_path, encoding='utf-8')
			json_dict = json.load(json_file, object_hook=self.__objectify)
			for key in json_dict:
				setattr(self, key, json_dict[key])
		except ValueError:
			err = "'{0}' is not a valid JSON file.".format(json_file_path)
			raise RuntimeError(err)
		except AttributeError as e:
			raise ValueError(e)
	
	def __objectify(self, dict_obj):
		# Check if JSON object name is a valid Python class attribute name
		valid_attr_name = re.compile(r"^[A-Za-z_]+([A-Za-z0-9_]+)?$")
		for key in dict_obj.keys():
			if re.match(valid_attr_name, key) == None:
				e = u"'{0}' is not a valid Python class attribute name ".format(key)
				e += u"(try removing spaces and special characters)."
				raise AttributeError(e)
		return AttributeDict(dict_obj)
