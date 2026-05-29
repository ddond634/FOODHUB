# Admin Sales Approval System - Quick Guide

## Overview
The admin sales approval interface allows you to review and manage discount requests from sellers for products nearing expiry. This system protects both seller margins and platform commission while offering value to customers.

## Accessing the Interface
1. Log in to the admin dashboard at `admin_dashboard.html`
2. Click **"Sales Approvals"** in the left sidebar
3. The system will automatically load all pending sale requests

## Understanding Sale Requests

### Urgency Levels
Each sale request is classified by urgency based on days until product expiry:

- **Critical** (Red): ≤3 days until expiry - Immediate action recommended
- **High** (Orange): 4-7 days until expiry - Review soon
- **Medium** (Yellow): 8-14 days until expiry - Standard priority
- **Low** (Green): >14 days until expiry - Can be reviewed later

### Profit Analysis
Each request card displays:

- **Original Price**: Product's current retail price
- **Sale Price**: Proposed discounted price
- **Discount Percentage**: Percentage reduction from original
- **Seller Margin**: Seller's profit margin at sale price (should be ≥10%)
- **Platform Commission**: Your platform's commission (typically 7.5%)

### Warning Indicators
- ⚠️ **Low Margin Warning**: Appears when seller margin falls below 10%
- This indicates the seller may be operating at break-even or minimal profit

## Taking Action

### Approving a Sale
1. Review the profit analysis to ensure viable margins
2. Check the urgency level and days until expiry
3. Click the green **"Approve"** button
4. Confirm the approval in the dialog
5. The discount becomes active immediately
6. The seller receives a notification

**When to Approve:**
- Seller margin is ≥10%
- Platform commission is maintained
- Discount is reasonable for the urgency level
- Product details are correct

### Rejecting a Sale
1. Click the red **"Reject"** button
2. Enter a detailed reason for rejection
3. Click **"Confirm Rejection"**
4. The seller receives the rejection with your notes

**Common Rejection Reasons:**
- Discount too high relative to urgency
- Seller margin below recommended threshold
- Pricing appears incorrect
- Product information incomplete
- Suspicious request pattern

## Statistics Dashboard
The sales section displays key metrics:

- **Pending Review**: Total requests awaiting your decision
- **Approved Today**: Sales approved in current day
- **Rejected**: Total declined requests
- **Critical Urgency**: Products expiring in ≤3 days requiring immediate attention

## Best Practices

### Review Priority
1. Sort by urgency (system does this automatically)
2. Address **Critical** (red) items first
3. Review profit margins carefully
4. Verify product details match seller inventory

### Approval Guidelines
- **Always** ensure seller margin ≥10% to protect seller viability
- **Always** maintain platform commission
- Approve time-sensitive requests promptly to reduce waste
- Reject unrealistic discounts that may indicate pricing errors

### Communication
- Provide clear, actionable feedback in rejection notes
- Be specific about what needs to change
- Help sellers understand profit protection requirements

## Smart Discount Logic (Background)
The system calculates discounts automatically based on:

- **Cost Estimation**: 65% of retail price
- **Platform Commission**: 7.5% of sale price
- **Minimum Margin**: 10% above break-even
- **Urgency Tiers**:
  - Last day: 40% discount
  - 1-3 days: 30% discount
  - 4-7 days: 20% discount
  - 8-14 days: 15% discount
  - 14+ days: 10% discount

These are **suggestions** - sellers can request custom discounts, which you must approve.

## API Integration
The interface uses these endpoints:

- `GET /api/admin/pending-sales` - Fetch all pending requests
- `POST /api/admin/sales/:id/approve` - Approve a sale
- `POST /api/admin/sales/:id/reject` - Reject with notes

## Troubleshooting

### No Pending Sales Showing
- Check network console for API errors
- Verify your admin token is valid
- Ensure sellers have submitted requests

### Error Approving/Rejecting
- Check server logs for backend errors
- Verify database connection
- Ensure sale request still exists and is pending

### Badge Not Updating
- Refresh the dashboard
- Check browser console for JavaScript errors
- Verify stats update function is running

## Support
For technical issues, refer to:
- `docs/SALES_SYSTEM_GUIDE.md` - Complete sales system documentation
- `docs/API_ENDPOINTS_REFERENCE.md` - API endpoint details
- Backend logs in `qwerty/` directory

---

**Note**: This system helps reduce food waste while maintaining business viability. Balance customer value with sustainable margins when making decisions.
