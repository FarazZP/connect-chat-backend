import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import Message
from asgiref.sync import sync_to_async

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.other_user_id = self.scope["url_route"]["kwargs"]["user_id"]

        # Create unique room name
        self.room_name = f"chat_{min(self.user.id, self.other_user_id)}_{max(self.user.id, self.other_user_id)}"
        self.room_group_name = self.room_name

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")

        # Save message to DB
        saved_message = await self.save_message(message)

        # Send message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender": self.user.email,
                "receiver_id": self.other_user_id,
                "message_id": saved_message.id,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
            "message_id": event["message_id"],
        }))

    @sync_to_async
    def save_message(self, message):
        receiver = User.objects.get(id=self.other_user_id)
        return Message.objects.create(
            sender=self.user,
            receiver=receiver,
            message=message
        )