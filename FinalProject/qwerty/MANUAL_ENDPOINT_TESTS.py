"""
Manual MySQL endpoint verification commands.
Copy-paste these curl commands in PowerShell to test endpoints.
"""

# Set environment and start server
"""
$env:DB_ENGINE="mysql"
$env:MIGRATE="1"
python c:\Users\USER\Downloads\FinalProject\qwerty\run.py
"""

# In another PowerShell terminal:

# 1. Health check
"""
curl http://127.0.0.1:5000/api/health
"""

# 2. Register seller
"""
curl -X POST http://127.0.0.1:5000/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"seller@test.com\",\"password\":\"Pass123!\",\"first_name\":\"Test\",\"last_name\":\"Seller\",\"role\":\"seller\"}'
"""

# 3. Login
"""
curl -X POST http://127.0.0.1:5000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"seller@test.com\",\"password\":\"Pass123!\"}'
"""
# Copy the access_token from response

# 4. Test /api/me (replace <TOKEN>)
"""
curl http://127.0.0.1:5000/api/me `
  -H "Authorization: Bearer <TOKEN>"
"""

# 5. Create store (requires seller to be verified/active first)
"""
curl -X POST http://127.0.0.1:5000/api/stores `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{\"name\":\"My Test Store\",\"category\":\"General\"}'
"""

# 6. List my stores
"""
curl http://127.0.0.1:5000/api/stores/mine `
  -H "Authorization: Bearer <TOKEN>"
"""

# 7. Shipping settings
"""
curl http://127.0.0.1:5000/api/seller/settings/shipping `
  -H "Authorization: Bearer <TOKEN>"
"""

# Admin endpoints (login as admin first with role='admin')
# 8. Pending stores
"""
curl http://127.0.0.1:5000/api/stores/pending `
  -H "Authorization: Bearer <ADMIN_TOKEN>"
"""

# 9. Approve store (replace <STORE_ID>)
"""
curl -X POST http://127.0.0.1:5000/api/stores/<STORE_ID>/status `
  -H "Authorization: Bearer <ADMIN_TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{\"action\":\"approve\"}'
"""
