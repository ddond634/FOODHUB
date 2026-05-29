# Shipping System Documentation

## Overview

The Shipping System allows sellers to configure shipping preferences that automatically calculate shipping costs at checkout. The system features threshold-based free shipping and per-item shipping fees.

---

## Features

### Seller Features
- **Configure Standard Shipping Fee**: Set a per-item shipping cost (e.g., ₱50.00 per item)
- **Set Free Shipping Threshold**: Define minimum order amount for free shipping (e.g., ₱500.00)
- **Real-time Settings Management**: Save and load shipping preferences instantly
- **Input Validation**: Automatic validation of numeric values and reasonable limits

### Customer Features
- **Automatic Calculation**: Shipping costs calculated at checkout based on seller's settings
- **Free Shipping Indicator**: See when orders qualify for free shipping
- **Multi-Store Support**: Separate shipping calculation for each seller in the cart
- **Transparent Pricing**: Clear breakdown of shipping costs per store

---

## Database Schema

### Migration: `migrate_add_shipping_preferences.py`

Added two columns to the `sellers` table:

```sql
-- Free shipping threshold (order subtotal)
free_shipping_threshold DECIMAL(10,2) DEFAULT 500.00

-- Standard shipping fee per item
standard_shipping_fee DECIMAL(10,2) DEFAULT 50.00
```

**Default Values:**
- Free Shipping Threshold: ₱500.00
- Standard Shipping Fee: ₱50.00 per item

**Data Types:**
- DECIMAL(10,2) - Supports up to ₱99,999,999.99
- MySQL and SQLite compatible

---

## Backend API

### Endpoints

#### 1. GET `/api/seller/settings/shipping`
Get current shipping settings for the authenticated seller.

**Authentication:** Required (Seller role)

**Headers:**
```json
{
  "Authorization": "Bearer <token>",
  "Content-Type": "application/json"
}
```

**Response (200 OK):**
```json
{
  "seller_id": 123,
  "business_name": "My Store",
  "free_shipping_threshold": 500.00,
  "standard_shipping_fee": 50.00
}
```

**Error Responses:**
- 401: Unauthorized (no token or invalid token)
- 404: Seller not found
- 500: Server error

---

#### 2. POST `/api/seller/settings/shipping`
Update shipping settings for the authenticated seller.

**Authentication:** Required (Seller role)

**Headers:**
```json
{
  "Authorization": "Bearer <token>",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "free_shipping_threshold": 500.00,
  "standard_shipping_fee": 50.00
}
```

**Validation Rules:**
- Both fields are required
- Must be numeric (float or int)
- Must be non-negative (>= 0)
- `standard_shipping_fee` max: ₱10,000
- `free_shipping_threshold` max: ₱1,000,000

**Response (200 OK):**
```json
{
  "message": "Shipping settings updated successfully",
  "settings": {
    "free_shipping_threshold": 500.00,
    "standard_shipping_fee": 50.00
  }
}
```

**Error Responses:**
- 400: Invalid input (missing fields, negative values, exceeds limits)
- 401: Unauthorized
- 404: Seller not found
- 500: Server error

---

#### 3. GET `/api/store/{store_id}/shipping`
Get shipping settings for a specific store (public endpoint for checkout).

**Authentication:** Not required (public)

**URL Parameters:**
- `store_id` (integer): The seller's ID

**Response (200 OK):**
```json
{
  "store_id": 123,
  "business_name": "My Store",
  "free_shipping_threshold": 500.00,
  "standard_shipping_fee": 50.00
}
```

**Error Responses:**
- 404: Store not found
- 500: Server error

---

#### 4. POST `/api/checkout/calculate-shipping`
Calculate total shipping cost for a multi-store checkout.

**Authentication:** Not required (public)

**Request Body:**
```json
{
  "stores": [
    {
      "store_id": 123,
      "items": [
        {
          "price": 100.00,
          "quantity": 2
        },
        {
          "price": 150.00,
          "quantity": 1
        }
      ]
    },
    {
      "store_id": 456,
      "items": [
        {
          "price": 200.00,
          "quantity": 3
        }
      ]
    }
  ]
}
```

**Calculation Logic:**
For each store:
1. Calculate `subtotal = sum(item.price * item.quantity)`
2. Count `total_items = sum(item.quantity)`
3. If `subtotal >= free_shipping_threshold`: **FREE SHIPPING**
4. Otherwise: `shipping = standard_shipping_fee * total_items`

