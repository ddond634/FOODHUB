"""API utilities and custom decorators for Hub."""
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime

def json_response(status='success', data=None, error=None, status_code=200):
    """Create standardized JSON response."""
    response = {
        'status': status,
        'timestamp': datetime.now().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if error is not None:
        response['error'] = error
    
    return jsonify(response), status_code

def success_response(data=None, message=None, status_code=200):
    """Create success response."""
    response = {
        'success': True,
        'timestamp': datetime.now().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return jsonify(response), status_code

def error_response(error, status_code=400):
    """Create error response."""
    return jsonify({
        'success': False,
        'error': error,
        'timestamp': datetime.now().isoformat()
    }), status_code

def validate_json_request(*required_fields):
    """Decorator to validate JSON request and required fields."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check content type
            if not request.is_json:
                return error_response('Content-Type must be application/json', 400)
            
            # Get JSON body
            try:
                body = request.get_json()
            except Exception as e:
                return error_response('Invalid JSON format', 400)
            
            # Check required fields
            if required_fields:
                for field in required_fields:
                    if field not in body or not body[field]:
                        return error_response(f'Missing required field: {field}', 400)
            
            # Store body in request context
            g.json_body = body
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def paginate(default_per_page=20, max_per_page=100):
    """Decorator to handle pagination parameters."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                page = int(request.args.get('page', 1))
                per_page = int(request.args.get('per_page', default_per_page))
                
                # Validate pagination
                if page < 1:
                    page = 1
                
                if per_page < 1:
                    per_page = default_per_page
                
                if per_page > max_per_page:
                    per_page = max_per_page
                
                # Calculate offset
                offset = (page - 1) * per_page
                
                # Store in request context
                g.page = page
                g.per_page = per_page
                g.offset = offset
                
            except ValueError:
                return error_response('Invalid pagination parameters', 400)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def format_row(row):
    """Convert database row to dictionary."""
    if hasattr(row, 'keys'):
        # sqlite3.Row or pymysql.DictCursor
        return dict(row)
    elif isinstance(row, dict):
        return row
    elif isinstance(row, tuple):
        return {'row': row}
    else:
        return str(row)

def format_rows(rows):
    """Convert list of database rows to list of dictionaries."""
    if not rows:
        return []
    
    return [format_row(row) for row in rows]

def paginated_response(items, page, per_page, total):
    """Create paginated response."""
    total_pages = (total + per_page - 1) // per_page
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages
        }
    }

def to_dict(obj):
    """Convert object to dictionary for JSON serialization."""
    if isinstance(obj, dict):
        return obj
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    elif hasattr(obj, 'keys'):  # database row
        return dict(obj)
    else:
        return str(obj)


def get_query_param(name, default=None, cast=str, min_len=None, max_len=1024, allowed=None):
    """Safely read and validate query parameters.

    - Trims whitespace and removes control characters.
    - Optionally casts to `cast` (callable).
    - Enforces min/max length for strings.
    - If `allowed` is provided, ensures value is one of the allowed set.

    Returns the processed value or `default` on invalid input.
    """
    try:
        from flask import request, g
        source = None
        if hasattr(g, 'sanitized_args') and isinstance(g.sanitized_args, dict):
            source = g.sanitized_args
        else:
            source = request.args

        raw = source.get(name, None)
        if raw is None:
            return default

        if isinstance(raw, str):
            # Strip BOM and control chars
            val = raw.strip()
            val = ''.join(ch for ch in val if ord(ch) >= 32)
            if max_len and len(val) > max_len:
                val = val[:max_len]
            if min_len and len(val) < min_len:
                return default
            if allowed and val not in allowed:
                return default
            if cast and cast is not str:
                try:
                    return cast(val)
                except Exception:
                    return default
            return val
        else:
            # Non-string values: try to cast
            if cast:
                try:
                    return cast(raw)
                except Exception:
                    return default
            return raw
    except Exception:
        return default

