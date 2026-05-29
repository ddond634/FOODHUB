# Seller Approval & Shop Activation Workflow

## Overview

When an admin approves a seller account, the system automatically:
1. ✅ Sets `verified = 1`
2. ✅ Activates shop: `shop_status = 'active'`
3. ✅ Records approval timestamp: `approved_at = NOW()`
4. ✅ Sends email notification to seller
5. ✅ Enables product management for seller

## Database Schema Changes

### Sellers Table - New Columns

```sql
ALTER TABLE sellers 
ADD COLUMN shop_status ENUM('pending','active','suspended') DEFAULT 'pending',
ADD COLUMN approved_at DATETIME;
```

**Shop Status Values:**
- `pending` - Awaiting admin approval (default)
- `active` - Approved and can manage products
- `suspended` - Temporarily disabled by admin

## Migration

Run the migration script to add columns to existing database:

```bash
python database/migrate_add_shop_status.py
```

This will:
- Add `shop_status` and `approved_at` columns
- Set existing verified sellers to 'active' status
- Preserve all existing data

## API Endpoints

### 1. Admin: Verify Seller (Approve Account)

**Endpoint:** `POST /api/sellers/{seller_id}/verify`  
**Auth:** Admin only  
**Alternative:** `PUT /api/admin/sellers/{seller_id}/verify`

**What Happens:**
1. Updates seller record:
   - `verified = 1`
   - `shop_status = 'active'`
   - `approved_at = NOW()`
2. Sends approval email to seller
3. Returns confirmation with shop status

**Request:**
```json
POST /api/sellers/123/verify
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Seller approved successfully",
  "data": {
    "seller_id": 123,
    "shop_status": "active",
    "verified": true,
    "message": "Seller verified and shop activated"
  }
}
```

**Email Sent to Seller:**
```
Subject: 🎉 Your Seller Account Has Been Approved!

Dear [Seller Name],

Congratulations! Your seller account for "[Business Name]" has been 
approved by our admin team.

✅ Your shop is now ACTIVE
✅ You can start adding products immediately
✅ Your products will appear in the marketplace

Next Steps:
1. Login to your seller dashboard
2. Add your first products
3. Start receiving orders

Thank you for joining Hub E-Commerce!
```

### 2. Seller: Check Shop Status

**Endpoint:** `GET /api/sellers/shop-status`  
**Auth:** Seller token required

**Response:**
```json
{
  "success": true,
  "data": {
    "seller_id": 123,
    "verified": true,
    "shop_status": "active",
    "approved_at": "2025-11-22T10:30:00",
    "business_name": "My Store",
    "can_add_products": true,
    "message": "Your shop is active! You can add products now."
  }
}
```

**Possible Messages:**
- `"Your seller account is pending admin approval."` - Not verified
- `"Your shop is active! You can add products now."` - Active
- `"Your shop has been suspended. Please contact admin."` - Suspended
- `"Your shop is pending activation."` - Verified but not active

### 3. Seller: Create Product

**Endpoint:** `POST /api/sellers/products`  
**Auth:** Seller token required

**Validation Checks:**
1. ✅ User must have 'seller' role
2. ✅ Seller must be verified
3. ✅ Shop status must be 'active'
4. ✅ Price must be > 0
5. ✅ Stock must be >= 0

**Request:**
```json
POST /api/sellers/products
Authorization: Bearer <seller_token>

{
  "title": "Premium Coffee Beans",
  "description": "100% Arabica beans from Colombia",
  "price": 299.99,
  "stock": 50,
  "category": "Food",
  "img_url": "https://example.com/coffee.jpg"
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Product created and added to your shop",
  "data": {
    "product_id": 456,
    "title": "Premium Coffee Beans",
    "price": 299.99,
    "stock": 50,
    "category": "Food",
    "seller_id": 123,
    "created_at": "2025-11-22T14:30:00"
  }
}
```

**Error Responses:**

