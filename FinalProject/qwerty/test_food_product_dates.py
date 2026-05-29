"""
Test script to verify manufacture_date and expiry_date functionality for food/beverage products
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

def test_product_with_dates():
    print("\n=== Testing Product Creation with Manufacture and Expiry Dates ===\n")
    
    # First, login as a seller (you'll need to have a verified seller account)
    # For this test, we'll assume you're logged in and have a token
    # Replace this with actual login
    
    print("Please login as a seller in your browser first.")
    token = input("Enter your authentication token (from browser dev tools, localStorage.getItem('token')): ").strip()
    
    if not token:
        print("❌ No token provided. Exiting test.")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: Create product with dates
    print("\n📝 Test 1: Creating product with manufacture and expiry dates...")
    product_data = {
        'title': 'Fresh Orange Juice',
        'description': 'Freshly squeezed orange juice, 100% natural',
        'price': 75.00,
        'stock': 50,
        'category': 'Beverages',
        'img_url': 'https://example.com/orange-juice.jpg',
        'manufacture_date': '2024-12-01',
        'expiry_date': '2024-12-15'
    }
    
    response = requests.post(f'{BASE_URL}/api/sellers/products', 
                            json=product_data, 
                            headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Product created successfully!")
        print(f"   Product ID: {data.get('data', {}).get('product_id')}")
        print(f"   Title: {data.get('data', {}).get('title')}")
        product_id = data.get('data', {}).get('product_id')
    else:
        print(f"❌ Failed to create product: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    # Test 2: Retrieve the product to verify dates were saved
    print("\n📖 Test 2: Retrieving product to verify dates...")
    response = requests.get(f'{BASE_URL}/api/products/{product_id}')
    
    if response.status_code == 200:
        data = response.json()
        product = data.get('product', {})
        print(f"✅ Product retrieved successfully!")
        print(f"   Title: {product.get('title')}")
        print(f"   Manufacture Date: {product.get('manufacture_date')}")
        print(f"   Expiry Date: {product.get('expiry_date')}")
        
        if product.get('manufacture_date') == '2024-12-01':
            print("   ✅ Manufacture date matches")
        else:
            print(f"   ❌ Manufacture date mismatch: expected '2024-12-01', got '{product.get('manufacture_date')}'")
            
        if product.get('expiry_date') == '2024-12-15':
            print("   ✅ Expiry date matches")
        else:
            print(f"   ❌ Expiry date mismatch: expected '2024-12-15', got '{product.get('expiry_date')}'")
    else:
        print(f"❌ Failed to retrieve product: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    # Test 3: Update product dates
    print("\n🔄 Test 3: Updating product dates...")
    update_data = {
        'manufacture_date': '2024-12-05',
        'expiry_date': '2024-12-20'
    }
    
    response = requests.put(f'{BASE_URL}/api/sellers/products/{product_id}',
                           json=update_data,
                           headers=headers)
    
    if response.status_code == 200:
        print("✅ Product dates updated successfully!")
        
        # Verify the update
        response = requests.get(f'{BASE_URL}/api/products/{product_id}')
        if response.status_code == 200:
            data = response.json()
            product = data.get('product', {})
            print(f"   New Manufacture Date: {product.get('manufacture_date')}")
            print(f"   New Expiry Date: {product.get('expiry_date')}")
            
            if product.get('manufacture_date') == '2024-12-05':
                print("   ✅ Updated manufacture date matches")
            else:
                print(f"   ❌ Manufacture date update failed")
                
            if product.get('expiry_date') == '2024-12-20':
                print("   ✅ Updated expiry date matches")
            else:
                print(f"   ❌ Expiry date update failed")
    else:
        print(f"❌ Failed to update product: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test 4: Create product without dates (should work - dates are optional)
    print("\n📝 Test 4: Creating product WITHOUT dates (optional fields)...")
    product_data_no_dates = {
        'title': 'Generic Snack',
        'description': 'A generic snack product',
        'price': 25.00,
        'stock': 100,
        'category': 'Snacks'
    }
    
    response = requests.post(f'{BASE_URL}/api/sellers/products',
                            json=product_data_no_dates,
                            headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Product without dates created successfully!")
        print(f"   Product ID: {data.get('data', {}).get('product_id')}")
        print(f"   Title: {data.get('data', {}).get('title')}")
    else:
        print(f"❌ Failed to create product without dates: {response.status_code}")
        print(f"   Response: {response.text}")
    
    print("\n=== All Tests Completed ===\n")

if __name__ == '__main__':
    test_product_with_dates()
