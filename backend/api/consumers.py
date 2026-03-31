"""
WebSocket Consumers - API Layer
Handles real-time WebSocket connections for channels and direct messages.

Features:
- Real-time message broadcasting
- Typing indicators ("Bob is typing...")
- User presence (join/leave notifications)
- JWT authentication via query parameters
"""
import json
import logging
from typing import Optional
from datetime import datetime

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from services.auth_service import AuthService
from domain.models.user import User

logger = logging.getLogger(__name__)


class BaseChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Base consumer with shared functionality for all chat consumers.
    Handles JWT authentication and common message patterns.
    """
    
    user: Optional[User] = None
    group_name: str = ""
    
    async def connect(self):
        """Handle new WebSocket connection with JWT authentication."""
        # Try to authenticate user from query parameter token
        self.user = await self.get_user_from_token()
        
        if self.user is None or isinstance(self.user, AnonymousUser):
            logger.warning("WebSocket connection rejected: Invalid or missing token")
            await self.close(code=4001)  # Custom close code for auth failure
            return
        
        # Update user's last active timestamp
        await self.update_user_active(self.user)
        
        # Accept the connection
        await self.accept()
        
        logger.info(f"WebSocket connected: user={self.user.email}, group={self.group_name}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"WebSocket disconnected: user={getattr(self.user, 'email', 'anonymous')}, group={self.group_name}")
    
    async def receive_json(self, content, **kwargs):
        """Handle incoming JSON messages from client."""
        message_type = content.get('type')
        
        if not message_type:
            await self.send_json({
                'type': 'error',
                'message': 'Message type is required'
            })
            return
        
        # Route to appropriate handler
        handler = getattr(self, f'handle_{message_type}', None)
        if handler:
            try:
                await handler(content)
            except Exception as e:
                logger.exception(f"Error handling message type '{message_type}': {e}")
                await self.send_json({
                    'type': 'error',
                    'message': f'Error processing {message_type}: {str(e)}'
                })
        else:
            await self.send_json({
                'type': 'error',
                'message': f'Unknown message type: {message_type}'
            })
    
    # ========== Message Handlers ==========
    
    async def handle_typing_start(self, content):
        """Handle typing_start event - broadcast to group and log."""
        username = self.user.get_short_name()
        logger.info(f"📝 TYPING START: {username} (user_id={self.user.id}) in {self.group_name}")
        
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': username,
                'is_typing': True,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    async def handle_typing_stop(self, content):
        """Handle typing_stop event - broadcast to group and log."""
        username = self.user.get_short_name()
        logger.info(f"🛑 TYPING STOP: {username} (user_id={self.user.id}) in {self.group_name}")
        
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': username,
                'is_typing': False,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    async def handle_ping(self, content):
        """Handle ping - respond with pong for connection health checks."""
        await self.send_json({
            'type': 'pong',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # ========== Group Broadcast Handlers ==========
    
    async def typing_indicator(self, event):
        """Broadcast typing indicator to client (called by channel_layer.group_send)."""
        # Don't send typing indicator back to the sender
        if event.get('user_id') == self.user.id:
            return
        
        await self.send_json({
            'type': 'typing_indicator',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing'],
            'timestamp': event.get('timestamp')
        })
    
    async def chat_message(self, event):
        """Broadcast chat message to client."""
        await self.send_json({
            'type': 'message',
            'message': event['message']
        })
    
    async def user_joined(self, event):
        """Broadcast user joined notification."""
        if event.get('user_id') != self.user.id:
            await self.send_json({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username']
            })
    
    async def user_left(self, event):
        """Broadcast user left notification."""
        if event.get('user_id') != self.user.id:
            await self.send_json({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username']
            })
    
    # ========== Utility Methods ==========
    
    @database_sync_to_async
    def get_user_from_token(self) -> Optional[User]:
        """
        Extract and validate JWT token from query parameters.
        Token can be passed as ?token=xxx or ?access_token=xxx
        """
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        
        # Parse query params manually
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=', 1)[1]
                break
            elif param.startswith('access_token='):
                token = param.split('=', 1)[1]
                break
        
        if not token:
            # Try headers (for some WebSocket clients)
            headers = dict(self.scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode('utf-8')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1]
        
        if not token:
            return None
        
        try:
            # Verify token
            payload = AuthService.verify_token(token)
            user_id = payload.get('user_id')
            
            if not user_id:
                return None
            
            # Get user
            user = AuthService.get_user_from_token(token)
            return user
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None
    
    @database_sync_to_async
    def update_user_active(self, user: User):
        """Update user's last active timestamp."""
        user.update_last_active()
    
    @database_sync_to_async
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


