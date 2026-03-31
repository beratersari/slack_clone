"""
WebSocket URL Routing - API Layer
Defines WebSocket URL patterns for real-time features.
"""
from django.urls import re_path

from api.consumers import ChannelConsumer, DMConsumer

# WebSocket URL patterns
# These are used by the ASGI application for routing WebSocket connections

websocket_urlpatterns = [
    # Channel WebSocket: /ws/workspaces/<workspace_id>/channels/<channel_id>/
    # Used for real-time messages and typing indicators in workspace channels
    # Note: URLRouter passes paths WITHOUT leading slash (e.g., 'ws/workspaces/1/channels/1/')
    re_path(
        r'^ws/workspaces/(?P<workspace_id>\d+)/channels/(?P<channel_id>\d+)/$',
        ChannelConsumer.as_asgi(),
        name='ws-channel'
    ),
    
    # Direct Message WebSocket: /ws/workspaces/<workspace_id>/dm/<conversation_id>/
    # Used for real-time DMs and typing indicators in direct message conversations
    re_path(
        r'^ws/workspaces/(?P<workspace_id>\d+)/dm/(?P<conversation_id>\d+)/$',
        DMConsumer.as_asgi(),
        name='ws-dm'
    ),
]