**Response (200 OK):**
```json
{
  "total_shipping": 100.00,
  "breakdown": [
    {
      "store_id": 123,
      "business_name": "My Store",
      "subtotal": 350.00,
      "items_count": 3,
      "shipping_cost": 0.00,
      "is_free_shipping": true,
      "free_shipping_threshold": 500.00
    },
    {
      "store_id": 456,
      "business_name": "Another Store",
      "subtotal": 600.00,
      "items_count": 3,
      "shipping_cost": 100.00,
      "is_free_shipping": false,
      "standard_shipping_fee": 50.00
    }
  ]
}
```

**Error Responses:**
- 400: Invalid input (missing stores, invalid format)
- 404: Store not found
- 500: Server error

---

## Frontend Implementation

### Seller Dashboard - Settings Section

**Location:** `frontend/seller_dashboard.html` (Lines 883-930)

**Form Fields:**

1. **Standard Shipping Fee (₱ per item)**
   - Input type: `number`
   - ID: `standardShippingFee`
   - Validation: min="0", step="0.01"
   - Default: 50.00

2. **Free Shipping Threshold (₱)**
   - Input type: `number`
   - ID: `freeShippingThreshold`
   - Validation: min="0", step="0.01"
   - Default: 500.00

3. **Save Button**
   - Calls: `saveShippingSettings()`
   - Full-width primary button
   - Icon: Save icon

**JavaScript Functions:** `frontend/js/seller_dashboard.js` (Lines 2314-2467)

#### `loadShippingSettings()`
- Loads current settings from backend API
- Called automatically when switching to Settings section
- Populates form fields with current values
- Handles authentication and error states

#### `saveShippingSettings()`
- Validates input values (numeric, non-negative, within limits)
- Sends POST request to backend API
- Shows success/error messages
- Updates form with saved values

#### `showShippingMessage(message, type)`
- Displays feedback messages to seller
- Types: 'success', 'error', 'info'
- Auto-hides success messages after 5 seconds
- Color-coded borders and backgrounds

---

## Integration Points

### Settings Section Loading
When the seller clicks on "Settings" in the navigation:

```javascript
// In switchSection() function
if (sectionId === 'settings') {
    if (typeof loadShippingSettings === 'function') {
        loadShippingSettings();
    }
}
```

### Checkout Integration (To Be Implemented)
The shipping calculation should be integrated into the checkout flow:

1. **Cart Page:**
   - Group items by seller/store
   - Calculate subtotal per store
   - Call `/api/checkout/calculate-shipping`
   - Display shipping breakdown

2. **Checkout Page:**
   - Show per-store shipping costs
   - Display "FREE SHIPPING" badge when applicable
   - Show progress to free shipping (e.g., "₱150 more for free shipping")
   - Update totals dynamically

3. **Order Summary:**
   - List shipping cost per store
   - Include in grand total
   - Highlight free shipping benefits

---

## Calculation Examples

### Example 1: Free Shipping Achieved

**Seller Settings:**
- Free Shipping Threshold: ₱500.00
- Standard Shipping Fee: ₱50.00 per item

**Customer Cart:**
- Item 1: ₱200.00 × 2 = ₱400.00
- Item 2: ₱150.00 × 1 = ₱150.00
- **Subtotal: ₱550.00**
- Items Count: 3

**Calculation:**
```
Subtotal (₱550) >= Threshold (₱500)
→ FREE SHIPPING! ✓
Shipping Cost: ₱0.00
```

---

### Example 2: Standard Shipping Applied

**Seller Settings:**
- Free Shipping Threshold: ₱500.00
- Standard Shipping Fee: ₱50.00 per item

**Customer Cart:**
- Item 1: ₱100.00 × 2 = ₱200.00
- Item 2: ₱80.00 × 1 = ₱80.00
- **Subtotal: ₱280.00**
- Items Count: 3

**Calculation:**
```
Subtotal (₱280) < Threshold (₱500)
→ Apply standard shipping
Shipping Cost: ₱50.00 × 3 items = ₱150.00
```

---

### Example 3: Multi-Store Checkout

**Store A Settings:**
- Threshold: ₱500.00
- Fee: ₱50.00 per item

**Store B Settings:**
- Threshold: ₱1000.00
- Fee: ₱75.00 per item

