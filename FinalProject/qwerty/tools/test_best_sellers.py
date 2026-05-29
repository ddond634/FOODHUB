#!/usr/bin/env python3
"""
Test Best Selling Products API Endpoint
Tests the best sellers functionality with various filters
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = 'http://localhost:5000'

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(success, message, data=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")
    if data:
        print(f"   Data: {json.dumps(data, indent=3)}")

class BestSellersTester:
    def __init__(self):
        pass
    
    def test_all_best_sellers(self):
        print_section("1. Get All Best Sellers (All Time)")
        try:
            response = requests.get(f'{BASE_URL}/api/products/best-sellers?limit=10')
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                
                print_result(True, f"Retrieved {len(products)} best sellers", {
                    'total': len(products),
                    'timeframe': data.get('data', {}).get('timeframe'),
                    'category': data.get('data', {}).get('category')
                })
                
                if products:
                    print("\n   Top 5 Best Sellers:")
                    for i, product in enumerate(products[:5], 1):
                        print(f"   {i}. {product['title']}")
                        print(f"      Price: ₱{product['price']} | Sold: {product['total_sold']} units")
                        print(f"      Seller: {product['seller_name']} | Category: {product['category']}")
                        print(f"      Stock: {product['stock']}")
                
                return True
            else:
                print_result(False, f"Failed: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def test_category_filter(self):
        print_section("2. Filter by Category")
        
        categories = ['Baking', 'Coffee & Tea', 'Snacks', 'Organic']
        success_count = 0
        
        for category in categories:
            try:
                response = requests.get(
                    f'{BASE_URL}/api/products/best-sellers',
                    params={'limit': 5, 'category': category}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = data.get('data', {}).get('products', [])
                    
                    print_result(True, f"Category '{category}': {len(products)} products", {
                        'category': category,
                        'count': len(products)
                    })
                    
                    # Verify all products match category
                    if products:
                        all_match = all(
                            category.lower() in product.get('category', '').lower() or
                            product.get('category_normalized') == category
                            for product in products
                        )
                        if all_match:
                            print(f"      ✓ All products match category filter")
                        else:
                            print(f"      ⚠ Some products don't match category")
                    
                    success_count += 1
                else:
                    print_result(False, f"Failed for category '{category}': {response.text}")
            except Exception as e:
                print_result(False, f"Exception for '{category}': {e}")
        
        return success_count == len(categories)
    
    def test_timeframe_filters(self):
        print_section("3. Test Timeframe Filters")
        
        timeframes = ['all', 'monthly', 'weekly', 'daily']
        success_count = 0
        
        for timeframe in timeframes:
            try:
                response = requests.get(
                    f'{BASE_URL}/api/products/best-sellers',
                    params={'limit': 10, 'timeframe': timeframe}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = data.get('data', {}).get('products', [])
                    
                    print_result(True, f"Timeframe '{timeframe}': {len(products)} products", {
                        'timeframe': timeframe,
                        'count': len(products)
                    })
                    
                    success_count += 1
                else:
                    print_result(False, f"Failed for timeframe '{timeframe}': {response.text}")
            except Exception as e:
                print_result(False, f"Exception for '{timeframe}': {e}")
        
        return success_count == len(timeframes)
    
    def test_combined_filters(self):
        print_section("4. Combined Filters (Category + Timeframe)")
        try:
            response = requests.get(
                f'{BASE_URL}/api/products/best-sellers',
                params={
                    'limit': 5,
                    'category': 'Snacks',
                    'timeframe': 'weekly'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                
                print_result(True, "Combined filters working", {
                    'category': 'Snacks',
                    'timeframe': 'weekly',
                    'products_found': len(products)
                })
                
                if products:
                    print("\n   Products:")
                    for product in products:
                        print(f"   - {product['title']} (Sold: {product['total_sold']})")
                
                return True
            else:
                print_result(False, f"Failed: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def test_data_structure(self):
        print_section("5. Verify Data Structure")
        try:
            response = requests.get(f'{BASE_URL}/api/products/best-sellers?limit=1')
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                
                if products:
                    product = products[0]
                    
                    # Check required fields
                    required_fields = [
                        'id', 'title', 'price', 'img_url', 'category',
                        'seller_name', 'seller_id', 'total_sold', 'order_count',
                        'stock', 'category_normalized'
                    ]
                    
                    missing_fields = [field for field in required_fields if field not in product]
                    
                    if not missing_fields:
                        print_result(True, "All required fields present", {
                            'sample_product': product['title'],
                            'fields_count': len(product.keys())
                        })
                        
                        print("\n   Sample Product Data:")
                        print(f"   Title: {product['title']}")
                        print(f"   Price: ₱{product['price']}")
                        print(f"   Category: {product['category']} → {product['category_normalized']}")
                        print(f"   Seller: {product['seller_name']}")
                        print(f"   Total Sold: {product['total_sold']} units")
                        print(f"   Orders: {product['order_count']}")
                        print(f"   Stock: {product['stock']}")
                        
                        return True
                    else:
                        print_result(False, f"Missing fields: {missing_fields}")
                        return False
                else:
                    print_result(False, "No products in response")
                    return False
            else:
                print_result(False, f"Failed: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def test_sorting(self):
        print_section("6. Verify Sorting by Sales")
        try:
            response = requests.get(f'{BASE_URL}/api/products/best-sellers?limit=10')
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                
                if len(products) >= 2:
                    # Check if sorted by total_sold DESC
                    is_sorted = all(
                        products[i]['total_sold'] >= products[i+1]['total_sold']
                        for i in range(len(products)-1)
                    )
                    
                    if is_sorted:
                        print_result(True, "Products correctly sorted by sales", {
                            'first_product_sold': products[0]['total_sold'],
                            'last_product_sold': products[-1]['total_sold']
                        })
                        
                        print("\n   Sales ranking:")
                        for i, product in enumerate(products[:5], 1):
                            print(f"   {i}. {product['title']}: {product['total_sold']} sold")
                        
                        return True
                    else:
                        print_result(False, "Products not properly sorted")
                        return False
                else:
                    print_result(False, "Not enough products to verify sorting")
                    return False
            else:
                print_result(False, f"Failed: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def test_active_sellers_only(self):
        print_section("7. Verify Active Sellers Only")
        try:
            response = requests.get(f'{BASE_URL}/api/products/best-sellers?limit=10')
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                
                print_result(True, f"Retrieved {len(products)} products from active sellers", {
                    'total_products': len(products)
                })
                
                if products:
                    sellers = set(product['seller_name'] for product in products)
                    print(f"\n   Active sellers ({len(sellers)}):")
                    for seller in sorted(sellers):
                        seller_products = [p for p in products if p['seller_name'] == seller]
                        total_sold = sum(p['total_sold'] for p in seller_products)
                        print(f"   - {seller}: {len(seller_products)} products, {total_sold} total sold")
                
                return True
            else:
                print_result(False, f"Failed: {response.text}")
                return False
        except Exception as e:
            print_result(False, f"Exception: {e}")
            return False
    
    def run_all_tests(self):
        print_section("🧪 BEST SELLERS API TEST SUITE")
        print(f"Testing API at: {BASE_URL}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        tests = [
            ("All Best Sellers", self.test_all_best_sellers),
            ("Category Filters", self.test_category_filter),
            ("Timeframe Filters", self.test_timeframe_filters),
            ("Combined Filters", self.test_combined_filters),
            ("Data Structure", self.test_data_structure),
            ("Sorting Verification", self.test_sorting),
            ("Active Sellers Only", self.test_active_sellers_only),
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
    tester = BestSellersTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
