from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"assets", views.AssetViewSet, basename="asset")
router.register(r"asset-links", views.AssetLinkViewSet, basename="asset-link")

urlpatterns = [
    path("", include(router.urls)),
]
