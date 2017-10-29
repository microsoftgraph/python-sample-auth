"""sample_flask.py - Flask-OAuthlib sample for Microsoft Graph"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import uuid

from flask import Flask, redirect, render_template, request, session
from flask_oauthlib.client import OAuth

from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, RESOURCE, API_VERSION
from config import AUTHORITY_URL, AUTH_ENDPOINT, TOKEN_ENDPOINT

APP = Flask(__name__, template_folder='static/templates')
APP.debug = True
APP.secret_key = 'development'

OAUTH = OAuth(APP)
MSGRAPH = OAUTH.remote_app(
    'microsoft', consumer_key=CLIENT_ID, consumer_secret=CLIENT_SECRET,
    request_token_params={'scope': 'User.Read'},
    base_url=RESOURCE + API_VERSION + '/',
    request_token_url=None, access_token_method='POST',
    access_token_url=AUTHORITY_URL + TOKEN_ENDPOINT,
    authorize_url=AUTHORITY_URL + AUTH_ENDPOINT)

@APP.route('/')
def homepage():
    """Render the home page."""
    return render_template('homepage.html', sample='Flask-OAuthlib')

@APP.route('/login')
def login():
    """Prompt user to authenticate."""
    session['state'] = str(uuid.uuid4())
    return MSGRAPH.authorize(callback=REDIRECT_URI, state=session['state'])

@APP.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    if str(session['state']) != str(request.args['state']):
        raise Exception('state returned to redirect URL does not match!')
    response = MSGRAPH.authorized_response()
    session['access_token'] = response['access_token']
    return redirect('/graphcall')

@APP.route('/graphcall')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = 'me'
    graphdata = MSGRAPH.get(endpoint).data
    return render_template('graphcall.html',
                           graphdata=graphdata,
                           endpoint=RESOURCE + API_VERSION + '/' + endpoint,
                           sample='Flask-OAuthlib')

@MSGRAPH.tokengetter
def get_token():
    """Called by flask_oauthlib.client to retrieve current access token."""
    return (session.get('access_token'), '')

if __name__ == '__main__':
    APP.run()
