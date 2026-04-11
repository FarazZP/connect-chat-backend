from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def create_notification(user, notification_type, message):
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
    )


def push_notification_ws(user_id, notification_type, message):
    """Push a real-time notification to all sockets in group user_<user_id>."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "notify",
                "notification_type": notification_type,
                "message": message,
            },
        )
    except Exception:
        # DB notification still succeeded; WS is best-effort if Redis/channel layer is down.
        pass
