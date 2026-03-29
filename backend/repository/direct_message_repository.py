"""
Direct Message Repository - Repository Layer
Handles data access operations for DM entities.
"""
from typing import Optional, List
from django.db.models import Q, Count
from domain.models.direct_message import (
    DirectMessageConversation,
    DirectMessageParticipant,
    DirectMessage
)
from domain.models.channel import MessageReaction, FileAttachment
from domain.models.workspace import Workspace
from domain.models.user import User


class DirectMessageRepository:
    """
    Repository for Direct Message data access operations.
    """
    
    # ========== Conversation Operations ==========
    
    @staticmethod
    def get_conversation_by_id(conversation_id: int) -> Optional[DirectMessageConversation]:
        """Get conversation by ID."""
        try:
            return DirectMessageConversation.objects.get(id=conversation_id)
        except DirectMessageConversation.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_conversations(user: User, workspace: Optional[Workspace] = None,
                                include_archived: bool = False) -> List[DirectMessageConversation]:
        """Get all conversations where user is a participant."""
        queryset = DirectMessageConversation.objects.filter(
            participants__user=user,
            participants__is_active=True,
            is_active=True
        ).select_related('workspace', 'created_by').prefetch_related('participants', 'participants__user')
        
        if workspace:
            queryset = queryset.filter(workspace=workspace)
        
        if not include_archived:
            queryset = queryset.filter(is_archived=False)
        
        return list(queryset.order_by('-last_message_at'))
    
    @staticmethod
    def find_existing_dm(user1: User, user2: User, workspace: Workspace) -> Optional[DirectMessageConversation]:
        """
        Find existing 1:1 DM between two users in a workspace.
        Returns None if not found.
        """
        # Find conversations where both users are participants and it's not a group DM
        conversations = DirectMessageConversation.objects.filter(
            workspace=workspace,
            is_group=False,
            is_active=True,
            participants__user=user1,
            participants__is_active=True
        ).filter(
            participants__user=user2,
            participants__is_active=True
        )
        
        # Ensure it's exactly 2 participants (1:1 DM)
        for conv in conversations:
            if conv.get_participant_count() == 2:
                return conv
        return None
    
    @staticmethod
    def create_conversation(workspace: Workspace, created_by: User,
                           name: str = '', is_group: bool = False) -> DirectMessageConversation:
        """Create a new DM conversation."""
        return DirectMessageConversation.objects.create(
            workspace=workspace,
            created_by=created_by,
            name=name,
            is_group=is_group
        )
    
    @staticmethod
    def update_conversation(conversation: DirectMessageConversation, **fields) -> DirectMessageConversation:
        """Update conversation fields."""
        allowed_fields = ['name', 'is_archived', 'last_message_at', 'last_message_preview']
        for field, value in fields.items():
            if field in allowed_fields and hasattr(conversation, field):
                setattr(conversation, field, value)
        conversation.save()
        return conversation
    
    @staticmethod
    def delete_conversation(conversation_id: int) -> bool:
        """Delete conversation by ID."""
        try:
            conversation = DirectMessageConversation.objects.get(id=conversation_id)
            conversation.delete()
            return True
        except DirectMessageConversation.DoesNotExist:
            return False
    
    # ========== Participant Operations ==========
    
    @staticmethod
    def get_participant(conversation: DirectMessageConversation, 
                       user: User) -> Optional[DirectMessageParticipant]:
        """Get participant record for a user in a conversation."""
        try:
            return DirectMessageParticipant.objects.get(
                conversation=conversation,
                user=user,
                is_active=True
            )
        except DirectMessageParticipant.DoesNotExist:
            return None
    
    @staticmethod
    def add_participant(conversation: DirectMessageConversation, user: User,
                       added_by: Optional[User] = None) -> DirectMessageParticipant:
        """Add a participant to a conversation."""
        participant, created = DirectMessageParticipant.objects.get_or_create(
            conversation=conversation,
            user=user,
            defaults={'added_by': added_by, 'is_active': True}
        )
        if not created and not participant.is_active:
            participant.is_active = True
            participant.added_by = added_by
            participant.save()
        return participant
    
    @staticmethod
    def remove_participant(conversation: DirectMessageConversation, user: User) -> bool:
        """Remove a participant from a conversation."""
        try:
            participant = DirectMessageParticipant.objects.get(
                conversation=conversation,
                user=user,
                is_active=True
            )
            participant.is_active = False
            from django.utils import timezone
            participant.left_at = timezone.now()
            participant.save()
            return True
        except DirectMessageParticipant.DoesNotExist:
            return False
    
    @staticmethod
    def get_participants(conversation: DirectMessageConversation) -> List[DirectMessageParticipant]:
        """Get all active participants of a conversation."""
        return list(DirectMessageParticipant.objects.filter(
            conversation=conversation,
            is_active=True
        ).select_related('user'))
    
    # ========== Message Operations ==========
    
    @staticmethod
    def create_message(conversation: DirectMessageConversation, sender: User,
                      content: str, parent_message: Optional[DirectMessage] = None,
                      is_thread_reply: bool = False) -> DirectMessage:
        """Create a new direct message."""
        return DirectMessage.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            parent_message=parent_message,
            is_thread_reply=is_thread_reply
        )
    
    @staticmethod
    def get_message_by_id(message_id: int) -> Optional[DirectMessage]:
        """Get message by ID."""
        try:
            return DirectMessage.objects.get(id=message_id, is_deleted=False)
        except DirectMessage.DoesNotExist:
            return None
    
    @staticmethod
    def get_messages(conversation: DirectMessageConversation, 
                    limit: int = 50,
                    before_id: Optional[int] = None) -> List[DirectMessage]:
        """Get messages from a conversation."""
        queryset = DirectMessage.objects.filter(
            conversation=conversation,
            is_deleted=False,
            is_thread_reply=False  # Only top-level messages
        ).select_related('sender').prefetch_related('reactions', 'reactions__user', 'attachments')
        
        if before_id:
            try:
                before_message = DirectMessage.objects.get(id=before_id)
                queryset = queryset.filter(created_at__lt=before_message.created_at)
            except DirectMessage.DoesNotExist:
                pass
        
        return list(queryset.order_by('-created_at')[:limit])
    
    @staticmethod
    def get_thread_replies(parent_message: DirectMessage) -> List[DirectMessage]:
        """Get replies to a message."""
        return list(DirectMessage.objects.filter(
            parent_message=parent_message,
            is_deleted=False,
            is_thread_reply=True
        ).select_related('sender').prefetch_related('reactions', 'attachments').order_by('created_at'))
    
    @staticmethod
    def search_messages(conversation: DirectMessageConversation, query: str,
                       limit: int = 20) -> List[DirectMessage]:
        """Search messages in a conversation."""
        return list(DirectMessage.objects.filter(
            conversation=conversation,
            content__icontains=query,
            is_deleted=False
        ).order_by('-created_at')[:limit])
    
    # ========== Reaction Operations ==========
    
    @staticmethod
    def add_reaction(message: DirectMessage, user: User, emoji: str,
                    emoji_name: str = '') -> MessageReaction:
        """Add a reaction to a message."""
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=user,
            emoji=emoji,
            defaults={'emoji_name': emoji_name}
        )
        return reaction
    
    @staticmethod
    def remove_reaction(message: DirectMessage, user: User, emoji: str) -> bool:
        """Remove a reaction from a message."""
        try:
            reaction = MessageReaction.objects.get(
                message=message,
                user=user,
                emoji=emoji
            )
            reaction.delete()
            return True
        except MessageReaction.DoesNotExist:
            return False
    
    @staticmethod
    def get_reactions(message: DirectMessage) -> List[MessageReaction]:
        """Get all reactions for a message."""
        return list(MessageReaction.objects.filter(
            message=message
        ).select_related('user'))
    
    @staticmethod
    def get_reaction_counts(message: DirectMessage) -> dict:
        """Get reaction counts grouped by emoji."""
        from django.db.models import Count
        reactions = MessageReaction.objects.filter(
            message=message
        ).values('emoji').annotate(
            count=Count('id')
        ).order_by('-count')
        return {r['emoji']: r['count'] for r in reactions}
    
    # ========== File Attachment Operations ==========
    
    @staticmethod
    def create_attachment(message: Optional[DirectMessage] = None, **kwargs) -> FileAttachment:
        """Create a file attachment."""
        return FileAttachment.objects.create(
            direct_message=message,
            **kwargs
        )
    
    @staticmethod
    def get_attachment_by_id(attachment_id: int) -> Optional[FileAttachment]:
        """Get attachment by ID."""
        try:
            return FileAttachment.objects.get(id=attachment_id, is_deleted=False)
        except FileAttachment.DoesNotExist:
            return None
    
    @staticmethod
    def get_message_attachments(message: DirectMessage) -> List[FileAttachment]:
        """Get all attachments for a message."""
        return list(FileAttachment.objects.filter(
            direct_message=message,
            is_deleted=False
        ))
