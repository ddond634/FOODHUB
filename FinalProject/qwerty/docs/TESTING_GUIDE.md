# End-to-End Testing Guide

## Quick Start: Test Complete Workflows

Follow these steps to test the entire e-commerce system with all 4 user types.

---

## PREREQUISITE: Start the Server

```powershell
cd "c:\Users\Imac\Downloads\hindi kAYANG TUMBASAN NG KAHIT ANONG SALAPI\qwerty"
python backend\run_server.py
```

The server will start at `http://localhost:5000`

---

## WORKFLOW TEST 1: CUSTOMER REGISTRATION & BROWSING

### Step 1.1: Register as Customer
1. Go to `http://localhost:5000/loginregister.html`
2. Click "Customer" tab
3. Fill in:
   - Email: `customer1@test.com`
   - Password: `Test123!`
   - First Name: `Juan`
   - Last Name: `Dela Cruz`
4. Click "Register"
5. Enter OTP code (check server console for code, usually `123456`)
6. Click "Verify"
7. You should be redirected to account.html

### Expected Results:
✅ Account created with role='customer'
✅ Session token stored in localStorage
✅ Profile page shows customer info
✅ No "Become a Seller" option visible

---

## WORKFLOW TEST 2: SELLER REGISTRATION & PRODUCT LISTING

### Step 2.1: Register as Seller
1. Go back to `http://localhost:5000/loginregister.html`
2. Click "Seller" tab
3. Fill in:
   - Email: `seller1@test.com`
   - Password: `Test123!`
   - First Name: `Juan`
   - Last Name: `Santos`
   - Business Name: `Juan's Burgers`
   - Category: `Fast Food`
4. Click "Register"
5. Verify with OTP (check console)
6. Redirected to seller_dashboard.html

### Expected Results:
✅ User created with role='seller'
✅ Seller record created with business_name, verified=0
✅ Dashboard shows "Pending verification" (admin approval needed)

### Step 2.2: Add Product for Sale
1. From seller_dashboard.html, click "Inventory" in sidebar
2. Click "Add Product" button
3. Fill in:
   - Product Name: `Homemade Burger`
   - Description: `Fresh beef patty with premium toppings`
   - Category: `Fast Food`
   - Price: `199.00`
   - Stock: `50`
   - Image URL: `https://source.unsplash.com/300x300/?burger`
4. Click "Save Product"

### Expected Results:
✅ Product created in products table
✅ seller_id = seller1's user_id
✅ Product appears in seller's inventory list
✅ Stock status shows "In Stock"

### Step 2.3: Edit Product Stock
1. In inventory list, click "Edit" on the burger product
2. Change stock to `45`
3. Click "Save Product"

### Expected Results:
✅ Stock updated to 45
✅ Status remains "In Stock"

### Step 2.4: Add Low-Stock Product
1. Click "Add Product" again
2. Fill in:
   - Product Name: `Premium Coffee`
   - Price: `150.00`
   - Stock: `5`
3. Save

### Expected Results:
✅ Product created with stock=5
✅ Status shows "Low Stock" (yellow badge)

---

## WORKFLOW TEST 3: ADMIN VERIFICATION

### Step 3.1: Register as Admin (Database Seed)
1. Open your database editor (SQLite viewer)
2. Query: `SELECT * FROM users WHERE role='admin'`
3. If no admin exists, insert:
   ```sql
   INSERT INTO users (email, password_hash, first_name, last_name, role, created_at)
   VALUES ('admin@test.com', 'hashed_password', 'Admin', 'User', 'admin', datetime('now'));
   ```

### Step 3.2: Test Admin Endpoints (Via Postman or Terminal)

**Get Admin Dashboard**:
```powershell
$headers = @{
    'Authorization' = 'Bearer <admin_token>'
    'Content-Type' = 'application/json'
}
Invoke-WebRequest -Uri "http://localhost:5000/api/admin/dashboard" -Headers $headers
```

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "total_users": 2,
    "user_breakdown": {"customer": 1, "seller": 1},
    "total_orders": 0,
    "total_revenue": 0,
    "pending_verifications": {"sellers": 1, "riders": 0},
    "active_orders": 0
  }
}
```

**Verify Seller**:
```powershell
$body = @{} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:5000/api/admin/sellers/1/verify" `
    -Method PUT -Headers $headers -Body $body
```

### Expected Results:
✅ Seller verification status updated to verified=1
✅ Seller can now receive orders

---

## WORKFLOW TEST 4: CUSTOMER SHOPPING

### Step 4.1: Browse Products
1. Go to `http://localhost:5000/shop.html` (or index.html and navigate to shop)
2. See all products from all sellers
3. You should see "Homemade Burger" and "Premium Coffee"

