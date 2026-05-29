# 🚴 Rider Approval Workflow Documentation

## Overview
Complete documentation for the rider approval, activation, and real-time status management system.

---

## 📊 Database Schema

### Riders Table Structure
```sql
CREATE TABLE IF NOT EXISTS riders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    vehicle_type VARCHAR(50),
    driver_license VARCHAR(255),
    plate_number VARCHAR(50),
    verified TINYINT DEFAULT 0,
    rider_status ENUM('pending','active','suspended','offline') DEFAULT 'pending',
    availability ENUM('available','busy','offline') DEFAULT 'offline',
    current_location VARCHAR(255),
    approved_at DATETIME,
    last_active DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Status Field Definitions

**rider_status** - Account approval status:
- `pending` - Awaiting admin approval (default)
- `active` - Approved and can accept orders
- `suspended` - Account suspended by admin
- `offline` - Rider manually set offline

**availability** - Current availability for orders:
- `available` - Ready to accept new deliveries
- `busy` - Currently handling a delivery
- `offline` - Not accepting orders (default)

---

## 🔄 Rider Approval Workflow

### Workflow Diagram
```
┌─────────────────┐
│ Rider Registers │
│  (verified=0)   │
│ status=pending  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Admin Reviews   │
│ Pending Riders  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ Admin Approves Rider        │
│ - verified = 1              │
│ - rider_status = 'active'   │
│ - availability = 'available'│
│ - approved_at = NOW()       │
│ - Send email notification   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Rider Active in System      │
│ - Appears in riders list    │
│ - Can accept delivery orders│
│ - Updates sync in real-time │
└─────────────────────────────┘
```

---

## 🛠️ API Endpoints Reference

### 1. Admin: Verify/Approve Rider
**Endpoint:** `PUT /api/admin/riders/{rider_id}/verify`  
**Auth:** Admin role required  
**Description:** Approves rider and activates account

**Request:**
```http
PUT /api/admin/riders/5/verify
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Rider verified and activated",
  "data": {
    "rider_id": 5,
    "rider_status": "active",
    "availability": "available",
    "verified": true
  }
}
```

**Actions Performed:**
- Sets `verified = 1`
- Sets `rider_status = 'active'`
- Sets `availability = 'available'`
- Records `approved_at = NOW()`
- Updates `last_active = NOW()`
- Sends approval email to rider

---

### 2. Admin: Get Pending Riders
**Endpoint:** `GET /api/admin/riders/pending`  
**Auth:** Admin role required  
**Description:** Lists all riders awaiting approval

**Request:**
```http
GET /api/admin/riders/pending
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Pending riders",
  "data": [
    {
      "id": 5,
      "user_id": 42,
      "email": "rider@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "vehicle_type": "Motorcycle",
      "driver_license": "DL123456",
      "plate_number": "ABC-123",
      "verified": 0,
      "rider_status": "pending",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

---

### 3. Admin: Get All Riders
**Endpoint:** `GET /api/admin/riders`  
**Auth:** Admin role required  
**Description:** Lists all riders with complete status information

**Request:**
```http
GET /api/admin/riders
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "All riders retrieved",
  "data": [
    {
      "id": 5,
      "user_id": 42,
      "first_name": "John",
      "last_name": "Doe",
      "email": "rider@example.com",
      "vehicle_type": "Motorcycle",
      "driver_license": "DL123456",
      "plate_number": "ABC-123",
      "verified": 1,
      "rider_status": "active",
      "availability": "available",
      "current_location": "Downtown Area",
      "approved_at": "2024-01-15T14:20:00",
      "last_active": "2024-01-15T16:45:00",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

---

### 4. Admin: Get Available Riders
**Endpoint:** `GET /api/admin/riders/available`  
**Auth:** Admin role required  
**Description:** Lists riders ready to accept delivery orders

**Request:**
```http
GET /api/admin/riders/available
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Found 3 available riders",
  "data": [
    {
      "id": 5,
      "user_id": 42,
      "first_name": "John",
      "last_name": "Doe",
      "email": "rider@example.com",
      "vehicle_type": "Motorcycle",
      "current_location": "Downtown Area",
      "last_active": "2024-01-15T16:45:00",
      "rider_status": "active",
      "availability": "available"
    }
  ]
}
```

**Filters Applied:**
- `verified = 1`
- `rider_status = 'active'`
- `availability = 'available'`

---

### 5. Admin: Suspend Rider
**Endpoint:** `POST /api/admin/riders/{rider_id}/suspend`  
**Auth:** Admin role required  
**Description:** Suspends rider account

**Request:**
```http
POST /api/admin/riders/5/suspend
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "reason": "Multiple customer complaints"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Rider suspended successfully",
  "data": {
    "rider_id": 5,
    "rider_status": "suspended",
    "reason": "Multiple customer complaints"
  }
}
```

**Actions Performed:**
- Sets `rider_status = 'suspended'`
- Sets `availability = 'offline'`
- Rider cannot accept new orders

---

### 6. Admin: Reactivate Rider
**Endpoint:** `POST /api/admin/riders/{rider_id}/reactivate`  
**Auth:** Admin role required  
**Description:** Reactivates a suspended rider

**Request:**
```http
POST /api/admin/riders/5/reactivate
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Rider reactivated successfully",
  "data": {
    "rider_id": 5,
    "rider_status": "active",
    "availability": "offline"
  }
}
```

**Note:** Rider is set to `offline` availability - they must manually set to `available`

---

### 7. Rider: Get Own Status
**Endpoint:** `GET /api/riders/status`  
**Auth:** Rider authentication required  
**Description:** Rider checks their account status and eligibility

**Request:**
```http
GET /api/riders/status
Authorization: Bearer {rider_token}
```

**Response (Active Rider):**
```json
{
  "success": true,
  "message": "Rider status retrieved",
  "data": {
    "id": 5,
    "verified": 1,
    "rider_status": "active",
    "availability": "available",
    "current_location": "Downtown Area",
    "approved_at": "2024-01-15T14:20:00",
    "last_active": "2024-01-15T16:45:00",
    "can_accept_orders": true,
    "status_message": "You are active and can accept delivery orders!"
  }
}
```

**Response (Pending Rider):**
```json
{
  "success": true,
  "message": "Rider status retrieved",
  "data": {
    "id": 6,
    "verified": 0,
    "rider_status": "pending",
    "availability": "offline",
    "current_location": null,
    "approved_at": null,
    "last_active": null,
    "can_accept_orders": false,
    "status_message": "Your account is pending admin approval"
  }
}
```

---

### 8. Rider: Update Availability
**Endpoint:** `PUT /api/riders/availability`  
**Auth:** Rider authentication required  
**Description:** Rider changes availability status

**Request:**
```http
PUT /api/riders/availability
Authorization: Bearer {rider_token}
Content-Type: application/json

