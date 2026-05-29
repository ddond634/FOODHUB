# Hub E-commerce System - MySQL Production Deployment

## Quick Start: Migrate to MySQL

This system now includes complete MySQL support for production deployments. All system content (products, sales reports, accounts) can be stored in MySQL.

### Requirements
- MySQL 5.7+ or MySQL 8.0+
- Python 3.7+
- PyMySQL library (included in requirements.txt)

### 3-Step Migration

#### Step 1: Create MySQL Database
```bash
mysql -u root -p
```

```sql
CREATE DATABASE qwerty CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

#### Step 2: Configure Environment
Edit `.env` in the root directory:
```env
DB_ENGINE=mysql
DB_HOST=127.0.0.1
DB_USER=root
DB_PASS=
DB_NAME=qwerty
DB_PORT=3306
MIGRATE=1
```

#### Step 3: Run Migration
```bash
# From Windows PowerShell
python migrate_to_mysql.py
```

Expected output:
```
==============================================================
  Hub E-commerce System: SQLite to MySQL Migration
==============================================================

[*] Starting migration from SQLite to MySQL...
[1] Connecting to MySQL...
    ✓ Connected to MySQL successfully
[2] Creating MySQL schema...
    ✓ Schema created/verified
[3] Connecting to SQLite...
    ✓ Connected to SQLite successfully
[4.1] Migrating table: users...
    ✓ Migrated X records
...
[5] Verifying migrated data...
    users: X records
    products: Y records
    orders: Z records

[✓] Migration Complete!
    Total records migrated: XXXX
```

### Start Server with MySQL
```bash
python run_server.py
```

The server will now use MySQL for all operations.

### Verify Migration Success
```bash
python verify_mysql_data.py
```

This will show:
- ✓ Account data (users, sellers, riders)
- ✓ Product inventory
- ✓ Sales reports and revenue
- ✓ Order data
- ✓ Database schema validation

## MySQL Data Structure

After migration, you have a complete MySQL database with:

### User Accounts (From `users` table)
- All registered users (admin, customer, seller, rider)
- Email, password hash, roles
- Account creation timestamps

Example query:
```sql
SELECT id, email, role, created_at FROM users;
```

### Products (From `products` table)
- All items for sale with:
  - Title, description, price, stock
  - Seller information (via seller_id)
  - Category, image URL
  - Creation timestamp

Example query:
```sql
SELECT id, title, price, stock, category, seller_id FROM products LIMIT 10;
```

### Sales Reports (From `orders` & `order_items` tables)
- Complete order history with:
  - Customer info, delivery address
  - Order total, payment status
  - Current delivery status
  - Creation and update timestamps
- Individual line items with quantities and prices

Example query (Daily Sales):
```sql
SELECT DATE(created_at) as date, COUNT(*) as orders, SUM(total) as revenue
FROM orders
WHERE status='delivered'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

Example query (Revenue by Seller):
```sql
SELECT 
    u.email, s.business_name,
    COUNT(oi.id) as items_sold,
    SUM(oi.quantity * oi.price) as revenue
FROM products p
JOIN users u ON p.seller_id = u.id
LEFT JOIN sellers s ON u.id = s.user_id
LEFT JOIN order_items oi ON p.id = oi.product_id
GROUP BY u.id
ORDER BY revenue DESC;
```

### Account Management (From `users` & `sellers`/`riders` tables)
- Seller profiles with business info and verification status
- Rider profiles with vehicle info and verification status
- All tracked through user accounts

Example query (Seller Accounts):
```sql
SELECT 
    u.id, u.email, s.business_name, s.verified, COUNT(p.id) as products
FROM users u
JOIN sellers s ON u.id = s.user_id
LEFT JOIN products p ON u.id = p.seller_id
WHERE u.role='seller'
GROUP BY u.id;
```

## Complete Feature List in MySQL

- ✅ **15 Database Tables** with proper relationships
- ✅ **User Management** - 4 roles (admin, customer, seller, rider)
- ✅ **Product Catalog** - Full inventory with stock tracking
- ✅ **Order Management** - Complete order lifecycle
- ✅ **Sales Analytics** - Revenue tracking by date, product, seller
- ✅ **User Verification** - Admin approval system for sellers/riders
- ✅ **OTP System** - Email verification codes
- ✅ **JWT Sessions** - Token-based authentication with refresh
- ✅ **Rider Tracking** - Location, earnings, payouts
- ✅ **Delivery Proof** - Photo and signature storage
- ✅ **Dispute Management** - Order complaint tracking
- ✅ **Wishlist** - Customer saved items
- ✅ **Reviews** - Product ratings and feedback

