# Seller Review System Documentation

## Overview
The Seller Review System is a comprehensive admin feature that allows platform administrators to review, approve, or decline seller account applications before they can start selling on the platform.

## Features Implemented

### 1. **Database Schema**
- **sellers table** - New columns added:
  - `status` (ENUM: 'pending', 'active', 'declined') - Default: 'pending'
  - `rejection_reason` (TEXT) - Stores reason when declined
  - `reviewed_by` (INT) - Foreign key to admin user who reviewed
  - `reviewed_at` (DATETIME) - Timestamp of review
  - `contact_number` (VARCHAR) - Seller contact number
  - `document_url` (VARCHAR) - URL to submitted documents

- **seller_audit_log table** - New table for accountability:
  - `id` (INT) - Primary key
  - `seller_id` (INT) - Reference to seller
  - `admin_id` (INT) - Reference to admin who took action
  - `action` (VARCHAR) - Action taken (approved/declined)
  - `previous_status` (VARCHAR) - Status before action
  - `new_status` (VARCHAR) - Status after action
  - `reason` (TEXT) - Reason for action (if declined)
  - `created_at` (DATETIME) - When action was taken

### 2. **Backend API Endpoints**

#### GET `/api/admin/sellers/pending`
Get all sellers with pending or declined status for admin review.

**Query Parameters:**
- `status` - Filter by status (pending, declined, active) - default: "pending,declined"
- `search` - Search by business name, email, or name
- `sort` - Sort field (created_at, business_name, status, reviewed_at) - default: created_at
- `order` - Sort order (asc, desc) - default: desc

**Response:**
```json
{
  "success": true,
  "sellers": [
    {
      "id": 1,
      "user_id": 10,
      "business_name": "Fresh Bakery",
      "category": "Baking",
      "region": "NCR",
      "province": "Metro Manila",
      "city": "Quezon City",
      "status": "pending",
      "rejection_reason": null,
      "reviewed_by": null,
      "reviewed_at": null,
      "contact_number": "+63912345678",
      "document_url": null,
      "verified": 0,
      "email": "baker@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "created_at": "2025-11-23T00:00:00",
      "reviewed_by_email": null,
      "reviewed_by_first_name": null,
      "reviewed_by_last_name": null
    }
  ],
  "count": 1
}
```

#### GET `/api/admin/sellers/<seller_id>`
Get detailed information about a specific seller for review.

**Response:**
```json
{
  "success": true,
  "seller": {
    "id": 1,
    "user_id": 10,
    "business_name": "Fresh Bakery",
    "email": "baker@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "status": "pending",
    "created_at": "2025-11-23T00:00:00"
  },
  "audit_log": [
    {
      "id": 1,
      "seller_id": 1,
      "admin_id": 1,
      "action": "approved",
      "previous_status": "pending",
      "new_status": "active",
      "reason": null,
      "created_at": "2025-11-23T10:30:00",
      "admin_email": "admin@platform.com",
      "admin_first_name": "Admin",
      "admin_last_name": "User"
    }
  ]
}
```

#### PUT `/api/admin/sellers/<seller_id>/status`
Approve or decline a seller account.

**Request Body:**
```json
{
  "status": "active",  // or "declined"
  "reason": "Incomplete documents"  // required if declining
}
```

**Response:**
```json
{
  "success": true,
  "message": "Seller approved successfully",
  "seller_id": 1,
  "new_status": "active"
}
```

**Actions Performed:**
- Updates seller status
- Sets `verified` flag (1 for active, 0 for declined)
- Records admin who reviewed and timestamp
- Creates audit log entry
- Sends notification to seller via platform notifications

#### GET `/api/admin/sellers/stats`
Get statistics about seller accounts (pending, active, declined counts).

**Response:**
```json
{
  "success": true,
  "stats": {
    "total": 10,
    "pending": 3,
    "active": 6,
    "declined": 1
  }
}
```

### 3. **Frontend Admin Dashboard**

#### New Menu Item
- **"Seller Reviews"** - Added to sidebar navigation
- Shows pending count badge (updates in real-time)
- Badge pulses to draw attention when there are pending sellers

#### Seller Reviews Section
**Features:**
- Statistics cards showing:
  - Pending Review count
  - Approved count
  - Declined count
  - Total Sellers count

- Filter buttons:
  - "Needs Review" (pending + declined)
  - "Pending Only"
  - "Declined Only"
  - "Approved"
  - "All"

- Search functionality:
  - Search by business name, email, or owner name
  - Real-time filtering

- Sellers table showing:
  - ID
  - Business Name
  - Owner Name
  - Email
  - Category
  - Location
  - Status (with color-coded badges)
  - Applied Date
  - Actions (View button)

