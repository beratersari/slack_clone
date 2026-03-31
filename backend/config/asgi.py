"""
ASGI config for Slack Clone project.
Supports both HTTP (Django REST Framework) and WebSocket (Django Channels).
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure the AppRegistry is populated
django_asgi_app = get_asgi_application()

# Import routing after Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import api.routing

application = ProtocolTypeRouter({
    # HTTP requests go to Django ASGI app
    "http": django_asgi_app,
    
    # WebSocket requests go through authentication middleware to consumers
    "websocket": AuthMiddlewareStack(
        URLRouter(
            api.routing.websocket_urlpatterns
        )
    ),
})
