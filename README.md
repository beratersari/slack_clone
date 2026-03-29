# Slack Clone Backend

A Django-based backend for a Slack clone application using N-layered architecture.

## Architecture Overview

This project follows N-layered architecture with clear separation of concerns:

```
backend/
├── domain/          # Domain Layer - Entities and models
│   └── models/
│       ├── user.py       # User model with types: Admin, Super User, User
│       └── workspace.py  # Workspace, Membership, Invite models
├── repository/      # Repository Layer - Data access
│   ├── user_repository.py
│   └── workspace_repository.py
├── services/        # Services Layer - Business logic
│   ├── auth_service.py
│   ├── user_service.py
│   └── workspace_service.py
├── api/             # API Layer - Controllers/Presentation
│   ├── serializers/
│   ├── views/
│   ├── authentication.py
│   └── permissions.py
└── config/          # Configuration
    └── settings.py
```

## User Types

1. **Admin** - Full system access, can manage all users and settings
2. **Super User** - Can manage workspaces and users within their scope
3. **User** - Regular user with access to their workspaces and channels

## Workspace Features

- **Create Workspace**: Any user can create a workspace and becomes its owner
- **Invite Members**: Owners and admins can invite users by email
- **Join by Invite Code**: Users can join using workspace invite code
- **Role Management**: Owner can promote/demote members to admin
- **Transfer Ownership**: Owner can transfer ownership to another member
- **Leave Workspace**: Members can leave (owner must transfer ownership first)

## Dummy Users

The following test users are pre-created:

| Type       | Email                     | Password       |
|------------|---------------------------|----------------|
| Admin      | admin@slackclone.com      | Admin@123!     |
| Super User | superuser@slackclone.com  | SuperUser@123! |
| User       | user@slackclone.com       | User@123!      |

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Create dummy users (optional):
```bash
python manage.py create_dummy_users
```

5. Start the development server:
```bash
python manage.py runserver
```

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register/` | Register new user | No |
| POST | `/api/auth/login/` | User login | No |
| POST | `/api/auth/logout/` | User logout | Yes |
| POST | `/api/auth/refresh/` | Refresh access token | No |
| POST | `/api/auth/change-password/` | Change password | Yes |

### User Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/profile/` | Get current user profile | Yes |
| PUT/PATCH | `/api/auth/profile/` | Update profile | Yes |
| GET | `/api/auth/users/` | List users | Yes |
| GET | `/api/auth/users/<id>/` | Get user details | Yes |
| POST | `/api/auth/users/<id>/activate/` | Activate user | Admin only |
| DELETE | `/api/auth/users/<id>/activate/` | Deactivate user | Admin only |

### Workspace Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/workspaces/` | List my workspaces | Yes |
| POST | `/api/auth/workspaces/` | Create workspace | Yes |
| GET | `/api/auth/workspaces/search/` | Search workspaces | Yes |
| GET | `/api/auth/workspaces/<id>/` | Get workspace details | Yes |
| PUT | `/api/auth/workspaces/<id>/` | Update workspace | Admin+ |
| DELETE | `/api/auth/workspaces/<id>/` | Delete workspace | Owner only |
| POST | `/api/auth/workspaces/join/` | Join by invite code | Yes |
| POST | `/api/auth/workspaces/<id>/leave/` | Leave workspace | Yes |

### Workspace Members

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/workspaces/<id>/members/` | List members | Member |
| PUT | `/api/auth/workspaces/<id>/members/<user_id>/` | Update role | Owner only |
| DELETE | `/api/auth/workspaces/<id>/members/<user_id>/` | Remove member | Admin+ |
| POST | `/api/auth/workspaces/<id>/transfer-ownership/` | Transfer ownership | Owner only |

### Workspace Invites

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/workspaces/invites/pending/` | My pending invites | Yes |
| POST | `/api/auth/workspaces/invites/accept/` | Accept invite | Yes |
| POST | `/api/auth/workspaces/invites/decline/` | Decline invite | Yes |
| GET | `/api/auth/workspaces/<id>/invites/` | List pending invites | Admin+ |
| POST | `/api/auth/workspaces/<id>/invites/` | Invite by email | Admin+ |
| POST | `/api/auth/workspaces/<id>/invites/<invite_id>/cancel/` | Cancel invite | Admin+ |
| POST | `/api/auth/workspaces/<id>/regenerate-invite/` | New invite code | Admin+ |

