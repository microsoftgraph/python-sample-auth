"""config.py
This file contains configuration settings for running the Python auth samples
locally. In a production deployment, this information should be saved in a
database or other secure storage mechanism.
"""

CLIENT_ID = 'PUT YOUR CLIENT ID HERE'
CLIENT_SECRET = 'PUT YOUR CLIENT SECRET HERE'
REDIRECT_URI = 'http://localhost:5000/login/authorized'

AUTHORITY_URL = 'https://login.microsoftonline.com/common'
AUTH_ENDPOINT = '/oauth2/v2.0/authorize'
TOKEN_ENDPOINT = '/oauth2/v2.0/token'

RESOURCE = 'https://graph.microsoft.com/'
API_VERSION = 'v1.0'
SCOPES = ['User.Read'] # add other scopes/permissions as needed

# This code can be removed after configuring CLIENT_ID and CLIENT_SECRET above.
if ' ' in CLIENT_ID or ' ' in CLIENT_SECRET:
    print('ERROR: config.py does not contain valid CLIENT_ID and CLIENT_SECRET')
    import sys
    sys.exit(1)