### Expected Results:
✅ Products display with seller name "Juan's Burgers"
✅ Pricing and stock info visible
✅ Star rating visible (for now, placeholder)

### Step 4.2: Search Products
1. In search bar, type "burger"
2. See filtered results

### Expected Results:
✅ Search filters products by title/description
✅ Only "Homemade Burger" shows

### Step 4.3: Add to Wishlist
1. Click heart icon on burger product
2. Heart should fill in red
3. Go to wishlist.html

### Expected Results:
✅ Product saved to localStorage wishlist
✅ Wishlist page shows the burger
✅ Item count updates

### Step 4.4: Add to Cart
1. On shop.html, click "Add to Cart" button on burger
2. Set quantity to `2`
3. Click "Add"

### Expected Results:
✅ Item added to localStorage cart
✅ Cart count badge updates
✅ Cart dropdown shows item

### Step 4.5: View Cart & Checkout
1. Click cart icon → "View Cart"
2. Or go to cart.html directly
3. See burger: qty=2, price=₱199 each = ₱398 subtotal

### Expected Results:
✅ Cart shows correct items and prices
✅ Subtotal calculated correctly

### Step 4.6: Complete Checkout
1. In cart, fill in:
   - Delivery Address: `123 Main St, Manila`
   - Phone: `09171234567`
   - Payment: `COD` (Cash on Delivery)
2. Click "Place Order"

### Expected Results:
✅ Order created in orders table
✅ Order_items table has 2 items (qty=2 of burger, qty=1 of coffee)
✅ Order status = 'placed'
✅ Customer receives confirmation modal with order_id

---

## WORKFLOW TEST 5: SELLER RECEIVES & PROCESSES ORDER

### Step 5.1: Seller Views Pending Orders
1. Login as seller (seller1@test.com)
2. Go to seller_dashboard.html
3. Click "Orders" tab or section

### Expected Results:
✅ GET /api/sellers/orders returns the order
✅ Shows customer name, phone, address, items, total

### Step 5.2: Seller Confirms Order
1. Click "Confirm" button on the order
2. Status changes to "processing"

### Expected Results:
✅ POST /api/sellers/orders/<id>/confirm updates status to 'processing'
✅ Order moves from "pending" to "processing" section

### Step 5.3: Seller Marks Ready
1. Click "Mark Ready" button
2. Status changes to "ready"

### Expected Results:
✅ POST /api/sellers/orders/<id>/ready updates status to 'ready'
✅ Order now available for rider pickup

---

## WORKFLOW TEST 6: RIDER REGISTRATION & DELIVERY

### Step 6.1: Register as Rider
1. Go to loginregister.html
2. Click "Rider" tab
3. Fill in:
   - Email: `rider1@test.com`
   - Password: `Test123!`
   - Vehicle Type: `Motorcycle`
   - Driver License: `ABC123456`
   - Plate Number: `ABC-1234`
4. Register and verify OTP

### Expected Results:
✅ Rider record created with verified=0
✅ Admin must verify before taking deliveries

### Step 6.2: Admin Verifies Rider
```powershell
# Using admin token
$body = @{} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:5000/api/admin/riders/1/verify" `
    -Method PUT -Headers $headers -Body $body
