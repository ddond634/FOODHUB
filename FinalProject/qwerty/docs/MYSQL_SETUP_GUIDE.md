# MySQL Migration & Setup Guide for Hub E-commerce System

## Overview
This guide covers migrating your system from SQLite to MySQL for production use. All system data (products, sales reports, accounts, orders) will be stored in MySQL.

## Prerequisites

### 1. MySQL Server Installation
You need MySQL Server 5.7+ or MySQL 8.0+

**Windows (XAMPP):**
- Download XAMPP from https://www.apachefriends.org/
- Install with MySQL included
- Start Apache & MySQL from XAMPP Control Panel

**Windows (Direct Installation):**
- Download from https://dev.mysql.com/downloads/mysql/
- Run installer and follow setup wizard
- Recommended port: 3306

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo mysql_secure_installation
```

**macOS:**
```bash
brew install mysql
brew services start mysql
mysql_secure_installation
```

### 2. Create MySQL Database
Login to MySQL and create the qwerty database:

```bash
mysql -u root -p
```

Then in MySQL prompt:
```sql
CREATE DATABASE qwerty CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SHOW DATABASES;
```

## Migration Steps

### Step 1: Verify SQLite Database Exists
The system currently uses SQLite with a file: `qwerty.db`

Check that it contains your data:
```bash
# From Windows PowerShell
sqlite3 "qwerty/db/qwerty.db" "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table';"
```

### Step 2: Update Environment Configuration

Edit `.env` file in the root directory:
```env
# Database Configuration - CHANGE TO MYSQL
DB_ENGINE=mysql
DB_HOST=127.0.0.1
DB_USER=root
DB_PASS=your_password_here
DB_NAME=qwerty
DB_PORT=3306

# Migration Flag
MIGRATE=1
```

**Note:** If using XAMPP with empty MySQL password, leave `DB_PASS=` empty.

### Step 3: Run Migration Script

```bash
# From Windows PowerShell in qwerty directory
python migrate_to_mysql.py
```

Expected output:
```
==============================================================
  Hub E-commerce System: SQLite to MySQL Migration
==============================================================

[*] Starting migration from SQLite to MySQL...
    SQLite DB: ./qwerty.db
    MySQL: root@127.0.0.1:3306/qwerty

[1] Connecting to MySQL...
    ✓ Connected to MySQL successfully
[2] Creating MySQL schema...
    ✓ Schema created/verified
[3] Connecting to SQLite...
    ✓ Connected to SQLite successfully
[4.1] Migrating table: users...
    ✓ Migrated X records
[4.2] Migrating table: products...
    ✓ Migrated Y records
...
[5] Verifying migrated data...
    users: X records
    products: Y records
    orders: Z records
    ...

[✓] Migration Complete!
    Total records migrated: XXXX

[!] Next steps:
    1. Verify all data in MySQL database
    2. Restart the Flask server
    3. Test all API endpoints
```

### Step 4: Verify Migration in MySQL

Open MySQL client and verify data:

```bash
mysql -u root -p qwerty
```

```sql
-- Check tables exist
SHOW TABLES;

-- Verify data counts
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as product_count FROM products;
SELECT COUNT(*) as order_count FROM orders;

-- Check sample data
SELECT id, email, first_name, role FROM users LIMIT 5;
SELECT id, title, price, stock FROM products LIMIT 5;
SELECT id, customer_name, total, status FROM orders LIMIT 5;

-- Check sales data
SELECT COUNT(*) as delivered_orders FROM orders WHERE status='delivered';
SELECT SUM(total) as total_revenue FROM orders WHERE status='delivered';

-- Check seller data
SELECT u.id, u.email, s.business_name, s.verified, COUNT(p.id) as product_count
FROM users u
LEFT JOIN sellers s ON u.id = s.user_id
LEFT JOIN products p ON u.id = p.seller_id
GROUP BY u.id
LIMIT 10;
```

### Step 5: Start the Server with MySQL

```bash
# From Windows PowerShell in qwerty/py files directory
python run_server.py
```

Expected output:
```
 * Running on http://127.0.0.1:5000
 * Using MySQL database: qwerty@127.0.0.1:3306
 * Schema verified/created
 * All tables initialized
```

## Important: Database Tables in MySQL

After migration, your MySQL database will contain:

### Core Tables (10 tables from original system)
1. **users** - All user accounts (admin, customer, seller, rider)
2. **sellers** - Seller profiles and verification status
3. **riders** - Rider profiles and verification status
4. **products** - All products listed for sale
5. **orders** - All orders placed
6. **order_items** - Line items in each order
7. **wishlist** - Customer wishlist items
8. **reviews** - Product reviews and ratings
9. **otp_codes** - One-time passwords for email verification
10. **refresh_tokens** - JWT refresh tokens for sessions

### Extended Tables (5 new tables)
1. **rider_locations** - Real-time rider location tracking
2. **proof_of_delivery** - Delivery photos and signatures
3. **disputes** - Order disputes and complaints
4. **rider_earnings** - Individual rider earnings per delivery
5. **rider_payouts** - Rider payment history

## Accessing System Data in MySQL

### Sales Reports
```sql
-- Daily sales
SELECT DATE(created_at) as sale_date, COUNT(*) as orders, SUM(total) as revenue
FROM orders
WHERE status='delivered'
GROUP BY DATE(created_at)
ORDER BY sale_date DESC;

-- Top selling products
SELECT p.id, p.title, COUNT(oi.id) as sales_count, SUM(oi.quantity) as units_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.id
GROUP BY p.id
ORDER BY units_sold DESC
LIMIT 10;

