from unittest import mock

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class MockResponse:
    _json = {}

    def __init__(self, status_code, json):
        self.status_code = status_code
        self._json = json

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"Unexpected Status Code: {self.status_code}")


def mocked_requests_post_running(*args, **kwargs):
    return MockResponse(200, {"running": True})


class UserCredentials(APITestCase):
    user_unauthorized_username = "unauthorized"
    user_authorized_username = "authorized"
    user_authorized_username_2 = "authorized_2"
    user_authorized = None
    user_authorized_2 = None
    user_unauthorized = None
    user_password = "12345"
    authorized_group_webservice = "access_to_webservice"
    authorized_group_logs = "access_to_logging"
    credentials_authorized = {}
    credentials_authorized_2 = {}
    credentials_unauthorized = {}
    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    def create_user(self, username, passwd):
        user = User.objects.create(username=username)
        user.set_password(passwd)
        user.save()
        user.auth_token = Token.objects.create(user=user)
        return user

    def setUp(self):
        self.user_authorized = self.create_user(
            self.user_authorized_username, self.user_password
        )
        self.credentials_authorized = {
            "HTTP_AUTHORIZATION": f"token {self.user_authorized.auth_token.key}"
        }
        self.user_authorized_2 = self.create_user(
            self.user_authorized_username_2, self.user_password
        )
        self.credentials_authorized_2 = {
            "HTTP_AUTHORIZATION": f"token {self.user_authorized_2.auth_token.key}"
        }
        self.user_unauthorized = self.create_user(
            self.user_unauthorized_username, self.user_password
        )
        self.credentials_unauthorized = {
            "HTTP_AUTHORIZATION": f"token {self.user_unauthorized.auth_token.key}"
        }
        group1 = Group.objects.create(name=self.authorized_group_webservice)
        group2 = Group.objects.create(name=self.authorized_group_logs)
        self.user_authorized.groups.add(group1)
        self.user_authorized.groups.add(group2)
        self.user_authorized_2.groups.add(group1)
        self.user_authorized_2.groups.add(group2)
        self.client.credentials(**self.credentials_authorized)
        return super().setUp()