**Customer Cart:**
- **From Store A:**
  - Subtotal: ₱600.00 (3 items)
  - ₱600 >= ₱500 → FREE SHIPPING
  - Shipping: ₱0.00

- **From Store B:**
  - Subtotal: ₱400.00 (2 items)
  - ₱400 < ₱1000 → Apply fee
  - Shipping: ₱75.00 × 2 = ₱150.00

**Total Shipping: ₱150.00**

---

## Testing Guide

### 1. Test Seller Settings Management

**Load Settings:**
1. Log in as a seller
2. Navigate to Settings → Shipping Preferences
3. Verify default values (₱500.00, ₱50.00) are displayed
4. Check that fields are properly populated

**Save Settings:**
1. Change Free Shipping Threshold to ₱1000.00
2. Change Standard Shipping Fee to ₱75.00
3. Click "Save Shipping Settings"
4. Verify success message appears
5. Refresh page and check values persist

**Validation Tests:**
1. Try negative value → Should show error
2. Try non-numeric value → Browser validation
3. Try fee > ₱10,000 → Should show error
4. Try threshold > ₱1,000,000 → Should show error
5. Try empty fields → Should show error

---

### 2. Test API Endpoints

**Using curl or Postman:**

```bash
# Get seller settings (requires auth token)
curl -X GET http://localhost:5000/api/seller/settings/shipping \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update settings
curl -X POST http://localhost:5000/api/seller/settings/shipping \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "free_shipping_threshold": 1000.00,
    "standard_shipping_fee": 75.00
  }'

# Get store shipping (public)
curl -X GET http://localhost:5000/api/store/1/shipping

# Calculate shipping
curl -X POST http://localhost:5000/api/checkout/calculate-shipping \
  -H "Content-Type: application/json" \
  -d '{
    "stores": [
      {
        "store_id": 1,
        "items": [
          {"price": 100.00, "quantity": 2},
          {"price": 150.00, "quantity": 1}
        ]
      }
    ]
  }'
```

---

### 3. Test Checkout Calculation

**Test Cases:**

1. **Single Store, Free Shipping:**
   - Subtotal: ₱600.00
   - Items: 3
   - Expected: ₱0.00 shipping

2. **Single Store, Standard Shipping:**
   - Subtotal: ₱200.00
   - Items: 2
   - Expected: ₱50.00 × 2 = ₱100.00 shipping

3. **Multi-Store Mixed:**
   - Store A: ₱600 (free) + Store B: ₱300 (paid)
   - Expected: Total varies by Store B settings

4. **Edge Cases:**
   - Subtotal exactly equals threshold → Free shipping
   - Zero items → ₱0.00 shipping
   - Zero threshold → Always free shipping
   - Zero fee → Always free shipping

---

## Configuration

### Default Values

Sellers start with these defaults when they first register:

```python
free_shipping_threshold = 500.00  # ₱500
standard_shipping_fee = 50.00      # ₱50 per item
```

### Limits

To prevent abuse and maintain reasonable pricing:

```python
MAX_SHIPPING_FEE = 10000.00        # ₱10,000 per item
MAX_FREE_THRESHOLD = 1000000.00    # ₱1,000,000
MIN_VALUE = 0.00                   # No negative values
```

### Database Precision

- Storage: `DECIMAL(10,2)`
- Max value: ₱99,999,999.99
- Precision: 2 decimal places (centavos)

---

## Future Enhancements

### Planned Features

1. **Multiple Shipping Tiers:**
   - Express shipping (higher fee)
   - Same-day delivery (premium)
   - Store pickup (free)

2. **Location-Based Shipping:**
   - Different rates by region/province
   - Metro Manila vs. provinces
   - International shipping

3. **Weight-Based Calculation:**
   - Add product weight field
   - Calculate shipping by total weight
   - Dimensional weight support

4. **Shipping Zones:**
   - Define zones with custom rates
   - Zone-based free shipping thresholds
   - Exclude certain areas

5. **Promotional Free Shipping:**
   - Time-limited free shipping campaigns
   - Free shipping for specific products
   - First-time buyer free shipping

6. **Customer Shipping Preferences:**
   - Save delivery addresses
   - Choose preferred shipping method
   - Schedule delivery time

7. **Real-Time Tracking:**
   - Integration with courier APIs
   - Tracking number generation
   - Delivery status updates

---

