"""Requests-OAuthlib sample for Microsoft Graph """
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import os

import bottle
from requests_oauthlib import OAuth2Session

from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, RESOURCE, API_VERSION
from config import AUTHORITY_URL, AUTH_ENDPOINT, TOKEN_ENDPOINT
MSGRAPH = OAuth2Session(CLIENT_ID, scope=['User.Read'], redirect_uri=REDIRECT_URI)

# enable non-HTTPS redirect URI for development/testing
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# allow token scope to not match requested scope (other auth libraries allow
# this, but Requests-OAuthlib raises exception on scope mismatch by default)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_IGNORE_SCOPE_CHANGE'] = '1'

bottle.TEMPLATE_PATH = ['./static/templates']

@bottle.route('/')
@bottle.view('homepage.html')
def homepage():
    """Render the home page."""
    return {'sample': 'Requests-OAuthlib'}

@bottle.route('/login')
def login():
    """Prompt user to authenticate."""
    auth_base = AUTHORITY_URL + AUTH_ENDPOINT
    authorization_url, state = MSGRAPH.authorization_url(auth_base)
    MSGRAPH.auth_state = state
    return bottle.redirect(authorization_url)

@bottle.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    if bottle.request.query.state != MSGRAPH.auth_state:
        raise Exception('state returned to redirect URL does not match!')
    MSGRAPH.fetch_token(AUTHORITY_URL + TOKEN_ENDPOINT,
                        client_secret=CLIENT_SECRET,
                        authorization_response=bottle.request.url)
    return bottle.redirect('/graphcall')

@bottle.route('/graphcall')
@bottle.view('graphcall.html')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = RESOURCE + API_VERSION + '/me'
    graphdata = MSGRAPH.get(endpoint).json()
    return {'graphdata': graphdata, 'endpoint': endpoint, 'sample': 'Requests-OAuthlib'}

@bottle.route('/static/<filepath:path>')
def server_static(filepath):
    """Static dev/test file server"""
    static_root = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')
    return bottle.static_file(filepath, root=static_root)

if __name__ == '__main__':
    bottle.run(app=bottle.app(), server='wsgiref', host='localhost', port=5000)
