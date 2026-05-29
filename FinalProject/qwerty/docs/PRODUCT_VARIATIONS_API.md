# Product Variations API Documentation

Complete API reference for the product variations system supporting multiple options (size, flavor, color, etc.) per product.

## Table of Contents
1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [Seller Endpoints](#seller-endpoints)
4. [Customer Endpoints](#customer-endpoints)
5. [Cart Endpoints](#cart-endpoints)
6. [Order Processing](#order-processing)
7. [Usage Examples](#usage-examples)

---

## Overview

The variations system allows:
- **Sellers**: Add multiple variations to products (Size, Flavor, Color, etc.)
- **Customers**: Select specific variations when purchasing
- **System**: Track inventory separately for each variation
- **Orders**: Store variation details for order history and receipts

### Key Features
- ✅ Multiple variation types per product (Size + Flavor)
- ✅ Individual pricing per variation (base price + adjustment)
- ✅ Separate inventory tracking
- ✅ SKU support for unique identification
- ✅ Cart persistence with variations
- ✅ Automatic stock deduction on order

---

## Database Schema

### `product_variation_options`
Stores all product variations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key |
| `product_id` | INT | FK to products table |
| `variation_type` | VARCHAR(50) | Type: "Size", "Flavor", "Color" |
| `variation_value` | VARCHAR(100) | Value: "Small", "Chocolate", "Red" |
| `price_adjustment` | DECIMAL(12,2) | Additional cost on base price |
| `stock` | INT | Available quantity for this variation |
| `sku` | VARCHAR(100) | Unique SKU (optional) |
| `is_available` | TINYINT | 1=available, 0=hidden |
| `created_at` | DATETIME | Timestamp |

**Indexes:**
- `idx_product_variation` on `(product_id, variation_type)`
- `idx_sku` on `sku` (UNIQUE)

### `cart_items`
Persistent shopping cart with variation support.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key |
| `user_id` | INT | FK to users table |
| `product_id` | INT | FK to products table |
| `variation_id` | INT | FK to product_variation_options (nullable) |
| `quantity` | INT | Item quantity |
| `created_at` | DATETIME | When added |
| `updated_at` | DATETIME | Last modified |

**Unique Constraint:** `(user_id, product_id, variation_id)`

### `order_items` (Enhanced)
Order line items with variation tracking.

| Column | Type | Description |
|--------|------|-------------|
| `variation_id` | INT | FK to product_variation_options (nullable) |
| `variation_details` | TEXT | JSON snapshot of variation at purchase |

**Example variation_details:**
```json
{
  "variation_type": "Size",
  "variation_value": "Medium",
  "price_adjustment": 5.00
}
```

### `inventory_movements_variations`
Tracks stock changes for variations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key |
| `variation_id` | INT | FK to product_variation_options |
| `qty` | INT | Change amount (negative for sales) |
| `movement_type` | VARCHAR(50) | "sale", "restock", "adjustment" |
| `ref` | VARCHAR(100) | Reference: "order:123" |
| `notes` | TEXT | Optional notes |
| `created_at` | DATETIME | Timestamp |

---

## Seller Endpoints

### 1. Add Variation to Product

**Endpoint:** `POST /api/sellers/products/{product_id}/variations`

**Authentication:** Required (Seller role)

**Request Body:**
```json
{
  "variation_type": "Size",
  "variation_value": "Medium",
  "price_adjustment": 5.00,
  "stock": 50,
  "sku": "PROD-001-MD"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Variation added successfully",
  "data": {
    "variation_id": 123,
    "product_id": 45,
    "variation_type": "Size",
    "variation_value": "Medium",
    "price_adjustment": 5.00,
    "stock": 50
  }
}
```

**Validation:**
- Seller must own the product
- `variation_type` and `variation_value` required
- `price_adjustment` defaults to 0
- `stock` defaults to 0
- `sku` must be unique if provided

---

### 2. Update Variation

**Endpoint:** `PUT /api/sellers/products/{product_id}/variations/{variation_id}`

**Authentication:** Required (Seller role)

**Request Body:**
```json
{
  "variation_value": "Extra Large",
  "price_adjustment": 12.00,
  "stock": 30,
  "is_available": true
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Variation updated",
  "data": {
    "variation_id": 123
  }
}
```

**Notes:**
- All fields optional (only send what needs updating)
- `is_available`: Set to `false` to hide variation without deleting

---

### 3. Delete Variation

**Endpoint:** `DELETE /api/sellers/products/{product_id}/variations/{variation_id}`

**Authentication:** Required (Seller role)

**Response (200):**
```json
{
  "success": true,
  "message": "Variation deleted",
  "data": {
    "variation_id": 123
  }
}
```

**Notes:**
- Permanently deletes variation
- Consider setting `is_available=false` instead for soft delete

---

## Customer Endpoints

### 4. Get Product Variations (Public)

**Endpoint:** `GET /api/products/{product_id}/variations`

**Authentication:** None (public)

**Response (200):**
```json
{
  "success": true,
  "message": "Variations fetched",
  "data": {
    "variations": [
      {
        "id": 101,
        "product_id": 45,
        "variation_type": "Size",
        "variation_value": "Small",
        "price_adjustment": 0,
        "stock": 50,
        "sku": "PROD-001-SM",
        "is_available": 1,
        "created_at": "2024-01-15T10:30:00"
      },
      {
        "id": 102,
        "product_id": 45,
        "variation_type": "Size",
        "variation_value": "Medium",
        "price_adjustment": 5,
        "stock": 40,
        "sku": "PROD-001-MD",
        "is_available": 1,
        "created_at": "2024-01-15T10:31:00"
      },
      {
        "id": 103,
        "product_id": 45,
        "variation_type": "Flavor",
        "variation_value": "Chocolate",
        "price_adjustment": 2,
        "stock": 60,
        "sku": "PROD-001-CHOC",
        "is_available": 1,
        "created_at": "2024-01-15T10:32:00"
      }
    ],
    "grouped": {
      "Size": [
        {"id": 101, "variation_value": "Small", "price_adjustment": 0, "stock": 50, ...},
        {"id": 102, "variation_value": "Medium", "price_adjustment": 5, "stock": 40, ...}
      ],
      "Flavor": [
        {"id": 103, "variation_value": "Chocolate", "price_adjustment": 2, "stock": 60, ...}
      ]
    },
    "total": 3
  }
}
```

**Notes:**
- Returns only available variations (`is_available=1`)
- `grouped` object organizes by variation type for UI rendering
- `variations` array is flat list of all variations

---

## Cart Endpoints

### 5. Add to Cart with Variation

**Endpoint:** `POST /api/cart`

**Authentication:** Required

**Request Body:**
```json
{
  "product_id": 45,
  "variation_id": 102,
  "quantity": 2
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Added to cart",
  "data": {
    "cart_item_id": 789,
    "product_id": 45,
    "variation_id": 102,
    "quantity": 2
  }
}
```

**Validation:**
- Stock availability checked for selected variation
- If item already in cart with same variation, quantity is added
- `variation_id` can be `null` for products without variations

---

### 6. Get Cart with Variations

**Endpoint:** `GET /api/cart`

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "message": "Cart fetched",
  "data": {
    "cart_items": [
      {
        "cart_item_id": 789,
        "product_id": 45,
        "variation_id": 102,
        "quantity": 2,
        "title": "Premium Coffee Beans",
        "description": "Arabica blend",
        "base_price": 250.00,
        "img_url": "/uploads/coffee.jpg",
        "seller_id": 12,
        "variation_type": "Size",
        "variation_value": "Medium",
        "price_adjustment": 5.00,
        "variation_stock": 40,
        "seller_name": "Bean & Brew Shop",
        "final_price": 255.00,
        "subtotal": 510.00
      }
    ],
    "total_items": 1,
    "total_amount": 510.00
  }
}
```

**Calculated Fields:**
- `final_price` = `base_price` + `price_adjustment`
- `subtotal` = `final_price` × `quantity`

---

### 7. Update Cart Item

**Endpoint:** `PUT /api/cart/{cart_item_id}`

**Authentication:** Required

**Request Body:**
```json
{
  "quantity": 5
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Cart updated",
  "data": {
    "cart_item_id": 789,
    "quantity": 5
  }
}
```

**Validation:**
- Stock availability re-checked for new quantity
- User must own the cart item

---

### 8. Remove from Cart

**Endpoint:** `DELETE /api/cart/{cart_item_id}`

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "message": "Removed from cart",
  "data": {
    "cart_item_id": 789
  }
}
```

---

## Order Processing

### 9. Create Order with Variations

**Endpoint:** `POST /api/orders`

**Authentication:** Optional (can be public for guest checkout)

**Request Body:**
```json
{
  "customer": {
    "name": "Juan Dela Cruz",
    "phone": "09171234567",
    "address": "123 Main St, Manila"
  },
  "items": [
    {
      "product_id": 45,
      "variation_id": 102,
      "quantity": 2,
      "price": 255.00,
      "title": "Premium Coffee Beans"
    }
  ],
  "payment": "Cash on Delivery",
  "delivery": 50
}
```

**Response (200):**
```json
{
  "success": true,
  "order_id": 5001,
  "total": 560.00
}
```

**Processing Logic:**
1. Validates stock availability for each variation
2. Creates order record
3. Creates order_items with `variation_id` and `variation_details` JSON
4. Deducts stock from `product_variation_options.stock`
5. Creates `inventory_movements_variations` record
6. If no variation: Deducts from `products.stock` (legacy behavior)

**variation_details Storage Example:**
```json
{
  "variation_type": "Size",
  "variation_value": "Medium",
  "price_adjustment": 5.00
}
```

This JSON snapshot preserves variation info even if variation is later deleted.

---

## Usage Examples

### Complete Purchase Flow

#### Step 1: Customer Views Product
```javascript
// Fetch product details
fetch('/api/products/45')
  .then(res => res.json())
  .then(product => {
    console.log('Product:', product.data);
    // Fetch variations
    return fetch('/api/products/45/variations');
  })
  .then(res => res.json())
  .then(variations => {
    console.log('Available variations:', variations.data.grouped);
  });
```

#### Step 2: Add to Cart with Selected Variation
```javascript
fetch('/api/cart', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + userToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    product_id: 45,
    variation_id: 102,  // Medium size
    quantity: 2
  })
})
.then(res => res.json())
.then(data => console.log('Added to cart:', data));
```

#### Step 3: Review Cart
```javascript
fetch('/api/cart', {
  headers: { 'Authorization': 'Bearer ' + userToken }
})
.then(res => res.json())
.then(cart => {
  console.log('Cart items:', cart.data.cart_items);
  console.log('Total:', cart.data.total_amount);
});
```

#### Step 4: Create Order
```javascript
// Prepare order from cart
fetch('/api/cart', {
  headers: { 'Authorization': 'Bearer ' + userToken }
})
.then(res => res.json())
.then(cart => {
  const orderItems = cart.data.cart_items.map(item => ({
    product_id: item.product_id,
    variation_id: item.variation_id,
    quantity: item.quantity,
    price: item.final_price,
    title: item.title
  }));
  
  return fetch('/api/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer: {
        name: 'Juan Dela Cruz',
        phone: '09171234567',
        address: '123 Main St, Manila'
      },
      items: orderItems,
      payment: 'Cash on Delivery',
      delivery: 50
    })
  });
})
.then(res => res.json())
.then(order => {
  console.log('Order created:', order.order_id);
  console.log('Total:', order.total);
});
```

---

### Seller Management

#### Add Multiple Variations
```javascript
const variations = [
  { variation_type: 'Size', variation_value: 'Small', price_adjustment: 0, stock: 50 },
  { variation_type: 'Size', variation_value: 'Medium', price_adjustment: 5, stock: 40 },
  { variation_type: 'Size', variation_value: 'Large', price_adjustment: 10, stock: 30 }
];

const productId = 45;

Promise.all(variations.map(variation => 
  fetch(`/api/sellers/products/${productId}/variations`, {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + sellerToken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(variation)
  }).then(res => res.json())
))
.then(results => console.log('All variations added:', results));
```

#### Update Stock for Variation
```javascript
fetch(`/api/sellers/products/45/variations/102`, {
  method: 'PUT',
  headers: {
    'Authorization': 'Bearer ' + sellerToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    stock: 100  // Restock
  })
})
.then(res => res.json())
.then(data => console.log('Stock updated:', data));
```

---

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "success": false,
  "message": "variation_type and variation_value required",
  "error": "validation_error"
}
```

**401 Unauthorized:**
```json
{
  "success": false,
  "message": "Unauthorized",
  "error": "auth_required"
}
```

**403 Forbidden:**
```json
{
  "success": false,
  "message": "Not authorized",
  "error": "insufficient_permissions"
}
```

**404 Not Found:**
```json
{
  "success": false,
  "message": "Cart item not found",
  "error": "not_found"
}
```

**Stock Validation:**
```json
{
  "success": false,
  "message": "Insufficient stock for this variation",
  "error": "stock_unavailable"
}
```

---

## Best Practices

### For Sellers
1. **Use descriptive variation types**: "Size", "Flavor", "Color" (capitalize first letter)
2. **Set realistic stock levels**: Update regularly to prevent overselling
3. **Use SKUs**: Helps with inventory management and reporting
4. **Price adjustments**: Relative to base price (can be 0, positive, or negative)
5. **Disable instead of delete**: Use `is_available=false` to hide variations without losing history

### For Frontend Developers
1. **Group variations by type**: Use the `grouped` object from GET variations
2. **Show final price**: Display `base_price + price_adjustment`
3. **Check stock**: Disable "Add to Cart" if `variation_stock == 0`
4. **Validate selection**: Ensure customer selects all required variation types
5. **Error handling**: Show user-friendly messages for stock/validation errors

### For System Administrators
1. **Monitor inventory**: Track `inventory_movements_variations` for audit trail
2. **Low stock alerts**: Query variations with `stock < threshold`
3. **Popular variations**: Analyze sales by variation for insights
4. **Data integrity**: Ensure `variation_id` foreign keys maintain referential integrity

---

## Migration Script

The database schema is created by:
```bash
python database/migrate_add_product_variations.py
```

This creates:
- `product_variation_options` table
- `cart_items` table
- `inventory_movements_variations` table
- Updates `order_items` with variation support

---

## Testing

Run comprehensive API tests:
```bash
python tools/test_variations.py
```

Tests cover:
- ✅ Adding variations
- ✅ Fetching variations (public)
- ✅ Updating variations
- ✅ Adding to cart with variations
- ✅ Cart operations
- ✅ Order creation with inventory deduction
- ✅ Deleting variations

---

## Support

For issues or questions:
- Check existing test cases in `tools/test_variations.py`
- Review error responses in logs
- Verify database schema matches migration script

**Last Updated:** 2024-01-15
