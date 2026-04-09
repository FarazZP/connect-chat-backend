from rest_framework import serializers
from .models import FriendRequest, Friendship
from django.conf import settings

User = settings.AUTH_USER_MODEL

class FriendRequestSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    receiver_email = serializers.CharField(source='receiver.email', read_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'sender', 'receiver', 'sender_email', 'receiver_email', 'status', 'created_at']

class FriendshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friendship
        fields = '__all__'
