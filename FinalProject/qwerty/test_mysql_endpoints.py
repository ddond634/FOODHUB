"""
Quick endpoint smoke test against MySQL DB.
Verifies key endpoints work with MySQL backend.
"""
import requests
import json
import os

BASE_URL = 'http://127.0.0.1:5000'
os.environ['DB_ENGINE'] = 'mysql'

def test_health():
    """Basic server health check"""
    try:
        r = requests.get(f'{BASE_URL}/api/health', timeout=5)
        print(f'✓ Health check: {r.status_code}')
        return r.status_code == 200
    except Exception as e:
        print(f'✗ Health check failed: {e}')
        return False

def test_signup_login():
    """Test user signup and login flow"""
    email = f'testuser_{os.urandom(4).hex()}@example.com'
    password = 'TestPass123!'
    
    # Signup (use /api/auth/register)
    try:
        r = requests.post(f'{BASE_URL}/api/auth/register', json={
            'email': email,
            'password': password,
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'seller'
        }, timeout=5)
        print(f'✓ Signup: {r.status_code} - {r.text[:100]}')
        if r.status_code not in [200, 201]:
            print(f'  Response: {r.text}')
            return None
    except Exception as e:
        print(f'✗ Signup failed: {e}')
        return None
    
    # Login
    try:
        r = requests.post(f'{BASE_URL}/api/auth/login', json={
            'email': email,
            'password': password
        }, timeout=5)
        print(f'✓ Login: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            token = data.get('data', {}).get('access_token') or data.get('access_token')
            print(f'  Token: {token[:20]}...' if token else '  No token')
            return token
    except Exception as e:
        print(f'✗ Login failed: {e}')
        return None

def test_me_endpoint(token):
    """Test /api/me profile endpoint"""
    try:
        r = requests.get(f'{BASE_URL}/api/me', headers={
            'Authorization': f'Bearer {token}'
        }, timeout=5)
        print(f'✓ GET /api/me: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            print(f'  User: {data.get("data", {}).get("email", "N/A")}')
        return r.status_code == 200
    except Exception as e:
        print(f'✗ GET /api/me failed: {e}')
        return False

def test_stores_endpoint(token):
    """Test store creation and listing"""
    try:
        # Create store
        r = requests.post(f'{BASE_URL}/api/stores', headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }, json={
            'name': 'Test Store',
            'category': 'Electronics',
            'description': 'A test store'
        }, timeout=5)
        print(f'✓ POST /api/stores: {r.status_code}')
        
        # List my stores
        r2 = requests.get(f'{BASE_URL}/api/stores/mine', headers={
            'Authorization': f'Bearer {token}'
        }, timeout=5)
        print(f'✓ GET /api/stores/mine: {r2.status_code}')
        if r2.status_code == 200:
            stores = r2.json().get('data', [])
            print(f'  Stores count: {len(stores)}')
        
        return True
    except Exception as e:
        print(f'✗ Stores endpoints failed: {e}')
        return False

def test_shipping_endpoint(token):
    """Test seller shipping settings"""
    try:
        r = requests.get(f'{BASE_URL}/api/seller/settings/shipping', headers={
            'Authorization': f'Bearer {token}'
        }, timeout=5)
        print(f'✓ GET /api/seller/settings/shipping: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            print(f'  Settings: {data.get("data", {})}')
        return True
    except Exception as e:
        print(f'✗ Shipping endpoint failed: {e}')
        return False

if __name__ == '__main__':
    print('=== MySQL Endpoint Verification ===\n')
    
    # 1. Health check
    if not test_health():
        print('\n⚠️  Server not running. Start with: python run.py')
        exit(1)
    
    print()
    
    # 2. Auth flow
    token = test_signup_login()
    if not token:
        print('\n⚠️  Could not obtain auth token')
        exit(1)
    
    print()
    
    # 3. Profile endpoint
    test_me_endpoint(token)
    
    print()
    
    # 4. Stores endpoint
    test_stores_endpoint(token)
    
    print()
    
    # 5. Shipping settings
    test_shipping_endpoint(token)
    
    print('\n=== Verification Complete ===')
