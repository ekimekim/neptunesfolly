from reportsystem import Report

@Report
def test(logger, reports):
	logger.info("test: %s", reports)
