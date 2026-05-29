"""Input validation utilities for Hub API."""
import re
from typing import Tuple

def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False, 'Email is required'
    
    email = email.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, 'Invalid email format'
    
    if len(email) > 255:
        return False, 'Email is too long'
    
    return True, ''

def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
    if not password or not isinstance(password, str):
        return False, 'Password is required'
    
    if len(password) < 6:
        return False, 'Password must be at least 6 characters'
    
    if len(password) > 128:
        return False, 'Password is too long'
    
    return True, ''

def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate Philippine phone number."""
    if not phone or not isinstance(phone, str):
        return False, 'Phone number is required'
    
    phone = phone.replace(' ', '').replace('-', '')
    
    # Accept formats: 09XXXXXXXXX, +639XXXXXXXXX, 639XXXXXXXXX
    if re.match(r'^(\+63|63)?9\d{9}$', phone) or re.match(r'^09\d{9}$', phone):
        return True, ''
    
    return False, 'Invalid Philippine phone number'

def validate_name(name: str, field_name: str = 'Name') -> Tuple[bool, str]:
    """Validate name field."""
    if not name or not isinstance(name, str):
        return False, f'{field_name} is required'
    
    name = name.strip()
    
    if len(name) < 2:
        return False, f'{field_name} must be at least 2 characters'
    
    if len(name) > 100:
        return False, f'{field_name} is too long'
    
    # Allow letters, spaces, hyphens, and apostrophes
    if not re.match(r"^[a-zA-Z\s'-]+$", name):
        return False, f'{field_name} contains invalid characters'
    
    return True, ''

def validate_business_name(name: str) -> Tuple[bool, str]:
    """Validate business name."""
    if not name or not isinstance(name, str):
        return False, 'Business name is required'
    
    name = name.strip()
    
    if len(name) < 3:
        return False, 'Business name must be at least 3 characters'
    
    if len(name) > 150:
        return False, 'Business name is too long'
    
    return True, ''

def validate_url(url: str) -> Tuple[bool, str]:
    """Validate URL format."""
    if not url or not isinstance(url, str):
        return False, 'URL is required'
    
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    
    if not re.match(url_pattern, url):
        return False, 'Invalid URL format'
    
    return True, ''

def validate_product_title(title: str) -> Tuple[bool, str]:
    """Validate product title."""
    if not title or not isinstance(title, str):
        return False, 'Product title is required'
    
    title = title.strip()
    
    if len(title) < 3:
        return False, 'Product title must be at least 3 characters'
    
    if len(title) > 200:
        return False, 'Product title is too long'
    
    return True, ''

def validate_price(price) -> Tuple[bool, str]:
    """Validate product price."""
    try:
        price = float(price)
        
        if price < 0:
            return False, 'Price cannot be negative'
        
        if price > 999999.99:
            return False, 'Price is too high'
        
        return True, ''
    except (TypeError, ValueError):
        return False, 'Invalid price format'

def validate_quantity(quantity) -> Tuple[bool, str]:
    """Validate product quantity."""
    try:
        quantity = int(quantity)
        
        if quantity < 0:
            return False, 'Quantity cannot be negative'
        
        if quantity > 999999:
            return False, 'Quantity is too high'
        
        return True, ''
    except (TypeError, ValueError):
        return False, 'Invalid quantity format'

def validate_address(address: str) -> Tuple[bool, str]:
    """Validate address."""
    if not address or not isinstance(address, str):
        return False, 'Address is required'
    
    address = address.strip()
    
    if len(address) < 5:
        return False, 'Address is too short'
    
    if len(address) > 255:
        return False, 'Address is too long'
    
    return True, ''

def validate_role(role: str) -> Tuple[bool, str]:
    """Validate user role."""
    valid_roles = ['customer', 'seller', 'rider', 'admin']
    
    if not role or role not in valid_roles:
        return False, f'Invalid role. Must be one of: {", ".join(valid_roles)}'
    
    return True, ''

def validate_order_status(status: str) -> Tuple[bool, str]:
    """Validate order status."""
    valid_statuses = ['placed', 'processing', 'dispatched', 'delivered', 'cancelled']
    
    if not status or status not in valid_statuses:
        return False, f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
    
    return True, ''

def validate_otp(otp: str) -> Tuple[bool, str]:
    """Validate OTP format."""
    if not otp or not isinstance(otp, str):
        return False, 'OTP is required'
    
    if not otp.isdigit() or len(otp) != 6:
        return False, 'OTP must be 6 digits'
    
    return True, ''

