"""
Enhanced Logging and Error Handling System
Provides structured logging and error tracking
"""
import logging
import traceback
from datetime import datetime
from functools import wraps
from flask import jsonify, request
import os

# Configure logging
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Create formatters
detailed_formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

simple_formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create handlers
def setup_logger(name, log_file, level=logging.INFO):
    """Set up a logger with file and console handlers"""
    handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
    handler.setFormatter(detailed_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger

# Create specific loggers
app_logger = setup_logger('app', 'app.log')
security_logger = setup_logger('security', 'security.log')
error_logger = setup_logger('error', 'errors.log', logging.ERROR)
api_logger = setup_logger('api', 'api.log')
db_logger = setup_logger('database', 'database.log')


class ErrorResponse:
    """Standardized error responses"""
    
    @staticmethod
    def bad_request(message="Bad request", details=None):
        """400 Bad Request"""
        response = {
            'success': False,
            'error': 'BAD_REQUEST',
            'message': message
        }
        if details:
            response['details'] = details
        return jsonify(response), 400
    
    @staticmethod
    def unauthorized(message="Unauthorized access"):
        """401 Unauthorized"""
        return jsonify({
            'success': False,
            'error': 'UNAUTHORIZED',
            'message': message
        }), 401
    
    @staticmethod
    def forbidden(message="Access forbidden"):
        """403 Forbidden"""
        return jsonify({
            'success': False,
            'error': 'FORBIDDEN',
            'message': message
        }), 403
    
    @staticmethod
    def not_found(message="Resource not found"):
        """404 Not Found"""
        return jsonify({
            'success': False,
            'error': 'NOT_FOUND',
            'message': message
        }), 404
    
    @staticmethod
    def conflict(message="Resource conflict"):
        """409 Conflict"""
        return jsonify({
            'success': False,
            'error': 'CONFLICT',
            'message': message
        }), 409
    
    @staticmethod
    def rate_limited(message="Too many requests", retry_after=60):
        """429 Rate Limited"""
        return jsonify({
            'success': False,
            'error': 'RATE_LIMITED',
            'message': message,
            'retry_after': retry_after
        }), 429
    
    @staticmethod
    def server_error(message="Internal server error", error_id=None):
        """500 Internal Server Error"""
        response = {
            'success': False,
            'error': 'SERVER_ERROR',
            'message': message
        }
        if error_id:
            response['error_id'] = error_id
        return jsonify(response), 500
    
    @staticmethod
    def validation_error(message="Validation failed", errors=None):
        """422 Validation Error"""
        response = {
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': message
        }
        if errors:
            response['validation_errors'] = errors
        return jsonify(response), 422


def log_api_request(func):
    """Decorator to log API requests"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Log request
        api_logger.info(f"{request.method} {request.path} - IP: {request.remote_addr}")
        
        if request.is_json and request.method in ['POST', 'PUT', 'PATCH']:
            # Don't log sensitive data
            data = request.get_json()
            safe_data = {k: v for k, v in data.items() 
                        if k not in ['password', 'password_hash', 'token', 'otp_code']}
            if safe_data:
                api_logger.debug(f"Request data: {safe_data}")
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            
            # Log response status
            if isinstance(result, tuple):
                status_code = result[1] if len(result) > 1 else 200
            else:
                status_code = 200
            
            api_logger.info(f"{request.method} {request.path} - Status: {status_code}")
            
            return result
        except Exception as e:
            api_logger.error(f"{request.method} {request.path} - Error: {str(e)}")
            raise
    
    return wrapper


def handle_exceptions(func):
    """Decorator to handle exceptions gracefully"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            error_logger.warning(f"ValueError in {func.__name__}: {str(e)}")
            return ErrorResponse.bad_request(str(e))
        except KeyError as e:
            error_logger.warning(f"KeyError in {func.__name__}: {str(e)}")
            return ErrorResponse.bad_request(f"Missing required field: {str(e)}")
        except PermissionError as e:
            error_logger.warning(f"PermissionError in {func.__name__}: {str(e)}")
            return ErrorResponse.forbidden(str(e))
        except Exception as e:
            # Log full traceback
            error_id = f"ERR_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            error_logger.error(
                f"Unhandled exception in {func.__name__} [ID: {error_id}]:\n"
                f"{traceback.format_exc()}"
            )
            
            # Return generic error to client
            return ErrorResponse.server_error(
                "An unexpected error occurred. Please contact support.",
                error_id=error_id
            )
    
    return wrapper


def log_security_event(event_type, user_id=None, details=None):
    """Log security-related events"""
    message = f"SECURITY EVENT: {event_type}"
    
    if user_id:
        message += f" - User ID: {user_id}"
    
    if details:
        message += f" - Details: {details}"
    
    message += f" - IP: {request.remote_addr if request else 'N/A'}"
    
    security_logger.warning(message)


def log_database_operation(operation, table, details=None):
    """Log database operations"""
    message = f"DB {operation.upper()}: {table}"
    
    if details:
        message += f" - {details}"
    
    db_logger.info(message)


class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message, errors=None):
        self.message = message
        self.errors = errors
        super().__init__(self.message)


class BusinessLogicError(Exception):
    """Custom business logic error"""
    def __init__(self, message, error_code=None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def validate_required_fields(data, required_fields):
    """
    Validate that all required fields are present
    Raises ValidationError if any field is missing
    """
    missing = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing.append(field)
    
    if missing:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing)}",
            errors={'missing_fields': missing}
        )


def safe_db_operation(func):
    """Decorator for safe database operations with rollback"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = None
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # Try to rollback if db connection exists
            if 'db' in locals() and db:
                try:
                    db.rollback()
                    db_logger.warning(f"Database rollback in {func.__name__}")
                except:
                    pass
            
            # Re-raise the exception
            raise
    
    return wrapper


# Export commonly used functions
__all__ = [
    'app_logger',
    'security_logger',
    'error_logger',
    'api_logger',
    'db_logger',
    'ErrorResponse',
    'log_api_request',
    'handle_exceptions',
    'log_security_event',
    'log_database_operation',
    'ValidationError',
    'BusinessLogicError',
    'validate_required_fields',
    'safe_db_operation'
]
