# Seller Review System - Quick Start Guide

## Overview
The Seller Review System allows admins to review and approve/decline seller account applications before they can start selling on the platform.

## ✅ Setup (Already Completed)

1. **Database Migration** ✅
   - New columns added to `sellers` table (status, rejection_reason, reviewed_by, reviewed_at, contact_number, document_url)
   - New `seller_audit_log` table created for accountability
   - Existing sellers migrated to appropriate status

2. **Backend API Endpoints** ✅
   - `GET /api/admin/sellers/pending` - List sellers needing review
   - `GET /api/admin/sellers/<id>` - Get seller details
   - `PUT /api/admin/sellers/<id>/status` - Approve/decline seller
   - `GET /api/admin/sellers/stats` - Get review statistics

3. **Frontend Admin Dashboard** ✅
   - New "Seller Reviews" menu item with badge
   - Statistics cards
   - Filterable seller list
   - Detailed seller review modal
   - Approve/decline workflow

## 🚀 How to Use

### For Admins:

1. **Login as Admin**
   - Go to the admin dashboard
   - You'll see a pending badge next to "Seller Reviews" if there are sellers awaiting review

2. **Review Pending Sellers**
   - Click "Seller Reviews" in the sidebar
   - See all pending and declined sellers
   - Use filters to view:
     - Needs Review (pending + declined)
     - Pending Only
     - Declined Only
     - Approved
     - All sellers
   - Use search to find specific sellers

3. **Review Individual Seller**
   - Click "View" button on any seller
   - Review their information:
     - Business details
     - Owner information
     - Contact details
     - Application date
   - Check audit log for any previous actions

4. **Approve Seller**
   - In the seller detail modal, click "✅ Approve Seller"
   - Confirm the approval
   - Seller status changes to "active"
   - Seller receives notification
   - Action logged in audit trail

5. **Decline Seller**
   - In the seller detail modal, click "❌ Decline Seller"
   - Enter a reason for declining (required)
   - Click "Confirm Decline"
   - Seller status changes to "declined"
   - Seller receives notification with reason
   - Action logged in audit trail

### For Sellers:

1. **Register**
   - Create seller account
   - Status automatically set to "pending"
   - Wait for admin review

2. **Check Status**
   - Check notifications for approval/decline message
   - If approved: Can access seller dashboard and start selling
   - If declined: See rejection reason in notification

3. **Reapply** (if declined)
   - Contact support to address issues mentioned in decline reason
   - Admin can review and approve after issues are resolved

## 📊 Key Features

### Statistics Dashboard
- **Pending Review**: Number of sellers awaiting review
- **Approved**: Total approved sellers
- **Declined**: Total declined sellers
- **Total Sellers**: All sellers in system

### Filtering & Search
- Filter by status (pending, declined, approved, all)
- Search by business name, email, or owner name
- Sort by date, business name, or status

### Audit Trail
- Every action is logged
- Shows who performed action
- When action was performed
- Reason (if declining)
- Full accountability

### Notifications
- Sellers receive in-app notifications
- Approval: "🎉 Seller Account Approved!"
- Decline: "❌ Seller Account Declined" with reason

## 🧪 Testing

### Test the System:

1. **Create Test Seller**
   ```bash
   # Register a new seller account through the UI
   # Or use the registration API endpoint
   ```

2. **Run API Tests**
   ```bash
   python tools/test_seller_review_system.py
   ```

3. **Test Through UI**
   - Login as admin
   - Go to Seller Reviews
   - View pending seller
   - Test approve/decline

## 📁 Files Changed/Added

### Database:
- `database/migrate_add_seller_review_system_mysql.py` - Migration script

### Backend:
- `backend/server.py` - Added 4 new API endpoints

### Frontend:
- `frontend/admin_dashboard.html` - Added Seller Reviews section and modals
- `frontend/css/admin_dashboard.css` - Added styles for badges and status
- `frontend/js/admin_dashboard.js` - Added seller review functionality

### Documentation:
- `docs/SELLER_REVIEW_SYSTEM.md` - Comprehensive documentation
- `docs/SELLER_REVIEW_QUICKSTART.md` - This file

### Tools:
- `tools/test_seller_review_system.py` - API endpoint tests

## 🔐 Security

- ✅ Admin-only access (role-based authorization)
- ✅ JWT authentication required
- ✅ SQL injection prevention
- ✅ XSS protection
- ✅ Full audit trail

## 🎯 Workflow

```
1. Seller Registers
   ↓
2. Status: PENDING (default)
   ↓
3. Admin Reviews Application
   ↓
4a. APPROVE                    4b. DECLINE
    ↓                              ↓
5a. Status: ACTIVE            5b. Status: DECLINED
    ↓                              ↓
6a. Seller Can Start Selling  6b. Seller Notified with Reason
    ↓                              ↓
7a. Notification Sent         7b. Can Contact Support/Reapply
```

## 📝 Admin Checklist

When reviewing a seller:
- [ ] Verify business name is legitimate
- [ ] Check contact information is provided
- [ ] Validate business category
- [ ] Ensure location details are complete
- [ ] Verify email is valid and verified
- [ ] Check for any red flags
- [ ] Review previous audit log (if any)
- [ ] Make decision: Approve or Decline
- [ ] If declining, provide clear reason

## 💡 Tips

1. **Pending Badge**: The badge on "Seller Reviews" shows pending count and pulses to get your attention

2. **Search**: Use search to quickly find sellers by name, business, or email

3. **Filters**: Use "Needs Review" filter to see only sellers requiring action

4. **Audit Log**: Check audit log to see if seller was previously declined

5. **Decline Reasons**: Be specific when declining - helps sellers understand what to fix

6. **Statistics**: Monitor approval rates and pending backlog regularly

## 🐛 Troubleshooting

**Issue**: Badge not updating
- **Solution**: Reload the page or check browser console for errors

**Issue**: Can't approve/decline
- **Solution**: Verify you're logged in as admin, check JWT token is valid

**Issue**: Seller not showing in list
- **Solution**: Check status filter, try "All" filter

**Issue**: Error when approving/declining
- **Solution**: Check backend logs, verify database migration completed

## 📞 Support

For issues or questions:
- Check `docs/SELLER_REVIEW_SYSTEM.md` for detailed documentation
- Review backend server logs for API errors
- Check browser console for frontend errors
- Verify database migration completed successfully

---

**Quick Access URLs:**
- Admin Dashboard: `http://localhost:5000/admin_dashboard.html`
- Seller Reviews: Click "Seller Reviews" in admin sidebar
- API Base: `http://localhost:5000/api/admin/sellers/`

**Admin Test Credentials** (update in production):
- Email: `admin@example.com`
- Password: `admin123`
