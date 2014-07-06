#!/usr/bin/env python

from email.MIMEText import MIMEText
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import os
import re
import smtplib
import subprocess
import logging


# ==============================
# Required account information
# ==============================

CARD_NUMBER = '...'  # AccesD access card number (omit first four numbers)
PASSWORD = '...'  # AccesD online account password

# Security questions and answers.
# These are case sensitive, use unicode for accents
SECURITY_QUESTIONS = (
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

# SMPT server used to send emails
SMTP_USERNAME = '...'
SMTP_PASSWORD = '...'
SMTP_SERVER = '...'

# Emails infos (sender and receiver)
# You can use SMS gateways to send messages to phones
EMAIL_FROM = '...'
EMAIL_TO = '...'

# Path to logging file
LOG_PATH = '/var/log/desjardins-parser-log.txt'


# ==============================
# Prepare the logger
# ==============================

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')


# ==============================
# Scrape the info from AccesD
# ==============================

logging.info("Scraping account information from AccesD Desjardins")

#Requires IceWeasel
#Set up driver
logging.info("Trying to start driver")
try_number = 1
while try_number > 0: # Had to do this while as my Raspberry Pi sometimes encounter strange errors
	try:
		if try_number > 1:
			try:
				driver.quit() # In case a previous run left traces
			except:
				pass
		driver = webdriver.PhantomJS()
		logging.info("Driver successfully started")
		try_number = 0
	except:
		logging.warning("Driver error (try " + str(try_number) + "), trying again")
		try_number += 1
driver.implicitly_wait(10)

logging.info("Entering card number")

#Scrape data
driver.get("https://accesd.desjardins.com/fr/accesd/")
driver.find_element_by_name("card_num").clear()
driver.find_element_by_name("card_num").send_keys(CARD_NUMBER)
driver.find_element_by_name("ch_but_logon").click()

logging.info("Card number correctly entered")
logging.info("Trying to detect if question is asked")

try: 
	#If no questions, go for next step
	password = driver.find_element_by_name("passwd")
	logging.info("No question asked")
except NoSuchElementException, e:
	logging.info("Question is asked")
	#Bypass security questions
	try:
		# Check if there's a security question
		answer_box = driver.find_element_by_css_selector(".disableAutoComplete")
	except NoSuchElementException, e:
		# No question, move on
		logging.error("Something went wrong, can't connect to Desjardins' Website, quitting program...")
		driver.quit()
		sys.exit(0)
	else:
		try:
			question_accesd = driver.find_element_by_css_selector("td.t[align=left]")
		except NoSuchElementException, e:
			logging.error("Question not found, quitting program...")
			driver.quit()
			sys.exit(0)
		else:
			# Known questions and answers
			logging.info('Security question: ' + question_accesd.text)
			# Try each question/answer combo
			for question, answer in SECURITY_QUESTIONS:
		        	if question in question_accesd.text:
		        		logging.info('Security answer: ' + answer)
		        		answer_box.send_keys(answer)
		        		driver.find_element_by_name("ch_valide_defi").click()
		        		break

try:
	#Check if it's really password time
	passwd = driver.find_element_by_name("passwd")
except NoSuchElementException, e:
	logging.error("Something went wrong, can't connect to Desjardins\' Website, quitting program...")
	driver.quit()
	sys.exit(0)
else:
	#Logging in
	logging.info("Trying to log in")
	passwd.clear()
	passwd.send_keys(PASSWORD)
	driver.find_element_by_name("ch_but_logon").click()
	logging.info("Log in successful")

# Fetch the account list
logging.info("Trying to fetch accounts list from " + driver.title)
try:
	driver.switch_to_frame('session')
	logging.info("Sucessfully changed frame")
except:
	logging.info("Failed to change frame")
	pass

try:
	accounts = {}
	account_rows = driver.find_elements_by_css_selector("form.f tr")
except NoSuchElementException, e:
	logging.info("Couldn't fetch accounts list")
else:
	logging.info("Accounts fetched successfully")

	#Parse each row
	logging.info("Trying to parse accounts")
	
	for row in account_rows[1:]:
		try:
			#Get and shorten account names
			account_name = row.find_element_by_css_selector('td.c a').text

			#Try each account number/account display name combo
			for account_number, account_display_name in ACCOUNTS_TO_FETCH:
				if account_name in account_number:
					title = account_display_name

					#Get the balance
					balance = row.find_element_by_css_selector('td.camnp span.ci').text

					#Add to the pile
					accounts[title] = balance + " $"
		except NoSuchElementException, e:
			pass  # Doesn't matter.
		
	logging.info("Accounts parsed successfully")

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
        for account, balance in accounts.iteritems():
                content += "%s: $%s\n" % (account, balance)

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
