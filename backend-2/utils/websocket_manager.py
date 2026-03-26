"""
WebSocket Connection Manager for Team Chat
Handles WebSocket connections, broadcasting, and connection lifecycle
"""
from typing import Dict, Set, List
from fastapi import WebSocket
import json
import asyncio
import sys
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections for team chat channels"""
    
    def __init__(self):
        # Structure: {channel_id: {user_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Track user to channels mapping for cleanup
        self.user_channels: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, channel_id: str, user_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        # Initialize channel connections if not exists
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = {}
        
        # Store connection
        self.active_connections[channel_id][user_id] = websocket
        
        # Track user's channels
        if user_id not in self.user_channels:
            self.user_channels[user_id] = set()
        self.user_channels[user_id].add(channel_id)
        
        print(f"[WS] User {user_id} connected to channel {channel_id}", file=sys.stderr)
        print(
            f"[WS] Active connections in channel {channel_id}: {len(self.active_connections[channel_id])}",
            file=sys.stderr,
        )
    
    def disconnect(self, channel_id: str, user_id: str):
        """Remove a WebSocket connection"""
        if channel_id in self.active_connections:
            if user_id in self.active_connections[channel_id]:
                del self.active_connections[channel_id][user_id]
                print(f"[WS] User {user_id} disconnected from channel {channel_id}", file=sys.stderr)
            
            # Clean up empty channel
            if not self.active_connections[channel_id]:
                del self.active_connections[channel_id]
                print(
                    f"[WS] Channel {channel_id} has no active connections, cleaned up",
                    file=sys.stderr,
                )
        
        # Remove from user channels tracking
        if user_id in self.user_channels:
            self.user_channels[user_id].discard(channel_id)
            if not self.user_channels[user_id]:
                del self.user_channels[user_id]
    
    def disconnect_user(self, user_id: str):
        """Disconnect user from all channels"""
        if user_id in self.user_channels:
            channels = list(self.user_channels[user_id])
            for channel_id in channels:
                self.disconnect(channel_id, user_id)
    
    async def send_personal_message(self, message: dict, channel_id: str, user_id: str):
        """Send message to a specific user in a channel"""
        if channel_id in self.active_connections:
            if user_id in self.active_connections[channel_id]:
                try:
                    await self.active_connections[channel_id][user_id].send_json(message)
                except Exception as e:
                    print(f"[WS] Error sending to user {user_id}: {str(e)}", file=sys.stderr)
                    self.disconnect(channel_id, user_id)
    
    async def broadcast_to_channel(self, message: dict, channel_id: str, exclude_user: str = None):
        """Broadcast message to all users in a channel"""
        if channel_id not in self.active_connections:
            print(f"[WS] No active connections for channel {channel_id}", file=sys.stderr)
            return
        
        # Get list of connections to avoid dict changed during iteration
        connections = list(self.active_connections[channel_id].items())
        
        disconnected_users = []
        success_count = 0
        
        for user_id, websocket in connections:
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await websocket.send_json(message)
                success_count += 1
            except Exception as e:
                print(f"[WS] Failed to send to user {user_id}: {str(e)}", file=sys.stderr)
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(channel_id, user_id)
        
        print(f"[WS] Broadcasted to {success_count} users in channel {channel_id}", file=sys.stderr)
    
    async def broadcast_to_all_channels(self, message: dict, project_id: str = None):
        """Broadcast to all channels (optionally filtered by project)"""
        for channel_id in list(self.active_connections.keys()):
            # If project_id filter is provided, you'd need to check channel's project
            # For now, broadcast to all
            await self.broadcast_to_channel(message, channel_id)
    
    def get_channel_users(self, channel_id: str) -> List[str]:
        """Get list of connected user IDs in a channel"""
        if channel_id in self.active_connections:
            return list(self.active_connections[channel_id].keys())
        return []
    
    def get_user_count(self, channel_id: str) -> int:
        """Get count of connected users in a channel"""
        if channel_id in self.active_connections:
            return len(self.active_connections[channel_id])
        return 0
    
    def is_user_connected(self, channel_id: str, user_id: str) -> bool:
        """Check if a user is connected to a channel"""
        return (channel_id in self.active_connections and 
                user_id in self.active_connections[channel_id])


# Global connection manager instance
manager = ConnectionManager()
