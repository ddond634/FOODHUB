# Seller and Rider Resubmission Workflow System

## Overview
Complete implementation of a resubmission workflow that allows admins to decline seller/rider applications with specific missing requirements, and enables declined users to resubmit only the required documents using the same email address.

---

## 1. Database Schema

### Added Fields to `sellers` table:
- `missing_requirements` JSON NULL - Stores array of missing requirement labels
- `shop_status` ENUM - Updated to include 'declined' and 'resubmitted'
- `declined_at` DATETIME NULL
- `declined_by` INT NULL  
- `decline_reason` TEXT NULL
- `resubmitted_at` DATETIME NULL

### Added Fields to `riders` table:
- `missing_requirements` JSON NULL - Stores array of missing requirement labels
- `rider_status` ENUM - Updated to include 'declined' and 'resubmitted'
- `declined_at` DATETIME NULL
- `declined_by` INT NULL
- `decline_reason` TEXT NULL
- `resubmitted_at` DATETIME NULL

### New `notifications` table:
```sql
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type ENUM('info','warning','success','error') DEFAULT 'info',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    action_url VARCHAR(512) NULL,
    is_read TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Migration File:** `database/migrate_add_resubmission_fields.py`

---

## 2. Backend API Endpoints

### Seller Endpoints

#### POST `/api/admin/sellers/<seller_id>/decline`
Decline a seller application with missing requirements.

**Authorization:** Admin only  
**Request Body:**
```json
{
  "missing_requirements": [
    "Valid ID (Government-issued)",
    "Business Permit",
    "Profile Photo"
  ],
  "reason": "Missing critical documentation"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Seller application declined. Notification sent.",
  "data": {
    "seller_id": 2,
    "status": "declined",
    "missing_requirements": ["Valid ID", "Business Permit"]
  }
}
```

**Actions Performed:**
- Updates `shop_status` to 'declined'
- Stores missing requirements as JSON
- Records decline timestamp and admin ID
- Creates in-platform notification
- Sends email to seller with missing requirements list

---

#### POST `/api/admin/sellers/<seller_id>/approve`
Approve a seller application (pending or resubmitted).

**Authorization:** Admin only  
**Response:**
```json
{
  "success": true,
  "message": "Seller approved successfully",
  "data": {
    "seller_id": 2,
    "status": "active"
  }
}
```

**Actions Performed:**
- Updates `shop_status` to 'active'
- Sets `verified` to 1
- Clears missing_requirements field
- Updates user `is_verified` to 1
- Creates approval notification
- Sends congratulations email

---

#### POST `/api/admin/sellers/<seller_id>/request-documents`
Request additional documents without declining.

**Authorization:** Admin only  
**Request Body:**
```json
{
  "message": "Please upload updated business permit"
}
```

**Actions Performed:**
- Logs request in audit_logs
- Creates notification for seller
- Sends email with custom message

---

#### POST `/api/seller/resubmit`
Handle seller document resubmission.

**Authorization:** Token required (seller role)  
**Request Body:**
```json
{
  "documents": {
    "valid_id": "path/to/id.jpg",
    "business_permit": "path/to/permit.pdf"
  }
}
```

**Actions Performed:**
- Updates `shop_status` to 'resubmitted'
- Records resubmission timestamp
- Notifies admins of new submission

---

### Rider Endpoints

#### POST `/api/admin/riders/<rider_id>/decline`
Decline rider application with missing requirements.

**Authorization:** Admin only  
**Request Body:**
```json
{
  "missing_requirements": [
    "Driver's License",
    "Vehicle OR/CR",
    "Valid ID"
  ],
  "reason": "Incomplete documents"
}
```

**Response:** Same structure as seller decline

---

#### POST `/api/admin/riders/<rider_id>/approve`
Approve rider application.

**Authorization:** Admin only  
**Actions:** Same as seller approval

---

#### POST `/api/admin/riders/<rider_id>/request-resubmission`
Request rider to resubmit application with corrections.

**Authorization:** Admin only  
**Request Body:**
```json
{
  "message": "Please provide clearer photo of driver's license"
}
```

---

#### POST `/api/rider/resubmit`
Handle rider application resubmission.

**Authorization:** Token required (rider role)

---

### Notification Endpoints

#### GET `/api/notifications`
Get all notifications for current user.

**Authorization:** Token required  
**Response:**
```json
{
  "success": true,
  "message": "Notifications retrieved",
  "data": {
    "notifications": [
      {
        "id": 1,
        "type": "warning",
        "title": "Additional Documents Required",
        "message": "Your seller application requires...",
        "action_url": "/seller_dashboard.html?action=resubmit",
        "is_read": 0,
        "created_at": "2025-11-24T10:30:00"
      }
    ]
  }
}
```

---

#### PUT `/api/notifications/<notification_id>/mark-read`
Mark notification as read.

**Authorization:** Token required

---

#### GET `/api/user/status`
Get current user's application status and missing requirements.

**Authorization:** Token required  
**Response:**
```json
{
  "success": true,
  "message": "User status retrieved",
  "data": {
    "status": "declined",
    "missing_requirements": ["Valid ID", "Business Permit"],
    "decline_reason": "Missing critical documentation"
  }
}
```

---

## 3. Frontend Components

### Admin Dashboard Features

#### Missing Requirements Modal
**Location:** `frontend/js/admin_dashboard.js`

**Function:** `showMissingRequirementsModal(userType, userId)`

**Features:**
- Checkbox list of common requirements:
  - **Sellers:** Valid ID, Business Permit, Address Proof, Profile Photo, Store Logo, Other
  - **Riders:** Valid ID, Driver's License, Vehicle OR/CR, Profile Photo, Address Proof, Other
- Additional notes textarea for custom instructions
- Validates at least one requirement selected
- Styled with gradient backgrounds and animations
- Responsive design

**Usage:**
```javascript
// Called when admin clicks "Decline Seller" or "Decline Rider"
declineSeller(); // Shows modal for seller
declineRider();  // Shows modal for rider
```

---

#### Dynamic Action Buttons

**Pending Status:**
```javascript
// Seller
<button onclick="approveSellerApplication()">Approve Seller</button>
<button onclick="declineSeller()">Decline Seller</button>
<button onclick="requestSellerDocuments()">Request Documents</button>

