
from galaxy import Galaxy
galaxy = Galaxy()

techs = galaxy.player.tech

width = max(len(name) for name in techs.keys())
for tech in techs.values():
	nextlevel = tech.level + 1
	print "{tech.name:{width}}: {tech.eta_range[0]:2}-{tech.eta_range[1]:2} ({tech.eta:2}) to level {nextlevel}".format(**locals())
