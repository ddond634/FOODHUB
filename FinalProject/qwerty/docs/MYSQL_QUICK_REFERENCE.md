# MySQL Quick Reference - Commands & Queries

## Quick MySQL Commands

### Connect to MySQL
```bash
# Interactive shell
mysql -u root -p

# Non-interactive (password at prompt)
mysql -u root -p qwerty

# Check if running
mysql -u root -p -e "SELECT 1"
```

### Create Database
```bash
mysql -u root -p -e "CREATE DATABASE qwerty CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Check Current Connection
```sql
-- Inside MySQL prompt
SELECT USER();
SELECT DATABASE();
SHOW TABLES;
```

---

## Data Verification Queries

### User Accounts
```sql
-- Count users by role
SELECT role, COUNT(*) FROM users GROUP BY role;

-- All users
SELECT id, email, first_name, last_name, role FROM users;

-- Recent registrations
SELECT * FROM users ORDER BY created_at DESC LIMIT 10;

-- Admin users
SELECT * FROM users WHERE role='admin';

-- Sellers with products
SELECT u.id, u.email, s.business_name, COUNT(p.id) as products
FROM users u
LEFT JOIN sellers s ON u.id = s.user_id
LEFT JOIN products p ON u.id = p.seller_id
WHERE u.role='seller'
GROUP BY u.id;
```

### Products
```sql
-- All products
SELECT id, title, price, stock, category FROM products;

-- Product count
SELECT COUNT(*) FROM products;

-- Products by category
SELECT category, COUNT(*) as count FROM products GROUP BY category;

-- Low stock products
SELECT id, title, stock FROM products WHERE stock < 5;

-- Out of stock
SELECT id, title FROM products WHERE stock = 0;

-- Product price range
SELECT MIN(price) as min, MAX(price) as max, AVG(price) as avg FROM products;
```

### Sales & Revenue
```sql
-- All orders
SELECT id, customer_name, total, status FROM orders;

-- Order count
SELECT COUNT(*) FROM orders;

-- Orders by status
SELECT status, COUNT(*) as count FROM orders GROUP BY status;

-- Total revenue (all completed)
SELECT SUM(total) as total_revenue FROM orders WHERE status='delivered';

-- Daily sales
SELECT DATE(created_at) as date, COUNT(*) as orders, SUM(total) as revenue
FROM orders WHERE status='delivered'
GROUP BY DATE(created_at) ORDER BY date DESC;

-- Seller revenue
SELECT u.email, s.business_name, SUM(oi.quantity * oi.price) as revenue
FROM products p
JOIN users u ON p.seller_id = u.id
LEFT JOIN sellers s ON u.id = s.user_id
LEFT JOIN order_items oi ON p.id = oi.product_id
WHERE oi.price IS NOT NULL
GROUP BY u.id
ORDER BY revenue DESC;

-- Top products sold
SELECT p.title, SUM(oi.quantity) as units, SUM(oi.price * oi.quantity) as revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.id
GROUP BY oi.product_id
ORDER BY units DESC LIMIT 10;

-- Average order value
SELECT AVG(total) as avg_order_value FROM orders WHERE status='delivered';

-- Customer spending
SELECT customer_name, COUNT(*) as orders, SUM(total) as spent
FROM orders WHERE status='delivered'
GROUP BY customer_id ORDER BY spent DESC LIMIT 10;
```

### Detailed Order Info
```sql
-- Single order with items
SELECT o.id, o.customer_name, o.total, COUNT(oi.id) as items
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
WHERE o.id = 1
GROUP BY o.id;

-- Order items for specific order
SELECT oi.id, p.title, oi.quantity, oi.price, (oi.quantity * oi.price) as line_total
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.order_id = 1;

-- Recent orders with details
SELECT o.id, o.customer_name, COUNT(oi.id) as items, SUM(oi.price * oi.quantity) as total, o.status
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id
ORDER BY o.created_at DESC LIMIT 20;
```

---

## System Operations

### Backup
```bash
# Backup entire database
mysqldump -u root -p qwerty > backup.sql

# Backup specific table
mysqldump -u root -p qwerty products > products_backup.sql

# Backup with timestamp
mysqldump -u root -p qwerty > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore
```bash
# Restore entire database
mysql -u root -p qwerty < backup.sql

# Restore specific table
mysql -u root -p qwerty < products_backup.sql
```

### Export to CSV
```bash
# Export users
SELECT * FROM users INTO OUTFILE '/tmp/users.csv' 
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';

# Export products
SELECT id, title, price, stock FROM products INTO OUTFILE '/tmp/products.csv'
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';

# Export orders
SELECT * FROM orders INTO OUTFILE '/tmp/orders.csv'
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n';
```

### Database Maintenance
```sql
-- Check table sizes
SELECT table_name, ROUND(((data_length + index_length) / 1024 / 1024), 2) as size_mb
FROM information_schema.tables WHERE table_schema='qwerty';

-- Optimize tables (defragment)
OPTIMIZE TABLE users, products, orders, order_items;

-- Repair table if corrupted
REPAIR TABLE users;

-- Analyze table statistics
ANALYZE TABLE products;

-- Show table status
SHOW TABLE STATUS FROM qwerty;
```

---

## Performance Queries

