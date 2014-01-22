import os
import logging
from getpass import getpass

import simplejson as json
from scriptlib import with_argv
import gevent
import gevent.event

from folly.galaxy import Galaxy
from folly.helpers import dotdict
from folly.request import RequestError

import emailer
from reportsystem import report_list
import reports

GALAXY_CACHE_PATH = '/var/lib/npwatcher/galaxies'
RETRY_INTERVAL = 60
SENDER_EMAIL = 'secondary.mikelang3000@gmail.com'
TARGET_EMAIL = 'mikelang3000@gmail.com'

force_refresh = gevent.event.Event()

def setup_logging():
	global logger, report_logger, report_handler

	password = getpass("Password for {}: ".format(SENDER_EMAIL))

	root_logger = logging.getLogger()
	root_logger.setLevel(logging.DEBUG)
	root_logger.addHandler(logging.StreamHandler())

	logger = logging.getLogger('npwatcher')

	report_logger = logger.getChild('reports')
	report_handler = emailer.EmailAggregateHandler((SENDER_EMAIL, password), TARGET_EMAIL)
	report_handler.setLevel(logging.INFO)
	report_logger.addHandler(report_handler)
	fmt = "%(name)s:%(levelname)s: %(message)s"
	report_handler.setFormatter(logging.Formatter(fmt))

def load_galaxies(game_number):
	galaxies = {}
	directory = os.path.join(GALAXY_CACHE_PATH, game_number)
	for filename in os.listdir(directory):
		try:
			filepath = os.path.join(directory, filename)
			with open(filepath) as f:
				data = json.loads(f.read(), object_hook=dotdict)
			galaxy = Galaxy(from_data=data)
		except (OSError, IOError, json.JSONDecodeError):
			logger.warning("Failed to load galaxy {!r}".format(filepath), exc_info=True)
		if galaxy.now in galaxies:
			logger.warning("Duplicate galaxy ({}) for time {:.2f}".format(
			               'equal' if galaxy == galaxies[galaxy.now] else 'differs',
			               galaxy.now))
		galaxies[galaxy.now] = galaxy
	return galaxies

def save_galaxy(galaxy):
	filepath = os.path.join(GALAXY_CACHE_PATH, galaxy.game_number, "{:.2f}.json".format(galaxy.now))
	if not os.path.exists(os.path.dirname(filepath)):
		os.makedirs(os.path.dirname(filepath))
	with open(filepath, 'w') as f:
		f.write(json.dumps(galaxy.data))

@with_argv
def main(game_number=None):
	if not game_number: game_number = os.environ['NP_GAME_NUMBER']
	setup_logging()

	try:
		galaxies = load_galaxies(game_number)
	except (OSError, IOError):
		logger.warning("Failed to load galaxies", exc_info=True)
		galaxies = {}

	while True:

		logger.debug("Fetching galaxy")
		galaxy = None
		first_attempt = True
		while not galaxy:
			try:
				galaxy = Galaxy(game_number=game_number)
			except RequestError as ex:
				level = logging.ERROR if first_attempt else logging.DEBUG
				logger.log(level, "Failed to fetch galaxy, retrying in {} seconds".format(RETRY_INTERVAL),
				           exc_info=True)
				first_attempt = False
				gevent.sleep(RETRY_INTERVAL)

		try:
			save_galaxy(galaxy)
		except (IOError, OSError):
			logger.warning("Could not save galaxy", exc_info=True)
		galaxies[galaxy.now] = galaxy

		for report in report_list:
			try:
				report(galaxies)
			except Exception:
				report.logger.exception("Report failed to run")

		report_handler.send("npwatcher report for {cycle}:{tick} of game {game_number}".format(
			cycle = galaxy.productions,
			tick = galaxy.production_counter,
			game_number = game_number,
		))

		minutes_to_tick = galaxy.tick_rate - galaxy.tick_fragment
		if force_refresh.wait(minutes_to_tick * 60 + 10): # we wait an extra 10sec to avoid nasty race cdns with the server
			logger.info("Forced refresh")
		force_refresh.clear()

if __name__=='__main__':
	main()