// Rider
<button onclick="approveRider()">Approve Rider</button>
<button onclick="declineRider()">Decline Rider</button>
<button onclick="requestRiderReSubmission()">Request Re-Submission</button>
```

**Declined Status:**
```html
<div style="text-align: center; background: #f8d7da;">
  <i class="fas fa-ban"></i>
  <h4>Status: Declined</h4>
  <p>No admin actions available.</p>
</div>
```

**Active Status:**
- Sellers: Warning, Suspension, Fine/Penalty, Listing Restrictions, Permanent Ban
- Riders: Warning, Suspension, Cooldown, Earnings Deduction, Permanent Ban

---

### Email Notifications

#### Seller Decline Email
**Subject:** "Seller Application – Additional Documents Required"

**Content:**
- Professional HTML template
- Bulleted list of missing requirements
- Instructions to log in and resubmit
- Support contact information

#### Rider Decline Email
**Subject:** "Rider Application – Re-Submission Required"

**Content:**
- Similar structure to seller email
- Emphasizes re-submission process
- Includes missing requirements list

#### Approval Emails
- **Sellers:** "Seller Application Approved!" 
- **Riders:** "Rider Application Approved!"
- Congratulations message with next steps

---

### In-Platform Notifications

**Notification Banner (Yellow Alert):**
```html
<div class="notification-banner warning">
  ⚠ Additional documents required. 
  <a href="/seller_dashboard.html?action=resubmit">Resubmit now</a>