{
  "availability": "available"
}
```

**Valid Values:**
- `available` - Ready for orders
- `busy` - Currently delivering
- `offline` - Not accepting orders

**Response:**
```json
{
  "success": true,
  "message": "Availability updated successfully",
  "data": {
    "availability": "available",
    "updated_at": "2024-01-15T17:00:00"
  }
}
```

**Error Response (Not Active):**
```json
{
  "success": false,
  "message": "Cannot update availability. Your account is pending",
  "status": 403
}
```

---

### 9. Rider: Update Location
**Endpoint:** `PUT /api/riders/location`  
**Auth:** Rider authentication required  
**Description:** Rider updates current location

**Request:**
```http
PUT /api/riders/location
Authorization: Bearer {rider_token}
Content-Type: application/json

{
  "location": "Shopping District, Near Mall"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Location updated successfully",
  "data": {
    "location": "Shopping District, Near Mall",
    "updated_at": "2024-01-15T17:05:00"
  }
}
```

---

## 🔒 Authorization & Validation

### Role-Based Access
- **Admin endpoints:** Require `@role_required('admin')` decorator
- **Rider endpoints:** Require `@token_required` decorator with rider user

### Status Validation Rules

**For Order Assignment:**
```python
can_receive_order = (
    verified == 1 AND
    rider_status == 'active' AND
    availability == 'available'
)
```

**For Availability Updates:**
- Rider must be `active` (not pending or suspended)
- Only riders can update their own availability

**For Location Updates:**
- No status restrictions
- Updates `last_active` timestamp automatically

---

## 📧 Email Notifications

### Approval Email Template
**Subject:** 🎉 Your Rider Account Has Been Approved!

**Content:**
```
Dear {first_name},

Congratulations! Your rider account has been approved by our admin team.

✅ Your account is now ACTIVE
✅ You can start accepting delivery orders immediately
✅ You are marked as AVAILABLE in the system
✅ Vehicle: {vehicle_type}

