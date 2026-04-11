import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import Q

from friends.models import Friendship
from .models import Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    room_group_name = None

    async def connect(self):
        self.user = self.scope["user"]
        self.other_user_id = self.scope["url_route"]["kwargs"]["user_id"]

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        if self.user.id == self.other_user_id:
            await self.close(code=4002)
            return

        other_exists = await sync_to_async(User.objects.filter(id=self.other_user_id).exists)()
        if not other_exists:
            await self.close(code=4004)
            return

        friends = await self._users_are_friends(self.user.id, self.other_user_id)
        if not friends:
            await self.close(code=4003)
            return

        # Same room for both users; no duplicate chats for the pair
        self.room_group_name = (
            f"chat_{min(self.user.id, self.other_user_id)}_{max(self.user.id, self.other_user_id)}"
        )

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        if not self.user.is_authenticated or not self.room_group_name:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
            return

        message = data.get("message")
        if message is None or (isinstance(message, str) and not message.strip()):
            await self.send(text_data=json.dumps({"error": "message is required"}))
            return

        saved_message = await self.save_message(str(message).strip())

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": saved_message.message,
                "sender": self.user.email,
                "receiver_id": self.other_user_id,
                "message_id": saved_message.id,
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "sender": event["sender"],
                    "message_id": event["message_id"],
                }
            )
        )

    @sync_to_async
    def _users_are_friends(self, user_a_id, user_b_id):
        return Friendship.objects.filter(
            Q(user1_id=user_a_id, user2_id=user_b_id)
            | Q(user1_id=user_b_id, user2_id=user_a_id)
        ).exists()

    @sync_to_async
    def save_message(self, text):
        receiver = User.objects.get(id=self.other_user_id)
        return Message.objects.create(sender=self.user, receiver=receiver, message=text)
