import os
import shutil
from unittest import mock

from django.http.response import HttpResponse
from django.urls.base import reverse
from services.models import ServicesModel
from services.models import UserJobsModel
from services.models import UserModel
from tests.mocks import config_mock
from tests.mocks import config_mock_services_mapping
from tests.mocks import config_mock_userhome_mapping
from tests.mocks import k8s_ApiClient
from tests.mocks import k8s_client_AppsV1Api
from tests.mocks import k8s_client_CoreV1Api
from tests.mocks import k8s_config_load_incluster_config
from tests.mocks import k8s_utils_create_from_yaml
from tests.mocks import k8s_V1Secret
from tests.mocks import mocked_exception
from tests.mocks import mocked_popen_init
from tests.mocks import mocked_popen_init_all_fail
from tests.mocks import mocked_popen_init_cancel_fail
from tests.mocks import mocked_popen_init_check_fail
from tests.mocks import mocked_popen_init_forward_fail
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

    simple_userjobs_data = {
        "ports": {
            "8080": "59998",
            "8081": "59999",
        },
        "service": "abc",
        "hostname": "jwlogin01i",
        "target_node": "jwc0050",
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
    @mock.patch(
        target="services.utils.common._config", side_effect=config_mock_services_mapping
    )
    def test_create_mapped_credential(
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
        with open(
            f"{services_base}/{r.data['servername']}-{r.data['start_id']}/service.yaml"
        ) as f:
            service_yaml = f.read()
        first_line = service_yaml.split("\n")[0]
        self.assertEqual(first_line, "# Mapped version")

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
    def test_create_unmapped_credential(
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
        with open(
            f"{services_base}/{r.data['servername']}-{r.data['start_id']}/service.yaml"
        ) as f:
            service_yaml = f.read()
        first_line = service_yaml.split("\n")[0]
        self.assertNotEqual(first_line, "# Mapped version")

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
        self.assertTrue(os.path.isdir(f"{userhomes_base}/authorized/17"))

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
    @mock.patch(
        target="services.utils.common._config", side_effect=config_mock_userhome_mapping
    )
    def test_create_userhome_mapping_created(
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
        self.assertTrue(os.path.isdir(f"{userhomes_base}/mapped_suffix/17"))

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
        self.assertFalse(os.path.isdir(f"{userhomes_base}/authorized/17"))
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(os.path.isdir(f"{userhomes_base}/authorized/17"))
        service_url = f"{url}{r.data['servername']}/"
        r = self.client.delete(service_url)
        self.assertEqual(r.status_code, 204)
        self.assertTrue(os.path.isdir(f"{userhomes_base}/authorized/17"))

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
    @mock.patch.dict(os.environ, {"STAGE": "stage1"})
    def test_skip_stage_specific_files(
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
        servername = r.data["servername"]
        start_id = r.data["start_id"]
        with open(
            f"web/tests/files/services/{servername}-{start_id}/service.yaml", "r"
        ) as f:
            service_yaml = f.read()
        b64_decoded = [
            x.split(": ")[1] for x in service_yaml.split("\n") if "input.tar.gz:" in x
        ][0]
        import base64

        with open(
            f"web/tests/files/services/{servername}-{start_id}/input.tar.gz", "wb"
        ) as f:
            f.write(base64.b64decode(b64_decoded))
        import tarfile

        with tarfile.open(
            f"web/tests/files/services/{servername}-{start_id}/input.tar.gz", "r:gz"
        ) as tar:
            tar.extractall(path=f"web/tests/files/services/{servername}-{start_id}")
        list_dir = os.listdir(f"web/tests/files/services/{servername}-{start_id}/input")
        self.assertTrue("stage1_file.txt" not in list_dir)
        self.assertTrue("stage2_file.txt" not in list_dir)
        self.assertTrue("file.txt" in list_dir)
        with open(
            f"web/tests/files/services/{servername}-{start_id}/input/file.txt", "r"
        ) as f:
            self.assertEqual("stage1", f.read().strip())

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
    @mock.patch.dict(os.environ, {"STAGE": "stage1"})
    def test_skip_credential_specific_files(
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
        servername = r.data["servername"]
        start_id = r.data["start_id"]
        with open(
            f"web/tests/files/services/{servername}-{start_id}/service.yaml", "r"
        ) as f:
            service_yaml = f.read()
        b64_decoded = [
            x.split(": ")[1] for x in service_yaml.split("\n") if "input.tar.gz:" in x
        ][0]
        import base64

        with open(
            f"web/tests/files/services/{servername}-{start_id}/input.tar.gz", "wb"
        ) as f:
            f.write(base64.b64decode(b64_decoded))
        import tarfile

        with tarfile.open(
            f"web/tests/files/services/{servername}-{start_id}/input.tar.gz", "r:gz"
        ) as tar:
            tar.extractall(path=f"web/tests/files/services/{servername}-{start_id}")
        list_dir = os.listdir(
            f"web/tests/files/services/{servername}-{start_id}/input/custom"
        )
        self.assertTrue("authorized_cred.txt" not in list_dir)
        self.assertTrue("authorized2_cred.txt" not in list_dir)
        self.assertTrue("cred.txt" in list_dir)
        with open(
            f"web/tests/files/services/{servername}-{start_id}/input/custom/cred.txt",
            "r",
        ) as f:
            self.assertEqual("authorized", f.read().strip())

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
    @mock.patch.dict(os.environ, {"STAGE": "stage2"})
    def test_replace_stage_specific(
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
        servername = r.data["servername"]
        start_id = r.data["start_id"]
        with open(
            f"web/tests/files/services/{servername}-{start_id}/service.yaml", "r"
        ) as f:
            service_yaml = f.read()
        stage_specific_value = [
            x.split(": ")[1] for x in service_yaml.split("\n") if "stagespecific:" in x
        ][0]
        self.assertEqual(stage_specific_value, "stage2")

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
    @mock.patch.dict(os.environ, {"STAGE": "stage2"})
    def test_replace_credential_specific(
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
        servername = r.data["servername"]
        start_id = r.data["start_id"]
        with open(
            f"web/tests/files/services/{servername}-{start_id}/service.yaml", "r"
        ) as f:
            service_yaml = f.read()
        cred_specific_value = [
            x.split(": ")[1]
            for x in service_yaml.split("\n")
            if "credential-stuff:" in x
        ][0]
        self.assertEqual(cred_specific_value, "auth")

    @mock.patch(
        "services.utils.ssh.subprocess.Popen",
        side_effect=mocked_popen_init,
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
    def test_userjobs_create(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        mocked_popen,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

        data = self.simple_userjobs_data
        data["service"] = r.data["servername"]
        url = reverse("userjobs-list")
        r = self.client.post(url, data=self.simple_userjobs_data, format="json")
        self.assertEqual(r.status_code, 201)

    @mock.patch(
        "services.utils.ssh.subprocess.Popen",
        side_effect=mocked_popen_init,
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
    def test_userjobs_delete(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        mocked_popen,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

        data = self.simple_userjobs_data
        data["service"] = r.data["servername"]
        url = reverse("userjobs-list")
        r = self.client.post(url, data=self.simple_userjobs_data, format="json")
        self.assertEqual(r.status_code, 201)
        url = f"{url}{self.simple_userjobs_data['service']}/"
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 204)

    @mock.patch(
        "services.utils.ssh.subprocess.Popen",
        side_effect=mocked_popen_init,
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
    def test_userjobs_cascade_delete(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        mocked_popen,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

        data = self.simple_userjobs_data
        data["service"] = r.data["servername"]
        url = reverse("userjobs-list")
        r = self.client.post(url, data=self.simple_userjobs_data, format="json")
        self.assertEqual(r.status_code, 201)

        url = reverse("services-list")
        url = f"{url}{self.simple_userjobs_data['service']}/"
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 204)

        url = reverse("userjobs-list")
        url = f"{url}{self.simple_userjobs_data['service']}/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 404)

    @mock.patch(
        "services.utils.ssh.subprocess.Popen",
        side_effect=mocked_popen_init,
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
    def test_userjobs_get(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        mocked_popen,
    ):
        url = reverse("services-list")
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

        data = self.simple_userjobs_data
        data["service"] = r.data["servername"]
        url = reverse("userjobs-list")
        r = self.client.post(url, data=self.simple_userjobs_data, format="json")
        self.assertEqual(r.status_code, 201)

        url = f"{url}{self.simple_userjobs_data['service']}/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)

    @mock.patch(
        "services.utils.ssh.subprocess.Popen",
        side_effect=mocked_popen_init,
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
    def test_userjobs_create_model_created(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        mocked_popen,
    ):
        url = reverse("services-list")
        pre_models = UserJobsModel.objects.all()
        self.assertEqual(len(pre_models), 0)
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

        data = self.simple_userjobs_data
        data["service"] = r.data["servername"]
        url = reverse("userjobs-list")
        r = self.client.post(url, data=self.simple_userjobs_data, format="json")

        models = UserJobsModel.objects.all()
        self.assertEqual(len(models), 1)

    @mock.patch(
        "services.utils.ssh.subprocess.Popen",
        side_effect=mocked_popen_init,
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
    def test_userjobs_create_model_deleted(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        mocked_popen,
    ):
        url = reverse("services-list")
        pre_models = UserJobsModel.objects.all()
        self.assertEqual(len(pre_models), 0)
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

        data = self.simple_userjobs_data
        data["service"] = r.data["servername"]
        url = reverse("userjobs-list")
        r = self.client.post(url, data=self.simple_userjobs_data, format="json")

        models = UserJobsModel.objects.all()
        self.assertEqual(len(models), 1)

        url = f"{url}{self.simple_userjobs_data['service']}/"
        r = self.client.delete(url, format="json")
        models = UserJobsModel.objects.all()
        self.assertEqual(len(models), 0)

    @mock.patch(
        "services.utils.ssh.subprocess.Popen",
        side_effect=mocked_popen_init,
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
    def test_userjobs_create_model_cascade_deleted(
        self,
        config_mocked,
        k8s_config,
        k8s_client,
        k8s_api_client,
        k8s_secret,
        k8s_create_from_yaml,
        mocked_popen,
    ):
        url = reverse("services-list")
        pre_models = UserJobsModel.objects.all()
        self.assertEqual(len(pre_models), 0)
        r = self.client.post(url, data=self.simple_request_data, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["servername"]), 32)

        data = self.simple_userjobs_data
        data["service"] = r.data["servername"]
        url = reverse("userjobs-list")
        r = self.client.post(url, data=self.simple_userjobs_data, format="json")

        models = UserJobsModel.objects.all()
        self.assertEqual(len(models), 1)

        url = reverse("services-list")
        url = f"{url}{self.simple_userjobs_data['service']}/"
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 204)
        models = UserJobsModel.objects.all()
        self.assertEqual(len(models), 0)
