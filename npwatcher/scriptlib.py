from functools import wraps
import sys


def with_argv(fn):
	"""Decorator that wraps your 'main' function, giving it some automatic behaviour.
	The resulting function should not be passed any args.
	Command line arguments are interpreted as follows:
		The first argument is the program name, it is dropped (you can still access it with sys.argv[0]).
		If an argument has form '--key=value', main's kwargs are updated
			with {key: value}
		If an argument has form '--flag', main's kwargs are updated
			with {flag: True}
		Short options (with a single '-') are treated similarly.
			Note that '-xyz=blah' produces the kwargs:
				{'x': True, 'y': True, 'z': 'blah'}
		Remaining arguments are passed to main as *args.
	If main raises a TypeError, it is suppressed and main's docstring is printed
		along with str() of the TypeError.
	Any other exception is not suppressed and will produce a normal traceback.
	If main returns None, exit(0) is called.
	Otherwise, exit(return value) is called.
	"""

	@wraps(fn)
	def _with_argv():
		args = []
		kwargs = {}
		argv = sys.argv[1:][::-1]

		while argv:
			arg = argv.pop()
			if arg.startswith('--'):
				arg = arg[2:]
			elif arg.startswith('-'):
				if len(arg) != 2 and arg[2] != '=': # rule out cases '-x' and '-x=value'
					argv.append('-' + arg[2:]) # thus '-xyz' becomes '-yz'
					arg = arg[1]
				else:
					arg = arg[1:]
			else:
				args.append(arg)
				continue
			# We have a flag or key=value
			if '=' in arg:
				k, v = arg.split('=', 1)
			else:
				k, v = arg, True
			kwargs[k] = v

		try:
			ret = fn(*args, **kwargs)
		except TypeError, e:
			print str(e)
			if fn.__doc__: print fn.__doc__
			ret = 255

		sys.exit(0 if ret is None else ret)

	return _with_argv


if __name__=='__main__':
	# for examples
	@with_argv
	def main(*args, **kwargs):
		print 'args:', args
		print 'kwargs:', kwargs
	main()
