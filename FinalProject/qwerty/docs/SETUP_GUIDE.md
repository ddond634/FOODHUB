# Hub E-Commerce Platform - Complete Setup Guide

## System Requirements
- Python 3.8+
- SQLite3 (built-in) or MySQL 5.7+
- Windows, macOS, or Linux

## Installation Steps

### Step 1: Clone/Download Project
```powershell
cd c:\Users\USER\Downloads\qwerty
```

### Step 2: Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r qwerty\requirements.txt
```

### Step 4: Configure Environment
```powershell
# Copy the example environment file
Copy-Item qwerty\.env.example qwerty\.env

# Edit .env with your settings
# Optional: Configure email settings for OTP verification
```

### Step 5: Initialize Database

#### Option A: SQLite (Default - No Setup Required)
Database will be created automatically on first run.

#### Option B: MySQL with XAMPP
1. Start XAMPP Control Panel
2. Start Apache and MySQL
3. Open phpMyAdmin: http://localhost/phpmyadmin
4. Create database: `qwerty`
5. Import schema: Go to Import tab → Select `qwerty\db\schema_mysql.sql`
6. Set environment variables in `.env`:
```
DB_ENGINE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=
DB_NAME=qwerty
```

### Step 6: Start Server
```powershell
cd py\ files
python run_server.py
```

Server will start at: http://127.0.0.1:5000

---

## Project Structure

```
qwerty/
├── py files/
│   ├── server.py              # Main Flask app
│   ├── auth.py                # JWT authentication
│   ├── run_server.py          # Entry point
│   ├── email_service.py       # Email & OTP service (NEW)
│   ├── validators.py          # Input validation (NEW)
│   ├── api_utils.py           # API utilities (NEW)
│   └── additional_endpoints.py # Extra endpoints (NEW)
├── templates/
│   ├── index.html
│   ├── loginregister.html
│   ├── cart.html
│   ├── seller_dashboard.html
│   ├── rider_dashboard.html
│   ├── admin_dashboard.html
│   └── [other templates]
├── static/
│   ├── css/
│   │   ├── style.css
│   │   ├── admin_dashboard.css
│   │   └── [other styles]
│   └── js/
│       ├── script.js
│       ├── admin_dashboard.js
│       └── [other scripts]
├── db/
│   ├── schema.sql             # SQLite schema
│   └── schema_mysql.sql       # MySQL schema
├── .env                       # Configuration (not in git)
├── .env.example              # Configuration template (NEW)
├── requirements.txt          # Python dependencies
├── MISSING_FEATURES.md       # Feature roadmap (NEW)
└── API_DOCUMENTATION.md      # API reference (NEW)
```

---

## Configuration Guide

### Email Service Configuration
For OTP verification emails to work:

#### Using Gmail:
1. Enable 2-Factor Authentication on Gmail account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. In `.env`:
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
SENDER_NAME=Hub E-Commerce
```

#### Using SendGrid:
```
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
EMAIL_ADDRESS=apikey
EMAIL_PASSWORD=SG.your-sendgrid-api-key
```

### Development Mode (No Email)
Leave EMAIL_ADDRESS and EMAIL_PASSWORD empty. OTP codes will be logged to console:
```
[DEV MODE] Email to user@example.com: Subject...
OTP Code: 123456
```

---

## Database Schema

### Key Tables Created

**users**
- id, email (UNIQUE), password_hash, first_name, last_name, role, created_at

**sellers**
- id, user_id (UNIQUE FK), business_name, category, region, province, city, verified, created_at

**riders**
- id, user_id (UNIQUE FK), vehicle_type, driver_license, plate_number, verified, created_at

**products**
- id, title, description, price, stock, seller_id (FK), category, img_url, created_at

**orders**
- id, customer_id (FK), customer_name, customer_phone, customer_address, subtotal, delivery_fee, total, payment, status, created_at

**order_items**
- id, order_id (FK), product_id (FK), quantity, price

**purchase_orders** (ERP)
- id, supplier_id (FK), status, created_at

**purchase_order_items**
- id, po_id (FK), product_id (FK), quantity, price

**inventory_movements**
- id, product_id (FK), qty, movement_type, ref, created_at

**refresh_tokens**
- id, user_id (FK), token_hash, expires_at, revoked, created_at

---

