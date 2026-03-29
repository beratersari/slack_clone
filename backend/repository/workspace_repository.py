"""
Workspace Repository - Repository Layer
Handles data access operations for Workspace entities.
"""
from typing import Optional, List
from django.db.models import Q
from domain.models.workspace import Workspace, WorkspaceMembership, WorkspaceInvite, WorkspaceRole
from domain.models.user import User


class WorkspaceRepository:
    """
    Repository for Workspace data access operations.
    Provides abstraction between domain and database.
    """
    
    # ========== Workspace Operations ==========
    
    @staticmethod
    def get_by_id(workspace_id: int) -> Optional[Workspace]:
        """Get workspace by ID."""
        try:
            return Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_slug(slug: str) -> Optional[Workspace]:
        """Get workspace by slug."""
        try:
            return Workspace.objects.get(slug=slug)
        except Workspace.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_invite_code(code: str) -> Optional[Workspace]:
        """Get workspace by invite code."""
        try:
            return Workspace.objects.get(invite_code=code, is_active=True)
        except Workspace.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_active() -> List[Workspace]:
        """Get all active workspaces."""
        return list(Workspace.objects.filter(is_active=True))
    
    @staticmethod
    def get_by_owner(user: User) -> List[Workspace]:
        """Get workspaces owned by a user."""
        return list(Workspace.objects.filter(owner=user, is_active=True))
    
    @staticmethod
    def get_by_member(user: User) -> List[Workspace]:
        """Get workspaces where user is a member."""
        return list(Workspace.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
            is_active=True
        ).distinct())
    
    @staticmethod
    def search(query: str) -> List[Workspace]:
        """Search workspaces by name or description."""
        return list(Workspace.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        ))
    
    @staticmethod
    def create_workspace(name: str, slug: str, owner: User, 
                         description: str = '', is_public: bool = False,
                         **extra_fields) -> Workspace:
        """Create a new workspace."""
        workspace = Workspace.objects.create(
            name=name,
            slug=slug,
            owner=owner,
            description=description,
            is_public=is_public,
            **extra_fields
        )
        # Create owner membership
        WorkspaceRepository.add_member(workspace, owner, WorkspaceRole.OWNER)
        return workspace
    
    @staticmethod
    def update_workspace(workspace: Workspace, **fields) -> Workspace:
        """Update workspace fields."""
        for field, value in fields.items():
            if hasattr(workspace, field):
                setattr(workspace, field, value)
        workspace.save()
        return workspace
    
    @staticmethod
    def delete_workspace(workspace_id: int) -> bool:
        """Soft delete workspace by ID."""
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            workspace.is_active = False
            workspace.save(update_fields=['is_active'])
            return True
        except Workspace.DoesNotExist:
            return False
    
    @staticmethod
    def slug_exists(slug: str) -> bool:
        """Check if workspace slug exists."""
        return Workspace.objects.filter(slug=slug).exists()
    
    # ========== Membership Operations ==========
    
    @staticmethod
    def get_membership(workspace: Workspace, user: User) -> Optional[WorkspaceMembership]:
        """Get membership for a user in a workspace."""
        try:
            return WorkspaceMembership.objects.get(
                workspace=workspace,
                user=user,
                is_active=True
            )
        except WorkspaceMembership.DoesNotExist:
            return None
    
    @staticmethod
    def get_members(workspace: Workspace, role: Optional[str] = None) -> List[WorkspaceMembership]:
        """Get all members of a workspace."""
        queryset = WorkspaceMembership.objects.filter(
            workspace=workspace,
            is_active=True
        )
        if role:
            queryset = queryset.filter(role=role)
        return list(queryset.select_related('user'))
    
    @staticmethod
    def add_member(workspace: Workspace, user: User, 
                   role: str = WorkspaceRole.MEMBER,
                   invited_by: Optional[User] = None) -> WorkspaceMembership:
        """Add a member to a workspace."""
        membership, created = WorkspaceMembership.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={
                'role': role,
                'is_active': True,
                'invited_by': invited_by
            }
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.role = role
            membership.invited_by = invited_by
            membership.save()
        return membership
    
    @staticmethod
    def remove_member(workspace: Workspace, user: User) -> bool:
        """Remove a member from a workspace."""
        try:
            membership = WorkspaceMembership.objects.get(
                workspace=workspace,
                user=user,
                is_active=True
            )
            membership.deactivate()
            return True
        except WorkspaceMembership.DoesNotExist:
            return False
    
    @staticmethod
    def update_member_role(workspace: Workspace, user: User, 
                           role: str) -> Optional[WorkspaceMembership]:
        """Update a member's role."""
        try:
            membership = WorkspaceMembership.objects.get(
                workspace=workspace,
                user=user,
                is_active=True
            )
            membership.role = role
            membership.save(update_fields=['role', 'updated_at'])
            return membership
        except WorkspaceMembership.DoesNotExist:
            return None
    
    @staticmethod
    def is_member(workspace: Workspace, user: User) -> bool:
        """Check if user is a member of workspace."""
        return WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=user,
            is_active=True
        ).exists()
    
    # ========== Invite Operations ==========
    
    @staticmethod
    def get_invite_by_token(token: str) -> Optional[WorkspaceInvite]:
        """Get invite by token."""
        try:
            return WorkspaceInvite.objects.get(token=token)
        except WorkspaceInvite.DoesNotExist:
            return None
    
    @staticmethod
    def get_pending_invites(workspace: Workspace) -> List[WorkspaceInvite]:
        """Get pending invites for a workspace."""
        return list(WorkspaceInvite.objects.filter(
            workspace=workspace,
            status='pending'
        ))
    
    @staticmethod
    def get_user_pending_invites(user: User) -> List[WorkspaceInvite]:
        """Get pending invites for a user by email."""
        return list(WorkspaceInvite.objects.filter(
            email=user.email,
            status='pending'
        ).select_related('workspace'))
    
    @staticmethod
    def create_invite(workspace: Workspace, email: str, 
                      invited_by: User) -> WorkspaceInvite:
        """Create a new workspace invite."""
        invite, created = WorkspaceInvite.objects.get_or_create(
            workspace=workspace,
            email=email.lower(),
            defaults={'invited_by': invited_by}
        )
        if not created:
            # Update expiry for existing invite
            invite.save()  # This regenerates token and expiry
        return invite
    
    @staticmethod
    def cancel_invite(invite_id: int) -> bool:
        """Cancel a pending invite."""
        try:
            invite = WorkspaceInvite.objects.get(id=invite_id, status='pending')
            invite.status = 'expired'
            invite.save()
            return True
        except WorkspaceInvite.DoesNotExist:
            return False
