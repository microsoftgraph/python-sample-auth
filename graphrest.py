"""graphrest.py - sample Microsoft Graph authentication library"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import json
import os
import time
import urllib.parse
import uuid

import requests
from bottle import redirect, request

# defaults/constants for Microsoft Graph authentication
API_BASE = 'https://graph.microsoft.com/'
API_VERSION = 'v1.0'
AUTH_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize/'
TOKEN_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

class GraphSession(object):
    """Microsoft Graph connection class. Implements OAuth 2.0 Authorization Code
    Grant workflow, handles configuration and state management, adding tokens
    for authenticated calls to Graph, related details."""
    def __init__(self, **kwargs):
        """
        These settings must be specified at runtime:
        client_id = client ID (application ID) from app registration portal
        client_secret = client secret (password) from app registration portal
        redirect_uri = must match value specified in app registration portal
        scopes = list of required scopes/permissions

        These settings have default values but can be overridden if desired:
        api_base = the base URL for calls to Microsoft Graph
        api_version = Graph version ('v1.0' is default, can also use 'beta')
        auth_endpoint = authentication endpoint for Azure AD
        token_endpoint = token endpoint for Azure AD
        cache_token = whether to cache token/state in local cache.json file
        refresh_enable = whether to auto-refresh expired tokens
        """
        self.config = {'client_id': '', 'client_secret': '', 'redirect_uri': '',
                       'scopes': [], 'cache_token': False, 'api_base': API_BASE,
                       'api_version': API_VERSION, 'auth_endpoint': AUTH_ENDPOINT,
                       'refresh_enable': True, 'token_endpoint': TOKEN_ENDPOINT}
        self.config.update(kwargs.items()) # add passed arguments to config

        self.initialize_state()
        self.manage_cache('read')

        # if refresh tokens are enabled, add the offline_access scope.
        # # Note that refresh_enable setting takes precedence over whether
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
        if url.split('/')[0].lower() in ['http:', 'https:']:
            return url
        return urllib.parse.urljoin(self.config['api_base'] + \
            self.config['api_version'] + '/', url.lstrip('/'))

    def delete(self, url, headers=None, data=None, verify=False, params=None):
        """Wrapper for authenticated HTTP DELETE to API endpoint.
        verify = Requests option for verifying SSL certificate; defaults
                 to False for demo purposes. For more information see:
        http://docs.python-requests.org/en/master/user/advanced/#ssl-csert-verification
        """
        self.token_validation()
        return self.state['session'].delete(self.api_endpoint(url), \
            headers=self.http_request_headers(headers), \
            data=data, verify=verify, params=params)

    def fetch_token(self, authcode):
        """attempt to fetch an access token, using specified authorization code."""
        self.state['authcode'] = authcode
        response = self.state['session'].post( \
            self.config['token_endpoint'], \
            data={'client_id': self.config['client_id'],
                  'client_secret': self.config['client_secret'],
                  'grant_type': 'authorization_code',
                  'code': authcode,
                  'redirect_uri': self.config['redirect_uri']})

        if self.parse_json_web_token(response):
            return response # valid token saved
        return None # token request failed

    def get(self, endpoint, headers=None, stream=False, jsononly=False):
        """Wrapper for authenticated HTTP GET from API endpoint.
        endpoint = absolute or relative URL (e.g., "me/contacts")
        headers = dictionary of HTTP request headers, can override the defaults
                  returned by http_request_headers()
        stream = Requests stream argument; e.g., use True for image data
        jsononly = if True, the JSON 'value' element is returned instead of
                   the response object
        """
        self.token_validation()
        response = self.state['session'].get(self.api_endpoint(endpoint), \
            headers=self.http_request_headers(headers), stream=stream)

        if jsononly:
            return response.json().get('value', None)
        return response

    def get_token(self, redirect_to='/'):
        """Redirect URL handler. For AuthCode workflow, uses the authorization
        code received from auth endpoint to call the token endpoint and obtain
        an access token."""

        # Verify that this authorization attempt came from this app, by checking
        # the received state against what we sent with our authorization request.
        if self.state['authstate'] != request.query.state:
            raise Exception(' -> SHUTTING DOWN: state mismatch' + \
                '\n\nState SENT: {0}\n\nState RECEIVED: {1}'. \
                format(str(self.state['authstate']), str(request.query.state)))
        self.state['authstate'] = '' # clear state to prevent re-use

        token_response = self.fetch_token(request.query.code)
        if not token_response or not token_response.ok:
            return redirect(redirect_to) # token request failed

        self.manage_cache('save')

        return redirect(redirect_to)

    def http_request_headers(self, headers=None):
        """Returns dictionary of the default HTTP headers used for calls to
        the Graph API, including access token.
        headers = optional additional headers or overrides for the default
                  headers, to be merged into returned dictionary"""
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

    def initialize_state(self):
        """Initialize connection state - sets self.state to default values."""
        self.state = {'session': requests.Session(), 'access_token': None,
                      'refresh_token': None, 'token_expires_at': 0, 'auth_url': '',
                      'authcode': '', 'authstate': '', 'token_scope': '',
                      'loggedin': False}

    def login(self):
        """Ask user to authenticate via Azure Active Directory."""
        self.state['authstate'] = str(uuid.uuid4())
        self.state['auth_url'] = self.config['auth_endpoint'] + \
            '?response_type=code' + \
            '&client_id=' + self.config['client_id'] + \
            '&redirect_uri=' + self.config['redirect_uri'] + \
            '&scope=' + '%20'.join(self.config['scopes']) + \
            '&state=' + self.state['authstate']
        redirect(self.state['auth_url'], 302)

    def logout(self, redirect_to='/'):
        """Clear current Graph connection state and redirect to specified route.
        If redirect_to == None, no redirection will take place and we just
        clear the current logged-in status."""
        self.initialize_state()
        self.manage_cache('clear')
        if redirect_to:
            redirect(redirect_to)

    def manage_cache(self, action):
        """Manage cached state
        'save' = save current state (if self.config['cache_token'])
        'read' = restore state from cached version (if self.config['cache_token'])
        'clear' = clear cached state"""
        cachefile = 'cache.json'

        if action == 'save' and self.config['cache_token']:
            cached_values = ['access_token', 'token_expires_at', 'token_scope',
                             'refresh_token', 'auth_url', 'loggedin']
            cached_data = {key:self.state[key] for key in cached_values}
            open(cachefile, 'w').write(json.dumps(cached_data))
        elif action == 'read' and self.config['cache_token']:
            if os.path.isfile(cachefile):
                cached_data = json.loads(open(cachefile).read())
                self.state.update(cached_data)
                self.token_validation()
                self.manage_cache('save') # update cache with current state
        else:
            if os.path.isfile(cachefile):
                os.remove(cachefile)

    def parse_json_web_token(self, response):
        """Parse a retrieved access token out of the JWT and save it.
        response = response object returned by self.config['token_endpoint']
        Returns True if the token was successfully saved, False if not.
        To manually inspect the contents of a JWT, see http://jwt.ms/"""
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

    def patch(self, url, headers=None, data=None, verify=False, params=None):
        """Wrapper for authenticated HTTP PATCH to API endpoint."""
        self.token_validation()
        return self.state['session'].patch(self.api_endpoint(url), \
            headers=self.http_request_headers(headers), \
            data=data, verify=verify, params=params)

    def post(self, url, headers=None, data=None, verify=False, params=None):
        """Wrapper for authenticated HTTP POST to API endpoint."""
        self.token_validation()
        return self.state['session'].post(self.api_endpoint(url), \
            headers=self.http_request_headers(headers), \
            data=data, verify=verify, params=params)

    def refresh_access_token(self):
        """Refresh the current access token."""
        if not self.config.get('refresh_enable', False):
            return
        response = self.state['session'].post( \
            self.config['token_endpoint'], \
            data={'client_id': self.config['client_id'],
                  'client_secret': self.config['client_secret'],
                  'grant_type': 'refresh_token',
                  'refresh_token': self.state['refresh_token']}, verify=False)
        self.parse_json_web_token(response)

    def token_seconds(self):
        """Return number of seconds until current access token will expire."""
        if not self.state['access_token'] or \
            time.time() >= self.state['token_expires_at']:
            return 0
        return int(self.state['token_expires_at'] - time.time())

    def token_validation(self, nseconds=5):
        """Verify that current access token is valid for at least nseconds, and
        if not then attempt to refresh it. Can be used to assure a valid token
        before making a call to Graph."""
        if self.token_seconds() < nseconds and self.config['refresh_enable']:
            self.refresh_access_token()

    def verify_scopes(self, token_scopes):
        """Verify that the list of scopes returned with an access token match
        the scopes that we requested."""
        self.state['token_scope'] = token_scopes
        scopes_returned = set([_.lower() for _ in token_scopes.split(' ')])
        scopes_expected = set([_.lower() for _ in self.config['scopes']
                               if _.lower() != 'offline_access'])
        if scopes_expected != scopes_returned:
            print('WARNING: requested scopes ' + str(scopes_expected) +
                  ' but token was returned with scopes ' + str(scopes_returned))