-- Seller revenue
SELECT u.email, s.business_name, COUNT(o.id) as order_count, SUM(o.subtotal) as revenue
FROM users u
JOIN sellers s ON u.id = s.user_id
LEFT JOIN products p ON u.id = p.seller_id
LEFT JOIN order_items oi ON p.id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.id
GROUP BY u.id
ORDER BY revenue DESC;
```

### Account Data
```sql
-- All user accounts
SELECT id, email, first_name, last_name, role, created_at FROM users;

-- Customer accounts with order history
SELECT u.id, u.email, COUNT(o.id) as order_count, SUM(o.total) as spent
FROM users u
LEFT JOIN orders o ON u.id = o.customer_id
WHERE u.role='customer'
GROUP BY u.id;

-- Seller accounts with product listings
SELECT u.id, u.email, s.business_name, s.verified, COUNT(p.id) as products
FROM users u
JOIN sellers s ON u.id = s.user_id
LEFT JOIN products p ON u.id = p.seller_id
GROUP BY u.id;

-- Rider accounts with delivery history
SELECT u.id, u.email, r.verified, r.vehicle_type, COUNT(DISTINCT o.id) as deliveries
FROM users u
JOIN riders r ON u.id = r.user_id
LEFT JOIN orders o ON o.status='delivered'
GROUP BY u.id;
```

### Product Data
```sql
-- All products
SELECT id, title, price, stock, category, seller_id, created_at FROM products;

-- Products by category
SELECT category, COUNT(*) as product_count, AVG(price) as avg_price, SUM(stock) as total_stock
FROM products
GROUP BY category
ORDER BY product_count DESC;

-- Low stock products
SELECT id, title, stock FROM products WHERE stock < 5 ORDER BY stock ASC;
```

## Troubleshooting

### Error: "Can't connect to MySQL server"

**Solution 1: Ensure MySQL is running**
- XAMPP: Start MySQL from control panel
- Command line: `mysql -u root -p` should work

**Solution 2: Check connection credentials in .env**
```env
DB_HOST=127.0.0.1   # or localhost
DB_USER=root
DB_PASS=            # Empty for XAMPP
DB_PORT=3306
```

**Solution 3: Check if database exists**
```bash
mysql -u root -p -e "SHOW DATABASES;"
```

If `qwerty` doesn't exist, create it:
```bash
mysql -u root -p -e "CREATE DATABASE qwerty CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Error: "Access denied for user 'root'@'localhost'"

**Solution:** Update .env with correct password:
```env
DB_PASS=your_actual_password
```

Or reset MySQL password:
```bash
# Linux/Mac
sudo mysqld_safe --skip-grant-tables &
mysql -u root
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
```

### Error: "Table already exists"

**Solution:** This is normal during migration. The schema creation step may report table exists errors - this is safe to ignore. Migration will proceed.

### Verification Failed - No Data Shows Up

**Solution 1:** Check if migration actually ran
```bash
python migrate_to_mysql.py
```

**Solution 2:** Verify SQLite had data
```bash
sqlite3 qwerty/db/qwerty.db "SELECT COUNT(*) FROM users;"
```

**Solution 3:** Check MySQL directly
```bash
mysql -u root -p qwerty -e "SELECT COUNT(*) FROM users;"
```

## Rollback (If Needed)

If you need to revert to SQLite:

1. Edit `.env`:
```env
DB_ENGINE=sqlite
```

2. Restart server:
```bash
python run_server.py
```

**Note:** SQLite file (`qwerty.db`) is unchanged, so all data is still there.

## Performance Considerations for MySQL

1. **Connection Pooling:** Add connection pool in production
   ```python
   from flask_mysqldb import MySQL
   # See MySQL connection pooling docs
   ```

2. **Query Optimization:** Add indexes for frequently queried columns
   ```sql
   CREATE INDEX idx_user_email ON users(email);
   CREATE INDEX idx_product_seller ON products(seller_id);
   CREATE INDEX idx_order_status ON orders(status);
   CREATE INDEX idx_order_created ON orders(created_at);
   ```

3. **Regular Backups:** Set up automated MySQL backups
   ```bash
   mysqldump -u root -p qwerty > qwerty_backup_$(date +%Y%m%d).sql
   ```

## API Verification

After migration, test these endpoints to verify all data is accessible:

```bash
# List all products (should show migrated products)
curl http://127.0.0.1:5000/api/products

# List all orders (should show migrated orders)
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:5000/api/orders

# Get product details (should show seller_id from MySQL)
curl http://127.0.0.1:5000/api/products/1

# Sales analytics (should show data from MySQL)
curl -H "Authorization: Bearer ADMIN_TOKEN" http://127.0.0.1:5000/api/admin/dashboard
```

## Next Steps

1. ✅ Run migration script
2. ✅ Verify data in MySQL
3. ✅ Update .env with DB_ENGINE=mysql
4. ✅ Start server and test endpoints
5. ✅ Monitor error logs during testing
6. ✅ Set up automated backups
7. ✅ Deploy to production with MySQL configuration

## Support

For issues with MySQL migration:
1. Check error logs: `tail -100 server.log`
2. Verify MySQL is running and accessible
3. Confirm database credentials in `.env`
4. Check that `qwerty` database exists
5. Verify PyMySQL is installed: `pip install PyMySQL==1.1.0`

---

**Migration Date:** [Run migration on your date]
**System:** Hub E-commerce & ERP
**Status:** ✅ Ready for Production MySQL Deployment
