# Customer Reviews System Documentation

## Overview
Complete customer reviews system that allows customers to leave reviews after receiving their orders.

## Features Implemented

### 1. Review Trigger
- ✅ Customers can only review products from **delivered orders**
- ✅ Review option unavailable for non-delivered orders
- ✅ One review per product per order

### 2. Review Fields
- ✅ Customer Name (auto-filled from JWT token)
- ✅ Product being reviewed
- ✅ Seller information (auto-populated)
- ✅ Rating (1–5 stars, required)
- ✅ Comment/Text feedback (optional, max 500 characters)
- ✅ Image upload placeholder (ready for implementation)

### 3. Database Integration
**Table Created:** `reviews`

Fields:
- `id` - Primary key (auto-increment)
- `customer_id` - Foreign key to users table
- `order_id` - Foreign key to orders table
- `product_id` - Foreign key to products table
- `seller_id` - Foreign key to users table (seller)
- `rating` - Integer (1-5, with CHECK constraint)
- `comment` - TEXT (optional)
- `images` - TEXT (JSON array of image paths)
- `created_at` - Timestamp (auto-generated)
- `updated_at` - Timestamp (auto-updated)

**Indexes Created:**
- idx_customer (customer_id)
- idx_product (product_id)
- idx_seller (seller_id)
- idx_order (order_id)
- idx_rating (rating)
- idx_created (created_at)

### 4. Customer Reviews Display
**Location:** `/account.html` (My Reviews section)

Features:
- Displays all reviews submitted by the logged-in customer
- Shows:
  - Product name and image
  - Seller name
  - Star rating (visual)
  - Review comment
  - Date submitted
  - Delete button
- Responsive card design with hover effects
- Empty state: "No reviews yet" message

### 5. Backend Endpoints

#### GET `/api/customer/reviews`
**Purpose:** Fetch all reviews of the logged-in customer

**Authentication:** Required (role: customer)

**Response:**
```json
{
  "success": true,
  "data": {
    "reviews": [
      {
        "id": 1,
        "order_id": 123,
        "product_id": 45,
        "seller_id": 10,
        "rating": 5,
        "comment": "Great product!",
        "images": [],
        "created_at": "2025-11-24 20:00:00",
        "updated_at": "2025-11-24 20:00:00",
        "product_name": "Organic Coffee Beans",
        "product_image": "/uploads/products/coffee.jpg",
        "seller_name": "Coffee Shop"
      }
    ],
    "total": 1
  }
}
```

#### POST `/api/customer/reviews`
**Purpose:** Submit a new review for a delivered order

**Authentication:** Required (role: customer)

**Request Body:**
```json
{
  "order_id": 123,
  "product_id": 45,
  "rating": 5,
  "comment": "Great product!",
  "images": []
}
```

**Validations:**
- Order must exist and belong to customer
- Order status must be "delivered"
- Product must exist in the order
- Rating must be 1-5
- Comment max 500 characters
- No duplicate reviews (one per product per order)

**Response:**
```json
{
  "success": true,
  "data": {
    "review_id": 1,
    "message": "Review submitted successfully"
  }
}
```

#### DELETE `/api/customer/reviews/<review_id>`
**Purpose:** Delete a review (only by the customer who created it)

