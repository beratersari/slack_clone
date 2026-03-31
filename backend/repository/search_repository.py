"""
Search Repository - Repository Layer
Handles efficient search operations for messages and users within workspaces.
Optimized for high-volume data (millions of records).

Includes TF-IDF based relevance scoring for message search.
"""
import math
import re
from collections import Counter
from typing import Optional, List, Tuple, Dict
from django.db.models import Q, Count, Prefetch
from django.db import connection
from django.utils import timezone
from domain.models.channel import Channel, Message, ChannelMembership
from domain.models.direct_message import DirectMessage, DirectMessageConversation
from domain.models.user import User
from domain.models.workspace import Workspace, WorkspaceMembership
from datetime import datetime, timedelta


# ========== TF-IDF Utilities ==========

def tokenize(text: str) -> List[str]:
    """
    Tokenize text into lowercase words, removing punctuation.
    Simple but effective tokenization for TF-IDF.
    """
    if not text:
        return []
    # Convert to lowercase and extract words (alphanumeric sequences)
    text = text.lower()
    tokens = re.findall(r'\b[a-z0-9]+\b', text)
    return tokens


def compute_tf(tokens: List[str]) -> Dict[str, float]:
    """
    Compute Term Frequency (TF) for a document.
    TF = (count of term in document) / (total terms in document)
    """
    if not tokens:
        return {}
    
    term_counts = Counter(tokens)
    total_terms = len(tokens)
    
    return {term: count / total_terms for term, count in term_counts.items()}


def compute_idf(documents_tokens: List[List[str]]) -> Dict[str, float]:
    """
    Compute Inverse Document Frequency (IDF) across all documents.
    IDF = log(N / df), where N = total docs, df = docs containing term
    Using smooth IDF: log((N+1) / (df+1)) + 1 to avoid zero/negative values
    """
    if not documents_tokens:
        return {}
    
    n_docs = len(documents_tokens)
    if n_docs == 0:
        return {}
    
    # Count documents containing each term
    doc_freq = Counter()
    for tokens in documents_tokens:
        unique_terms = set(tokens)
        doc_freq.update(unique_terms)
    
    # Compute IDF with smoothing
    idf = {}
    for term, df in doc_freq.items():
        idf[term] = math.log((n_docs + 1) / (df + 1)) + 1
    
    return idf


def compute_tf_idf(tf: Dict[str, float], idf: Dict[str, float]) -> Dict[str, float]:
    """
    Compute TF-IDF score for each term.
    TF-IDF = TF * IDF
    """
    return {term: tf_val * idf.get(term, 0) for term, tf_val in tf.items()}


def score_document(query_tokens: List[str], doc_tokens: List[str], 
                   idf: Dict[str, float]) -> float:
    """
    Score a document against a query using TF-IDF.
    Returns the sum of TF-IDF scores for query terms found in the document.
    """
    if not query_tokens or not doc_tokens:
        return 0.0
    
    doc_tf = compute_tf(doc_tokens)
    
    score = 0.0
    for term in query_tokens:
        if term in doc_tf:
            score += doc_tf[term] * idf.get(term, 0)
    
    return score