class ChannelConsumer(BaseChatConsumer):
    """
    WebSocket consumer for workspace channels.
    Handles real-time messaging and typing in channels.
    """
    
    workspace_id: int = None
    channel_id: int = None
    
    async def connect(self):
        """Connect to a channel's WebSocket group."""
        # Extract path parameters
        self.workspace_id = self.scope['url_route']['kwargs']['workspace_id']
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.group_name = f'channel_{self.channel_id}'
        
        # Call parent connect (handles auth)
        await super().connect()
        
        if self.user is None:
            return
        
        # Verify user has access to this channel
        has_access = await self.check_channel_access()
        if not has_access:
            logger.warning(f"User {self.user.email} denied access to channel {self.channel_id}")
            await self.send_json({
                'type': 'error',
                'message': 'You do not have access to this channel'
            })
            await self.close(code=4003)
            return
        
        # Join the channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.get_short_name()
            }
        )
        
        await self.send_json({
            'type': 'connected',
            'message': f'Connected to channel {self.channel_id}',
            'workspace_id': self.workspace_id,
            'channel_id': self.channel_id,
            'user_id': self.user.id,
            'username': self.user.get_short_name()
        })
    
    async def disconnect(self, close_code):
        """Disconnect from channel."""
        if self.group_name and self.user:
            # Notify others that user left
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_left',
                    'user_id': self.user.id,
                    'username': self.user.get_short_name()
                }
            )
        
        await super().disconnect(close_code)
    
    async def handle_message(self, content):
        """Handle new message in channel - save, broadcast, and log."""
        message_content = content.get('content', '').strip()
        
        if not message_content:
            await self.send_json({
                'type': 'error',
                'message': 'Message content cannot be empty'
            })
            return
        
        username = self.user.get_short_name()
        logger.info(f"💬 MESSAGE in {self.group_name}: {username} says: {message_content[:50]}{'...' if len(message_content) > 50 else ''}")
        
        # Save message using existing service
        message_data = await self.save_channel_message(message_content)
        
        if message_data:
            # Broadcast to all in group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'message': 'Failed to save message'
            })
    
    @database_sync_to_async
    def check_channel_access(self) -> bool:
        """Check if user can access this channel."""
        from domain.models.channel import Channel
        
        try:
            channel = Channel.objects.get(id=self.channel_id)
            return channel.can_view(self.user)
        except Channel.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_channel_message(self, content: str) -> Optional[dict]:
        """Save message to database using existing service."""
        from services.channel_service import ChannelService
        from domain.models.channel import Channel
        from api.serializers.channel_serializers import MessageSerializer
        
        try:
            channel = Channel.objects.get(id=self.channel_id)
            
            # Use the existing service to post message
            message = ChannelService.post_message(
                channel=channel,
                sender=self.user,
                content=content
            )
            
            # Serialize for JSON response
            serializer = MessageSerializer(message)
            return serializer.data
        except Exception as e:
            logger.exception(f"Failed to save channel message: {e}")
            return None


class DMConsumer(BaseChatConsumer):
    """
    WebSocket consumer for direct message conversations.
    Handles real-time messaging and typing in DMs.
    """
    
    workspace_id: int = None
    conversation_id: int = None
    
    async def connect(self):
        """Connect to a DM conversation's WebSocket group."""
        # Extract path parameters
        self.workspace_id = self.scope['url_route']['kwargs']['workspace_id']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f'dm_{self.conversation_id}'
        
        # Call parent connect (handles auth)
        await super().connect()
        
        if self.user is None:
            return
        
        # Verify user is a participant
        is_participant = await self.check_dm_access()
        if not is_participant:
            logger.warning(f"User {self.user.email} denied access to DM {self.conversation_id}")
            await self.send_json({
                'type': 'error',
                'message': 'You are not a participant in this conversation'
            })
            await self.close(code=4003)
            return
        
        # Join the DM group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.get_short_name()
            }
        )
        
        await self.send_json({
            'type': 'connected',
            'message': f'Connected to DM conversation {self.conversation_id}',
            'workspace_id': self.workspace_id,
            'conversation_id': self.conversation_id,
            'user_id': self.user.id,
            'username': self.user.get_short_name()
        })
    
    async def disconnect(self, close_code):
        """Disconnect from DM."""
        if self.group_name and self.user:
            # Notify others that user left
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_left',
                    'user_id': self.user.id,
                    'username': self.user.get_short_name()
                }
            )
        
        await super().disconnect(close_code)
    
    async def handle_message(self, content):
        """Handle new message in DM - save, broadcast, and log."""
        message_content = content.get('content', '').strip()
        
        if not message_content:
            await self.send_json({
                'type': 'error',
                'message': 'Message content cannot be empty'
            })
            return
        
        username = self.user.get_short_name()
        logger.info(f"💬 DM MESSAGE in {self.group_name}: {username} says: {message_content[:50]}{'...' if len(message_content) > 50 else ''}")
        
        # Save message using existing service
        message_data = await self.save_dm_message(message_content)
        
        if message_data:
            # Broadcast to all in group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
        else:
            await self.send_json({
                'type': 'error',
                'message': 'Failed to save message'
            })
    
    @database_sync_to_async
    def check_dm_access(self) -> bool:
        """Check if user is a participant in this DM conversation."""
        from domain.models.direct_message import DirectMessageConversation
        
        try:
            conversation = DirectMessageConversation.objects.get(id=self.conversation_id)
            return conversation.has_participant(self.user)
        except DirectMessageConversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_dm_message(self, content: str) -> Optional[dict]:
        """Save DM to database using existing service."""
        from services.direct_message_service import DirectMessageService
        from domain.models.direct_message import DirectMessageConversation
        from api.serializers.direct_message_serializers import DirectMessageSerializer
        
        try:
            conversation = DirectMessageConversation.objects.get(id=self.conversation_id)
            
            # Use the existing service to send DM
            dm = DirectMessageService.send_message(
                conversation=conversation,
                sender=self.user,
                content=content
            )
            
            # Serialize for JSON response
            serializer = DirectMessageSerializer(dm)
            return serializer.data
        except Exception as e:
            logger.exception(f"Failed to save DM: {e}")
            return None
