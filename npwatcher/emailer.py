import logging
import smtplib
from email.MIMEText import MIMEText

import gevent

class EmailAggregateHandler(logging.Handler):
	def __init__(self, creds, target, *args, **kwargs):
		"""Creds should be (email, password). Assumed gmail."""
		super(EmailAggregateHandler, self).__init__(*args, **kwargs)
		self.creds = creds
		self.target = target
		self.to_send = []

	def emit(self, record):
		self.to_send.append(self.format(record))

	def send(self, subject):
		if not self.to_send: return
		body = '\n'.join(self.to_send)
		gevent.spawn(send_email, self.creds, self.target, subject, body)
		self.to_send = []


def send_email(creds, target, subject, body):
	RETRY_INTERVAL = 60

	logger = logging.getLogger("emailer")
	sender, password = creds

	message = MIMEText(body)
	message['From'] = sender
	message['To'] = target
	message['Subject'] = subject

	first_attempt = True
	while True:
		try:
			server = smtplib.SMTP("smtp.gmail.com", 587)
			server.ehlo()
			server.starttls()
			server.ehlo()
			server.login(sender, password)
			server.sendmail(sender, target, message.as_string())
			server.close()
		except smtplib.SMTPException:
			level = logging.ERROR if first_attempt else logging.DEBUG
			logger.log(level, "Failed to send message, retrying in {} seconds".format(RETRY_INTERVAL), exc_info=True)
			first_attempt = False
			gevent.sleep(RETRY_INTERVAL)
		else:
			return
