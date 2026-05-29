# Seller Ratings System Documentation

## Overview

The Seller Ratings System provides dynamic, real-time rating analytics for sellers based on customer reviews. It displays overall ratings, detailed breakdowns by star level, and a comprehensive list of all reviews received.

## Features

### 1. Overall Rating Display
- **Average Rating**: Calculated from all customer reviews (1-5 stars)
- **Visual Stars**: Dynamic star display with half-star support
- **Review Count**: Total number of reviews received
- **Dashboard Integration**: Overall rating displayed in dashboard stats card

### 2. Rating Breakdown
- **Star Distribution**: Shows count and percentage for each star level (1-5)
- **Visual Progress Bars**: Color-coded bars representing percentage distribution
- **Real-time Updates**: Automatically recalculates when new reviews are submitted

### 3. Reviews List
- **Grouped by Product**: Reviews organized by product name
- **Product Rating**: Average rating per product with review count
- **Customer Information**: Reviewer name and review date
- **Review Content**: Star rating and customer comment
- **Product Images**: Thumbnail of reviewed product

### 4. Filtering & Search
- **Filter by Rating**: View only reviews with specific star ratings (1-5 or all)
- **Search Function**: Search by product name, customer name, or review content
- **Combined Filtering**: Apply both search and rating filter simultaneously

### 5. Auto-Refresh
- **Background Updates**: Ratings refresh every 30 seconds when on reviews section
- **Manual Refresh**: Load latest data when switching to reviews section
- **No Page Reload**: Updates happen dynamically without full page refresh

## Technical Implementation

### Backend API

#### Endpoint: GET /api/sellers/my-ratings

**Purpose**: Fetch comprehensive rating statistics for logged-in seller

**Authentication**: Requires valid JWT token with seller role

**Response Format**:
```json
{
    "status": "success",
    "data": {
        "overall_rating": 4.5,
        "total_reviews": 248,
        "rating_breakdown": {
            "5": {
                "count": 186,
                "percentage": 75.0
            },
            "4": {
                "count": 37,
                "percentage": 15.0
            },
            "3": {
                "count": 17,
                "percentage": 7.0
            },
            "2": {
                "count": 5,
                "percentage": 2.0
            },
            "1": {
                "count": 3,
                "percentage": 1.0
            }
        },
        "reviews": [
            {
                "id": 1,
                "rating": 5,
                "comment": "Excellent product! Fast shipping.",
                "created_at": "2024-11-20 14:30:00",
                "product_name": "Sample Product A",
                "product_image": "/uploads/products/sample.jpg",
                "customer_name": "John Doe"
            }
        ]
    }
}
```

#### Endpoint: GET /api/sellers/{seller_id}/ratings

**Purpose**: Fetch rating statistics for any seller (public endpoint)

**Authentication**: Not required

**Response Format**: Same as my-ratings, but without full review list (only recent 5)

#### Endpoint: GET /api/sellers/products/{product_id}/ratings

**Purpose**: Fetch rating statistics for a specific product

**Authentication**: Not required

**Response Format**:
```json
{
    "status": "success",
    "data": {
        "overall_rating": 4.8,
        "total_reviews": 45,
        "rating_breakdown": {
            "5": { "count": 35, "percentage": 77.8 },
            "4": { "count": 8, "percentage": 17.8 },
            "3": { "count": 2, "percentage": 4.4 },
            "2": { "count": 0, "percentage": 0.0 },
            "1": { "count": 0, "percentage": 0.0 }
        }
    }
}
```

### Database Schema

The ratings system uses the existing `reviews` table:

```sql
CREATE TABLE reviews (
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
    FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE,
    INDEX idx_customer_id (customer_id),
    INDEX idx_product_id (product_id),
    INDEX idx_seller_id (seller_id),
    INDEX idx_order_id (order_id),
    INDEX idx_rating (rating),
    INDEX idx_created_at (created_at)
);
```

**Indexes**: The system uses indexes on `seller_id` and `rating` for optimal query performance.

### Frontend Components

#### File Structure
```
frontend/
├── seller_dashboard.html      # Main dashboard with reviews section
├── css/
│   └── seller_dashboard.css   # Styles for ratings display
└── js/
    └── seller_ratings.js      # Rating logic and API integration
```

#### Key Functions

**loadSellerRatings()**
- Fetches rating data from backend API
- Updates all UI components with latest data
- Called on page load and section switch

**updateRatingDisplay(ratingsData)**
- Updates overall rating number and stars
- Updates review count text
- Triggers breakdown and list updates

**updateStarDisplay(selector, rating)**
- Dynamically renders star icons based on rating
- Supports full stars, half stars, and empty stars
- Used for overall rating and individual reviews

**updateRatingBreakdown(breakdown, totalReviews)**
- Updates progress bars for each star level
- Displays count and percentage for each rating
- Animates bar width changes

