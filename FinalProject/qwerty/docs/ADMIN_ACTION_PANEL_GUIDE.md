# Admin Action Panel - Complete Guide

## 🎯 Overview

The Admin Action Panel provides comprehensive disciplinary management tools for Sellers and Riders directly from the Admin Dashboard. Admins can issue warnings, apply suspensions, fines, restrictions, and permanent bans with full audit trail logging.

## 📋 Features

### For Sellers
1. **⚠️ Issue Warning** - Send formal warnings for policy violations
2. **⏸️ Suspend Account** - Temporarily suspend seller access (1-30+ days)
3. **💰 Apply Fine/Penalty** - Deduct amounts for violations or damages
4. **🚫 Product Restrictions** - Limit product listings or categories
5. **❌ Permanent Ban** - Irreversible account termination
6. **📊 Audit Log** - View complete action history

### For Riders
1. **⚠️ Issue Warning** - Send formal warnings for delivery issues
2. **⏸️ Suspend Account** - Temporarily suspend rider access (1-30+ days)
3. **🕐 Apply Cooldown** - Short-term delivery restrictions (2-48 hours)
4. **💸 Earnings Deduction** - Deduct for damaged goods or refunds
5. **❌ Permanent Ban** - Irreversible account termination
6. **📊 Audit Log** - View complete action history

## 🚀 How to Use

### Accessing the Action Panel

1. Login as admin at http://127.0.0.1:5000/admin_dashboard.html
   - Email: admin@hub.com
   - Password: admin123

2. Navigate to either:
   - **Sellers Management** section → Click "View" button on any seller
   - **Riders Management** section → Click "View" button on any rider

3. The Action Panel will open with 6 color-coded action buttons

### Action Types

#### 1. Issue Warning (Orange)
**When to use:** First offense, minor violations, educational purposes

**Seller Example:**
- Policy Violation
- Product Quality Issue
- Customer Complaint
- Late Delivery

**Rider Example:**
- Late Delivery
- Customer Complaint
- Unsafe Driving
- Policy Violation

**Process:**
1. Click "Issue Warning" button
2. Select warning type from dropdown
3. Enter detailed warning message
4. Click "Issue Warning"
5. Warning count automatically increments

**Effects:**
- Increases warning_count by 1
- Creates audit log entry
- No operational restrictions

---

#### 2. Suspend Account (Red)
**When to use:** Repeated violations, serious misconduct, investigation period

**Duration Options:**
- 1 Day
- 3 Days
- 7 Days
- 14 Days
- 30 Days
- Custom (enter any number of days)

**Process:**
1. Click "Suspend Account" button
2. Select suspension duration
3. Enter detailed suspension reason
4. Confirm suspension
5. Status changes immediately

**Effects:**
- Changes status to "suspended"
- Sets suspended_until date (auto-calculated)
- User cannot login or operate
- Products/deliveries become unavailable

---

#### 3. Apply Fine (Sellers) / Earnings Deduction (Riders) (Purple)
**When to use:** Customer refunds, damaged goods, policy violations with financial impact

**Seller Fine Types:**
- Policy Violation
- Late Shipping
- Product Issue
- Customer Refund Penalty
- Other

**Rider Deduction Types:**
- Customer Refund
- Damaged Goods
- Late Delivery Penalty
- Policy Violation
- Other

**Process:**
1. Click "Apply Fine" or "Earnings Deduction"
2. Enter amount in ₱ (Philippine Peso)
3. Select fine/deduction type
4. Enter detailed reason
5. Confirm amount
6. Deduction recorded immediately

**Effects:**
- **Sellers:** Increments total_fines column
- **Riders:** Increments earnings_deducted column
- Creates audit log with amount
- Financial records for accounting

---

#### 4. Product Restrictions (Sellers) / Cooldown (Riders)

**For Sellers (Gray):**
**When to use:** Quality issues, category bans, listing limits

**Restriction Types:**
- Restrict Adding New Products
- Restrict Editing Products
- Ban Specific Categories
- Limit Total Listings

**Process:**
1. Click "Product Restrictions"
2. Select restriction type
3. Enter restriction details (categories, limits, etc.)
4. Enter reason
5. Apply restriction

**Effects:**
- Increments restriction_level
- Admin must manually enforce restrictions in code
- Creates audit trail

---

**For Riders (Cyan):**
**When to use:** Temporary delivery breaks, minor issues, cooling off period

