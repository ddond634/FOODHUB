# 🔒 Suspension System Documentation

## Overview
Complete suspension system for sellers and riders with instant system-wide effects, detailed tracking, and automated notifications.

---

## 🎯 Key Features

### Instant System-Wide Effects
✅ **Suspended sellers:** Shop and products immediately hidden from customers  
✅ **Suspended riders:** Removed from active riders list, cannot receive orders  
✅ **Real-time enforcement:** All permissions disabled instantly  
✅ **Database-driven:** Changes reflected across all endpoints immediately  

### Suspension Types
- **Temporary:** Can be appealed and reversed by admin
- **Permanent:** Cannot be reversed, account permanently blocked

### Detailed Tracking
- **suspended_at:** Timestamp of when suspension occurred
- **suspended_by:** Admin user ID who suspended the account
- **suspension_reason:** Detailed explanation for suspension
- **suspension_type:** 'temporary' or 'permanent'

---

## 📊 Database Schema

### Sellers Table - Suspension Fields
```sql
CREATE TABLE IF NOT EXISTS sellers (
    ...existing fields...
    shop_status ENUM('pending','active','suspended') DEFAULT 'pending',
    approved_at DATETIME,
    suspended_at DATETIME,
    suspended_by INT,
    suspension_reason TEXT,
    suspension_type ENUM('temporary','permanent'),
    FOREIGN KEY (suspended_by) REFERENCES users(id) ON DELETE SET NULL
);
```

### Riders Table - Suspension Fields
```sql
CREATE TABLE IF NOT EXISTS riders (
    ...existing fields...
    rider_status ENUM('pending','active','suspended','offline') DEFAULT 'pending',
    availability ENUM('available','busy','offline') DEFAULT 'offline',
    suspended_at DATETIME,
    suspended_by INT,
    suspension_reason TEXT,
    suspension_type ENUM('temporary','permanent'),
    FOREIGN KEY (suspended_by) REFERENCES users(id) ON DELETE SET NULL
);
```

---

## 🛠️ API Endpoints

### 1. Suspend Seller Shop
**Endpoint:** `POST /api/sellers/{seller_id}/suspend-shop`  
**Auth:** Admin role required  
**Description:** Suspends seller's shop with instant system-wide effect

**Request:**
```http
POST /api/sellers/5/suspend-shop
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "reason": "Violation of terms and conditions",
  "type": "temporary"
}
```

**Parameters:**
- `reason` (optional): Detailed explanation (default: "Violation of terms and conditions")
- `type` (optional): "temporary" or "permanent" (default: "temporary")

**Response:**
```json
{
  "success": true,
  "message": "Seller shop temporarily suspended",
  "data": {
    "seller_id": 5,
    "shop_status": "suspended",
    "suspension_type": "temporary",
    "reason": "Violation of terms and conditions",
    "suspended_at": "2025-11-22T10:30:00",
    "effect": "Shop and products hidden from customers instantly"
  }
}
```

**Instant Effects:**
- ✅ shop_status set to 'suspended'
- ✅ Seller cannot add/edit products
- ✅ Shop hidden from customers
- ✅ All products hidden from search and listings
- ✅ Email notification sent to seller
- ✅ Suspension tracked with admin ID and timestamp

---

### 2. Reactivate Seller Shop
**Endpoint:** `POST /api/sellers/{seller_id}/reactivate-shop`  
**Auth:** Admin role required  
**Description:** Reactivates suspended seller's shop

**Request:**
```http
POST /api/sellers/5/reactivate-shop
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Seller shop reactivated successfully",
  "data": {
    "seller_id": 5,
    "shop_status": "active",
    "reactivated_at": "2025-11-22T12:00:00",
    "effect": "Shop and products visible to customers instantly"
  }
}
```

**Instant Effects:**
- ✅ shop_status set to 'active'
- ✅ All suspension fields cleared (NULL)
- ✅ Seller can add/edit products
- ✅ Shop visible to customers
- ✅ Products appear in search and listings
- ✅ Email notification sent to seller

