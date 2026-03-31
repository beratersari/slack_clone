# Slack Clone Backend

A Django-based REST API backend for a Slack clone application with real-time messaging via WebSockets and advanced search capabilities. Built with a clean N-layered architecture.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the Server](#-running-the-server)
- [Test Users](#-test-users)
- [API Endpoints](#-api-endpoints)
- [Search API](#-search-api)
- [Real-Time Messaging (WebSockets)](#-real-time-messaging-websockets)
- [Management Commands](#-management-commands)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [License](#-license)

---

## ✨ Features

### Core Features
- ✅ **User Authentication** - JWT-based auth with registration, login, logout, password change
- ✅ **User Management** - Profile management, user types (Admin, Super User, User)
- ✅ **Workspaces** - Create, join via invite code, invite members, manage roles (Owner/Admin/Member)
- ✅ **Channels** - Public/private channels, join/leave, archive/unarchive, member management
- ✅ **Messages** - Post, edit, delete, reactions, threading (replies)
- ✅ **Direct Messages** - 1:1 and group DMs with conversations, reactions

### Search Features
- ✅ **Message Search** - TF-IDF based relevance scoring across workspace messages
- ✅ **People Search** - Search workspace members by name, email, username
- ✅ **DM Search** - Search within direct message conversations
- ✅ **Search Suggestions** - Autocomplete for channels and users
- ✅ **Search Filters** - By channel, sender, date range, has files, threads
- ✅ **Efficient for Large Data** - Optimized for millions of messages

### Real-Time Features
- ✅ **WebSocket Support** - Real-time bidirectional communication
- ✅ **Typing Indicators** - "Bob is typing..." in channels and DMs
- ✅ **Live Messages** - Instantly broadcast new messages to all connected clients
- ✅ **User Presence** - See when users join/leave a channel or DM
- ✅ **Connection Health** - Ping/pong for connection monitoring

### File Attachments
- ✅ **File Uploads** - Attach files to messages and DMs
- ✅ **File Types** - Images, videos, audio, documents, code, archives
- ✅ **Thumbnails** - Auto-generated for images/videos

---

## 🏗️ Architecture

This project follows **N-layered architecture** with clear separation of concerns:

```
backend/
├── domain/          # Domain Layer - Entities and models
│   └── models/
│       ├── user.py          # User model (Admin, Super User, User)
│       ├── workspace.py     # Workspace, Membership, Invite
│       ├── channel.py       # Channel, ChannelMembership, Message
│       └── direct_message.py # DM conversations and messages
├── repository/      # Repository Layer - Data access (CRUD)
├── services/        # Services Layer - Business logic
├── api/             # API Layer - HTTP views + WebSocket consumers
│   ├── views/       # REST API endpoints
│   ├── serializers/ # Request/response formatting
│   ├── consumers.py # WebSocket handlers (NEW!)
│   └── routing.py   # WebSocket URL routing (NEW!)
└── config/          # Django configuration
    ├── settings.py
    ├── asgi.py      # ASGI for HTTP + WebSocket (UPDATED!)
    └── urls.py
```

---

## 🔧 Prerequisites

- Python 3.8+
- pip
- (Optional for production) Redis server (for multi-server WebSocket scaling)

---

## 📦 Installation

### 1. Navigate to the backend directory

```bash
cd backend
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs Django, Django REST Framework, Django Channels, and other dependencies.

### 4. Run database migrations

```bash
python manage.py migrate
```

### 5. Create dummy users (optional)

```bash
python manage.py create_dummy_users
```

---

## 🚀 Running the Server

### Development Server

```bash
python manage.py runserver
```

The API will be available at: `http://localhost:8000`

### Development with In-Memory Channels (No Redis)

For development without Redis, the settings are pre-configured. If you want to explicitly use in-memory channels (single-process only), edit `backend/config/settings.py`:

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

### Production with Redis

Set the `REDIS_URL` environment variable:

```bash
export REDIS_URL="redis://localhost:6379"
```

Or update `settings.py` to use Redis:

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

---

## 👥 Test Users

After running `create_dummy_users`, these users are available:

| Type       | Email                     | Password       |
|------------|---------------------------|----------------|
| Admin      | admin@slackclone.com      | Admin@123!     |
| Super User | superuser@slackclone.com  | SuperUser@123! |
| User       | user@slackclone.com       | User@123!      |

---

## 🛠️ Management Commands

| Command | Description |
|---------|-------------|
| `python manage.py create_dummy_users` | Create basic test users (admin, superuser, user) |
| `python manage.py create_mock_data` | Create comprehensive mock data (workspaces, channels, messages) |
| `python manage.py generate_massive_data --messages 1000000` | Generate millions of messages for search performance testing |

### Generate Massive Test Data

For testing search with large datasets (TF-IDF performance):

```bash
# Generate 1 million messages
python manage.py generate_massive_data --messages 1000000 --batch-size 10000

# Reset and regenerate
python manage.py generate_massive_data --messages 500000 --reset

# Target specific workspace
python manage.py generate_massive_data --messages 100000 --workspace-id 1
```

---

## 🔌 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login, returns JWT token |
| POST | `/api/auth/logout/` | Logout (revoke token) |
| POST | `/api/auth/refresh/` | Refresh access token |
| POST | `/api/auth/change-password/` | Change password |

### Workspaces

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/workspaces/` | List my workspaces |
| POST | `/api/auth/workspaces/` | Create workspace |
| GET | `/api/auth/workspaces/<id>/` | Workspace details |
| POST | `/api/auth/workspaces/join/` | Join by invite code |
| GET | `/api/auth/workspaces/<id>/members/` | List members |

### Channels

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/workspaces/<id>/channels/` | List channels |
| POST | `/api/auth/workspaces/<id>/channels/` | Create channel |
| GET | `/api/auth/workspaces/<id>/channels/<channel_id>/` | Channel details |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/join/` | Join channel |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/messages/` | Post message |
| GET | `/api/auth/workspaces/<id>/channels/<channel_id>/messages/` | List messages |

### Direct Messages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspaces/<id>/dm/` | List DM conversations |
| POST | `/api/workspaces/<id>/dm/start/` | Start 1:1 DM |
| POST | `/api/workspaces/<id>/dm/create/` | Create group DM |
| GET | `/api/workspaces/<id>/dm/<conv_id>/messages/` | List DM messages |
| POST | `/api/workspaces/<id>/dm/<conv_id>/messages/` | Send DM |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspaces/<id>/search/` | Combined search (messages + people) |
| GET | `/api/workspaces/<id>/search/messages/` | Search messages (TF-IDF ranked) |
| GET | `/api/workspaces/<id>/search/people/` | Search workspace members |
| GET | `/api/workspaces/<id>/search/dm/` | Search direct messages |
| GET | `/api/workspaces/<id>/search/suggestions/` | Autocomplete suggestions |
| GET | `/api/workspaces/<id>/search/counts/` | Quick result counts |
| GET | `/api/search/users/` | Global user search |

**Search Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `q` | Search query string (required) |
| `channel_ids` | Comma-separated channel IDs to filter |
| `sender_ids` | Comma-separated user IDs to filter |
| `from_date` | ISO date (messages from) |
| `to_date` | ISO date (messages until) |
| `has_files` | `true`/`false` - filter by attachments |
| `in_threads` | `true`/`false` - only thread replies |
| `sort_by` | `relevance` (TF-IDF) or `date` |
| `limit` | Results per page (default: 20, max: 100) |
| `offset` | Pagination offset |

**Example:**

```bash
# Search messages with TF-IDF relevance
GET /api/workspaces/1/search/messages/?q=meeting&limit=20

# Search with filters
GET /api/workspaces/1/search/messages/?q=team&channel_ids=1,2&from_date=2024-01-01

# Search people
GET /api/workspaces/1/search/people/?q=alice&role=admin
```

> **Full API docs available at:** `http://localhost:8000/api/docs/` (Swagger UI)

---

## ⚡ Real-Time Messaging (WebSockets)

### WebSocket Endpoints

| Purpose | URL Pattern |
|---------|-------------|
| **Channel Messages** | `ws://localhost:8000/ws/workspaces/<workspace_id>/channels/<channel_id>/` |
| **DM Messages** | `ws://localhost:8000/ws/workspaces/<workspace_id>/dm/<conversation_id>/` |

### Message Types

Clients send and receive JSON messages. Here are the supported types:

#### Client → Server (Send)

| Type | Payload | Description |
|------|---------|-------------|
| `typing_start` | `{}` | User started typing |
| `typing_stop` | `{}` | User stopped typing |
| `message` | `{"content": "Hello!"}` | Send a new message |
| `ping` | `{}` | Health check (get `pong` back) |

#### Server → Client (Receive)

| Type | Payload | Description |
|------|---------|-------------|
| `connected` | `{workspace_id, channel_id, user_id, username}` | Successfully connected |
| `typing_indicator` | `{user_id, username, is_typing, timestamp}` | Someone is/isn't typing |
| `message` | `{message: {...}}` | New message posted |
| `user_joined` | `{user_id, username}` | User joined the room |
| `user_left` | `{user_id, username}` | User left the room |
| `pong` | `{timestamp}` | Response to ping |
| `error` | `{message}` | Error occurred |

### Example WebSocket Flow

```
1. Client connects: ws://localhost:8000/ws/workspaces/1/channels/5/?token=<JWT>
   → Server: {"type": "connected", "channel_id": 5, "username": "Bob"}

2. Client sends: {"type": "typing_start"}
   → All other clients in channel 5 receive:
      {"type": "typing_indicator", "username": "Bob", "is_typing": true}

3. Client sends: {"type": "message", "content": "Hello everyone!"}
   → All clients receive:
      {"type": "message", "message": {"id": 42, "content": "Hello everyone!", ...}}

4. Client sends: {"type": "typing_stop"}
   → All other clients receive:
      {"type": "typing_indicator", "username": "Bob", "is_typing": false}
```

---

## 🧪 Testing Real-Time Features

Since this is a **backend-only project**, here are step-by-step instructions to test WebSockets.

### Step 1: Get a JWT Token

First, login to get your access token:

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@slackclone.com",
    "password": "Admin@123!"
  }'
```

Response (example):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {...}
}
```

**Save the `access_token`** — you'll need it for WebSocket connections.

---

### Step 2: Create a Workspace (if needed)

```bash
curl -X POST http://localhost:8000/api/auth/workspaces/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "name": "Test Workspace",
    "description": "For testing real-time features"
  }'
```

Note the `id` in the response (e.g., `workspace_id: 1`).

---

### Step 3: Create a Channel

```bash
curl -X POST http://localhost:8000/api/auth/workspaces/1/channels/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "name": "general",
    "channel_type": "public"
  }'
```

Note the `id` (e.g., `channel_id: 1`).

---

### Step 4: Test with Python Script (Recommended)

Create a file `test_websocket.py`:

```python
import asyncio
import json
import websockets

# Replace with your actual token and IDs
JWT_TOKEN = "YOUR_ACCESS_TOKEN_HERE"
WORKSPACE_ID = 1
CHANNEL_ID = 1

WS_URL = f"ws://localhost:8000/ws/workspaces/{WORKSPACE_ID}/channels/{CHANNEL_ID}/?token={JWT_TOKEN}"

async def test_typing_indicator():
    print(f"Connecting to: {WS_URL}")
    
    async with websockets.connect(WS_URL) as ws:
        print("✅ Connected!")
        
        # Listen for server messages
        async def listen():
            async for message in ws:
                data = json.loads(message)
                print(f"📨 Received: {json.dumps(data, indent=2)}")
        
        # Start listener in background
        listen_task = asyncio.create_task(listen())
        
        # Give it a moment to connect
        await asyncio.sleep(1)
        
        # Send typing_start
        print("\n⌨️  Sending typing_start...")
        await ws.send(json.dumps({"type": "typing_start"}))
        await asyncio.sleep(2)
        
        # Send typing_stop
        print("\n⌨️  Sending typing_stop...")
        await ws.send(json.dumps({"type": "typing_stop"}))
        await asyncio.sleep(1)
        
        # Send a message
        print("\n💬 Sending message...")
        await ws.send(json.dumps({
            "type": "message",
            "content": "Hello from WebSocket test!"
        }))
        await asyncio.sleep(2)
        
        # Send ping
        print("\n🏓 Sending ping...")
        await ws.send(json.dumps({"type": "ping"}))
        await asyncio.sleep(1)
        
        # Cancel listener and close
        listen_task.cancel()
        print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_typing_indicator())
```

Run it:

```bash
python test_websocket.py
```

**Expected Output:**
```
Connecting to: ws://localhost:8000/ws/workspaces/1/channels/1/?token=...
✅ Connected!
📨 Received: {
  "type": "connected",
  "message": "Connected to channel 1",
  "workspace_id": 1,
  "channel_id": 1,
  "user_id": 1,
  "username": "Admin"
}

⌨️  Sending typing_start...

⌨️  Sending typing_stop...

💬 Sending message...
📨 Received: {
  "type": "message",
  "message": {
    "id": 1,
    "content": "Hello from WebSocket test!",
    "sender": {...},
    ...
  }
}

🏓 Sending ping...
📨 Received: {
  "type": "pong",
  "timestamp": "2024-01-01T12:00:00.000000"
}

✅ Test complete!
```

---

### Step 5: Test with Two Clients (Typing Indicator Demo)

To see typing indicators work, open **two terminal windows**:

**Terminal 1 (User A - Admin):**
```bash
python test_websocket.py  # Uses admin token
```

**Terminal 2 (User B - Regular User):**
1. First, login as `user@slackclone.com` to get a different token
2. Edit `test_websocket.py` with User B's token
3. Run it:

```bash
python test_websocket.py
```

When User A sends `typing_start`, User B will see:
```json
{
  "type": "typing_indicator",
  "user_id": 1,
  "username": "Admin",
  "is_typing": true
}
```

This is exactly how Slack shows "Bob is typing..."! 🎉

---

### Step 6: Test with wscat (Alternative)

If you have `wscat` installed (`npm install -g wscat`):

```bash
wscat -c "ws://localhost:8000/ws/workspaces/1/channels/1/?token=YOUR_TOKEN"
```

Then type messages interactively:

```json
> {"type": "typing_start"}
< {"type": "typing_indicator", "user_id": 1, "username": "Admin", "is_typing": true}
> {"type": "message", "content": "Hi there!"}
< {"type": "message", "message": {"id": 5, "content": "Hi there!", ...}}
```

---

### Step 7: Test DM WebSocket

Similar to channels, but use the DM endpoint:

```bash
# First, start a DM via REST API
curl -X POST http://localhost:8000/api/auth/workspaces/1/dm/start/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"user_id": 2}'

# Note the conversation_id from response, then connect:
wscat -c "ws://localhost:8000/ws/workspaces/1/dm/1/?token=YOUR_TOKEN"
```

---

## 📁 Project Structure

```
backend/
├── config/
│   ├── asgi.py              # ASGI app (HTTP + WebSocket routing)
│   ├── settings.py          # Django settings (includes CHANNEL_LAYERS)
│   ├── urls.py              # HTTP URL patterns
│   └── wsgi.py
├── domain/
│   ├── models/
│   │   ├── user.py          # User (Admin, Super User, User)
│   │   ├── workspace.py     # Workspace, Membership, Invite
│   │   ├── channel.py       # Channel, Message, Reaction, FileAttachment
│   │   └── direct_message.py # DM conversations and messages
│   ├── admin.py
│   └── signals.py
├── repository/
│   ├── user_repository.py
│   ├── workspace_repository.py
│   ├── channel_repository.py
│   ├── direct_message_repository.py
│   └── search_repository.py         # 🔍 TF-IDF search operations
├── services/
│   ├── auth_service.py
│   ├── user_service.py
│   ├── workspace_service.py
│   ├── channel_service.py
│   ├── direct_message_service.py
│   └── search_service.py            # 🔍 Search business logic
├── api/
│   ├── views/
│   │   ├── auth_views.py
│   │   ├── user_views.py
│   │   ├── workspace_views.py
│   │   ├── channel_views.py
│   │   ├── direct_message_views.py
│   │   └── search_views.py          # 🔍 Search endpoints
│   ├── serializers/
│   │   ├── user_serializers.py
│   │   ├── workspace_serializers.py
│   │   ├── channel_serializers.py
│   │   ├── direct_message_serializers.py
│   │   └── search_serializers.py    # 🔍 Search response serializers
│   ├── consumers.py         # WebSocket consumers
│   ├── routing.py           # WebSocket URL routing
│   ├── authentication.py
│   ├── permissions.py
│   └── urls.py
├── repository/management/commands/
│   ├── create_dummy_users.py
│   ├── create_mock_data.py
│   └── generate_massive_data.py     # 🔍 Generate millions of messages
├── manage.py
├── requirements.txt
├── schema.yml
└── db.sqlite3
```

---

## 📚 API Documentation

Interactive API documentation is available at:

| Tool | URL |
|------|-----|
| **Swagger UI** | `http://localhost:8000/api/docs/` |
| **ReDoc** | `http://localhost:8000/api/redoc/` |
| **OpenAPI Schema** | `http://localhost:8000/api/schema/` |

### Using Swagger UI

1. Go to `http://localhost:8000/api/docs/`
2. Click **Authorize** → Enter: `Bearer <your_jwt_token>`
3. Try any endpoint interactively!

---

## 🛠️ Development

### Running Tests

```bash
python manage.py test
```

### Creating a Superuser

```bash
python manage.py createsuperuser
```

### Django Admin

Access at: `http://localhost:8000/admin/`

Use: `admin@slackclone.com` / `Admin@123!`

---

## 📄 License

This project is for educational purposes.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## ❓ Troubleshooting

### WebSocket connection fails with 4001

- Your JWT token is invalid or expired
- Get a fresh token via `/api/auth/login/`

### WebSocket connection fails with 4003

- You don't have access to the channel or DM
- Make sure you're a member of the workspace and channel

### No messages received from other clients

- Ensure both clients connected to the **same** `workspace_id` and `channel_id`
- Check that the server is running with ASGI (not just WSGI)

### ImportError: No module named 'channels'

- Run `pip install -r requirements.txt` again

---

## 🎯 Summary

You now have a fully functional Slack-like backend with:

- ✅ REST API for all CRUD operations
- ✅ JWT authentication
- ✅ **TF-IDF based search** for messages and people (efficient for millions of records)
- ✅ Real-time WebSockets for channels and DMs
- ✅ Typing indicators ("X is typing...")
- ✅ Live message broadcasting
- ✅ User presence (join/leave)
- ✅ File attachments with type detection
- ✅ Message reactions and threading
- ✅ Group DMs and private channels
- ✅ Management commands for massive test data generation

**Happy coding!** 🚀
