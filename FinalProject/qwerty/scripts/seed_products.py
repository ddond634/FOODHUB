import sys
import os
from datetime import datetime

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.server import get_db, app, DB_ENGINE
from werkzeug.security import generate_password_hash


def column_exists(cur, table, column):
    if DB_ENGINE == 'mysql':
        cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s;", (table, column))
        return cur.fetchone() is not None
    else:
        cur.execute(f"PRAGMA table_info({table});")
        return any(r[1] == column for r in cur.fetchall())


def ensure_seller(cur, email='seller@example.com', password='Seller123!', business_name='Sample Store', category='General'):
    # Check user
    if DB_ENGINE == 'mysql':
        cur.execute("SELECT id FROM users WHERE email=%s;", (email,))
    else:
        cur.execute("SELECT id FROM users WHERE email=?;", (email,))
    row = cur.fetchone()
    if row:
        user_id = row['id'] if isinstance(row, dict) else row[0]
    else:
        pw_hash = generate_password_hash(password)
        now = datetime.utcnow().isoformat()
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,is_verified,created_at) VALUES (%s,%s,%s,%s,%s,1,%s);",
                        (email, pw_hash, 'Sample', 'Seller', 'seller', now))
        else:
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,is_verified,created_at) VALUES (?,?,?,?,?,1,?);",
                        (email, pw_hash, 'Sample', 'Seller', 'seller', now))
        user_id = cur.lastrowid
    # Check sellers row
    if DB_ENGINE == 'mysql':
        cur.execute("SELECT id FROM sellers WHERE user_id=%s;", (user_id,))
    else:
        cur.execute("SELECT id FROM sellers WHERE user_id=?;", (user_id,))
    srow = cur.fetchone()
    if not srow:
        fields = ['user_id','business_name','category']
        values = [user_id, business_name, category]
        placeholders = []
        if DB_ENGINE == 'mysql':
            placeholders = ['%s']*len(fields)
        else:
            placeholders = ['?']*len(fields)
        # If shop_status column exists, set to 'active'
        if column_exists(cur, 'sellers', 'shop_status'):
            fields.append('shop_status'); values.append('active'); placeholders.append('%s' if DB_ENGINE=='mysql' else '?')
        # If verified column exists, set 1
        if column_exists(cur, 'sellers', 'verified'):
            fields.append('verified'); values.append(1); placeholders.append('%s' if DB_ENGINE=='mysql' else '?')
        sql = f"INSERT INTO sellers ({','.join(fields)}) VALUES ({','.join(placeholders)});"
        cur.execute(sql, tuple(values))
    return user_id


def seed_products():
    products = [
        {
            'title': 'Classic White T-Shirt',
            'description': 'Soft cotton tee with a relaxed fit.',
            'price': 299.00,
            'stock': 50,
            'category': 'Apparel',
            'img_url': 'https://picsum.photos/seed/shirt/400/300'
        },
        {
            'title': 'Insulated Water Bottle 750ml',
            'description': 'Keeps drinks cold for 24h, hot for 12h.',
            'price': 799.00,
            'stock': 30,
            'category': 'Outdoors',
            'img_url': 'https://picsum.photos/seed/bottle/400/300'
        },
        {
            'title': 'Wireless Earbuds Pro',
            'description': 'Active noise cancellation and long battery life.',
            'price': 2499.00,
            'stock': 20,
            'category': 'Electronics',
            'img_url': 'https://picsum.photos/seed/earbuds/400/300'
        },
        {
            'title': 'Organic Dark Roast Coffee Beans 1kg',
            'description': 'Rich flavor, ethically sourced Arabica beans.',
            'price': 899.00,
            'stock': 40,
            'category': 'Grocery',
            'img_url': 'https://picsum.photos/seed/coffee/400/300'
        },
        {
            'title': 'Ergonomic Office Chair',
            'description': 'Lumbar support, breathable mesh back.',
            'price': 4999.00,
            'stock': 10,
            'category': 'Home & Office',
            'img_url': 'https://picsum.photos/seed/chair/400/300'
        }
    ]

    with app.app_context():
        db = get_db(); cur = db.cursor()
        try:
            seller_id = ensure_seller(cur)
            # Prepare insert with engine-specific placeholders
            cols = ['title','description','price','stock','seller_id','category','img_url','created_at']
            ph = ['%s']*len(cols) if DB_ENGINE=='mysql' else ['?']*len(cols)
            sql = f"INSERT INTO products ({','.join(cols)}) VALUES ({','.join(ph)});"

            # Avoid duplicates by title
            for p in products:
                if DB_ENGINE == 'mysql':
                    cur.execute("SELECT id FROM products WHERE title=%s;", (p['title'],))
                else:
                    cur.execute("SELECT id FROM products WHERE title=?;", (p['title'],))
                if cur.fetchone():
                    print(f"[SKIP] Product exists: {p['title']}")
                    continue
                values = [
                    p['title'], p['description'], p['price'], p['stock'], seller_id, p['category'], p['img_url'], datetime.utcnow().isoformat()
                ]
                cur.execute(sql, tuple(values))
            db.commit()
            print("[OK] Sample products seeded.")
        finally:
            try: cur.close()
            except: pass


if __name__ == '__main__':
    seed_products()