---

### 3. Suspend Rider Account
**Endpoint:** `POST /api/admin/riders/{rider_id}/suspend`  
**Auth:** Admin role required  
**Description:** Suspends rider account with instant effect

**Request:**
```http
POST /api/admin/riders/8/suspend
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "reason": "Multiple customer complaints",
  "type": "temporary"
}
```

**Parameters:**
- `reason` (optional): Detailed explanation (default: "Violation of delivery standards")
- `type` (optional): "temporary" or "permanent" (default: "temporary")

**Response:**
```json
{
  "success": true,
  "message": "Rider temporarily suspended",
  "data": {
    "rider_id": 8,
    "rider_status": "suspended",
    "suspension_type": "temporary",
    "availability": "offline",
    "reason": "Multiple customer complaints",
    "suspended_at": "2025-11-22T10:45:00",
    "effect": "Rider removed from active list and cannot receive orders"
  }
}
```

**Instant Effects:**
- ✅ rider_status set to 'suspended'
- ✅ availability set to 'offline'
- ✅ Rider removed from available riders list
- ✅ Rider cannot receive new delivery tasks
- ✅ Rider cannot update availability
- ✅ Email notification sent to rider
- ✅ Suspension tracked with admin ID and timestamp

---

### 4. Reactivate Rider Account
**Endpoint:** `POST /api/admin/riders/{rider_id}/reactivate`  
**Auth:** Admin role required  
**Description:** Reactivates suspended rider account

**Request:**
```http
POST /api/admin/riders/8/reactivate
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Rider reactivated successfully",
  "data": {
    "rider_id": 8,
    "rider_status": "active",
    "availability": "offline",
    "reactivated_at": "2025-11-22T13:00:00",
    "effect": "Rider can now receive orders after setting availability"
  }
}
```

**Instant Effects:**
- ✅ rider_status set to 'active'
- ✅ availability set to 'offline' (rider must manually set to 'available')
- ✅ All suspension fields cleared (NULL)
- ✅ Rider can update availability
- ✅ Rider eligible for delivery tasks when available
- ✅ Email notification sent to rider

---

## ⚡ Real-Time Enforcement

### Seller Suspension Effects

#### 1. Product Creation Blocked
```python
# POST /api/sellers/products endpoint automatically checks:
if shop_status == 'suspended':
    return error_response(
        'Your shop is suspended. You cannot add products. 
         Reason: {suspension_reason} Contact support for assistance.',
        403
    )
```

#### 2. Products Hidden from Customers
```python
# GET /api/products endpoint filters:
WHERE s.shop_status='active' OR s.shop_status IS NULL
# Suspended sellers' products NOT returned
```

#### 3. Shop Not Visible
All public-facing queries filter out suspended shops automatically.

---

### Rider Suspension Effects

#### 1. Availability Update Blocked
```python
# PUT /api/riders/availability endpoint checks:
if rider_status == 'suspended':
    return error_response(
        'Your account is suspended. You cannot update availability. 
         Reason: {suspension_reason}',
        403
    )
```

#### 2. Removed from Available Riders
```python
# GET /api/admin/riders/available endpoint filters:
WHERE r.verified = 1 
AND r.rider_status = 'active'
AND r.rider_status != 'suspended'
AND r.availability = 'available'
# Suspended riders NEVER appear
```

#### 3. Cannot Receive Orders
All order assignment queries exclude suspended riders.

---

## 📧 Email Notifications

### Seller Suspension Email
**Subject:** ⚠️ Your Seller Account Has Been [Temporarily/Permanently] Suspended

