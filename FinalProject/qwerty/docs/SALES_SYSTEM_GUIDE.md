# Sales & Discount System Documentation

## Overview
Smart discount system for expiring food/beverage products with seller-admin approval workflow.

## Business Logic

### Profit Protection Formula
```
Estimated Seller Cost = Product Price × 65%
Platform Commission = Product Price × 7.5%
Minimum Viable Price = Cost + Commission
Seller Profit Margin = ((Sale Price - Commission - Cost) / Cost) × 100%
```

### Discount Tiers by Expiry Urgency

| Days Until Expiry | Suggested Discount | Rationale |
|-------------------|-------------------|-----------|
| 14+ days | 10% | Early promotion |
| 10-14 days | 15% | Moderate discount |
| 7-10 days | 20% | Significant discount (1 week) |
| 5-7 days | 25% | Steep discount |
| 3-5 days | 30% | Urgent discount |
| 1-3 days | 35% | Maximum discount |
| 0-1 days | 40% | Clearance |

**Note**: System ensures discounts never go below cost + commission + 10% minimum margin.

## Database Schema

### `product_sales` table
Stores all sale requests and their status.

```sql
CREATE TABLE product_sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    discount_percentage DECIMAL(5,2) NOT NULL,
    original_price DECIMAL(10,2) NOT NULL,
    sale_price DECIMAL(10,2) NOT NULL,
    reason VARCHAR(50) DEFAULT 'expiring_soon',
    status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected
    days_until_expiry INT,
    seller_profit_margin DECIMAL(5,2),
    platform_commission DECIMAL(5,2) DEFAULT 7.50,
    seller_requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    admin_approved_at DATETIME NULL,
    admin_rejected_at DATETIME NULL,
    valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
    valid_until DATETIME NULL,
    requested_by INT,
    approved_by INT NULL,
    admin_notes TEXT,
    is_active BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by) REFERENCES users(id),
    FOREIGN KEY (approved_by) REFERENCES users(id)
);
```

### `sale_suggestions` table
Auto-generated suggestions for sellers.

```sql
CREATE TABLE sale_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    suggested_discount DECIMAL(5,2) NOT NULL,
    suggested_price DECIMAL(10,2) NOT NULL,
    days_until_expiry INT NOT NULL,
    reason TEXT,
    seller_id INT NOT NULL,
    notification_sent BOOLEAN DEFAULT 0,
    seller_viewed BOOLEAN DEFAULT 0,
    seller_action VARCHAR(20) DEFAULT 'pending',  -- pending/accepted/rejected
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES users(id)
);
```

## API Endpoints

### Seller Endpoints

#### 1. Get Sale Suggestions
**GET** `/api/sellers/sale-suggestions`
- Auth: Required (Seller)
- Returns: List of expiring products with calculated discount suggestions

**Response:**
```json
{
  "success": true,
  "data": {
    "suggestions": [
      {
        "product_id": 123,
        "product_title": "Organic Milk",
        "current_price": 150.00,
        "stock": 25,
        "expiry_date": "2025-12-05",
        "days_until_expiry": 8,
        "suggested_discount": 20.00,
        "sale_price": 120.00,
        "seller_profit_margin": 15.5,
        "platform_commission_pct": 7.5,
        "estimated_cost": 97.50,
        "seller_revenue": 111.00,
        "seller_profit": 13.50,
        "rationale": "Significant discount - 1 week until expiry"
      }
    ],
    "total_products": 1
  },
  "message": "Sale suggestions generated"
}
```

#### 2. Request Sale/Discount
**POST** `/api/sellers/products/:product_id/request-sale`
- Auth: Required (Seller)
- Body: `{ "discount_percentage": 20, "reason": "expiring_soon" }`

**Response:**
```json
{
  "success": true,
  "data": {
    "sale_id": 456,
    "product_id": 123,
    "status": "pending",
    "discount_percentage": 20.0,
    "sale_price": 120.00,
    "suggested_discount": 20.0
  },
  "message": "Sale request submitted for admin approval"
}
```

### Admin Endpoints

#### 3. Get Pending Sales
**GET** `/api/admin/pending-sales`
- Auth: Required (Admin)
- Returns: All pending sale requests

**Response:**
```json
{
  "success": true,
  "data": {
    "pending_sales": [
      {
        "id": 456,
        "product_id": 123,
        "product_title": "Organic Milk",
        "product_image": "/uploads/milk.jpg",
        "discount_percentage": 20.0,
        "original_price": 150.00,
        "sale_price": 120.00,
        "days_until_expiry": 8,
        "seller_profit_margin": 15.5,
        "platform_commission": 7.5,
        "seller_email": "seller@example.com",
        "seller_name": "Fresh Foods Store",
        "seller_requested_at": "2025-11-27T10:30:00"
      }
    ],
    "total": 1
  }
}
```