## API Endpoints Work with MySQL

All API endpoints automatically work with MySQL:

```bash
# Register account
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Doe",
  "role": "customer"
}

# Browse products (from MySQL)
GET /api/products

# Create seller product
POST /api/sellers/products
{
  "title": "Product Name",
  "description": "...",
  "price": 99.99,
  "stock": 50,
  "category": "Electronics"
}

# Place order
POST /api/orders
{
  "items": [{"product_id": 1, "quantity": 2}],
  "delivery_address": "..."
}

# View sales dashboard
GET /api/sellers/dashboard

# Get revenue analytics
GET /api/admin/dashboard
```

All data is transparently stored in and retrieved from MySQL.

## Important Notes

### Default Database Engine
- **SQLite** (local development): `DB_ENGINE=sqlite` in .env
- **MySQL** (production): `DB_ENGINE=mysql` in .env (default)

The system automatically detects the configured engine and routes all operations accordingly.

### Data Safety
- Migration script does NOT delete SQLite data
- SQLite file (`qwerty.db`) remains unchanged
- You can revert to SQLite by changing .env back to `DB_ENGINE=sqlite`

### Performance
- MySQL is much faster for large datasets (100k+ records)
- Better for concurrent users
- Supports connection pooling
- Suitable for production deployments

### Backup
Always backup MySQL before making changes:
```bash
mysqldump -u root -p qwerty > backup_$(date +%Y%m%d_%H%M%S).sql
```

Restore from backup:
```bash
mysql -u root -p qwerty < backup_20231120_143022.sql
```

## Troubleshooting

### Q: Server won't connect to MySQL
**A:** Check .env configuration and that MySQL is running:
```bash
mysql -u root -p -e "SELECT 1"
```

### Q: Migration ran but no data appears
**A:** Verify SQLite had data and migration completed:
```bash
# Check SQLite
sqlite3 qwerty/db/qwerty.db "SELECT COUNT(*) FROM users;"

# Check MySQL
mysql -u root -p -e "USE qwerty; SELECT COUNT(*) FROM users;"
```

### Q: Some tables are missing in MySQL
**A:** Run migration again - it creates missing tables:
```bash
python migrate_to_mysql.py
```

### Q: Want to add MySQL-specific features later
**A:** You can add indexes, views, and triggers:
```sql
-- Add index for fast searches
CREATE INDEX idx_product_title ON products(title);

-- Create a sales view
CREATE VIEW v_daily_sales AS
SELECT DATE(created_at) as date, COUNT(*) as orders, SUM(total) as revenue
FROM orders
WHERE status='delivered'
GROUP BY DATE(created_at);
```

## Files Included for MySQL

1. **migrate_to_mysql.py** - Migration script
   - Copies all data from SQLite to MySQL
   - Creates schema automatically
   - Handles relationships and foreign keys

2. **verify_mysql_data.py** - Verification tool
   - Checks all data migrated correctly
   - Shows product counts
   - Displays sales reports
   - Validates account data

3. **MYSQL_SETUP_GUIDE.md** - Detailed setup documentation
   - Step-by-step instructions
   - SQL query examples
   - Troubleshooting guide

4. **.env** - Configuration file
   - Set DB_ENGINE=mysql
   - Configure connection details
   - Ready for your MySQL server

5. **qwerty/db/schema_mysql.sql** - MySQL schema
   - All 15 tables
   - Foreign key relationships
   - Proper data types

## Next Steps

1. ✅ Create MySQL database (see Step 1 above)
2. ✅ Configure .env file
3. ✅ Run `python migrate_to_mysql.py`
4. ✅ Run `python verify_mysql_data.py`
5. ✅ Start server: `python run_server.py`
6. ✅ Test API endpoints
7. ✅ Monitor production usage

## Production Deployment

For production:

1. **Use dedicated MySQL server** (not localhost)
2. **Set strong password** in DB_PASS
3. **Use environment variables** for credentials (not in .env)
4. **Enable SSL** for database connections
5. **Set up automated backups**
6. **Monitor performance** with slow query log
7. **Create read replicas** for large scale
8. **Implement connection pooling**

Example production .env:
```env
DB_ENGINE=mysql
DB_HOST=mysql.production.com
DB_USER=hub_user
DB_PASS=${MYSQL_PASSWORD}  # From environment variable
DB_NAME=hub_production
DB_PORT=3306
MIGRATE=0  # Don't auto-migrate in production
```

---

**Status:** ✅ Ready for MySQL Production Deployment
**Last Updated:** 2024
**Support:** See MYSQL_SETUP_GUIDE.md for detailed help