**Content:**
```
Dear {first_name},

Your seller account and shop "{business_name}" has been {temporarily/permanently} suspended.

🚫 Suspension Details:
- Type: TEMPORARY/PERMANENT
- Reason: {suspension_reason}
- Date: {suspended_at}

🚫 Effect of Suspension:
- Your shop is no longer visible to customers
- All your products are hidden from search and listings
- You cannot add or edit products
- You cannot process orders
- All permissions are disabled

[For temporary] This is a temporary suspension. Contact our support team to appeal.
[For permanent] This suspension is permanent and cannot be reversed.

If you believe this is a mistake, contact: support@hubcommerce.com

Best regards,
Hub E-Commerce Admin Team
```

---

### Seller Reactivation Email
**Subject:** ✅ Your Seller Account Has Been Reactivated!

**Content:**
```
Dear {first_name},

Good news! Your seller account and shop "{business_name}" has been reactivated.

✅ Your shop is now ACTIVE
✅ Your products are visible to customers
✅ You can add and edit products
✅ You can process orders normally
✅ All permissions restored

You can now resume your business activities.

Please comply with our terms and conditions to avoid future suspensions.

Best regards,
Hub E-Commerce Admin Team
```

---

### Rider Suspension Email
**Subject:** ⚠️ Your Rider Account Has Been [Temporarily/Permanently] Suspended

**Content:**
```
Dear {first_name},

Your rider account has been {temporarily/permanently} suspended.

🚫 Suspension Details:
- Type: TEMPORARY/PERMANENT
- Reason: {suspension_reason}
- Date: {suspended_at}

🚫 Effect of Suspension:
- You are removed from active riders list
- You cannot receive new delivery tasks
- You cannot accept orders
- You are marked as offline in the system
- All delivery permissions disabled

[For temporary] This is a temporary suspension. Contact support to appeal.
[For permanent] This suspension is permanent.

If you believe this is a mistake, contact: support@hubcommerce.com

Best regards,
Hub E-Commerce Admin Team
```

---

### Rider Reactivation Email
**Subject:** ✅ Your Rider Account Has Been Reactivated!

**Content:**
```
Dear {first_name},

Good news! Your rider account has been reactivated.

✅ Your account is now ACTIVE
✅ You can receive delivery tasks
✅ You can accept orders
✅ All delivery permissions restored

You are currently set to OFFLINE. Update your availability to AVAILABLE to start receiving orders.

Please comply with our delivery standards to avoid future suspensions.

Best regards,
Hub E-Commerce Admin Team
```

---

## 🧪 Testing Procedures

### Test Scenario 1: Suspend and Reactivate Seller

```bash
# 1. Suspend seller shop
POST /api/sellers/5/suspend-shop
{
  "reason": "Selling counterfeit products",
  "type": "temporary"
}
# Expected: shop_status='suspended', email sent

# 2. Verify seller cannot add products
POST /api/sellers/products
{
  "title": "New Product",
  "price": 100
}
# Expected: 403 error with suspension message

# 3. Verify products hidden from customers
GET /api/products
# Expected: Seller's products NOT in response

# 4. Reactivate seller
POST /api/sellers/5/reactivate-shop
# Expected: shop_status='active', suspension fields NULL, email sent

# 5. Verify seller can add products
POST /api/sellers/products
{
  "title": "New Product",
  "price": 100
}
# Expected: Success

# 6. Verify products visible again
GET /api/products
# Expected: Seller's products appear in response
```

---

### Test Scenario 2: Suspend and Reactivate Rider

```bash
# 1. Suspend rider
POST /api/admin/riders/8/suspend
{
  "reason": "Multiple delivery delays",
  "type": "permanent"
}
# Expected: rider_status='suspended', availability='offline', email sent

# 2. Verify rider cannot update availability
PUT /api/riders/availability
{
  "availability": "available"
}
# Expected: 403 error with suspension message

# 3. Verify rider not in available list
GET /api/admin/riders/available
# Expected: Rider NOT in response

# 4. Reactivate rider
POST /api/admin/riders/8/reactivate
# Expected: rider_status='active', suspension fields NULL, email sent

# 5. Rider updates availability
PUT /api/riders/availability
{
  "availability": "available"
}
# Expected: Success

# 6. Verify rider appears in available list
GET /api/admin/riders/available
# Expected: Rider appears in response
```

