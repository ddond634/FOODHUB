# 🚀 QUICK START GUIDE - Testing the Complete System

## START HERE ⬇️

### 1️⃣ Launch Server (30 seconds)
```powershell
cd c:\Users\USER\Downloads\qwerty\py files
python run_server.py
```

✅ Should see: `Running on http://127.0.0.1:5000`

---

### 2️⃣ Open Browser (10 seconds)
```
http://localhost:5000/index.html
```

---

### 3️⃣ Test Customer Journey (5 minutes)

**Register as Customer**:
- Go to: `/loginregister.html`
- Click "Customer" tab
- Fill form: juan@test.com / Test123! / Juan Dela Cruz
- Get OTP from server console (usually 123456)
- Verify OTP
- ✅ Redirected to account.html

**Browse Products**:
- Click "Shop" in navbar
- You'll see products (empty if first time - that's okay)

**Search & Filter**:
- Type in search bar
- Use category filter
- Works with empty database

---

### 4️⃣ Test Seller Journey (5 minutes)

**Register as Seller**:
- New browser tab → `/loginregister.html`
- Click "Seller" tab
- Fill form: seller@test.com / Test123! / Juan Santos / Juan's Burgers
- Verify OTP (same code)
- ✅ Redirected to seller_dashboard.html

**Add Products**:
- Click "Inventory" in sidebar
- Click "Add Product" button
- Fill: Burger / 199 / 50 stock / Fast Food
- Click "Save Product"
- ✅ Product appears in table

**Edit Product**:
- Click "Edit" on product
- Change price to 199.50
- Save
- ✅ Updated in list

**Delete Product**:
- Click "Delete"
- Confirm
- ✅ Removed from list

**View Dashboard**:
- Click "Dashboard" link
- See sales metrics (will show 0 until customer buys)

---

### 5️⃣ Test Rider Journey (5 minutes)

**Register as Rider**:
- New browser tab → `/loginregister.html`
- Click "Rider" tab
- Fill: rider@test.com / Test123! / Santos / ABC123456 / ABC-1234
- Verify OTP
- ✅ Redirected to rider_dashboard.html

---

### 6️⃣ Test Admin Approval (2 minutes)

**Get Admin Token** (Terminal):
```powershell
# Note: You need admin account in database
# Check server console for how to add admin
# For now, test endpoints with customer token
```

**Verify Seller via Postman**:
```
PUT http://localhost:5000/api/admin/sellers/1/verify
Header: Authorization: Bearer <admin_token>
Body: {}
```

---

### 7️⃣ Complete Purchase Flow (10 minutes)

**As Customer**:
1. Go to `/shop.html`
2. Add seller's burger to cart (mock in localStorage)
3. Go to `/cart.html`
4. Fill: "123 Main St, Manila" / "09171234567"
5. Click "Place Order"
6. ✅ See order confirmation with ID

**Check Database**:
```powershell
sqlite3 qwerty.db "SELECT * FROM orders;"
```

---

### 8️⃣ Full Integration Test (15 minutes)

Follow **TESTING_GUIDE.md** exactly:
- ✅ Customer registers
- ✅ Seller registers & adds product
- ✅ Admin verifies seller
- ✅ Customer browses & buys
- ✅ Seller receives order
- ✅ Rider accepts delivery
- ✅ Rider marks delivered
- ✅ Customer rates product
- ✅ Check database records

---

## 🔥 Key Endpoints to Test

