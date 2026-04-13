from django.urls import path
from . import views

urlpatterns = [
    path("enrichment/user/", views.enrich_user, name="enrich-user"),
    path("enrichment/asset/", views.enrich_asset, name="enrich-asset"),
    path("enrichment/address/", views.lookup_address, name="lookup-address"),
]