---

### Test Scenario 3: Verify Suspension Tracking

```bash
# 1. Admin (ID: 1) suspends seller
POST /api/sellers/5/suspend-shop
# Authorization: Bearer {admin_token for user_id=1}

# 2. Query database to verify tracking
SELECT suspended_at, suspended_by, suspension_reason, suspension_type
FROM sellers WHERE id=5;

# Expected:
# suspended_at: 2025-11-22 10:30:00
# suspended_by: 1
# suspension_reason: "Violation of terms..."
# suspension_type: "temporary"

# 3. Reactivate seller
POST /api/sellers/5/reactivate-shop

# 4. Query database to verify fields cleared
SELECT suspended_at, suspended_by, suspension_reason, suspension_type
FROM sellers WHERE id=5;

# Expected:
# suspended_at: NULL
# suspended_by: NULL
# suspension_reason: NULL
# suspension_type: NULL
```

---

## 🔗 Integration Examples

### Admin Dashboard: Suspend Seller

```javascript
async function suspendSeller(sellerId) {
  const reason = document.getElementById('suspension-reason').value;
  const type = document.getElementById('suspension-type').value; // 'temporary' or 'permanent'
  
  const response = await fetch(`/api/sellers/${sellerId}/suspend-shop`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ reason, type })
  });
  
  const data = await response.json();
  
  if (data.success) {
    alert(`Seller suspended ${type}ly. Effect: ${data.data.effect}`);
    location.reload(); // Refresh to show updated status
  } else {
    alert(`Error: ${data.message}`);
  }
}
```

---

### Admin Dashboard: View Suspension Details

```javascript
async function viewSellerDetails(sellerId) {
  const response = await fetch(`/api/sellers/${sellerId}`, {
    headers: {
      'Authorization': `Bearer ${adminToken}`
    }
  });
  
  const data = await response.json();
  const seller = data.data;
  
  if (seller.shop_status === 'suspended') {
    document.getElementById('status').innerHTML = `
      <span class="badge badge-danger">SUSPENDED</span>
      <p><strong>Type:</strong> ${seller.suspension_type}</p>
      <p><strong>Reason:</strong> ${seller.suspension_reason}</p>
      <p><strong>Suspended At:</strong> ${new Date(seller.suspended_at).toLocaleString()}</p>
      <button onclick="reactivateSeller(${sellerId})">Reactivate</button>
    `;
  }
}
```

---

### Seller Dashboard: Check Suspension Status

```javascript
async function checkShopStatus() {
  const response = await fetch('/api/sellers/shop-status', {
    headers: {
      'Authorization': `Bearer ${sellerToken}`
    }
  });
  
  const data = await response.json();
  
  if (data.data.shop_status === 'suspended') {
    document.getElementById('status-banner').innerHTML = `
      <div class="alert alert-danger">
        <h3>⚠️ Your Shop Is Suspended</h3>
        <p><strong>Reason:</strong> ${data.data.suspension_reason || 'Not specified'}</p>
        <p>You cannot add products or process orders.</p>
        <p>Contact support: support@hubcommerce.com</p>
      </div>
    `;
    
    // Disable all product management buttons
    document.querySelectorAll('.product-action-btn').forEach(btn => {
      btn.disabled = true;
    });
  }
}
```

---

## 🛠️ SQL Maintenance Queries

### View All Suspended Sellers
```sql
SELECT 
    s.id,
    u.email,
    s.business_name,
    s.suspension_type,
    s.suspension_reason,
    s.suspended_at,
    admin.email as suspended_by_email
FROM sellers s
JOIN users u ON s.user_id = u.id
LEFT JOIN users admin ON s.suspended_by = admin.id
WHERE s.shop_status = 'suspended'
ORDER BY s.suspended_at DESC;
```

