from rest_framework.test import APITestCase
from services.models import ServicesModel


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
