import math

from request import request
from helpers import dotdict, aliasdict


class Galaxy(object):
	_report = None

	def __init__(self, game_number, cookies):
		self.game_number = game_number
		self.cookies = cookies

	def update(self):
		self._report = request('order', order='full_universe_report', game_number=self.game_number, cookies=self.cookies)

	@property
	def report(self):
		if not self._report:
			self.update()
		return self._report

	def __getattr__(self, attr):
		return self.report[attr]

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
	def stars(self):
		return [Star(int(star_id), galaxy=self) for star_id in self.report.stars]

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
		return self.data[attr]

	def __hasattr__(self, attr):
		if attr in self.aliases:
			return hasattr(self, self.aliases[attr])
		return attr in self.data


class Fleet(_HasGalaxy, _HasData):
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
		return [Star(star_id, galaxy=self.galaxy) for star in self.data.p]

	@property
	def player(self):
		return Player(self.data.puid, galaxy=self.galaxy)

	@property
	def star(self):
		if 'ouid' in self.data:
			return Star(self.data.ouid, galaxy=self.galaxy)
		return None

	@property
	def x(self): return float(self.data.x)
	@property
	def y(self): return float(self.data.y)
	@property
	def lx(self): return float(self.data.lx)
	@property
	def ly(self): return float(self.data.ly)


class Star(_HasGalaxy, _HasData):
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
		return [fleet for fleet in self.galaxy.fleets if fleet.ouid == self.star_id]

	def distance(self, other, as_level=False):
		"""Return distance to other star.
		If as_level=True, convert the result into the minimum range level required.
		"""
		dist = math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
		if not as_level: return dist
		level = math.ceil(dist) - 3
		if level < 1: level = 1
		return level


class Player(_HasGalaxy, _HasData):
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
	def conceded(self):
		return self.data.conceded == 1

	@property
	def tech(self):
		class TechDict(aliasdict, dotdict):
			aliases = Tech.TECH_NAME_ALIASES
		return TechDict({tech_name: Tech(self.player_id, tech_name, galaxy=self.galaxy)
		                 for tech_name in self.data.tech})

	@property
	def stars(self):
		return [star for star in galaxy.stars if star.data.puid == self.player_id]

	@property
	def fleets(self):
		"""Note: RETURNS VISIBLE FLEETS ONLY"""
		return [fleet for fleet in galaxy.fleets if fleet.data.puid == self.player_id]

	@property
	def researching(self):
		return Tech(self.player_id, self.data.researching, galaxy=self.galaxy)

	@property
	def researching_next(self):
		return Tech(self.player_id, self.data.researching_next, galaxy=self.galaxy)


class Tech(_HasData, _HasGalaxy):
	aliases = {
		'current': 'research',
		'required': 'brr',
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
		min_eta = max(0, int(math.ceil(self.remaining / max_sci_rate)))
		max_eta = max(0, int(math.ceil(self.remaining / min_sci_rate)))
		return (min_eta, max_eta)

	@property
	def eta_details(self):
		"""Ticks to completion, based on current player science and experimentation level.
		Returns a dict {ticks: chance}, ie. mapping from potential completion time in ticks
		to the probability that it will complete at that time."""
		raise NotImplementedError # TODO proper freq distribution