### View All Suspended Riders
```sql
SELECT 
    r.id,
    u.email,
    u.first_name,
    u.last_name,
    r.suspension_type,
    r.suspension_reason,
    r.suspended_at,
    admin.email as suspended_by_email
FROM riders r
JOIN users u ON r.user_id = u.id
LEFT JOIN users admin ON r.suspended_by = admin.id
WHERE r.rider_status = 'suspended'
ORDER BY r.suspended_at DESC;
```

### Suspension Statistics
```sql
-- Seller suspension stats
SELECT 
    suspension_type,
    COUNT(*) as count
FROM sellers
WHERE shop_status = 'suspended'
GROUP BY suspension_type;

-- Rider suspension stats
SELECT 
    suspension_type,
    COUNT(*) as count
FROM riders
WHERE rider_status = 'suspended'
GROUP BY suspension_type;
```

### Find Sellers Suspended by Specific Admin
```sql
SELECT 
    s.id,
    u.email,
    s.business_name,
    s.suspended_at,
    s.suspension_reason
FROM sellers s
JOIN users u ON s.user_id = u.id
WHERE s.suspended_by = {admin_user_id}
ORDER BY s.suspended_at DESC;
```

---

## 📋 Migration Guide

### Running the Migration
```bash
cd c:\Users\Imac\Downloads\qwerty
python database/migrate_add_suspension_fields.py
```

### Migration Actions
1. ✅ Adds `suspended_at` DATETIME to sellers table
2. ✅ Adds `suspended_by` INT to sellers table (FK to users.id)
3. ✅ Adds `suspension_reason` TEXT to sellers table
4. ✅ Adds `suspension_type` ENUM to sellers table
5. ✅ Adds `suspended_at` DATETIME to riders table
6. ✅ Adds `suspended_by` INT to riders table (FK to users.id)
7. ✅ Adds `suspension_reason` TEXT to riders table
8. ✅ Adds `suspension_type` ENUM to riders table

### Rollback (if needed)
```sql
-- Sellers table
ALTER TABLE sellers DROP FOREIGN KEY fk_sellers_suspended_by;
ALTER TABLE sellers DROP COLUMN suspended_at;
ALTER TABLE sellers DROP COLUMN suspended_by;
ALTER TABLE sellers DROP COLUMN suspension_reason;
ALTER TABLE sellers DROP COLUMN suspension_type;

-- Riders table
ALTER TABLE riders DROP FOREIGN KEY fk_riders_suspended_by;
ALTER TABLE riders DROP COLUMN suspended_at;
ALTER TABLE riders DROP COLUMN suspended_by;
ALTER TABLE riders DROP COLUMN suspension_reason;
ALTER TABLE riders DROP COLUMN suspension_type;
```

---

## 🎯 Summary

### Key Capabilities
✅ **Temporary or Permanent Suspensions** - Flexible suspension types  
✅ **Instant System-Wide Effect** - Real-time enforcement across all endpoints  
✅ **Detailed Tracking** - Know who, when, why, and what type  
✅ **Automated Notifications** - Email sent to suspended/reactivated users  
✅ **Permission Revocation** - All actions blocked for suspended accounts  
✅ **Product/Service Hiding** - Content invisible to customers instantly  
✅ **Audit Trail** - Complete history of suspensions with admin tracking  

### Enforcement Points
- ✅ Product creation/editing blocked for suspended sellers
- ✅ Products hidden from public listings automatically
- ✅ Availability updates blocked for suspended riders
- ✅ Riders removed from available/active lists
- ✅ All suspension checks happen before operations
- ✅ Error messages include suspension reason

### Admin Controls
- ✅ Suspend with custom reason and type
- ✅ Track who suspended the account
- ✅ View suspension history and details
- ✅ Reactivate with one click
- ✅ Automatic email notifications
- ✅ Complete audit trail

---

**📅 Last Updated:** November 22, 2025  
**📝 Version:** 1.0  
**👨‍💻 Maintainer:** Hub E-Commerce Development Team
