import logging

from jupyterjsc_k8smgr.decorators import request_decorator
from jupyterjsc_k8smgr.permissions import HasGroupPermission
from jupyterjsc_k8smgr.settings import LOGGER_NAME
from rest_framework import mixins
from rest_framework import viewsets

from .models import ServicesModel
from .serializers import ServicesSerializer
from .utils import get_custom_headers
from .utils.common import initial_data_to_logs_extra
from .utils.common import instance_dict_and_custom_headers_to_logs_extra
from .utils.common import start_service
from .utils.common import stop_service

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class ServicesViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ServicesSerializer
    lookup_field = "servername"

    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice"]

    def get_queryset(self):
        queryset = ServicesModel.objects.filter(jhub_credential=self.request.user)
        return queryset

    def perform_create(self, serializer):
        custom_headers = get_custom_headers(self.request._request.META)
        logs_extra = initial_data_to_logs_extra(
            serializer.validated_data["servername"],
            serializer.initial_data,
            custom_headers,
        )
        start_service(
            serializer.validated_data,
            serializer.initial_data,
            custom_headers,
            self.request.user.username,
            logs_extra,
        )
        serializer.save()

    def perform_destroy(self, instance):
        custom_headers = get_custom_headers(self.request._request.META)
        logs_extra = instance_dict_and_custom_headers_to_logs_extra(
            instance.__dict__, custom_headers
        )
        if instance.stop_pending:
            log.info("Service is already stopping. Do nothing.", extra=logs_extra)
            return
        try:
            instance.stop_pending = True
            instance.save()
            stop_service(instance.__dict__, custom_headers, logs_extra)
        except Exception as e:
            log.critical(
                "Could not stop service.", extra=instance.__dict__, exc_info=True
            )
        return super().perform_destroy(instance)

    def get_object(self):
        try:
            return super().get_object()
        except ServicesModel.MultipleObjectsReturned:
            log.warning("Multiple Objects found. Keep only latest one")
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            lookup_kwargs = {lookup_url_kwarg: self.kwargs[lookup_url_kwarg]}
            models = self.get_queryset().filter(**lookup_kwargs).all()
            ids = [x.id for x in models]
            keep_id = max(ids)
            for model in models:
                if not model.id == keep_id:
                    self.perform_destroy(model)
            return super().get_object()

    @request_decorator
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @request_decorator
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @request_decorator
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @request_decorator
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
