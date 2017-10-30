"""sample_adal_bottle.py - ADAL/Bottle sample for Microsoft Graph"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import os
import uuid

from adal import AuthenticationContext
import bottle
import requests

from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from config import RESOURCE, API_VERSION, AUTHORITY_URL
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # enable non-HTTPS for testing

SESSION = requests.Session()

bottle.TEMPLATE_PATH = ['./static/templates']

@bottle.route('/')
@bottle.view('homepage.html')
def homepage():
    """Render the home page."""
    return {'sample': 'ADAL'}

@bottle.route('/login')
def login():
    """Prompt user to authenticate."""
    auth_state = str(uuid.uuid4())
    SESSION.auth_state = auth_state
    # note that we don't use the AUTH_ENDPOINT setting from config.py below,
    # because this sample doesn't use the v2.0 endpoint
    return bottle.redirect(AUTHORITY_URL + '/oauth2/authorize?'+ \
        f'response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&'+ \
        f'state={auth_state}&resource={RESOURCE}')

@bottle.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    code = bottle.request.query.code
    auth_state = bottle.request.query.state
    if auth_state != SESSION.auth_state:
        raise Exception('state returned to redirect URL does not match!')
    auth_context = AuthenticationContext(AUTHORITY_URL, api_version=None)
    token_response = auth_context.acquire_token_with_authorization_code(
        code, REDIRECT_URI, RESOURCE, CLIENT_ID, CLIENT_SECRET)
    SESSION.headers.update( \
        {'Authorization': f"Bearer {token_response['accessToken']}",
         'User-Agent': 'adal-sample',
         'Accept': 'application/json',
         'Content-Type': 'application/json',
         'return-client-request-id': 'true'})
    return bottle.redirect('/graphcall')

@bottle.route('/graphcall')
@bottle.view('graphcall.html')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = RESOURCE + API_VERSION + '/me'
    http_headers = {'client-request-id': str(uuid.uuid4())}
    graphdata = SESSION.get(endpoint, headers=http_headers, stream=False).json()
    return {'graphdata': graphdata, 'endpoint': endpoint, 'sample': 'ADAL'}

@bottle.route('/static/<filepath:path>')
def server_static(filepath):
    """Static dev/test file server"""
    static_root = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')
    return bottle.static_file(filepath, root=static_root)

if __name__ == '__main__':
    bottle.run(app=bottle.app(), server='wsgiref', host='localhost', port=5000)