**Authentication:** Required (role: customer)

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Review deleted successfully"
  }
}
```

#### GET `/api/customer/orders/reviewable`
**Purpose:** Get all delivered orders that can be reviewed

**Authentication:** Required (role: customer)

**Response:**
```json
{
  "success": true,
  "data": {
    "reviewable_items": [
      {
        "order_id": 123,
        "order_date": "2025-11-20",
        "product_id": 45,
        "product_name": "Organic Coffee Beans",
        "product_image": "/uploads/products/coffee.jpg",
        "seller_id": 10,
        "seller_name": "Coffee Shop"
      }
    ],
    "total": 1
  }
}
```

### 6. Frontend Implementation

**Files:**
- `/frontend/account.html` - Main page with reviews section
- `/frontend/js/customer_reviews.js` - Reviews JavaScript functionality

**Features:**
- Dynamic rendering of reviews with styling
- Write review modal with star rating input
- Real-time character count (0/500)
- Form validation (rating required)
- Delete confirmation dialog
- Responsive design for mobile
- Loading states and error handling

**Functions:**
- `loadCustomerReviews()` - Loads reviews and reviewable orders
- `displayReviews(reviews)` - Renders review cards
- `displayReviewableOrders(items)` - Shows products awaiting review
- `openReviewModal()` - Opens review submission form
- `submitReview(event)` - Submits new review
- `deleteReview(reviewId)` - Deletes existing review
- `setRating(rating)` - Sets star rating (1-5)
- `updateCharCount()` - Updates character counter

### 7. Notifications
✅ **Implemented:** Sellers receive notification when new review is submitted
- Notification type: 'review'
- Message: "New X-star review received on your product"
- Linked to review ID

**Note:** Notifications table must exist in database for this feature to work.

## Setup Instructions

### 1. Run Migration
```bash
python database/migrate_add_customer_reviews.py
```

This creates the `reviews` table in your MySQL database.

### 2. Restart Server
The reviews API blueprint is automatically registered in `server.py`.

```bash
python run.py
```

### 3. Test the Feature
1. Log in as a customer
2. Place an order
3. Admin changes order status to "delivered"
4. Go to account page
5. See "Write a Review" button for delivered products
6. Submit a review (1-5 stars, optional comment)
7. Review appears in "My Reviews" section

## Security Features
- ✅ JWT authentication required
- ✅ Role-based access (customer only)
- ✅ Customer can only review their own orders
- ✅ Customer can only delete their own reviews
- ✅ Order ownership verification
- ✅ Delivered status verification
- ✅ Duplicate review prevention
- ✅ SQL injection protection (parameterized queries)
- ✅ XSS protection (HTML escaping in frontend)

## Error Handling
- Order not found
- Order not delivered
- Product not in order
- Unauthorized access
- Duplicate review
- Invalid rating
- Comment too long (>500 chars)
- Database errors with traceback

## Future Enhancements (Optional)
- [ ] Image upload for product photos
- [ ] Edit existing reviews
- [ ] Helpful/Not helpful voting
- [ ] Display reviews on product pages
- [ ] Average rating calculation per product
- [ ] Seller response to reviews
- [ ] Review moderation by admin
- [ ] Email notifications to sellers
- [ ] Review images in lightbox gallery

## Files Modified/Created

**Created:**
- `database/migrate_add_customer_reviews.py` - Database migration
- `backend/reviews_api.py` - Reviews API endpoints
- `frontend/js/customer_reviews.js` - Frontend JavaScript
- `docs/CUSTOMER_REVIEWS_DOCUMENTATION.md` - This file

**Modified:**
- `backend/server.py` - Registered reviews blueprint
- `frontend/account.html` - Added reviews section + modal

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    seller_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    images TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_customer (customer_id),
    INDEX idx_product (product_id),
    INDEX idx_seller (seller_id),
    INDEX idx_order (order_id),
    INDEX idx_rating (rating),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;
```

## API Testing Examples

### Submit a Review (cURL)
```bash
curl -X POST http://127.0.0.1:5000/api/customer/reviews \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "order_id": 1,
    "product_id": 5,
    "rating": 5,
    "comment": "Excellent product, highly recommended!"
  }'
```

### Get My Reviews
```bash
curl -X GET http://127.0.0.1:5000/api/customer/reviews \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Delete a Review
```bash
curl -X DELETE http://127.0.0.1:5000/api/customer/reviews/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Reviewable Orders
```bash
curl -X GET http://127.0.0.1:5000/api/customer/orders/reviewable \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Success Criteria
✅ All specifications met:
1. ✅ Review trigger (delivered orders only)
2. ✅ Review fields (name, product, seller, rating, comment)
3. ✅ Database integration (reviews table created)
4. ✅ Customer reviews display (dynamic rendering)
5. ✅ Backend endpoints (4 endpoints implemented)
6. ✅ Frontend requirements (validation, styling, placeholder)
7. ✅ Notifications (seller notified on new review)

## Support
For issues or questions, check:
- Server logs for backend errors
- Browser console for frontend errors
- Database connection settings
- JWT token expiration
- Role permissions (customer role required)
