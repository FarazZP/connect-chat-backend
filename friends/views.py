from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.contrib.auth import get_user_model
from .models import FriendRequest, Friendship
from .serializers import FriendRequestSerializer
from django.shortcuts import get_object_or_404

User = get_user_model()


class SendFriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        receiver = get_object_or_404(User, id=user_id)

        if receiver == request.user:
            return Response({"error": "You cannot send request to yourself"})

        already_pending = FriendRequest.objects.filter(
            sender=request.user,
            receiver=receiver,
            status='pending'
        ).exists()
        if already_pending:
            return Response({"error": "Friend request already pending"})

        FriendRequest.objects.create(
            sender=request.user,
            receiver=receiver
        )

        return Response({"message": "Friend request sent"})


class AcceptFriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, request_id):
        friend_request = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)

        friend_request.status = 'accepted'
        friend_request.save()

        Friendship.objects.create(
            user1=friend_request.sender,
            user2=friend_request.receiver
        )

        return Response({"message": "Friend request accepted"})


class RejectFriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, request_id):
        friend_request = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)

        friend_request.status = 'rejected'
        friend_request.save()

        return Response({"message": "Friend request rejected"})


class FriendListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        friendships = Friendship.objects.filter(user1=request.user) | Friendship.objects.filter(user2=request.user)

        friends = []
        for friendship in friendships:
            if friendship.user1 == request.user:
                friends.append(friendship.user2.email)
            else:
                friends.append(friendship.user1.email)

        return Response({"friends": friends})


class PendingRequestsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requests = FriendRequest.objects.filter(receiver=request.user, status='pending')
        serializer = FriendRequestSerializer(requests, many=True)
        return Response(serializer.data)