### Authentication
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/send-otp
POST /api/auth/verify-otp
```

### Products (Customer)
```
GET /api/products
GET /api/products/<id>
GET /api/products/search?q=burger
GET /api/products/filter?category=Fast%20Food
```

### Cart (Client-side)
```
localStorage.setItem('hub_cart', JSON.stringify([...]))
localStorage.getItem('hub_cart')
```

### Orders
```
POST /api/orders
GET /api/orders/<id>/track
GET /api/users/<id>/orders
```

### Seller
```
POST /api/sellers/products
GET /api/sellers/products
PUT /api/sellers/products/<id>
DELETE /api/sellers/products/<id>
GET /api/sellers/orders
POST /api/sellers/orders/<id>/confirm
GET /api/sellers/dashboard
```

### Rider
```
GET /api/riders/available-orders
POST /api/riders/accept-order
PUT /api/orders/<id>/delivery-update
GET /api/riders/earnings
```

### Admin
```
GET /api/admin/dashboard
GET /api/admin/sellers/pending
PUT /api/admin/sellers/<id>/verify
GET /api/admin/riders/pending
PUT /api/admin/riders/<id>/verify
```

---

## 📱 Test Checklist

### Customer ✅
- [ ] Register as customer
- [ ] Login works
- [ ] Browse products
- [ ] Search works
- [ ] Add to wishlist works
- [ ] Add to cart works
- [ ] Checkout submits order
- [ ] Can view profile

### Seller ✅
- [ ] Register as seller
- [ ] Login works
- [ ] Add product works
- [ ] Edit product works
- [ ] Delete product works
- [ ] View dashboard
- [ ] Can see incoming orders (after customer buys)

### Rider ✅
- [ ] Register as rider
- [ ] Login works
- [ ] View available orders
- [ ] Accept order works

### Admin ✅
- [ ] Can verify seller
- [ ] Can verify rider
- [ ] Dashboard shows correct numbers

---

## 🆘 Troubleshooting

### "404 Templates Not Found"
✅ **Fix**: Server auto-detects paths. Check console shows template folder.

### "Token Expired"
✅ **Fix**: Clear localStorage: `localStorage.clear()` and re-login.

### "OTP Not Working"
✅ **Fix**: Check server console for generated OTP code. Use that number.

### "Database Error"
✅ **Fix**: Delete qwerty.db and restart server (recreates schema).

### "Products Not Showing"
✅ **Fix**: Need seller to add products first. Test seller flow first.

---

## 🎯 Success Criteria

**You'll know it's working when:**

1. ✅ Can register all 4 user types
2. ✅ Each role can login
3. ✅ Seller can add/edit/delete products
4. ✅ Customer can search and filter
5. ✅ Customer can checkout
6. ✅ Seller sees incoming order
7. ✅ Rider can view available orders
8. ✅ Database has: users, products, orders, order_items records
9. ✅ No errors in server console
10. ✅ All pages load correctly

---

## 📊 Expected Database State After Testing

```sql
-- After full test cycle, you should see:
sqlite3 qwerty.db

SELECT COUNT(*) FROM users;          -- Should be 4+ (customer, seller, rider, admin)
SELECT COUNT(*) FROM products;       -- Should be 1+ (seller added)
SELECT COUNT(*) FROM orders;         -- Should be 1+ (customer bought)
SELECT COUNT(*) FROM order_items;    -- Should be 1+ (items in order)
SELECT COUNT(*) FROM reviews;        -- Should be 0-1 (if rated)

-- Check specific order:
SELECT * FROM orders ORDER BY id DESC LIMIT 1;
SELECT * FROM order_items WHERE order_id = <order_id>;
```

---

## 💡 Pro Tips

### View Server Logs
Keep terminal running. Watch for:
- API calls logged
- OTP codes generated
- Database queries
- Errors with tracebacks

### Test With Postman
```
Import these endpoints:
- POST /api/auth/register
- GET /api/products
- POST /api/orders
- etc.
```

### Check Network Tab
Open DevTools (F12):
- Network tab → see all API calls
- Console → check for JavaScript errors
- Application → view localStorage data

### Quick Database Dump
```powershell
sqlite3 qwerty.db ".dump" > backup.sql
sqlite3 qwerty.db ".dump users"  # Just users table
```

---

## ⏱️ Estimated Time

| Task | Time |
|------|------|
| Start server | 30 sec |
| Test 1 role (register, add item) | 3 min |
| Test 4 roles complete flow | 15 min |
| Full TESTING_GUIDE.md validation | 45 min |
| **Total** | **~1 hour** |

---

## 🎓 Learning Resources

**Read These in Order**:
1. **This file** - Quick overview
2. **TESTING_GUIDE.md** - Detailed steps
3. **COMPLETE_WORKFLOWS.md** - Flow diagrams
4. **API_DOCUMENTATION.md** - All endpoints
5. **IMPLEMENTATION_SUMMARY.md** - Technical details

---

## ✨ You're All Set!

Everything is implemented and tested for syntax errors.

**Next Step**: Follow **TESTING_GUIDE.md** to validate the complete end-to-end workflow.

Server is ready. Database schema is ready. API endpoints are ready.

**Let's test this! 🚀**

