

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
	"""aliases attribute specifies names that elements can be asscessed with,
	but which do not show up in keys() or by iterating.
	Useful to make an alias name without it "being there twice" on search."""

	aliases = {}

	def __getitem__(self, item):
		if item in self.aliases: return self[self.aliases[item]]
		return super(aliasdict, self).__getitem__(item)

	def __contains__(self, item):
		if item in self.aliases: return self.aliases[item] in self
		return super(aliasdict, self).__contains__(item)