**Not Verified (403):**
```json
{
  "success": false,
  "error": "Your seller account is pending approval. Please wait for admin verification."
}
```

**Shop Suspended (403):**
```json
{
  "success": false,
  "error": "Your shop has been suspended. Please contact admin for assistance."
}
```

**Shop Not Active (403):**
```json
{
  "success": false,
  "error": "Your shop is not active yet. Please wait for admin approval."
}
```

### 4. Admin: List All Sellers

**Endpoint:** `GET /api/sellers`  
**Auth:** Admin only

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "seller_id": 123,
      "user_id": 456,
      "email": "seller@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "business_name": "My Store",
      "category": "Food",
      "verified": 1,
      "shop_status": "active",
      "approved_at": "2025-11-22T10:30:00",
      "suspended": 0,
      "created_at": "2025-11-20T08:00:00"
    }
  ]
}
```

### 5. Admin: Suspend Seller Shop

**Endpoint:** `POST /api/sellers/{seller_id}/suspend-shop`  
**Auth:** Admin only

**Request:**
```json
POST /api/sellers/123/suspend-shop
Authorization: Bearer <admin_token>

{
  "reason": "Violation of terms of service"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Seller shop suspended",
  "data": {
    "seller_id": 123,
    "shop_status": "suspended",
    "reason": "Violation of terms of service"
  }
}
```

### 6. Admin: Reactivate Seller Shop

**Endpoint:** `POST /api/sellers/{seller_id}/reactivate-shop`  
**Auth:** Admin only

**Response:**
```json
{
  "success": true,
  "message": "Seller shop reactivated",
  "data": {
    "seller_id": 123,
    "shop_status": "active"
  }
}
```

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Seller Registration                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Seller Signs │
                  │      Up      │
                  └──────┬───────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Status: pending       │
              │ verified: 0           │
              │ shop_status: pending  │
              └──────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Admin Reviews Application  │
        └────────┬───────────────────┘
                 │
       ┌─────────┴─────────┐
       │                   │
       ▼                   ▼
  ┌─────────┐      ┌──────────────┐
  │ APPROVE │      │    REJECT    │
  └────┬────┘      └──────────────┘
       │
       ▼
┌──────────────────────────────┐
│ System Updates:              │
│ • verified = 1               │
│ • shop_status = 'active'     │
│ • approved_at = NOW()        │
│ • Send email notification    │
└──────────┬───────────────────┘
           │
           ▼
    ┌──────────────┐
    │ Shop Active! │
    └──────┬───────┘
           │
           ▼
    ┌─────────────────┐
    │ Seller Can Now: │
    │ • Add products  │
    │ • Edit products │
    │ • View orders   │
    └─────────────────┘
```

## Real-Time Sync

### Database Changes
- All updates use transactions to ensure atomicity
- Product creation immediately visible in database
- No caching delays - changes reflect instantly

### Product Visibility
When seller adds a product after approval:
1. Product inserted with `seller_id = user_id`
2. Immediately appears in:
   - Seller's product list (`GET /api/sellers/products`)
   - Marketplace (`GET /api/products`)
   - Shop page (`GET /api/products?seller_id={id}`)
3. Searchable via product search API
4. Filterable by category

### Shop Page Integration
```javascript
// Fetch seller's products in real-time
fetch('/api/sellers/products', {
  headers: {
    'Authorization': 'Bearer ' + sellerToken
  }
})
.then(res => res.json())
.then(data => {
  // Products array includes all seller products
  displayProducts(data.data);
});
```

## Testing the Workflow

### 1. Register as Seller
```bash
POST /api/sellers/register
{
  "email": "newseller@test.com",
  "password": "password123",
  "first_name": "Test",
  "last_name": "Seller",
  "business_name": "Test Store",
  "category": "Food"
}
```

### 2. Check Status (Should be Pending)
```bash
GET /api/sellers/shop-status
Authorization: Bearer <seller_token>

# Response: can_add_products = false
```

