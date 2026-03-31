#!/usr/bin/env python3
"""
WebSocket Typing Indicator Demo - Two Clients
Simulates two users in the same channel. When one types, the other sees it.

This demonstrates the "Bob is typing..." feature!

Usage:
    Terminal 1: python tests/test_typing_demo.py --user user1
    Terminal 2: python tests/test_typing_demo.py --user user2

Both will connect to the same channel and exchange typing indicators.

Configuration:
    Edit the TOKENS dict below with your actual JWT tokens.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("❌ Error: websockets package not installed.")
    print("   Install it with: pip install websockets")
    sys.exit(1)

# ============ Configuration ============
# Replace with your actual JWT tokens from login
TOKENS = {
    "user1": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6ImFkbWluQHNsYWNrY2xvbmUuY29tIiwidXNlcm5hbWUiOiJhZG1pbiIsInVzZXJfdHlwZSI6ImFkbWluIiwiaXNfc3RhZmYiOnRydWUsImV4cCI6MTc3NDk3MzA3OSwiaWF0IjoxNzc0ODg2Njc5LCJ0eXBlIjoiYWNjZXNzIn0.EyJ5hgbW2b0ihQjbcn6ZU4BBsyfe4o6LgTLtlfRNGz8",
    "user2": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJlbWFpbCI6InN1cGVydXNlckBzbGFja2Nsb25lLmNvbSIsInVzZXJuYW1lIjoic3VwZXJ1c2VyIiwidXNlcl90eXBlIjoic3VwZXJfdXNlciIsImlzX3N0YWZmIjpmYWxzZSwiZXhwIjoxNzc0OTcyOTA1LCJpYXQiOjE3NzQ4ODY1MDUsInR5cGUiOiJhY2Nlc3MifQ.hr7CuMouQVvmIxHMQPMixYTX56HMYVyG8kLCbdt5Vkk",
}

# Workspace and channel IDs (both users must have access)
WORKSPACE_ID = 1
CHANNEL_ID = 1

# WebSocket URL template
WS_URL_TEMPLATE = "ws://localhost:8000/ws/workspaces/{workspace_id}/channels/{channel_id}/?token={token}"


def get_ws_url(user_key):
    """Build WebSocket URL for a user."""
    token = TOKENS.get(user_key, "")
    return WS_URL_TEMPLATE.format(
        workspace_id=WORKSPACE_ID,
        channel_id=CHANNEL_ID,
        token=token
    )


async def client(user_key: str, role: str):
    """
    WebSocket client that connects and participates in typing demo.
    
    role: 'sender' or 'receiver'
    - sender: sends typing_start/typing_stop events
    - receiver: just listens and prints what it receives
    """
    url = get_ws_url(user_key)
    username = f"User-{user_key}"
    
    print(f"\n{'='*60}")
    print(f"[{role.upper()}] {username} connecting...")
    print(f"{'='*60}")
    
    try:
        async with websockets.connect(url) as ws:
            print(f"✅ [{role.upper()}] Connected as {username}!")
            
            # Track received messages
            received = []
            
            async def listener():
                """Listen for incoming messages and print them."""
                try:
                    async for message in ws:
                        data = json.loads(message)
                        received.append(data)
                        msg_type = data.get('type', 'unknown')
                        
                        # Pretty print interesting messages
                        if msg_type == 'typing_indicator':
                            who = data.get('username', '?')
                            is_typing = data.get('is_typing', False)
                            action = "started typing" if is_typing else "stopped typing"
                            print(f"\n   👀 [{role}] SAW: {who} {action}!")
                        elif msg_type == 'connected':
                            print(f"   📍 [{role}] Server says: {data.get('message', 'Connected')}")
                        elif msg_type == 'message':
                            msg_data = data.get('message', {})
                            who = msg_data.get('sender', {}).get('username', 'Someone')
                            content = msg_data.get('content', '')[:40]
                            print(f"\n   💬 [{role}] Message from {who}: {content}...")
                        elif msg_type == 'user_joined':
                            who = data.get('username', '?')
                            print(f"   👋 [{role}] {who} joined the channel")
                        elif msg_type == 'user_left':
                            who = data.get('username', '?')
                            print(f"   👋 [{role}] {who} left the channel")
                        elif msg_type == 'pong':
                            print(f"   🏓 [{role}] Pong received!")
                        else:
                            print(f"\n   📨 [{role}] {msg_type}: {json.dumps(data)[:80]}")
                except websockets.exceptions.ConnectionClosed:
                    print(f"\n   ⚠️  [{role}] Connection closed")
            
            # Start listener
            listen_task = asyncio.create_task(listener())
            await asyncio.sleep(1)  # Let connection establish
            
            if role == "sender":
                print(f"\n{'-'*40}")
                print(f"[{role.upper()}] {username} will now type...")
                print(f"{'-'*40}\n")
                
                # Simulate typing
                print(f"   [{username}] Starting to type...")
                await ws.send(json.dumps({"type": "typing_start"}))
                await asyncio.sleep(3)  # "Type" for 3 seconds
                
                print(f"   [{username}] Finished typing, sending message...")
                await ws.send(json.dumps({"type": "typing_stop"}))
                await asyncio.sleep(0.5)
                
                await ws.send(json.dumps({
                    "type": "message",
                    "content": f"Hello from {username}! I was typing. Did you see it?"
                }))
                await asyncio.sleep(2)
                
                # Send another typing burst
                print(f"\n   [{username}] Typing again briefly...")
                await ws.send(json.dumps({"type": "typing_start"}))
                await asyncio.sleep(1.5)
                await ws.send(json.dumps({"type": "typing_stop"}))
                await asyncio.sleep(1)
                
                print(f"\n   [{username}] Done! Check the other terminal to see typing indicators.")
            
            else:  # receiver
                print(f"\n{'-'*40}")
                print(f"[{role.upper()}] {username} is listening for typing indicators...")
                print(f"{'-'*40}")
                print("   (Waiting for sender to type...)\n")
                
                # Just wait and listen
                await asyncio.sleep(20)  # Listen for 20 seconds
            
            # Cancel listener
            listen_task.cancel()
            print(f"\n✅ [{role.upper()}] {username} finished.")
            
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ [{role.upper()}] WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"❌ [{role.upper()}] Error: {e}")
        return False
    
    return True


async def main(user_key: str):
    """Main entry point."""
    print("=" * 60)
    print("WebSocket Typing Indicator Demo")
    print("=" * 60)
    print(f"\nUser: {user_key}")
    print(f"Workspace: {WORKSPACE_ID}, Channel: {CHANNEL_ID}")
    
    # Validate token
    token = TOKENS.get(user_key, "")
    if not token or token.startswith("YOUR_"):
        print(f"\n❌ Error: Please configure TOKENS['{user_key}'] in this script!")
        print("\n   Steps:")
        print("   1. Login twice to get two different tokens:")
        print("      curl -X POST http://localhost:8000/api/auth/login/ \\")
        print("        -H 'Content-Type: application/json' \\")
        print("        -d '{\"email\": \"admin@slackclone.com\", \"password\": \"Admin@123!\"}'")
        print("      curl -X POST http://localhost:8000/api/auth/login/ \\")
        print("        -H 'Content-Type: application/json' \\")
        print("        -d '{\"email\": \"user@slackclone.com\", \"password\": \"User@123!\"}'")
        print("   2. Copy both 'access_token' values")
        print("   3. Paste them into TOKENS dict at the top of this file")
        return False
    
    # Run as sender or receiver based on user
    if user_key == "user1":
        return await client("user1", "sender")
    else:
        return await client("user2", "receiver")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Typing Indicator Demo")
    parser.add_argument(
        "--user",
        choices=["user1", "user2"],
        required=True,
        help="Which user to simulate (user1=sender, user2=receiver)"
    )
    args = parser.parse_args()
    
    success = asyncio.run(main(args.user))
    sys.exit(0 if success else 1)
