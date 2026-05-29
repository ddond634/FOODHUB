# Script to delete products with missing images from MySQL
import pymysql
import os

# Database connection settings (update if needed)
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', '')
DB_NAME = os.environ.get('DB_NAME', 'qwerty')
DB_PORT = int(os.environ.get('DB_PORT', '3306'))

missing_images = [
    '2_20251125_112327_ba2b02fc.jpg',
    '2_20251127_105042_cf085bbb.jpeg'
]

try:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4'
    )
    with conn.cursor() as cursor:
        # Find products to delete
        sql_select = "SELECT id, name, image_url FROM products WHERE image_url IN (%s, %s)"
        cursor.execute(sql_select, missing_images)
        products = cursor.fetchall()
        if not products:
            print('No products found with missing images.')
        else:
            print('Deleting the following products:')
            for p in products:
                print(f"ID: {p['id']}, Name: {p['name']}, Image: {p['image_url']}")
            # Delete products
            sql_delete = "DELETE FROM products WHERE image_url IN (%s, %s)"
            cursor.execute(sql_delete, missing_images)
            conn.commit()
            print(f"Deleted {cursor.rowcount} products.")
finally:
    conn.close()
