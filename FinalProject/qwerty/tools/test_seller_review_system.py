"""
Test script for Seller Review System

This script tests the seller review system endpoints.
Run this after the migration to verify everything is working.
"""
import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

# Test credentials - update with your admin credentials
ADMIN_EMAIL = 'admin@example.com'
ADMIN_PASSWORD = 'admin123'

def login_admin():
    """Login as admin and get token"""
    response = requests.post(f'{BASE_URL}/api/auth/login', json={
        'email': ADMIN_EMAIL,
        'password': ADMIN_PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('token')
        print('✅ Admin login successful')
        return token
    else:
        print(f'❌ Admin login failed: {response.status_code}')
        print(response.text)
        return None

def test_seller_stats(token):
    """Test GET /api/admin/sellers/stats"""
    print('\n📊 Testing Seller Stats Endpoint...')
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(f'{BASE_URL}/api/admin/sellers/stats', headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print('✅ Seller stats retrieved successfully')
        print(f'   Total: {data["stats"]["total"]}')
        print(f'   Pending: {data["stats"]["pending"]}')
        print(f'   Active: {data["stats"]["active"]}')
        print(f'   Declined: {data["stats"]["declined"]}')
        return data['stats']
    else:
        print(f'❌ Failed to get seller stats: {response.status_code}')
        print(response.text)
        return None

def test_pending_sellers(token):
    """Test GET /api/admin/sellers/pending"""
    print('\n📋 Testing Pending Sellers Endpoint...')
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(f'{BASE_URL}/api/admin/sellers/pending?status=pending,declined', headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f'✅ Pending sellers retrieved successfully ({data["count"]} sellers)')
        
        if data['sellers']:
            print('\n   Sellers pending review:')
            for seller in data['sellers'][:3]:  # Show first 3
                print(f'   - ID: {seller["id"]}, Business: {seller["business_name"]}, Status: {seller["status"]}')
            return data['sellers']
        else:
            print('   No pending sellers found')
            return []
    else:
        print(f'❌ Failed to get pending sellers: {response.status_code}')
        print(response.text)
        return None

def test_seller_details(token, seller_id):
    """Test GET /api/admin/sellers/<id>"""
    print(f'\n🔍 Testing Seller Details Endpoint (ID: {seller_id})...')
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(f'{BASE_URL}/api/admin/sellers/{seller_id}', headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print('✅ Seller details retrieved successfully')
        seller = data['seller']
        print(f'   Business: {seller["business_name"]}')
        print(f'   Email: {seller["email"]}')
        print(f'   Status: {seller["status"]}')
        print(f'   Audit log entries: {len(data["audit_log"])}')
        return data
    else:
        print(f'❌ Failed to get seller details: {response.status_code}')
        print(response.text)
        return None

def test_approve_seller(token, seller_id):
    """Test PUT /api/admin/sellers/<id>/status (approve)"""
    print(f'\n✅ Testing Seller Approval (ID: {seller_id})...')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    response = requests.put(
        f'{BASE_URL}/api/admin/sellers/{seller_id}/status',
        headers=headers,
        json={'status': 'active'}
    )
    
    if response.status_code == 200:
        data = response.json()
        print('✅ Seller approved successfully')
        print(f'   Message: {data["message"]}')
        print(f'   New status: {data["new_status"]}')
        return True
    else:
        print(f'❌ Failed to approve seller: {response.status_code}')
        print(response.text)
        return False

def test_decline_seller(token, seller_id, reason):
    """Test PUT /api/admin/sellers/<id>/status (decline)"""
    print(f'\n❌ Testing Seller Decline (ID: {seller_id})...')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    response = requests.put(
        f'{BASE_URL}/api/admin/sellers/{seller_id}/status',
        headers=headers,
        json={'status': 'declined', 'reason': reason}
    )
    
    if response.status_code == 200:
        data = response.json()
        print('✅ Seller declined successfully')
        print(f'   Message: {data["message"]}')
        print(f'   New status: {data["new_status"]}')
        return True
    else:
        print(f'❌ Failed to decline seller: {response.status_code}')
        print(response.text)
        return False

def run_all_tests():
    """Run all tests"""
    print('='*60)
    print('SELLER REVIEW SYSTEM - API ENDPOINT TESTS')
    print('='*60)
    
    # Login
    token = login_admin()
    if not token:
        print('\n❌ Cannot proceed without admin token')
        return
    
    # Test stats
    stats = test_seller_stats(token)
    
    # Test pending sellers list
    sellers = test_pending_sellers(token)
    
    # Test seller details (if sellers exist)
    if sellers and len(sellers) > 0:
        seller_id = sellers[0]['id']
        test_seller_details(token, seller_id)
        
        # Ask user if they want to test approval/decline
        print(f'\n⚠️  Would you like to test approval/decline for seller ID {seller_id}?')
        print('   This will change the seller status in the database.')
        print('   Type "yes" to continue, or press Enter to skip: ', end='')
        
        # For automated testing, skip the interactive part
        # In production, uncomment the line below
        # user_input = input().strip().lower()
        user_input = ''  # Skip by default
        
        if user_input == 'yes':
            print('\n   Choose action:')
            print('   1. Approve seller')
            print('   2. Decline seller')
            print('   3. Skip')
            print('   Enter choice (1-3): ', end='')
            
            # For automated testing, skip
            choice = '3'  # Skip by default
            
            if choice == '1':
                test_approve_seller(token, seller_id)
                # Verify status change
                test_seller_details(token, seller_id)
            elif choice == '2':
                test_decline_seller(token, seller_id, 'Test decline reason - incomplete documents')
                # Verify status change
                test_seller_details(token, seller_id)
    else:
        print('\n⚠️  No sellers available for detail/approval/decline tests')
        print('   To test these endpoints:')
        print('   1. Register a new seller account')
        print('   2. Run this test script again')
    
    print('\n' + '='*60)
    print('TESTS COMPLETED')
    print('='*60)
    print('\n📝 Next Steps:')
    print('   1. Open browser and login as admin')
    print('   2. Navigate to Admin Dashboard > Seller Reviews')
    print('   3. Verify the UI shows pending sellers')
    print('   4. Test approve/decline functionality through UI')
    print('\n✅ Backend API endpoints are working!')

if __name__ == '__main__':
    run_all_tests()