**displayReviewsList(reviews)**
- Groups reviews by product
- Calculates per-product average ratings
- Renders review cards with customer info and comments
- Shows empty state if no reviews exist

**filterReviewsByRating(rating)**
- Filters displayed reviews by star rating
- Updates active filter button state
- Shows/hides review items based on filter

**filterReviews()**
- Search function for reviews
- Searches by product name, customer name, or comment text
- Works in conjunction with rating filter

**startRatingsAutoRefresh()**
- Sets up 30-second interval for automatic updates
- Only refreshes when reviews section is active
- Prevents unnecessary API calls

### CSS Styling

#### Key Classes

**.reviews-summary**
- Container for overall rating and breakdown cards
- Responsive grid layout

**.rating-display**
- Large rating number with stars
- Flexbox layout for proper alignment

**.rating-bars**
- Container for star-level breakdown
- Vertically stacked progress bars

**.rating-bar-item**
- Individual star level row
- Contains label, bar, and percentage

**.rating-fill**
- Animated progress bar fill
- Width controlled by JavaScript percentage

**.review-item**
- Individual review card
- Hover effects for interactivity
- Border and shadow styling

**.empty-state**
- Centered message when no reviews exist
- Icon, heading, and descriptive text

## Usage Guide

### For Sellers

1. **Viewing Ratings**
   - Navigate to "Reviews" section in seller dashboard
   - View overall rating at top of page
   - See rating breakdown by star level
   - Scroll through all reviews

2. **Filtering Reviews**
   - Click star filter buttons to view specific ratings
   - Use search box to find reviews by keyword
   - Clear filters by clicking "All" button

3. **Understanding Metrics**
   - Overall Rating: Average of all review ratings
   - Rating Breakdown: Distribution of 1-5 star ratings
   - Review Count: Total number of reviews received
   - Product Ratings: Average rating per product

### For Developers

#### Adding Rating Display to New Pages

1. **Include Script**
```html
<script src="js/seller_ratings.js"></script>
```

2. **HTML Structure**
```html
<div class="reviews-summary">
    <div class="review-summary-card">
        <span class="rating-number">0.0</span>
        <div class="rating-stars">
            <i class="fa-solid fa-star"></i>
            <!-- 5 stars total -->
        </div>
        <p class="review-count">Based on 0 reviews</p>
    </div>
</div>
```

3. **Load Data**
```javascript
loadSellerRatings(); // Fetches and displays ratings
```

#### Customizing Auto-Refresh Interval

Edit `seller_ratings.js`:
```javascript
// Change from 30000 (30 seconds) to desired milliseconds
ratingsRefreshInterval = setInterval(() => {
    // ...
}, 60000); // 60 seconds
```

#### Extending API Endpoints

Add new rating queries in `backend/ratings_api.py`:
```python
@ratings_bp.route('/custom-endpoint', methods=['GET'])
def custom_rating_query():
    # Your custom logic
    return success_response(data)
```

## Performance Considerations

### Optimization Strategies

1. **Database Indexes**
   - Indexes on `seller_id`, `product_id`, `rating` fields
   - Compound indexes for complex queries
   - Regular ANALYZE TABLE for query optimization

2. **Caching** (Future Enhancement)
   - Cache overall rating in `sellers` table
   - Update cache on new review submission
   - Reduces database queries for frequently accessed data

3. **Query Efficiency**
   - Single query for all statistics using CASE WHEN
   - Minimize joins by denormalizing common fields
   - Use COALESCE for null handling

4. **Frontend Optimization**
   - Conditional auto-refresh (only when section is active)
   - Debounced search function
   - Virtual scrolling for large review lists (future)

### Load Testing Results

Expected performance with MySQL database:
- **< 100 reviews**: ~50ms query time
- **< 1000 reviews**: ~100ms query time
- **< 10000 reviews**: ~250ms query time

## Security

### Authentication & Authorization

1. **Token Validation**
   - All API requests require valid JWT token
   - Token verified using `@role_required('seller')` decorator
   - Seller can only access their own ratings via `/my-ratings`

2. **Input Sanitization**
   - HTML escaping on frontend using `escapeHtml()` function
   - Parameterized SQL queries prevent injection
   - Rating validation (1-5 range) in database CHECK constraint

3. **Rate Limiting** (Recommended)
   - Implement request throttling for API endpoints
   - Prevent abuse of auto-refresh feature
   - Use Flask-Limiter or similar middleware

## Testing

### Manual Testing Steps

1. **Test No Reviews Scenario**
   - Log in as new seller with no reviews
   - Navigate to Reviews section
   - Verify empty state displays correctly

2. **Test Rating Display**
   - Add test reviews with various ratings (1-5 stars)
   - Verify overall rating calculates correctly
   - Check star display matches rating (full/half/empty stars)