#### 4. Approve Sale
**POST** `/api/admin/sales/:sale_id/approve`
- Auth: Required (Admin)
- Body: `{ "notes": "Approved - reasonable discount" }`

#### 5. Reject Sale
**POST** `/api/admin/sales/:sale_id/reject`
- Auth: Required (Admin)
- Body: `{ "notes": "Discount too high" }`

### Public Endpoints

#### 6. Get Product Sale
**GET** `/api/products/:product_id/sale`
- Auth: None
- Returns: Active sale for a product (if any)

## Workflow

### 1. Seller Receives Suggestion
- System detects products expiring in 1-14 days
- Calculates smart discount based on urgency and profit margins
- Displays in "Sales & Discounts" section of seller dashboard

### 2. Seller Requests Sale
- Reviews suggestion with profit analysis
- Can accept suggested discount or request custom (1-50%)
- Submits request with reason

### 3. Admin Reviews Request
- Sees all pending requests sorted by urgency
- Views profit impact analysis
- Approves or rejects with notes

### 4. Sale Goes Live
- Upon approval, sale becomes active (`is_active=1`)
- Customers see sale badge and discounted price
- Cart/checkout uses sale price automatically

### 5. Sale Expiration
- Sale can be set to expire on product expiry date
- Admin can manually deactivate anytime

## UI Components

### Seller Dashboard - Sales Section
Location: `/seller_dashboard.html#salesSection`

Features:
- Smart discount suggestions with urgency indicators
- Profit margin calculator
- One-click sale request
- Custom discount modal

### Admin Panel (Future)
Location: `/admin_dashboard.html` (to be created)

Features:
- Pending sales queue
- Profit impact analysis
- Bulk approve/reject
- Sales analytics

### Customer View
Updates to `shop.html` and product cards:
- Sale badge overlay
- Original price strikethrough
- Sale price in red
- Savings percentage

## Files Created

### Backend
1. `database/migrate_add_sales_system.py` - Database migration
2. `backend/sales_logic.py` - Smart discount calculation
3. `backend/server.py` - API endpoints (added)

### Frontend
1. `frontend/js/sales_system.js` - Seller UI logic
2. `frontend/css/sales_system.css` - Sales UI styling
3. `frontend/seller_dashboard.html` - Sales section (updated)

## Installation

1. Run migration:
```bash
python database/migrate_add_sales_system.py
```

2. Restart server:
```bash
python run.py
```

3. Test seller dashboard:
- Login as seller
- Navigate to "Sales & Discounts"
- View suggestions for expiring products

## Example Calculation

**Product**: Organic Green Tea  
**Original Price**: ₱200  
**Days Until Expiry**: 6 days  
**Suggested Discount**: 25%

**Calculation:**
- Sale Price: ₱200 × (1 - 0.25) = ₱150
- Platform Fee (7.5%): ₱150 × 0.075 = ₱11.25
- Seller Revenue: ₱150 - ₱11.25 = ₱138.75
- Estimated Cost: ₱200 × 0.65 = ₱130
- Seller Profit: ₱138.75 - ₱130 = ₱8.75
- Profit Margin: (₱8.75 / ₱130) × 100 = **6.7%**

**Result**: Seller still makes profit while moving expiring inventory!

## Future Enhancements

1. **Auto-approval** for small discounts (<15%)
2. **Flash sales** - Time-limited discounts
3. **Bundle deals** - Multiple expiring products
4. **SMS notifications** to sellers
5. **Analytics dashboard** - Sales performance tracking
6. **Customer alerts** - Notify customers of new sales

## Testing

### Test Scenarios
1. Create product with expiry date 7 days from now
2. Check sale suggestions appear in seller dashboard
3. Request 20% discount
4. Admin approves sale
5. Verify sale appears on customer product page
6. Add to cart and verify sale price used

### SQL Test Queries
```sql
-- View all pending sales
SELECT * FROM product_sales WHERE status = 'pending';

-- View active sales
SELECT * FROM product_sales WHERE is_active = 1;

-- Products expiring soon without sales
SELECT p.* FROM products p
LEFT JOIN product_sales ps ON p.id = ps.product_id AND ps.is_active = 1
WHERE p.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 14 DAY)
  AND ps.id IS NULL;
```

---

**Status**: ✅ Core system implemented  
**Next**: Admin approval interface and customer sale display