Next Steps:
1. Login to your rider dashboard
2. Update your availability status
3. Start accepting delivery orders
4. Update your location for better order matching

Thank you for joining Hub E-Commerce as a delivery partner!

Best regards,
Hub Team
```

---

## ⚡ Real-Time Sync Implementation

### Automatic Updates
All rider status changes immediately reflect in:
- Admin dashboard rider lists
- Order assignment queries
- Availability checks
- Location tracking

### Database Triggers
Every update automatically sets:
```sql
last_active = NOW()  -- Tracks rider activity
```

### Sync Points
1. **Verification:** Admin approves → Status active → Email sent
2. **Availability:** Rider changes → Database updated → Admin sees change
3. **Location:** Rider updates → Stored in DB → Visible to admin
4. **Suspension:** Admin suspends → Rider offline → Orders blocked

---

## 🧪 Testing Procedures

### Test Scenario 1: Rider Registration to Approval
```bash
# 1. Register new rider
POST /api/register
{
  "email": "newrider@test.com",
  "password": "Test123!",
  "first_name": "Test",
  "last_name": "Rider",
  "role": "rider"
}

# 2. Create rider profile
POST /api/riders
{
  "vehicle_type": "Motorcycle",
  "driver_license": "DL999888",
  "plate_number": "XYZ-999"
}

# 3. Admin checks pending riders
GET /api/admin/riders/pending
# Should show newrider@test.com with status=pending

# 4. Admin approves rider
PUT /api/admin/riders/{rider_id}/verify
# Rider should receive email

# 5. Rider checks status
GET /api/riders/status
# Should show: rider_status=active, availability=available, can_accept_orders=true
```

### Test Scenario 2: Availability Updates
```bash
# 1. Rider sets to offline
PUT /api/riders/availability
{"availability": "offline"}

# 2. Admin checks available riders
GET /api/admin/riders/available
# Rider should NOT appear in list

# 3. Rider sets to available
PUT /api/riders/availability
{"availability": "available"}

# 4. Admin checks available riders again
GET /api/admin/riders/available
# Rider SHOULD appear in list
```

### Test Scenario 3: Suspension & Reactivation
```bash
# 1. Admin suspends rider
POST /api/admin/riders/{rider_id}/suspend
{"reason": "Testing suspension"}

# 2. Rider tries to update availability
PUT /api/riders/availability
{"availability": "available"}
# Should return 403 error

# 3. Admin reactivates rider
POST /api/admin/riders/{rider_id}/reactivate

# 4. Rider can now update availability
PUT /api/riders/availability
{"availability": "available"}
# Should succeed
```

---

## 🔗 Integration Examples

### Admin Dashboard: Display Rider Status
```javascript
// Fetch all riders
async function loadRiders() {
  const response = await fetch('/api/admin/riders', {
    headers: {
      'Authorization': `Bearer ${adminToken}`
    }
  });
  const data = await response.json();
  
  data.data.forEach(rider => {
    console.log(`Rider: ${rider.first_name} ${rider.last_name}`);
    console.log(`Status: ${rider.rider_status}`);
    console.log(`Availability: ${rider.availability}`);
    console.log(`Location: ${rider.current_location || 'Not set'}`);
    console.log(`Last Active: ${rider.last_active}`);
  });
}
```

### Rider Dashboard: Check Own Status
```javascript
// Check rider status on page load
async function checkRiderStatus() {
  const response = await fetch('/api/riders/status', {
    headers: {
      'Authorization': `Bearer ${riderToken}`
    }
  });
  const data = await response.json();
  
  if (data.data.can_accept_orders) {
    document.getElementById('status').textContent = '✅ Ready for Orders';
    document.getElementById('toggle-btn').disabled = false;
  } else {
    document.getElementById('status').textContent = data.data.status_message;
    document.getElementById('toggle-btn').disabled = true;
  }
}
```

### Toggle Rider Availability
```javascript
async function toggleAvailability(newStatus) {
  const response = await fetch('/api/riders/availability', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${riderToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ availability: newStatus })
  });
  
  const data = await response.json();
  
  if (data.success) {
    alert(`Availability changed to: ${newStatus}`);
    location.reload();
  } else {
    alert(`Error: ${data.message}`);
  }
}
```

### Update Rider Location
```javascript
async function updateLocation() {
  const location = document.getElementById('location-input').value;
  
  const response = await fetch('/api/riders/location', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${riderToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ location: location })
  });
  
  const data = await response.json();
  alert(data.message);
}
```

### Order Assignment: Check Rider Eligibility
```javascript
async function assignOrderToRider(orderId) {
  // First, get available riders
  const response = await fetch('/api/admin/riders/available', {
    headers: {
      'Authorization': `Bearer ${adminToken}`
    }
  });
  const data = await response.json();
  
  if (data.data.length === 0) {
    alert('No available riders at this time');
    return;
  }
  
  // Show list and let admin select
  const riderId = selectRiderFromList(data.data);
  
  // Assign order
  await fetch(`/api/admin/orders/${orderId}/assign`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ rider_id: riderId })
  });
}
```

---

## 🛠️ SQL Maintenance Queries

### Check Rider Statistics
```sql
SELECT 
    rider_status,
    availability,
    COUNT(*) as count
