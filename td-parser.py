from email.MIMEText import MIMEText
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from decimal import Decimal
import os
import re
import smtplib
import subprocess
import logging

# Requires Xfvb. "Xvfb :99 -ac", and "export DISPLAY=:99" to load the Firefox driver
subprocess.Popen(["Xvfb", ":99", "-ac"])
os.environ["DISPLAY"] = ":99"


# ==============================
# CONFIG
# ==============================

#TD EasyWeb card number and password
CARD_NUMBER = '000000000000000'
PASSWORD = '...'

#The TD security questions
SECURITY_QUESTIONS = (
    ('What is the first name of your best childhood friend', '...'),
    ('As a child, what did you want to be when you grew up?', '...'),
    ('What is your nickname?', '...'),
    ('What is your favourite hobby?', '...'),
    ('What was the name of your high school?', '...'),
)

#SMTP server used to send emails
SMTP_USERNAME = '...'
SMTP_PASSWORD = '...'
SMTP_SERVER = '...'

EMAIL_FROM = '...'  # The email of the sender
EMAIL_TO = '...'  # The recipient of the balance emails. You can use SMS gateways to send messages to phones.

LOG_PATH = '/var/log/log.txt'  # Errors are logged there


# ==============================
# Prepare the logger
# ==============================

logging.basicConfig(filename=LOG_PATH,level=logging.INFO,format='%(asctime)s %(message)s')

# ==============================
# Scrape the info from TD Canada
# ==============================

logging.info("Scraping account information from TD Canada...")

#Set up driver
driver = webdriver.Firefox()
driver.implicitly_wait(10)
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
try:
    account_rows = driver.find_elements_by_css_selector("table.myAccounts tr")
except NoSuchElementException, e:
    logging.error("Couldn't parse accounts")
    account_rows = []

#Parse the scraped data to retrieve the balances
logging.info("Parsing account data...")
content = ""
splitter = re.compile(r'\d')

#Parse each row
accounts = {}
for row in account_rows[1:]:
    try:
        #Get and shorten account names
        title = row.find_element_by_css_selector('td:first-child a').text
        title = splitter.split(title)[0].replace("TD HIGH INTEREST SAVINGS ACCOUNT", "EPARGNES").replace("HIGH INTEREST TFSA SAVINGS ACCOUNT", "CELI")

        #Get the balance
        balance = row.find_element_by_css_selector('td:last-child a').text.replace(',', '').replace('$', '')

        #Add to the pile
        accounts[title.strip().lower()] = Decimal(balance)
    except NoSuchElementException:
        pass  # Doesn't matter.

if len(accounts) == 0:
    logging.warning("No accounts found.")

driver.quit()


# ============================
# Send an SMS with the balance
# ============================

print "Sending balance to cellphone..."

content = ""
for account in accounts:
    content += "%s: $%s\n" % (account[0], account[1])

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

print "Done."