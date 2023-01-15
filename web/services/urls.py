from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ServicesViewSet
from .views import UserJobsViewSet

router = DefaultRouter()
router.register("services", ServicesViewSet, basename="services")
router.register("userjobs", UserJobsViewSet, basename="userjobs")

urlpatterns = [path("", include(router.urls))]
