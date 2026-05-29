"""JWT token utilities and role-based access control for the Hub API."""
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g

# Secret key for JWT signing - MUST be set in production
_jwt_secret = os.environ.get('JWT_SECRET')
if not _jwt_secret:
    import sys
    if 'pytest' not in sys.modules and os.environ.get('ENV', 'dev') == 'prod':
        raise RuntimeError('JWT_SECRET environment variable MUST be set in production')
    _jwt_secret = 'dev-jwt-secret-change-in-prod'  # Development only
JWT_SECRET = _jwt_secret
JWT_EXPIRY_HOURS = 24
REFRESH_TOKEN_EXP_DAYS = int(os.environ.get('REFRESH_TOKEN_EXP_DAYS', '30'))

def generate_token(user_id, role, email):
    """Generate JWT token for a user."""
    payload = {
        'user_id': user_id,
        'role': role,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

def generate_access_token(user_id, role, email):
    """Compatibility wrapper: generate access JWT token."""
    return generate_token(user_id, role, email)

def verify_token(token):
    """Verify and decode JWT token; return payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_token_from_request():
    """Extract JWT token from Authorization header or cookies."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    # Optionally check cookies
    return request.cookies.get('token')

def token_required(f):
    """Decorator to require valid JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({'error': 'unauthorized', 'message': 'No token provided'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'unauthorized', 'message': 'Invalid or expired token'}), 401
        
        # Store user info in Flask's g object for this request
        g.user_id = payload.get('user_id')
        g.role = payload.get('role')
        g.email = payload.get('email')
        
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    """Decorator to require specific role(s)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return jsonify({'error': 'unauthorized', 'message': 'No token provided'}), 401
            
            payload = verify_token(token)
            if not payload:
                return jsonify({'error': 'unauthorized', 'message': 'Invalid or expired token'}), 401
            
            user_role = payload.get('role')
            if user_role not in roles:
                return jsonify({'error': 'forbidden', 'message': f'Role {user_role} not permitted'}), 403
            
            # Store user info in Flask's g object
            g.user_id = payload.get('user_id')
            g.role = user_role
            g.email = payload.get('email')
            
            return f(*args, **kwargs)
        return decorated
    return decorator
