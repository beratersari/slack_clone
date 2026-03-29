"""
OpenAPI Schema Extensions
Custom authentication extension for JWT.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """OpenAPI extension for JWT Authentication."""
    target_class = 'api.authentication.JWTAuthentication'
    name = 'Bearer'
    
    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': 'JWT token authentication. Use format: Bearer <your_token>'
        }
