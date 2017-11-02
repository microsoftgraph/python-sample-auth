"""sample Microsoft Graph authentication library"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import json
import os
import time
import urllib.parse
import uuid

import requests
import bottle

import config

class GraphSession(object):
    """Microsoft Graph connection class. Implements OAuth 2.0 Authorization Code
    Grant workflow, handles configuration and state management, adding tokens
    for authenticated calls to Graph, related details.
    """

    def __init__(self, **kwargs):
        """Initialize instance with default values and user-provided overrides.

        These settings must be specified at runtime:
        client_id = client ID (application ID) from app registration portal
        client_secret = client secret (password) from app registration portal
        redirect_uri = must match value specified in app registration portal
        scopes = list of required scopes/permissions

        These settings have default values but can be overridden if desired:
        resource = the base URL for calls to Microsoft Graph
        api_version = Graph version ('v1.0' is default, can also use 'beta')
        authority_url = base URL for authorization authority
        auth_endpoint = authentication endpoint (at authority_url)
        token_endpoint = token endpoint (at authority_url)
        cache_token = whether to cache token/state in local cache.json file
        refresh_enable = whether to auto-refresh expired tokens
        """

        self.config = {'client_id': '', 'client_secret': '', 'redirect_uri': '',
                       'scopes': [], 'cache_token': False,
                       'resource': config.RESOURCE, 'api_version': config.API_VERSION,
                       'authority_url': config.AUTHORITY_URL,
                       'auth_endpoint': config.AUTHORITY_URL + config.AUTH_ENDPOINT,
                       'token_endpoint': config.AUTHORITY_URL + config.TOKEN_ENDPOINT,
                       'refresh_enable': True}
        self.config.update(kwargs.items()) # add passed arguments to config

        self.state_initialize()
        self.cache('read')

        # If refresh tokens are enabled, add the offline_access scope.
        # Note that refresh_enable setting takes precedence over whether
        # the offline_access scope is explicitly requested.
        refresh_scope = 'offline_access'
        if self.config['refresh_enable']:
            if refresh_scope not in self.config['scopes']:
                self.config['scopes'].append(refresh_scope)
        else:
            if refresh_scope in self.config['scopes']:
                self.config['scopes'].remove(refresh_scope)

    def api_endpoint(self, url):
        """Convert relative endpoint (e.g., 'me') to full Graph API endpoint."""

        if urllib.parse.urlparse(url).scheme in ['http', 'https']:
            return url
        return urllib.parse.urljoin(
            f"{self.config['resource']}{self.config['api_version']}/",
            url.lstrip('/'))

    def cache(self, action):
        """Manage self.state dictionary (cached connection metadata).

        the action argument value must be one of these:
        'save' -- save current state (if self.config['cache_token'])
        'read' -- restore state from cached version (if self.config['cache_token'])
        'clear' -- clear cached state
        """

        cache_file = 'cache.json'

        if action == 'save' and self.config['cache_token']:
            cached_values = ['access_token', 'token_expires_at', 'token_scope',
                             'refresh_token', 'authorization_url', 'loggedin']
            cached_data = {key:self.state[key] for key in cached_values}
            with open(cache_file, 'w') as fhandle:
                fhandle.write(json.dumps(cached_data))
        elif action == 'read' and self.config['cache_token']:
            if os.path.isfile(cache_file):
                with open(cache_file) as fhandle:
                    cached_data = json.loads(fhandle.read())
                self.state.update(cached_data)
                self.token_validation()
                self.cache('save') # update cache with current state
        elif os.path.isfile(cache_file):
            os.remove(cache_file)

    def headers(self, headers=None):
        """Returns dictionary of default HTTP headers for calls to Microsoft Graph API,
        including access token and a unique client-request-id.

        Keyword arguments:
        headers -- optional additional headers or overrides for default headers
        """

        token = self.state['access_token']
        merged_headers = {'User-Agent' : 'graphrest-python',
                          'Authorization' : f'Bearer {token}',
                          'Accept' : 'application/json',
                          'Content-Type' : 'application/json',
                          'client-request-id' : str(uuid.uuid4()),
                          'return-client-request-id' : 'true'}
        if headers:
            merged_headers.update(headers)
        return merged_headers

    def login(self):
        """Ask user to authenticate via Azure Active Directory."""

        self.state['authstate'] = str(uuid.uuid4())
        self.state['authorization_url'] = self.config['auth_endpoint'] + \
            '?response_type=code' + \
            '&client_id=' + self.config['client_id'] + \
            '&redirect_uri=' + self.config['redirect_uri'] + \
            '&scope=' + '%20'.join(self.config['scopes']) + \
            '&state=' + self.state['authstate']
        bottle.redirect(self.state['authorization_url'], 302)

    def logout(self, redirect_to='/'):
        """Clear current Graph connection state and redirect to specified route.
        If redirect_to == None, no redirection will take place and just clears
        the current logged-in status.
        """

        self.state_initialize()
        self.cache('clear')
        if redirect_to:
            bottle.redirect(redirect_to)

    def redirect_uri_handler(self, redirect_to='/'):
        """Redirect URL handler for AuthCode workflow. Uses the authorization
        code received from auth endpoint to call the token endpoint and obtain
        an access token.
        """

        # Verify that this authorization attempt came from this app, by checking
        # the received state against what we sent with our authorization request.
        if self.state['authstate'] != bottle.request.query.state:
            raise Exception(f"STATE MISMATCH: {self.state['authstate']} sent,"
                            f"{bottle.request.query.state} received")
        self.state['authstate'] = '' # clear state to prevent re-use

        self.state['authcode'] = bottle.request.query.code
        token_response = requests.post(self.config['token_endpoint'],
                                       data={'client_id': self.config['client_id'],
                                             'client_secret': self.config['client_secret'],
                                             'grant_type': 'authorization_code',
                                             'code': bottle.request.query.code,
                                             'redirect_uri': self.config['redirect_uri']})
        self.token_save(token_response)

        if not token_response or not token_response.ok:
            return bottle.redirect(redirect_to) # token request failed
        self.cache('save')
        return bottle.redirect(redirect_to)

    def state_initialize(self):
        """Initialize connection state - sets self.state to default values."""

        self.state = {'access_token': None, 'refresh_token': None, 'token_expires_at': 0,
                      'authorization_url': '', 'authcode': '', 'authstate': '',
                      'token_scope': '', 'loggedin': False}

    def token_refresh(self):
        """Refresh the current access token."""

        if not self.config.get('refresh_enable', False):
            return
        response = requests.post(self.config['token_endpoint'],
                                 data={'client_id': self.config['client_id'],
                                       'client_secret': self.config['client_secret'],
                                       'grant_type': 'refresh_token',
                                       'refresh_token': self.state['refresh_token']},
                                 verify=False)
        self.token_save(response)

    def token_save(self, response):
        """Parse an access token out of the JWT response from token endpoint and save it.

        Arguments:
        response -- response object returned by self.config['token_endpoint'], which
                    contains a JSON web token

        Returns True if the token was successfully saved, False if not.
        To manually inspect the contents of a JWT, see http://jwt.ms/.
        """

        jsondata = response.json()
        if not 'access_token' in jsondata:
            self.logout(redirect_to=None)
            return False

        self.verify_scopes(jsondata['scope'])
        self.state['access_token'] = jsondata['access_token']
        self.state['loggedin'] = True

        # token_expires_at = time.time() value (seconds) at which it expires
        self.state['token_expires_at'] = time.time() + int(jsondata['expires_in'])
        self.state['refresh_token'] = jsondata.get('refresh_token', None)
        return True

    def token_seconds(self):
        """Return number of seconds until current access token will expire."""

        if not self.state['access_token'] or time.time() >= self.state['token_expires_at']:
            return 0
        return int(self.state['token_expires_at'] - time.time())

    def token_validation(self, nseconds=5):
        """Verify that current access token is valid for at least nseconds, and
        if not then attempt to refresh it. Can be used to assure a valid token
        before making a call to Graph.
        """

        if self.token_seconds() < nseconds and self.config['refresh_enable']:
            self.token_refresh()

    def verify_scopes(self, token_scopes):
        """Verify that the list of scopes returned with an access token match
        the scopes that we requested.
        """

        self.state['token_scope'] = token_scopes
        scopes_returned = frozenset({_.lower() for _ in token_scopes.split(' ')})
        scopes_expected = frozenset({_.lower() for _ in self.config['scopes']
                                     if _.lower() != 'offline_access'})
        if scopes_expected != scopes_returned:
            print(f'WARNING: requested scopes {list(scopes_expected)}'
                  f' but token was returned with scopes {list(scopes_returned)}')