**Cooldown Periods:**
- 2 Hours
- 6 Hours
- 12 Hours
- 24 Hours
- 48 Hours

**Process:**
1. Click "Apply Cooldown"
2. Select cooldown period in hours
3. Enter reason
4. Apply cooldown

**Effects:**
- Sets cooldown_until timestamp
- Rider cannot accept new deliveries until timer expires
- Temporary restriction without full suspension

---

#### 5. Permanent Ban (Dark Red)
**⚠️ WARNING:** This action is **PERMANENT** and **IRREVERSIBLE**!

**When to use:** Severe violations, fraud, safety threats, repeated offenses

**Process:**
1. Click "Permanent Ban" button
2. Red warning box appears
3. Enter detailed ban reason
4. Check confirmation checkbox
5. Click "Permanently Ban Seller/Rider"
6. Second confirmation dialog appears
7. Confirm final action

**Effects:**
- Changes status to "banned"
- Sets is_active = 0 in users table
- User completely blocked from platform
- All products/services delisted
- Cannot be reversed (requires manual database edit)

---

#### 6. Audit Log (Blue)
**Purpose:** View complete history of all actions taken against this seller/rider

**Information Displayed:**
- Action type (WARNING, SUSPENSION, FINE, etc.)
- Timestamp (date and time)
- Admin who performed action
- Reason provided
- Duration/amount (if applicable)

**Process:**
1. Click "Audit Log" button
2. View chronological list (newest first)
3. Up to 50 most recent entries shown
4. Click "Close" when done reviewing

---

## 🗄️ Database Schema

### New Tables

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target_type ENUM('seller', 'rider') NOT NULL,
    target_id INT NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    reason TEXT,
    amount DECIMAL(10, 2) DEFAULT NULL,
    duration_days INT DEFAULT NULL,
    admin_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_target (target_type, target_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
);
```

### New Columns

#### sellers
- `suspended_until` DATETIME - When suspension expires
- `warning_count` INT - Total warnings issued
- `restriction_level` INT - Number of restrictions applied
- `total_fines` DECIMAL(10,2) - Total fines accumulated

#### riders
- `suspended_until` DATETIME - When suspension expires
- `cooldown_until` DATETIME - When cooldown expires
- `warning_count` INT - Total warnings issued
- `earnings_deducted` DECIMAL(10,2) - Total deductions

#### users
- `is_active` TINYINT(1) - Account active status (0 = banned)

---

## 🔌 API Endpoints

### Seller Actions
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/seller/warning` | POST | Issue warning |
| `/api/admin/seller/suspend` | POST | Suspend account |
| `/api/admin/seller/fine` | POST | Apply fine |
| `/api/admin/seller/restrict` | POST | Apply restrictions |
| `/api/admin/seller/ban` | POST | Permanent ban |
| `/api/admin/seller/<id>/audit-log` | GET | Get audit history |

### Rider Actions
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/rider/warning` | POST | Issue warning |
| `/api/admin/rider/suspend` | POST | Suspend account |
| `/api/admin/rider/cooldown` | POST | Apply cooldown |
| `/api/admin/rider/deduction` | POST | Earnings deduction |
| `/api/admin/rider/ban` | POST | Permanent ban |
| `/api/admin/rider/<id>/audit-log` | GET | Get audit history |

All endpoints require:
- **Authorization:** Bearer token (admin role)
- **Content-Type:** application/json

---

## 🧪 Testing Guide

### Test Scenario 1: Issue Seller Warning
1. Login as admin
2. Go to Sellers Management
3. Click "View" on seller (user_id=2)
4. Click "⚠️ Issue Warning"
5. Select "Policy Violation"
6. Enter: "Product descriptions must be accurate"
7. Submit
8. Verify success notification
9. Click "Audit Log" to verify entry

### Test Scenario 2: Suspend Rider
1. Login as admin
2. Go to Riders Management
3. Click "View" on rider (user_id=3)
4. Click "⏸️ Suspend Account"
5. Select "7 Days"
6. Enter: "Multiple late delivery complaints"
7. Confirm suspension
8. Verify rider status changes to "suspended"
9. Try logging in as rider → should fail

### Test Scenario 3: Apply Fine to Seller
1. Open seller action panel
2. Click "💰 Apply Fine/Penalty"
3. Enter amount: 500.00
4. Select "Customer Refund Penalty"
5. Enter reason: "Product damaged during shipping"
6. Confirm
7. Verify total_fines incremented in database:
   ```sql
   SELECT total_fines FROM sellers WHERE id = 2;
   ```

### Test Scenario 4: Permanent Ban
1. Open seller/rider action panel
2. Click "❌ Permanent Ban"
3. Read red warning
4. Enter detailed reason
5. Check confirmation checkbox
6. Click "Permanently Ban"
7. Confirm second dialog
8. Verify status = "banned"
9. Try logging in → should fail completely
10. Check users.is_active = 0

---

## 📊 Audit Trail Example

After performing actions, the audit log will show:

```
╔═══════════════════════════════════════════════════════════╗
║  2024-01-20 14:35:22                                      ║
║  WARNING: Policy Violation                                 ║
║  Product descriptions must be accurate and complete        ║
║  By: Admin User                                            ║
╠═══════════════════════════════════════════════════════════╣
║  2024-01-19 09:12:45                                      ║
║  SUSPENSION                                                ║
║  Multiple customer complaints about product quality        ║
║  Duration: 7 days                                          ║
║  By: Admin User                                            ║
╠═══════════════════════════════════════════════════════════╣
║  2024-01-15 16:20:33                                      ║
║  FINE: Customer Refund Penalty                             ║
║  Product damaged during shipping                           ║
║  Amount: ₱500.00                                           ║
║  By: Admin User                                            ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🎨 UI Elements

