"""
Workspace Views - API Layer
API endpoints for workspace operations.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter

from api.serializers.workspace_serializers import (
    WorkspaceSerializer,
    WorkspaceCreateSerializer,
    WorkspaceUpdateSerializer,
    WorkspaceListSerializer,
    WorkspaceMembershipSerializer,
    WorkspaceMemberUpdateSerializer,
    WorkspaceInviteSerializer,
    WorkspaceInviteCreateSerializer,
    JoinByInviteCodeSerializer,
    AcceptInviteSerializer,
    TransferOwnershipSerializer
)
from services.workspace_service import WorkspaceService, WorkspaceError, PermissionError
from repository.workspace_repository import WorkspaceRepository
from repository.user_repository import UserRepository


class WorkspaceListView(APIView):
    """View for listing and creating workspaces."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspaces'],
        summary='List my workspaces',
        description='Get a list of all workspaces where the current user is a member.',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='List of workspaces',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'count': 2,
                            'workspaces': [
                                {
                                    'id': 1,
                                    'name': 'Engineering Team',
                                    'slug': 'engineering-team',
                                    'description': 'Our engineering workspace',
                                    'icon_url': '',
                                    'is_public': False,
                                    'member_count': 5,
                                    'user_role': 'owner',
                                    'created_at': '2024-01-01T00:00:00Z'
                                }
                            ]
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request):
        """Get list of user's workspaces."""
        workspaces = WorkspaceService.list_user_workspaces(request.user)
        serializer = WorkspaceListSerializer(
            workspaces, 
            many=True,
            context={'request': request}
        )
        return Response({
            'count': len(workspaces),
            'workspaces': serializer.data
        })
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Create workspace',
        description='Create a new workspace. The creator automatically becomes the owner.',
        request=WorkspaceCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=dict,
                description='Workspace created successfully',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'Workspace created successfully',
                            'workspace': {
                                'id': 1,
                                'name': 'Engineering Team',
                                'slug': 'engineering-team',
                                'description': 'Our engineering workspace',
                                'owner': {'id': 1, 'email': 'user@example.com'},
                                'is_public': False,
                                'invite_code': 'AbCdEfGh12345678'
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request):
        """Create a new workspace."""
        serializer = WorkspaceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            workspace = WorkspaceService.create_workspace(
                name=serializer.validated_data['name'],
                owner=request.user,
                description=serializer.validated_data.get('description', ''),
                is_public=serializer.validated_data.get('is_public', False)
            )
            return Response({
                'message': 'Workspace created successfully',
                'workspace': WorkspaceSerializer(workspace, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceSearchView(APIView):
    """View for searching workspaces."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Search workspaces',
        description='Search workspaces by name or description.',
        parameters=[
            OpenApiParameter(
                name='q',
                description='Search query string',
                required=False,
                type=str
            )
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Search results'
            ),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request):
        """Search workspaces."""
        query = request.query_params.get('q', '')
        workspaces = WorkspaceService.search_workspaces(query, request.user)
        serializer = WorkspaceListSerializer(
            workspaces,
            many=True,
            context={'request': request}
        )
        return Response({
            'count': len(workspaces),
            'workspaces': serializer.data
        })


class WorkspaceDetailView(APIView):
    """View for workspace details."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Get workspace details',
        description='Get detailed information about a specific workspace.',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Workspace details'
            ),
            403: OpenApiResponse(description='Not a member of this workspace'),
            404: OpenApiResponse(description='Workspace not found'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request, workspace_id):
        """Get workspace details."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            serializer = WorkspaceSerializer(workspace, context={'request': request})
            return Response({'workspace': serializer.data})
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Update workspace',
        description='Update workspace settings (admin only).',
        request=WorkspaceUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Workspace updated'
            ),
            403: OpenApiResponse(description='Admin permission required'),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def put(self, request, workspace_id):
        """Update workspace."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            serializer = WorkspaceUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            workspace = WorkspaceService.update_workspace(
                workspace,
                request.user,
                **serializer.validated_data
            )
            return Response({
                'message': 'Workspace updated successfully',
                'workspace': WorkspaceSerializer(workspace, context={'request': request}).data
            })
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Delete workspace',
        description='Delete a workspace (owner only).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Workspace deleted'
            ),
            403: OpenApiResponse(description='Owner permission required'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def delete(self, request, workspace_id):
        """Delete workspace."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            WorkspaceService.delete_workspace(workspace, request.user)
            return Response({
                'message': 'Workspace deleted successfully'
            })
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceJoinView(APIView):
    """View for joining workspace."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Join workspace by invite code',
        description='Join a workspace using its invite code.',
        request=JoinByInviteCodeSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Joined workspace successfully'
            ),
            404: OpenApiResponse(description='Invalid invite code'),
            400: OpenApiResponse(description='Already a member or invalid code'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request):
        """Join workspace by invite code."""
        serializer = JoinByInviteCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        code = serializer.validated_data['invite_code']
        workspace = WorkspaceRepository.get_by_invite_code(code)
        
        if not workspace:
            return Response(
                {'error': 'Invalid invite code'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            membership = WorkspaceService.join_by_invite_code(
                workspace, request.user, code
            )
            return Response({
                'message': 'Joined workspace successfully',
                'workspace': WorkspaceListSerializer(workspace, context={'request': request}).data
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceMemberListView(APIView):
    """View for workspace members."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Members'],
        summary='List workspace members',
        description='Get a list of all members in a workspace.',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='List of members'
            ),
            403: OpenApiResponse(description='Not a member of this workspace'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request, workspace_id):
        """Get workspace members."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            members = WorkspaceService.get_workspace_members(workspace, request.user)
            serializer = WorkspaceMembershipSerializer(members, many=True)
            return Response({
                'count': len(members),
                'members': serializer.data
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class WorkspaceMemberDetailView(APIView):
    """View for workspace member operations."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Members'],
        summary='Update member role',
        description='Update a member role (owner only).',
        request=WorkspaceMemberUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Member role updated'
            ),
            403: OpenApiResponse(description='Owner permission required'),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def put(self, request, workspace_id, member_id):
        """Update member role."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            serializer = WorkspaceMemberUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            membership = WorkspaceService.update_member_role(
                workspace,
                member_id,
                serializer.validated_data['role'],
                request.user
            )
            return Response({
                'message': 'Member role updated',
                'member': WorkspaceMembershipSerializer(membership).data
            })
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Workspace Members'],
        summary='Remove member',
        description='Remove a member from the workspace (admin+).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Member removed'
            ),
            403: OpenApiResponse(description='Admin permission required'),
            400: OpenApiResponse(description='Cannot remove owner'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def delete(self, request, workspace_id, member_id):
        """Remove member from workspace."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            WorkspaceService.remove_member(workspace, member_id, request.user)
            return Response({
                'message': 'Member removed successfully'
            })
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceLeaveView(APIView):
    """View for leaving a workspace."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Members'],
        summary='Leave workspace',
        description='Leave a workspace (owner must transfer ownership first).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Left workspace successfully'
            ),
            400: OpenApiResponse(description='Owner cannot leave without transferring ownership'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request, workspace_id):
        """Leave workspace."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            WorkspaceService.leave_workspace(workspace, request.user)
            return Response({
                'message': 'Left workspace successfully'
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceInviteListView(APIView):
    """View for workspace invites."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Invites'],
        summary='List pending invites',
        description='Get pending invites for a workspace (admin+).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='List of pending invites'
            ),
            403: OpenApiResponse(description='Admin permission required'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request, workspace_id):
        """Get pending invites."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            invites = WorkspaceService.get_pending_invites(workspace, request.user)
            serializer = WorkspaceInviteSerializer(invites, many=True)
            return Response({
                'count': len(invites),
                'invites': serializer.data
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        tags=['Workspace Invites'],
        summary='Invite user by email',
        description='Send an invitation to join the workspace (admin+).',
        request=WorkspaceInviteCreateSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Invitation sent'
            ),
            403: OpenApiResponse(description='Admin permission required'),
            400: OpenApiResponse(description='User already a member'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request, workspace_id):
        """Invite user by email."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            serializer = WorkspaceInviteCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            invite, is_new = WorkspaceService.invite_by_email(
                workspace,
                serializer.validated_data['email'],
                request.user
            )
            
            message = 'Invitation sent' if is_new else 'Invitation refreshed'
            return Response({
                'message': message,
                'invite': WorkspaceInviteSerializer(invite).data
            })
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceInviteCancelView(APIView):
    """View for canceling invites."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Invites'],
        summary='Cancel invitation',
        description='Cancel a pending invitation (admin+).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Invitation cancelled'
            ),
            403: OpenApiResponse(description='Admin permission required'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request, workspace_id, invite_id):
        """Cancel a pending invite."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            WorkspaceService.cancel_invite(workspace, invite_id, request.user)
            return Response({
                'message': 'Invitation cancelled'
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


class WorkspaceInviteAcceptView(APIView):
    """View for accepting invites."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Invites'],
        summary='Accept invitation',
        description='Accept a workspace invitation using the invite token.',
        request=AcceptInviteSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Joined workspace successfully'
            ),
            400: OpenApiResponse(description='Invalid or expired invitation'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request):
        """Accept workspace invitation."""
        serializer = AcceptInviteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            workspace = WorkspaceService.accept_invite(
                serializer.validated_data['token'],
                request.user
            )
            return Response({
                'message': 'Joined workspace successfully',
                'workspace': WorkspaceListSerializer(workspace, context={'request': request}).data
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceInviteDeclineView(APIView):
    """View for declining invites."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Invites'],
        summary='Decline invitation',
        description='Decline a workspace invitation.',
        request=AcceptInviteSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Invitation declined'
            ),
            400: OpenApiResponse(description='Invalid invitation'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request):
        """Decline workspace invitation."""
        serializer = AcceptInviteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = WorkspaceService.decline_invite(
            serializer.validated_data['token'],
            request.user
        )
        
        if success:
            return Response({'message': 'Invitation declined'})
        return Response(
            {'error': 'Invalid invitation'},
            status=status.HTTP_400_BAD_REQUEST
        )


class UserPendingInvitesView(APIView):
    """View for user's pending invites."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspace Invites'],
        summary='Get my pending invites',
        description='Get all pending workspace invitations for the current user.',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='List of pending invites'
            ),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request):
        """Get pending invites for current user."""
        invites = WorkspaceRepository.get_user_pending_invites(request.user)
        serializer = WorkspaceInviteSerializer(invites, many=True)
        return Response({
            'count': len(invites),
            'invites': serializer.data
        })


class WorkspaceTransferOwnershipView(APIView):
    """View for transferring workspace ownership."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Transfer ownership',
        description='Transfer workspace ownership to another member (owner only).',
        request=TransferOwnershipSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Ownership transferred successfully'
            ),
            403: OpenApiResponse(description='Owner permission required'),
            400: OpenApiResponse(description='New owner must be a member'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request, workspace_id):
        """Transfer ownership to another member."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            serializer = TransferOwnershipSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            workspace = WorkspaceService.transfer_ownership(
                workspace,
                serializer.validated_data['new_owner_id'],
                request.user
            )
            return Response({
                'message': 'Ownership transferred successfully',
                'workspace': WorkspaceSerializer(workspace, context={'request': request}).data
            })
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkspaceRegenerateInviteCodeView(APIView):
    """View for regenerating invite code."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Workspaces'],
        summary='Regenerate invite code',
        description='Generate a new invite code for the workspace (admin+).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='New invite code generated',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'Invite code regenerated',
                            'invite_code': 'NewAbCdEfGh12345678',
                            'expires_at': '2024-02-01T00:00:00Z'
                        }
                    )
                ]
            ),
            403: OpenApiResponse(description='Admin permission required'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request, workspace_id):
        """Regenerate workspace invite code."""
        try:
            workspace = WorkspaceService.get_workspace_detail(workspace_id, request.user)
            if not workspace.can_manage(request.user):
                return Response(
                    {'error': 'Only admins can regenerate invite code'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            new_code = workspace.regenerate_invite_code()
            return Response({
                'message': 'Invite code regenerated',
                'invite_code': new_code,
                'expires_at': workspace.invite_code_expires_at
            })
        except WorkspaceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
