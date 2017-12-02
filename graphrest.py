"""Sample Microsoft Graph authentication library."""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import json
import os
import time
import urllib.parse
import urllib3
import uuid

import requests
import bottle

import config


# Disable warnings to allow use of non-HTTPS for local dev/test.
urllib3.disable_warnings()

class GraphSession(object):
    """Microsoft Graph connection class.

    Implements OAuth 2.0 Authorization Code Grant workflow, handles
    configuration and state management, adding tokens for authenticated calls to
    Graph, related details.
    """

    def __init__(self, **kwargs):
        """Initialize instance with default values and user-provided overrides.

        The only argument that MUST be specified at runtime is scopes, the list
        of required scopes for this session.

        These settings have default values imported from config.py, but can
        be overridden if desired:
        client_id = client ID (application ID) from app registration portal
        client_secret = client secret (password) from app registration portal
        redirect_uri = must match value specified in app registration portal
        resource = the base URL for calls to Microsoft Graph
        api_version = Graph version ('v1.0' is default, can also use 'beta')
        authority_url = base URL for authorization authority
        auth_endpoint = authentication endpoint (at authority_url)
        token_endpoint = token endpoint (at authority_url)
        cache_state = whether to cache session state in local state.json file
                      If cache_state==True and a valid access token has been
                      cached, the token will be used without any user
                      authentication required ("silent SSO")
        refresh_enable = whether to auto-refresh expired tokens
        """

        self.config = {'client_id': config.CLIENT_ID,
                       'client_secret': config.CLIENT_SECRET,
                       'redirect_uri': config.REDIRECT_URI,
                       'scopes': config.SCOPES,
                       'cache_state': False,
                       'resource': config.RESOURCE,
                       'api_version': config.API_VERSION,
                       'authority_url': config.AUTHORITY_URL,
                       'auth_endpoint': config.AUTHORITY_URL + config.AUTH_ENDPOINT,
                       'token_endpoint': config.AUTHORITY_URL + config.TOKEN_ENDPOINT,
                       'refresh_enable': True}

        # Print warning if any unknown arguments were passed, since those may be
        # errors/typos.
        for key in kwargs:
            if key not in self.config:
                print(f'WARNING: unknown "{key}" argument passed to GraphSession')

        self.config.update(kwargs.items()) # add passed arguments to config

        self.state_manager('init')

        # used by login() and redirect_uri_handler() to identify current session
        self.authstate = ''

        # route to redirect to after authentication; can be overridden in login()
        self.login_redirect = '/'

        # If refresh tokens are enabled, add the offline_access scope.
        # Note that refresh_enable setting takes precedence over whether
        # the offline_access scope is explicitly requested.
        refresh_scope = 'offline_access'
        if self.config['refresh_enable']:
            if refresh_scope not in self.config['scopes']:
                self.config['scopes'].append(refresh_scope)
        elif refresh_scope in self.config['scopes']:
                self.config['scopes'].remove(refresh_scope)

    def __repr__(self):
        """Return string representation of class instance."""
        return ('<GraphSession(loggedin='
                f'{"True" if self.state["loggedin"] else "False"}'
                f', client_id={self.config["client_id"]})>')

    def api_endpoint(self, url):
        """Convert relative endpoint (e.g., 'me') to full Graph API endpoint."""
        if urllib.parse.urlparse(url).scheme in ['http', 'https']:
            return url
        return urllib.parse.urljoin(
            f"{self.config['resource']}{self.config['api_version']}/",
            url.lstrip('/'))

    def delete(self, endpoint, *, headers=None, data=None, verify=False,
               params=None):
        """Wrapper for authenticated HTTP DELETE to API endpoint.

        endpoint = URL (can be partial; for example, 'me/contacts')
        headers = HTTP header dictionary; will be merged with graphrest's
                  standard headers, which include access token
        data = HTTP request body
        verify = the Requests option for verifying SSL certificate; defaults
                 to False for demo purposes. For more information see:
        http://docs.python-requests.org/en/master/user/advanced/#ssl-csert-verification
        params = query string parameters

        Returns Requests response object.
        """
        self.token_validation()
        return requests.delete(self.api_endpoint(endpoint),
                               headers=self.headers(headers),
                               data=data, verify=verify, params=params)

    def get(self, endpoint='me', *, headers=None, stream=False, verify=False, params=None):
        """Wrapper for authenticated HTTP GET to API endpoint.

        endpoint = URL (can be partial; for example, 'me/contacts')
        headers = HTTP header dictionary; will be merged with graphrest's
                  standard headers, which include access token
        stream = Requests streaming option; set to True for image data, etc.
        verify = the Requests option for verifying SSL certificate; defaults
                 to False for demo purposes. For more information see:
        http://docs.python-requests.org/en/master/user/advanced/#ssl-csert-verification
        params = query string parameters

        Returns Requests response object.
        """
        self.token_validation()
        # Merge passed headers with default headers.
        merged_headers = self.headers()
        if headers:
            merged_headers.update(headers)

        return requests.get(self.api_endpoint(endpoint),
                            headers=merged_headers,
                            stream=stream, verify=verify, params=params)

    def headers(self, headers=None):
        """Return a dict of default HTTP headers for calls to Microsoft Graph API,
        including access token and a unique client-request-id.

        Keyword arguments:
        headers -- optional additional headers or overrides for default headers
        """

        token = self.state['access_token']
        merged_headers = {'User-Agent' : 'graphrest-python',
                          'Authorization' : f'Bearer {token}',
                          'Accept' : 'application/json',
                          'Content-Type' : 'application/json',
                          'SdkVersion': 'sample-python-graphrest',
                          'x-client-SKU': 'sample-python-graphrest',
                          'client-request-id' : str(uuid.uuid4()),
                          'return-client-request-id' : 'true'}
        if headers:
            merged_headers.update(headers)
        return merged_headers

    def login(self, login_redirect=None):
        """Ask user to authenticate via Azure Active Directory.
        Optional login_redirect argument is route to redirect to after user
        is authenticated.
        """
        if login_redirect:
            self.login_redirect = login_redirect
        # If caching is enabled, attempt silent SSO first.
        if self.config['cache_state']:
            if self.silent_sso():
                return bottle.redirect(self.login_redirect)

        self.authstate = str(uuid.uuid4())
        data = {
            'response_type': 'code',
            'client_id': self.config['client_id'],
            'redirect_uri': self.config['redirect_uri'],
            'scope': ' '.join(self.config['scopes']),
            'state': self.authstate,
            'prompt': 'select_account',
        }
        params = urllib.parse.urlencode(data)
        url = f"{self.config['auth_endpoint']}?{params}"
        self.state['authorization_url'] = url
        bottle.redirect(self.state['authorization_url'], 302)

    def logout(self, redirect_to=None):
        """Clear current Graph connection state and redirect to specified route.

        If redirect_to is false, no redirection will take place and just clears
        the current logged-in status.
        """

        self.state_manager('init')
        if redirect_to:
            bottle.redirect(redirect_to)

    def patch(self, endpoint, *, headers=None, data=None, verify=False, params=None):
        """Wrapper for authenticated HTTP PATCH to API endpoint.

        endpoint = URL (can be partial; for example, 'me/contacts')
        headers = HTTP header dictionary; will be merged with graphrest's
                  standard headers, which include access token
        data = HTTP request body
        verify = the Requests option for verifying SSL certificate; defaults
                 to False for demo purposes. For more information see:
        http://docs.python-requests.org/en/master/user/advanced/#ssl-csert-verification
        params = query string parameters

        Returns Requests response object.
        """
        self.token_validation()
        return requests.patch(self.api_endpoint(endpoint),
                              headers=self.headers(headers),
                              data=data, verify=verify, params=params)

    def post(self, endpoint, headers=None, data=None, verify=False, params=None):
        """POST to API (authenticated with access token).

        headers = custom HTTP headers (merged with defaults, including access token)

        verify = the Requests option for verifying SSL certificate; defaults
                 to False for demo purposes. For more information see:
        http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification
        """
        self.token_validation()
        merged_headers = self.headers()
        if headers:
            merged_headers.update(headers)

        return requests.post(self.api_endpoint(endpoint),
                             headers=merged_headers, data=data,
                             verify=verify, params=params)

    def put(self, endpoint, *, headers=None, data=None, verify=False, params=None):
        """Wrapper for authenticated HTTP PUT to API endpoint.

        endpoint = URL (can be partial; for example, 'me/contacts')
        headers = HTTP header dictionary; will be merged with graphrest's
                  standard headers, which include access token
        data = HTTP request body
        verify = the Requests option for verifying SSL certificate; defaults
                 to False for demo purposes. For more information see:
        http://docs.python-requests.org/en/master/user/advanced/#ssl-csert-verification
        params = query string parameters

        Returns Requests response object.
        """
        self.token_validation()
        return requests.put(self.api_endpoint(endpoint),
                            headers=self.headers(headers),
                            data=data, verify=verify, params=params)

    def redirect_uri_handler(self):
        """Redirect URL handler for AuthCode workflow. Uses the authorization
        code received from auth endpoint to call the token endpoint and obtain
        an access token.
        """
        # Verify that this authorization attempt came from this app, by checking
        # the received state against what we sent with our authorization request.
        if self.authstate != bottle.request.query.state:
            raise ValueError(f"STATE MISMATCH: {self.authstate} sent, "
                             f"{bottle.request.query.state} received")
        self.authstate = '' # clear state to prevent re-use
        data = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'grant_type': 'authorization_code',
            'code': bottle.request.query.code,
            'redirect_uri': self.config['redirect_uri']
        }
        token_response = requests.post(self.config['token_endpoint'],
                                       data=data)
        self.token_save(token_response)

        if token_response and token_response.ok:
            self.state_manager('save')
        return bottle.redirect(self.login_redirect)

    def silent_sso(self):
        """Attempt silent SSO, by checking whether current access token is valid
        and/or attempting to refresh it.

        Return True is we have successfully stored a valid access token.
        """
        if self.token_seconds() > 0:
            return True # current token is vald
        elif self.state['refresh_token']:
            # we have a refresh token, so use it to refresh the access token
            self.token_refresh()
            return True
        return False # can't do silent SSO at this time

    def state_manager(self, action):
        """Manage self.state dictionary (session/connection metadata).

        action argument must be one of these:
        'init' -- initialize state (set properties to defaults)
        'save' -- save current state (if self.config['cache_state'])
        """
        initialized_state = {'access_token': None, 'refresh_token': None,
                             'token_expires_at': 0, 'authorization_url': '',
                             'token_scope': '', 'loggedin': False}
        filename = 'state.json'

        if action == 'init':
            self.state = initialized_state
            if self.config['cache_state'] and os.path.isfile(filename):
                with open(filename) as fhandle:
                    self.state.update(json.loads(fhandle.read()))
                self.token_validation()
            elif not self.config['cache_state'] and os.path.isfile(filename):
                os.remove(filename)
        elif action == 'save' and self.config['cache_state']:
            with open(filename, 'w') as fhandle:
                fhandle.write(json.dumps(
                    {key:self.state[key] for key in initialized_state}))

    def token_refresh(self):
        """Refresh the current access token."""
        data = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'grant_type': 'refresh_token',
            'refresh_token': self.state['refresh_token'],
        }
        response = requests.post(self.config['token_endpoint'],
                                 data=data, verify=False)
        self.token_save(response)

    def token_save(self, response):
        """Parse an access token out of the JWT response from token endpoint and save it.

        Arguments:
        response -- response object returned by self.config['token_endpoint'], which
                    contains a JSON web token

        Returns True if the token was successfully saved, False if not.
        To manually inspect the contents of a JWT, see http://jwt.ms/.
        """
        json_data = response.json()
        if 'access_token' not in json_data:
            self.logout()
            return False

        self.verify_scopes(json_data['scope'])
        self.state['access_token'] = json_data['access_token']
        self.state['loggedin'] = True

        # token_expires_at = time.time() value (seconds) at which it expires
        self.state['token_expires_at'] = time.time() + int(json_data['expires_in'])
        self.state['refresh_token'] = json_data.get('refresh_token')
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
        the scopes that we requested."""
        self.state['token_scope'] = token_scopes
        scopes_returned = frozenset({_.lower() for _ in token_scopes.split(' ')})
        scopes_expected = frozenset({_.lower() for _ in self.config['scopes']
                                     if _.lower() != 'offline_access'})
        if scopes_expected != scopes_returned:
            print(f'scopes {list(scopes_expected)} requested, but scopes '
                  f'{list(scopes_returned)} returned with token')
