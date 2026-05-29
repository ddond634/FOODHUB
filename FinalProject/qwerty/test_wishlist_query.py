#!/usr/bin/env python3
"""Test the exact wishlist query used by backend"""
import pymysql

try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='qwerty',
        port=3306
    )
    
    user_id = 4  # From the database check
    
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT p.id as product_id, p.title, p.price, p.img_url, 
               p.category, p.stock
        FROM wishlist w 
        JOIN products p ON p.id=w.product_id 
        WHERE w.user_id=%s
    """
    
    print("🔍 Executing query:")
    print(query)
    print(f"   With user_id = {user_id}")
    print()
    
    cur.execute(query, (user_id,))
    items = cur.fetchall()
    
    print(f"📦 Query returned {len(items)} item(s)")
    print()
    
    if items:
        for i, item in enumerate(items, 1):
            print(f"Item {i}:")
            print(f"  product_id: {item.get('product_id')}")
            print(f"  title: {item.get('title')}")
            print(f"  price: {item.get('price')}")
            print(f"  img_url: {item.get('img_url')}")
            print(f"  category: {item.get('category')}")
            print(f"  stock: {item.get('stock')}")
            print()
            
            # Format as backend does
            formatted = {
                'product_id': item.get('product_id'),
                'name': item.get('title'),
                'price': str(item.get('price')),
                'image_url': item.get('img_url'),
                'category': item.get('category'),
                'stock': item.get('stock')
            }
            print("Formatted for frontend:")
            print(formatted)
            print()
    else:
        print("❌ No items returned")
        
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
