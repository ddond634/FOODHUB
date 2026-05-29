#!/usr/bin/env python3
"""
Script to create test accounts for sellers and riders.
This script calls the admin API endpoint to create dummy accounts.
"""

import requests
import json
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration
BASE_URL = "http://127.0.0.1:5000"
ADMIN_EMAIL = "admin@hub.local"
ADMIN_PASSWORD = "admin123"

def login_as_admin():
    """Login as admin and get the token"""
    login_url = f"{BASE_URL}/api/auth/login"
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            data = response.json()
            return data.get('token')
        else:
            print(f"Login failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error during login: {e}")
        return None

def create_test_accounts(token):
    """Create test accounts using the admin endpoint"""
    create_url = f"{BASE_URL}/api/admin/create-test-accounts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(create_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully created test accounts!")
            print(f"\n📊 Summary:")
            print(f"   - Sellers created: {len(data.get('accounts', {}).get('sellers', []))}")
            print(f"   - Riders created: {len(data.get('accounts', {}).get('riders', []))}")
            
            print(f"\n🏪 Seller Accounts:")
            for seller in data.get('accounts', {}).get('sellers', []):
                print(f"   - Email: {seller['email']}")
                print(f"     Password: {seller['password']}")
                print(f"     Business: {seller['business_name']}")
                print(f"     User ID: {seller['user_id']}\n")
            
            print(f"🚴 Rider Accounts:")
            for rider in data.get('accounts', {}).get('riders', []):
                print(f"   - Email: {rider['email']}")
                print(f"     Password: {rider['password']}")
                print(f"     Vehicle: {rider['vehicle_type']}")
                print(f"     User ID: {rider['user_id']}\n")
            
            return True
        else:
            print(f"❌ Failed to create accounts: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error creating accounts: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Creating test accounts for admin actions testing...\n")
    
    # Login as admin
    print("🔐 Logging in as admin...")
    token = login_as_admin()
    
    if not token:
        print("❌ Failed to login. Please check your admin credentials.")
        sys.exit(1)
    
    print("✅ Login successful!\n")
    
    # Create test accounts
    print("👥 Creating test accounts...")
    success = create_test_accounts(token)
    
    if success:
        print("\n✨ All done! You can now test admin actions on these accounts.")
        print("\n💡 Tip: Use these accounts in the admin dashboard to test:")
        print("   - Warning actions")
        print("   - Suspension actions")
        print("   - Ban actions")
    else:
        print("\n❌ Failed to create test accounts.")
        sys.exit(1)

