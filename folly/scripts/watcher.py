#!/bin/env python

import time
import sys

from folly import Galaxy
from folly.request import RequestError

old_galaxy = None
while True:
	galaxy = Galaxy()
	try:
		galaxy.update()
	except RequestError, ex:
		print "ERROR: Could not update:", ex
		if old_galaxy:
			print "Next update will track changes from tick {}".format(old_galaxy.tick)
	else:
		print "TICK {}".format(galaxy.tick)
		if old_galaxy:
			if old_galaxy.tick == galaxy.tick:
				if old_galaxy.paused or galaxy.paused:
					print "WARNING: No change in tick due to game pause"
				else:
					print "WARNING: No change in tick. Bad update time or force refresh?"

			# star change ownership
			for star, old_star in zip(galaxy.stars, old_galaxy.stars):
				if star.puid != old_star.puid:
					if old_star.puid == -1:
						print "{0.player.name} colonised {0.name}".format(star, old_star)
					else:
						print "{0.player.name} captured {0.name} from {1.player.name}".format(star, old_star)

			# players have unexpected ship count (indicates battles)
			SHIP_CHANGE_THRESHOLD = 4
			for player, old_player in zip(galaxy.players, old_galaxy.players):
				missing = int(old_player.ships + old_player.ship_rate) - player.ships
				if missing > SHIP_CHANGE_THRESHOLD:
					print "{player.name} missing {missing} ships - possible battle?".format(player=player, missing=missing)

			# tech upgrades
			for player, old_player in zip(galaxy.players, old_galaxy.players):
				for tech_name in player.tech:
					tech = player.tech[tech_name]
					old_tech = old_player.tech[tech_name]
					if tech.level != old_tech.level:
						print "{player.name} upgraded {tech.name} tech {old_tech.level} -> {tech.level}".format(player=player, old_tech=old_tech, tech=tech)
		else:
			print "No previous data."

	try:
		time.sleep(3600)
	except KeyboardInterrupt:
		if raw_input("forced refresh. exit? ").startswith('y'):
			sys.exit(0)
	old_galaxy = galaxy
	print