### 3. Try to Add Product (Should Fail)
```bash
POST /api/sellers/products
Authorization: Bearer <seller_token>
{
  "title": "Test Product",
  "price": 99.99,
  "stock": 10
}

# Response: 403 - Pending approval
```

### 4. Admin Approves Seller
```bash
POST /api/sellers/{seller_id}/verify
Authorization: Bearer <admin_token>

# Seller receives email notification
```

### 5. Check Status Again (Should be Active)
```bash
GET /api/sellers/shop-status
Authorization: Bearer <seller_token>

# Response: can_add_products = true, shop_status = 'active'
```

### 6. Add Product (Should Succeed)
```bash
POST /api/sellers/products
Authorization: Bearer <seller_token>
{
  "title": "Test Product",
  "price": 99.99,
  "stock": 10
}

# Response: 200 - Product created
```

### 7. Verify Product Appears
```bash
GET /api/sellers/products
Authorization: Bearer <seller_token>

# Product appears in list immediately
```

## Error Handling

### Scenario 1: Seller Not Verified
**Trigger:** Seller tries to add product before approval  
**Response:** `403 Forbidden`  
**Message:** "Your seller account is pending approval. Please wait for admin verification."

### Scenario 2: Shop Suspended
**Trigger:** Admin suspends shop, seller tries to add product  
**Response:** `403 Forbidden`  
**Message:** "Your shop has been suspended. Please contact admin for assistance."

### Scenario 3: Invalid Product Data
**Trigger:** Price <= 0 or stock < 0  
**Response:** `400 Bad Request`  
**Message:** "Price must be greater than 0" or "Stock cannot be negative"

### Scenario 4: Missing Required Fields
**Trigger:** Missing title, price, or stock  
**Response:** `400 Bad Request`  
**Message:** "Required fields: title, price, stock"

## Admin Dashboard Integration

Update admin dashboard to show shop status:

```javascript
// Seller list display
sellers.forEach(seller => {
  const statusBadge = seller.shop_status === 'active' 
    ? '<span class="badge-success">Active</span>'
    : seller.shop_status === 'suspended'
    ? '<span class="badge-danger">Suspended</span>'
    : '<span class="badge-warning">Pending</span>';
  
  // Show approve button only for pending sellers
  const actionButton = seller.shop_status === 'pending'
    ? `<button onclick="approveSeller(${seller.seller_id})">Approve</button>`
    : seller.shop_status === 'active'
    ? `<button onclick="suspendShop(${seller.seller_id})">Suspend</button>`
    : `<button onclick="reactivateShop(${seller.seller_id})">Reactivate</button>`;
});
```

## Seller Dashboard Integration

Show shop status banner:

```javascript
// Check shop status on page load
fetch('/api/sellers/shop-status')
  .then(res => res.json())
  .then(data => {
    if (!data.data.can_add_products) {
      showStatusBanner(data.data.message);
      disableProductButtons();
    }
  });
```

## Security Considerations

1. **Role Verification:** All endpoints verify user role
2. **Token Validation:** JWT tokens required for all operations
3. **Ownership Checks:** Sellers can only manage their own products
4. **Admin Authorization:** Only admins can approve/suspend shops
5. **SQL Injection Prevention:** Parameterized queries used
6. **Input Validation:** Price, stock, and field validation

## Maintenance

### Check Pending Sellers
```sql
SELECT * FROM sellers WHERE shop_status = 'pending';
```

### Find Active Shops
```sql
SELECT * FROM sellers WHERE shop_status = 'active';
```

### Suspended Shops
```sql
SELECT * FROM sellers WHERE shop_status = 'suspended';
```

### Recently Approved
```sql
SELECT * FROM sellers 
WHERE shop_status = 'active' 
AND approved_at > DATE_SUB(NOW(), INTERVAL 7 DAY);
```

---

**Status:** Implemented and ready for production  
**Version:** 1.0  
**Last Updated:** 2025-11-22