### Color Coding
- 🟠 **Orange** - Warning (caution)
- 🔴 **Red** - Suspension (temporary block)
- 🟣 **Purple** - Fine/Deduction (financial)
- ⚪ **Gray** - Restrictions (limitations)
- 🔵 **Blue** - Audit Log (information)
- ⚫ **Dark Red** - Permanent Ban (danger)

### Button Styles
All buttons have gradient backgrounds with hover effects:
```css
.warning-btn {
  background: linear-gradient(135deg, #ff9800, #f57c00);
}
.suspension-btn {
  background: linear-gradient(135deg, #ff5722, #e64a19);
}
```

---

## ⚠️ Important Notes

1. **Permanent bans cannot be undone** through the UI - requires manual database editing
2. **All actions are logged** with admin ID and timestamp
3. **Suspensions automatically expire** based on suspended_until date
4. **Cooldowns are shorter than suspensions** - for minor issues
5. **Fines are tracked but not automatically deducted** from payments (requires integration)
6. **Restrictions require custom enforcement** in product/delivery logic

---

## 🔐 Security

- All endpoints require `@role_required('admin')` decorator
- JWT token validation on every request
- SQL injection protection via parameterized queries
- CSRF protection via token-based auth
- Admin actions logged with admin_id for accountability

---

## 🛠️ Troubleshooting

### Issue: "Missing required fields"
**Solution:** Ensure all required form fields are filled (marked with *)

### Issue: Action panel not opening
**Solution:** 
1. Check browser console for JavaScript errors
2. Verify sellers/riders arrays are loaded
3. Ensure modal HTML exists in admin_dashboard.html

### Issue: Audit log empty
**Solution:**
1. Perform at least one action first
2. Check database: `SELECT * FROM audit_logs WHERE target_id = X`
3. Verify API endpoint returns 200 status

### Issue: Suspension not preventing login
**Solution:**
1. Check suspended_until date is in future
2. Verify shop_status/rider_status = 'suspended'
3. Clear browser localStorage and try again

---

## 📝 Change Log

### Version 1.0 (2024-01-20)
- Initial release
- Seller action panel with 6 actions
- Rider action panel with 6 actions
- Audit log system
- Database migration script
- 12 new API endpoints
- Complete UI with color-coded buttons

---

## 🎓 Best Practices

1. **Always provide detailed reasons** - helps with appeals and audits
2. **Start with warnings** before escalating to suspensions
3. **Document everything** in the reason field
4. **Review audit logs** before taking action
5. **Use cooldowns for minor issues** instead of full suspensions
6. **Double-check before permanent bans** - they cannot be undone
7. **Keep track of warning counts** - 3 strikes policy recommended
8. **Apply fines consistently** - document policy in separate guide

---

## 📞 Support

For issues or questions:
- Check console logs (F12 → Console)
- Review Flask logs in terminal
- Check database tables: audit_logs, sellers, riders, users
- Verify migration ran successfully

---

**End of Guide**
