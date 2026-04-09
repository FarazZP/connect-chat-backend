from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Message
from .serializers import MessageSerializer
from django.shortcuts import get_object_or_404

User = get_user_model()


class SendMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        receiver = get_object_or_404(User, id=user_id)

        message = Message.objects.create(
            sender=request.user,
            receiver=receiver,
            message=request.data.get('message', '')
        )

        serializer = MessageSerializer(message)
        return Response(serializer.data)


class ConversationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        other_user = get_object_or_404(User, id=user_id)

        messages = Message.objects.filter(
            Q(sender=request.user, receiver=other_user) |
            Q(sender=other_user, receiver=request.user)
        ).order_by('created_at')

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class DeleteMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, message_id):
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        message.delete()
        return Response({"message": "Message deleted"})


class EditMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, message_id):
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        message.message = request.data.get('message')
        message.save()

        serializer = MessageSerializer(message)
        return Response(serializer.data)