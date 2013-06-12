import os

import requests
from simplejson import loads

from helpers import dotdict

BASE_URL = "http://triton.ironhelmet.com/grequest"

def request(name, cookies=None, **data):
	"""Do a request with given name and form data."""

	url = os.path.join(BASE_URL, name)
	data['type'] = name

	resp = requests.post(url, data=data, cookies=cookies)
	resp.raise_for_status()
	resp_obj = decode_json(resp.text)
	return resp_obj.get('report', None)

def decode_json(s):
	"""This is just a helper method to isolate how we turn a response from JSON into python objects."""
	return loads(s, object_hook=dotdict)

