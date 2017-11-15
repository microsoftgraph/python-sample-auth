"""Requests-OAuthlib sample for Microsoft Graph """
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import os
import uuid

import bottle
import requests_oauthlib

import config

MSGRAPH = requests_oauthlib.OAuth2Session(config.CLIENT_ID,
                                          scope=config.SCOPES,
                                          redirect_uri=config.REDIRECT_URI)

# Enable non-HTTPS redirect URI for development/testing.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Allow token scope to not match requested scope. (Other auth libraries allow
# this, but Requests-OAuthlib raises exception on scope mismatch by default.)
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
    auth_base = config.AUTHORITY_URL + config.AUTH_ENDPOINT
    authorization_url, state = MSGRAPH.authorization_url(auth_base)
    MSGRAPH.auth_state = state
    return bottle.redirect(authorization_url)

@bottle.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    if bottle.request.query.state != MSGRAPH.auth_state:
        raise Exception('state returned to redirect URL does not match!')
    MSGRAPH.fetch_token(config.AUTHORITY_URL + config.TOKEN_ENDPOINT,
                        client_secret=config.CLIENT_SECRET,
                        authorization_response=bottle.request.url)
    return bottle.redirect('/graphcall')

@bottle.route('/graphcall')
@bottle.view('graphcall.html')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = config.RESOURCE + config.API_VERSION + '/me'
    headers = {'SdkVersion': 'sample-python-requests-0.1.0',
               'x-client-SKU': 'sample-python-requests',
               'SdkVersion': 'sample-python-requests',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    graphdata = MSGRAPH.get(endpoint, headers=headers).json()
    return {'graphdata': graphdata, 'endpoint': endpoint, 'sample': 'Requests-OAuthlib'}

@bottle.route('/static/<filepath:path>')
def server_static(filepath):
    """Handler for static files, used with the development server."""
    root_folder = os.path.abspath(os.path.dirname(__file__))
    return bottle.static_file(filepath, root=os.path.join(root_folder, 'static'))

if __name__ == '__main__':
    bottle.run(app=bottle.app(), server='wsgiref', host='localhost', port=5000)