## API Usage Examples

### Register a new user
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "New",
    "last_name": "User"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@slackclone.com",
    "password": "User@123!"
  }'
```

### Create a Workspace
```bash
curl -X POST http://localhost:8000/api/auth/workspaces/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{
    "name": "Engineering Team",
    "description": "Our engineering workspace",
    "is_public": false
  }'
```

### Invite User by Email
```bash
curl -X POST http://localhost:8000/api/auth/workspaces/1/invites/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{
    "email": "colleague@example.com"
  }'
```

### Join Workspace by Invite Code
```bash
curl -X POST http://localhost:8000/api/auth/workspaces/join/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{
    "invite_code": "AbCdEfGh12345678"
  }'
```

### Accept Workspace Invite
```bash
curl -X POST http://localhost:8000/api/auth/workspaces/invites/accept/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{
    "token": "invite_token_here"
  }'
```

### Access protected endpoint
```bash
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer <your_access_token>"
```

## Database

The project uses SQLite3, with the database file located at `backend/db.sqlite3`.

## Django Admin

All models are registered in Django Admin:
- **Users**: Manage users, their types, and status
- **Workspaces**: Manage workspaces and their settings
- **Workspace Memberships**: View and manage member roles
- **Workspace Invites**: Track pending invitations

Access the admin at: `http://localhost:8000/admin/`

Use the admin credentials:
- Email: `admin@slackclone.com`
- Password: `Admin@123!`

## Project Structure

```
/testbed/zed-base/
├── .gitignore           # Git ignore file
├── README.md            # This file
└── backend/             # Backend application
    ├── config/          # Django configuration
    ├── domain/          # Domain layer (models, admin)
    ├── repository/      # Repository layer (data access)
    ├── services/        # Services layer (business logic)
    ├── api/             # API layer (views, serializers)
    ├── db.sqlite3       # SQLite database
    ├── manage.py        # Django management script
    └── requirements.txt # Python dependencies
```

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

## Development

### Running tests
```bash
python manage.py test
```

### Creating a superuser
```bash
python manage.py createsuperuser
```

### Django admin
Access the admin panel at `http://localhost:8000/admin/`

## License

This project is for educational purposes.

## API Documentation (Swagger)

The API is fully documented with Swagger/OpenAPI. You can access the interactive documentation at:

### Swagger UI
**URL:** `http://localhost:8000/api/docs/`

Features:
- Interactive API testing
- Request/response examples
- Authentication with JWT tokens
- Filter and search endpoints

### Redoc (Alternative Documentation)
**URL:** `http://localhost:8000/api/redoc/`

Features:
- Clean, responsive documentation
- Better for reading and reference

### OpenAPI Schema
**URL:** `http://localhost:8000/api/schema/`

Raw OpenAPI 3.0 schema in YAML format.

### Using Swagger UI

1. **Login** to get your JWT token:
   - Go to `POST /api/auth/login/`
   - Enter credentials:
     ```json
     {
       "email": "admin@slackclone.com",
       "password": "Admin@123!"
     }
     ```
   - Click "Execute"

2. **Authorize** with your token:
   - Click the "Authorize" button at the top
   - Enter: `Bearer <your_access_token>`
   - Click "Authorize" and close the dialog

3. **Test endpoints**:
   - All authenticated endpoints will now include your token
   - Try `GET /api/auth/profile/` to see your user info
   - Try `GET /api/auth/workspaces/` to list your workspaces

