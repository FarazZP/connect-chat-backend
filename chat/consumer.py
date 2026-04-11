import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from friends.models import Friendship
from notifications.utils import create_notification
from .models import Message

User = get_user_model()


def _set_user_online_status(user_id, online):
    user = User.objects.get(pk=user_id)
    user.is_online = online
    if not online:
        user.last_seen = timezone.now()
    if online:
        user.save(update_fields=["is_online"])
    else:
        user.save(update_fields=["is_online", "last_seen"])


set_user_online_status = sync_to_async(_set_user_online_status)


class ChatConsumer(AsyncWebsocketConsumer):
    room_group_name = None
    user_group = None
    _accepted = False

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
        self.user_group = f"user_{self.user.id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        self._accepted = True

        await set_user_online_status(self.user.id, True)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "presence_event",
                "sender": self.user.email,
                "online": True,
            },
        )

    async def disconnect(self, close_code):
        if self._accepted:
            await set_user_online_status(self.user.id, False)
            if self.room_group_name:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "presence_event",
                        "sender": self.user.email,
                        "online": False,
                    },
                )

        if self.user_group:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
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

        typing = data.get("typing", False)
        if typing:
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "typing_event", "sender": self.user.email},
            )
            return

        seen = data.get("seen", False)
        if seen:
            count = await self.mark_messages_seen()
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "seen_event", "sender": self.user.email},
            )
            if count > 0:
                seen_msg = f"{self.user.email} saw your messages"
                await self.create_message_seen_notification(seen_msg)
                await self.channel_layer.group_send(
                    f"user_{self.other_user_id}",
                    {
                        "type": "notify",
                        "notification_type": "message_seen",
                        "message": seen_msg,
                    },
                )
            return

        message = data.get("message")
        if message is None or (isinstance(message, str) and not message.strip()):
            await self.send(text_data=json.dumps({"error": "message is required"}))
            return

        text = str(message).strip()
        saved_message = await self.save_message(text)
        await self.create_new_message_notification(text)

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

        notif_message = f"{self.user.email}: {saved_message.message}"
        await self.channel_layer.group_send(
            f"user_{self.other_user_id}",
            {
                "type": "notify",
                "notification_type": "new_message",
                "message": notif_message,
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message": event["message"],
                    "sender": event["sender"],
                    "message_id": event["message_id"],
                }
            )
        )

    async def typing_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "sender": event["sender"],
                }
            )
        )

    async def seen_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "seen",
                    "sender": event["sender"],
                }
            )
        )

    async def presence_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "sender": event["sender"],
                    "online": event["online"],
                }
            )
        )

    async def notify(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "notification_type": event.get("notification_type", ""),
                    "message": event["message"],
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
    def mark_messages_seen(self):
        return Message.objects.filter(
            sender_id=self.other_user_id,
            receiver=self.user,
            is_seen=False,
        ).update(is_seen=True)

    @sync_to_async
    def create_new_message_notification(self, message_text):
        receiver = User.objects.get(id=self.other_user_id)
        create_notification(
            user=receiver,
            notification_type="new_message",
            message=f"{self.user.email}: {message_text}",
        )

    @sync_to_async
    def create_message_seen_notification(self, message_text):
        other = User.objects.get(id=self.other_user_id)
        create_notification(
            user=other,
            notification_type="message_seen",
            message=message_text,
        )

    @sync_to_async
    def save_message(self, text):
        receiver = User.objects.get(id=self.other_user_id)
        return Message.objects.create(sender=self.user, receiver=receiver, message=text)
