#!/bin/env python

from folly import Galaxy
galaxy = Galaxy()

width = max(len(name) for name in galaxy.players_by_name)

COLUMNS = 100
for attr in ['total_stars', 'ships', 'economy', 'industry', 'science']:
	print "  {attr} graph:".format(attr=attr)
	scale = max(getattr(player, attr) for player in galaxy.players) / float(COLUMNS)
	for player in galaxy.players:
		value = getattr(player, attr)
		print '{player.name:>{width}}: {value:#> {scaled}}'.format(player=player, scaled=int(value/scale), width=width, value=value)
	print
