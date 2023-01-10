import logging
import uuid

from django.urls.base import reverse
from jupyterjsc_k8smgr.settings import LOGGER_NAME
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import ServicesModel
from .models import UserJobsModel
from .utils import get_custom_headers
from .utils.common import instance_dict_and_custom_headers_to_logs_extra
from .utils.common import status_service

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicesModel
        fields = [
            "servername",
            "start_id",
            "user_options",
            "jhub_user_id",
            "jhub_credential",
            "start_date",
            "stop_pending",
        ]

    def check_input_keys(self):
        required_keys = {
            "env": [
                "JUPYTERHUB_STATUS_URL",
                "JUPYTERHUB_API_TOKEN",
                "JUPYTERHUB_USER_ID",
            ],
            "user_options": ["service"],
            "start_id": [],
        }
        for key, values in required_keys.items():
            if key not in self.initial_data.keys():
                self._validated_data = []
                self._errors = [f"Missing key in input data: {key}"]
                raise ValidationError(self._errors)
            for value in values:
                if value not in self.initial_data[key].keys():
                    self._validated_data = []
                    self._errors = [f"Missing key in input data: {key}.{value}"]
                    raise ValidationError(self._errors)

    def is_valid(self, raise_exception=False):
        try:
            self.check_input_keys()
        except ValidationError as exc:
            _errors = exc.detail
        else:
            _errors = {}
        if _errors and raise_exception:
            raise ValidationError(_errors)
        return super().is_valid(raise_exception=raise_exception)

    def to_internal_value(self, data):
        custom_headers = get_custom_headers(self.context["request"]._request.META)
        servername = custom_headers.get("uuidcode", uuid.uuid4().hex)
        model_data = {
            "servername": servername,
            "start_id": data["start_id"],
            "user_options": data["user_options"],
            "jhub_user_id": data["env"]["JUPYTERHUB_USER_ID"],
            "jhub_credential": self.context["request"].user.username,
            "stop_pending": False,
        }
        if "vo" not in model_data["user_options"].keys():
            model_data["user_options"]["vo"] = "default"
        else:
            model_data["user_options"]["vo"] = (
                model_data["user_options"]["vo"]
                .lower()
                .replace(" ", "-")
                .replace("_", "-")
            )
        return super().to_internal_value(model_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # For create or list we don't want to update status
        if self.context["request"].path == reverse("services-list"):
            return ret
        custom_headers = get_custom_headers(self.context["request"]._request.META)
        logs_extra = instance_dict_and_custom_headers_to_logs_extra(
            instance.__dict__, custom_headers
        )
        logs_extra["start_date"] = ret["start_date"]
        if instance.stop_pending:
            log.info("Service is already stopping. Return false", extra=logs_extra)
            status = {"running": False}
        else:
            try:
                status = status_service(
                    instance.__dict__,
                    custom_headers,
                    logs_extra=logs_extra,
                )
            except Exception as e:
                if len(e.args) >= 2 and e.args[1].startswith(
                    "No pod found with app label"
                ):
                    log.warning("Pod does not exist", extra=logs_extra, exc_info=True)
                    status = {
                        "running": False,
                        "details": {"error": e.args[0], "detailed_error": e.args[1]},
                    }
                else:
                    log.critical(
                        "Could not check status of service",
                        extra=logs_extra,
                        exc_info=True,
                    )
                    status = {
                        "running": True,
                        "details": {"error": e.args[0], "detailed_error": e.args[1]},
                    }
        if not status:
            status = {"running": True}
        ret.update(status)
        return ret


class UserJobsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserJobsModel
        fields = ["userjobs", "service", "suffix", "hostname", "target_node"]

    required_keys = ["service", "ports", "suffix", "hostname", "target_node"]

    def to_internal_value(self, data):
        jhub_credential = self.context["request"].user.username
        service_name = data["service"]
        services = (
            ServicesModel.objects.filter(jhub_credential=jhub_credential)
            .filter(servername=service_name)
            .all()
        )
        data["service"] = services.first().pk
        data["userjobs"] = f"{service_name}-{data['suffix']}"
        ret = super().to_internal_value(data)
        ret["jhub_credential"] = jhub_credential
        return ret

    def is_valid(self, raise_exception=False):
        try:
            for key in self.required_keys:
                if key not in self.initial_data.keys():
                    self._validated_data = {}
                    self._errors = [f"Missing key in input data: {key}"]
                    raise ValidationError(f"Missing key: {key}")

            jhub_credential = self.context["request"].user.username
            service_name = self.initial_data["service"]
            services = (
                ServicesModel.objects.filter(jhub_credential=jhub_credential)
                .filter(servername=service_name)
                .all()
            )
            if len(services) == 0:
                self._validated_data = []
                self._errors = [
                    f"Service {service_name} unknown for {jhub_credential}."
                ]
                raise ValidationError(self._errors)

        except ValidationError as exc:
            _errors = exc.detail
        else:
            _errors = {}
        if _errors and raise_exception:
            raise ValidationError(_errors)
        return super().is_valid(raise_exception=raise_exception)
