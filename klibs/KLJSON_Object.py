__author__ = 'jono'

import json
import unicodedata
from re import compile
from klibs.KLUtilities import iterable, now


class JSON_Object(object):
	__eval_regex__ = compile("^EVAL:[ ]*(.*)$")

	def __init__(self, json_file_path=None, decoded_data=None, child_object=False):
		self.file_path = json_file_path
		try:
			self.__items__ = self.__unicode_to_str__(json.load(open(json_file_path)) if json_file_path else decoded_data)
		except ValueError:
			raise ValueError("JSON file is poorly formatted. Please check syntax.")
		self.__objectified__ = self.__objectify__(self.__items__, not (child_object and type(decoded_data) is list))
		self.__current__ = 0
		try:
			self.keys = self.__items__.keys()
			self.values = []
			for k in self.keys:
				self.values.append(self.__dict__[k])
		except AttributeError:
			self.keys = range(0, len(self.__items__))
			self.values = self.__items__

	def __unicode_to_str__(self, content):
		"""

		:param content:
		:return:
		"""
		if type(content) is unicode:
			# convert string to ascii
			converted = unicodedata.normalize('NFKD', content).encode('ascii','ignore')

			# convert JS booleans to Python booleans
			if converted in ("true", "false"):
				converted = converted == "true"

			# run eval on Python code passed as a JSON string
			eval_statement = self.__eval_regex__.match(converted)
			if eval_statement is not None:
				converted = eval(eval_statement.group(1))
				if type(converted) is tuple:
					converted = list(converted)
				# todo: this next bit is broken, it's so unimportant I didn't even try to fix it but maybe one day
				# on the off chance that the eval returns well-formed JSON
				# try:
				# 	converted = JSON_Object(converted)
				# except ValueError:
				# 	pass

		elif type(content) in (list, dict):
			#  manage dicts first
			try:
				converted = {}  # converted output for this level of the data
				for k in content:
					v = content[k]  # ensure the keys are ascii strings
					if type(k) is unicode:
						k = self.__unicode_to_str__(k)
					if type(v) is unicode:
						converted[k] = self.__unicode_to_str__(v)
					elif iterable(v):
						converted[k] = self.__unicode_to_str__(v)
					else:
						converted[k] = v

			except (TypeError, IndexError):
				converted = []
				for i in content:
					if type(i) is unicode:
						converted.append(self.__unicode_to_str__(i))
					elif iterable(i):
						converted.append(self.__unicode_to_str__(i))
					else:
						converted.append(i)

		else:
			# assume it's numeric
			return content

		return converted

	def __find_nested_dicts__(self, data):
		"""

		:param data:
		:return:
		"""
		tmp = []
		for i in data:
			if type(i) is dict:
				tmp.append(JSON_Object(None, i, True))
			elif type(i) is list:
				tmp.append(self.__find_nested_dicts__(i))
			else:
				tmp.append(i)
		return tmp

	def __objectify__(self, content, initial_pass=False):

		"""

		:param content:
		:param initial_pass:
		:return: :raise ValueError:
		"""
		try:
			converted = {}
			for i in content:
				v = content[i]
				if type(v) is dict:
					v = JSON_Object(None, v, True)
				elif type(v) is list:
					v = self.__find_nested_dicts__(v)
				converted[i] = v
				if initial_pass:
					setattr(self, i, v)
		except (TypeError, IndexError) as e:
			if initial_pass:
				print e
				raise ValueError("Top-level element must be a key-value pair.")
			converted = []
			for i in content:
				if type(i) is dict:
					converted.append(JSON_Object(None, i, True))
				elif type(i) is list:
					converted.append(self.__find_nested_dicts__(i))
				else:
					converted.append(i)
		return converted

	def __iter__(self):
		return self

	def __getitem__(self, key):
		return self.__dict__[key]

	def next(self):
		"""


		:return: :raise StopIteration:
		"""
		try:
			i =  self.keys[self.__current__]
			self.__current__ += 1
			return i
		except IndexError:
			self.__current__ = 0
			raise StopIteration

	def report(self, depth=0, subtree=None):
		"""

		:param depth:
		:param subtree:
		"""
		keys = self.keys if not subtree else subtree
		vals = self.__items__ if not subtree else subtree.__items__
		for k in keys:
			if isinstance(vals[k], JSON_Object):
				print "{0}".format(depth * "\t" + k)
				self.report(depth + 1, vals[k])
			else:
				print "{0}: {1}".format(depth * "\t" + k, vals[k])

