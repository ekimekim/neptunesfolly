import math
from collections import defaultdict

from galaxy import Star, Fleet

def from_objects(*combatants, **kwargs):
	"""Run a combat between any combination of combatants.
	If any of the combatants is a star, its owner is the default defender.
	Otherwise, or if there is more than one star (in case you only wish to count the ships waiting there),
	a defender must be specified manually with the defender kwarg, which should be a Player.

	The return value is (winner, remaining)
	winner is the Player that won the fight.
	remaining is a dict mapping combatants to remaining forces.
	Note that destroyed fleets are not contained in this dict.
	Ships from stars are always assumed to fight first, followed by fleets.
	"""

	# map players to the fleets and stars fighting for them
	forces = defaultdict(lambda: [])

	if 'defender' not in kwargs:
		stars = [combatant for combatant in combatants if isinstance(combatant, Star)]
		if len(stars) != 1:
			raise ValueError("Could not determine defender")
		defender = stars[0].player
	else:
		defender = kwargs.pop('defender')

	# group by player
	for combatant in combatants:
		forces[combatant.player].append(combatant)

	inf = float('inf')
	force_lists = {}
	for player, force in forces.items():
		# sort into the order they'll fight in: stars first, then fleets in size order
		force.sort(reverse=True, key=lambda x: inf if isinstance(x, Star) else x.ships)
		# produce an integer force list in the same order
		force_lists[player] = [combatant.ships for combatant in force]

	# sort players into the needed order: defender first, then in order of player_id, wrapping around.
	players = sorted(forces.keys(), key=lambda p: (p.player_id - defender.player_id) % len(p.galaxy.players))

	# Run the simulation
	combat([(p.tech.weapons, force_lists[p]) for p in players])

	# prepare remaining dict
	# if not listed, stars had 0 left (but are still present, they don't die like fleets)
	remaining = {combatant: 0 for combatant in combatants if isinstance(combatant, Star)}

	for player, force_list in force_lists.items():
		if not force_list: continue # scan for the winner
		force = forces[player]
		for combatant, ships in zip(force[::-1], force_list[::-1]):
			# by matching backwards, we match up the surviving fleets
			remaining[combatant] = ships
		return player, remaining


def combat(*forces):
	"""Run a combat between any combination of forces.
	Each force represents all ships owned by a given player.
	The first force should be the defender, with forces then proceeding in order of player index (wrapping around).
	Each force has form (player_WS, force_list).
	Each force list should be a list of integers, giving the ships of the player and how they're split.
	The force list should be the order in which the ships fight.
	Note that, in a normal situation, a player's ships orbiting a star fight first,
	followed by each fleet they have, from largest to smallest.

	Each force list will be modified in-place to account for losses.
	Thus, only one force list will remain non-empty upon return.
	This force list will contain one or more remaining groups of ships, though possibly less than it started with.
	This reflects lost fleets.

	As an extended example, consider a fight between 3 players.
	Let's call them player 1, 2 and 3, with 2 defending.
	Player 1 is attacking with 200 ships in one fleet, and 2 WS.
	Player 2 has 100 ships on their star, with two additional fleets of 50 and 75 ships, and 1 WS.
	Player 3 is attacking with 150 ships in one fleet, and 50 in another, and 2 WS.
	Then we would call this function thus:
		p1 = [200]
		p2 = [100, 75, 50]
		p3 = [150, 50]
		combat((2, p2), (1, p3), (2, p1))
	And a possible result might be:
		p1 == []
		p2 == [25]
		p3 == []
	ie. The defender won, but lost one of its two fleets.
	"""
	# TODO this entire thing is horrible

	# add 1 to first force's WS
	forces = [(ws + 1 if n == 0 else ws, force_list) for n, (ws, force_list) in enumerate(forces)]

	# this is the only way to loop when we need to be able to remove things during the loop
	i = 0
	next = lambda x: (x+1) % len(forces)
	while 1:
		damage, force = forces[i]

		while damage:
			_, target_force = forces[next(i)]
			dealt = min(damage, target_force[0])
			target_force[0] -= dealt
			damage -= dealt
			if target_force[0] == 0:
				target_force.pop(0)
				if not target_force:
					forces.pop(next(i))
					if len(forces) == 1:
						return

		i = next(i)


def simple((def_WS, def_n), (att_WS, att_n)):
	"""A simplified interface for a simpler situation:
	This is for two-player fights between single collections of ships,
	or if you don't care about whether fleets survive.

	It returns (def_won, remaining) where def_won is true if defender won, else false,
	and remaining is the number of remaining ships on the winning side.
	"""
	att_left = att_n - math.ceil(def_n/att_WS) * (def_WS + 1)
	def_left = def_n - (math.ceil(att_n/(def_WS+1)) - 1) * att_WS
	if def_left > 0:
		return True, def_left
	else:
		return False, att_left