### API Tags

The API is organized into the following categories:

- **Authentication** - Login, register, logout, password management
- **Users** - User profiles and user management
- **Workspaces** - Workspace CRUD operations
- **Workspace Members** - Member management
- **Workspace Invites** - Invitation system

## Channel Features

The channel system works just like Slack:

### Channel Types

- **Public Channels** (`#general`, `#engineering`) - Any workspace member can join/leave
- **Private Channels** - Invite-only, hidden from non-members
- **Default Channel** (`#general`) - Auto-created with workspace, everyone is in it

### Channel Features

| Feature | Description |
|---------|-------------|
| **Join/Leave** | Join public channels freely, must be invited to private |
| **Archive** | Archive old channels (read-only), except #general |
| **Messages** | Post, edit, and delete messages |
| **Unread Count** | Track unread messages per channel |
| **Mark as Read** | Mark all messages as read |
| **Member List** | See who's in the channel |

### Channel API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/workspaces/<id>/channels/` | List channels |
| POST | `/api/auth/workspaces/<id>/channels/` | Create channel |
| GET | `/api/auth/workspaces/<id>/channels/<channel_id>/` | Channel details |
| PUT | `/api/auth/workspaces/<id>/channels/<channel_id>/` | Update channel |
| DELETE | `/api/auth/workspaces/<id>/channels/<channel_id>/` | Delete channel |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/join/` | Join channel |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/leave/` | Leave channel |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/archive/` | Archive channel |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/unarchive/` | Unarchive channel |
| GET | `/api/auth/workspaces/<id>/channels/<channel_id>/members/` | List members |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/invite/` | Invite to private |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/mark-read/` | Mark as read |

### Message API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/workspaces/<id>/channels/<channel_id>/messages/` | List messages |
| POST | `/api/auth/workspaces/<id>/channels/<channel_id>/messages/` | Post message |
| PUT | `/api/auth/workspaces/<id>/channels/<channel_id>/messages/<msg_id>/` | Edit message |
| DELETE | `/api/auth/workspaces/<id>/channels/<channel_id>/messages/<msg_id>/` | Delete message |

### Channel Usage Examples

**Create a channel:**
```bash
curl -X POST http://localhost:8000/api/auth/workspaces/1/channels/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "engineering-team",
    "channel_type": "public",
    "topic": "Engineering discussions",
    "description": "For all engineering topics"
  }'
```

**Join a channel:**
```bash
curl -X POST http://localhost:8000/api/auth/workspaces/1/channels/2/join/ \
  -H "Authorization: Bearer <token>"
```

**Post a message:**
```bash
curl -X POST http://localhost:8000/api/auth/workspaces/1/channels/2/messages/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "content": "Hello team! How is everyone doing?"
  }'
```

**Get messages:**
```bash
curl "http://localhost:8000/api/auth/workspaces/1/channels/2/messages/?limit=50" \
  -H "Authorization: Bearer <token>"
```

## Updated Project Structure

```
backend/
├── domain/
│   ├── models/
│   │   ├── user.py           # User model
│   │   ├── workspace.py      # Workspace, Membership, Invite
│   │   └── channel.py        # Channel, Membership, Message
│   └── admin.py              # All models in Django admin
├── repository/
│   ├── user_repository.py
│   ├── workspace_repository.py
│   └── channel_repository.py # NEW
├── services/
│   ├── auth_service.py
│   ├── user_service.py
│   ├── workspace_service.py
│   └── channel_service.py    # NEW
├── api/
│   ├── serializers/
│   │   ├── user_serializers.py
│   │   ├── workspace_serializers.py
│   │   └── channel_serializers.py  # NEW
│   └── views/
│       ├── auth_views.py
│       ├── user_views.py
│       ├── workspace_views.py
│       └── channel_views.py  # NEW
```