## Troubleshooting

### Common Issues

**1. Settings Not Saving**
- Check browser console for errors
- Verify auth token is present in localStorage
- Ensure backend server is running
- Check network tab for API response

**2. Calculation Incorrect**
- Verify subtotal calculation includes all items
- Check quantity is being multiplied correctly
- Ensure threshold comparison uses correct operator (>=)
- Confirm store_id matches seller ID

**3. Settings Not Loading**
- Check that `loadShippingSettings()` is called on section switch
- Verify seller ID in token matches database
- Check database migration ran successfully
- Ensure columns exist with correct data types

**4. API Errors**
- 401: Token expired or invalid → Re-login
- 404: Store not found → Check store_id
- 400: Invalid input → Check request format
- 500: Server error → Check server logs

---

## File Structure

```
qwerty/
├── backend/
│   ├── shipping_api.py           # 292 lines - Shipping API endpoints
│   └── server.py                 # Shipping blueprint registration
├── database/
│   └── migrate_add_shipping_preferences.py  # Database migration
├── frontend/
│   ├── seller_dashboard.html     # Settings UI (lines 883-930)
│   └── js/
│       └── seller_dashboard.js   # Shipping functions (lines 2314-2467)
└── docs/
    └── SHIPPING_SYSTEM.md        # This file
```

---

## API Blueprint Registration

The shipping API is registered in `backend/server.py`:

```python
from backend.shipping_api import shipping_bp

app.register_blueprint(shipping_bp)
```

All endpoints are prefixed with `/api/` automatically.

---

## Security Considerations

### Authentication
- Seller endpoints require valid JWT token
- Token validated by `@role_required('seller')` decorator
- Public endpoints (store info, calculate) don't require auth

### Input Validation
- All numeric inputs validated server-side
- Maximum limits enforced to prevent abuse
- SQL injection prevented by parameterized queries
- XSS prevented by proper input sanitization

### Authorization
- Sellers can only view/edit their own settings
- Cannot modify other sellers' shipping preferences
- Public endpoints don't expose sensitive data

---

## Performance Considerations

### Database Queries
- Simple SELECT queries with indexed columns
- No complex joins or subqueries
- Fast lookups by seller ID (primary key)

### Caching Opportunities
- Store shipping settings can be cached
- Cache invalidation on settings update
- Reduce database load for frequent calculations

### Optimization Tips
- Calculate shipping client-side after initial load
- Only call API when cart changes or checkout initiated
- Batch calculate for all stores in one request
- Use connection pooling for concurrent requests

---

## Success Metrics

Track these metrics to measure system adoption:

1. **Seller Adoption:**
   - % of sellers who customize shipping settings
   - Average threshold amount
   - Average shipping fee

2. **Free Shipping Impact:**
   - % of orders with free shipping
   - Average order value increase
   - Conversion rate improvement

3. **Customer Behavior:**
   - Cart abandonment rate changes
   - Orders just above/below threshold
   - Multi-store checkout frequency

4. **API Performance:**
   - Average response time
   - Error rate by endpoint
   - Peak concurrent requests

---

## Conclusion

The Shipping System provides flexible, automatic shipping cost calculation that benefits both sellers and customers. Sellers can configure competitive shipping rates and incentivize larger orders through free shipping thresholds, while customers enjoy transparent, predictable shipping costs that update in real-time.

The system is fully functional on the backend and seller dashboard. Next steps include integrating the calculation into the customer checkout flow and adding visual indicators for free shipping eligibility.

---

## Quick Reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/seller/settings/shipping` | GET | Seller | Get own settings |
| `/api/seller/settings/shipping` | POST | Seller | Update settings |
| `/api/store/{id}/shipping` | GET | Public | Get store settings |
| `/api/checkout/calculate-shipping` | POST | Public | Calculate total |

| Setting | Default | Max | Description |
|---------|---------|-----|-------------|
| `free_shipping_threshold` | ₱500.00 | ₱1M | Order subtotal for free shipping |
| `standard_shipping_fee` | ₱50.00 | ₱10K | Fee per item |

**Calculation Formula:**
```
IF subtotal >= threshold THEN
    shipping = 0
ELSE
    shipping = fee × item_count
END IF
```

---

*Last Updated: November 24, 2025*
*System Status: ✅ Backend Complete | ✅ Seller UI Complete | ⏳ Checkout Integration Pending*
