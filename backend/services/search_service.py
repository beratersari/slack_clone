"""
Search Service - Services Layer
Handles business logic for search operations within workspaces.
Similar to Slack's search functionality.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from domain.models.channel import Channel, Message
from domain.models.direct_message import DirectMessage
from domain.models.user import User
from domain.models.workspace import Workspace, WorkspaceMembership
from repository.search_repository import SearchRepository
from repository.workspace_repository import WorkspaceRepository


class SearchError(Exception):
    """Custom exception for search errors."""
    pass


class SearchService:
    """
    Service for handling search business logic.
    Provides Slack-like search functionality for messages and people.
    """
    
    # ========== Message Search ==========
    
    @staticmethod
    def search_messages(
        workspace_id: int,
        user: User,
        query: str,
        channel_ids: Optional[List[int]] = None,
        sender_ids: Optional[List[int]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        has_files: Optional[bool] = None,
        in_threads: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = 'relevance'
    ) -> Dict[str, Any]:
        """
        Search messages in a workspace.
        
        Args:
            workspace_id: Workspace to search in
            user: User performing search
            query: Search query string
            channel_ids: Optional channel filter
            sender_ids: Optional sender filter
            from_date: ISO date string for start date
            to_date: ISO date string for end date
            has_files: Filter for messages with attachments
            in_threads: Filter for thread replies
            limit: Max results per page
            offset: Pagination offset
            sort_by: 'relevance' or 'date'
            
        Returns:
            Dict with messages, total count, and pagination info
        """
        # Verify workspace access
        workspace = WorkspaceRepository.get_by_id(workspace_id)
        if not workspace:
            raise SearchError("Workspace not found")
        
        if not workspace.has_member(user):
            raise SearchError("You are not a member of this workspace")
        
        # Parse dates if provided
        parsed_from_date = None
        parsed_to_date = None
        
        if from_date:
            try:
                parsed_from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            except ValueError:
                raise SearchError("Invalid from_date format. Use ISO 8601 format.")
        
        if to_date:
            try:
                parsed_to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            except ValueError:
                raise SearchError("Invalid to_date format. Use ISO 8601 format.")
        
        # Perform search
        messages, total_count = SearchRepository.search_messages_in_workspace(
            workspace=workspace,
            query=query,
            user=user,
            channel_ids=channel_ids,
            sender_ids=sender_ids,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            has_files=has_files,
            in_threads=in_threads,
            limit=limit,
            offset=offset,
            sort_by=sort_by
        )
        
        return {
            'messages': messages,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
            'query': query
        }
    
    @staticmethod
    def search_messages_in_channel(
        channel_id: int,
        user: User,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search messages within a specific channel.
        """
        from repository.channel_repository import ChannelRepository
        
        channel = ChannelRepository.get_by_id(channel_id)
        if not channel:
            raise SearchError("Channel not found")
        
        if not channel.can_view(user):
            raise SearchError("You cannot view this channel")
        
        messages, total_count = SearchRepository.search_messages_in_channel(
            channel=channel,
            query=query,
            user=user,
            limit=limit,
            offset=offset
        )
        
        return {
            'messages': messages,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
            'query': query,
            'channel': channel
        }
    
    @staticmethod
    def search_direct_messages(
        workspace_id: int,
        user: User,
        query: str,
        conversation_ids: Optional[List[int]] = None,
        sender_ids: Optional[List[int]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search direct messages in a workspace.
        """
        workspace = WorkspaceRepository.get_by_id(workspace_id)
        if not workspace:
            raise SearchError("Workspace not found")
        
        if not workspace.has_member(user):
            raise SearchError("You are not a member of this workspace")
        
        messages, total_count = SearchRepository.search_direct_messages(
            workspace=workspace,
            query=query,
            user=user,
            conversation_ids=conversation_ids,
            sender_ids=sender_ids,
            limit=limit,
            offset=offset
        )
        
        return {
            'messages': messages,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
            'query': query
        }
    
    # ========== People Search ==========
    
    @staticmethod
    def search_people(
        workspace_id: int,
        user: User,
        query: str,
        limit: int = 20,
        offset: int = 0,
        role: Optional[str] = None,
        online_only: bool = False
    ) -> Dict[str, Any]:
        """
        Search people (members) in a workspace.
        
        Args:
            workspace_id: Workspace to search in
            user: User performing search
            query: Search query (name, email, username)
            limit: Max results
            offset: Pagination offset
            role: Filter by role
            online_only: Only recently active users
            
        Returns:
            Dict with memberships, total count, pagination info
        """
        # Verify workspace access
        workspace = WorkspaceRepository.get_by_id(workspace_id)
        if not workspace:
            raise SearchError("Workspace not found")
        
        if not workspace.has_member(user):
            raise SearchError("You are not a member of this workspace")
        
        # Validate role if provided
        valid_roles = ['owner', 'admin', 'member']
        if role and role not in valid_roles:
            raise SearchError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        
        memberships, total_count = SearchRepository.search_people_in_workspace(
            workspace=workspace,
            query=query,
            limit=limit,
            offset=offset,
            role=role,
            online_only=online_only
        )
        
        return {
            'members': memberships,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
            'query': query
        }
    
    @staticmethod
    def search_users_global(
        user: User,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Global user search (for inviting users, etc.).
        """
        users, total_count = SearchRepository.search_users_global(
            query=query,
            limit=limit,
            offset=offset
        )
        
        return {
            'users': users,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
            'query': query
        }
    
    # ========== Search Suggestions & Counts ==========
    
    @staticmethod
    def get_search_suggestions(
        workspace_id: int,
        user: User,
        partial_query: str
    ) -> Dict[str, Any]:
        """
        Get search suggestions for autocomplete.
        """
        workspace = WorkspaceRepository.get_by_id(workspace_id)
        if not workspace:
            raise SearchError("Workspace not found")
        
        if not workspace.has_member(user):
            raise SearchError("You are not a member of this workspace")
        
        suggestions = SearchRepository.get_search_suggestions(
            workspace=workspace,
            user=user,
            partial_query=partial_query
        )
        
        return suggestions
    
    @staticmethod
    def get_search_counts(
        workspace_id: int,
        user: User,
        query: str
    ) -> Dict[str, int]:
        """
        Get quick counts for search tabs.
        """
        workspace = WorkspaceRepository.get_by_id(workspace_id)
        if not workspace:
            raise SearchError("Workspace not found")
        
        if not workspace.has_member(user):
            raise SearchError("You are not a member of this workspace")
        
        counts = SearchRepository.count_search_results(
            workspace=workspace,
            user=user,
            query=query
        )
        
        return counts
    
    # ========== Advanced Search (Slack-like syntax) ==========
    
    @staticmethod
    def parse_search_query(query: str) -> Dict[str, Any]:
        """
        Parse Slack-like search syntax.
        
        Supports:
        - from:@user - messages from a specific user
        - in:#channel - messages in a specific channel
        - before:2024-01-01 - messages before date
        - after:2024-01-01 - messages after date
        - has:file - messages with attachments
        - is:thread - only thread replies
        
        Example: "hello from:@alice in:#general after:2024-01-01"
        """
        filters = {
            'text_query': [],
            'sender_ids': [],
            'channel_ids': [],
            'from_date': None,
            'to_date': None,
            'has_files': None,
            'in_threads': None
        }
        
        import re
        
        # Extract from:@user patterns
        from_pattern = r'from:@(\w+)'
        from_matches = re.findall(from_pattern, query)
        for username in from_matches:
            # Would need to resolve username to user_id
            # For now, we'll handle this in the service layer
            pass
        query = re.sub(from_pattern, '', query)
        
        # Extract in:#channel patterns
        in_pattern = r'in:#(\w+)'
        in_matches = re.findall(in_pattern, query)
        for channel_name in in_matches:
            # Would need to resolve channel_name to channel_id
            pass
        query = re.sub(in_pattern, '', query)
        
        # Extract date filters
        before_pattern = r'before:(\d{4}-\d{2}-\d{2})'
        before_match = re.search(before_pattern, query)
        if before_match:
            filters['to_date'] = before_match.group(1)
            query = re.sub(before_pattern, '', query)
        
        after_pattern = r'after:(\d{4}-\d{2}-\d{2})'
        after_match = re.search(after_pattern, query)
        if after_match:
            filters['from_date'] = after_match.group(1)
            query = re.sub(after_pattern, '', query)
        
        # Extract has:file
        if 'has:file' in query:
            filters['has_files'] = True
            query = query.replace('has:file', '')
        
        # Extract is:thread
        if 'is:thread' in query:
            filters['in_threads'] = True
            query = query.replace('is:thread', '')
        
        # Clean up remaining query
        filters['text_query'] = ' '.join(query.split()).strip()
        
        return filters
