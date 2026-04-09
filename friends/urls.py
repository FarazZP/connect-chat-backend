from django.urls import path
from .views import (
    SendFriendRequestView,
    AcceptFriendRequestView,
    RejectFriendRequestView,
    FriendListView,
    PendingRequestsView
)

urlpatterns = [
    path('send/<int:user_id>/', SendFriendRequestView.as_view()),
    path('accept/<int:request_id>/', AcceptFriendRequestView.as_view()),
    path('reject/<int:request_id>/', RejectFriendRequestView.as_view()),
    path('list/', FriendListView.as_view()),
    path('requests/', PendingRequestsView.as_view()),
]