FROM riders
GROUP BY rider_status, availability;
```

### Find Inactive Riders
```sql
SELECT 
    r.id, u.email, r.rider_status, r.last_active
FROM riders r
JOIN users u ON r.user_id = u.id
WHERE r.last_active < DATE_SUB(NOW(), INTERVAL 7 DAY)
OR r.last_active IS NULL;
```

### Get Riders by Verification Status
```sql
-- Pending approval
SELECT * FROM riders WHERE verified = 0;

-- Active and available
SELECT * FROM riders 
WHERE verified = 1 
AND rider_status = 'active' 
AND availability = 'available';

-- Suspended riders
SELECT * FROM riders WHERE rider_status = 'suspended';
```

### Reset Rider to Pending
```sql
UPDATE riders 
SET rider_status = 'pending',
    availability = 'offline',
    verified = 0,
    approved_at = NULL
WHERE id = {rider_id};
```

### Bulk Activate All Verified Riders
```sql
UPDATE riders 
SET rider_status = 'active',
    approved_at = NOW()
WHERE verified = 1 AND rider_status = 'pending';
```

---

## 📋 Migration Guide

### Running the Migration
```bash
# Navigate to project directory
cd c:\Users\Imac\Downloads\qwerty

# Run migration script
python database/migrate_add_rider_status.py
```

### What the Migration Does
1. ✅ Adds `rider_status` ENUM column
2. ✅ Adds `availability` ENUM column
3. ✅ Adds `current_location` VARCHAR column
4. ✅ Adds `approved_at` DATETIME column
5. ✅ Adds `last_active` DATETIME column
6. ✅ Updates existing verified riders to 'active' status

### Rollback (if needed)
```sql
ALTER TABLE riders DROP COLUMN rider_status;
ALTER TABLE riders DROP COLUMN availability;
ALTER TABLE riders DROP COLUMN current_location;
ALTER TABLE riders DROP COLUMN approved_at;
ALTER TABLE riders DROP COLUMN last_active;
```

---

## 🎯 Summary

### Workflow Benefits
✅ **Automated Activation** - Admin approval instantly activates rider  
✅ **Real-Time Sync** - All updates immediately reflect in database  
✅ **Email Notifications** - Riders notified of approval automatically  
✅ **Status Management** - Complete control over rider states  
✅ **Availability Tracking** - Know which riders can accept orders  
✅ **Location Updates** - Track rider positions for better matching  
✅ **Suspension Controls** - Admin can suspend/reactivate riders  

### Key Features
- 🔐 Role-based access control
- 📧 Automatic email notifications
- ⚡ Real-time status synchronization
- 🚦 Multi-state status management
- 📍 Location tracking
- 📊 Comprehensive admin analytics
- 🔄 Reversible suspension system

---

## 🆘 Troubleshooting

### Issue: Rider can't update availability
**Cause:** Rider account not active  
**Solution:** Check `rider_status` - must be 'active'

### Issue: Rider doesn't appear in available list
**Causes:**
- `verified = 0` → Admin must approve first
- `rider_status != 'active'` → Admin must activate or reactivate
- `availability != 'available'` → Rider must change availability

### Issue: Email not received after approval
**Causes:**
- Email service not configured
- Invalid email address in user record
- Email in spam folder

**Check:** Look for email error in server logs

### Issue: Last active not updating
**Cause:** Queries not using NOW() or datetime.utcnow()  
**Solution:** All update queries automatically set last_active

---

**📅 Last Updated:** 2024-01-15  
**📝 Version:** 1.0  
**👨‍💻 Maintainer:** Hub E-Commerce Development Team
