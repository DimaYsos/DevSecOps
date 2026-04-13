from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"tickets", views.TicketViewSet, basename="ticket")
router.register(r"incidents", views.IncidentViewSet, basename="incident")
router.register(r"comments", views.CommentViewSet, basename="comment")
router.register(r"attachments", views.AttachmentViewSet, basename="attachment")

urlpatterns = [
    path("", include(router.urls)),
    path("attachments/<uuid:attachment_id>/download/", views.download_attachment, name="attachment-download"),
    path("search/advanced/", views.advanced_search, name="advanced-search"),
    path("tickets/internal/", views.internal_tickets, name="internal-tickets"),
    path("exports/tickets/", views.public_ticket_export, name="public-ticket-export"),
]
