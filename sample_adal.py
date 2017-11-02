"""ADAL/Flask sample for Microsoft Graph """
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import os
import uuid

from adal import AuthenticationContext
import flask
import requests

import config

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # enable non-HTTPS for testing

APP = flask.Flask(__name__, template_folder='static/templates')
APP.debug = True
APP.secret_key = 'development'

SESSION = requests.Session()

@APP.route('/')
def homepage():
    """Render the home page."""

    return flask.render_template('homepage.html', sample='ADAL')

@APP.route('/login')
def login():
    """Prompt user to authenticate."""

    auth_state = str(uuid.uuid4())
    SESSION.auth_state = auth_state
    # note that we don't use the AUTH_ENDPOINT setting from config.py below,
    # because this sample doesn't use the v2.0 endpoint
    return flask.redirect(config.AUTHORITY_URL + '/oauth2/authorize?'
                          f'response_type=code&client_id={config.CLIENT_ID}&'
                          f'redirect_uri={config.REDIRECT_URI}&'
                          f'state={auth_state}&'
                          f'resource={config.RESOURCE}')

@APP.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""

    code = flask.request.args['code']
    auth_state = flask.request.args['state']
    if auth_state != SESSION.auth_state:
        raise Exception('state returned to redirect URL does not match!')
    auth_context = AuthenticationContext(config.AUTHORITY_URL, api_version=None)
    token_response = auth_context.acquire_token_with_authorization_code(
        code, config.REDIRECT_URI, config.RESOURCE, config.CLIENT_ID, config.CLIENT_SECRET)
    SESSION.headers.update({'Authorization': f"Bearer {token_response['accessToken']}",
                            'User-Agent': 'adal-sample',
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'return-client-request-id': 'true'})
    return flask.redirect('/graphcall')

@APP.route('/graphcall')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""

    endpoint = config.RESOURCE + config.API_VERSION + '/me'
    http_headers = {'client-request-id': str(uuid.uuid4())}
    graphdata = SESSION.get(endpoint, headers=http_headers, stream=False).json()
    return flask.render_template('graphcall.html',
                                 graphdata=graphdata,
                                 endpoint=endpoint,
                                 sample='ADAL')

if __name__ == '__main__':
    APP.run()
