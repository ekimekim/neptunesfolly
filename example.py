
cookies = open('/home/mike/.npcookie').read().strip()
cookies = dict(part.strip().split('=',1) for part in cookies.split(';'))
game_number = 5895296

from galaxy import *
galaxy = Galaxy(game_number, cookies)

FORMAT = (
	'{namestr:{width}}  {0.economy}/{0.industry}/{0.science} ships:{0.ships}+{0.ship_rate:.2f}/tick '
	'stars:{0.total_stars}/{0.galaxy.stars_for_victory} tech:{0.scanning.level}/{0.range.level}/'
	'{0.terraforming.level}/{0.experimentation.level}/{0.weapons.level}/{0.banking.level}/'
	'{0.manufacturing.level}  fleets: {fleet_count}/{0.total_fleets} visible'
)

width = max(len(name) for name in galaxy.players_by_name) + 1
for player in galaxy.players:
	print FORMAT.format(player, namestr=player.name+':', width=width, fleet_count=len(player.fleets))
