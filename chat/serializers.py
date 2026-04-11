from rest_framework import serializers
from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    receiver_email = serializers.CharField(source='receiver.email', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'message', 'file', 'is_seen', 'receiver_email', 'sender_email', 'created_at']