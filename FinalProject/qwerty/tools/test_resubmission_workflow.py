"""
Test Script for Resubmission Workflow
Tests all API endpoints and database functionality
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

# Test credentials
ADMIN_EMAIL = "admin@hub.com"
ADMIN_PASSWORD = "admin123"

SELLER_EMAIL = "pendingseller@hub.com"
SELLER_PASSWORD = "test123"

RIDER_EMAIL = "pendingrider@hub.com"
RIDER_PASSWORD = "test123"

def login(email, password):
    """Login and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data['data']['access_token']
    
    print(f"Login failed for {email}: {response.text}")
    return None

def test_decline_seller(admin_token, seller_id):
    """Test declining a seller with missing requirements"""
    print(f"\n=== Testing Decline Seller (ID: {seller_id}) ===")
    
    response = requests.post(
        f"{BASE_URL}/api/admin/sellers/{seller_id}/decline",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "missing_requirements": [
                "Valid ID (Government-issued)",
                "Business Permit",
                "Profile Photo"
            ],
            "reason": "Test decline - missing critical documents"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_approve_seller(admin_token, seller_id):
    """Test approving a seller"""
    print(f"\n=== Testing Approve Seller (ID: {seller_id}) ===")
    
    response = requests.post(
        f"{BASE_URL}/api/admin/sellers/{seller_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_decline_rider(admin_token, rider_id):
    """Test declining a rider with missing requirements"""
    print(f"\n=== Testing Decline Rider (ID: {rider_id}) ===")
    
    response = requests.post(
        f"{BASE_URL}/api/admin/riders/{rider_id}/decline",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "missing_requirements": [
                "Driver's License",
                "Vehicle OR/CR",
                "Valid ID"
            ],
            "reason": "Test decline - incomplete rider documents"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_approve_rider(admin_token, rider_id):
    """Test approving a rider"""
    print(f"\n=== Testing Approve Rider (ID: {rider_id}) ===")
    
    response = requests.post(
        f"{BASE_URL}/api/admin/riders/{rider_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_get_notifications(user_token):
    """Test getting user notifications"""
    print(f"\n=== Testing Get Notifications ===")
    
    response = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data.get('data', {}).get('notifications', []))} notifications")
        for notif in data.get('data', {}).get('notifications', [])[:3]:
            print(f"  - [{notif['type']}] {notif['title']}")
    return response.status_code == 200

def test_get_user_status(user_token):
    """Test getting user application status"""
    print(f"\n=== Testing Get User Status ===")
    
    response = requests.get(
        f"{BASE_URL}/api/user/status",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    print("=" * 60)
    print("RESUBMISSION WORKFLOW - API TESTING")
    print("=" * 60)
    
    # Login as admin
    print("\n[1/7] Logging in as Admin...")
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin_token:
        print("❌ Admin login failed. Exiting.")
        return
    print("✓ Admin logged in successfully")
    
    # Login as seller
    print("\n[2/7] Logging in as Pending Seller...")
    seller_token = login(SELLER_EMAIL, SELLER_PASSWORD)
    if not seller_token:
        print("❌ Seller login failed. Exiting.")
        return
    print("✓ Seller logged in successfully")
    
    # Test decline seller
    print("\n[3/7] Testing Decline Seller Endpoint...")
    if test_decline_seller(admin_token, 2):  # Seller ID 2
        print("✓ Seller declined successfully")
    else:
        print("❌ Failed to decline seller")
    
    # Test get user status (seller)
    print("\n[4/7] Testing Get User Status (Seller)...")
    if test_get_user_status(seller_token):
        print("✓ User status retrieved")
    else:
        print("❌ Failed to get user status")
    
    # Test get notifications (seller)
    print("\n[5/7] Testing Get Notifications (Seller)...")
    if test_get_notifications(seller_token):
        print("✓ Notifications retrieved")
    else:
        print("❌ Failed to get notifications")
    
    # Login as rider
    print("\n[6/7] Logging in as Pending Rider...")
    rider_token = login(RIDER_EMAIL, RIDER_PASSWORD)
    if not rider_token:
        print("⚠ Rider login failed. Skipping rider tests.")
    else:
        print("✓ Rider logged in successfully")
        
        # Test decline rider
        print("\n[7/7] Testing Decline Rider Endpoint...")
        if test_decline_rider(admin_token, 2):  # Rider ID 2
            print("✓ Rider declined successfully")
        else:
            print("❌ Failed to decline rider")
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print("\nTo approve accounts:")
    print(f"  test_approve_seller(admin_token, 2)")
    print(f"  test_approve_rider(admin_token, 2)")
    print("\nCheck the admin dashboard to see updated statuses!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
