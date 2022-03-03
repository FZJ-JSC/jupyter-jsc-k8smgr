import os
import pytest

from functools import partial
from jupyterhub import orm
from tornado import web
from tornado.httpclient import HTTPResponse
from unittest.mock import Mock, patch
from urllib.parse import urljoin, urlparse

from oauthenticator.oauth2 import STATE_COOKIE_NAME
from oauthenticator.tests.mocks import setup_oauth_mock, mock_handler
from customauthenticator.customoauthenticator import CustomGenericOAuthenticator
from custom_utils import VoException


oauth_base_url = "https://unity-jsc.fz-juelich.de"
token_path = "/oauth2/token"
userinfo_path = "/oauth2/userinfo"
tokeninfo_path = "/oauth2/tokeninfo"
custom_config_file = os.environ.get("CUSTOM_CONFIG_FILE", "~/tests/config/jupyterhub_custom_config.json")


def user_model(username, used_authenticator_attr='ldap'):
    """Return a user model"""
    user = {
        'username': username,
        'email': username+'@fz-juelich.de',
        'hpc_infos_attribute': [ 
            'demouser1,demo_site,project1,demo-user-1', 
            'demouser1,demo_site_NOBATCH,project1,demo-user-1', 
            'demouser1,demo_site,users,demo-user-1'
        ], 
        'used_authenticator_attr': used_authenticator_attr, 
    }
    return user
    

def get_simple_handler(custom_oauth_client):
    return custom_oauth_client.handler_for_user(user_model('demo-user-1'))


def _get_authenticator(**kwargs):
    return CustomGenericOAuthenticator(
        token_url=urljoin(oauth_base_url, token_path),
        userdata_url=urljoin(oauth_base_url, userinfo_path),
        **kwargs
    )


@pytest.fixture
def custom_oauth_client(client):
    uri = urlparse(oauth_base_url)
    setup_oauth_mock(
        client,
        host=uri.netloc,
        access_token_path=token_path,
        user_path=userinfo_path,token_type='bearer',
    )
    # Add tokeninfo url to mocked requests
    get_tokeninfo = client.hosts[uri.netloc][1][1]
    for host in client.hosts:
        client.hosts[host].append( (tokeninfo_path, get_tokeninfo) )
    return client


@pytest.fixture
def get_authenticator(custom_oauth_client, **kwargs):
    return partial(_get_authenticator, http_client=custom_oauth_client, **kwargs)


@pytest.fixture
def mock_user():
    class User:
        name = 'demo-user'
        orm_user = orm.User(name=name)
        state = {}

        async def get_auth_state(self):
            return self.state

    return User()


async def test_custom_oauth(get_authenticator, custom_oauth_client):
    authenticator = get_authenticator(tls_verify=False)
    handler = get_simple_handler(custom_oauth_client)
    user_info = await authenticator.authenticate(handler)

    assert sorted(user_info) == ['auth_state', 'name']
    name = user_info['name']
    assert name == 'demo-user-1'
    auth_state = user_info['auth_state']
    assert 'access_token' in auth_state
    assert 'oauth_user' in auth_state
    assert 'refresh_token' in auth_state
    assert 'scope' in auth_state


async def test_config_file(get_authenticator):
    no_config_authenticator = get_authenticator(custom_config_file="fake_file.json")
    assert no_config_authenticator.custom_config == {}

    authenticator = get_authenticator(custom_config_file=custom_config_file)
    assert authenticator.custom_config != {}


async def test_post_auth_hook(get_authenticator, custom_oauth_client):
    authenticator = get_authenticator(
        custom_config_file=custom_config_file,
        tokeninfo_url=oauth_base_url+tokeninfo_path,
    )
    handler = get_simple_handler(custom_oauth_client)
    handler.statsd = Mock()
    user_info = await authenticator.authenticate(handler)

    post_auth_info = await authenticator.post_auth_hook(authenticator, handler, user_info)
    name = post_auth_info['name']
    assert name == 'demo-user-1'
    auth_state = post_auth_info['auth_state']
    assert 'exp' in auth_state
    assert 'last_login' in auth_state
    assert 'vo_active' in auth_state
    assert 'vo_available' in auth_state


