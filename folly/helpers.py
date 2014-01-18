import functools
import traceback


class dotdict(dict):
	def __getattr__(self, attr):
		if attr in self:
			return self[attr]
		raise AttributeError
	def __setattr__(self, attr, value):
		self[attr] = value
	def __delattr__(self, attr):
		if attr in self:
			del self[attr]
		raise AttributeError
	def __hasattr__(self, attr):
		return attr in self


class aliasdict(dict):
	"""subclass of dict.
	aliases attribute specifies names that elements can be accessed with,
	but which do not show up in keys() or by iterating.
	Useful to make an alias name without it "being there twice" on search."""

	aliases = {}

	def __getitem__(self, item):
		if item in self.aliases: return self[self.aliases[item]]
		return super(aliasdict, self).__getitem__(item)

	def __contains__(self, item):
		if item in self.aliases: return self.aliases[item] in self
		return super(aliasdict, self).__contains__(item)


class _HasData(object):
	"""A base class for classes that have a block of response data they draw information from.
	It assumes this data is stored in self.data by init.
	It defines a getattr to search it, and further, points any names given in self.aliases to other attrs.
	self.aliases should have form: {'key': 'key_to_use_instead'}
	For example, to make self.name return self.n, you would set self.aliases = {'name': 'n'}
	"""
	data = {}
	aliases = {}

	def __getattr__(self, attr):
		if attr in self.aliases:
			return getattr(self, self.aliases[attr])
		if attr in self.data:
			return self.data[attr]
		raise AttributeError(attr)

	def __hasattr__(self, attr):
		if attr in self.aliases:
			return hasattr(self, self.aliases[attr])
		return attr in self.data

	def __eq__(self, other):
		if type(self) != type(other): return False
		return self.data == other.data
	def __ne__(self, other):
		return not self == other


class PropertyError(Exception): pass
def safe_property(fn):
	"""Acts like @property, but patches a subtle problem: If the property code raises AttributeError for any reason,
	the property is ignored and getattr is consulted instead (sometimes causing infinite recursion).
	With this wrapper, the AttributeError will be "wrapped" in a PropertyError, and the traceback printed.
	"""
	@functools.wraps(fn)
	def wrapper(self):
		try:
			return fn(self)
		except AttributeError as ex:
			traceback.print_exc()
			raise PropertyError(str(ex))
	return property(wrapper)
