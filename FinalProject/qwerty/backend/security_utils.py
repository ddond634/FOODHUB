"""
Security Utilities and Input Validation
Provides comprehensive security functions for the e-commerce platform
"""
import re
from functools import wraps
from flask import request, jsonify
import time
from collections import defaultdict
from datetime import datetime, timedelta

# Rate limiting storage (in-memory, use Redis in production)
request_counts = defaultdict(lambda: {'count': 0, 'reset_time': time.time()})

class SecurityValidator:
    """Centralized security validation"""
    
    @staticmethod
    def sanitize_input(text, max_length=1000):
        """Sanitize text input to prevent XSS"""
        if not text:
            return ""
        
        text = str(text)[:max_length]
        
        # Remove potentially dangerous characters
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onload\s*=',
            r'<iframe',
            r'eval\(',
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email or len(email) > 254:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        """Validate Philippine phone number"""
        if not phone:
            return False
        
        # Remove spaces and dashes
        phone = re.sub(r'[\s-]', '', phone)
        
        # Philippine format: +63XXXXXXXXXX or 09XXXXXXXXX or 9XXXXXXXXX
        patterns = [
            r'^\+639\d{9}$',
            r'^09\d{9}$',
            r'^9\d{9}$',
        ]
        
        return any(re.match(pattern, phone) for pattern in patterns)
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength
        Returns: (is_valid, message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password is too long (max 128 characters)"
        
        # Check for at least one uppercase
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check for at least one lowercase
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong"
    
    @staticmethod
    def validate_price(price):
        """Validate product price"""
        try:
            price = float(price)
            if price < 0:
                return False, "Price cannot be negative"
            if price > 1000000:
                return False, "Price is too high"
            return True, price
        except (ValueError, TypeError):
            return False, "Invalid price format"
    
    @staticmethod
    def validate_stock(stock):
        """Validate stock quantity"""
        try:
            stock = int(stock)
            if stock < 0:
                return False, "Stock cannot be negative"
            if stock > 1000000:
                return False, "Stock quantity is too high"
            return True, stock
        except (ValueError, TypeError):
            return False, "Invalid stock format"
    
    @staticmethod
    def validate_sql_safe(text):
        """Check for SQL injection patterns"""
        if not text:
            return True
        
        dangerous_sql = [
            r'\bDROP\b',
            r'\bDELETE\b.*\bFROM\b',
            r'\bUPDATE\b.*\bSET\b',
            r'\bINSERT\b.*\bINTO\b',
            r'--',
            r';.*\bDROP\b',
            r'\bUNION\b.*\bSELECT\b',
            r'\bEXEC\b',
            r'\bEXECUTE\b',
        ]
        
        for pattern in dangerous_sql:
            if re.search(pattern, str(text), re.IGNORECASE):
                return False
        
        return True


def rate_limit(max_requests=100, window_seconds=60):
    """
    Rate limiting decorator
    Args:
        max_requests: Maximum requests allowed in the time window
        window_seconds: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client identifier (IP or user ID)
            client_id = request.remote_addr
            
            # Get or create request tracker
            tracker = request_counts[client_id]
            current_time = time.time()
            
            # Reset counter if window has passed
            if current_time > tracker['reset_time']:
                tracker['count'] = 0
                tracker['reset_time'] = current_time + window_seconds
            
            # Check rate limit
            if tracker['count'] >= max_requests:
                return jsonify({
                    'success': False,
                    'message': 'Rate limit exceeded. Please try again later.',
                    'retry_after': int(tracker['reset_time'] - current_time)
                }), 429
            
            # Increment counter
            tracker['count'] += 1
            
            return f(*args, **kwargs)
        return wrapped
    return decorator


def validate_file_upload(file, allowed_extensions=None, max_size_mb=5):
    """
    Validate uploaded file
    Args:
        file: FileStorage object
        allowed_extensions: Set of allowed extensions (e.g., {'jpg', 'png'})
        max_size_mb: Maximum file size in megabytes
    Returns:
        (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
    
    if not file.filename:
        return False, "No filename provided"
    
    # Check if file has an extension
    if '.' not in file.filename:
        return False, "File must have an extension"
    
    # Get extension
    ext = file.filename.rsplit('.', 1)[1].lower()
    
    # Validate extension
    if allowed_extensions and ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if size > max_size_bytes:
        return False, f"File too large. Maximum size: {max_size_mb}MB"
    
    if size == 0:
        return False, "File is empty"
    
    return True, None


def validate_date_range(start_date, end_date):
    """Validate date range"""
    try:
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        if start_date > end_date:
            return False, "Start date must be before end date"
        
        # Check if dates are not too far in the future
        max_future = datetime.now() + timedelta(days=3650)  # 10 years
        if start_date > max_future or end_date > max_future:
            return False, "Date is too far in the future"
        
        return True, None
    except (ValueError, AttributeError):
        return False, "Invalid date format"


def sanitize_order_data(data):
    """Sanitize order data before processing"""
    sanitized = {}
    
    # Customer info
    if 'customer' in data:
        customer = data['customer']
        sanitized['customer'] = {
            'name': SecurityValidator.sanitize_input(customer.get('name', ''), 100),
            'phone': SecurityValidator.sanitize_input(customer.get('phone', ''), 20),
            'address': SecurityValidator.sanitize_input(customer.get('address', ''), 500)
        }
    
    # Items
    if 'items' in data:
        sanitized['items'] = []
        for item in data['items']:
            sanitized['items'].append({
                'product_id': int(item.get('product_id', 0)),
                'quantity': int(item.get('quantity', 1)),
                'price': float(item.get('price', 0)),
                'title': SecurityValidator.sanitize_input(item.get('title', ''), 200)
            })
    
    # Payment and delivery
    sanitized['payment'] = SecurityValidator.sanitize_input(data.get('payment', ''), 50)
    sanitized['delivery'] = SecurityValidator.sanitize_input(data.get('delivery', ''), 50)
    
    return sanitized


def validate_business_logic(data, validation_type):
    """
    Business logic validation
    Returns: (is_valid, error_message)
    """
    if validation_type == 'order':
        # Validate order
        if not data.get('items') or len(data['items']) == 0:
            return False, "Order must contain at least one item"
        
        if len(data['items']) > 100:
            return False, "Order cannot contain more than 100 items"
        
        for item in data['items']:
            if item.get('quantity', 0) <= 0:
                return False, "Item quantity must be greater than 0"
            if item.get('quantity', 0) > 1000:
                return False, "Item quantity is too high"
            if item.get('price', 0) <= 0:
                return False, "Item price must be greater than 0"
        
        if not data.get('customer', {}).get('name'):
            return False, "Customer name is required"
        
        if not data.get('customer', {}).get('phone'):
            return False, "Customer phone is required"
        
        if not data.get('customer', {}).get('address'):
            return False, "Customer address is required"
    
    elif validation_type == 'product':
        # Validate product
        if not data.get('title') or len(data.get('title', '')) < 3:
            return False, "Product title must be at least 3 characters"
        
        if len(data.get('title', '')) > 200:
            return False, "Product title is too long (max 200 characters)"
        
        is_valid, result = SecurityValidator.validate_price(data.get('price', 0))
        if not is_valid:
            return False, result
        
        is_valid, result = SecurityValidator.validate_stock(data.get('stock', 0))
        if not is_valid:
            return False, result
    
    return True, None


# Export commonly used functions
__all__ = [
    'SecurityValidator',
    'rate_limit',
    'validate_file_upload',
    'validate_date_range',
    'sanitize_order_data',
    'validate_business_logic'
]