class SearchRepository:
    """
    Repository for search operations.
    Provides efficient search across messages and users in a workspace.
    """
    
    # ========== Message Search ==========
    
    @staticmethod
    def search_messages_in_workspace(
        workspace: Workspace,
        query: str,
        user: User,
        channel_ids: Optional[List[int]] = None,
        sender_ids: Optional[List[int]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        has_files: Optional[bool] = None,
        in_threads: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = 'relevance'
    ) -> Tuple[List[Message], int]:
        """
        Search messages within a workspace with filters.
        Optimized for large datasets with proper indexing.
        
        Args:
            workspace: The workspace to search in
            query: Search query string
            user: User performing the search (for permission checks)
            channel_ids: Filter by specific channels (None = all visible)
            sender_ids: Filter by specific senders
            from_date: Filter messages from this date
            to_date: Filter messages until this date
            has_files: Filter messages with/without attachments
            in_threads: Filter only thread replies or main messages
            limit: Maximum results to return
            offset: Pagination offset
            sort_by: 'relevance' or 'date'
            
        Returns:
            Tuple of (messages list, total count)
        """
        # Get channels user can see
        visible_channel_ids = SearchRepository._get_visible_channel_ids(workspace, user)
        
        if channel_ids:
            # Intersect with visible channels
            visible_channel_ids = [cid for cid in channel_ids if cid in visible_channel_ids]
        
        if not visible_channel_ids:
            return ([], 0)
        
        # Build base queryset - exclude deleted messages
        queryset = Message.objects.filter(
            channel_id__in=visible_channel_ids,
            is_deleted=False
        ).select_related('sender', 'channel').prefetch_related('attachments')
        
        # Apply text search
        if query and query.strip():
            # Use full-text search if available, fallback to icontains
            search_terms = query.strip().split()
            for term in search_terms:
                if len(term) >= 2:  # Skip very short terms
                    queryset = queryset.filter(content__icontains=term)
        
        # Apply filters
        if sender_ids:
            queryset = queryset.filter(sender_id__in=sender_ids)
        
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)
        
        if has_files is not None:
            if has_files:
                queryset = queryset.filter(attachments__isnull=False)
            else:
                queryset = queryset.filter(attachments__isnull=True)
        
        if in_threads is not None:
            queryset = queryset.filter(is_thread_reply=in_threads)
        
        # Get total count before pagination (matching documents)
        total_count = queryset.count()
        
        # Apply sorting
        if sort_by == 'date':
            queryset = queryset.order_by('-created_at')
            messages = list(queryset[offset:offset + limit])
        else:
            # For relevance, use TF-IDF scoring:
            # 1. Fetch candidate messages (up to 2000 for scoring efficiency)
            # 2. Compute TF-IDF scores
            # 3. Sort by TF-IDF score (with secondary factors)
            
            # Get user membership info for secondary ranking
            user_channel_ids = set(
                ChannelMembership.objects.filter(
                    user=user,
                    channel_id__in=visible_channel_ids,
                    is_active=True
                ).values_list('channel_id', flat=True)
            )
            
            # Fetch candidates for TF-IDF scoring (limit to avoid memory issues)
            # We fetch more than needed to ensure good TF-IDF ranking
            candidate_limit = min(total_count, 2000)
            candidates = list(queryset[:candidate_limit])
            
            if not candidates:
                return ([], 0)
            
            # Compute TF-IDF scores
            query_tokens = tokenize(query)
            
            # Build document corpus for IDF calculation
            # For efficiency, we use the candidates as the corpus
            # (In production, you'd want a pre-computed corpus or use full-text search)
            documents_tokens = [tokenize(msg.content) for msg in candidates]
            idf = compute_idf(documents_tokens)
            
            # Score each message
            scored_messages = []
            for msg in candidates:
                doc_tokens = tokenize(msg.content)
                tfidf_score = score_document(query_tokens, doc_tokens, idf)
                
                # Add bonuses for better relevance
                bonus = 0.0
                
                # Bonus for user's channel membership
                if msg.channel_id in user_channel_ids:
                    bonus += 0.5
                
                # Bonus for exact phrase match
                if query.lower() in msg.content.lower():
                    bonus += 1.0
                
                # Recency bonus (messages from last 7 days get slight boost)
                days_old = (datetime.now(timezone.utc) - msg.created_at).days
                if days_old < 7:
                    bonus += 0.1 * (7 - days_old) / 7
                
                final_score = tfidf_score + bonus
                scored_messages.append((msg, final_score))
            
            # Sort by score descending, then by date as tiebreaker
            scored_messages.sort(key=lambda x: (-x[1], -x[0].created_at.timestamp()))
            
            # Apply pagination on scored results
            paginated = scored_messages[offset:offset + limit]
            messages = [msg for msg, score in paginated]
        
        return (messages, total_count)
    
    @staticmethod
    def search_messages_in_channel(
        channel: Channel,
        query: str,
        user: User,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Message], int]:
        """
        Search messages within a specific channel.
        """
        if not channel.can_view(user):
            return ([], 0)
        
        queryset = Message.objects.filter(
            channel=channel,
            is_deleted=False
        ).select_related('sender').prefetch_related('attachments')
        
        if query and query.strip():
            for term in query.strip().split():
                if len(term) >= 2:
                    queryset = queryset.filter(content__icontains=term)
        
        total_count = queryset.count()
        messages = list(queryset.order_by('-created_at')[offset:offset + limit])
        
        return (messages, total_count)
    
    @staticmethod
    def search_direct_messages(
        workspace: Workspace,
        query: str,
        user: User,
        conversation_ids: Optional[List[int]] = None,
        sender_ids: Optional[List[int]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[DirectMessage], int]:
        """
        Search direct messages within a workspace.
        """
        # Get conversations user is part of
        user_conversation_ids = DirectMessageConversation.objects.filter(
            workspace=workspace,
            participants__user=user,
            participants__is_active=True
        ).values_list('id', flat=True)
        
        if conversation_ids:
            user_conversation_ids = [cid for cid in conversation_ids if cid in user_conversation_ids]
        
        if not user_conversation_ids:
            return ([], 0)
        
        queryset = DirectMessage.objects.filter(
            conversation_id__in=user_conversation_ids,
            is_deleted=False
        ).select_related('sender', 'conversation').prefetch_related('attachments')
        
        if query and query.strip():
            for term in query.strip().split():
                if len(term) >= 2:
                    queryset = queryset.filter(content__icontains=term)
        
        if sender_ids:
            queryset = queryset.filter(sender_id__in=sender_ids)
        
        total_count = queryset.count()
        messages = list(queryset.order_by('-created_at')[offset:offset + limit])
        
        return (messages, total_count)
    
    # ========== People Search ==========
    
    @staticmethod
    def search_people_in_workspace(
        workspace: Workspace,
        query: str,
        limit: int = 20,
        offset: int = 0,
        role: Optional[str] = None,
        online_only: bool = False
    ) -> Tuple[List[WorkspaceMembership], int]:
        """
        Search people (members) within a workspace.
        
        Args:
            workspace: The workspace
            query: Search query (name, username, email)
            limit: Max results
            offset: Pagination offset
            role: Filter by role (owner, admin, member)
            online_only: Only show recently active users
            
        Returns:
            Tuple of (memberships list, total count)
        """
        queryset = WorkspaceMembership.objects.filter(
            workspace=workspace,
            is_active=True
        ).select_related('user')
        
        # Apply text search
        if query and query.strip():
            search_terms = query.strip().split()
            q_object = Q()
            for term in search_terms:
                if len(term) >= 1:
                    q_object |= (
                        Q(user__email__icontains=term) |
                        Q(user__username__icontains=term) |
                        Q(user__first_name__icontains=term) |
                        Q(user__last_name__icontains=term) |
                        Q(user__display_name__icontains=term)
                    )
            queryset = queryset.filter(q_object)
        
        # Apply role filter
        if role:
            queryset = queryset.filter(role=role)
        
        # Apply online filter (active in last 15 minutes)
        if online_only:
            from django.utils import timezone
            fifteen_min_ago = timezone.now() - timedelta(minutes=15)
            queryset = queryset.filter(user__last_active__gte=fifteen_min_ago)
        
        total_count = queryset.count()
        
        # Order by relevance (exact matches first) then alphabetically
        memberships = list(
            queryset.order_by('role', 'user__display_name', 'user__username')[offset:offset + limit]
        )
        
        return (memberships, total_count)
    
    @staticmethod
    def search_users_global(
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[User], int]:
        """
        Global user search (across all workspaces user has access to).
        Used for finding users to invite, etc.
        """
        queryset = User.objects.filter(is_active=True)
        
        if query and query.strip():
            search_terms = query.strip().split()
            q_object = Q()
            for term in search_terms:
                if len(term) >= 1:
                    q_object |= (
                        Q(email__icontains=term) |
                        Q(username__icontains=term) |
                        Q(first_name__icontains=term) |
                        Q(last_name__icontains=term) |
                        Q(display_name__icontains=term)
                    )
            queryset = queryset.filter(q_object)
        
        total_count = queryset.count()
        users = list(
            queryset.order_by('display_name', 'username')[offset:offset + limit]
        )
        
        return (users, total_count)
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def _get_visible_channel_ids(workspace: Workspace, user: User) -> List[int]:
        """
        Get all channel IDs that a user can see in a workspace.
        Includes public channels and private channels where user is member.
        """
        # Public channels
        public_ids = list(
            Channel.objects.filter(
                workspace=workspace,
                channel_type='public',
                is_archived=False
            ).values_list('id', flat=True)
        )
        
        # Private channels where user is member
        private_ids = list(
            ChannelMembership.objects.filter(
                channel__workspace=workspace,
                channel__channel_type='private',
                channel__is_archived=False,
                user=user,
                is_active=True
            ).values_list('channel_id', flat=True)
        )
        
        return public_ids + private_ids
    
    @staticmethod
    def get_search_suggestions(
        workspace: Workspace,
        user: User,
        partial_query: str,
        limit: int = 10
    ) -> dict:
        """
        Get search suggestions for autocomplete.
        Returns matching channels, users, and common search terms.
        """
        suggestions = {
            'channels': [],
            'users': [],
            'recent_searches': []  # Could be implemented with user history
        }
        
        if not partial_query or len(partial_query) < 2:
            return suggestions
        
        # Suggest channels
        visible_ids = SearchRepository._get_visible_channel_ids(workspace, user)
        channels = Channel.objects.filter(
            id__in=visible_ids,
            name__icontains=partial_query
        ).values('id', 'name', 'channel_type')[:5]
        suggestions['channels'] = list(channels)
        
        # Suggest users
        users = User.objects.filter(
            workspace_memberships__workspace=workspace,
            workspace_memberships__is_active=True,
            is_active=True
        ).filter(
            Q(display_name__icontains=partial_query) |
            Q(username__icontains=partial_query) |
            Q(first_name__icontains=partial_query) |
            Q(last_name__icontains=partial_query)
        ).values('id', 'display_name', 'username', 'avatar_url')[:5]
        suggestions['users'] = list(users)
        
        return suggestions
    
    @staticmethod
    def count_search_results(
        workspace: Workspace,
        user: User,
        query: str
    ) -> dict:
        """
        Get quick count of search results across different types.
        Used for showing tabs with counts (e.g., "Messages (42)").
        """
        visible_channel_ids = SearchRepository._get_visible_channel_ids(workspace, user)
        
        if not visible_channel_ids:
            return {'messages': 0, 'people': 0, 'files': 0}
        
        # Message count
        message_count = Message.objects.filter(
            channel_id__in=visible_channel_ids,
            is_deleted=False,
            content__icontains=query
        ).count() if query else 0
        
        # People count
        people_count = WorkspaceMembership.objects.filter(
            workspace=workspace,
            is_active=True
        ).filter(
            Q(user__display_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query)
        ).count() if query else 0
        
        # File count (messages with attachments matching query)
        file_count = Message.objects.filter(
            channel_id__in=visible_channel_ids,
            is_deleted=False,
            attachments__isnull=False,
            content__icontains=query
        ).count() if query else 0
        
        return {
            'messages': message_count,
            'people': people_count,
            'files': file_count
        }