#### Seller Review Modal
When clicking "View" on a seller:
- Displays comprehensive seller information:
  - **Business Information:**
    - Business Name
    - Category
    - Location (City, Province, Region)
    - Contact Number
    - Status
  
  - **Owner Information:**
    - Full Name
    - Email
    - Email Verification Status
    - Applied Date
    - Reviewed By (if reviewed)
    - Reviewed At (if reviewed)
  
  - **Rejection Information** (if declined):
    - Rejection reason with highlighted display
  
  - **Audit Log**:
    - History of all actions taken
    - Admin who performed action
    - Timestamp
    - Reason (if applicable)

- Action Buttons (only for pending sellers):
  - **Approve Button** - Approves seller account
  - **Decline Button** - Opens decline reason modal

#### Decline Reason Modal
- Text area for entering decline reason
- Validation: Reason is required
- Actions:
  - Confirm Decline
  - Cancel

### 4. **Registration Flow Update**

When a seller registers:
1. User creates account with role='seller'
2. Seller profile created with `status='pending'`
3. `verified=0` by default
4. Seller cannot access seller features until approved
5. Admin receives notification of new seller application (via pending badge)

### 5. **Notification System**

When seller is approved:
- **Title:** "🎉 Seller Account Approved!"
- **Message:** "Congratulations! Your seller account has been approved. You can now start selling on our platform."

When seller is declined:
- **Title:** "❌ Seller Account Declined"
- **Message:** "Your seller account application has been declined. Reason: [reason provided by admin]"

### 6. **Audit Trail**

Every action is logged in `seller_audit_log` table:
- Who performed the action (admin_id)
- What action was taken (approved/declined)
- When it was performed (created_at)
- Previous and new status
- Reason (if declining)

This provides:
- Full accountability
- Compliance tracking
- Dispute resolution capability
- Performance metrics for admins

## Access Control

- **Only admins** can access seller review endpoints
- Protected by `@role_required('admin')` decorator
- Uses JWT authentication
- Unauthorized access returns 403 Forbidden

## Migration

**Run Migration:**
```bash
python database/migrate_add_seller_review_system_mysql.py
```

**What it does:**
- Adds new columns to sellers table
- Creates seller_audit_log table
- Updates existing sellers:
  - verified=1 sellers → status='active'
  - verified=0 sellers → status='pending'

## Testing

### Test Seller Registration:
1. Register new seller account
2. Check that status is 'pending'
3. Verify seller cannot access seller features
4. Check admin dashboard shows pending count

### Test Approval:
1. Login as admin
2. Go to "Seller Reviews" section
3. Click "View" on pending seller
4. Click "Approve"
5. Verify seller status changes to 'active'
6. Verify seller receives notification
7. Check audit log records action

### Test Decline:
1. Login as admin
2. View pending seller
3. Click "Decline"
4. Enter decline reason
5. Click "Confirm Decline"
6. Verify seller status changes to 'declined'
7. Verify seller receives notification with reason
8. Check audit log records action and reason

## Future Enhancements

Potential additions:
- Email notifications (in addition to platform notifications)
- Document upload and verification
- Multi-step approval workflow
- Seller re-application process
- Bulk approval/decline actions
- Export seller applications to CSV
- Advanced filtering (by date range, category, location)
- Approval templates for common decline reasons
- Performance metrics dashboard
- SLA tracking for review times

## Security Considerations

- ✅ Admin-only access enforced
- ✅ JWT authentication required
- ✅ SQL injection prevention (parameterized queries)
- ✅ XSS prevention (proper escaping in frontend)
- ✅ Audit trail for accountability
- ✅ Input validation on both frontend and backend
- ✅ Rate limiting recommended for production

## Database Indexes (Recommended for Production)

```sql
-- Add indexes for better query performance
CREATE INDEX idx_sellers_status ON sellers(status);
CREATE INDEX idx_sellers_reviewed_at ON sellers(reviewed_at);
CREATE INDEX idx_seller_audit_log_seller_id ON seller_audit_log(seller_id);
CREATE INDEX idx_seller_audit_log_created_at ON seller_audit_log(created_at);
```

## API Rate Limiting (Recommended)

For production, consider implementing rate limiting:
- Seller review endpoints: 100 requests/minute per admin
- Status update endpoint: 30 requests/minute per admin

## Monitoring

Key metrics to track:
- Average review time (from application to decision)
- Approval rate (approved / total reviewed)
- Pending backlog
- Admin review throughput
- Decline reasons distribution

## Support

For issues or questions:
- Check audit logs for action history
- Review backend server logs for errors
- Check browser console for frontend errors
- Verify database migration completed successfully

---

**Version:** 1.0  
**Last Updated:** November 23, 2025  
**Author:** Development Team
