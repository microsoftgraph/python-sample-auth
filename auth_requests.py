"""sample.py - Requests-OAuthlib sample for Microsoft Graph """
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import os

import bottle
from requests_oauthlib import OAuth2Session

with open('config.txt') as configfile:
    CLIENT_ID, CLIENT_SECRET, *_ = configfile.read().splitlines()
MSGRAPH = OAuth2Session(CLIENT_ID, scope=['User.Read'],
                        redirect_uri='http://localhost:5000/login/authorized')

# enable non-HTTPS redirect URI for development/testing
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# allow token scope to not match requested scope (other auth libraries allow
# this, but Requests-OAuthlib raises exception on scope mismatch by default)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_IGNORE_SCOPE_CHANGE'] = '1'

bottle.TEMPLATE_PATH.insert(0, './templates') # template files are in /templates

@bottle.route('/')
@bottle.view('homepage.html')
def homepage():
    """Render the home page."""
    return {'sample': 'Requests-OAuthlib'}

@bottle.route('/login')
def login():
    """Prompt user to authenticate."""
    auth_base = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
    authorization_url, state = MSGRAPH.authorization_url(auth_base)
    MSGRAPH.auth_state = state
    return bottle.redirect(authorization_url)

@bottle.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    if bottle.request.query.state != MSGRAPH.auth_state:
        raise Exception('state returned to redirect URL does not match!')
    MSGRAPH.fetch_token('https://login.microsoftonline.com/common/oauth2/v2.0/token',
                        client_secret=CLIENT_SECRET,
                        authorization_response=bottle.request.url)
    return bottle.redirect('/graphcall')

@bottle.route('/graphcall')
@bottle.view('graphcall.html')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = 'https://graph.microsoft.com/v1.0/me'
    graphdata = MSGRAPH.get(endpoint).json()
    return {'graphdata': graphdata, 'endpoint': endpoint, 'sample': 'Requests-OAuthlib'}

@bottle.route('/static/<filepath:path>')
def server_static(filepath):
    """Static dev/test file server"""
    static_root = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')
    return bottle.static_file(filepath, root=static_root)

if __name__ == '__main__':
    bottle.run(app=bottle.app(), server='wsgiref', host='localhost', port=5000)
