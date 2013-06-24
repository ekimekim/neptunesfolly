import math

from request import request, USE_DEFAULT
from helpers import dotdict, aliasdict


class Galaxy(object):
	_report = None

	def __init__(self, game_number=USE_DEFAULT, cookies=USE_DEFAULT, **request_opts):
		self.game_number = game_number
		self.cookies = cookies
		self.request_opts = request_opts

	def update(self):
		self._report = request('order', order='full_universe_report', game_number=self.game_number, cookies=self.cookies, extra_opts=self.request_opts)

	@property
	def report(self):
		if not self._report:
			self.update()
		return self._report

	def __getattr__(self, attr):
		if attr in self.report: return self.report[attr]
		if attr in self.players_by_name: return self.players_by_name[attr]
		raise AttributeError(attr)

	def __str__(self):
		subpart = "{self.player.name} at {self.now}".format(self=self) if self._report else '???'
		game_number = 'default' if self.game_number is USE_DEFAULT else self.game_number
		return "<Galaxy {game_number}:{subpart}>".format(game_number=game_number, subpart=subpart)

	def __repr__(self):
		return str(self)

	def __eq__(self, other):
		if type(self) != type(other): return False
		if self.game_number != other.game_number: return False
		if not self._report: return other._report is None
		EXCLUDE = {'now', 'tick_fragment'}
		for key in set(self._report.keys()) - EXCLUDE:
			if self._report[key] != other._report[key]: return False
		return True

	@property
	def admin(self):
		return self.players[self.report.admin]

	@property
	def fleets(self):
		# We use a dict {id: object} instead of a list [object] because the "list" is sparse - only visible ones present
		return {int(fleet_id): Fleet(int(fleet_id), galaxy=self) for fleet_id in self.report.fleets}

	@property
	def game_state(self):
		if self.report.game_over: return 'finished'
		if not self.report.started: return 'not started'
		if self.report.paused: return 'paused'
		return 'running'

	@property
	def now(self):
		return self.report.now / 1000.0 # epoch time

	@property
	def player(self):
		return self.players[self.report.player_uid]

	@property
	def players(self):
		return [Player(int(player_id), galaxy=self) for player_id in sorted(self.report.players, key=int)]

	@property
	def players_by_name(self):
		return {player.name: player for player in self.players}

	@property
	def stars(self):
		return [Star(int(star_id), galaxy=self) for star_id in sorted(self.report.stars)]

	@property
	def start_time(self):
		return self.report.start_time / 1000.0 # epoch time

	@property
	def turn_based(self):
		return self.report.turn_based == 1


class _HasGalaxy(object):
	"""A base class for classes that are contained in a galaxy."""
	def __init__(self, *args, **kwargs):
		"""A common feature of these classes is that, while they would normally be generated
		by a galaxy object, they may be created independently. By giving the nessecary game_number
		and cookies, it fetches a temporary galaxy object in order to get its info.
		For example, if you only cared about Fleet 42, you might use:
			myfleet = Fleet(42, game_number=game_number, cookies=cookies)
		instead of:
			galaxy = Galaxy(game_number, cookies)
			myfleet = galaxy.fleets[42]

		Inheritance note: Once this init is called, the parent galaxy is available as self.galaxy
		"""
		# all this kwargs.pop nonsense is because python2 doesn't allow def f(*args, key=default, ...)
		if 'game_number' in kwargs or 'cookies' in kwargs:
			game_number = kwargs.pop('game_number')
			cookies = kwargs.pop('cookies')
			galaxy = Galaxy(game_number, cookies)
		else:
			galaxy = kwargs.pop('galaxy')

		self.galaxy = galaxy

		super(_HasGalaxy, self).__init__(*args, **kwargs)


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


class _HasName(object):
	"""Base class for game objects that are described / uniquely identified by name.
	Name is expected to be self.name
	All this class does is provide a shared str() method."""

	def __str__(self):
		return "<{cls.__name__} {self.name!r}>".format(self=self, cls=type(self))
	def __repr__(self):
		return str(self)


class Fleet(_HasGalaxy, _HasData, _HasName):
	aliases = {
		'owner': 'player',
		'name': 'n',
		'ships': 'st',
		'orbiting': 'star',
	}

	def __init__(self, fleet_id, **kwargs):
		super(Fleet, self).__init__(**kwargs)
		self.fleet_id = fleet_id

	@property
	def data(self):
		return self.galaxy.report.fleets[str(self.fleet_id)]

	@property
	def waypoints(self):
		return [Star(star_id, galaxy=self.galaxy) for star_id in self.data.p]

	@property
	def player(self):
		return Player(self.data.puid, galaxy=self.galaxy)

	@property
	def star(self):
		if 'ouid' in self.data:
			return Star(self.data.ouid, galaxy=self.galaxy)
		return None

	@property
	def eta(self):
		"""Reports number of ticks until fleet reaches each destination in waypoint list.
		Returns a list of integers in the same order as waypoints.
		eg. You could map stars to the fleet's eta with dict(zip(fleet.waypoints, fleet.eta))
		"""
		result = []
		time = 0
		position = self
		for star in self.waypoints:
			time += int(math.ceil(star.distance(position) / self.galaxy.fleet_speed))
			position = star
			result.append(time)
		return result

	@property
	def x(self): return float(self.data.x)
	@property
	def y(self): return float(self.data.y)
	@property
	def lx(self): return float(self.data.lx)
	@property
	def ly(self): return float(self.data.ly)


