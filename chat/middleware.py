"""ASGI middleware: authenticate WebSockets via JWT in the query string.

Clients connect with:
  ws://127.0.0.1:8000/ws/chat/<other_user_id>/?token=<access_jwt>
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_token_payload(user_id):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if user_id is None:
        return AnonymousUser()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Set scope['user'] from ?token=... (SimpleJWT access token)."""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            query_string = scope.get("query_string", b"").decode()
            token = parse_qs(query_string).get("token", [None])[0]
            if token:
                from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
                from rest_framework_simplejwt.tokens import AccessToken

                try:
                    access = AccessToken(token)
                    user_id = access.get("user_id")
                    scope["user"] = await _user_from_token_payload(user_id)
                except (InvalidToken, TokenError, TypeError, KeyError):
                    scope["user"] = AnonymousUser()
            else:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
