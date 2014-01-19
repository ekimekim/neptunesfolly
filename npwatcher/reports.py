from reportsystem import Report


class CompareReport(Report):
	"""Specific case of report where we only want to compare against previous tick.
	Will pass in args (logger, current_galaxy, previous_galaxy).
	previous is not guarenteed to be 1 tick behind, for example after a failure or force refresh.
	If no previous available, the report will not be called.
	"""
	def __call__(self, galaxies):
		galaxies = sorted(galaxies.values(), key=lambda g: g.now)
		if len(galaxies) < 2: return
		self.fn(self.logger, galaxies[-1], galaxies[-2])


@CompareReport
def check_tick_count(logger, galaxy, oldgalaxy):
	if galaxy.tick != oldgalaxy.tick + 1:
		logger.warning("Most recent galaxy is {} ticks behind, not 1. Some values may be strange.".format(galaxy.tick - oldgalaxy.tick))
		if galaxy.paused or oldgalaxy.paused:
			logger.info("Likely explanation: Either galaxy is paused.")

@CompareReport
def incoming_fleets(logger, galaxy, oldgalaxy):
	for fleet in galaxy.fleets.values():
		if fleet.player == galaxy.player: continue
		for star in fleet.waypoints:
			if star.owner != galaxy.player: continue
			# check if it was new this tick
			if fleet.fleet_id in oldgalaxy.fleets:
				old_waypoints = oldgalaxy.fleets[fleet.fleet_id].waypoints
				if any(star.star_id == s.star_id for s in old_waypoints):
					continue # it isn't new, ignore
			# it is new
			logger.warning("INCOMING! {fleet.owner.name}'s fleet {fleet.name} is attacking {star.name} with {fleet.ships} ships, and arrives in {eta} ticks".format(
				fleet=fleet, star=star, eta=dict(zip(fleet.waypoints, fleet.eta))[star]
			))

@CompareReport
def star_ownership(logger, galaxy, oldgalaxy):
	for star, old_star in zip(galaxy.stars, oldgalaxy.stars):
		if star.puid != old_star.puid:
			if old_star.puid == -1: 
				logger.info("{0.player.name} colonised {0.name}".format(star, old_star))
			else:
				logger.info("{0.player.name} captured {0.name} from {1.player.name}".format(star, old_star))

@CompareReport
def players_tech(logger, galaxy, oldgalaxy):
	for player, old_player in zip(galaxy.players, oldgalaxy.players):
		for tech_name in player.tech:
			tech = player.tech[tech_name]
			old_tech = old_player.tech[tech_name]
			if tech.level != old_tech.level:
				logger.info("{player.name} upgraded {tech.name} tech {old_tech.level} -> {tech.level}".format(player=player, old_tech=old_tech, tech=tech))

@CompareReport
def players_core_stats(logger, galaxy, oldgalaxy):
	for player, old_player in zip(galaxy.players, oldgalaxy.players):
		for attr in ('economy', 'industry', 'science', 'total_fleets'):
			oldval = getattr(old_player, attr)
			newval = getattr(player, attr) 
			attrname = 'fleets' if attr == 'total_fleets' else attr
			if oldval > newval:
				logger.info("{player.name} has lost {loss} {attr}".format(player=player, attr=attrname, loss=oldval-newval))
			elif newval > oldval:
				logger.info("{player.name} has gained {gain} {attr}".format(player=player, attr=attrname, gain=newval-oldval))

@CompareReport
def unexpected_ship_counts(logger, galaxy, oldgalaxy):
	SHIP_CHANGE_THRESHOLD = 4 
	for player, old_player in zip(galaxy.players, old_galaxy.players):
		missing = int(old_player.ships + old_player.ship_rate) - player.ships
		if missing > SHIP_CHANGE_THRESHOLD:
			logger.info("{player.name} missing {missing} ships - possible battle?".format(player=player, missing=missing))
