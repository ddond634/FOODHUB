#!/usr/bin/env python3
"""
Direct database script to create test accounts for sellers and riders.
This script directly accesses the database without needing authentication.
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database connection
try:
    import os
    from dotenv import load_dotenv
    from werkzeug.security import generate_password_hash
    from datetime import datetime
    
    # Load environment variables
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(BASE_DIR, '.env'))
    
    # Determine database engine
    DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()
    
    # Import database libraries
    if DB_ENGINE == 'mysql':
        import pymysql
        import pymysql.cursors
    else:
        import sqlite3
    
    def get_db():
        """Get database connection without Flask context"""
        if DB_ENGINE == 'mysql':
            return pymysql.connect(
                host=os.environ.get('DB_HOST', '127.0.0.1'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASS', ''),
                db=os.environ.get('DB_NAME', 'qwerty'),
                port=int(os.environ.get('DB_PORT', '3306')),
                cursorclass=pymysql.cursors.DictCursor,
                charset='utf8mb4'
            )
        else:
            db_path = os.path.join(BASE_DIR, 'qwerty.db')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
            
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running this from the backend directory and required packages are installed.")
    sys.exit(1)

def create_test_accounts():
    """Create test accounts directly in the database"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        created_accounts = {
            'sellers': [],
            'riders': []
        }
        
        # Delete existing test accounts first
        test_emails = [
            'test-seller-1@test.com', 'test-seller-2@test.com', 'test-seller-3@test.com',
            'test-rider-1@test.com', 'test-rider-2@test.com', 'test-rider-3@test.com'
        ]
        
        print("🗑️  Deleting existing test accounts...")
        for email in test_emails:
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
                else:
                    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user_row = cursor.fetchone()
                if user_row:
                    user_id = user_row[0] if isinstance(user_row, tuple) else (user_row.get('id') if hasattr(user_row, 'get') else user_row['id'])
                    if user_id:
                        if DB_ENGINE == 'mysql':
                            cursor.execute('DELETE FROM sellers WHERE user_id = %s', (user_id,))
                            cursor.execute('DELETE FROM riders WHERE user_id = %s', (user_id,))
                            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
                        else:
                            cursor.execute('DELETE FROM sellers WHERE user_id = ?', (user_id,))
                            cursor.execute('DELETE FROM riders WHERE user_id = ?', (user_id,))
                            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            except Exception as del_err:
                print(f"   ⚠️  Warning: Could not delete {email}: {del_err}")
        
        # Create 3 test seller accounts
        print("\n🏪 Creating seller accounts...")
        seller_data = [
            {'email': 'test-seller-1@test.com', 'first_name': 'Test', 'last_name': 'Seller One', 'business_name': 'Test Store One', 'category': 'Food'},
            {'email': 'test-seller-2@test.com', 'first_name': 'Test', 'last_name': 'Seller Two', 'business_name': 'Test Store Two', 'category': 'Electronics'},
            {'email': 'test-seller-3@test.com', 'first_name': 'Test', 'last_name': 'Seller Three', 'business_name': 'Test Store Three', 'category': 'Clothing'}
        ]
        
        for seller_info in seller_data:
            email = seller_info['email']
            password_hash = generate_password_hash('test123')
            
            try:
                # Create user account
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (email, password_hash, seller_info['first_name'], seller_info['last_name'], 'seller', 1, 1))
                    user_id = cursor.lastrowid
                else:
                    cursor.execute('''
                        INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (email, password_hash, seller_info['first_name'], seller_info['last_name'], 'seller', 1, 1))
                    user_id = cursor.lastrowid
                
                # Create seller profile
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        INSERT INTO sellers (user_id, business_name, category, verified, shop_status)
                        VALUES (%s, %s, %s, 1, 'active')
                    ''', (user_id, seller_info['business_name'], seller_info['category']))
                    seller_id = cursor.lastrowid
                else:
                    cursor.execute('''
                        INSERT INTO sellers (user_id, business_name, category, verified, shop_status)
                        VALUES (?, ?, ?, 1, 'active')
                    ''', (user_id, seller_info['business_name'], seller_info['category']))
                    seller_id = cursor.lastrowid
                
                created_accounts['sellers'].append({
                    'email': email,
                    'password': 'test123',
                    'user_id': user_id,
                    'seller_id': seller_id,
                    'business_name': seller_info['business_name']
                })
                print(f"   ✅ Created: {email} (ID: {seller_id})")
            except Exception as err:
                print(f"   ❌ Failed to create {email}: {err}")
        
        # Create 3 test rider accounts
        print("\n🚴 Creating rider accounts...")
        rider_data = [
            {'email': 'test-rider-1@test.com', 'first_name': 'Test', 'last_name': 'Rider One', 'vehicle_type': 'Motorcycle', 'driver_license': 'DL001'},
            {'email': 'test-rider-2@test.com', 'first_name': 'Test', 'last_name': 'Rider Two', 'vehicle_type': 'Bicycle', 'driver_license': 'DL002'},
            {'email': 'test-rider-3@test.com', 'first_name': 'Test', 'last_name': 'Rider Three', 'vehicle_type': 'Car', 'driver_license': 'DL003'}
        ]
        
        for rider_info in rider_data:
            email = rider_info['email']
            password_hash = generate_password_hash('test123')
            
            try:
                # Create user account
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (email, password_hash, rider_info['first_name'], rider_info['last_name'], 'rider', 1, 1))
                    user_id = cursor.lastrowid
                else:
                    cursor.execute('''
                        INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (email, password_hash, rider_info['first_name'], rider_info['last_name'], 'rider', 1, 1))
                    user_id = cursor.lastrowid
                
                # Create rider profile
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        INSERT INTO riders (user_id, vehicle_type, driver_license, verified, rider_status, availability)
                        VALUES (%s, %s, %s, 1, 'active', 'available')
                    ''', (user_id, rider_info['vehicle_type'], rider_info['driver_license']))
                    rider_id = cursor.lastrowid
                else:
                    cursor.execute('''
                        INSERT INTO riders (user_id, vehicle_type, driver_license, verified, rider_status, availability)
                        VALUES (?, ?, ?, 1, 'active', 'available')
                    ''', (user_id, rider_info['vehicle_type'], rider_info['driver_license']))
                    rider_id = cursor.lastrowid
                
                created_accounts['riders'].append({
                    'email': email,
                    'password': 'test123',
                    'user_id': user_id,
                    'rider_id': rider_id,
                    'vehicle_type': rider_info['vehicle_type']
                })
                print(f"   ✅ Created: {email} (ID: {rider_id})")
            except Exception as err:
                print(f"   ❌ Failed to create {email}: {err}")
        
        # Commit the transaction
        db.commit()
        cursor.close()
        db.close()
        
        print(f"\n✨ Successfully created {len(created_accounts['sellers'])} seller accounts and {len(created_accounts['riders'])} rider accounts!")
        
        print(f"\n📋 Account Summary:")
        print(f"\n🏪 Seller Accounts:")
        for seller in created_accounts['sellers']:
            print(f"   - {seller['email']} | Password: {seller['password']} | Business: {seller['business_name']}")
        
        print(f"\n🚴 Rider Accounts:")
        for rider in created_accounts['riders']:
            print(f"   - {rider['email']} | Password: {rider['password']} | Vehicle: {rider['vehicle_type']}")
        
        print("\n💡 These accounts are now ready for testing admin actions!")
        return True
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error: {e}")
        print(traceback.format_exc())
        try:
            db.rollback()
        except:
            pass
        try:
            cursor.close()
        except:
            pass
        try:
            db.close()
        except:
            pass
        return False

if __name__ == "__main__":
    print("🔧 Creating test accounts directly in database...\n")
    success = create_test_accounts()
    sys.exit(0 if success else 1)

