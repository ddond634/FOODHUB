# MySQL Setup Instructions for qwerty database

## Prerequisites
1. MySQL Server installed and running (XAMPP, MySQL Workbench, or standalone)
2. MySQL credentials (default: root with no password)

## Setup Steps

### Option 1: Using MySQL Command Line
```bash
# 1. Login to MySQL
mysql -u root -p

# 2. Create database
CREATE DATABASE qwerty CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 3. Exit MySQL
exit;

# 4. Import schema
mysql -u root -p qwerty < database/schema_mysql.sql
```

### Option 2: Using Python Script
Run the setup script:
```bash
python scripts/setup_mysql.py
```

### Option 3: Using XAMPP phpMyAdmin
1. Open phpMyAdmin (http://localhost/phpmyadmin)
2. Click "New" to create database
3. Database name: `qwerty`
4. Collation: `utf8mb4_unicode_ci`
5. Click "Create"
6. Click "Import" tab
7. Choose file: `database/schema_mysql.sql`
8. Click "Go"

## Environment Variables (Optional)
If your MySQL uses different credentials, set these before running:

```powershell
# PowerShell
$env:DB_ENGINE = 'mysql'
$env:DB_HOST = '127.0.0.1'
$env:DB_USER = 'root'
$env:DB_PASS = 'your_password'
$env:DB_NAME = 'qwerty'
$env:DB_PORT = '3306'
```

## Verify Setup
After importing, verify tables were created:
```bash
mysql -u root -p qwerty -e "SHOW TABLES;"
```

You should see ~20 tables including:
- users
- sellers
- riders
- products
- orders
- order_items
- etc.

## Start Server
Once database is ready:
```bash
python run.py
```

The server will connect to MySQL automatically (DB_ENGINE defaults to 'mysql').
