from rest_framework.test import APITestCase
from services.models import ServicesModel
from services.models import UserJobsModel


class ModelsTests(APITestCase):
    def test_create_model(self):
        data = {"jhub_user_id": 5}
        ServicesModel(**data).save()
        a = ServicesModel.objects.all()
        self.assertEqual(len(a), 1)

    def test_delete_model(self):
        ServicesModel(jhub_user_id=123).save()
        a = ServicesModel.objects.all()
        self.assertEqual(len(a), 1)
        a[0].delete()
        a = ServicesModel.objects.all()
        self.assertEqual(len(a), 0)

    def test_create_userjobs_model(self):
        data = {"jhub_user_id": 5}
        ServicesModel(**data).save()
        a = ServicesModel.objects.all()
        data_uj = {
            "service": a.first(),
            "used_ports": ["5678"],
            "hostname": "host",
            "target_node": "target",
        }
        UserJobsModel(**data_uj).save()
        b = UserJobsModel.objects.all()
        self.assertEqual(len(b), 1)

    def test_delete_userjobs_model(self):
        data = {"jhub_user_id": 5}
        ServicesModel(**data).save()
        a = ServicesModel.objects.all()
        data_uj = {
            "service": a.first(),
            "used_ports": ["5678"],
            "hostname": "host",
            "target_node": "target",
        }
        UserJobsModel(**data_uj).save()
        b = UserJobsModel.objects.all()
        self.assertEqual(len(b), 1)
        b[0].delete()
        b = UserJobsModel.objects.all()
        self.assertEqual(len(b), 0)
