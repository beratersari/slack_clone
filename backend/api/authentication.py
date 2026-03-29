"""
JWT Authentication - API Layer
Custom JWT authentication for Django REST Framework.
"""
from rest_framework import authentication, exceptions
from services.auth_service import AuthService


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT Authentication class.
    Validates JWT tokens from the Authorization header.
    """
    keyword = 'Bearer'
    
    def authenticate(self, request):
        """Authenticate the request and return user and token."""
        auth_header = authentication.get_authorization_header(request).split()
        
        if not auth_header or auth_header[0].lower() != self.keyword.lower().encode():
            return None
        
        if len(auth_header) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth_header) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)
        
        try:
            token = auth_header[1].decode('utf-8')
        except UnicodeError:
            msg = 'Invalid token header. Token string should not contain invalid characters.'
            raise exceptions.AuthenticationFailed(msg)
        
        return self.authenticate_credentials(token)
    
    def authenticate_credentials(self, token):
        """Validate the token and return user."""
        try:
            payload = AuthService.verify_token(token)
        except Exception as e:
            raise exceptions.AuthenticationFailed(str(e))
        
        user_id = payload.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Invalid token payload')
        
        user = AuthService.get_user_from_token(token)
        
        if not user:
            raise exceptions.AuthenticationFailed('User not found')
        
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User account is disabled')
        
        return (user, token)
    
    def authenticate_header(self, request):
        """Return the authentication header keyword."""
        return self.keyword
