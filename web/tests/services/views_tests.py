import os
import shutil
from unittest import mock

from django.http.response import HttpResponse
from django.urls.base import reverse
from services.models import ServicesModel
from services.models import UserModel
from tests.mocks import config_mock
from tests.mocks import k8s_ApiClient
from tests.mocks import k8s_client_AppsV1Api
from tests.mocks import k8s_client_CoreV1Api
from tests.mocks import k8s_config_load_incluster_config
from tests.mocks import k8s_utils_create_from_yaml
from tests.mocks import k8s_V1Secret
from tests.mocks import mocked_exception
from tests.mocks import services_base
from tests.mocks import userhomes_base
from tests.user_credentials import UserCredentials

# from tests.user_credentials import mocked_requests_post_running
# from .mocks import mocked_pass
# from .mocks import mocked_pyunicore_client_init
# from .mocks import mocked_pyunicore_job_init
# from .mocks import mocked_pyunicore_transport_init


class ServiceViewTests(UserCredentials):
    def setUp(self):
        for x in os.walk(userhomes_base):
            if x[1] and x[0].startswith("web/tests/files"):
                shutil.rmtree(f"{x[0]}/{x[1][0]}")

        for x in os.walk(services_base):
            if x[1] and x[0].startswith("web/tests/files"):
                shutil.rmtree(f"{x[0]}/{x[1][0]}")
        return super().setUp()

    def test_health(self):
        url = "/api/health/"
        r = self.client.get(url, format="json")
        self.assertEqual(200, r.status_code)

    simple_request_data = {
        "user_options": {
            "system": "HDF-Cloud",
            "service": "JupyterLab/JupyterLab",
            "vo": "myvo",
        },
        "auth_state": {"access_token": "ZGVtb3VzZXI6dGVzdDEyMw=="},
        "env": {
            "JUPYTERHUB_USER_ID": 17,
            "JUPYTERHUB_API_TOKEN": "secret",
            "JUPYTERHUB_STATUS_URL": "http://jhub:8000",
        },
        "start_id": "abcdefgh",
    }

    def mock_return_HttpResponse(*args, **kwargs):
        return HttpResponse()

    def mock_return_none(*args, **kwargs):
        pass

    @mock.patch(
        "services.views.ServicesViewSet.create", side_effect=mock_return_HttpResponse
    )
    def test_viewset_create_called(self, mock):
        url = reverse("services-list")
        self.client.post(url, data={}, format="json")
        self.assertTrue(mock.called)

    def test_invalid_input_data(self):
        url = reverse("services-list")
        r = self.client.post(url, data={}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), ["Missing key in input data: env"])

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

    @mock.patch(
        target="services.utils.common.start_service",
        side_effect=mocked_exception,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_exception_model_deleted(
        self,
        config_mocked,
        start_service,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 500)
        models = ServicesModel.objects.all()
        self.assertEqual(len(models), 0)

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_service_model_created(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        pre_models = ServicesModel.objects.all()
        self.assertEqual(len(pre_models), 0)
        r = self.client.post(url, data=self.simple_request_data, format="json")
        models = ServicesModel.objects.all()
        self.assertEqual(len(models), 1)

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_user_model_created(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        pre_models = UserModel.objects.all()
        self.assertEqual(len(pre_models), 0)
        r = self.client.post(url, data=self.simple_request_data, format="json")
        models = UserModel.objects.all()
        self.assertEqual(len(models), 1)

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_userhome_created(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertTrue(os.path.isdir(f"{userhomes_base}/authorized_17"))

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_service_dir_created(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        model = ServicesModel.objects.first()
        self.assertTrue(
            os.path.isdir(f"{services_base}/{model.servername}-{model.start_id}")
        )

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_create_servername_in_headers(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        servername = "12345"
        r = self.client.post(
            url,
            headers={"uuidcode": servername},
            data=self.simple_request_data,
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["servername"], servername)
        service_model = ServicesModel.objects.first()
        self.assertEqual(service_model.servername, servername)

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_get_service(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.get(service_url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["running"])

    @mock.patch(
        target="services.utils.k8s.client.AppsV1Api",
        side_effect=k8s_client_AppsV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_delete_service(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        k8s_apps,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.delete(service_url)
        self.assertEqual(r.status_code, 204)

    @mock.patch(
        target="services.utils.k8s.client.AppsV1Api",
        side_effect=k8s_client_AppsV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_delete_service_service_model_removed(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        k8s_apps,
    ):
        url = reverse("services-list")
        pre_models = ServicesModel.objects.all()
        self.assertEqual(len(pre_models), 0)
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        models = ServicesModel.objects.all()
        self.assertEqual(len(models), 1)
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.delete(service_url)
        self.assertEqual(r.status_code, 204)
        post_models = ServicesModel.objects.all()
        self.assertEqual(len(post_models), 0)

    @mock.patch(
        target="services.utils.k8s.client.AppsV1Api",
        side_effect=k8s_client_AppsV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_delete_service_user_model_not_removed(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        k8s_apps,
    ):
        url = reverse("services-list")
        pre_models = UserModel.objects.all()
        self.assertEqual(len(pre_models), 0)
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        models = UserModel.objects.all()
        self.assertEqual(len(models), 1)
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.delete(service_url)
        self.assertEqual(r.status_code, 204)
        post_models = UserModel.objects.all()
        self.assertEqual(len(post_models), 1)

    @mock.patch(
        target="services.utils.k8s.client.AppsV1Api",
        side_effect=k8s_client_AppsV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_delete_service_userhome_still_exists(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        k8s_apps,
    ):
        url = reverse("services-list")
        self.assertFalse(os.path.isdir(f"{userhomes_base}/authorized_17"))
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(os.path.isdir(f"{userhomes_base}/authorized_17"))
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.delete(service_url)
        self.assertEqual(r.status_code, 204)
        self.assertTrue(os.path.isdir(f"{userhomes_base}/authorized_17"))

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_show_data_user_specific(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        self.client.post(url, data=self.simple_request_data, format="json")
        rg1 = self.client.get(url, format="json")
        self.assertEqual(len(rg1.data), 1)

        self.client.credentials(**self.credentials_authorized_2)
        rg2 = self.client.get(url, format="json")
        self.assertEqual(len(rg2.data), 0)

    @mock.patch(
        target="services.utils.k8s.k8s_utils.create_from_yaml",
        side_effect=k8s_utils_create_from_yaml,
    )
    @mock.patch(
        target="services.utils.k8s.client.V1Secret",
        side_effect=k8s_V1Secret,
    )
    @mock.patch(
        target="services.utils.k8s.client.ApiClient",
        side_effect=k8s_ApiClient,
    )
    @mock.patch(
        target="services.utils.k8s.client.CoreV1Api",
        side_effect=k8s_client_CoreV1Api,
    )
    @mock.patch(
        target="services.utils.k8s.config.load_incluster_config",
        side_effect=k8s_config_load_incluster_config,
    )
    @mock.patch(target="services.utils.common._config", side_effect=config_mock)
    def test_cannot_delete_other_services(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
    ):
        url = reverse("services-list")
        self.client.post(url, data=self.simple_request_data, format="json")
        rg1 = self.client.get(url, format="json")
        self.assertEqual(len(rg1.data), 1)

        self.client.credentials(**self.credentials_authorized_2)
        rd2 = self.client.delete(f"{url}{rg1.data[0]['servername']}/", format="json")
        self.assertEqual(rd2.status_code, 404)

        self.client.credentials(**self.credentials_authorized)
        rd1 = self.client.delete(f"{url}{rg1.data[0]['servername']}/", format="json")
        self.assertEqual(rd1.status_code, 204)
