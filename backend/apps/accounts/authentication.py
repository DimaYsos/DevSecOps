from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import APIToken

class APITokenAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        token = request.META.get("HTTP_X_API_TOKEN")
        if not token:
            auth = request.META.get("HTTP_AUTHORIZATION", "")
            if auth.startswith("Token "):
                token = auth[6:].strip()

        if not token:
            return None

        try:
            api_token = APIToken.objects.select_related("user").get(
                token=token, is_active=True
            )
        except APIToken.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API token.")

        if api_token.expires_at and api_token.expires_at < timezone.now():
            raise exceptions.AuthenticationFailed("Token expired.")

        api_token.last_used = timezone.now()
        api_token.save(update_fields=["last_used"])

        return (api_token.user, api_token)
