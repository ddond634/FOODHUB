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
            'admin': None,
            'buyer': None,
            'rider': None,
            'sellers': []
        }

        # Remove any existing accounts that clash with the seeded emails
        test_emails = [
            'admin@example.com', 'buyer@example.com', 'rider@example.com',
            'seller1@example.com','seller2@example.com','seller3@example.com','seller4@example.com','seller5@example.com'
        ]

        print("🗑️  Deleting existing seeded accounts if present...")
        for email in test_emails:
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
                else:
                    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user_row = cursor.fetchone()
                if user_row:
                    # row may be dict or tuple
                    if isinstance(user_row, dict):
                        user_id = user_row.get('id')
                    else:
                        user_id = user_row[0]
                    if user_id:
                        if DB_ENGINE == 'mysql':
                            cursor.execute('DELETE FROM products WHERE seller_id = %s', (user_id,))
                            cursor.execute('DELETE FROM sellers WHERE user_id = %s', (user_id,))
                            cursor.execute('DELETE FROM riders WHERE user_id = %s', (user_id,))
                            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
                        else:
                            cursor.execute('DELETE FROM products WHERE seller_id = ?', (user_id,))
                            cursor.execute('DELETE FROM sellers WHERE user_id = ?', (user_id,))
                            cursor.execute('DELETE FROM riders WHERE user_id = ?', (user_id,))
                            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                        print(f"   - Removed existing account: {email}")
            except Exception as del_err:
                print(f"   ⚠️  Warning: Could not delete {email}: {del_err}")

        # Helper to create a user if not exists
        def ensure_user(email, pw, first, last, role):
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            else:
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            r = cursor.fetchone()
            if r:
                uid = r['id'] if isinstance(r, dict) else r[0]
                return uid
            pw_hash = generate_password_hash(pw)
            if DB_ENGINE == 'mysql':
                cursor.execute('''INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active) VALUES (%s,%s,%s,%s,%s,1,1)''',
                               (email, pw_hash, first, last, role))
            else:
                cursor.execute('''INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, created_at) VALUES (?,?,?,?,?,1,?)''',
                               (email, pw_hash, first, last, role, datetime.utcnow().isoformat()))
            return cursor.lastrowid

        # Create admin
        print('\n👤 Creating admin account...')
        admin_id = ensure_user('admin@example.com', 'Admin123!', 'Admin', 'User', 'admin')
        created_accounts['admin'] = {'email': 'admin@example.com', 'password': 'Admin123!', 'user_id': admin_id}
        print(f"   ✅ admin@example.com -> id {admin_id}")

        # Create buyer
        print('\n🛒 Creating buyer account...')
        buyer_id = ensure_user('buyer@example.com', 'Buyer123!', 'Buyer', 'Customer', 'customer')
        created_accounts['buyer'] = {'email': 'buyer@example.com', 'password': 'Buyer123!', 'user_id': buyer_id}
        print(f"   ✅ buyer@example.com -> id {buyer_id}")

        # Create rider
        print('\n🚴 Creating rider account...')
        rider_user_id = ensure_user('rider@example.com', 'Rider123!', 'Rider', 'Courier', 'rider')
        # insert rider profile using only existing columns
        try:
            cols = ['user_id', 'vehicle_type', 'driver_license']
            vals = [rider_user_id, 'Motorcycle', 'DL-RIDER-001']
            # detect optional columns in riders table
            if DB_ENGINE == 'mysql':
                cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='riders';")
                existing = {r[0] for r in cursor.fetchall()}
            else:
                cursor.execute("PRAGMA table_info(riders);")
                existing = {r[1] for r in cursor.fetchall()}

            if 'verified' in existing:
                cols.append('verified'); vals.append(1)
            if 'rider_status' in existing:
                cols.append('rider_status'); vals.append('active')
            if 'availability' in existing:
                cols.append('availability'); vals.append('available')

            placeholders = ['%s']*len(cols) if DB_ENGINE=='mysql' else ['?']*len(cols)
            sql = f"INSERT INTO riders ({','.join(cols)}) VALUES ({','.join(placeholders)})"
            cursor.execute(sql, tuple(vals))
        except Exception as rerr:
            print(f"   ⚠️  Could not insert rider profile with flexible columns: {rerr}")

        created_accounts['rider'] = {'email': 'rider@example.com', 'password': 'Rider123!', 'user_id': rider_user_id}
        print(f"   ✅ rider@example.com -> id {rider_user_id}")

        # Seller definitions and products
        sellers = [
            {
                'email': 'seller1@example.com', 'first': 'Fresh', 'last': 'Greens', 'business_name': 'Fresh Greens Market', 'category': 'Produce',
                'products': [
                    ('Organic Lettuce Bundle','Crisp organic lettuce perfect for salads and wraps.',120.00,20,'/uploads/products/fresh-greens-lettuce.jpg'),
                    ('Cherry Tomato Pack','Sweet cherry tomatoes for snacks and sauces.',80.00,35,'/uploads/products/fresh-greens-tomatoes.jpg'),
                    ('Baby Carrot Snack Bag','Ready-to-eat baby carrots with high crunch.',75.00,40,'/uploads/products/fresh-greens-carrots.jpg'),
                    ('Mixed Salad Greens','Mixed greens blend for healthy bowls.',150.00,25,'/uploads/products/fresh-greens-mix.jpg'),
                    ('Cucumber Crisp','Fresh cucumbers sliced for salads.',90.00,30,'/uploads/products/fresh-greens-cucumber.jpg')
                ]
            },
            {
                'email': 'seller2@example.com', 'first': 'Metro', 'last': 'Snacks', 'business_name': 'Metro Snacks Co.', 'category': 'Snacks',
                'products': [
                    ('Crunchy Nacho Chips','Salted nacho chips with a light crunch.',95.00,50,'/uploads/products/metro-snacks-nachos.jpg'),
                    ('Classic Popcorn Tub','Butter-popcorn perfect for movie nights.',110.00,45,'/uploads/products/metro-snacks-popcorn.jpg'),
                    ('Barbecue Nuts Mix','Savory roasted nut mix with smoky BBQ flavor.',150.00,30,'/uploads/products/metro-snacks-nuts.jpg'),
                    ('Premium Beef Jerky','Spicy beef jerky made from premium cuts.',220.00,20,'/uploads/products/metro-snacks-jerky.jpg'),
                    ('Fruit Gummies Pack','Colorful gummy candies with mixed fruit flavors.',85.00,60,'/uploads/products/metro-snacks-gummies.jpg'),
                    ('Crispy Potato Sticks','Crunchy potato sticks seasoned with cheese.',105.00,40,'/uploads/products/metro-snacks-sticks.jpg')
                ]
            },
            {
                'email': 'seller3@example.com', 'first': 'Daily', 'last': 'Bites', 'business_name': 'Daily Bites Kitchen', 'category': 'Prepared Meals',
                'products': [
                    ('Classic Chicken Adobo','Hearty chicken adobo meal with rice.',220.00,18,'/uploads/products/daily-bites-adobo.jpg'),
                    ('Beef Kare-Kare Bowl','Rich kare-kare stew with peanut sauce.',260.00,15,'/uploads/products/daily-bites-kare-kare.jpg'),
                    ('Garlic Shrimp Pasta','Creamy garlic shrimp pasta with herbs.',240.00,20,'/uploads/products/daily-bites-pasta.jpg'),
                    ('Vegetable Lumpia Set','Crispy vegetable lumpia with dipping sauce.',180.00,28,'/uploads/products/daily-bites-lumpia.jpg'),
                    ('Breakfast Pancake Stack','Fluffy pancakes with honey and fruit.',190.00,22,'/uploads/products/daily-bites-pancakes.jpg'),
                    ('Rice Bowl Combo','Rice bowl with egg, veggies, and choice of protein.',210.00,24,'/uploads/products/daily-bites-rice-bowl.jpg')
                ]
            },
            {
                'email': 'seller4@example.com', 'first': 'Picnic', 'last': 'Pantry', 'business_name': 'Picnic Pantry', 'category': 'Beverages',
                'products': [
                    ('Iced Lemon Tea','Refreshing iced tea with lemon slices.',95.00,30,'/uploads/products/picnic-pantry-lemon-tea.jpg'),
                    ('Mango Smoothie Bottle','Smooth mango drink with tropical flavor.',120.00,26,'/uploads/products/picnic-pantry-mango-smoothie.jpg'),
                    ('Espresso Cold Brew','Strong cold brew coffee in a chilled bottle.',140.00,18,'/uploads/products/picnic-pantry-cold-brew.jpg'),
                    ('Strawberry Lemonade','Sweet and tangy strawberry lemonade.',110.00,28,'/uploads/products/picnic-pantry-lemonade.jpg'),
                    ('Coconut Water Pack','Pure coconut water with natural electrolytes.',130.00,22,'/uploads/products/picnic-pantry-coconut-water.jpg'),
                    ('Matcha Latte','Creamy matcha latte made with premium matcha powder.',150.00,20,'/uploads/products/picnic-pantry-matcha-latte.jpg'),
                    ('Sparkling Fruit Soda','Fizzy fruit soda blend with citrus notes.',125.00,25,'/uploads/products/picnic-pantry-soda.jpg')
                ]
            },
            {
                'email': 'seller5@example.com', 'first': 'Baker', 'last': 'Corner', 'business_name': "Baker's Corner", 'category': 'Bakery',
                'products': [
                    ('Chocolate Chip Muffin','Warm muffin filled with chocolate chips.',95.00,35,'/uploads/products/bakers-corner-muffin.jpg'),
                    ('Rustic Sourdough Loaf','Artisan sourdough bread with crisp crust.',180.00,20,'/uploads/products/bakers-corner-sourdough.jpg'),
                    ('Cinnamon Roll Treat','Sweet cinnamon roll with icing drizzle.',130.00,25,'/uploads/products/bakers-corner-cinnamon-roll.jpg'),
                    ('Blueberry Danish','Flaky Danish pastry with blueberry filling.',110.00,28,'/uploads/products/bakers-corner-danish.jpg'),
                    ('Salted Caramel Tart','Creamy caramel tart with sea salt finish.',145.00,20,'/uploads/products/bakers-corner-tart.jpg'),
                    ('Garlic Cheese Bread','Savory garlic bread topped with cheese.',120.00,30,'/uploads/products/bakers-corner-garlic-bread.jpg'),
                    ('Honey Oat Cookies','Chewy cookies with oat and honey goodness.',85.00,40,'/uploads/products/bakers-corner-cookies.jpg')
                ]
            }
        ]

        # Insert sellers and their products
        print('\n🏪 Creating seller accounts and sample products...')
        # product insert preparation
        prod_cols = ['title','description','price','stock','seller_id','category','img_url','created_at']
        prod_placeholders = ['%s']*len(prod_cols) if DB_ENGINE=='mysql' else ['?']*len(prod_cols)
        prod_sql = f"INSERT INTO products ({','.join(prod_cols)}) VALUES ({','.join(prod_placeholders)});"

        for s in sellers:
            try:
                user_id = ensure_user(s['email'], 'Seller123!', s['first'], s['last'], 'seller')
                # create sellers profile if table exists
                try:
                    if DB_ENGINE == 'mysql':
                        cursor.execute('SELECT id FROM sellers WHERE user_id = %s', (user_id,))
                    else:
                        cursor.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,))
                    if not cursor.fetchone():
                        if DB_ENGINE == 'mysql':
                            cursor.execute('INSERT INTO sellers (user_id, business_name, category, verified, shop_status) VALUES (%s,%s,%s,1,%s)',
                                           (user_id, s['business_name'], s['category'], 'active'))
                        else:
                            cursor.execute('INSERT INTO sellers (user_id, business_name, category, verified, shop_status) VALUES (?,?,?,?,?)',
                                           (user_id, s['business_name'], s['category'], 1, 'active'))
                except Exception:
                    # If sellers table or columns differ, ignore and continue
                    pass

                for p in s['products']:
                    title, desc, price, stock, img = p
                    # avoid duplicate by title + seller
                    try:
                        if DB_ENGINE == 'mysql':
                            cursor.execute('SELECT id FROM products WHERE title = %s AND seller_id = %s', (title, user_id))
                        else:
                            cursor.execute('SELECT id FROM products WHERE title = ? AND seller_id = ?', (title, user_id))
                        if cursor.fetchone():
                            continue
                    except Exception:
                        pass
                    vals = [title, desc, price, stock, user_id, s['category'], img, datetime.utcnow().isoformat()]
                    cursor.execute(prod_sql, tuple(vals))

                created_accounts['sellers'].append({'email': s['email'], 'password': 'Seller123!', 'user_id': user_id, 'business_name': s['business_name']})
                print(f"   ✅ Created seller {s['email']} with {len(s['products'])} products")
            except Exception as serr:
                print(f"   ❌ Failed creating seller {s['email']}: {serr}")

        # Commit and close
        db.commit()
        cursor.close()
        db.close()

        # Summary
        print('\n✨ Seeding complete! Accounts created:')
        print(f"  - Admin: {created_accounts['admin']['email']} (id {created_accounts['admin']['user_id']})")
        print(f"  - Buyer: {created_accounts['buyer']['email']} (id {created_accounts['buyer']['user_id']})")
        print(f"  - Rider: {created_accounts['rider']['email']} (id {created_accounts['rider']['user_id']})")
        print('\n  - Sellers:')
        for s in created_accounts['sellers']:
            print(f"     * {s['email']} | Business: {s['business_name']} | user_id: {s['user_id']}")

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

