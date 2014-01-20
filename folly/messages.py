from itertools import count
from time import strptime
from calendar import timegm # inverse of time.gmtime - stdlib is retarded

from request import USE_DEFAULT, request
from helpers import _HasData


def unread_count(**request_kwargs):
	"""Return (int, int), count of unread messages/events respectively."""
	resp = request("fetch_unread_count", type="message:unread_count", **request_kwargs)
	return resp['diplomacy'], resp['events']


def events(**kwargs):
	"""Returns an iterator that lazily fetches Events.
	For description of kwargs, see _fetch_iterator(), request.request()
	"""
	return _fetch_iterator(Event, name='fetch_game_messages', type='messages:new_messages',
	                       group='game_event', **kwargs)


def message_threads(**kwargs):
	"""Returns an iterator that lazily fetches MessageThreads.
	For description of kwargs, see _fetch_iterator(), request.request()
	"""
	return _fetch_iterator(Diplomacy, name='fetch_game_messages', type='messages:new_messages',
	                       group='game_diplomacy', **kwargs)


def _fetch_iterator(callback=None, start=0, chunksize=10, **kwargs):
	"""Returns an iterator that lazily fetches results. Passes kwargs to request().
	start indicates how many messages to skip. chunksize indicates how many to fetch with each request.
	If callback is given, yields callback(result) instead of result.
	Note that it will stop iterating as soon as it sees the end. If you wish to re-check for further messages
	that have arrived sice then, you should create a fresh iterator.
	"""
	if not callback: callback = lambda x: x
	for offset in count(start, chunksize):
		resp = request(count=chunksize, offset=offset, **kwargs)
		for message in resp['messages']:
			yield callback(message)
		if len(resp['messages']) != chunksize:
			return # stop iterating if we run out


def _date_to_epoch(s):
	return timegm(strptime('%b %d %Y %T GMT+0000', s))


class Message(_HasData):
	"""Base class for Events and diplomacy Threads."""
	aliases = {
		'modified': 'activity',
	}

	def __init__(self, message_data):
		"""Expects arg containing message data already fetched from server."""
		self.data = message_data

	@property
	def activity(self):
		return _date_to_epoch(self.data.activity)

	@property
	def created(self):
		return _date_to_epoch(self.data.created)

	@property
	def sender(self):
		"""Either the user_id of sender, or None if sender is 'game'"""
		return None if self.data.sender == 'game' else self.data.sender

	@property
	def is_read(self):
		"""Return bool if message is read."""
		return self.status == 'read'

	def lookup_recipients(self, galaxy):
		"""Use given Galaxy object to return Player objects for recipients. Omits any unknown."""
		return [player for player in galaxy.players if player.user_id in self.recipients]

	def lookup_sender(self, galaxy):
		"""Use given Galaxy object to return Player object of sender, or None if sender is None/unknown."""
		found = [player for player in galaxy.players if player.user_id == self.sender]
		if not found: return None
		assert len(found) == 1, "Multiple players with user_id {}".format(self.sender)
		return found[0]


class Event(Message):
	"""Represents a game event message.
	Subclasses implement event templates.
	The Event() constructor will automatically create the correct kind of Event based on payload.template
	Unknown event types create a bare Event() object.
	"""
	name = None # subclasses should override with template name

	def __new__(cls, data):
		if cls is Event: # subclasses should ignore this
			for subcls in cls.__subclasses___():
				if subcls.name == data.payload.template:
					return subcls(data)
		return super(Event, self).__new__(data)

	@property
	def tick(self):
		return self.payload.tick

	@property
	def text(self):
		kwargs = self.payload.copy()
		for key in ('tick','template'): del kwargs[key]
		return self.template(**kwargs)

	def template(self, **payload):
		"""Subclasses should override this with a function that returns a human-readable report of the event,
		similar (but not nessecarily identical) to the standard UI."""
		from pprint import pprint
		return "An event of unknown type {!r} occurred, with payload info:\n{}".format(
			self.payload.template, pprint(payload)
		)


class MessageThread(Message):
	"""Represents a conversation (initial message + comments) in the diplomacy menu"""

	def __init__(self, data):
		self.data = data
		# to simplify things, we preload all the comments immediately
		self.comments = list(self.get_comments(chunksize=self.comment_count))

	def get_comments(start=0, chunksize=10, **request_kwargs):
		"""Returns an iterator that lazily fetches comments from the server"""
		return _fetch_iterator(MessageComment, name=fetch_game_message_comments, message_key=self.key,
		                       start=start, chunksize=chunksize, **request_kwargs)

	@property
	def text(self):
		return self.payload.body # TODO decode html encoding

	@property
	def subject(self):
		return self.payload.subject


class MessageComment(_HasData):
	def __init__(self, data):
		self.data = data

	@property
	def text(self):
		return self.body # TODO decode html encoding

	@property
	def created(self):
		return _date_to_epoch(self.data.created)

	def lookup_sender(self, galaxy):
		"""Use given galaxy to lookup message sender and return a Player object"""
		found = [player for player in galaxy.players if player.user_id == self.sender]
		if len(found) != 1: raise ValueError("Player not found or user_id not unique")
		return found[0]
