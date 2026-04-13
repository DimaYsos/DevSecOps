import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from django.db import models
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from vulnops.access import is_org_admin, is_sys_admin, scope_queryset

from .models import Organization, User, APIToken, PasswordResetToken, LoginHistory
from .serializers import (
    OrganizationSerializer, UserSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserPublicSerializer, LegacyUserSerializer,
    APITokenSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, LoginSerializer, ChangePasswordSerializer,
    LoginHistorySerializer,
)

logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFCookieView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"message": "CSRF cookie set"})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        user = authenticate(request, username=username, password=password)
        LoginHistory.objects.create(
            user=user if user and user.is_active else None,
            username_attempted=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=bool(user and user.is_active),
        )

        if user is None or not user.is_active:
            User.objects.filter(username=username).update(failed_login_count=models.F("failed_login_count") + 1)
            return Response({"error": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)

        if request.user.is_authenticated:
            logout(request)

        login(request, user)
        request.session.cycle_key()
        user.last_login_ip = ip_address
        user.failed_login_count = 0
        user.save(update_fields=["last_login_ip", "failed_login_count"])

        return Response({
            "message": "Login successful",
            "user": UserSerializer(user, context={"request": request}).data,
            "session_id": request.session.session_key,
        })


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        response = Response({"message": "Logged out successfully"})
        response.delete_cookie(
            settings.SESSION_COOKIE_NAME,
            path="/",
            samesite=settings.SESSION_COOKIE_SAMESITE,
            secure=settings.SESSION_COOKIE_SECURE,
        )
        return response


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
            token = PasswordResetToken(user=user)
            token.save()
            # Placeholder for mail delivery integration.
            if settings.DEBUG:
                return Response({
                    "message": "If the account exists, a reset token has been issued.",
                    "debug_token": token.token,
                })

        return Response({"message": "If the account exists, a reset token has been issued."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        token_value = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(email=email, is_active=True).first()
        token = None
        if user:
            token = PasswordResetToken.objects.filter(
                user=user, token=token_value, is_used=False,
            ).order_by("-created_at").first()

        if token and token.is_valid:
            user.set_password(new_password)
            user.save(update_fields=["password"])
            token.is_used = True
            token.save(update_fields=["is_used"])
            return Response({"message": "Password reset successful"})
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response({"error": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"message": "Password changed successfully"})


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.action == "create" and not is_org_admin(request.user):
            raise PermissionDenied("Only administrators can create users from this endpoint.")

    def get_queryset(self):
        qs = User.objects.select_related("organization")
        if is_sys_admin(self.request.user):
            return qs
        if is_org_admin(self.request.user):
            return qs.filter(organization_id=self.request.user.organization_id)
        return qs.filter(id=self.request.user.id)

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action in ("list", "retrieve"):
            return UserPublicSerializer
        return UserSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_destroy(self, instance):
        if not (is_sys_admin(self.request.user) or (is_org_admin(self.request.user) and instance.organization_id == self.request.user.organization_id)):
            raise PermissionDenied("You cannot delete this user.")
        instance.delete()

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def promote(self, request, pk=None):
        if not is_org_admin(request.user):
            raise PermissionDenied("Only administrators can change roles.")
        user = self.get_object()
        new_role = request.data.get("role", "user")
        allowed_roles = {"user", "agent", "org_admin", "service_account"}
        if is_sys_admin(request.user):
            allowed_roles.add("sys_admin")
        if new_role not in allowed_roles:
            return Response({"error": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
        if not is_sys_admin(request.user) and user.organization_id != request.user.organization_id:
            raise PermissionDenied("You cannot manage users outside your organization.")
        user.role = new_role
        user.is_staff = new_role == "sys_admin"
        user.save(update_fields=["role", "is_staff"])
        return Response(UserPublicSerializer(user).data)


class SelfRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserPublicSerializer(user).data, status=status.HTTP_201_CREATED)


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Organization.objects.all()
        if is_sys_admin(self.request.user):
            return qs
        if self.request.user.organization_id:
            return qs.filter(id=self.request.user.organization_id)
        return qs.none()

    def perform_create(self, serializer):
        if not is_sys_admin(self.request.user):
            raise PermissionDenied("Only system administrators can create organizations.")
        serializer.save()

    def perform_update(self, serializer):
        if not is_org_admin(self.request.user):
            raise PermissionDenied("Only administrators can update organization details.")
        if not is_sys_admin(self.request.user) and self.get_object().id != self.request.user.organization_id:
            raise PermissionDenied("You cannot update another organization.")
        serializer.save()

    def perform_destroy(self, instance):
        if not is_sys_admin(self.request.user):
            raise PermissionDenied("Only system administrators can delete organizations.")
        instance.delete()


class APITokenViewSet(viewsets.ModelViewSet):
    serializer_class = APITokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return APIToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_org_admin(request.user):
            raise PermissionDenied("Administrative access required.")
        if is_sys_admin(request.user):
            qs = User.objects.select_related("organization").all()
        else:
            qs = User.objects.select_related("organization").filter(organization_id=request.user.organization_id)
        return Response(UserPublicSerializer(qs[:100], many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def login_history_view(request):
    requested_user_id = request.GET.get("user_id")
    if requested_user_id and requested_user_id != str(request.user.id) and not is_org_admin(request.user):
        raise PermissionDenied("You cannot view another user's login history.")
    user_id = requested_user_id or request.user.id
    history = LoginHistory.objects.filter(user_id=user_id).order_by("-created_at")[:50]
    if not is_sys_admin(request.user):
        history = history.filter(Q(user__organization_id=request.user.organization_id) | Q(user=request.user))
    return Response(LoginHistorySerializer(history, many=True).data)


@api_view(["GET", "POST", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def legacy_user_api(request):
    if not is_org_admin(request.user):
        raise PermissionDenied("Administrative access required.")

    if request.method == "GET":
        user_id = request.GET.get("id")
        qs = User.objects.select_related("organization")
        if not is_sys_admin(request.user):
            qs = qs.filter(organization_id=request.user.organization_id)
        if user_id:
            user = qs.filter(id=user_id).first()
            if not user:
                return Response({"error": "Not found"}, status=404)
            return Response(LegacyUserSerializer(user).data)
        return Response(LegacyUserSerializer(qs[:100], many=True).data)

    if request.method == "POST":
        serializer = UserCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(LegacyUserSerializer(user).data, status=201)

    user_id = request.data.get("id") or request.GET.get("id")
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"error": "Not found"}, status=404)
    if not is_sys_admin(request.user) and user.organization_id != request.user.organization_id:
        raise PermissionDenied("You cannot manage this user.")

    if request.method == "PUT":
        serializer = UserUpdateSerializer(user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LegacyUserSerializer(user).data)

    user.delete()
    return Response({"message": "Deleted"})
