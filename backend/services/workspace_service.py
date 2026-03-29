"""
Workspace Service - Services Layer
Handles business logic for workspace operations.
"""
from typing import List, Optional, Tuple
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
from domain.models.workspace import Workspace, WorkspaceMembership, WorkspaceInvite, WorkspaceRole
from domain.models.user import User
from repository.workspace_repository import WorkspaceRepository
from repository.user_repository import UserRepository


class WorkspaceError(Exception):
    """Custom exception for workspace errors."""
    pass


class PermissionError(WorkspaceError):
    """Custom exception for permission errors."""
    pass


class WorkspaceService:
    """
    Service for handling workspace business logic.
    """
    
    # ========== Workspace CRUD ==========
    
    @staticmethod
    def create_workspace(name: str, owner: User, description: str = '',
                         is_public: bool = False, **extra_fields) -> Workspace:
        """
        Create a new workspace.
        
        Args:
            name: Workspace name
            owner: User creating the workspace
            description: Workspace description
            is_public: Whether workspace is public
            
        Returns:
            Created workspace
            
        Raises:
            WorkspaceError: If creation fails
        """
        # Generate unique slug
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while WorkspaceRepository.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        workspace = WorkspaceRepository.create_workspace(
            name=name,
            slug=slug,
            owner=owner,
            description=description,
            is_public=is_public,
            **extra_fields
        )
        
        # Create default #general channel
        from services.channel_service import ChannelService
        ChannelService.create_default_general_channel(workspace, owner)
        
        return workspace
    
    @staticmethod
    def update_workspace(workspace: Workspace, user: User, 
                         **data) -> Workspace:
        """
        Update workspace settings.
        
        Args:
            workspace: Workspace to update
            user: User making the update
            **data: Fields to update
            
        Returns:
            Updated workspace
            
        Raises:
            PermissionError: If user cannot manage workspace
        """
        if not workspace.can_manage(user):
            raise PermissionError("Only workspace admins can update settings")
        
        allowed_fields = ['name', 'description', 'is_public', 
                         'allow_guests', 'icon_url']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        return WorkspaceRepository.update_workspace(workspace, **update_data)
    
    @staticmethod
    def delete_workspace(workspace: Workspace, user: User) -> bool:
        """
        Delete a workspace (soft delete).
        
        Args:
            workspace: Workspace to delete
            user: User requesting deletion
            
        Returns:
            True if deleted
            
        Raises:
            PermissionError: If user is not owner
        """
        if not workspace.is_owner(user):
            raise PermissionError("Only the workspace owner can delete it")
        
        return WorkspaceRepository.delete_workspace(workspace.id)
    
    @staticmethod
    def get_workspace_detail(workspace_id: int, user: User) -> Workspace:
        """
        Get workspace details.
        
        Args:
            workspace_id: Workspace ID
            user: User requesting details
            
        Returns:
            Workspace instance
            
        Raises:
            WorkspaceError: If workspace not found
            PermissionError: If user is not a member
        """
        workspace = WorkspaceRepository.get_by_id(workspace_id)
        if not workspace or not workspace.is_active:
            raise WorkspaceError("Workspace not found")
        
        if not WorkspaceRepository.is_member(workspace, user):
            raise PermissionError("You are not a member of this workspace")
        
        return workspace
    
    @staticmethod
    def list_user_workspaces(user: User) -> List[Workspace]:
        """Get all workspaces where user is a member."""
        return WorkspaceRepository.get_by_member(user)
    
    @staticmethod
    def search_workspaces(query: str, user: User) -> List[Workspace]:
        """
        Search workspaces user has access to.
        
        Args:
            query: Search query
            user: User searching
            
        Returns:
            List of matching workspaces
        """
        if not query or len(query) < 2:
            return []
        
        # Search in user's workspaces and public workspaces
        user_workspaces = WorkspaceRepository.get_by_member(user)
        public_workspaces = [w for w in WorkspaceRepository.search(query) 
                           if w.is_public and w not in user_workspaces]
        
        return user_workspaces + public_workspaces
    
    # ========== Member Management ==========
    
    @staticmethod
    def invite_by_email(workspace: Workspace, email: str, 
                        invited_by: User) -> Tuple[WorkspaceInvite, bool]:
        """
        Invite a user to workspace by email.
        
        Args:
            workspace: Workspace to invite to
            email: Email to invite
            invited_by: User sending the invite
            
        Returns:
            Tuple of (invite, is_new)
            
        Raises:
            PermissionError: If user cannot manage workspace
            WorkspaceError: If invite fails
        """
        if not workspace.can_manage(invited_by):
            raise PermissionError("Only workspace admins can invite members")
        
        email = email.lower().strip()
        
        # Check if user is already a member
        existing_user = UserRepository.get_by_email(email)
        if existing_user and WorkspaceRepository.is_member(workspace, existing_user):
            raise WorkspaceError("User is already a member of this workspace")
        
        # Check for existing pending invite
        existing_invites = WorkspaceRepository.get_pending_invites(workspace)
        for invite in existing_invites:
            if invite.email == email:
                # Refresh existing invite
                invite.save()
                return invite, False
        
        # Create new invite
        invite = WorkspaceRepository.create_invite(workspace, email, invited_by)
        
        # Send invite email (placeholder - configure email backend for production)
        # WorkspaceService._send_invite_email(invite)
        
        return invite, True
    
    @staticmethod
    def accept_invite(token: str, user: User) -> Workspace:
        """
        Accept a workspace invitation.
        
        Args:
            token: Invitation token
            user: User accepting the invite
            
        Returns:
            Workspace joined
            
        Raises:
            WorkspaceError: If invite invalid
        """
        invite = WorkspaceRepository.get_invite_by_token(token)
        if not invite:
            raise WorkspaceError("Invalid invitation")
        
        if invite.email != user.email:
            raise WorkspaceError("This invitation is for a different email address")
        
        if not invite.is_valid():
            raise WorkspaceError("Invitation has expired or been cancelled")
        
        # Add user to workspace
        WorkspaceRepository.add_member(
            invite.workspace, 
            user, 
            WorkspaceRole.MEMBER
        )
        
        # Add user to default #general channel
        from services.channel_service import ChannelService
        from repository.channel_repository import ChannelRepository
        general_channel = ChannelRepository.get_by_workspace_and_name(
            invite.workspace, 'general'
        )
        if general_channel:
            ChannelRepository.add_member(general_channel, user)
        
        # Mark invite as accepted
        invite.accept()
        
        return invite.workspace
    
    @staticmethod
    def decline_invite(token: str, user: User) -> bool:
        """
        Decline a workspace invitation.
        
        Args:
            token: Invitation token
            user: User declining the invite
            
        Returns:
            True if declined
        """
        invite = WorkspaceRepository.get_invite_by_token(token)
        if not invite or invite.email != user.email:
            return False
        
        if not invite.is_valid():
            return False
        
        invite.decline()
        return True
    
    @staticmethod
    def join_by_invite_code(workspace: Workspace, user: User, 
                           code: str) -> WorkspaceMembership:
        """
        Join workspace using invite code.
        
        Args:
            workspace: Workspace to join
            user: User joining
            code: Invite code
            
        Returns:
            Membership
            
        Raises:
            WorkspaceError: If code invalid
        """
        if workspace.invite_code != code:
            raise WorkspaceError("Invalid invite code")
        
        if not workspace.is_invite_code_valid():
            raise WorkspaceError("Invite code has expired")
        
        if WorkspaceRepository.is_member(workspace, user):
            raise WorkspaceError("You are already a member of this workspace")
        
        membership = WorkspaceRepository.add_member(workspace, user, WorkspaceRole.MEMBER)
        
        # Add user to default #general channel
        from repository.channel_repository import ChannelRepository
        general_channel = ChannelRepository.get_by_workspace_and_name(
            workspace, 'general'
        )
        if general_channel:
            ChannelRepository.add_member(general_channel, user)
        
        return membership
    
    @staticmethod
    def remove_member(workspace: Workspace, member_id: int, 
                     removed_by: User) -> bool:
        """
        Remove a member from workspace.
        
        Args:
            workspace: Workspace
            member_id: User ID to remove
            removed_by: User performing the removal
            
        Returns:
            True if removed
            
        Raises:
            PermissionError: If user cannot remove members
        """
        if not workspace.can_manage(removed_by):
            raise PermissionError("Only admins can remove members")
        
        member = UserRepository.get_by_id(member_id)
        if not member:
            raise WorkspaceError("Member not found")
        
        # Cannot remove owner
        if workspace.is_owner(member):
            raise WorkspaceError("Cannot remove the workspace owner")
        
        # Admin can only be removed by owner
        if workspace.is_admin(member) and not workspace.is_owner(removed_by):
            raise PermissionError("Only the owner can remove admins")
        
        return WorkspaceRepository.remove_member(workspace, member)
    
    @staticmethod
    def update_member_role(workspace: Workspace, member_id: int,
                          new_role: str, updated_by: User) -> WorkspaceMembership:
        """
        Update a member's role.
        
        Args:
            workspace: Workspace
            member_id: User ID to update
            new_role: New role (admin/member)
            updated_by: User making the change
            
        Returns:
            Updated membership
        """
        if not workspace.can_manage(updated_by):
            raise PermissionError("Only admins can update member roles")
        
        member = UserRepository.get_by_id(member_id)
        if not member:
            raise WorkspaceError("Member not found")
        
        # Only owner can promote/demote admins
        if new_role == WorkspaceRole.ADMIN or workspace.is_admin(member):
            if not workspace.is_owner(updated_by):
                raise PermissionError("Only the owner can manage admin roles")
        
        # Cannot change owner's role
        if workspace.is_owner(member):
            raise WorkspaceError("Cannot change the owner's role")
        
        membership = WorkspaceRepository.update_member_role(workspace, member, new_role)
        if not membership:
            raise WorkspaceError("Member not found in workspace")
        
        return membership
    
    @staticmethod
    def leave_workspace(workspace: Workspace, user: User) -> bool:
        """
        Leave a workspace.
        
        Args:
            workspace: Workspace to leave
            user: User leaving
            
        Returns:
            True if left
            
        Raises:
            WorkspaceError: If owner tries to leave
        """
        if workspace.is_owner(user):
            raise WorkspaceError("Owner cannot leave workspace. Transfer ownership or delete workspace.")
        
        return WorkspaceRepository.remove_member(workspace, user)
    
    @staticmethod
    def get_workspace_members(workspace: Workspace, 
                              user: User) -> List[WorkspaceMembership]:
        """
        Get all members of a workspace.
        
        Args:
            workspace: Workspace
            user: User requesting members list
            
        Returns:
            List of memberships
        """
        if not WorkspaceRepository.is_member(workspace, user):
            raise PermissionError("You are not a member of this workspace")
        
        return WorkspaceRepository.get_members(workspace)
    
    @staticmethod
    def get_pending_invites(workspace: Workspace, 
                           user: User) -> List[WorkspaceInvite]:
        """
        Get pending invites for a workspace.
        
        Args:
            workspace: Workspace
            user: User requesting invites
            
        Returns:
            List of pending invites
        """
        if not workspace.can_manage(user):
            raise PermissionError("Only admins can view pending invites")
        
        return WorkspaceRepository.get_pending_invites(workspace)
    
    @staticmethod
    def cancel_invite(workspace: Workspace, invite_id: int,
                     cancelled_by: User) -> bool:
        """
        Cancel a pending invitation.
        
        Args:
            workspace: Workspace
            invite_id: Invite ID to cancel
            cancelled_by: User cancelling
            
        Returns:
            True if cancelled
        """
        if not workspace.can_manage(cancelled_by):
            raise PermissionError("Only admins can cancel invites")
        
        return WorkspaceRepository.cancel_invite(invite_id)
    
    @staticmethod
    def transfer_ownership(workspace: Workspace, new_owner_id: int,
                          current_owner: User) -> Workspace:
        """
        Transfer workspace ownership to another member.
        
        Args:
            workspace: Workspace
            new_owner_id: User ID of new owner
            current_owner: Current owner
            
        Returns:
            Updated workspace
        """
        if not workspace.is_owner(current_owner):
            raise PermissionError("Only the owner can transfer ownership")
        
        new_owner = UserRepository.get_by_id(new_owner_id)
        if not new_owner:
            raise WorkspaceError("User not found")
        
        if not WorkspaceRepository.is_member(workspace, new_owner):
            raise WorkspaceError("New owner must be a workspace member")
        
        # Update new owner's membership to owner
        WorkspaceRepository.update_member_role(workspace, new_owner, WorkspaceRole.OWNER)
        
        # Demote current owner to admin
        WorkspaceRepository.update_member_role(workspace, current_owner, WorkspaceRole.ADMIN)
        
        # Update workspace owner
        workspace.owner = new_owner
        workspace.save(update_fields=['owner'])
        
        return workspace
    
    @staticmethod
    def _send_invite_email(invite: WorkspaceInvite):
        """Send invitation email (placeholder)."""
        # TODO: Configure email backend and implement email sending
        # For now, just print to console
        print(f"\n{'='*60}")
        print(f"INVITATION EMAIL")
        print(f"{'='*60}")
        print(f"To: {invite.email}")
        print(f"Subject: You've been invited to join {invite.workspace.name}")
        print(f"\nYou've been invited by {invite.invited_by.get_full_name()} to join")
        print(f"the workspace '{invite.workspace.name}' on Slack Clone.")
        print(f"\nClick here to accept: /api/workspaces/invites/{invite.token}/accept/")
        print(f"{'='*60}\n")