```

### Expected Results:
✅ Rider verification status = verified=1

### Step 6.3: Rider Views Available Orders
1. Login as rider1@test.com
2. Go to rider_dashboard.html

### Expected Results:
✅ GET /api/riders/available-orders shows the order ready for delivery
✅ Displays customer name, address, delivery fee, items

### Step 6.4: Rider Accepts Order
1. Click "Accept" button on the order
2. Order assigned to rider

### Expected Results:
✅ POST /api/riders/accept-order assigns rider_id to order
✅ Order status changes to 'dispatched'
✅ Customer sees rider info on order tracking page

### Step 6.5: Rider Updates Delivery Status
1. Click "Pickup from Seller" button
2. Status changes to "in-transit"

**Via API**:
```powershell
$body = @{
    'status' = 'in-transit'
    'notes' = 'Picked up, heading to customer'
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/api/orders/1/delivery-update" `
    -Method PUT -Headers $headers -Body $body
```

### Expected Results:
✅ Order status = 'in-transit'
✅ Customer sees "Out for Delivery" status

### Step 6.6: Rider Completes Delivery
1. Click "Deliver" button
2. Upload proof photo (or skip)
3. Status changes to "delivered"

**Via API**:
```powershell
$body = @{
    'status' = 'delivered'
    'notes' = 'Delivered to customer'
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/api/orders/1/delivery-update" `
    -Method PUT -Headers $headers -Body $body
```

### Expected Results:
✅ Order status = 'delivered'
✅ delivered_at timestamp recorded
✅ Rider earnings updated (+₱50 delivery fee)
✅ Customer can now rate the product

---

## WORKFLOW TEST 7: CUSTOMER REVIEWS & RATING

### Step 7.1: View Order Status (As Customer)
1. Login as customer1@test.com
2. Go to account.html
3. Click "My Orders" section

### Expected Results:
✅ GET /api/users/<id>/orders shows order status = 'delivered'
✅ Timeline shows: placed → processing → dispatched → delivered

### Step 7.2: Rate Product
1. Click "Rate" button on the burger item
2. Give 5-star rating
3. Title: `Excellent burger!`
4. Comment: `Fresh ingredients, highly recommend`
5. Submit

### Expected Results:
✅ POST /api/reviews creates review
✅ Review appears on product page
✅ Seller's average rating updates

---

## WORKFLOW TEST 8: VIEW ANALYTICS

### Seller Analytics
1. Login as seller1
2. Click "Dashboard" in seller_dashboard
3. See metrics:
   - Total Orders: 1
   - Total Revenue: ₱398 (from burger order)
   - Pending Orders: 0
   - Avg Rating: 5.0

### Rider Analytics
1. Login as rider1
2. Click "Earnings" section
3. See:
   - Total Earnings: ₱50 (delivery fee)
   - Completed Deliveries: 1
   - Rating: 4.8 (placeholder)

### Admin Analytics
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/api/admin/dashboard" -Headers $headers
```

### Expected Results:
✅ total_users = 3
✅ total_orders = 1
✅ total_revenue = 448 (including delivery fee)
✅ pending_verifications = 0

---

## COMPLETE FLOW VALIDATION CHECKLIST

- [ ] Customer registration & login
- [ ] Seller registration & product listing
- [ ] Admin verification of seller
- [ ] Customer browsing & searching products
- [ ] Add to wishlist & cart
- [ ] Complete checkout
- [ ] Seller receives order notification
- [ ] Seller confirms & marks ready
- [ ] Rider registration & verification
- [ ] Rider accepts delivery
- [ ] Rider updates status to in-transit
- [ ] Rider marks delivered
- [ ] Customer views order tracking
- [ ] Customer rates product
- [ ] All analytics updated correctly

---

## TESTING UTILITIES

### Reset Database
```powershell
# Delete and recreate qwerty.db
Remove-Item "c:\Users\USER\Downloads\qwerty\qwerty.db" -Force
# On next server start, schema.sql will be imported
python run_server.py
```

### View Database (SQLite)
```powershell
sqlite3 c:\Users\USER\Downloads\qwerty\qwerty.db
# Then query:
SELECT * FROM users;
SELECT * FROM products;
SELECT * FROM orders;
SELECT * FROM order_items;
```

### Check API Response (PowerShell)
```powershell
$headers = @{
    'Authorization' = 'Bearer <token>'
    'Content-Type' = 'application/json'
}
$response = Invoke-WebRequest -Uri "http://localhost:5000/api/products" -Headers $headers
$response.Content | ConvertFrom-Json | ConvertTo-Json
```

### Monitor Server Logs
Keep server terminal window open to see:
- API call logs
- OTP codes
- Database queries
- Error messages

---

## Common Issues & Solutions

### Issue: 404 on templates
**Solution**: Ensure server correctly detects template folder:
```
✅ Should see: "TEMPLATES_DIR = /path/to/qwerty/templates"
```

### Issue: "Unauthorized" error
**Solution**: Check that token is in localStorage:
```javascript
console.log(localStorage.getItem('hub_access_token'));
```

### Issue: OTP not sending
**Solution**: Check email_service.py is configured:
- Check console for OTP code
- Use that code in UI
- Or configure SMTP in .env

### Issue: Database errors
**Solution**: Check schema.sql tables exist:
```sql
.tables
```

### Issue: CORS errors
**Solution**: Server has CORS enabled. Check browser console for:
- Network tab shows 200 responses
- Headers include `Access-Control-Allow-Origin`

---

## Next Steps After Testing

1. **Enhance UI**:
   - Add real product images
   - Implement map view for rider tracking
   - Add order timeline visualizations

2. **Add Notifications**:
   - Email notifications on order status changes
   - SMS for delivery updates
   - In-app notifications

3. **Payment Integration**:
   - Add Stripe/GCash payment gateway
   - Remove COD-only limitation

4. **Search & Filtering**:
   - Full-text search on products
   - Advanced filters (rating, delivery time, etc.)

5. **Performance**:
   - Add database indexes
   - Cache frequently accessed data
   - Implement pagination

6. **Security**:
   - Input validation on all endpoints
   - Rate limiting
   - SQL injection prevention (already parameterized)

