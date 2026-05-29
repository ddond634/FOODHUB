# Hub E-Commerce API Documentation

## Base URL
```
http://127.0.0.1:5000/api
```

## Authentication
Most endpoints require JWT token in Authorization header:
```
Authorization: Bearer <token>
```

---

## 1. AUTHENTICATION ENDPOINTS

### 1.1 Register User
**POST** `/auth/register`

Request:
```json
{
  "email": "user@example.com",
  "password": "securepass123",
  "role": "customer|seller|rider",
  "first_name": "John",
  "last_name": "Doe"
}
```

Response (201):
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "email": "user@example.com",
    "token": "eyJ...",
    "refresh_token": "ref..."
  }
}
```

### 1.2 Login
**POST** `/auth/login`

Request:
```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

Response (200):
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "email": "user@example.com",
    "role": "customer",
    "token": "eyJ...",
    "refresh_token": "ref..."
  }
}
```

### 1.3 Refresh Token
**POST** `/auth/refresh`

Request:
```json
{
  "refresh_token": "ref..."
}
```

Response (200):
```json
{
  "success": true,
  "data": {
    "token": "eyJ..."
  }
}
```

### 1.4 Logout
**POST** `/auth/logout`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### 1.5 Change Password
**POST** `/auth/change-password`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "current_password": "oldpass123",
  "new_password": "newpass123"
}
```

Response (200):
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

---

## 2. PRODUCT ENDPOINTS

### 2.1 List Products
**GET** `/products?page=1&per_page=20`

Response (200):
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Fresh Mango",
      "description": "Organic mangoes",
      "price": 150.00,
      "stock": 50,
      "seller_id": 2,
      "category": "Fruits",
      "img_url": "...",
      "created_at": "2025-11-17T12:00:00"
    }
  ]
}
```

### 2.2 Get Product Details
**GET** `/products/<product_id>`

Response (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "Fresh Mango",
    "description": "Organic mangoes",
    "price": 150.00,
    "stock": 50,
    "seller_id": 2,
    "category": "Fruits",
    "img_url": "...",
    "rating": 4.5,
    "review_count": 12,
    "created_at": "2025-11-17T12:00:00"
  }
}
```

### 2.3 Search Products
**GET** `/products/search?q=mango`

Response (200):
```json
{
  "success": true,
  "data": [...]
}
```

### 2.4 Filter Products
**GET** `/products/filter?category=Fruits&price_min=100&price_max=500&seller_id=2`

Response (200):
```json
{
  "success": true,
  "data": [...]
}
```

---

## 3. ORDER ENDPOINTS

### 3.1 Create Order
**POST** `/orders`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "customer_name": "John Doe",
  "customer_phone": "09123456789",
  "customer_address": "123 Main St, Manila",
  "payment": "cod",
  "items": [
    {
      "product_id": 1,
      "quantity": 2,
      "price": 150.00
    }
  ]
}
```

Response (201):
```json
{
  "success": true,
  "data": {
    "order_id": 1,
    "subtotal": 300.00,
    "delivery_fee": 50.00,
    "total": 350.00,
    "status": "placed",
    "created_at": "2025-11-17T12:00:00"
  }
}
```

### 3.2 Get Order
**GET** `/orders/<order_id>`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "customer_id": 5,
    "customer_name": "John Doe",
    "customer_phone": "09123456789",
    "customer_address": "123 Main St, Manila",
    "subtotal": 300.00,
    "delivery_fee": 50.00,
    "total": 350.00,
    "payment": "cod",
    "status": "placed",
    "items": [...],
    "created_at": "2025-11-17T12:00:00"
  }
}
```

### 3.3 Track Order
**GET** `/orders/<order_id>/track`

Response (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "dispatched",
    "rider_id": 3,
    "rider_name": "Maria Santos",
    "items": [...],
    "created_at": "2025-11-17T12:00:00"
  }
}
```

### 3.4 Update Order Status (Admin/Rider)
**POST** `/orders/<order_id>/status`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "status": "processing|dispatched|delivered|cancelled"
}
```

Response (200):
```json
{
  "success": true,
  "message": "Order status updated"
}
```

### 3.5 Get User Orders
**GET** `/users/<user_id>/orders`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": [...]
}
```

---

## 4. USER ENDPOINTS

### 4.1 Get User Profile
**GET** `/users/<user_id>`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "created_at": "2025-11-17T12:00:00"
  }
}
```

### 4.2 Update User Profile
**PUT** `/users/<user_id>`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "first_name": "John",
  "last_name": "Doe"
}
```

Response (200):
```json
{
  "success": true,
  "message": "Profile updated successfully"
}
```

### 4.3 List Users (Admin Only)
**GET** `/users?role=seller&page=1&per_page=20`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": [...]
}
```

