#!/bin/env python

from folly import Galaxy
galaxy = Galaxy()
player = galaxy.player

objs = player.stars + player.fleets

COLUMNS = 100
width = max(len(obj.name) for obj in objs)
scale = max(obj.ships for obj in objs) / float(COLUMNS)

objs.sort(key=lambda obj: obj.ships, reverse=True)

for obj in objs:
	print '{objtype} {obj.name:>{width}}: {value:#> {scaled}}'.format(obj=obj, scaled=int(obj.ships/scale), width=width, value=obj.ships, objtype=type(obj).__name__[0])
