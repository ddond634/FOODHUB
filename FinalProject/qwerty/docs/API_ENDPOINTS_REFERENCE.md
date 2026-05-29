# API Endpoint Reference - Complete List

## Authentication Endpoints (5)

### Register User
```
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@test.com",
  "password": "Test123!",
  "role": "customer",  // or "seller", "rider"
  "first_name": "Juan",
  "last_name": "Dela Cruz",
  
  // If role = "seller":
  "business_name": "Juan's Burgers",
  "category": "Fast Food",
  
  // If role = "rider":
  "vehicle_type": "Motorcycle",
  "driver_license": "ABC123456",
  "plate_number": "ABC-1234"
}

Response:
{
  "success": true,
  "data": {
    "user_id": 1,
    "email": "user@test.com",
    "role": "customer"
  }
}
```

### Send OTP
```
POST /api/auth/send-otp
{
  "email": "user@test.com"
}

Response:
{
  "success": true,
  "data": {
    "email": "user@test.com",
    "message": "OTP sent to email"
  }
}
```

### Verify OTP
```
POST /api/auth/verify-otp
{
  "email": "user@test.com",
  "code": "123456"
}

Response:
{
  "success": true,
  "data": {
    "verified": true,
    "message": "Email verified"
  }
}
```

### Login
```
POST /api/auth/login
{
  "email": "user@test.com",
  "password": "Test123!"
}

Response:
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1Q...",
    "refresh_token": "refresh_token_value",
    "user_id": 1,
    "role": "customer"
  }
}
```

### Change Password
```
POST /api/auth/change-password
Authorization: Bearer {token}
{
  "current_password": "Test123!",
  "new_password": "NewTest123!"
}

Response:
{
  "success": true,
  "data": {
    "message": "Password changed"
  }
}
```

---

## User Endpoints (3)

### Get User Profile
```
GET /api/users/{user_id}
Authorization: Bearer {token}

Response:
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@test.com",
    "first_name": "Juan",
    "last_name": "Dela Cruz",
    "role": "customer",
    "created_at": "2025-11-17T10:30:00"
  }
}
```

### Update User Profile
```
PUT /api/users/{user_id}
Authorization: Bearer {token}
{
  "first_name": "Juan",
  "last_name": "Santos",
  "email": "new@test.com"  // optional
}

Response:
{
  "success": true,
  "data": {
    "user_id": 1,
    "message": "Profile updated"
  }
}
```

### Get User Orders
```
GET /api/users/{user_id}/orders
Authorization: Bearer {token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "customer_id": 1,
      "status": "delivered",
      "total": 448,
      "created_at": "2025-11-17T10:30:00",
      "items": [
        {
          "product_id": 1,
          "title": "Burger",
          "quantity": 2,
          "price": 199
        }
      ]
    }
  ]
}
```

---

## Product Endpoints (4)

### List All Products
```
GET /api/products?limit=20&offset=0

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Burger",
      "description": "Fresh beef patty",
      "price": 199,
      "stock": 50,
      "category": "Fast Food",
      "seller_id": 2,
      "created_at": "2025-11-17T10:00:00"
    }
  ]
}
```

### Get Product Details
```
GET /api/products/{product_id}

Response:
{
  "success": true,
  "data": {
    "id": 1,
    "title": "Burger",
    "description": "Fresh beef patty",
    "price": 199,
    "stock": 50,
    "category": "Fast Food",
    "seller_id": 2,
    "seller_name": "Juan's Burgers",
    "reviews": [
      {
        "id": 1,
        "user_id": 1,
        "rating": 5,
        "title": "Excellent!",
        "body": "Fresh and delicious"
      }
    ]
  }
}
```

### Search Products
```
GET /api/products/search?q=burger

Response:
{
  "success": true,
  "data": [
    { "id": 1, "title": "Homemade Burger", ... }
  ]
}
```

### Filter Products
```
GET /api/products/filter?category=Fast%20Food&min_price=100&max_price=300&seller_id=2

Response:
{
  "success": true,
  "data": [...]
}
```

---

## Wishlist Endpoints (3)

### Get Wishlist
```
GET /api/wishlist
Authorization: Bearer {token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "product_id": 1,
      "title": "Burger",
      "price": 199,
      "added_at": "2025-11-17T10:30:00"
    }
  ]
}
```

### Add to Wishlist
```
POST /api/wishlist/{product_id}
Authorization: Bearer {token}

Response:
{
  "success": true,
  "data": {
    "product_id": 1,
    "message": "Added to wishlist"
  }
}
```

### Remove from Wishlist
```
DELETE /api/wishlist/{product_id}
Authorization: Bearer {token}

Response:
{
  "success": true,
  "data": {
    "product_id": 1,
    "message": "Removed from wishlist"
  }
}
```

---

## Order Endpoints (3)