---

## 5. SELLER ENDPOINTS

### 5.1 Get Seller Profile
**GET** `/sellers/<seller_id>`

Response (200):
```json
{
  "success": true,
  "data": {
    "user_id": 2,
    "business_name": "John's Fresh Market",
    "category": "Fruits & Vegetables",
    "region": "NCR",
    "province": "Metro Manila",
    "city": "Manila",
    "verified": 1,
    "created_at": "2025-11-17T12:00:00"
  }
}
```

### 5.2 List Products by Seller
**GET** `/seller/products?seller_id=2`

Response (200):
```json
{
  "success": true,
  "data": [...]
}
```

### 5.3 Create Product (Seller Only)
**POST** `/seller/products`

Headers: `Authorization: Bearer <token>`

Request:
```json
{
  "title": "Fresh Mango",
  "description": "Organic mangoes",
  "price": 150.00,
  "stock": 50,
  "category": "Fruits",
  "img_url": "..."
}
```

Response (201):
```json
{
  "success": true,
  "data": {
    "product_id": 1
  }
}
```

### 5.4 Get Seller Dashboard
**GET** `/seller/dashboard`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "total_sales": 15000.00,
    "completed_orders": 25,
    "total_products": 10,
    "pending_orders": 3,
    "earnings": {
      "gross_revenue": 15000.00,
      "commission": 1800.00,
      "net_earnings": 13200.00,
      "pending_payout": 5000.00
    }
  }
}
```

---

## 6. RIDER ENDPOINTS

### 6.1 Get Rider Profile
**GET** `/riders/<rider_id>`

Response (200):
```json
{
  "success": true,
  "data": {
    "user_id": 3,
    "vehicle_type": "motorcycle",
    "driver_license": "DL123456",
    "plate_number": "ABC123",
    "verified": 1
  }
}
```

### 6.2 Get Rider Dashboard
**GET** `/rider/dashboard`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "total_deliveries": 150,
    "completed_today": 8,
    "pending_deliveries": 2,
    "total_earnings": 18500.00,
    "pending_payout": 2000.00,
    "rating": 4.8
  }
}
```

### 6.3 Get Rider Earnings
**GET** `/rider/earnings?month=11&year=2025`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": {
    "period": "November 2025",
    "total_earnings": 8500.00,
    "total_deliveries": 85,
    "average_per_delivery": 100.00,
    "breakdown": [
      {
        "date": "2025-11-17",
        "deliveries": 8,
        "earnings": 850.00
      }
    ]
  }
}
```

---

## 7. ADMIN ENDPOINTS

### 7.1 Get Admin Dashboard
**GET** `/admin/dashboard`

Headers: `Authorization: Bearer <token>` (Admin role required)

Response (200):
```json
{
  "success": true,
  "data": {
    "total_users": 250,
    "total_sellers": 35,
    "total_riders": 20,
    "total_orders": 1250,
    "total_revenue": 250000.00,
    "pending_orders": 45,
    "pending_seller_verification": 5
  }
}
```

### 7.2 List All Orders (Admin)
**GET** `/admin/orders?status=placed&page=1&per_page=20`

Headers: `Authorization: Bearer <token>` (Admin role required)

Response (200):
```json
{
  "success": true,
  "data": [...]
}
```

---

## 8. WISHLIST ENDPOINTS

### 8.1 Get Wishlist
**GET** `/wishlist`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "data": [...]
}
```

### 8.2 Add to Wishlist
**POST** `/wishlist/<product_id>`

Headers: `Authorization: Bearer <token>`

Response (201):
```json
{
  "success": true,
  "message": "Product added to wishlist"
}
```

### 8.3 Remove from Wishlist
**DELETE** `/wishlist/<product_id>`

Headers: `Authorization: Bearer <token>`

Response (200):
```json
{
  "success": true,
  "message": "Product removed from wishlist"
}
```

---

## 9. HEALTH CHECK

### 9.1 API Health Status
**GET** `/health`

Response (200):
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2025-11-17T12:00:00"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "error": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "error": "Missing or invalid token"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "error": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Resource not found"
}
```

### 500 Server Error
```json
{
  "success": false,
  "error": "Server error"
}
```

---

## Rate Limiting

API requests are rate limited to 100 requests per minute per IP address.

## Pagination

For list endpoints, use `page` and `per_page` query parameters:
```
GET /products?page=1&per_page=20
```

Default: page=1, per_page=20, max_per_page=100

