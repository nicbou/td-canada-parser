#!/usr/bin/env python

from email.MIMEText import MIMEText
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from decimal import Decimal
import smtplib
import logging


# ==============================
# CONFIG
# ==============================

#TD EasyWeb card number and password
CARD_NUMBER = '000000000000000'
PASSWORD = '...'

#The TD security questions
SECURITY_QUESTIONS = (
	('...', '...'),
	('...', '...'),
	('...', '...'),
	('...', '...'),
	('...', '...'),
)

#Accounts numbers and display name.
#The number MUST be the exact same as on your account page
ACCOUNTS_TO_FETCH = (
	('...','...'),
	('...','...'),
	('...','...'),
)

#SMTP server used to send emails
SMTP_USERNAME = '...'
SMTP_PASSWORD = '...'
SMTP_SERVER = '...'

EMAIL_FROM = '...'  # The email of the sender
EMAIL_TO = '...'  # The recipient of the balance emails. You can use SMS gateways to send messages to phones.

LOG_PATH = '/var/log/td-parser-log.txt'  # Errors are logged there


# ==============================
# Prepare the logger
# ==============================

logging.basicConfig(filename=LOG_PATH,level=logging.INFO,format='%(levelname)s %(asctime)s %(message)s')

# ==============================
# Scrape the info from TD Canada
# ==============================

logging.info("Scraping account information from TD Canada...")

#Set up driver
driver = webdriver.PhantomJS()
driver.implicitly_wait(5)
base_url = "https://w.tdgroup.com/"
verificationErrors = []
accept_next_alert = True

#Scrape data
driver.get(base_url + "wireless/servlet/ca.tdbank.wireless3.servlet.AuthenticateServletR1?source=BBerry&LOGONTO=BANKE&&NATIVE_APP_VER=A4.1&OS_VER=A4.2.2&IS_EMBEDDED_BROWSER=Y&MARKUP=HTML")
driver.find_element_by_name("MASKEDUID").clear()
driver.find_element_by_name("MASKEDUID").send_keys(CARD_NUMBER)
driver.find_element_by_name("PSWD").clear()
driver.find_element_by_name("PSWD").send_keys(PASSWORD)
driver.find_element_by_css_selector("input.buttonOrange").click()

#Bypass security questions
try:
	# Check if there's a security question
	security_question = driver.find_element_by_css_selector("#mfaQuestion")
except NoSuchElementException, e:
	# No question, move on
	logging.info('No security question')
else:
	# Known questions and answers
	logging.info('Security question: ' + security_question.text)
	# Try each question/answer combo
	for question, answer in SECURITY_QUESTIONS:
		if question in security_question.text:
			logging.info('Security answer: ' + answer)
			driver.find_element_by_name("answer").send_keys(answer)
			driver.find_element_by_css_selector("#btnMFALogin").click()
			break

# Fetch the account list
logging.info("Trying to fetch accounts list from " + driver.title)
try:
	accounts = {}
	account_rows = driver.find_elements_by_css_selector("table.myAccounts tr")
except NoSuchElementException, e:
	logging.error("Couldn't fetch accounts list")
else:
	#Parse the scraped data to retrieve the balances
	logging.info("Parsing account data...")
	
	#Parse each row
	for row in account_rows[1:]:
		try:
			#Get and shorten account names
			account_title = row.find_element_by_css_selector('td:first-child a').text
			
			#Try each account name/account display name combo
			for account_name, account_display_name in ACCOUNTS_TO_FETCH:
				if account_title in account_name:
					title = account_display_name
			
					#Get the balance
					balance = row.find_element_by_css_selector('td:last-child a').text.replace(',', '').replace('$', '')
	
					#Add to the pile
					accounts[title.strip().lower()] = Decimal(balance)
		except NoSuchElementException:
			pass  # Doesn't matter.

driver.quit()

# ============================
# Send an SMS with the balance
# ============================

logging.info("Trying to send balance via email to cellphone")

content = "\n"
if len(accounts) == 0:
	logging.warning("No accounts found, will send notification anyway")
	content += "Failed to get your accounts balance. Read log in " + LOG_PATH + " for further details"
else:
	for name,account in accounts.iteritems():
		content += "%s: $%s\n" % (name, account)

# Message
message = MIMEText(content, 'plain')
message['From'] = EMAIL_FROM
message['Subject'] = 'Balance'

# Send the email
server = smtplib.SMTP(SMTP_SERVER)
server.ehlo()
server.starttls()
server.ehlo()
server.login(SMTP_USERNAME, SMTP_PASSWORD)
server.sendmail(EMAIL_FROM, EMAIL_TO, message.as_string())
server.quit()

logging.info("Email successfully sent, program will now quit...")