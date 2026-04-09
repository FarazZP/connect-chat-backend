from django.urls import path
from .views import SendMessageView, ConversationView, DeleteMessageView, EditMessageView

urlpatterns = [
    path('send/<int:user_id>/', SendMessageView.as_view(), name='send-message'),
    path('conversation/<int:user_id>/', ConversationView.as_view(), name='conversation'),
    path('delete/<int:message_id>/', DeleteMessageView.as_view(), name='delete-message'),
    path('edit/<int:message_id>/', EditMessageView.as_view(), name='edit-message'),
]