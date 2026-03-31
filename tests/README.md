# WebSocket Test Scripts

This folder contains Python scripts to test the real-time WebSocket features of the Slack Clone backend.

## Prerequisites

Install the required package:

```bash
pip install websockets
```

## Available Scripts

### 1. `test_websocket.py` - Single Client Test

Tests basic WebSocket functionality with a single client:
- Connects to a channel
- Sends `typing_start`
- Sends `typing_stop`
- Sends a message
- Sends `ping`

**Usage:**
```bash
# 1. Get a JWT token first
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@slackclone.com", "password": "Admin@123!"}'

# 2. Edit test_websocket.py and paste your token into JWT_TOKEN

# 3. Run the test
python tests/test_websocket.py
```

**What to look for in backend logs:**
```
INFO - WebSocket connected: user=admin@slackclone.com, group=channel_1
INFO - 📝 TYPING START: Admin (user_id=1) in channel_1
INFO - 🛑 TYPING STOP: Admin (user_id=1) in channel_1
INFO - 💬 MESSAGE in channel_1: Admin says: Hello from WebSocket test script!
```

---

### 2. `test_typing_demo.py` - Two Client Typing Demo

Simulates two users in the same channel. When one types, the other sees it in real-time!

This demonstrates the "Bob is typing..." feature.

**Usage (two terminals):**

**Terminal 1 (Sender):**
```bash
`python tests/test_typing_demo.py --user user1`
```

**Terminal 2 (Receiver):**
```bash
python tests/test_typing_demo.py --user user2
```

**Configuration:**
1. Login twice to get two tokens:
   ```bash
   curl -X POST http://localhost:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@slackclone.com", "password": "Admin@123!"}'
   
   curl -X POST http://localhost:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"email": "user@slackclone.com", "password": "User@123!"}'
   ```

2. Edit `test_typing_demo.py` and paste the tokens:
   ```python
   TOKENS = {
       "user1": "eyJhbGciOiJIUzI1NiIs...",
       "user2": "eyJhbGciOiJIUzI1NiIs...",
   }
   ```

**What you'll see:**

In Terminal 1 (sender):
```
✅ [SENDER] Connected as User-user1!
   [User-user1] Starting to type...
```

In Terminal 2 (receiver):
```
✅ [RECEIVER] Connected as User-user2!
   (Waiting for sender to type...)

   👀 [RECEIVER] SAW: User-user1 started typing!
   👀 [RECEIVER] SAW: User-user1 stopped typing!
   💬 [RECEIVER] Message from User-user1: Hello from User-user1! I was...
```

**What to look for in backend logs:**
```
INFO - 📝 TYPING START: User-user1 (user_id=1) in channel_1
INFO - 🛑 TYPING STOP: User-user1 (user_id=1) in channel_1
INFO - 💬 MESSAGE in channel_1: User-user1 says: Hello from User-user1!...
```

---

## Backend Logging

The backend logs typing and messaging events. With DEBUG level logging, you'll see:

```
📝 TYPING START: {username} (user_id={id}) in {group_name}
🛑 TYPING STOP: {username} (user_id={id}) in {group_name}
💬 MESSAGE in {group_name}: {username} says: {content}
💬 DM MESSAGE in {group_name}: {username} says: {content}
```

These are logged via `logger.info()` in `backend/api/consumers.py`.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'websockets'` | `pip install websockets` |
| `WebSocket connection rejected: Invalid or missing token` | Get a fresh token from `/api/auth/login/` |
| `You do not have access to this channel` | Make sure user is a member of the workspace/channel |
| No messages received | Both clients must connect to the same `workspace_id` and `channel_id` |

---

## Files

```
tests/
├── README.md              # This file
├── test_websocket.py      # Single client test
└── test_typing_demo.py    # Two client typing demo
```
