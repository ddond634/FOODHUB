# Quick Integration Guide

## How to Integrate All New Features into server.py

### Step 1: Add Import Statements (Top of server.py)

Add these imports after existing imports:

```python
from email_service import send_otp_email, verify_otp, store_otp, send_order_confirmation_email
from validators import (
    validate_email, validate_password, validate_phone, validate_name,
    validate_business_name, validate_product_title, validate_price,
    validate_quantity, validate_address, validate_role, validate_order_status, validate_otp
)
from api_utils import (
    json_response, success_response, error_response, validate_json_request,
    paginate, format_row, format_rows, paginated_response
)
```

### Step 2: Add OTP Endpoint (Before Product Endpoints)

```python
@app.route('/api/auth/send-otp', methods=['POST'])
def api_send_otp():
    """Send OTP to email for verification."""
    try:
        body = request.json or {}
        email = body.get('email', '').strip()
        user_type = body.get('type', 'customer')  # customer, seller, rider
        
        # Validate email
        is_valid, error_msg = validate_email(email)
        if not is_valid:
            return error_response(error_msg, 400)
        
        # Generate and send OTP
        otp_code = email_service.generate_otp()
        email_service.store_otp(email, otp_code)
        
        if email_service.send_otp_email(email, otp_code, user_type):
            return success_response(message=f'OTP sent to {email}')
        else:
            return error_response('Failed to send OTP. Please try again.', 500)
    
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        return error_response('Server error', 500)

@app.route('/api/auth/verify-otp', methods=['POST'])
def api_verify_otp():
    """Verify OTP code."""
    try:
        body = request.json or {}
        email = body.get('email', '').strip()
        otp_code = body.get('otp', '').strip()
        
        # Validate OTP format
        is_valid, error_msg = validate_otp(otp_code)
        if not is_valid:
            return error_response(error_msg, 400)
        
        # Verify OTP
        success, message = email_service.verify_otp(email, otp_code)
        if success:
            return success_response(message='OTP verified successfully')
        else:
            return error_response(message, 400)
    
    except Exception as e:
        print(f"Error verifying OTP: {str(e)}")
        return error_response('Server error', 500)
```

### Step 3: Update Registration Endpoint

Modify the existing `/api/auth/register` endpoint to include OTP logic:

```python
@app.route('/api/auth/register', methods=['POST'])
def api_register():
    body = request.json or {}
    email = body.get('email')
    password = body.get('password')
    role = body.get('role','customer')
    first = body.get('first_name','')
    last = body.get('last_name','')
    
    # Validate inputs
    email_valid, email_error = validate_email(email)
    if not email_valid:
        return error_response(email_error, 400)
    
    password_valid, password_error = validate_password(password)
    if not password_valid:
        return error_response(password_error, 400)
    
    role_valid, role_error = validate_role(role)
    if not role_valid:
        return error_response(role_error, 400)
    
    # [Keep existing code for user creation]
    # ...
    
    # After user creation, send OTP email
    otp_code = email_service.generate_otp()
    email_service.store_otp(email, otp_code)
    email_service.send_otp_email(email, otp_code, role)
    
    return success_response({
        'user_id': user_id,
        'email': email,
        'token': token,
        'refresh_token': refresh_token,
        'message': f'OTP sent to {email}'
    }, status_code=201)
```

### Step 4: Add New User Endpoints (After Existing User Routes)

Copy the content from `additional_endpoints.py` → User Profile section

### Step 5: Add Search & Filter Endpoints

Copy from `additional_endpoints.py` → Search & Filter section

### Step 6: Add Wishlist Endpoints

Copy from `additional_endpoints.py` → Wishlist section

### Step 7: Add Order Tracking

Copy from `additional_endpoints.py` → Order History & Tracking section

### Step 8: Update .env File

Copy `qwerty/.env.example` to `qwerty/.env` and configure:

```bash
# Database
DB_ENGINE=sqlite
# DB_HOST=127.0.0.1
# DB_USER=root
# DB_PASS=
# DB_NAME=qwerty

# JWT
JWT_SECRET=dev-jwt-secret-change-in-prod
JWT_EXPIRY_HOURS=24
REFRESH_TOKEN_EXP_DAYS=30

# Email (optional for development)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=
EMAIL_PASSWORD=
SENDER_NAME=Hub E-Commerce
```

### Step 9: Test Integration

```powershell
# Restart server
python py\ files\run_server.py

# Test OTP endpoint
curl -X POST http://127.0.0.1:5000/api/auth/send-otp `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","type":"customer"}'

# Test registration
curl -X POST http://127.0.0.1:5000/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{
    "email":"user@test.com",
    "password":"securepass123",
    "role":"customer",
    "first_name":"John",
    "last_name":"Doe"
  }'
