from django.urls import path
from . import views

urlpatterns = [
    path("", views.legacy_user_api, name="legacy-users"),
]
