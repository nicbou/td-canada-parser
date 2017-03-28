# Using the script

Fetches account information from a TD Canada Trust or AccesD Desjardins ccount, and sends them by email.

The script is rather straightforward to use:

1. Install selenium-python and phantomjs
1. Set the correct variables at the top of the script
1. Create the log file and make it writable
1. Mark the script as executable and run it

## Extending the script

Since the base script is rather simple, you can extend it to send the balance with Twilio or Pushover.

**Credit where due:** Thanks to Marc-Antoine Parent (#marcaparent) for the AccesD script.
