#!/usr/bin/env python3
"""
Test Product Variations API Endpoints
Tests the complete variation workflow: create, read, update, delete, cart, and orders
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = 'http://localhost:5000'
SELLER_EMAIL = 'seller@test.com'
SELLER_PASSWORD = 'password123'
CUSTOMER_EMAIL = 'customer@test.com'
CUSTOMER_PASSWORD = 'password123'

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(success, message, data=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")
    if data:
        print(f"   Data: {json.dumps(data, indent=3)}")

class VariationTester:
    def __init__(self):
        self.seller_token = None
        self.customer_token = None
        self.test_product_id = None
        self.variation_ids = []
        self.cart_item_ids = []
        
    def login_seller(self):
        print_section("1. Seller Authentication")
        try:
            response = requests.post(f'{BASE_URL}/api/auth/login', json={
                'email': SELLER_EMAIL,
                'password': SELLER_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.seller_token = data.get('token')
                print_result(True, "Seller logged in", {'token_preview': self.seller_token[:20] + '...'})
                return True
            else:
                print_result(False, f"Login failed: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def login_customer(self):
        print_section("2. Customer Authentication")
        try:
            response = requests.post(f'{BASE_URL}/api/auth/login', json={
                'email': CUSTOMER_EMAIL,
                'password': CUSTOMER_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.customer_token = data.get('token')
                print_result(True, "Customer logged in", {'token_preview': self.customer_token[:20] + '...'})
                return True
            else:
                print_result(False, f"Login failed: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def get_seller_product(self):
        print_section("3. Get Seller's Product")
        try:
            headers = {'Authorization': f'Bearer {self.seller_token}'}
            response = requests.get(f'{BASE_URL}/api/sellers/products', headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                if products:
                    self.test_product_id = products[0]['id']
                    print_result(True, "Found seller product", {
                        'product_id': self.test_product_id,
                        'title': products[0].get('title'),
                        'stock': products[0].get('stock')
                    })
                    return True
                else:
                    print_result(False, "No products found for seller")
                    return False
            else:
                print_result(False, f"Failed to fetch products: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def add_variations(self):
        print_section("4. Add Product Variations")
        
        variations_to_add = [
            {'variation_type': 'Size', 'variation_value': 'Small', 'price_adjustment': 0, 'stock': 50, 'sku': 'PROD-SM'},
            {'variation_type': 'Size', 'variation_value': 'Medium', 'price_adjustment': 5, 'stock': 40, 'sku': 'PROD-MD'},
            {'variation_type': 'Size', 'variation_value': 'Large', 'price_adjustment': 10, 'stock': 30, 'sku': 'PROD-LG'},
            {'variation_type': 'Flavor', 'variation_value': 'Chocolate', 'price_adjustment': 2, 'stock': 60, 'sku': 'PROD-CHOC'},
            {'variation_type': 'Flavor', 'variation_value': 'Vanilla', 'price_adjustment': 2, 'stock': 50, 'sku': 'PROD-VAN'},
            {'variation_type': 'Flavor', 'variation_value': 'Strawberry', 'price_adjustment': 3, 'stock': 40, 'sku': 'PROD-STRAW'},
        ]
        
        headers = {'Authorization': f'Bearer {self.seller_token}'}
        success_count = 0
        
        for var_data in variations_to_add:
            try:
                response = requests.post(
                    f'{BASE_URL}/api/sellers/products/{self.test_product_id}/variations',
                    headers=headers,
                    json=var_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    variation_id = data.get('data', {}).get('variation_id')
                    self.variation_ids.append(variation_id)
                    print_result(True, f"Added {var_data['variation_type']}: {var_data['variation_value']}", {
                        'variation_id': variation_id,
                        'sku': var_data['sku']
                    })
                    success_count += 1
                else:
                    print_result(False, f"Failed to add variation: {response.text}")
            except Exception as e:
                print_result(False, f"Exception: {e}")
        
        return success_count == len(variations_to_add)
    
    def get_variations(self):
        print_section("5. Get Product Variations (Public)")
        try:
            response = requests.get(f'{BASE_URL}/api/products/{self.test_product_id}/variations')
            
            if response.status_code == 200:
                data = response.json()
                variations = data.get('data', {}).get('variations', [])
                grouped = data.get('data', {}).get('grouped', {})
                
                print_result(True, f"Retrieved {len(variations)} variations", {
                    'total': len(variations),
                    'types': list(grouped.keys())
                })
                
                print("\n   Grouped by type:")
                for var_type, vars_list in grouped.items():
                    print(f"   {var_type}:")
                    for var in vars_list:
                        print(f"      - {var['variation_value']}: +₱{var['price_adjustment']} (Stock: {var['stock']})")
                
                return True
            else:
                print_result(False, f"Failed to get variations: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def update_variation(self):
        print_section("6. Update Variation")
        if not self.variation_ids:
            print_result(False, "No variations to update")
            return False
        
        try:
            variation_id = self.variation_ids[0]
            headers = {'Authorization': f'Bearer {self.seller_token}'}
            
            response = requests.put(
                f'{BASE_URL}/api/sellers/products/{self.test_product_id}/variations/{variation_id}',
                headers=headers,
                json={'stock': 100, 'price_adjustment': 1}
            )
            
            if response.status_code == 200:
                print_result(True, "Updated variation stock and price", {
                    'variation_id': variation_id,
                    'new_stock': 100,
                    'new_price_adjustment': 1
                })
                return True
            else:
                print_result(False, f"Failed to update: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def add_to_cart(self):
        print_section("7. Add Variations to Cart")
        if not self.variation_ids:
            print_result(False, "No variations to add to cart")
            return False
        
        headers = {'Authorization': f'Bearer {self.customer_token}'}
        success_count = 0
        
        # Add first two variations to cart
        for i, variation_id in enumerate(self.variation_ids[:2]):
            try:
                response = requests.post(
                    f'{BASE_URL}/api/cart',
                    headers=headers,
                    json={
                        'product_id': self.test_product_id,
                        'variation_id': variation_id,
                        'quantity': 2
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    cart_item_id = data.get('data', {}).get('cart_item_id')
                    self.cart_item_ids.append(cart_item_id)
                    print_result(True, f"Added variation {variation_id} to cart", {
                        'cart_item_id': cart_item_id,
                        'quantity': 2
                    })
                    success_count += 1
                else:
                    print_result(False, f"Failed to add to cart: {response.text}")
            except Exception as e:
                print_result(False, f"Exception: {e}")
        
        return success_count > 0
    
    def get_cart(self):
        print_section("8. View Cart with Variations")
        try:
            headers = {'Authorization': f'Bearer {self.customer_token}'}
            response = requests.get(f'{BASE_URL}/api/cart', headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                cart_items = data.get('data', {}).get('cart_items', [])
                total = data.get('data', {}).get('total_amount', 0)
                
                print_result(True, f"Cart retrieved with {len(cart_items)} items", {
                    'total_items': len(cart_items),
                    'total_amount': total
                })
                
                print("\n   Cart items:")
                for item in cart_items:
                    print(f"   - {item['title']}")
                    print(f"     Variation: {item.get('variation_type')}: {item.get('variation_value')}")
                    print(f"     Price: ₱{item['base_price']} + ₱{item['price_adjustment']} = ₱{item['final_price']}")
                    print(f"     Quantity: {item['quantity']} | Subtotal: ₱{item['subtotal']}")
                
                return True
            else:
                print_result(False, f"Failed to get cart: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def update_cart_item(self):
        print_section("9. Update Cart Item Quantity")
        if not self.cart_item_ids:
            print_result(False, "No cart items to update")
            return False
        
        try:
            headers = {'Authorization': f'Bearer {self.customer_token}'}
            cart_item_id = self.cart_item_ids[0]
            
            response = requests.put(
                f'{BASE_URL}/api/cart/{cart_item_id}',
                headers=headers,
                json={'quantity': 5}
            )
            
            if response.status_code == 200:
                print_result(True, "Updated cart item quantity", {
                    'cart_item_id': cart_item_id,
                    'new_quantity': 5
                })
                return True
            else:
                print_result(False, f"Failed to update: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def create_order_with_variations(self):
        print_section("10. Create Order with Variations")
        try:
            # First get cart to prepare order
            headers = {'Authorization': f'Bearer {self.customer_token}'}
            cart_response = requests.get(f'{BASE_URL}/api/cart', headers=headers)
            
            if cart_response.status_code != 200:
                print_result(False, "Failed to fetch cart for order")
                return False
            
            cart_data = cart_response.json().get('data', {})
            cart_items = cart_data.get('cart_items', [])
            
            # Prepare order items
            order_items = []
            for item in cart_items:
                order_items.append({
                    'product_id': item['product_id'],
                    'variation_id': item.get('variation_id'),
                    'quantity': item['quantity'],
                    'price': item['final_price'],
                    'title': item['title']
                })
            
            # Create order
            order_payload = {
                'customer': {
                    'name': 'Test Customer',
                    'phone': '09171234567',
                    'address': '123 Test Street, Test City'
                },
                'items': order_items,
                'payment': 'Cash on Delivery',
                'delivery': 50
            }
            
            response = requests.post(f'{BASE_URL}/api/orders', json=order_payload)
            
            if response.status_code == 200:
                data = response.json()
                order_id = data.get('order_id')
                total = data.get('total')
                
                print_result(True, "Order created with variations", {
                    'order_id': order_id,
                    'total': total,
                    'items_count': len(order_items)
                })
                return True
            else:
                print_result(False, f"Failed to create order: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def delete_variation(self):
        print_section("11. Delete Variation")
        if len(self.variation_ids) < 3:
            print_result(False, "Not enough variations to delete")
            return False
        
        try:
            # Delete the last variation
            variation_id = self.variation_ids[-1]
            headers = {'Authorization': f'Bearer {self.seller_token}'}
            
            response = requests.delete(
                f'{BASE_URL}/api/sellers/products/{self.test_product_id}/variations/{variation_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                print_result(True, "Deleted variation", {'variation_id': variation_id})
                return True
            else:
                print_result(False, f"Failed to delete: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def run_all_tests(self):
        print_section("🧪 PRODUCT VARIATIONS API TEST SUITE")
        print(f"Testing API at: {BASE_URL}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        tests = [
            ("Seller Login", self.login_seller),
            ("Customer Login", self.login_customer),
            ("Get Seller Product", self.get_seller_product),
            ("Add Variations", self.add_variations),
            ("Get Variations", self.get_variations),
            ("Update Variation", self.update_variation),
            ("Add to Cart", self.add_to_cart),
            ("View Cart", self.get_cart),
            ("Update Cart Item", self.update_cart_item),
            ("Create Order", self.create_order_with_variations),
            ("Delete Variation", self.delete_variation),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print_result(False, f"Test crashed: {e}")
                failed += 1
        
        print_section("📊 TEST SUMMARY")
        print(f"Total Tests: {len(tests)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return failed == 0

if __name__ == '__main__':
    tester = VariationTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
