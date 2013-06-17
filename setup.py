
from os import path
from glob import glob

from distutils.core import setup
setup(
	name='neptunesfolly',
	description="Reverse-engineered python bindings for browser game Neptune's Pride",
	author="Mike Lang",
	author_email="mikelang3000@gmail.com",
	url="http://github.com/ekimekim/neptunesfolly",
	packages=['folly', 'folly.scripts'],
	requires=["requests"],
)
