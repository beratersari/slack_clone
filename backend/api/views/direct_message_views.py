"""
Direct Message Views - API Layer
API endpoints for DM operations.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from api.serializers.direct_message_serializers import (
    DirectMessageConversationSerializer,
    DirectMessageConversationListSerializer,
    DirectMessageConversationCreateSerializer,
    DirectMessageSerializer,
    DirectMessageCreateSerializer,
    DirectMessageEditSerializer,
    MessageReactionSerializer,
    ReactionCreateSerializer,
    DirectMessageParticipantSerializer
)
from services.direct_message_service import (
    DirectMessageService,
    DirectMessageError,
    PermissionError as DMPermissionError
)
from services.workspace_service import WorkspaceService, WorkspaceError, PermissionError as WorkspacePermissionError
from repository.direct_message_repository import DirectMessageRepository
from repository.user_repository import UserRepository


class DMConversationListView(APIView):
    """View for listing and creating DM conversations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='List DM conversations',
        description='Get all DM conversations for the current user in a workspace.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a workspace member')
        }
    )
    def get(self, request, workspace_id):
        """List DM conversations."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            conversations = DirectMessageService.list_user_conversations(
                request.user, workspace
            )
            serializer = DirectMessageConversationListSerializer(
                conversations,
                many=True,
                context={'request': request}
            )
            return Response({
                'count': len(conversations),
                'conversations': serializer.data
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except WorkspacePermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMConversationCreateView(APIView):
    """View for creating new DM conversations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Create group DM',
        description='Create a new group DM conversation.',
        request=DirectMessageConversationCreateSerializer,
        responses={
            201: OpenApiResponse(response=dict),
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Not a workspace member')
        }
    )
    def post(self, request, workspace_id):
        """Create a group DM conversation."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            
            serializer = DirectMessageConversationCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            participant_ids = serializer.validated_data['participant_ids']
            name = serializer.validated_data.get('name', '')
            
            conversation = DirectMessageService.create_group_dm(
                created_by=request.user,
                participant_ids=participant_ids,
                workspace=workspace,
                name=name
            )
            
            return Response({
                'message': 'Group DM created',
                'conversation': DirectMessageConversationSerializer(
                    conversation, context={'request': request}
                ).data
            }, status=status.HTTP_201_CREATED)
            
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMConversationDetailView(APIView):
    """View for DM conversation details."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Get DM conversation',
        description='Get details of a DM conversation.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant'),
            404: OpenApiResponse(description='Conversation not found')
        }
    )
    def get(self, request, workspace_id, conversation_id):
        """Get conversation details."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            # Verify conversation belongs to workspace
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found in this workspace'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = DirectMessageConversationSerializer(
                conversation, context={'request': request}
            )
            return Response({'conversation': serializer.data})
            
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


class DMStartView(APIView):
    """View for starting a 1:1 DM with a user."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Start 1:1 DM',
        description='Start or get existing 1:1 DM with a user.',
        request=dict,
        responses={
            200: OpenApiResponse(response=dict),
            201: OpenApiResponse(response=dict, description='New conversation created'),
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Not a workspace member')
        }
    )
    def post(self, request, workspace_id):
        """Start a 1:1 DM with a user."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            
            user_id = request.data.get('user_id')
            if not user_id:
                return Response(
                    {'error': 'user_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            other_user = UserRepository.get_by_id(user_id)
            if not other_user:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            conversation = DirectMessageService.get_or_create_dm(
                request.user, other_user, workspace
            )
            
            # Determine if new or existing
            is_new = conversation.created_by == request.user and conversation.get_participant_count() == 2
            
            return Response({
                'message': 'DM conversation ready',
                'conversation': DirectMessageConversationSerializer(
                    conversation, context={'request': request}
                ).data
            }, status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK)
            
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMConversationArchiveView(APIView):
    """View for archiving DM conversations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Archive DM conversation',
        description='Archive a DM conversation.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def post(self, request, workspace_id, conversation_id):
        """Archive a conversation."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            DirectMessageService.archive_conversation(conversation, request.user)
            return Response({'message': 'Conversation archived'})
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMConversationUnarchiveView(APIView):
    """View for unarchiving DM conversations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Unarchive DM conversation',
        description='Unarchive a previously archived DM conversation.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def post(self, request, workspace_id, conversation_id):
        """Unarchive a conversation."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            DirectMessageService.unarchive_conversation(conversation, request.user)
            return Response({'message': 'Conversation unarchived'})
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMLeaveView(APIView):
    """View for leaving group DMs."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Leave group DM',
        description='Leave a group DM conversation.',
        responses={
            200: OpenApiResponse(response=dict),
            400: OpenApiResponse(description='Cannot leave 1:1 DM'),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def post(self, request, workspace_id, conversation_id):
        """Leave a group DM."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            DirectMessageService.leave_conversation(conversation, request.user)
            return Response({'message': 'Left conversation'})
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DMParticipantAddView(APIView):
    """View for adding participants to group DMs."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Add participant to group DM',
        description='Add a user to a group DM conversation.',
        request=dict,
        responses={
            200: OpenApiResponse(response=dict),
            400: OpenApiResponse(description='Group full or user already in'),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def post(self, request, workspace_id, conversation_id):
        """Add a participant to a group DM."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            user_id = request.data.get('user_id')
            if not user_id:
                return Response(
                    {'error': 'user_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            new_user = UserRepository.get_by_id(user_id)
            if not new_user:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            participant = DirectMessageService.add_participant_to_group(
                conversation, new_user, request.user
            )
            
            return Response({
                'message': 'Participant added',
                'participant': DirectMessageParticipantSerializer(participant).data
            })
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMMarkReadView(APIView):
    """View for marking DM conversation as read."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Mark DM as read',
        description='Mark all messages in a DM conversation as read.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def post(self, request, workspace_id, conversation_id):
        """Mark conversation as read."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            DirectMessageService.mark_conversation_as_read(conversation, request.user)
            return Response({'message': 'Conversation marked as read'})
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


# ========== Message Views ==========

class DMMessageListView(APIView):
    """View for listing and sending DM messages."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='List DM messages',
        description='Get messages from a DM conversation.',
        parameters=[
            {'name': 'limit', 'in': 'query', 'type': 'integer', 'description': 'Number of messages (default 50)'},
            {'name': 'before_id', 'in': 'query', 'type': 'integer', 'description': 'Get messages before this ID'}
        ],
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def get(self, request, workspace_id, conversation_id):
        """Get DM messages."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            limit = int(request.query_params.get('limit', 50))
            before_id = request.query_params.get('before_id')
            if before_id:
                before_id = int(before_id)
            
            messages = DirectMessageService.get_messages(
                conversation, request.user, limit=limit, before_id=before_id
            )
            serializer = DirectMessageSerializer(
                messages,
                many=True,
                context={'request': request}
            )
            
            # Mark as read
            DirectMessageService.mark_conversation_as_read(conversation, request.user)
            
            return Response({
                'count': len(messages),
                'messages': serializer.data
            })
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Send DM message',
        description='Send a message to a DM conversation.',
        request=DirectMessageCreateSerializer,
        responses={
            201: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant or archived')
        }
    )
    def post(self, request, workspace_id, conversation_id):
        """Send a DM message."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = DirectMessageCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Handle thread replies
            parent_message = None
            parent_id = serializer.validated_data.get('parent_message_id')
            if parent_id:
                parent_message = DirectMessageRepository.get_message_by_id(parent_id)
                if not parent_message or parent_message.conversation != conversation:
                    return Response(
                        {'error': 'Parent message not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            message = DirectMessageService.send_message(
                conversation=conversation,
                sender=request.user,
                content=serializer.validated_data['content'],
                parent_message=parent_message
            )
            
            return Response({
                'message': 'Message sent',
                'data': DirectMessageSerializer(message, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMMessageDetailView(APIView):
    """View for individual DM message operations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Edit DM message',
        description='Edit your own DM message.',
        request=DirectMessageEditSerializer,
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Can only edit own messages')
        }
    )
    def put(self, request, workspace_id, conversation_id, message_id):
        """Edit a DM message."""
        try:
            message = DirectMessageRepository.get_message_by_id(message_id)
            if not message or message.conversation.id != conversation_id:
                return Response(
                    {'error': 'Message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = DirectMessageEditSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            message = DirectMessageService.edit_message(
                message, request.user, serializer.validated_data['content']
            )
            return Response({
                'message': 'Message updated',
                'data': DirectMessageSerializer(message, context={'request': request}).data
            })
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Delete DM message',
        description='Delete your own DM message.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Can only delete own messages')
        }
    )
    def delete(self, request, workspace_id, conversation_id, message_id):
        """Delete a DM message."""
        try:
            message = DirectMessageRepository.get_message_by_id(message_id)
            if not message or message.conversation.id != conversation_id:
                return Response(
                    {'error': 'Message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            DirectMessageService.delete_message(message, request.user)
            return Response({'message': 'Message deleted'})
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


# ========== Thread Reply Views ==========

class DMThreadReplyListView(APIView):
    """View for thread replies in DMs."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Get thread replies',
        description='Get all replies to a DM message.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def get(self, request, workspace_id, conversation_id, message_id):
        """Get thread replies."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            parent_message = DirectMessageRepository.get_message_by_id(message_id)
            if not parent_message or parent_message.conversation != conversation:
                return Response(
                    {'error': 'Parent message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            replies = DirectMessageService.get_thread_replies(
                parent_message, request.user
            )
            serializer = DirectMessageSerializer(
                replies,
                many=True,
                context={'request': request}
            )
            
            return Response({
                'count': len(replies),
                'replies': serializer.data,
                'parent_message': DirectMessageSerializer(
                    parent_message, context={'request': request}
                ).data
            })
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


# ========== Reaction Views ==========

class DMReactionAddView(APIView):
    """View for adding reactions to DM messages."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Add reaction',
        description='Add an emoji reaction to a DM message.',
        request=ReactionCreateSerializer,
        responses={
            201: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def post(self, request, workspace_id, conversation_id, message_id):
        """Add a reaction to a message."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            message = DirectMessageRepository.get_message_by_id(message_id)
            if not message or message.conversation != conversation:
                return Response(
                    {'error': 'Message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ReactionCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reaction = DirectMessageService.add_reaction(
                message=message,
                user=request.user,
                emoji=serializer.validated_data['emoji'],
                emoji_name=serializer.validated_data.get('emoji_name', '')
            )
            
            return Response({
                'message': 'Reaction added',
                'reaction': MessageReactionSerializer(reaction).data
            }, status=status.HTTP_201_CREATED)
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class DMReactionRemoveView(APIView):
    """View for removing reactions from DM messages."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Direct Messages'],
        summary='Remove reaction',
        description='Remove your emoji reaction from a DM message.',
        responses={
            200: OpenApiResponse(response=dict),
            403: OpenApiResponse(description='Not a participant')
        }
    )
    def delete(self, request, workspace_id, conversation_id, message_id):
        """Remove a reaction from a message."""
        try:
            conversation = DirectMessageService.get_conversation(
                conversation_id, request.user
            )
            if conversation.workspace.id != workspace_id:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            message = DirectMessageRepository.get_message_by_id(message_id)
            if not message or message.conversation != conversation:
                return Response(
                    {'error': 'Message not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            emoji = request.query_params.get('emoji')
            if not emoji:
                return Response(
                    {'error': 'emoji query parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            DirectMessageService.remove_reaction(message, request.user, emoji)
            return Response({'message': 'Reaction removed'})
            
        except DirectMessageError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DMPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