### Create Order
```
POST /api/orders
Authorization: Bearer {token}
{
  "customer_name": "Juan Dela Cruz",
  "customer_phone": "09171234567",
  "customer_address": "123 Main St, Manila",
  "items": [
    {
      "product_id": 1,
      "quantity": 2,
      "price": 199
    }
  ],
  "subtotal": 398,
  "delivery_fee": 50,
  "total": 448,
  "payment": "cod"  // or "card", "gcash"
}

Response:
{
  "success": true,
  "data": {
    "order_id": 1,
    "status": "placed",
    "total": 448,
    "created_at": "2025-11-17T10:30:00"
  }
}
```

### Track Order
```
GET /api/orders/{order_id}/track
Authorization: Bearer {token}

Response:
{
  "success": true,
  "data": {
    "order_id": 1,
    "status": "dispatched",
    "items": [
      { "product_id": 1, "title": "Burger", "quantity": 2 }
    ],
    "total": 448,
    "delivery_address": "123 Main St, Manila",
    "rider": {
      "name": "Santos Delivery",
      "phone": "09189876543",
      "current_location": { "lat": 14.5899, "lng": 120.9822 },
      "estimated_arrival": "11:45 AM"
    },
    "timeline": [
      { "status": "placed", "timestamp": "10:30 AM", "message": "Order placed" },
      { "status": "processing", "timestamp": "10:35 AM", "message": "Seller preparing" },
      { "status": "dispatched", "timestamp": "10:45 AM", "message": "Out for delivery" }
    ]
  }
}
```

### Admin: Get All Orders
```
GET /api/admin/orders
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "customer_id": 1,
      "customer_name": "Juan Dela Cruz",
      "status": "delivered",
      "total": 448,
      "items": [...]
    }
  ]
}
```

---

## Seller Endpoints (8)

### Create Product
```
POST /api/sellers/products
Authorization: Bearer {seller_token}
{
  "title": "Homemade Burger",
  "description": "Fresh beef patty with toppings",
  "price": 199,
  "stock": 50,
  "category": "Fast Food",
  "img_url": "https://..."
}

Response:
{
  "success": true,
  "data": {
    "product_id": 1,
    "title": "Homemade Burger",
    "price": 199
  }
}
```

### List Seller's Products
```
GET /api/sellers/products
Authorization: Bearer {seller_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Burger",
      "price": 199,
      "stock": 50,
      "category": "Fast Food"
    }
  ]
}
```

### Update Product
```
PUT /api/sellers/products/{product_id}
Authorization: Bearer {seller_token}
{
  "price": 199.50,
  "stock": 45,
  "title": "Premium Burger"
}

Response:
{
  "success": true,
  "data": {
    "product_id": 1,
    "message": "Product updated"
  }
}
```

### Delete Product
```
DELETE /api/sellers/products/{product_id}
Authorization: Bearer {seller_token}

Response:
{
  "success": true,
  "data": {
    "product_id": 1,
    "message": "Product deleted"
  }
}
```

### Get Seller's Orders
```
GET /api/sellers/orders
Authorization: Bearer {seller_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "customer_name": "Juan Dela Cruz",
      "customer_phone": "09171234567",
      "customer_address": "123 Main St",
      "status": "placed",
      "items": [
        { "product_id": 1, "title": "Burger", "quantity": 2, "price": 199 }
      ],
      "total": 448,
      "created_at": "2025-11-17T10:30:00"
    }
  ]
}
```

### Confirm Order
```
POST /api/sellers/orders/{order_id}/confirm
Authorization: Bearer {seller_token}
{}

Response:
{
  "success": true,
  "data": {
    "order_id": 1,
    "status": "processing",
    "message": "Order confirmed"
  }
}
```

### Mark Ready for Delivery
```
POST /api/sellers/orders/{order_id}/ready
Authorization: Bearer {seller_token}
{}

Response:
{
  "success": true,
  "data": {
    "order_id": 1,
    "status": "ready",
    "message": "Order marked ready"
  }
}
```

### Seller Dashboard
```
GET /api/sellers/dashboard
Authorization: Bearer {seller_token}

Response:
{
  "success": true,
  "data": {
    "total_orders": 127,
    "total_revenue": 25400,
    "pending_orders": 3,
    "avg_rating": 4.8,
    "verified": true,
    "business_name": "Juan's Burgers",
    "products_count": 12
  }
}
```

### Seller Sales Analytics
```
GET /api/sellers/sales?period=month
Authorization: Bearer {seller_token}

Response:
{
  "success": true,
  "data": [
    {
      "date": "2025-11-17",
      "revenue": 1450,
      "orders": 5
    }
  ]
}
```

---

## Rider Endpoints (5)

### Get Available Orders
```
GET /api/riders/available-orders
Authorization: Bearer {rider_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "customer_name": "Juan Dela Cruz",
      "customer_address": "123 Main St, Manila",
      "customer_phone": "09171234567",
      "items_count": 2,
      "total": 448,
      "delivery_fee": 50,
      "seller_name": "Juan's Burgers"
    }
  ]
}
```

