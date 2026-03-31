"""
Direct Message Service - Services Layer
Handles business logic for DM operations.
"""
from typing import List, Optional
from django.db import transaction
from domain.models.direct_message import (
    DirectMessageConversation,
    DirectMessageParticipant,
    DirectMessage
)
from domain.models.channel import MessageReaction
from domain.models.workspace import Workspace
from domain.models.user import User
from repository.direct_message_repository import DirectMessageRepository
from repository.user_repository import UserRepository


class DirectMessageError(Exception):
    """Custom exception for DM errors."""
    pass


class PermissionError(DirectMessageError):
    """Custom exception for permission errors."""
    pass


class DirectMessageService:
    """
    Service for handling direct message business logic.
    """
    
    # ========== Conversation Operations ==========
    
    @staticmethod
    def get_or_create_dm(user1: User, user2: User, workspace: Workspace) -> DirectMessageConversation:
        """
        Get existing 1:1 DM or create a new one between two users.
        
        Args:
            user1: First user
            user2: Second user
            workspace: The workspace
            
        Returns:
            DM conversation
        """
        # Check if both users are workspace members
        if not workspace.has_member(user1) or not workspace.has_member(user2):
            raise PermissionError("Both users must be workspace members")
        
        # Check for existing DM
        existing = DirectMessageRepository.find_existing_dm(user1, user2, workspace)
        if existing:
            return existing
        
        # Create new conversation
        with transaction.atomic():
            conversation = DirectMessageRepository.create_conversation(
                workspace=workspace,
                created_by=user1,
                is_group=False
            )
            # Add both participants
            DirectMessageRepository.add_participant(conversation, user1)
            DirectMessageRepository.add_participant(conversation, user2)
        
        return conversation
    
    @staticmethod
    def create_group_dm(created_by: User, participant_ids: List[int],
                       workspace: Workspace, name: str = '') -> DirectMessageConversation:
        """
        Create a group DM conversation.
        
        Args:
            created_by: User creating the group
            participant_ids: List of user IDs to include
            workspace: The workspace
            name: Optional name for the group
            
        Returns:
            Group DM conversation
        """
        # Validate creator is workspace member
        if not workspace.has_member(created_by):
            raise PermissionError("Must be a workspace member to create group DMs")
        
        # Get participants
        participants = []
        for user_id in participant_ids:
            user = UserRepository.get_by_id(user_id)
            if not user:
                raise DirectMessageError(f"User with ID {user_id} not found")
            if not workspace.has_member(user):
                raise DirectMessageError(f"User {user.email} is not a workspace member")
            participants.append(user)
        
        # Include creator if not already in list
        if created_by not in participants:
            participants.append(created_by)
        
        # Need at least 2 participants
        if len(participants) < 2:
            raise DirectMessageError("Group DM requires at least 2 participants")
        
        # Max 8 participants for group DMs (Slack-like limit)
        if len(participants) > 8:
            raise DirectMessageError("Group DM cannot have more than 8 participants")
        
        with transaction.atomic():
            conversation = DirectMessageRepository.create_conversation(
                workspace=workspace,
                created_by=created_by,
                name=name,
                is_group=True
            )
            
            for participant in participants:
                DirectMessageRepository.add_participant(
                    conversation, participant, added_by=created_by
                )
        
        return conversation
    
    @staticmethod
    def get_conversation(conversation_id: int, user: User) -> DirectMessageConversation:
        """
        Get conversation details.
        
        Args:
            conversation_id: Conversation ID
            user: User requesting details
            
        Returns:
            Conversation
        """
        conversation = DirectMessageRepository.get_conversation_by_id(conversation_id)
        if not conversation:
            raise DirectMessageError("Conversation not found")
        
        if not conversation.has_participant(user):
            raise PermissionError("You are not a participant in this conversation")
        
        return conversation
    
    @staticmethod
    def list_user_conversations(user: User, workspace: Optional[Workspace] = None) -> List[DirectMessageConversation]:
        """
        List all conversations for a user.
        
        Args:
            user: The user
            workspace: Optional workspace filter
            
        Returns:
            List of conversations
        """
        return DirectMessageRepository.get_user_conversations(user, workspace)
    
    @staticmethod
    def update_conversation_name(conversation: DirectMessageConversation, 
                                 name: str, user: User) -> DirectMessageConversation:
        """
        Update conversation name (group DMs only).
        
        Args:
            conversation: The conversation
            name: New name
            user: User making the change
        """
        if not conversation.has_participant(user):
            raise PermissionError("You are not a participant in this conversation")
        
        if not conversation.is_group:
            raise DirectMessageError("Cannot rename 1:1 DMs")
        
        conversation.name = name[:100]
        conversation.save(update_fields=['name', 'updated_at'])
        return conversation
    
    @staticmethod
    def archive_conversation(conversation: DirectMessageConversation, user: User) -> DirectMessageConversation:
        """Archive a conversation for the user."""
        if not conversation.has_participant(user):
            raise PermissionError("You are not a participant in this conversation")
        
        participant = DirectMessageRepository.get_participant(conversation, user)
        if participant:
            # For DMs, archiving is per-user, so we don't archive the conversation itself
            # Instead, we could track this in participant preferences
            pass
        
        conversation.archive()
        return conversation
    
    @staticmethod
    def unarchive_conversation(conversation: DirectMessageConversation, user: User) -> DirectMessageConversation:
        """Unarchive a conversation."""
        if not conversation.has_participant(user):
            raise PermissionError("You are not a participant in this conversation")
        
        conversation.unarchive()
        return conversation
    
    @staticmethod
    def leave_conversation(conversation: DirectMessageConversation, user: User) -> bool:
        """
        Leave a conversation.
        
        Args:
            conversation: The conversation
            user: User leaving
        """
        if not conversation.has_participant(user):
            raise DirectMessageError("You are not in this conversation")
        
        # Cannot leave 1:1 DMs, only archive them
        if not conversation.is_group:
            raise DirectMessageError("Cannot leave 1:1 DMs. Archive the conversation instead.")
        
        return DirectMessageRepository.remove_participant(conversation, user)
    
    @staticmethod
    def add_participant_to_group(conversation: DirectMessageConversation,
                                 new_user: User, added_by: User) -> DirectMessageParticipant:
        """
        Add a participant to a group DM.
        
        Args:
            conversation: The conversation
            new_user: User to add
            added_by: User adding them
        """
        if not conversation.is_group:
            raise DirectMessageError("Cannot add participants to 1:1 DMs")
        
        if not conversation.has_participant(added_by):
            raise PermissionError("You are not in this conversation")
        
        if conversation.has_participant(new_user):
            raise DirectMessageError("User is already in this conversation")
        
        # Max 8 participants
        if conversation.get_participant_count() >= 8:
            raise DirectMessageError("Group DM cannot have more than 8 participants")
        
        if not conversation.workspace.has_member(new_user):
            raise DirectMessageError("User must be a workspace member")
        
        return DirectMessageRepository.add_participant(
            conversation, new_user, added_by=added_by
        )
    
    # ========== Messaging Operations ==========
    
    @staticmethod
    def send_message(conversation: DirectMessageConversation, sender: User,
                    content: str, parent_message: Optional[DirectMessage] = None) -> DirectMessage:
        """
        Send a message to a conversation.
        
        Args:
            conversation: The conversation
            sender: User sending the message
            content: Message content
            parent_message: Parent message for thread replies
            
        Returns:
            Created message
        """
        if not conversation.has_participant(sender):
            raise PermissionError("You are not in this conversation")
        
        if conversation.is_archived:
            raise DirectMessageError("Cannot send messages to archived conversations")
        
        # Validate parent message belongs to same conversation
        if parent_message and parent_message.conversation != conversation:
            raise DirectMessageError("Parent message not found in this conversation")
        
        with transaction.atomic():
            message = DirectMessageRepository.create_message(
                conversation=conversation,
                sender=sender,
                content=content,
                parent_message=parent_message,
                is_thread_reply=parent_message is not None
            )
            
            # Update conversation last message info
            conversation.update_last_message(message)
            
            # Mark as read for sender
            participant = DirectMessageRepository.get_participant(conversation, sender)
            if participant:
                participant.mark_as_read()
        
        # Create notifications for DM recipients
        try:
            from services.notification_service import NotificationService
            NotificationService.create_dm_notification(message, sender, conversation)
        except Exception:
            pass  # Don't fail message sending if notifications fail
        
        return message
    
    @staticmethod
    def edit_message(message: DirectMessage, user: User, new_content: str) -> DirectMessage:
        """Edit a message."""
        if message.sender != user:
            raise PermissionError("Can only edit your own messages")
        
        if message.is_deleted:
            raise DirectMessageError("Cannot edit deleted messages")
        
        message.edit(new_content)
        return message
    
    @staticmethod
    def delete_message(message: DirectMessage, user: User) -> bool:
        """Delete a message."""
        if message.sender != user:
            raise PermissionError("Can only delete your own messages")
        
        message.soft_delete()
        return True
    
    @staticmethod
    def get_messages(conversation: DirectMessageConversation, user: User,
                    limit: int = 50, before_id: Optional[int] = None) -> List[DirectMessage]:
        """
        Get messages from a conversation.
        
        Args:
            conversation: The conversation
            user: User requesting messages
            limit: Number of messages
            before_id: Get messages before this ID
            
        Returns:
            List of messages
        """
        if not conversation.has_participant(user):
            raise PermissionError("You are not in this conversation")
        
        return DirectMessageRepository.get_messages(conversation, limit, before_id)
    
    @staticmethod
    def get_thread_replies(parent_message: DirectMessage, user: User) -> List[DirectMessage]:
        """Get thread replies for a message."""
        if not parent_message.conversation.has_participant(user):
            raise PermissionError("You are not in this conversation")
        
        return DirectMessageRepository.get_thread_replies(parent_message)
    
    @staticmethod
    def mark_conversation_as_read(conversation: DirectMessageConversation, user: User) -> bool:
        """Mark all messages in conversation as read."""
        if not conversation.has_participant(user):
            raise PermissionError("You are not in this conversation")
        
        participant = DirectMessageRepository.get_participant(conversation, user)
        if participant:
            participant.mark_as_read()
            return True
        return False
    
    # ========== Reaction Operations ==========
    
    @staticmethod
    def add_reaction(message: DirectMessage, user: User, emoji: str,
                    emoji_name: str = '') -> MessageReaction:
        """
        Add a reaction to a message.
        
        Args:
            message: The message
            user: User reacting
            emoji: Emoji unicode or shortcode
            emoji_name: Name for custom emojis
        """
        if not message.conversation.has_participant(user):
            raise PermissionError("You are not in this conversation")
        
        if message.is_deleted:
            raise DirectMessageError("Cannot react to deleted messages")
        
        return DirectMessageRepository.add_reaction(
            message, user, emoji, emoji_name
        )
    
    @staticmethod
    def remove_reaction(message: DirectMessage, user: User, emoji: str) -> bool:
        """Remove a reaction from a message."""
        if not message.conversation.has_participant(user):
            raise PermissionError("You are not in this conversation")
        
        return DirectMessageRepository.remove_reaction(message, user, emoji)
    
    @staticmethod
    def get_reactions(message: DirectMessage, user: User) -> List[MessageReaction]:
        """Get reactions for a message."""
        if not message.conversation.has_participant(user):
            raise PermissionError("You are not in this conversation")
        
        return DirectMessageRepository.get_reactions(message)
    
    # ========== Search Operations ==========
    
    @staticmethod
    def search_messages(conversation: DirectMessageConversation, user: User,
                       query: str, limit: int = 20) -> List[DirectMessage]:
        """Search messages in a conversation."""
        if not conversation.has_participant(user):
            raise PermissionError("You are not in this conversation")
        
        return DirectMessageRepository.search_messages(conversation, query, limit)
