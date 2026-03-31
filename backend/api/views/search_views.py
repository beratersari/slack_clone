"""
Search Views - API Layer
API endpoints for searching messages and people in workspaces.
Similar to Slack's search functionality.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from services.search_service import SearchService, SearchError
from api.serializers.search_serializers import (
    SearchMessageSerializer,
    SearchMemberSerializer,
    SearchDirectMessageSerializer,
    SearchSuggestionsSerializer,
    SearchCountsSerializer,
    SearchUserSerializer
)


class WorkspaceSearchView(APIView):
    """
    Main search endpoint for a workspace.
    Searches both messages and people, returns combined results.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary='Search workspace',
        description='Search messages and people in a workspace. Similar to Slack search.',
        parameters=[
            OpenApiParameter(
                name='q',
                description='Search query string',
                required=True,
                type=str
            ),
            OpenApiParameter(
                name='type',
                description='Search type: messages, people, all',
                required=False,
                type=str,
                default='all'
            ),
            OpenApiParameter(
                name='limit',
                description='Results per page (default 20)',
                required=False,
                type=int,
                default=20
            ),
            OpenApiParameter(
                name='offset',
                description='Pagination offset (default 0)',
                required=False,
                type=int,
                default=0
            ),
            OpenApiParameter(
                name='sort_by',
                description='Sort by: relevance or date',
                required=False,
                type=str,
                default='relevance'
            ),
        ],
        responses={
            200: OpenApiResponse(description='Search results'),
            400: OpenApiResponse(description='Invalid search parameters'),
            403: OpenApiResponse(description='Not a workspace member')
        }
    )
    def get(self, request, workspace_id):
        """Search workspace for messages and/or people."""
        query = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', 'all')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        sort_by = request.query_params.get('sort_by', 'relevance')
        
        # Limit max page size
        limit = min(limit, 100)
        
        if not query:
            return Response(
                {'error': 'Search query (q) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            results = {
                'query': query,
                'workspace_id': workspace_id
            }
            
            if search_type in ['messages', 'all']:
                message_results = SearchService.search_messages(
                    workspace_id=workspace_id,
                    user=request.user,
                    query=query,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by
                )
                results['messages'] = {
                    'count': len(message_results['messages']),
                    'total_count': message_results['total_count'],
                    'has_more': message_results['has_more'],
                    'data': SearchMessageSerializer(
                        message_results['messages'],
                        many=True,
                        context={'request': request}
                    ).data
                }
            
            if search_type in ['people', 'all']:
                people_results = SearchService.search_people(
                    workspace_id=workspace_id,
                    user=request.user,
                    query=query,
                    limit=limit,
                    offset=offset
                )
                results['people'] = {
                    'count': len(people_results['members']),
                    'total_count': people_results['total_count'],
                    'has_more': people_results['has_more'],
                    'data': SearchMemberSerializer(
                        people_results['members'],
                        many=True,
                        context={'request': request}
                    ).data
                }
            
            return Response(results)
            
        except SearchError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class MessageSearchView(APIView):
    """Search messages within a workspace."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary='Search messages',
        description='Search messages in a workspace with advanced filters.',
        parameters=[
            OpenApiParameter(name='q', description='Search query', required=True, type=str),
            OpenApiParameter(name='channel_ids', description='Comma-separated channel IDs', required=False, type=str),
            OpenApiParameter(name='sender_ids', description='Comma-separated user IDs', required=False, type=str),
            OpenApiParameter(name='from_date', description='ISO date (messages from)', required=False, type=str),
            OpenApiParameter(name='to_date', description='ISO date (messages until)', required=False, type=str),
            OpenApiParameter(name='has_files', description='Only messages with files', required=False, type=bool),
            OpenApiParameter(name='in_threads', description='Only thread replies', required=False, type=bool),
            OpenApiParameter(name='sort_by', description='relevance or date', required=False, type=str),
            OpenApiParameter(name='limit', description='Results per page', required=False, type=int),
            OpenApiParameter(name='offset', description='Pagination offset', required=False, type=int),
        ],
        responses={200: OpenApiResponse(description='Message search results')}
    )
    def get(self, request, workspace_id):
        """Search messages with filters."""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'Search query (q) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse channel_ids
        channel_ids = None
        if request.query_params.get('channel_ids'):
            try:
                channel_ids = [int(x) for x in request.query_params['channel_ids'].split(',')]
            except ValueError:
                return Response(
                    {'error': 'Invalid channel_ids format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Parse sender_ids
        sender_ids = None
        if request.query_params.get('sender_ids'):
            try:
                sender_ids = [int(x) for x in request.query_params['sender_ids'].split(',')]
            except ValueError:
                return Response(
                    {'error': 'Invalid sender_ids format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Parse other parameters
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
            offset = int(request.query_params.get('offset', 0))
            sort_by = request.query_params.get('sort_by', 'relevance')
            has_files = request.query_params.get('has_files')
            if has_files is not None:
                has_files = has_files.lower() == 'true'
            in_threads = request.query_params.get('in_threads')
            if in_threads is not None:
                in_threads = in_threads.lower() == 'true'
            
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            
        except ValueError as e:
            return Response(
                {'error': f'Invalid parameter: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            results = SearchService.search_messages(
                workspace_id=workspace_id,
                user=request.user,
                query=query,
                channel_ids=channel_ids,
                sender_ids=sender_ids,
                from_date=from_date,
                to_date=to_date,
                has_files=has_files,
                in_threads=in_threads,
                limit=limit,
                offset=offset,
                sort_by=sort_by
            )
            
            return Response({
                'count': len(results['messages']),
                'total_count': results['total_count'],
                'messages': SearchMessageSerializer(
                    results['messages'],
                    many=True,
                    context={'request': request}
                ).data,
                'has_more': results['has_more'],
                'query': query,
                'limit': limit,
                'offset': offset
            })
            
        except SearchError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PeopleSearchView(APIView):
    """Search people (members) within a workspace."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary='Search people',
        description='Search workspace members by name, email, or username.',
        parameters=[
            OpenApiParameter(name='q', description='Search query', required=True, type=str),
            OpenApiParameter(name='role', description='Filter by role: owner, admin, member', required=False, type=str),
            OpenApiParameter(name='online_only', description='Only show recently active users', required=False, type=bool),
            OpenApiParameter(name='limit', description='Results per page', required=False, type=int),
            OpenApiParameter(name='offset', description='Pagination offset', required=False, type=int),
        ],
        responses={200: OpenApiResponse(description='People search results')}
    )
    def get(self, request, workspace_id):
        """Search people."""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'Search query (q) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
            offset = int(request.query_params.get('offset', 0))
            role = request.query_params.get('role')
            online_only = request.query_params.get('online_only', 'false').lower() == 'true'
            
        except ValueError as e:
            return Response(
                {'error': f'Invalid parameter: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            results = SearchService.search_people(
                workspace_id=workspace_id,
                user=request.user,
                query=query,
                limit=limit,
                offset=offset,
                role=role,
                online_only=online_only
            )
            
            return Response({
                'count': len(results['members']),
                'total_count': results['total_count'],
                'members': SearchMemberSerializer(
                    results['members'],
                    many=True,
                    context={'request': request}
                ).data,
                'has_more': results['has_more'],
                'query': query,
                'limit': limit,
                'offset': offset
            })
            
        except SearchError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DMSearchView(APIView):
    """Search direct messages within a workspace."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary='Search direct messages',
        description='Search DMs in a workspace.',
        parameters=[
            OpenApiParameter(name='q', description='Search query', required=True, type=str),
            OpenApiParameter(name='limit', description='Results per page', required=False, type=int),
            OpenApiParameter(name='offset', description='Pagination offset', required=False, type=int),
        ],
        responses={200: OpenApiResponse(description='DM search results')}
    )
    def get(self, request, workspace_id):
        """Search direct messages."""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'Search query (q) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
            offset = int(request.query_params.get('offset', 0))
            
        except ValueError as e:
            return Response(
                {'error': f'Invalid parameter: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            results = SearchService.search_direct_messages(
                workspace_id=workspace_id,
                user=request.user,
                query=query,
                limit=limit,
                offset=offset
            )
            
            return Response({
                'count': len(results['messages']),
                'total_count': results['total_count'],
                'messages': SearchDirectMessageSerializer(
                    results['messages'],
                    many=True,
                    context={'request': request}
                ).data,
                'has_more': results['has_more'],
                'query': query,
                'limit': limit,
                'offset': offset
            })
            
        except SearchError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SearchSuggestionsView(APIView):
    """Get search suggestions for autocomplete."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary='Get search suggestions',
        description='Get autocomplete suggestions for channels and users.',
        parameters=[
            OpenApiParameter(name='q', description='Partial query', required=True, type=str),
        ],
        responses={200: OpenApiResponse(response=SearchSuggestionsSerializer)}
    )
    def get(self, request, workspace_id):
        """Get search suggestions."""
        partial_query = request.query_params.get('q', '').strip()
        
        if len(partial_query) < 2:
            return Response({
                'channels': [],
                'users': [],
                'recent_searches': []
            })
        
        try:
            suggestions = SearchService.get_search_suggestions(
                workspace_id=workspace_id,
                user=request.user,
                partial_query=partial_query
            )
            
            return Response(suggestions)
            
        except SearchError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SearchCountsView(APIView):
    """Get quick counts for search result tabs."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary='Get search counts',
        description='Get counts of results for messages, people, files tabs.',
        parameters=[
            OpenApiParameter(name='q', description='Search query', required=True, type=str),
        ],
        responses={200: OpenApiResponse(response=SearchCountsSerializer)}
    )
    def get(self, request, workspace_id):
        """Get search result counts."""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({
                'messages': 0,
                'people': 0,
                'files': 0
            })
        
        try:
            counts = SearchService.get_search_counts(
                workspace_id=workspace_id,
                user=request.user,
                query=query
            )
            
            return Response(counts)
            
        except SearchError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class GlobalUserSearchView(APIView):
    """Global user search (for finding users to invite, etc.)."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Search'],
        summary='Global user search',
        description='Search all users (for inviting to workspaces, etc.).',
        parameters=[
            OpenApiParameter(name='q', description='Search query', required=True, type=str),
            OpenApiParameter(name='limit', description='Results per page', required=False, type=int),
            OpenApiParameter(name='offset', description='Pagination offset', required=False, type=int),
        ],
        responses={200: OpenApiResponse(description='User search results')}
    )
    def get(self, request):
        """Global user search."""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'Search query (q) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
            offset = int(request.query_params.get('offset', 0))
            
        except ValueError as e:
            return Response(
                {'error': f'Invalid parameter: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            results = SearchService.search_users_global(
                user=request.user,
                query=query,
                limit=limit,
                offset=offset
            )
            
            return Response({
                'count': len(results['users']),
                'total_count': results['total_count'],
                'users': SearchUserSerializer(
                    results['users'],
                    many=True,
                    context={'request': request}
                ).data,
                'has_more': results['has_more'],
                'query': query,
                'limit': limit,
                'offset': offset
            })
            
        except SearchError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
