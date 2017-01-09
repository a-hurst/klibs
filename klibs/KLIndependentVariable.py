__author__ = 'jono'

from klibs.KLNamedObject import NamedInventory, NamedObject
from klibs.KLUtilities import iterable

class VariableValue(NamedObject):

	def __init__(self, name, distribution=1):
		"""

		:param name:
		:param distribution:
		"""
		super(VariableValue, self).__init__(name)
		self.distribution = distribution
		self.enabled = True

class IndependentVariable(NamedObject):

	def __init__(self, name, data_type):
		"""

		:param name:
		:param data_type:
		"""
		super(IndependentVariable, self).__init__(name)
		self.values = NamedInventory()
		self.__data_type__ = None
		self.enabled = True
		self.data_type = data_type

	def add_value(self, name, distribution=1):
		"""

		:param name:
		:param distribution:
		:raise ValueError:
		"""
		try:
			name = self.data_type(name)
		except ValueError:
			e_msg = "{0} cannot be validly represented as a {0} value.".format(name, self.data_type)
			raise ValueError(e_msg)
		self.values.add(VariableValue(name, distribution))

	def add_values(self, *args):
		"""

		:param args:
		"""
		for v in args:
			if iterable(v):
				self.add_value(*v)
			else:
				self.add_value(v)

	def to_list(self):
		"""


		:return:
		"""
		values = []
		for v in self.values:
			values += [v.name] * v.distribution
		return [self.name, values]

	@property
	def data_type(self):
		"""


		:return:
		"""
		return self.__data_type__

	@data_type.setter
	def data_type(self, d_type):
		"""

		:param d_type:
		:raise TypeError:
		"""
		if d_type not in [float, int, bool, str]:
			raise TypeError("{0} is not a valid python type.".format(d_type))
		self.__data_type__ = d_type


class IndependentVariableSet(NamedInventory):

	def __init__(self):
		"""


		"""
		super(IndependentVariableSet, self).__init__()

	def add_variable(self, name, d_type, values=[]):
		"""

		:param name:
		:param d_type:
		:param values:
		"""
		ivar = IndependentVariable(name, d_type)
		for v in values:
			if iterable(v):
				ivar.add_value(*v)
			else:
				ivar.add_value(v)
		self.add(ivar)

	@property
	def enabled(self):
		"""


		:return:
		"""
		active_vars = NamedInventory()
		for indv in self:
			if not len(indv.values):
				indv.enabled = False
			if indv.enabled:
				active_vars.add(indv)

		return active_vars

	def to_list(self):
		"""


		:return:
		"""
		return [iv.to_list() for iv in self.enabled]

	def delete(self, ivar_old):
		self.__delitem__(ivar_old)




