"""
Comprehensive API Testing Script
Tests critical endpoints and business logic
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓{Colors.END} {message}")

def print_error(message):
    print(f"{Colors.RED}✗{Colors.END} {message}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ{Colors.END} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")


class APITester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.admin_token = None
        self.seller_token = None
        self.customer_token = None
        self.test_product_id = None
        self.test_order_id = None
        
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def test_health_check(self):
        """Test health check endpoint"""
        print("\n" + "="*60)
        print("Testing Health Check")
        print("="*60)
        
        try:
            response = requests.get(f"{self.base_url}/api/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') or data.get('status') == 'healthy':
                    print_success("Health check passed")
                    print_info(f"  Database: {data.get('database', 'N/A')}")
                    print_info(f"  Timestamp: {data.get('timestamp', 'N/A')}")
                    self.passed += 1
                else:
                    print_error("Health check returned OK but status unhealthy")
                    self.failed += 1
            else:
                print_error(f"Health check failed with status {response.status_code}")
                self.failed += 1
        except Exception as e:
            print_error(f"Health check error: {e}")
            self.failed += 1
    
    def test_registration(self):
        """Test user registration"""
        print("\n" + "="*60)
        print("Testing User Registration")
        print("="*60)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Test customer registration
        try:
            response = requests.post(f"{self.base_url}/api/auth/register", json={
                'email': f'test_customer_{timestamp}@test.com',
                'password': 'Test1234!',
                'first_name': 'Test',
                'last_name': 'Customer',
                'role': 'customer'
            })
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                if data.get('success'):
                    print_success("Customer registration successful")
                    self.customer_token = data.get('token') or data.get('data', {}).get('token')
                    self.passed += 1
                else:
                    print_error(f"Registration failed: {data.get('message')}")
                    self.failed += 1
            else:
                print_error(f"Registration failed with status {response.status_code}")
                print_info(f"  Response: {response.text}")
                self.failed += 1
        except Exception as e:
            print_error(f"Registration error: {e}")
            self.failed += 1
    
    def test_login(self):
        """Test user login"""
        print("\n" + "="*60)
        print("Testing User Login")
        print("="*60)
        
        # Try to login as admin (should exist)
        try:
            response = requests.post(f"{self.base_url}/api/auth/login", json={
                'email': 'admin@example.com',
                'password': 'admin'
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.admin_token = data.get('token') or data.get('data', {}).get('token')
                    print_success("Admin login successful")
                    print_info(f"  Token: {self.admin_token[:20]}...")
                    self.passed += 1
                else:
                    print_warning("Admin login returned 200 but success=false")
                    print_info(f"  Message: {data.get('message')}")
                    self.warnings += 1
            else:
                print_warning(f"Admin login failed - might not exist yet")
                print_info(f"  Status: {response.status_code}")
                self.warnings += 1
        except Exception as e:
            print_error(f"Login error: {e}")
            self.failed += 1
    
    def test_products_list(self):
        """Test products listing"""
        print("\n" + "="*60)
        print("Testing Products Listing")
        print("="*60)
        
        try:
            response = requests.get(f"{self.base_url}/api/products")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) or (isinstance(data, dict) and 'data' in data):
                    products = data if isinstance(data, list) else data.get('data', [])
                    print_success(f"Products listing successful ({len(products)} products)")
                    
                    if len(products) > 0:
                        self.test_product_id = products[0].get('id')
                        print_info(f"  Sample product: {products[0].get('title', 'N/A')}")
                    else:
                        print_warning("  No products found")
                    
                    self.passed += 1
                else:
                    print_error("Invalid response format")
                    self.failed += 1
            else:
                print_error(f"Products listing failed with status {response.status_code}")
                self.failed += 1
        except Exception as e:
            print_error(f"Products listing error: {e}")
            self.failed += 1
    
    def test_product_detail(self):
        """Test product detail endpoint"""
        if not self.test_product_id:
            print_warning("Skipping product detail test - no product ID available")
            return
        
        print("\n" + "="*60)
        print("Testing Product Detail")
        print("="*60)
        
        try:
            response = requests.get(f"{self.base_url}/api/products/{self.test_product_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('id') or data.get('data', {}).get('id'):
                    print_success("Product detail retrieved successfully")
                    product = data if data.get('id') else data.get('data')
                    print_info(f"  Title: {product.get('title', 'N/A')}")
                    print_info(f"  Price: ₱{product.get('price', 0)}")
                    print_info(f"  Stock: {product.get('stock', 0)}")
                    self.passed += 1
                else:
                    print_error("Invalid product detail response")
                    self.failed += 1
            else:
                print_error(f"Product detail failed with status {response.status_code}")
                self.failed += 1
        except Exception as e:
            print_error(f"Product detail error: {e}")
            self.failed += 1
    
    def test_auth_protected_endpoint(self):
        """Test authentication protection"""
        print("\n" + "="*60)
        print("Testing Authentication Protection")
        print("="*60)
        
        try:
            # Try to access protected endpoint without token
            response = requests.get(f"{self.base_url}/api/sellers/products")
            
            if response.status_code in [401, 403]:
                print_success("Protected endpoint correctly requires authentication")
                self.passed += 1
            elif response.status_code == 200:
                print_error("Protected endpoint accessible without authentication!")
                self.failed += 1
            else:
                print_warning(f"Unexpected status code: {response.status_code}")
                self.warnings += 1
        except Exception as e:
            print_error(f"Auth test error: {e}")
            self.failed += 1
    
    def test_validation(self):
        """Test input validation"""
        print("\n" + "="*60)
        print("Testing Input Validation")
        print("="*60)
        
        try:
            # Try to register with invalid email
            response = requests.post(f"{self.base_url}/api/auth/register", json={
                'email': 'invalid-email',
                'password': 'Test1234!',
                'role': 'customer'
            })
            
            if response.status_code in [400, 422]:
                print_success("Invalid email correctly rejected")
                self.passed += 1
            else:
                print_warning(f"Invalid email not rejected (status: {response.status_code})")
                self.warnings += 1
        except Exception as e:
            print_error(f"Validation test error: {e}")
            self.failed += 1
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print(f"{Colors.BLUE}Starting API Tests{Colors.END}")
        print(f"Base URL: {self.base_url}")
        print("="*60)
        
        self.test_health_check()
        self.test_registration()
        self.test_login()
        self.test_products_list()
        self.test_product_detail()
        self.test_auth_protected_endpoint()
        self.test_validation()
        
        # Print summary
        print("\n" + "="*60)
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
        print("="*60)
        print(f"{Colors.GREEN}Passed:{Colors.END}    {self.passed}")
        print(f"{Colors.RED}Failed:{Colors.END}    {self.failed}")
        print(f"{Colors.YELLOW}Warnings:{Colors.END}  {self.warnings}")
        print(f"Total:     {self.passed + self.failed + self.warnings}")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}All critical tests passed!{Colors.END}")
            return 0
        else:
            print(f"\n{Colors.RED}Some tests failed. Please review above.{Colors.END}")
            return 1


if __name__ == '__main__':
    import sys
    
    tester = APITester()
    exit_code = tester.run_all_tests()
    
    sys.exit(exit_code)