## API Endpoints Overview

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/auth/logout` - Logout
- `POST /api/auth/change-password` - Change password

### Products
- `GET /api/products` - List products
- `GET /api/products/<id>` - Get product details
- `GET /api/products/search?q=query` - Search products
- `GET /api/products/filter?category=X&price_min=Y` - Filter products

### Orders
- `POST /api/orders` - Create order
- `GET /api/orders/<id>` - Get order details
- `GET /api/orders/<id>/track` - Track order
- `POST /api/orders/<id>/status` - Update order status
- `GET /api/users/<id>/orders` - Get user's orders

### Users
- `GET /api/users/<id>` - Get user profile
- `PUT /api/users/<id>` - Update profile
- `GET /api/users` - List users (admin)

### Sellers
- `GET /api/sellers/<id>` - Get seller profile
- `GET /api/seller/products` - List seller's products
- `POST /api/seller/products` - Create product
- `GET /api/seller/dashboard` - Seller dashboard

### Riders
- `GET /api/riders/<id>` - Get rider profile
- `GET /api/rider/dashboard` - Rider dashboard
- `GET /api/rider/earnings` - Rider earnings

### Admin
- `GET /api/admin/dashboard` - Admin dashboard
- `GET /api/admin/orders` - List all orders

### ERP/Inventory
- `GET /api/erp/purchase_orders` - List POs
- `POST /api/erp/po/<id>/confirm` - Confirm PO
- `POST /api/erp/po/<id>/receive` - Receive PO
- `GET /api/inventory/movements` - Inventory history

### Other
- `GET /api/suppliers` - List suppliers
- `GET /api/health` - Health check
- `GET /api/wishlist` - Get wishlist
- `POST /api/wishlist/<id>` - Add to wishlist
- `DELETE /api/wishlist/<id>` - Remove from wishlist

**Full documentation**: See `API_DOCUMENTATION.md`

---

## Testing the System

### 1. Test User Registration
```bash
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "role": "customer",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 2. Test Login
```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### 3. Browse Products
Visit: http://127.0.0.1:5000

### 4. Test API with Token
```bash
curl -X GET http://127.0.0.1:5000/api/users/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Running Tests

```powershell
# Run all tests
pytest

# Run specific test file
pytest py\ files\test_server.py

# Run with coverage
pytest --cov=. py\ files\test_server.py
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution**: Make sure virtual environment is activated and requirements installed
```powershell
.\venv\Scripts\Activate.ps1
pip install -r qwerty\requirements.txt
```

### Issue: "Address already in use"
**Solution**: Server already running on port 5000. Change port in `run_server.py` or kill existing process
```powershell
Get-Process python | Stop-Process -Force
```

### Issue: "Static files returning 404"
**Solution**: Ensure static folder path is correct
```powershell
# Check folder exists
Test-Path "qwerty\static"
Test-Path "qwerty\templates"
```

### Issue: Database connection error
**Solution**: Check `.env` settings
```powershell
# For SQLite - verify file exists
Test-Path "qwerty.db"

# For MySQL - verify XAMPP is running and database exists
```

### Issue: Email not sending
**Solution**: 
1. Check SMTP credentials in `.env`
2. If using Gmail, use App Password (not regular password)
3. Leave email settings empty to use development mode

---

## Next Steps to Complete System

### High Priority
1. ✅ Email & OTP service - DONE
2. ✅ Input validators - DONE
3. ✅ API utilities - DONE
4. ✅ Additional endpoints - DONE
5. ✅ API documentation - DONE
6. ⏳ Integrate additional endpoints into server.py
7. ⏳ Update frontend auth handlers to use real APIs
8. ⏳ Create OTP/email verification table in database

### Medium Priority
9. Create notifications system
10. Create review/rating system
11. Add payment integration
12. Create dashboard analytics endpoints
13. Add file upload functionality

### Low Priority
14. Advanced reporting
15. Performance optimization
16. Security hardening

---

## Production Deployment Checklist

- [ ] Change all secrets in `.env`
- [ ] Set `FLASK_ENV=production`
- [ ] Set `FLASK_DEBUG=False`
- [ ] Use production WSGI server (gunicorn, uWSGI)
- [ ] Use PostgreSQL or MySQL (not SQLite)
- [ ] Configure proper email service
- [ ] Set up SSL/HTTPS
- [ ] Configure logging
- [ ] Set up database backups
- [ ] Configure CDN for static files
- [ ] Set up monitoring and alerts

---

## Support & Documentation

- **API Documentation**: `API_DOCUMENTATION.md`
- **Missing Features**: `MISSING_FEATURES.md`
- **Backend README**: `README_BACKEND.md`
- **JWT Guide**: `JWT_AUTH_IMPLEMENTATION.md`

