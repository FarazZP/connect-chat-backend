import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

from chat.consumer import ChatConsumer
from chat.middleware import JWTAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    # JWT: ws://127.0.0.1:8000/ws/chat/<other_user_id>/?token=<access_token>
    "websocket": JWTAuthMiddleware(
        URLRouter([
            path("ws/chat/<int:user_id>/", ChatConsumer.as_asgi()),
        ])
    ),
})