```

---

## Frontend Integration (loginregister.html)

### Update handleCustomerRegistration() Function

Replace mock fetch with real API:

```javascript
function handleCustomerRegistration(ev){
  ev.preventDefault();
  const firstName = document.getElementById('custFirstName').value.trim();
  const lastName = document.getElementById('custLastName').value.trim();
  const email = document.getElementById('custEmail').value.trim();
  const password = document.getElementById('custPassword').value;
  const confirm = document.getElementById('custConfirmPassword').value;
  
  // Validation...
  
  if(ok){
    // Register user
    const payload = {
      email, password, role: 'customer',
      first_name: firstName,
      last_name: lastName
    };
    
    fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(resp => {
      if(resp && resp.success){
        // Save tokens
        if(resp.data.token) 
          localStorage.setItem('hub_access_token', resp.data.token);
        if(resp.data.refresh_token)
          localStorage.setItem('hub_refresh_token', resp.data.refresh_token);
        
        // Store registration data
        pendingRegistrations.customer = {firstName, lastName, email};
        
        // Show OTP form
        showSuccess('customerSuccess', resp.data.message || 'OTP sent!');
        switchCustomerStep(4);
      } else {
        showError('custEmailError', resp.error || 'Registration failed');
      }
    })
    .catch(err => {
      console.error(err);
      showError('custEmailError', 'Server error');
    });
  }
}
```

### Update handleCustomerOTP() Function

```javascript
function handleCustomerOTP(ev){
  ev.preventDefault();
  const code = document.getElementById('custOTP').value.trim();
  const email = pendingRegistrations.customer?.email;
  
  if(code.length < 4){
    showError('custOTPError', 'Enter the verification code');
    return;
  }
  
  // Verify OTP
  fetch('/api/auth/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp: code })
  })
  .then(r => r.json())
  .then(resp => {
    if(resp && resp.success){
      showSuccess('customerSuccess', 'Account verified! Redirecting...');
      pendingRegistrations.customer = null;
      document.getElementById('customerForm').reset();
      document.getElementById('customerFormOTP').reset?.();
      setTimeout(() => switchForm('login'), 2000);
    } else {
      showError('custOTPError', resp.error || 'OTP verification failed');
    }
  })
  .catch(err => {
    console.error(err);
    showError('custOTPError', 'Server error');
  });
}
```

### Update sendOTP() Function

```javascript
function sendOTP(email, type){
  fetch('/api/auth/send-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, type })
  })
  .then(r => r.json())
  .then(resp => {
    if(resp && resp.success){
      showSuccess(type + 'Success', resp.message || `OTP sent to ${email}`);
    } else {
      showError(type + 'OTPError', resp.error || 'Failed to send OTP');
    }
  })
  .catch(err => {
    console.error(err);
    showError(type + 'OTPError', 'Server error');
  });
}
```

### Update handleLogin() Function

```javascript
function handleLogin(ev){
  ev.preventDefault();
  clearError('loginEmailError');
  clearError('loginPasswordError');
  
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  
  if(!validateEmail(email)){
    showError('loginEmailError', 'Invalid email address');
    return;
  }
  if(!password){
    showError('loginPasswordError', 'Password is required');
    return;
  }
  
  // Call real login API
  fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })
  .then(r => r.json())
  .then(resp => {
    if(resp && resp.success){
      // Save tokens
      localStorage.setItem('hub_access_token', resp.data.token);
      localStorage.setItem('hub_refresh_token', resp.data.refresh_token);
      localStorage.setItem('hub_user_id', resp.data.user_id);
      localStorage.setItem('hub_user_role', resp.data.role);
      
      showSuccess('loginSuccess', `Welcome back, ${email}!`);
      document.getElementById('loginForm').reset();
      
      // Redirect based on role
      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
    } else {
      showError('loginEmailError', resp.error || 'Login failed');
    }
  })
  .catch(err => {
    console.error(err);
    showError('loginEmailError', 'Server error');
  });
}
```

---

## Database Schema Addition

Add these tables to `qwerty/db/schema.sql`:

```sql
-- OTP codes table (optional - can use in-memory store)
CREATE TABLE IF NOT EXISTS otp_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    created_at TEXT
);

-- Wishlist table
CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT,
    UNIQUE(user_id, product_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    title TEXT,
    comment TEXT,
    created_at TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT,
    title TEXT,
    message TEXT,
    read INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## Testing Checklist

- [ ] Email service sends OTP in development mode
- [ ] OTP expires after 10 minutes
- [ ] OTP fails after 5 wrong attempts
- [ ] Registration validates email and password
- [ ] User can register and receive OTP
- [ ] User can verify OTP and login
- [ ] Token is saved in localStorage
- [ ] Refresh token endpoint works
- [ ] Search/filter endpoints return results
- [ ] Wishlist endpoints work
- [ ] Order tracking returns correct data
- [ ] User profile endpoints work

---

## Troubleshooting Integration

### Issue: "Module not found"
```python
# Make sure files are in py files/ directory
# Python imports are case-sensitive on Linux/macOS
```

### Issue: "Email service not working"
```python
# Check .env configuration
# Leave EMAIL_ADDRESS empty for dev mode
# Check console for OTP code (dev mode)
```

### Issue: "Frontend not getting responses"
```javascript
// Check browser console for CORS errors
// Verify API paths are correct
// Use browser DevTools Network tab to debug
```

---

## Next Steps

1. **Integration**: Copy all code into server.py
2. **Testing**: Run tests with pytest
3. **Frontend**: Update loginregister.html with new API calls
4. **Database**: Run schema.sql or schema_mysql.sql
5. **Deployment**: Configure .env and deploy

---

## Files Modified/Created

**New Files**:
- ✅ `py files/email_service.py`
- ✅ `py files/validators.py`
- ✅ `py files/api_utils.py`
- ✅ `py files/additional_endpoints.py`
- ✅ `.env.example`

**Modified Files**:
- ⏳ `py files/server.py` (add imports and endpoints)
- ⏳ `qwerty/templates/loginregister.html` (update frontend)
- ⏳ `qwerty/db/schema.sql` (add new tables)

**Documentation**:
- ✅ `API_DOCUMENTATION.md`
- ✅ `SETUP_GUIDE.md`
- ✅ `MISSING_FEATURES.md`
- ✅ `IMPLEMENTATION_SUMMARY.md`
- ✅ `QUICK_INTEGRATION_GUIDE.md` (this file)

