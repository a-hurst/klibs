__author__ = 'Jonathan Mulle & Austin Hurst'

import collections


class NamedObject(object):

	def __init__(self, name):
		super(NamedObject, self).__init__()
		self.__name__ = name

	@property
	def name(self):
		return self.__name__


class NamedInventory(collections.MutableMapping):
	"""A dictionary specifically for objects that implement KLObject mixin."""

	def __init__(self, *args, **kwargs):
		self.store = dict()
		self.update(dict(*args, **kwargs))  # use the free update to set keys

	def __getitem__(self, key):
		return self.store[self.__keytransform__(key)]

	def __setitem__(self, k, v=None):
		try:
			if k != v.name:
				raise ValueError("KLInventory keys MUST match the name property of their associated value.")
			self.store[v.name] = v
		except AttributeError:
			raise TypeError("Only objects inheriting from KLObject can be stored in a KLInventory collection.")

	def __delitem__(self, key):
		del self.store[self.__keytransform__(key)]

	def __iter__(self):
		return iter(self.store.values())

	def __len__(self):
		return len(self.store)

	def __keytransform__(self, key):
		try:
			return key.name
		except AttributeError:
			return key

	def __str__(self):
		return str(self.store)

	def add(self, key):
		if not isinstance(key, NamedObject):
			try:
				for k in key:
					self.__setitem__(k.name, k)
			except AttributeError:
				raise TypeError("Only objects inheriting from KLObject can be stored in a KLInventory collection.")
		else:
			self.__setitem__(key.name, key)


class CachedInventory(NamedInventory):

	def __init__(self, *args, **kwargs):
		super(CachedInventory, self).__init__(*args, **kwargs)
		self.__cache_store__ = dict()

	def __getitem__(self, k, cache=None):
		try:
			return self.__cache_store__[cache][self.__keytransform__(k)]
		except KeyError:
			return self.store[self.__keytransform__(k)]

	def __setitem__(self, k, v, cache=None):
		try:
			store = self.__cache_store__[cache]
		except KeyError:
			store = self.store
		try:
			if k != v.name:
				raise ValueError("KLInventory keys MUST match the name property of their associated value.")
			store[v.name] = v
		except AttributeError:
			raise TypeError("Only objects inheriting from KLObject can be stored in a KLInventory collection.")

	def cache(self, label):
		self.__cache_store__[label] = self.store
		self.store = dict()

	def dump(self):
		return self.__cache_store__

	def retrieve(self, k, cache=None):
		return self.__getitem__(k, cache)


