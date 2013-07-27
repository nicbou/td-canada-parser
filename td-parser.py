from email.MIMEText import MIMEText
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import os
import re
import smtplib
import subprocess

# Requires Xfvb. "Xvfb :99 -ac", and "export DISPLAY=:99" to load the Firefox driver
subprocess.Popen(["Xvfb", ":99", "-ac"])
os.environ["DISPLAY"] = ":99"


# ==============================
# Required account information
# ==============================

CARD_NUMBER = '000000000000'  # TD access card number
PASSWORD = 'pass'  # TD online account password

# Security questions and answers. These are case sensitive.
SECURITY_QUESTIONS = (
    ('What is the first name of your best childhood friend', '...'),
    ('As a child, what did you want to be when you grew up?', '...'),
    ('What is your nickname?', '...'),
    ('What is your favourite hobby?', '...'),
    ('What was the name of your high school?', '...'),
)

# Email server information
SMTP_USERNAME = 'user'
SMTP_PASSWORD = 'pass'
SMTP_SERVER = 'smtp.emailserver.com:587'

EMAIL_FROM = 'bot@emailserver.com'
EMAIL_TO = 'wiseguy@gmail.com'

# ==============================
# Scrape the info from TD Canada
# ==============================

print "Scraping account information from TD Canada..."

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
    print('No security question')
else:
    # Known questions and answers
    print('Security question: ' + security_question.text)
    # Try each question/answer combo
    for question, answer in SECURITY_QUESTIONS:
        if question in security_question.text:
            print('Security answer: ' + answer)
            driver.find_element_by_name("answer").send_keys(answer)
            driver.find_element_by_css_selector("#btnMFALogin").click()
            break

# Fetch the account list
try:
    account_rows = driver.find_elements_by_css_selector("table.myAccounts tr")
except NoSuchElementException, e:
    print "Couldn't parse accounts"
    accounts = []

#Parse the scraped data to retrieve the balances
print "Parsing account data..."
content = ""
splitter = re.compile(r'\d')
accounts = []

#Parse each row
accounts = []
for row in account_rows[1:]:
    try:
        #Get and shorten account names
        title = row.find_element_by_css_selector('td:first-child a').text
        title = splitter.split(title)[0].replace("TD HIGH INTEREST SAVINGS ACCOUNT", "EPARGNES").replace("HIGH INTEREST TFSA SAVINGS ACCOUNT", "CELI")

        #Get the balance
        balance = row.find_element_by_css_selector('td:last-child a').text.replace(',', '').replace('$', '')

        #Add to the pile
        accounts.append((title, balance))
    except NoSuchElementException:
        pass  # Doesn't matter.

if len(accounts) == 0:
    print("No accounts found.")

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
