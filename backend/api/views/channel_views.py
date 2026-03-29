"""
Channel Views - API Layer
API endpoints for channel operations.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from api.serializers.channel_serializers import (
    ChannelSerializer,
    ChannelListSerializer,
    ChannelCreateSerializer,
    ChannelUpdateSerializer,
    ChannelMembershipSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageEditSerializer
)
from services.channel_service import ChannelService, ChannelError, PermissionError as ChannelPermissionError
from services.workspace_service import WorkspaceService, WorkspaceError, PermissionError as WorkspacePermissionError
from repository.channel_repository import ChannelRepository
from repository.workspace_repository import WorkspaceRepository
from repository.user_repository import UserRepository


class ChannelListView(APIView):
    """View for listing and creating channels in a workspace."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='List workspace channels',
        description='Get all channels visible to the current user in a workspace.',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='List of channels'
            ),
            403: OpenApiResponse(description='Not a workspace member'),
            404: OpenApiResponse(description='Workspace not found')
        }
    )
    def get(self, request, workspace_id):
        """List channels in a workspace."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            channels = ChannelService.list_workspace_channels(workspace, request.user)
            serializer = ChannelListSerializer(
                channels,
                many=True,
                context={'request': request}
            )
            return Response({
                'count': len(channels),
                'channels': serializer.data
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except (ChannelError, ChannelPermissionError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Channels'],
        summary='Create channel',
        description='Create a new channel in the workspace.',
        request=ChannelCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=dict,
                description='Channel created'
            ),
            400: OpenApiResponse(description='Validation error or name exists'),
            403: OpenApiResponse(description='Not a workspace member')
        }
    )
    def post(self, request, workspace_id):
        """Create a new channel."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            serializer = ChannelCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            channel = ChannelService.create_channel(
                workspace=workspace,
                name=serializer.validated_data['name'],
                created_by=request.user,
                channel_type=serializer.validated_data.get('channel_type', 'public'),
                topic=serializer.validated_data.get('topic', ''),
                description=serializer.validated_data.get('description', '')
            )
            
            return Response({
                'message': 'Channel created successfully',
                'channel': ChannelSerializer(channel, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelDetailView(APIView):
    """View for channel details."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='Get channel details',
        description='Get detailed information about a channel.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Cannot view this channel'),
            404: OpenApiResponse(description='Channel not found')
        }
    )
    def get(self, request, workspace_id, channel_id):
        """Get channel details."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            # Verify channel belongs to workspace
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found in this workspace'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ChannelSerializer(channel, context={'request': request})
            return Response({'channel': serializer.data})
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        tags=['Channels'],
        summary='Update channel',
        description='Update channel topic and description.',
        request=ChannelUpdateSerializer,
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Admin permission required'),
            400: OpenApiResponse(description='Channel is archived')
        }
    )
    def put(self, request, workspace_id, channel_id):
        """Update channel."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ChannelUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            channel = ChannelService.update_channel(
                channel, request.user, **serializer.validated_data
            )
            return Response({
                'message': 'Channel updated',
                'channel': ChannelSerializer(channel, context={'request': request}).data
            })
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Channels'],
        summary='Delete channel',
        description='Delete an empty channel.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Admin permission required'),
            400: OpenApiResponse(description='Channel has messages or is default')
        }
    )
    def delete(self, request, workspace_id, channel_id):
        """Delete channel."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            ChannelService.delete_channel(channel, request.user)
            return Response({'message': 'Channel deleted'})
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelArchiveView(APIView):
    """View for archiving/unarchiving channels."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='Archive channel',
        description='Archive a channel (make read-only).',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Admin permission required'),
            400: OpenApiResponse(description='Cannot archive default channel')
        }
    )
    def post(self, request, workspace_id, channel_id):
        """Archive channel."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            ChannelService.archive_channel(channel, request.user)
            return Response({'message': 'Channel archived'})
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelUnarchiveView(APIView):
    """View for unarchiving channels."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='Unarchive channel',
        description='Unarchive a previously archived channel.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Admin permission required')
        }
    )
    def post(self, request, workspace_id, channel_id):
        """Unarchive channel."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            ChannelService.unarchive_channel(channel, request.user)
            return Response({'message': 'Channel unarchived'})
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelJoinView(APIView):
    """View for joining public channels."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='Join channel',
        description='Join a public channel.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Private channel or not workspace member'),
            400: OpenApiResponse(description='Already a member or archived')
        }
    )
    def post(self, request, workspace_id, channel_id):
        """Join a channel."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            membership = ChannelService.join_channel(channel, request.user)
            return Response({
                'message': 'Joined channel',
                'membership': ChannelMembershipSerializer(membership).data
            })
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelLeaveView(APIView):
    """View for leaving channels."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='Leave channel',
        description='Leave a channel (cannot leave #general).',
        responses={
            200: OpenApiResponse(response=dict),
            400: OpenApiResponse(description='Not a member or is default channel')
        }
    )
    def post(self, request, workspace_id, channel_id):
        """Leave a channel."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            ChannelService.leave_channel(channel, request.user)
            return Response({'message': 'Left channel'})
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelMemberListView(APIView):
    """View for channel members."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='List channel members',
        description='Get all members of a channel.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Cannot view this channel')
        }
    )
    def get(self, request, workspace_id, channel_id):
        """Get channel members."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            members = ChannelService.get_channel_members(channel, request.user)
            serializer = ChannelMembershipSerializer(members, many=True)
            return Response({
                'count': len(members),
                'members': serializer.data
            })
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelInviteView(APIView):
    """View for inviting users to private channels."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='Invite to channel',
        description='Invite a workspace member to a private channel.',
        request=dict,
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Must be channel member'),
            400: OpenApiResponse(description='User already member or not in workspace')
        }
    )
    def post(self, request, workspace_id, channel_id):
        """Invite user to channel."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            user_id = request.data.get('user_id')
            if not user_id:
                return Response(
                    {'error': 'user_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            invited_user = UserRepository.get_by_id(user_id)
            if not invited_user:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            membership = ChannelService.invite_to_channel(
                channel, invited_user, request.user
            )
            return Response({
                'message': 'User invited to channel',
                'membership': ChannelMembershipSerializer(membership).data
            })
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class ChannelMarkReadView(APIView):
    """View for marking channel as read."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Channels'],
        summary='Mark as read',
        description='Mark all messages in channel as read.',
        responses={
            200: OpenApiResponse(response=dict)
        }
    )
    def post(self, request, workspace_id, channel_id):
        """Mark channel as read."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            ChannelService.mark_channel_as_read(channel, request.user)
            return Response({'message': 'Channel marked as read'})
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


# ========== Message Views ==========

class MessageListView(APIView):
    """View for listing and creating messages."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Messages'],
        summary='List messages',
        description='Get messages from a channel (paginated).',
        parameters=[
            {'name': 'limit', 'in': 'query', 'type': 'integer', 'description': 'Number of messages (default 50)'},
            {'name': 'before_id', 'in': 'query', 'type': 'integer', 'description': 'Get messages before this ID'}
        ],
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Cannot view channel')
        }
    )
    def get(self, request, workspace_id, channel_id):
        """Get channel messages."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            limit = int(request.query_params.get('limit', 50))
            before_id = request.query_params.get('before_id')
            if before_id:
                before_id = int(before_id)
            
            messages = ChannelService.get_channel_messages(
                channel, request.user, limit=limit, before_id=before_id
            )
            serializer = MessageSerializer(
                messages,
                many=True,
                context={'request': request}
            )
            
            # Mark as read
            ChannelService.mark_channel_as_read(channel, request.user)
            
            return Response({
                'count': len(messages),
                'messages': serializer.data
            })
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Messages'],
        summary='Post message',
        description='Post a new message to a channel.',
        request=MessageCreateSerializer,
        responses={
            201: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Cannot post to channel'),
            400: OpenApiResponse(description='Channel is archived')
        }
    )
    def post(self, request, workspace_id, channel_id):
        """Post a message."""
        try:
            channel = ChannelService.get_channel_detail(channel_id, request.user)
            if channel.workspace.id != workspace_id:
                return Response(
                    {'error': 'Channel not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = MessageCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Handle thread replies
            parent_message = None
            parent_id = serializer.validated_data.get('parent_message_id')
            if parent_id:
                parent_message = ChannelRepository.get_message_by_id(parent_id)
                if not parent_message or parent_message.channel != channel:
                    return Response(
                        {'error': 'Parent message not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            message = ChannelService.post_message(
                channel=channel,
                sender=request.user,
                content=serializer.validated_data['content'],
                parent_message=parent_message
            )
            
            return Response({
                'message': 'Message posted',
                'data': MessageSerializer(message, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class MessageDetailView(APIView):
    """View for individual message operations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Messages'],
        summary='Edit message',
        description='Edit your own message.',
        request=MessageEditSerializer,
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Can only edit own messages')
        }
    )
    def put(self, request, workspace_id, channel_id, message_id):
        """Edit a message."""
        try:
            message = ChannelRepository.get_message_by_id(message_id)
            if not message or message.channel.id != channel_id:
                return Response(
                    {'error': 'Message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = MessageEditSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            message = ChannelService.edit_message(
                message, request.user, serializer.validated_data['content']
            )
            return Response({
                'message': 'Message updated',
                'data': MessageSerializer(message, context={'request': request}).data
            })
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Messages'],
        summary='Delete message',
        description='Delete your own message (or admin can delete any).',
        responses={
            200: OpenApiResponse(response=dict)
        }
    )
    def delete(self, request, workspace_id, channel_id, message_id):
        """Delete a message."""
        try:
            message = ChannelRepository.get_message_by_id(message_id)
            if not message or message.channel.id != channel_id:
                return Response(
                    {'error': 'Message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            ChannelService.delete_message(message, request.user)
            return Response({'message': 'Message deleted'})
        except ChannelError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChannelPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
