"""graphrest sample for Microsoft Graph"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import os

import bottle
import graphrest

MSGRAPH = graphrest.GraphSession()

bottle.TEMPLATE_PATH = ['./static/templates']

@bottle.route('/')
@bottle.view('homepage.html')
def homepage():
    """Render the home page."""
    return {'sample': 'graphrest'}

@bottle.route('/login')
def login():
    """Prompt user to authenticate."""
    MSGRAPH.login('/graphcall')

@bottle.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    MSGRAPH.redirect_uri_handler()

@bottle.route('/graphcall')
@bottle.view('graphcall.html')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = MSGRAPH.api_endpoint('me')
    graphdata = MSGRAPH.get(endpoint).json()
    return {'graphdata': graphdata, 'endpoint': endpoint, 'sample': 'graphrest'}

@bottle.route('/static/<filepath:path>')
def server_static(filepath):
    """Handler for static files, used with the development server."""
    root_folder = os.path.abspath(os.path.dirname(__file__))
    return bottle.static_file(filepath, root=os.path.join(root_folder, 'static'))

if __name__ == '__main__':
    bottle.run(app=bottle.app(), server='wsgiref', host='localhost', port=5000)
