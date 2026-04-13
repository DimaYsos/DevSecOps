from django.contrib import admin
from .models import Organization, User, APIToken, PasswordResetToken, LoginHistory

admin.site.register(Organization)
admin.site.register(User)
admin.site.register(APIToken)
admin.site.register(PasswordResetToken)
admin.site.register(LoginHistory)
