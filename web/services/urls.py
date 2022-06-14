from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ServicesViewSet

router = DefaultRouter()
router.register("services", ServicesViewSet, basename="services")

urlpatterns = [path("", include(router.urls))]
