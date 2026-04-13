from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"organizations", views.OrganizationViewSet, basename="organization")
router.register(r"tokens", views.APITokenViewSet, basename="apitoken")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/register/", views.SelfRegistrationView.as_view(), name="register"),
    path("auth/password-reset/", views.PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path("login-history/", views.login_history_view, name="login-history"),
    path("debug/user-info/", views.debug_user_info, name="debug-user-info"),
]

legacy_urlpatterns = [
    path("users", views.legacy_user_api, name="legacy-users"),
]