3. **Test Rating Breakdown**
   - Add reviews with different star ratings
   - Verify bar widths match percentages
   - Confirm counts are accurate

4. **Test Filtering**
   - Filter by each star rating (1-5)
   - Verify only matching reviews display
   - Test "All" filter shows all reviews

5. **Test Search**
   - Search by product name
   - Search by customer name
   - Search by review text
   - Test search + filter combination

6. **Test Auto-Refresh**
   - Stay on reviews section for 30+ seconds
   - Add new review from another browser/account
   - Verify ratings update automatically

### API Testing with cURL

**Get Seller Ratings:**
```bash
curl -X GET http://127.0.0.1:5000/api/sellers/my-ratings \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected Response:**
```json
{
    "status": "success",
    "data": {
        "overall_rating": 4.5,
        "total_reviews": 10,
        "rating_breakdown": { ... },
        "reviews": [ ... ]
    }
}
```

### Automated Testing (Future)

Create test file `tests/test_ratings_api.py`:
```python
def test_get_seller_ratings():
    # Create test seller and reviews
    # Call API endpoint
    # Assert response structure
    # Verify calculations
    pass
```

## Troubleshooting

### Common Issues

**1. Ratings Not Displaying**
- **Symptom**: Reviews section shows "No reviews yet" despite having reviews
- **Solution**: Check browser console for JavaScript errors
- **Check**: Verify JWT token is valid and role is 'seller'
- **Verify**: Ensure `seller_ratings.js` is loaded after `seller_dashboard.js`

**2. Incorrect Rating Calculations**
- **Symptom**: Overall rating doesn't match expected average
- **Solution**: Check database for invalid rating values
- **Query**: `SELECT * FROM reviews WHERE rating < 1 OR rating > 5`
- **Fix**: Update invalid ratings or delete corrupt records

**3. Auto-Refresh Not Working**
- **Symptom**: Ratings don't update after 30 seconds
- **Solution**: Check if `startRatingsAutoRefresh()` is called
- **Verify**: Ensure reviews section is active (has `.active` class)
- **Debug**: Add `console.log()` in interval function

**4. Star Display Issues**
- **Symptom**: Stars showing as squares or not updating
- **Solution**: Verify Font Awesome is loaded (check Network tab)
- **Check**: Ensure Font Awesome CSS is in `<head>`
- **Fallback**: Use `@import` in CSS file as backup

**5. Slow API Response**
- **Symptom**: Ratings take 3+ seconds to load
- **Solution**: Check database indexes exist
- **Query**: `SHOW INDEX FROM reviews`
- **Optimize**: Run `ANALYZE TABLE reviews` to update statistics

### Debug Mode

Add to `seller_ratings.js` for verbose logging:
```javascript
const DEBUG = true;

async function loadSellerRatings() {
    if (DEBUG) console.log('Loading seller ratings...');
    try {
        // ... existing code
        if (DEBUG) console.log('Ratings data:', data);
    } catch (error) {
        if (DEBUG) console.error('Error details:', error);
    }
}
```

## Future Enhancements

### Planned Features

1. **Seller Response to Reviews**
   - Allow sellers to reply to customer reviews
   - Display seller responses below reviews
   - Notification to customer when seller responds

2. **Review Analytics Dashboard**
   - Chart showing rating trends over time
   - Comparison with category averages
   - Best/worst rated products

3. **Review Moderation**
   - Flag inappropriate reviews
   - Admin review and approval workflow
   - Automated spam detection

4. **Advanced Filtering**
   - Filter by date range
   - Filter by product category
   - Filter by verified purchase
   - Sort by most helpful, recent, rating

5. **Review Incentives**
   - Badge for sellers with high ratings
   - Featured products based on ratings
   - Discount codes for reviewed products

6. **Export Functionality**
   - Download reviews as CSV/PDF
   - Generate rating reports
   - Schedule automated reports

## API Reference Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/sellers/my-ratings` | GET | Required (Seller) | Get current seller's ratings |
| `/api/sellers/{id}/ratings` | GET | Optional | Get any seller's public ratings |
| `/api/sellers/products/{id}/ratings` | GET | Optional | Get product rating statistics |

## Change Log

### Version 1.0.0 (2024-11-24)
- Initial implementation of seller ratings system
- Overall rating display with star visualization
- Rating breakdown by star level (1-5)
- Reviews list grouped by product
- Filter and search functionality
- Auto-refresh every 30 seconds
- Empty state handling
- MySQL database integration
- JWT authentication
- Responsive design

## Support

For issues or questions:
1. Check this documentation for troubleshooting steps
2. Review browser console for JavaScript errors
3. Check server logs for API errors
4. Verify database indexes and constraints
5. Test API endpoints directly with cURL

## License

This feature is part of the Hub marketplace system. All rights reserved.