### Slow Queries
```sql
-- Find slow queries (if slow query log enabled)
SELECT * FROM mysql.slow_log;

-- Manual timing
SELECT COUNT(*) FROM orders WHERE status='delivered';  -- Check time

-- Check query plan
EXPLAIN SELECT * FROM orders WHERE status='delivered';
```

### Add Indexes (for speed)
```sql
-- Create indexes for common queries
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);
CREATE INDEX idx_products_seller ON products(seller_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_products_category ON products(category);

-- Check existing indexes
SHOW INDEXES FROM orders;
SHOW INDEXES FROM products;
```

### Connection Info
```sql
-- Show max connections
SHOW VARIABLES LIKE 'max_connections';

-- Show current connections
SHOW PROCESSLIST;

-- Show database size
SELECT SUM(data_length + index_length) / 1024 / 1024 as size_mb FROM information_schema.tables WHERE table_schema='qwerty';
```

---

## Data Cleanup & Maintenance

### Delete Operations (Be Careful!)
```sql
-- Delete old orders (older than 1 year)
DELETE FROM orders WHERE created_at < DATE_SUB(NOW(), INTERVAL 1 YEAR);

-- Delete cancelled orders
DELETE FROM orders WHERE status='cancelled' AND created_at < DATE_SUB(NOW(), INTERVAL 3 MONTH);

-- Clear OTP codes (older than 1 hour)
DELETE FROM otp_codes WHERE created_at < DATE_SUB(NOW(), INTERVAL 1 HOUR);

-- Clear refresh tokens (expired)
DELETE FROM refresh_tokens WHERE expires_at < NOW();
```

### Update Operations
```sql
-- Mark old riders as inactive
UPDATE riders SET verified = 0 WHERE id IN (
    SELECT r.id FROM riders r 
    LEFT JOIN orders o ON r.id = o.rider_id
    WHERE o.id IS NULL AND r.created_at < DATE_SUB(NOW(), INTERVAL 6 MONTH)
);

-- Recalculate product stock
UPDATE products SET stock = (
    SELECT total_stock FROM (
        SELECT product_id, SUM(qty) as total_stock FROM inventory_movements
        GROUP BY product_id
    ) as calc
    WHERE calc.product_id = products.id
);
```

---

## Troubleshooting Queries

### Check Data Integrity
```sql
-- Find orders with missing customer info
SELECT id FROM orders WHERE customer_id IS NULL AND customer_name IS NULL;

-- Find products with no seller
SELECT id, title FROM products WHERE seller_id IS NULL;

-- Find orphaned order items
SELECT oi.id FROM order_items oi
LEFT JOIN products p ON oi.product_id = p.id
WHERE p.id IS NULL;

-- Check for duplicate users
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
```

### Verify Relationships
```sql
-- Check seller references
SELECT u.id FROM users u WHERE u.role='seller' 
AND u.id NOT IN (SELECT user_id FROM sellers);

-- Check rider references
SELECT u.id FROM users u WHERE u.role='rider'
AND u.id NOT IN (SELECT user_id FROM riders);

-- Check all foreign keys
SHOW CREATE TABLE order_items;
```

---

## Useful Views (Optional - Create for Reports)

```sql
-- Create daily sales view
CREATE OR REPLACE VIEW v_daily_sales AS
SELECT DATE(o.created_at) as sale_date, COUNT(*) as orders, SUM(o.total) as revenue
FROM orders o WHERE o.status='delivered'
GROUP BY DATE(o.created_at);

-- Query view
SELECT * FROM v_daily_sales ORDER BY sale_date DESC;

-- Create seller revenue view
CREATE OR REPLACE VIEW v_seller_revenue AS
SELECT u.email, s.business_name, COUNT(oi.id) as items_sold, SUM(oi.price * oi.quantity) as revenue
FROM products p
JOIN users u ON p.seller_id = u.id
LEFT JOIN sellers s ON u.id = s.user_id
LEFT JOIN order_items oi ON p.id = oi.product_id
GROUP BY u.id;

-- Create product sales view
CREATE OR REPLACE VIEW v_product_sales AS
SELECT p.id, p.title, COUNT(oi.id) as times_sold, SUM(oi.quantity) as units_sold, SUM(oi.price * oi.quantity) as revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.id
GROUP BY oi.product_id;
```

---

## Quick Status Check

```bash
# All in one: check if MySQL is working
mysql -u root -p qwerty -e "
    SELECT CONCAT('Users: ', COUNT(*)) FROM users;
    SELECT CONCAT('Products: ', COUNT(*)) FROM products;
    SELECT CONCAT('Orders: ', COUNT(*)) FROM orders;
"
```

---

## Emergency Procedures

### Reset Database
```bash
# Backup first!
mysqldump -u root -p qwerty > emergency_backup.sql

# Drop and recreate
mysql -u root -p -e "DROP DATABASE qwerty; CREATE DATABASE qwerty CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Re-run migration
python migrate_to_mysql.py
```

### Check Connection Issues
```bash
# Test connection
mysql -u root -p -e "SELECT 1" 2>&1

# Check MySQL is running
ps aux | grep mysql

# Check listening ports
netstat -an | grep 3306

# Verify .env configuration
cat .env | grep DB_
```

---

**Tip:** Save this file and use it as your MySQL reference guide.
**Status:** ✅ All data is in MySQL - System ready for production.
