import sqlite3

DB = 'FinalProject/qwerty/qwerty.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('USERS:')
cur.execute("SELECT id,email,first_name,last_name,role,is_verified,created_at FROM users")
for u in cur.fetchall():
    print(f" - id {u['id']}: {u['email']} ({u['role']})")

print('\nPRODUCTS (per seller):')
cur.execute("SELECT seller_id, count(*) as cnt FROM products GROUP BY seller_id")
for r in cur.fetchall():
    print(f" - seller_id {r['seller_id']}: {r['cnt']} products")

print('\nSAMPLE PRODUCTS (first 10):')
cur.execute("SELECT id,title,price,stock,seller_id FROM products LIMIT 10")
for p in cur.fetchall():
    print(f" - id {p['id']}: {p['title']} ₱{p['price']} stock {p['stock']} seller {p['seller_id']}")

conn.close()