async def test_no_vo_post_auth_hook(get_authenticator, custom_oauth_client):
    authenticator = get_authenticator(
        custom_config_file=custom_config_file,
        tokeninfo_url=oauth_base_url+tokeninfo_path,
    )
    handler = custom_oauth_client.handler_for_user(
        user_model('demo-user-1', used_authenticator_attr='unknown')
    )
    handler.statsd = Mock()
    user_info = await authenticator.authenticate(handler)

    with pytest.raises(VoException, match=r"demo-user-1"):
        await authenticator.post_auth_hook(authenticator, handler, user_info)


async def test_authorize_redirect_params_allowed(get_authenticator):
    def foo():
        return { 'key1': ['value1', 'value2'] }

    authenticator = get_authenticator(
        extra_params_allowed_runtime=foo
    )

    handler = mock_handler(
        authenticator.login_handler,
        'https://hub.example.com/hub/oauth_login?extra_param_key1=value1',
        authenticator=authenticator
    )
    handler.authorize_redirect()
    assert handler.get_status() == 302
    assert 'Location' in handler._headers
    assert 'key1=value1' in handler._headers['Location']
    assert 'extra_param' not in handler._headers['Location']
    
    handler = mock_handler(
        authenticator.login_handler,
        'https://hub.example.com/hub/oauth_login?extra_param_key1=value2',
        authenticator=authenticator
    )
    handler.authorize_redirect()
    assert handler.get_status() == 302
    assert 'Location' in handler._headers
    assert 'key1=value2' in handler._headers['Location']
    assert 'extra_param' not in handler._headers['Location']


async def test_authorize_redirect_params_not_allowed(get_authenticator):
    def foo():
        return { 'key1': ['value1', 'value2'] }
        
    authenticator = get_authenticator(
        extra_params_allowed_runtime=foo
    )

    handler = mock_handler(
        authenticator.login_handler,
        'https://hub.example.com/hub/oauth_login?extra_param_key1=value3',
        authenticator=authenticator
    )
    handler.authorize_redirect()
    assert handler.get_status() == 302
    assert 'Location' in handler._headers
    assert 'key1' not in handler._headers['Location']

    handler = mock_handler(
        authenticator.login_handler,
        'https://hub.example.com/hub/oauth_login?extra_param_key2=value1',
        authenticator=authenticator
    )
    handler.authorize_redirect()
    assert handler.get_status() == 302
    assert 'Location' in handler._headers
    assert 'key2' not in handler._headers['Location']


async def test_custom_logout(custom_oauth_client, mock_user, monkeypatch):
    login_url = "https://hub.example.com/hub/login"
    custom_oauth_client.add_host('backend.svc', [
        ('/api/unity/', lambda request: HTTPResponse(request, code=200)),
    ])

    authenticator = CustomGenericOAuthenticator(custom_config_file=custom_config_file, )
    logout_handler = mock_handler(
        authenticator.logout_handler, 
        "https://hub.example.com/hub/logout", 
        authenticator=authenticator
    )   
    mock_user.authenticator = authenticator

    monkeypatch.setattr(web.RequestHandler, 'redirect', Mock())
    logout_handler.clear_login_cookie = Mock()
    logout_handler.clear_cookie = Mock()    
    logout_handler._jupyterhub_user = mock_user
    monkeypatch.setitem(logout_handler.settings, 'statsd', Mock())
    monkeypatch.setitem(logout_handler.settings, 'login_url', login_url)

    # Sanity check: Ensure the logout handler and url are set on the hub
    handlers = [handler for _, handler in authenticator.get_handlers(None)]
    assert any([h == authenticator.logout_handler for h in handlers])
    assert authenticator.logout_url('http://myhost') == 'http://myhost/logout'

    with patch('customauthenticator.customoauthenticator.drf_request') as mock_drf_request:
        await logout_handler.get()
    mock_drf_request.assert_called_once()
    logout_handler.redirect.assert_called_once_with(login_url, permanent=False)
    assert logout_handler.clear_login_cookie.called
    logout_handler.clear_cookie.assert_called_once_with(STATE_COOKIE_NAME)


# Test user.auth_state after logout?