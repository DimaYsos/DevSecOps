import jwt
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, User, APIToken, PasswordResetToken, LoginHistory
from .serializers import (
    OrganizationSerializer, UserSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserPublicSerializer, LegacyUserSerializer,
    APITokenSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, LoginSerializer, ChangePasswordSerializer,
    LoginHistorySerializer,
)

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            user.last_login_ip = request.META.get("REMOTE_ADDR")
            user.failed_login_count = 0
            user.save(update_fields=["last_login_ip", "failed_login_count"])

            return Response({
                "message": "Login successful",
                "user": UserSerializer(user).data,
                "session_id": request.session.session_key,
            })
        else:
            try:
                existing = User.objects.get(username=username)
                existing.failed_login_count += 1
                existing.save(update_fields=["failed_login_count"])
                return Response(
                    {"error": "Invalid password for this account."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "No account found with this username."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Logged out successfully"})

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            token = PasswordResetToken(user=user)
            token.save()

            return Response({
                "message": f"Reset token sent to {email}",
                "debug_token": token.token,
                "expires_at": token.expires_at.isoformat(),
            })
        except User.DoesNotExist:
            return Response(
                {"error": "No account found with this email address."},
                status=status.HTTP_404_NOT_FOUND,
            )

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        token_value = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)
            token = PasswordResetToken.objects.filter(
                user=user, token=token_value, is_used=False,
            ).order_by("-created_at").first()

            if token and token.is_valid:
                user.set_password(new_password)
                user.save()
                token.is_used = True
                token.save()
                return Response({"message": "Password reset successful"})
            else:
                return Response(
                    {"error": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"error": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"message": "Password changed successfully"})

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.all().select_related("organization")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=True, methods=["post"])
    def promote(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get("role", "org_admin")
        user.role = new_role
        user.save(update_fields=["role"])
        return Response(UserSerializer(user).data)

class SelfRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )

class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Organization.objects.all()

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
        users = User.objects.all()
        serializer = LegacyUserSerializer(users, many=True)
        return Response(serializer.data)

@api_view(["GET"])
@permission_classes([AllowAny])
def debug_user_info(request):
    user_id = request.GET.get("user_id")
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            return Response(LegacyUserSerializer(user).data)
        except User.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

    return Response({
        "total_users": User.objects.count(),
        "total_orgs": Organization.objects.count(),
        "active_tokens": APIToken.objects.filter(is_active=True).count(),
        "settings": {
            "secret_key_prefix": settings.SECRET_KEY[:20],
            "debug": settings.DEBUG,
            "database_host": settings.DATABASES["default"]["HOST"],
            "jwt_secret": settings.JWT_SECRET,
        },
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def login_history_view(request):
    user_id = request.GET.get("user_id", request.user.id)
    history = LoginHistory.objects.filter(user_id=user_id)[:50]
    return Response(LoginHistorySerializer(history, many=True).data)

@api_view(["GET", "POST", "PUT", "DELETE"])
@permission_classes([AllowAny])
def legacy_user_api(request):
    if request.method == "GET":
        user_id = request.GET.get("id")
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                return Response(LegacyUserSerializer(user).data)
            except User.DoesNotExist:
                return Response({"error": "Not found"}, status=404)
        users = User.objects.all()[:100]
        return Response(LegacyUserSerializer(users, many=True).data)

    elif request.method == "POST":
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(LegacyUserSerializer(user).data, status=201)
        return Response(serializer.errors, status=400)

    elif request.method == "PUT":
        user_id = request.data.get("id") or request.GET.get("id")
        try:
            user = User.objects.get(id=user_id)
            for key, value in request.data.items():
                if key != "id" and hasattr(user, key):
                    setattr(user, key, value)
            user.save()
            return Response(LegacyUserSerializer(user).data)
        except User.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

    elif request.method == "DELETE":
        user_id = request.data.get("id") or request.GET.get("id")
        try:
            User.objects.get(id=user_id).delete()
            return Response({"message": "Deleted"})
        except User.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
