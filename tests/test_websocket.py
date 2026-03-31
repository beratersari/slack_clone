#!/usr/bin/env python3
"""
WebSocket Test Script - Single Client
Tests typing indicators, messages, and connection health.

Usage:
    python tests/test_websocket.py

Configuration:
    Edit the constants below to match your setup.
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("❌ Error: websockets package not installed.")
    print("   Install it with: pip install websockets")
    sys.exit(1)

# ============ Configuration ============
# Replace with your actual JWT token from login
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6ImFkbWluQHNsYWNrY2xvbmUuY29tIiwidXNlcm5hbWUiOiJhZG1pbiIsInVzZXJfdHlwZSI6ImFkbWluIiwiaXNfc3RhZmYiOnRydWUsImV4cCI6MTc3NDk3MzA3OSwiaWF0IjoxNzc0ODg2Njc5LCJ0eXBlIjoiYWNjZXNzIn0.EyJ5hgbW2b0ihQjbcn6ZU4BBsyfe4o6LgTLtlfRNGz8"

# Workspace and channel IDs (create via REST API first)
WORKSPACE_ID = 1
CHANNEL_ID = 1

# WebSocket URL
WS_URL = f"ws://localhost:8000/ws/workspaces/{WORKSPACE_ID}/channels/{CHANNEL_ID}/?token={JWT_TOKEN}"


async def test_websocket():
    """Test WebSocket connection, typing indicators, and messages."""
    print("=" * 60)
    print("WebSocket Test Script - Single Client")
    print("=" * 60)
    print(f"\n📡 Connecting to: {WS_URL.replace(JWT_TOKEN, '***')}")
    
    try:
        async with websockets.connect(WS_URL) as ws:
            print("✅ Connected successfully!\n")
            
            # Listen for incoming messages in background
            received_messages = []
            
            async def listener():
                try:
                    async for message in ws:
                        data = json.loads(message)
                        received_messages.append(data)
                        print(f"\n📨 [{data.get('type', 'unknown')}] {json.dumps(data, indent=2)}")
                except websockets.exceptions.ConnectionClosed:
                    print("\n⚠️  Connection closed by server")
            
            # Start listener task
            listen_task = asyncio.create_task(listener())
            
            # Give connection a moment to establish
            await asyncio.sleep(1)
            
            # Test 1: Typing start
            print("-" * 40)
            print("⌨️  TEST 1: Sending typing_start")
            print("-" * 40)
            await ws.send(json.dumps({"type": "typing_start"}))
            await asyncio.sleep(2)  # Wait to see logs
            
            # Test 2: Typing stop
            print("\n" + "-" * 40)
            print("⌨️  TEST 2: Sending typing_stop")
            print("-" * 40)
            await ws.send(json.dumps({"type": "typing_stop"}))
            await asyncio.sleep(1)
            
            # Test 3: Send a message
            print("\n" + "-" * 40)
            print("💬 TEST 3: Sending a message")
            print("-" * 40)
            test_message = "Hello from WebSocket test script!"
            await ws.send(json.dumps({
                "type": "message",
                "content": test_message
            }))
            await asyncio.sleep(2)
            
            # Test 4: Ping
            print("\n" + "-" * 40)
            print("🏓 TEST 4: Sending ping")
            print("-" * 40)
            await ws.send(json.dumps({"type": "ping"}))
            await asyncio.sleep(1)
            
            # Summary
            print("\n" + "=" * 60)
            print("✅ Test Complete!")
            print(f"   Total messages received: {len(received_messages)}")
            print("=" * 60)
            
            # Cancel listener
            listen_task.cancel()
            
    except websockets.exceptions.WebSocketException as e:
        print(f"\n❌ WebSocket error: {e}")
        print("\n💡 Tips:")
        print("   1. Make sure the Django server is running: python manage.py runserver")
        print("   2. Check your JWT token is valid (get from /api/auth/login/)")
        print("   3. Verify WORKSPACE_ID and CHANNEL_ID exist")
        return False
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # Check if token is configured
    if JWT_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("❌ Error: Please configure JWT_TOKEN at the top of this script!")
        print("\n   Steps:")
        print("   1. Login to get a token:")
        print("      curl -X POST http://localhost:8000/api/auth/login/ \\")
        print("        -H 'Content-Type: application/json' \\")
        print("        -d '{\"email\": \"admin@slackclone.com\", \"password\": \"Admin@123!\"}'")
        print("   2. Copy the 'access_token' value")
        print("   3. Paste it into JWT_TOKEN at line ~25")
        sys.exit(1)
    
    # Run the test
    success = asyncio.run(test_websocket())
    sys.exit(0 if success else 1)
