import logging

report_list = []

class Report(object):
	"""Reports should log to their self.logger instance.
	Logs are aggregated and a report email is sent."""
	def __init__(self, fn=None, name=None):
		"""Can be optionally used as a decorator, or a subclass can override __call__ directly.
		name can be passed in explicitly, or is taken from the name of the fn, or the class name is used.
		"""
		report_list.append(self)
		self.name = name
		self.fn = fn
		if fn and not self.name: self.name = fn.__name__
		if not self.name: self.name = self.__class__.__name__
		self.logger = logging.getLogger('npwatcher.reports').getChild(self.name)
	def __call__(self, galaxies):
		self.fn(self.logger, galaxies)


