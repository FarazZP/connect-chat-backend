from django.urls import path

from .views import MarkAsReadView, NotificationListView

urlpatterns = [
    path("", NotificationListView.as_view()),
    path("read/<int:notification_id>/", MarkAsReadView.as_view()),
]
