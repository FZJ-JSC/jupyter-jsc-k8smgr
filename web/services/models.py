from django.db import models


class ServicesModel(models.Model):
    servername = models.TextField("servername")
    start_id = models.TextField("start_id")
    start_date = models.DateTimeField(auto_now_add=True)
    user_options = models.JSONField("user_options", default=dict)
    jhub_user_id = models.IntegerField("jhub_user_id", null=False)
    jhub_credential = models.TextField("jhub_credential", default="jupyterhub")
    stop_pending = models.BooleanField(null=False, default=False)


class UserModel(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True)
    jhub_user_id = models.IntegerField("jhub_user_id", null=False)
    jhub_credential = models.TextField("jhub_credential", default="jupyterhub")


class UserJobsModel(models.Model):
    service = models.TextField("userjobs", null=False)
    used_ports = models.JSONField("used_ports", null=False, default=dict)
    jhub_credential = models.TextField("jhub_credential", default="jupyterhub")
    hostname = models.TextField("hostname", null=False)
    target_node = models.TextField("target_node", null=False)
