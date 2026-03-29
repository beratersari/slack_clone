"""
API URL Configuration
URL patterns for the API layer.
"""
from django.urls import path

from api.views.auth_views import (
    RegisterView,
    LoginView,
    LogoutView,
    RefreshTokenView,
    ChangePasswordView
)
from api.views.user_views import (
    UserProfileView,
    UserListView,
    UserDetailView,
    UserActivateView
)
from api.views.workspace_views import (
    WorkspaceListView,
    WorkspaceSearchView,
    WorkspaceDetailView,
    WorkspaceJoinView,
    WorkspaceMemberListView,
    WorkspaceMemberDetailView,
    WorkspaceLeaveView,
    WorkspaceInviteListView,
    WorkspaceInviteCancelView,
    WorkspaceInviteAcceptView,
    WorkspaceInviteDeclineView,
    UserPendingInvitesView,
    WorkspaceTransferOwnershipView,
    WorkspaceRegenerateInviteCodeView
)
from api.views.channel_views import (
    ChannelListView,
    ChannelDetailView,
    ChannelArchiveView,
    ChannelUnarchiveView,
    ChannelJoinView,
    ChannelLeaveView,
    ChannelMemberListView,
    ChannelInviteView,
    ChannelMarkReadView,
    MessageListView,
    MessageDetailView
)

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh-token'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # User endpoints
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:user_id>/activate/', UserActivateView.as_view(), name='user-activate'),
    
    # Workspace endpoints
    path('workspaces/', WorkspaceListView.as_view(), name='workspace-list'),
    path('workspaces/search/', WorkspaceSearchView.as_view(), name='workspace-search'),
    path('workspaces/join/', WorkspaceJoinView.as_view(), name='workspace-join'),
    path('workspaces/invites/pending/', UserPendingInvitesView.as_view(), name='user-pending-invites'),
    path('workspaces/invites/accept/', WorkspaceInviteAcceptView.as_view(), name='workspace-invite-accept'),
    path('workspaces/invites/decline/', WorkspaceInviteDeclineView.as_view(), name='workspace-invite-decline'),
    path('workspaces/<int:workspace_id>/', WorkspaceDetailView.as_view(), name='workspace-detail'),
    path('workspaces/<int:workspace_id>/members/', WorkspaceMemberListView.as_view(), name='workspace-members'),
    path('workspaces/<int:workspace_id>/members/<int:member_id>/', WorkspaceMemberDetailView.as_view(), name='workspace-member-detail'),
    path('workspaces/<int:workspace_id>/leave/', WorkspaceLeaveView.as_view(), name='workspace-leave'),
    path('workspaces/<int:workspace_id>/invites/', WorkspaceInviteListView.as_view(), name='workspace-invites'),
    path('workspaces/<int:workspace_id>/invites/<int:invite_id>/cancel/', WorkspaceInviteCancelView.as_view(), name='workspace-invite-cancel'),
    path('workspaces/<int:workspace_id>/transfer-ownership/', WorkspaceTransferOwnershipView.as_view(), name='workspace-transfer-ownership'),
    path('workspaces/<int:workspace_id>/regenerate-invite/', WorkspaceRegenerateInviteCodeView.as_view(), name='workspace-regenerate-invite'),
    
    # Channel endpoints
    path('workspaces/<int:workspace_id>/channels/', ChannelListView.as_view(), name='channel-list'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/', ChannelDetailView.as_view(), name='channel-detail'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/archive/', ChannelArchiveView.as_view(), name='channel-archive'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/unarchive/', ChannelUnarchiveView.as_view(), name='channel-unarchive'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/join/', ChannelJoinView.as_view(), name='channel-join'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/leave/', ChannelLeaveView.as_view(), name='channel-leave'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/members/', ChannelMemberListView.as_view(), name='channel-members'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/invite/', ChannelInviteView.as_view(), name='channel-invite'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/mark-read/', ChannelMarkReadView.as_view(), name='channel-mark-read'),
    
    # Message endpoints
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('workspaces/<int:workspace_id>/channels/<int:channel_id>/messages/<int:message_id>/', MessageDetailView.as_view(), name='message-detail'),
]
