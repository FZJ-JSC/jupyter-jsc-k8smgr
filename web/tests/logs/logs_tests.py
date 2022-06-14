import copy
import logging
import os

from django.urls import reverse
from jupyterjsc_k8smgr.settings import LOGGER_NAME
from logs import utils
from logs.models import HandlerModel
from tests.user_credentials import UserCredentials


class LogsUnitTest(UserCredentials):

    stream_config = {
        "handler": "stream",
        "configuration": {
            "formatter": "simple",
            "level": 10,
            "stream": "ext://sys.stdout",
        },
    }

    def test_minimal_post(self):
        url = reverse("handler-list")
        response_post = self.client.post(url, data={"handler": "stream"}, format="json")
        self.assertEqual(response_post.status_code, 201)
        model = HandlerModel.objects.all()[0]
        self.assertEqual(model.configuration, utils.default_configurations["stream"])

    def test_only_send_level(self):
        url = reverse("handler-list")
        response_post = self.client.post(
            url,
            data={"handler": "stream", "configuration": {"level": 5}},
            format="json",
        )
        self.assertEqual(response_post.status_code, 201)
        model = HandlerModel.objects.all()[0]
        expected_config = copy.deepcopy(utils.default_configurations["stream"])
        expected_config["level"] = 5
        self.assertEqual(model.configuration, expected_config)

    def test_unsupported_level(self):
        url = reverse("handler-list")
        response_post = self.client.post(
            url,
            data={"handler": "stream", "configuration": {"level": 3}},
            format="json",
        )
        self.assertEqual(response_post.status_code, 400)
        sw = response_post.data[0].startswith("Unsupported level: 3. Supported levels:")
        self.assertTrue(sw, f"Unexpected error msg: {response_post.data[0]}")

    def test_unsupported_type(self):
        url = reverse("handler-list")
        response_post = self.client.post(
            url,
            data={"handler": "file", "configuration": {"filename": 3}},
            format="json",
        )
        self.assertEqual(response_post.status_code, 400)
        self.assertEqual(
            response_post.data[0],
            "filename in configuration must be of type [<class 'str'>] not <class 'int'>",
        )

    def test_list(self):
        url = reverse("handler-list")
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

    def test_list_forbidden(self):
        url = reverse("handler-list")
        self.client.credentials(**self.credentials_unauthorized)
        response_get = self.client.get(url)
        self.client.credentials(**self.credentials_authorized)
        self.assertEqual(response_get.status_code, 403)

    def test_list_unauthorized(self):
        url = reverse("handler-list")
        self.client.credentials(**{})
        response_get = self.client.get(url)
        self.client.credentials(**self.credentials_authorized)
        self.assertEqual(response_get.status_code, 401)

    def test_post_and_delete(self):
        url = reverse("handler-list")
        logtest_url = reverse("logtest-list")
        log = logging.getLogger(LOGGER_NAME)
        response = self.client.post(url, data=self.stream_config, format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 1)
        response = self.client.delete(f"{url}stream/", format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 0)

    def test_post_and_update(self):
        url = reverse("handler-list")
        logtest_url = reverse("logtest-list")
        log = logging.getLogger(LOGGER_NAME)
        response = self.client.post(url, data=self.stream_config, format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 1)
        self.assertEqual(
            log.handlers[0].level, self.stream_config["configuration"]["level"]
        )
        config = copy.deepcopy(self.stream_config)
        config["configuration"]["level"] = 50
        self.client.patch(f"{url}stream/", data=config, format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 1)
        self.assertEqual(log.handlers[0].level, 50)
        response = self.client.delete(f"{url}stream/", format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 0)

    def test_set_additional_file_handler(self):
        url = reverse("handler-list")
        stream_config_trace = copy.deepcopy(self.stream_config)
        stream_config_trace["configuration"]["level"] = 10
        self.client.post(url, data=stream_config_trace, format="json")
        logtest_url = reverse("logtest-list")
        self.client.get(logtest_url)

        filename = "/tmp/filelogger.txt"
        file_config = {
            "handler": "file",
            "configuration": {"filename": filename, "level": 5},
        }
        if os.path.exists(filename):
            os.remove(filename)

        self.client.post(url, data=file_config, format="json")
        self.client.get(logtest_url)

        with open(filename, "r") as f:
            data = f.read()
        self.assertTrue("KeyError" not in data)

        if os.path.exists(filename):
            os.remove(filename)

    def test_do_not_log_forbidden_extras(self):
        url = reverse("handler-list")
        filename = "/tmp/filelogger.txt"
        file_config = {
            "handler": "file",
            "configuration": {"filename": filename, "level": 10},
        }
        if os.path.exists(filename):
            os.remove(filename)

        self.client.post(url, data=file_config, format="json")

        logtest_url = reverse("logtest-list")
        self.client.get(logtest_url)

        with open(filename, "r") as f:
            data = f.read()
        self.assertTrue("KeyError" not in data)
        self.assertTrue("filename_extra" in data)

        if os.path.exists(filename):
            os.remove(filename)
