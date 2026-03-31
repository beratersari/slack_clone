"""
Notification Views - API Layer
API endpoints for notifications and mentions.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from services.notification_service import NotificationService
from repository.notification_repository import NotificationRepository, MentionRepository
from api.serializers.notification_serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    MentionSerializer
)


class NotificationListView(APIView):
    """List and manage user notifications."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Notifications'],
        summary='List notifications',
        description='Get notifications for the current user.',
        parameters=[
            OpenApiParameter(name='unread_only', type=bool, required=False),
            OpenApiParameter(name='limit', type=int, required=False),
            OpenApiParameter(name='offset', type=int, required=False),
        ],
        responses={200: OpenApiResponse(description='List of notifications')}
    )
    def get(self, request):
        """Get user notifications."""
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        limit = min(int(request.query_params.get('limit', 50)), 100)
        offset = int(request.query_params.get('offset', 0))
        
        notifications = NotificationService.get_user_notifications(
            user=request.user,
            unread_only=unread_only,
            limit=limit,
            offset=offset
        )
        
        unread_count = NotificationService.get_unread_count(request.user)
        
        return Response({
            'count': len(notifications),
            'unread_count': unread_count,
            'notifications': NotificationListSerializer(notifications, many=True).data
        })
    
    @extend_schema(
        tags=['Notifications'],
        summary='Mark all as read',
        description='Mark all notifications as read.',
        responses={200: OpenApiResponse(description='All marked as read')}
    )
    def post(self, request):
        """Mark all notifications as read."""
        count = NotificationService.mark_all_as_read(request.user)
        return Response({
            'message': f'Marked {count} notifications as read',
            'marked_count': count
        })


class NotificationDetailView(APIView):
    """Single notification operations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Notifications'],
        summary='Mark as read',
        description='Mark a single notification as read.',
        responses={200: OpenApiResponse(description='Marked as read')}
    )
    def post(self, request, notification_id):
        """Mark a notification as read."""
        success = NotificationService.mark_as_read(notification_id, request.user)
        if success:
            return Response({'message': 'Notification marked as read'})
        return Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @extend_schema(
        tags=['Notifications'],
        summary='Delete notification',
        description='Delete a notification.',
        responses={204: OpenApiResponse(description='Deleted')}
    )
    def delete(self, request, notification_id):
        """Delete a notification."""
        success = NotificationService.delete_notification(notification_id, request.user)
        if success:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )


class UnreadNotificationCountView(APIView):
    """Get unread notification count."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Notifications'],
        summary='Get unread count',
        description='Get the count of unread notifications.',
        responses={200: OpenApiResponse(description='Unread count')}
    )
    def get(self, request):
        """Get unread notification count."""
        count = NotificationService.get_unread_count(request.user)
        return Response({'unread_count': count})


class MentionListView(APIView):
    """List mentions for the current user."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Notifications'],
        summary='List mentions',
        description='Get mentions where you were mentioned.',
        parameters=[
            OpenApiParameter(name='limit', type=int, required=False),
        ],
        responses={200: OpenApiResponse(description='List of mentions')}
    )
    def get(self, request):
        """Get mentions for user."""
        limit = min(int(request.query_params.get('limit', 20)), 100)
        
        mentions = MentionRepository.get_user_mentions(request.user, limit=limit)
        
        return Response({
            'count': len(mentions),
            'mentions': MentionSerializer(mentions, many=True).data
        })
