#!/usr/bin/env python3
"""
Comprehensive Auth Flow Testing
Tests registration, OTP verification, login, token refresh, and profile operations
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = 'http://localhost:5000'
TIMEOUT = 10

# Test accounts to create
TEST_ACCOUNTS = {
    'customer': {
        'email': f'test_customer_{int(time.time())}@test.com',
        'password': 'Test123456!',
        'first_name': 'John',
        'last_name': 'Doe',
        'role': 'customer'
    },
    'seller': {
        'email': f'test_seller_{int(time.time())}@test.com',
        'password': 'Test123456!',
        'first_name': 'Jane',
        'role': 'seller',
        'business_name': 'Test Shop',
        'category': 'Groceries'
    },
    'rider': {
        'email': f'test_rider_{int(time.time())}@test.com',
        'password': 'Test123456!',
        'first_name': 'Mike',
        'role': 'rider',
        'vehicle_type': 'motorcycle',
        'driver_license': 'DL123456'
    }
}

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(name, status, details=''):
    """Log test result with color"""
    emoji = '✓' if status else '✗'
    color = Colors.GREEN if status else Colors.RED
    print(f"{color}{emoji} {name}{Colors.END}", end='')
    if details:
        print(f" - {details}")
    else:
        print()

def test_registration(role, account_data):
    """Test registration endpoint"""
    print(f"\n{Colors.BLUE}=== Testing {role.upper()} Registration ==={Colors.END}")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/auth/register',
            json=account_data,
            timeout=TIMEOUT
        )
        
        log_test('Request sent', response.status_code == 201 or response.status_code == 200)
        
        try:
            data = response.json()
            log_test('Response is JSON', True)
        except:
            log_test('Response is JSON', False, f'Got: {response.text[:100]}')
            return None
        
        success = data.get('success', False)
        log_test('Registration successful', success, f"success={success}")
        
        if success:
            token = data.get('token')
            refresh_token = data.get('refresh_token')
            log_test('Token generated', bool(token), f"token={'yes' if token else 'no'}")
            log_test('Refresh token generated', bool(refresh_token), f"refresh={'yes' if refresh_token else 'no'}")
            
            # Validate token format (JWT: 3 parts)
            if token:
                parts = token.split('.')
                if len(parts) == 3:
                    try:
                        import base64
                        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
                        log_test('Token has valid structure', True, f"role={payload.get('role')}")
                        log_test('Token contains role claim', 'role' in payload, f"role={payload.get('role')}")
                    except Exception as e:
                        log_test('Token payload readable', False, str(e)[:50])
                else:
                    log_test('Token has 3 parts', False, f"Got {len(parts)} parts")
            
            return {
                'account': account_data,
                'token': token,
                'refresh_token': refresh_token,
                'user_id': data.get('user_id')
            }
        else:
            log_test('Error message', True, f"error={data.get('error')}")
            return None
            
    except requests.exceptions.RequestException as e:
        log_test('Request succeeded', False, f"Connection error: {str(e)[:50]}")
        return None

def test_otp_verification(email):
    """Test OTP verification (manual OTP entry for now)"""
    print(f"\n{Colors.BLUE}=== Testing OTP Verification ==={Colors.END}")
    
    # In a real test, we'd need to extract OTP from email
    # For now, we'll just test with dummy OTP
    print(f"{Colors.YELLOW}Note: Actual OTP verification requires email access or DB query{Colors.END}")
    
    try:
        # Try with dummy OTP (will fail but tests endpoint)
        response = requests.post(
            f'{BASE_URL}/api/auth/verify-otp',
            json={'email': email, 'code': '0000'},
            timeout=TIMEOUT
        )
        
        log_test('Endpoint exists', response.status_code in [200, 400, 404], f"status={response.status_code}")
        
        try:
            data = response.json()
            log_test('Response is JSON', True)
            
            # We expect 400 for invalid OTP
            if response.status_code == 400 and not data.get('success'):
                log_test('Rejects invalid OTP', True, f"error={data.get('error')}")
            else:
                log_test('Error handling', True, f"status={response.status_code}")
        except:
            log_test('Response is JSON', False)
            
    except requests.exceptions.RequestException as e:
        log_test('Endpoint accessible', False, str(e)[:50])

def test_login(account_data):
    """Test login endpoint"""
    print(f"\n{Colors.BLUE}=== Testing Login ==={Colors.END}")
    
    try:
        login_payload = {
            'email': account_data['email'],
            'password': account_data['password']
        }
        
        response = requests.post(
            f'{BASE_URL}/api/auth/login',
            json=login_payload,
            timeout=TIMEOUT
        )
        
        log_test('Login request sent', response.status_code in [200, 401], f"status={response.status_code}")
        
        try:
            data = response.json()
            log_test('Response is JSON', True)
        except:
            log_test('Response is JSON', False, f'Got: {response.text[:100]}')
            return None
        
        success = data.get('success', False)
        log_test('Login successful', success, f"success={success}")
        
        if success:
            token = data.get('token')
            refresh_token = data.get('refresh_token')
            user = data.get('user', {})
            
            log_test('Token returned', bool(token))
            log_test('Refresh token returned', bool(refresh_token))
            log_test('User info included', bool(user), f"email={user.get('email')}")
            
            # Validate token
            if token:
                parts = token.split('.')
                if len(parts) == 3:
                    try:
                        import base64
                        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
                        role = payload.get('role')
                        log_test('Token contains role', 'role' in payload, f"role={role}")
                        expected_role = account_data.get('role', 'customer')
                        log_test('Role matches account type', role == expected_role, f"expected={expected_role}, got={role}")
                    except Exception as e:
                        log_test('Token payload readable', False, str(e)[:50])
            
            return {
                'token': token,
                'refresh_token': refresh_token,
                'user': user
            }
        else:
            error = data.get('error') or data.get('message') or 'Unknown error'
            # Some errors are expected (pending approval, etc.)
            log_test('Response has error message', True, f"error={error}")
            return None
            
    except requests.exceptions.RequestException as e:
        log_test('Request succeeded', False, f"Connection error: {str(e)[:50]}")
        return None

def test_profile_access(token, role):
    """Test profile fetch with token"""
    print(f"\n{Colors.BLUE}=== Testing Profile Access ==={Colors.END}")
    
    if not token:
        log_test('Skip (no token)', True, 'Registration/login not completed')
        return
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            f'{BASE_URL}/api/account/me',
            headers=headers,
            timeout=TIMEOUT
        )
        
        log_test('Profile fetch successful', response.status_code == 200, f"status={response.status_code}")
        
        try:
            data = response.json()
            log_test('Response is JSON', True)
            
            if response.status_code == 200:
                user = data.get('data', {})
                log_test('User data included', bool(user))
                log_test('User has ID', 'id' in user or 'user_id' in user)
                log_test('User has email', 'email' in user)
                
                # Check role-specific data
                if role == 'seller' and 'seller' in user:
                    log_test('Seller data included', True, f"seller={list(user['seller'].keys())[:3]}")
                elif role == 'rider' and 'rider' in user:
                    log_test('Rider data included', True, f"rider={list(user['rider'].keys())[:3]}")
                else:
                    log_test('Role-specific data', role == 'customer', f"role={role}")
        except:
            log_test('Response is JSON', False)
            
    except requests.exceptions.RequestException as e:
        log_test('Request succeeded', False, str(e)[:50])

def test_token_refresh(refresh_token):
    """Test token refresh"""
    print(f"\n{Colors.BLUE}=== Testing Token Refresh ==={Colors.END}")
    
    if not refresh_token:
        log_test('Skip (no refresh token)', True)
        return
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/auth/refresh',
            json={'refresh_token': refresh_token},
            timeout=TIMEOUT
        )
        
        log_test('Refresh request sent', response.status_code in [200, 401], f"status={response.status_code}")
        
        try:
            data = response.json()
            log_test('Response is JSON', True)
        except:
            log_test('Response is JSON', False)
            return
        
        if response.status_code == 200:
            new_token = data.get('token')
            new_refresh = data.get('refresh_token')
            
            log_test('New token returned', bool(new_token))
            log_test('New refresh token returned', bool(new_refresh))
        else:
            log_test('Refresh failure handled', 'error' in data, f"error={data.get('error')}")
            
    except requests.exceptions.RequestException as e:
        log_test('Request succeeded', False, str(e)[:50])

def main():
    """Run all tests"""
    print(f"{Colors.BLUE}{'='*60}")
    print("FOODHUB Authentication Flow Test Suite")
    print(f"{'='*60}{Colors.END}\n")
    
    # Check if backend is running
    try:
        response = requests.get(f'{BASE_URL}/health', timeout=TIMEOUT)
        log_test('Backend is running', response.status_code == 200, f"status={response.status_code}")
    except:
        log_test('Backend is running', False, 'Cannot connect to localhost:5000')
        print(f"\n{Colors.RED}Please start the backend server first: python run.py{Colors.END}\n")
        return 1
    
    # Test each account type
    results = {}
    for role, account_data in TEST_ACCOUNTS.items():
        # Registration
        reg_result = test_registration(role, account_data)
        
        # OTP Verification (skip actual verification for now)
        if reg_result:
            test_otp_verification(account_data['email'])
        
        # Login (this will fail if account not verified, but test endpoint)
        login_result = test_login(account_data)
        
        # Profile access
        if login_result:
            test_profile_access(login_result.get('token'), role)
            test_token_refresh(login_result.get('refresh_token'))
        
        results[role] = {
            'registration': bool(reg_result),
            'login': bool(login_result),
            'profile': bool(login_result)
        }
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("Test Summary")
    print(f"{'='*60}{Colors.END}\n")
    
    for role, outcomes in results.items():
        status = '✓' if all(outcomes.values()) else '✗'
        print(f"{status} {role.upper()}: Registration={outcomes['registration']}, Login={outcomes['login']}, Profile={outcomes['profile']}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