### Accept Order
```
POST /api/riders/accept-order
Authorization: Bearer {rider_token}
{
  "order_id": 1,
  "current_location": { "lat": 14.5899, "lng": 120.9822 }
}

Response:
{
  "success": true,
  "data": {
    "order_id": 1,
    "status": "dispatched",
    "message": "Order accepted"
  }
}
```

### Update Delivery Status
```
PUT /api/orders/{order_id}/delivery-update
Authorization: Bearer {rider_token}
{
  "status": "in-transit",  // or "delivered"
  "notes": "Picked up from seller, heading to customer",
  "rider_location": { "lat": 14.5950, "lng": 120.9850 }
}

Response:
{
  "success": true,
  "data": {
    "order_id": 1,
    "status": "in-transit",
    "message": "Delivery updated"
  }
}
```

### Assign Rider to Order
```
PUT /api/orders/{order_id}/assign-rider
Authorization: Bearer {admin_token}
{
  "rider_id": 3
}

Response:
{
  "success": true,
  "data": {
    "order_id": 1,
    "rider_id": 3,
    "message": "Rider assigned"
  }
}
```

### Get Rider Earnings
```
GET /api/riders/earnings
Authorization: Bearer {rider_token}

Response:
{
  "success": true,
  "data": {
    "total_earnings": 2450,
    "completed_deliveries": 49,
    "active_deliveries": 2,
    "rating": 4.9
  }
}
```

---

## Admin Endpoints (8)

### Dashboard
```
GET /api/admin/dashboard
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": {
    "total_users": 342,
    "user_breakdown": { "customer": 250, "seller": 50, "rider": 40, "admin": 2 },
    "total_orders": 1823,
    "total_revenue": 285600,
    "pending_verifications": { "sellers": 5, "riders": 3 },
    "active_orders": 12,
    "verified_sellers": 47,
    "verified_riders": 21
  }
}
```

### List Users
```
GET /api/admin/users?role=seller
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 2,
      "email": "seller@test.com",
      "first_name": "Juan",
      "role": "seller",
      "created_at": "2025-11-17T10:00:00"
    }
  ]
}
```

### Update User Status
```
PUT /api/admin/users/{user_id}/status
Authorization: Bearer {admin_token}
{
  "status": "suspended"  // or "active"
}

Response:
{
  "success": true,
  "data": {
    "user_id": 1,
    "status": "suspended"
  }
}
```

### Get Pending Sellers
```
GET /api/admin/sellers/pending
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "user_id": 2,
      "email": "seller@test.com",
      "business_name": "Juan's Burgers",
      "category": "Fast Food",
      "verified": 0,
      "created_at": "2025-11-17T10:00:00"
    }
  ]
}
```

### Verify Seller
```
PUT /api/admin/sellers/{seller_id}/verify
Authorization: Bearer {admin_token}
{}

Response:
{
  "success": true,
  "data": {
    "seller_id": 1,
    "message": "Seller verified"
  }
}
```

### Get Pending Riders
```
GET /api/admin/riders/pending
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "user_id": 3,
      "email": "rider@test.com",
      "vehicle_type": "Motorcycle",
      "driver_license": "ABC123456",
      "verified": 0,
      "created_at": "2025-11-17T10:00:00"
    }
  ]
}
```

### Verify Rider
```
PUT /api/admin/riders/{rider_id}/verify
Authorization: Bearer {admin_token}
{}

Response:
{
  "success": true,
  "data": {
    "rider_id": 1,
    "message": "Rider verified"
  }
}
```

### Revenue Analytics
```
GET /api/admin/analytics/revenue?period=month
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": [
    {
      "date": "2025-11-17",
      "revenue": 14500,
      "orders": 45
    }
  ]
}
```

---

## Review Endpoints (2)

### Submit Review
```
POST /api/reviews
Authorization: Bearer {customer_token}
{
  "product_id": 1,
  "rating": 5,
  "title": "Excellent burger!",
  "body": "Fresh ingredients, highly recommend"
}

Response:
{
  "success": true,
  "data": {
    "review_id": 1,
    "product_id": 1,
    "rating": 5
  }
}
```

### Get Product Reviews
```
GET /api/products/{product_id}/reviews

Response:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "user_id": 1,
      "rating": 5,
      "title": "Excellent!",
      "body": "Fresh and delicious"
    }
  ]
}
```

---

## Health Check

### Server Status
```
GET /api/health

Response:
{
  "status": "ok"
}
```

---

## Error Responses

### Standard Error Format
```json
{
  "success": false,
  "error": "error message",
  "data": null
}
```

### Common Status Codes
- **200** - Success
- **400** - Bad request (missing fields, invalid data)
- **401** - Unauthorized (invalid token)
- **403** - Forbidden (insufficient permissions)
- **404** - Not found
- **500** - Server error

---

## Authentication Header
All endpoints except auth and public endpoints require:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

**Last Updated**: November 2025
**Total Endpoints**: 30+
**Supported Roles**: customer, seller, rider, admin