</div>
```

**Features:**
- Persistent until requirements submitted
- Click-through to resubmission form
- Dismissible but reappears on page reload
- Color-coded by type (warning, success, error, info)

---

## 4. User Experience Flow

### Admin Workflow

1. **Review Application**
   - Click "View" on pending seller/rider
   - Modal opens with complete application details

2. **Decline with Requirements**
   - Click "Decline Seller/Rider" button
   - Modal appears with checkbox list
   - Select missing requirements
   - Add optional notes
   - Click "Confirm Decline"

3. **Result**
   - Status changes to "declined"
   - User receives email and in-platform notification
   - Admin sees "Status: Declined" in modal (no actions)

4. **Review Resubmission**
   - When user resubmits, status changes to "resubmitted"
   - Admin receives notification
   - Review panel shows same approve/decline options
   - Can decline again with different requirements

---

### Seller/Rider Workflow

1. **Decline Notification**
   - Receives email: "Additional Documents Required"
   - Receives in-platform notification
   - Dashboard shows yellow warning banner

2. **Login Experience**
   - Can still log in with same email
   - Dashboard redirects to resubmission form
   - Form displays ONLY missing requirements

3. **Resubmission Form**
   ```html
   <h3>Resubmit Missing Documents</h3>
   <p>The following requirements are needed:</p>
   <ul>
     <li>✗ Valid ID (Government-issued)</li>
     <li>✗ Business Permit</li>
     <li>✗ Profile Photo</li>
   </ul>
   
   <form>
     <input type="file" name="valid_id" required>
     <input type="file" name="business_permit" required>
     <input type="file" name="profile_photo" required>
     <button>Resubmit Application</button>
   </form>
   ```

4. **After Resubmission**
   - Status changes to "resubmitted"
   - Success message: "Documents submitted. Admin will review."
   - Email confirmation sent
   - Can still access limited dashboard features

5. **Approval**
   - Receives approval email
   - Status changes to "active"
   - Full dashboard access granted
   - Welcome message displayed

---

## 5. Technical Implementation Details

### Status Enum Values

**Sellers (shop_status):**
- `pending` - Initial registration
- `active` - Approved and verified
- `suspended` - Temporarily suspended by admin
- `declined` - Rejected due to missing requirements
- `resubmitted` - User resubmitted after decline

**Riders (rider_status):**
- `pending` - Initial registration  
- `active` - Approved and verified
- `suspended` - Temporarily suspended
- `offline` - Not accepting orders
- `declined` - Rejected due to missing requirements
- `resubmitted` - User resubmitted after decline

---

### Missing Requirements Format

**Database Storage (JSON):**
```json
[
  "Valid ID (Government-issued)",
  "Business Permit",
  "Profile Photo"
]
```

**Frontend Display:**
```javascript
const requirements = JSON.parse(seller.missing_requirements);
requirements.forEach(req => {
  console.log(`Missing: ${req}`);
});
```

---

### Notification System

**Notification Types:**
- `info` - Blue - Informational messages
- `warning` - Yellow - Action required
- `success` - Green - Positive confirmation
- `error` - Red - Critical issues

**Auto-Expiration:**
```sql
-- Notifications expire after 30 days
expires_at = DATE_ADD(NOW(), INTERVAL 30 DAY)
```

---

## 6. Security Considerations

1. **Authorization Checks**
   - All admin endpoints use `@role_required('admin')`
   - User endpoints use `@token_required`
   - User can only access their own data

2. **Input Validation**
   - Missing requirements array validated (min 1 item)
   - File uploads sanitized and validated
   - SQL injection prevented with parameterized queries

3. **Data Privacy**
   - Decline reasons only visible to admin and affected user
   - Notifications are user-specific
   - Audit logs track all admin actions

---

## 7. Testing Checklist

### Admin Tests
- [ ] Decline seller with 1 requirement selected
- [ ] Decline seller with multiple requirements
- [ ] Decline without selecting requirements (should error)
- [ ] Approve pending seller
- [ ] Approve resubmitted seller
- [ ] View declined seller (verify no action buttons)
- [ ] Request documents from pending seller
- [ ] Repeat all tests for riders

### User Tests
- [ ] Receive decline email
- [ ] See in-platform notification
- [ ] Access resubmission form
- [ ] Upload only missing documents
- [ ] Resubmit application
- [ ] Receive confirmation
- [ ] Get approved and access full dashboard
- [ ] Test with same email throughout process

### Edge Cases
- [ ] User logs out and back in while declined
- [ ] Admin declines twice with different requirements
- [ ] User submits incomplete files
- [ ] Network error during resubmission
- [ ] Multiple admins reviewing same application

---

## 8. Files Modified/Created

### Database
- `database/migrate_add_resubmission_fields.py` ✓ Created

### Backend
- `backend/resubmission_api.py` ✓ Created
- `backend/server.py` ✓ Modified (registered blueprint)
- `backend/email_service.py` (uses existing send_email function)

### Frontend
- `frontend/js/admin_dashboard.js` ✓ Modified
  - Added `showMissingRequirementsModal()`
  - Added `confirmDecline()`
  - Updated `approveSellerApplication()`
  - Updated `declineSeller()` and `declineRider()`
  
### Documentation
- `docs/RESUBMISSION_WORKFLOW.md` ✓ This file

---

## 9. Future Enhancements

1. **Document Upload Preview**
   - Show thumbnails of uploaded documents
   - PDF viewer for permits/licenses

2. **Requirement Templates**
   - Admin can save common requirement sets
   - Quick-select templates for different seller types

3. **Automated Checks**
   - OCR validation of ID documents
   - Business permit number verification

4. **Bulk Actions**
   - Approve/decline multiple applications
   - Mass notifications

5. **Advanced Analytics**
   - Decline reasons statistics
   - Average resubmission time
   - Approval rate trends

---

## 10. API Response Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Missing required fields or invalid data |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permissions (not admin) |
| 404 | Not Found | Seller/rider ID does not exist |
| 500 | Server Error | Database or internal error |

---

## 11. Contact & Support

For issues or questions about this feature:
- Check audit logs for admin actions
- Review notification table for delivery status
- Verify email service configuration
- Test with test accounts: `pendingseller@hub.com`, `pendingrider@hub.com`

---

**Last Updated:** November 24, 2025  
**Version:** 1.0  
**Status:** ✅ Fully Implemented