class Star(_HasGalaxy, _HasData, _HasName):
	aliases = {
		'owner': 'player',
		'name': 'n',
		'economy': 'e',
		'carriers': 'c',
		'garrison': 'g',
		'industry': 'i',
		'resources': 'r',
		'natural_resources': 'nr',
		'natural': 'nr',
		'science': 's',
		'ships': 'st',
	}

	def __init__(self, star_id, **kwargs):
		super(Star, self).__init__(**kwargs)
		self.star_id = star_id

	@property
	def data(self):
		return self.galaxy.report.stars[str(self.star_id)]

	@property
	def player(self):
		puid = self.data.puid
		return None if puid == -1 else Player(puid, galaxy=self.galaxy)

	@property
	def visible(self):
		return self.data.v == '1'

	@property
	def x(self): return float(self.data.x)
	@property
	def y(self): return float(self.data.y)

	@property
	def fleets(self):
		"""Get all orbiting fleets (reverse lookup)"""
		return [fleet for fleet in self.galaxy.fleets.values() if 'ouid' in fleet.data and fleet.ouid == self.star_id]

	def distance(self, other, as_level=False):
		"""Return distance to other star.
		If as_level=True, convert the result into the minimum range level required.
		"""
		dist = math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
		if not as_level: return dist
		level = math.ceil(dist) - 3
		if level < 1: level = 1
		return level


class Player(_HasGalaxy, _HasData, _HasName):
	aliases = {
		'name': 'alias',
		'economy': 'total_economy',
		'industry': 'total_industry',
		'science': 'total_science',
		'ships': 'total_strength',
	}

	def __init__(self, player_id, **kwargs):
		super(Player, self).__init__(**kwargs)
		self.player_id = player_id

	@property
	def data(self):
		return self.galaxy.report.players[str(self.player_id)]

	def __getattr__(self, attr):
		# Allow tech to be referenced directly from player object
		if attr in self.tech:
			return self.tech[attr]
		return super(Player, self).__getattr__(attr)

	@property
	def state(self):
		return {
			0: 'active',
			1: 'quit', # <-- guessing
			2: 'afk',
			3: 'ko',
		}.get(self.data.conceded, 'unknown')

	@property
	def tech(self):
		class TechDict(aliasdict, dotdict):
			aliases = Tech.TECH_NAME_ALIASES
		return TechDict({tech_name: Tech(self.player_id, tech_name, galaxy=self.galaxy)
		                 for tech_name in self.data.tech})

	@property
	def stars(self):
		return [star for star in self.galaxy.stars if star.data.puid == self.player_id]

	@property
	def fleets(self):
		"""Note: RETURNS VISIBLE FLEETS ONLY"""
		return [fleet for fleet in self.galaxy.fleets.values() if fleet.data.puid == self.player_id]

	@property
	def researching(self):
		return Tech(self.player_id, self.data.researching, galaxy=self.galaxy)

	@property
	def researching_next(self):
		return Tech(self.player_id, self.data.researching_next, galaxy=self.galaxy)

	@property
	def ship_rate(self):
		"""New ships per tick"""
		return self.industry * (self.manufacturing.level + 5) / 24.0


class Tech(_HasData, _HasGalaxy, _HasName):
	aliases = {
		'current': 'research',
	}

	TECH_NAME_ALIASES = {
		'experimentation': 'research',
		'range': 'propulsion',
		'hyperspace': 'propulsion',
	}

	def __init__(self, player_id, tech_name, **kwargs):
		super(Tech, self).__init__(**kwargs)
		if tech_name in self.TECH_NAME_ALIASES:
			tech_name = self.TECH_NAME_ALIASES[tech_name]
		self.player_id = player_id
		self.name = tech_name

	@property
	def data(self):
		return self.galaxy.report.players[str(self.player_id)].tech[self.name]

	@property
	def player(self):
		return Player(self.player_id, galaxy=self.galaxy)

	@property
	def basecost(self):
		try:
			return self.brr
		except AttributeError:
			# brr is only available for calling player's tech, but is the same across all tech of same type
			return Tech(self.galaxy.player_uid, self.tech_name, galaxy=self.galaxy).basecost

	@property
	def required(self):
		return self.level * self.basecost

	@property
	def remaining(self):
		return self.required - self.current

	@property
	def progress(self):
		return float(self.current)/self.required

	@property
	def eta(self):
		"""Most likely ticks to completion, based on current player science and experimentation level"""
		player = self.player
		sci_rate = self.player.science + 4 * self.player.experimentation.level / 7.0
		return max(0, int(math.ceil(self.remaining / sci_rate)))

	@property
	def eta_range(self):
		"""Ticks to completion, based on current player science and experimentation level.
		Returns (lower bound, upper bound)."""
		player = self.player
		min_sci_rate = self.player.science
		max_sci_rate = self.player.science + 4 * self.player.experimentation.level
		min_eta = max(0, int(math.ceil(float(self.remaining) / max_sci_rate)))
		max_eta = max(0, int(math.ceil(float(self.remaining) / min_sci_rate)))
		return (min_eta, max_eta)

	@property
	def eta_details(self):
		"""Ticks to completion, based on current player science and experimentation level.
		Returns a dict {ticks: chance}, ie. mapping from potential completion time in ticks
		to the probability that it will complete at that time."""
		raise NotImplementedError # TODO proper freq distribution
