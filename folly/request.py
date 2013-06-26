import os
from posixpath import join as urljoin

import requests
try:
	from simplejson import loads
except ImportError:
	from json import loads

from helpers import dotdict

BASE_URL = "http://5.tritonsrage.appspot.com/grequest"

USE_DEFAULT = object() # we use object() to get a unique constant
DEFAULT_COOKIE_PATH = "~/.npcookie"
default_cookies = None

def request(name, cookies=USE_DEFAULT, game_number=USE_DEFAULT, json=True, extra_opts={}, **data):
	"""Do a request with given name and form data."""

	if cookies == USE_DEFAULT:
		global default_cookies
		if not default_cookies:
			with open(os.path.expanduser(DEFAULT_COOKIE_PATH)) as f:
				default_cookies = parse_cookies(f.read().strip())
		cookies = default_cookies
	elif isinstance(cookies, basestring):
		cookies = parse_cookies(cookies)

	if game_number == USE_DEFAULT:
		game_number = os.environ['NP_GAME_NUMBER']

	url = urljoin(BASE_URL, name)
	data['type'] = name
	if game_number: data['game_number'] = game_number

	resp = requests.post(url, data=data, cookies=cookies, **extra_opts)
	resp.raise_for_status()
	if not json: return resp.text
	resp_obj = decode_json(resp.text)
	report = resp_obj.get('report', None)

	if report == 'must_be_logged_in':
		raise RequestError(report)

	return report

def decode_json(s):
	"""This is just a helper method to isolate how we turn a response from JSON into python objects."""
	return loads(s, object_hook=dotdict)

def parse_cookies(s):
	return dict(part.strip().split('=',1) for part in s.split(';'))

class RequestError(Exception):
	pass
