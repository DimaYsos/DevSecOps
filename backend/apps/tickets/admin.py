from django.contrib import admin
from .models import Ticket, Incident, Comment, Attachment
admin.site.register(Ticket)
admin.site.register(Incident)
admin.site.register(Comment)
admin.site.register(Attachment)
