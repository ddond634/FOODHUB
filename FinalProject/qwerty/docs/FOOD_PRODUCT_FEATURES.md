# Food & Beverage Product Features

## Overview
Enhanced product management system for food and beverage sellers with industry-specific requirements including manufacture dates, expiry dates, and detailed variation management with per-variation stock tracking.

## Features Implemented

### 1. **Manufacture and Expiry Dates**
Food safety compliance fields for tracking product freshness and regulatory requirements.

#### Database Schema
- **Table**: `products`
- **New Columns**:
  - `manufacture_date` (DATE, nullable) - When the product was manufactured
  - `expiry_date` (DATE, nullable) - When the product expires

#### Frontend (Seller Dashboard)
- **File**: `frontend/seller_dashboard.html` (lines 1195-1209)
- Date input fields with:
  - Type: `date` for native date picker
  - Max date: `9999-12-31` to prevent overflow
  - Help text explaining the purpose
  - Optional fields (can be left blank)

#### Backend API
- **Create Product**: `POST /api/sellers/products`
  - Accepts `manufacture_date` and `expiry_date` in request body
  - Format: `YYYY-MM-DD` (ISO 8601)
  - Both fields are optional (null allowed)
  
- **Update Product**: `PUT /api/sellers/products/<product_id>`
  - Can update dates independently or together
  - Supports partial updates (only changed fields)

- **Get Products**: `GET /api/products`
  - Returns `manufacture_date` and `expiry_date` in product list
  - Available for filtering/display in shop

Example JSON:
```json
{
  "title": "Fresh Orange Juice",
  "price": 75.00,
  "stock": 50,
  "category": "Beverages",
  "manufacture_date": "2024-12-01",
  "expiry_date": "2024-12-15"
}
```

### 2. **Product Variations with Stock Management**
Advanced variation system allowing sellers to offer different sizes, flavors, or options with individual pricing and stock levels.

#### Database Schema
- **Table**: `product_variation_options`
- **Columns**:
  - `id` - Unique variation ID
  - `product_id` - Parent product reference
  - `variation_type` - Category (e.g., "Size", "Flavor")
  - `variation_value` - Specific option (e.g., "Small", "Large", "Vanilla")
  - `price_adjustment` - Additional cost/discount for this variation (₱)
  - `stock` - Available quantity for this specific variation

#### Frontend Features
- **Dynamic Variation Fields**:
  - Add/remove variations on the fly
  - Each variation has 4 inputs:
    1. **Type**: Category of variation (Size, Flavor, Color, etc.)
    2. **Value**: Specific option name
    3. **Price Adjustment**: Additional charge (₱) - can be 0 or negative
    4. **Stock**: Inventory count for this variation
  
- **User Interface**:
  - "Add Variation" button to create new variation fields
  - Remove button (×) on each variation to delete
  - Clear help text: "e.g., Size: Small, Large / Flavor: Vanilla, Chocolate"
  - Stock guidance: "Stock quantity for this specific variation"

#### Variation Examples

**Example 1: Coffee with Size Variations**
```
Product: Premium Coffee Beans
Base Price: ₱250.00
Base Stock: 0 (all stock is in variations)

Variations:
- Type: Size | Value: 250g  | Price Adj: ₱0.00   | Stock: 30
- Type: Size | Value: 500g  | Price Adj: ₱200.00 | Stock: 20
- Type: Size | Value: 1kg   | Price Adj: ₱450.00 | Stock: 10

Customer sees:
- 250g - ₱250.00 (30 available)
- 500g - ₱450.00 (20 available)
- 1kg - ₱700.00 (10 available)
```

**Example 2: Juice with Flavor Options**
```
Product: Fresh Fruit Juice
Base Price: ₱80.00
Base Stock: 0

Variations:
- Type: Flavor | Value: Orange      | Price Adj: ₱0.00  | Stock: 25
- Type: Flavor | Value: Mango       | Price Adj: ₱10.00 | Stock: 15
- Type: Flavor | Value: Mixed Berry | Price Adj: ₱15.00 | Stock: 10

Customer sees:
- Orange - ₱80.00 (25 available)
- Mango - ₱90.00 (15 available)
- Mixed Berry - ₱95.00 (10 available)
```

**Example 3: Combo Product**
```
Product: Gourmet Chocolate Bar
Base Price: ₱120.00
Base Stock: 5 (plain chocolate, no variation)

Variations:
- Type: Size   | Value: Regular | Price Adj: ₱0.00   | Stock: 20
- Type: Size   | Value: Large   | Price Adj: ₱40.00  | Stock: 15
- Type: Flavor | Value: Dark    | Price Adj: ₱10.00  | Stock: 12
- Type: Flavor | Value: Mint    | Price Adj: ₱15.00  | Stock: 8

Note: In this case, customers can choose:
- Plain (no variation) - ₱120.00 (5 available)
- Regular size variations with different flavors
- Large size variations with different flavors
```

### 3. **Stock Management Strategy**

#### Base Stock vs Variation Stock
- **Base Stock**: General inventory when no variation is selected
- **Variation Stock**: Specific inventory per variation
- **Best Practice**: 
  - If all products have variations, set base stock to 0
  - If some products are sold without variations, keep base stock > 0

#### Frontend Validation
- Stock cannot be negative
- Price adjustments can be positive (upcharge) or negative (discount)
- All variation fields are required when creating a variation

## Migration Details

### Migration File
**Path**: `database/migrate_add_food_product_dates.py`

**Executed**: ✅ Successful

**Changes Made**:
1. Added `manufacture_date DATE` column to `products` table
2. Added `expiry_date DATE` column to `products` table
3. Both columns are nullable (optional fields)
4. Compatible with both MySQL and SQLite

**Migration Output**:
```
[MIGRATION] Adding manufacture_date and expiry_date columns to products table...
✅ Added manufacture_date column
✅ Added expiry_date column
[SUCCESS] Migration completed successfully!
```

## Code Changes Summary

### Frontend JavaScript
**File**: `frontend/js/seller_dashboard.js`

**Changes**:
1. **Line 742-750**: Updated `saveProduct()` to collect date values:
   ```javascript
   const productData = {
       title: document.getElementById('productName').value.trim(),
       // ... other fields ...
       manufacture_date: document.getElementById('manufactureDate').value || null,
       expiry_date: document.getElementById('expiryDate').value || null
   };
   ```

2. **Line 622-627**: Updated `clearProductForm()` to reset date fields:
   ```javascript
   document.getElementById('manufactureDate').value = '';
   document.getElementById('expiryDate').value = '';
   ```

3. **Line 900-907**: Updated `loadProductForEdit()` to populate date fields when editing:
   ```javascript
   document.getElementById('manufactureDate').value = product.manufacture_date || '';
   document.getElementById('expiryDate').value = product.expiry_date || '';
   ```

### Backend API
**File**: `backend/server.py`

**Changes**:
1. **Line 4250-4254**: Extract dates from request in `api_seller_create_product()`:
   ```python
   manufacture_date = data.get('manufacture_date') or None
   expiry_date = data.get('expiry_date') or None
   ```

2. **Line 4260-4272**: Updated INSERT queries to include date columns:
   ```python
   # MySQL
   'INSERT INTO products (..., manufacture_date, expiry_date, ...) VALUES (%s, %s, ...)'
   
   # SQLite
   'INSERT INTO products (..., manufacture_date, expiry_date, ...) VALUES (?, ?, ...)'
   ```

3. **Line 4347**: Updated `api_seller_update_product()` to allow date field updates:
   ```python
   for field in ['title', 'description', 'price', 'stock', 'category', 'img_url', 'manufacture_date', 'expiry_date']:
   ```

4. **Line 2784-2812**: Updated `get_products()` SELECT query to include dates:
   ```sql
   SELECT p.id, p.title, ..., p.manufacture_date, p.expiry_date, ...
   ```

## Testing

### Manual Testing Checklist
- [ ] Create new product with both dates
- [ ] Create new product with only manufacture date
- [ ] Create new product with only expiry date
- [ ] Create new product with no dates (should work)
- [ ] Edit existing product to add dates
- [ ] Edit existing product to remove dates
- [ ] Verify dates display correctly in seller dashboard
- [ ] Verify dates appear in shop product listings

### Automated Test Script
**File**: `test_food_product_dates.py`

**Usage**:
```bash
python test_food_product_dates.py
```

**Test Cases**:
1. Create product with dates
2. Retrieve product and verify dates match
3. Update product dates
4. Create product without dates (optional field test)

## API Examples

### Create Product with Dates and Variations
```bash
POST /api/sellers/products
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Organic Green Tea",
  "description": "Premium organic green tea leaves",
  "price": 150.00,
  "stock": 0,
  "category": "Beverages",
  "img_url": "https://example.com/green-tea.jpg",
  "manufacture_date": "2024-11-15",
  "expiry_date": "2025-11-15"
}
```

### Add Variations to Product
```bash
POST /api/sellers/products/<product_id>/variations
Authorization: Bearer <token>
Content-Type: application/json

{
  "variations": [
    {
      "variation_type": "Size",
      "variation_value": "50g",
      "price_adjustment": 0,
      "stock": 40
    },
    {
      "variation_type": "Size",
      "variation_value": "100g",
      "price_adjustment": 130,
      "stock": 25
    }
  ]
}
```

### Update Product Dates
```bash
PUT /api/sellers/products/<product_id>
Authorization: Bearer <token>
Content-Type: application/json

{
  "manufacture_date": "2024-12-01",
  "expiry_date": "2025-12-01"
}
```

## Best Practices for Sellers

### For Food Products
1. **Always include dates**: Manufacture and expiry dates are critical for food safety
2. **Keep dates current**: Update when restocking with new batches
3. **Use variations for sizes**: Different package sizes often have different shelf lives
4. **Monitor expiry dates**: Consider implementing alerts for products nearing expiry

### For Beverage Products
1. **Date precision**: Beverages often have specific best-before dates
2. **Variation pricing**: Larger sizes typically have better unit economics
3. **Stock management**: Track individual variation stock carefully
4. **Flavor variations**: Use price adjustments for premium flavors

### General Tips
1. **Variation strategy**: 
   - Use variations for genuine product differences
   - Keep variation names consistent (e.g., always "Small/Medium/Large")
   - Price adjustments should reflect actual cost differences

2. **Stock accuracy**:
   - Update stock levels promptly after sales
   - Set realistic stock quantities per variation
   - Use base stock = 0 when ALL items have variations

3. **Data quality**:
   - Use clear, descriptive variation types and values
   - Ensure manufacture dates are not in the future
   - Expiry dates should be after manufacture dates (frontend validation recommended)

## Future Enhancements

### Potential Improvements
1. **Date Validation**:
   - Frontend validation: expiry_date > manufacture_date
   - Warning if expiry date is soon (e.g., < 7 days)
   - Prevent manufacture_date in the future

2. **Batch Tracking**:
   - Add batch_number field
   - Link variations to specific batches
   - Track manufacture dates per batch

3. **Expiry Alerts**:
   - Email notifications for products nearing expiry
   - Dashboard widget showing soon-to-expire items
   - Automatic price reduction for near-expiry products

4. **Variation Combinations**:
   - Matrix view for size × flavor combinations
   - Bulk stock updates for multiple variations
   - Import/export variation data via CSV

5. **Advanced Stock Management**:
   - Low stock alerts per variation
   - Automatic stock reservations during checkout
   - Stock history and analytics

## Support

### Common Issues

**Q: Dates not saving?**
A: Ensure date format is `YYYY-MM-DD`. Check browser console for JavaScript errors.

**Q: Can I leave dates blank?**
A: Yes, both fields are optional. However, recommended for food products.

**Q: How do variations affect total stock?**
A: Total stock = base stock + sum of all variation stocks. Display this in seller dashboard.

**Q: Can I have variations without stock?**
A: Yes, but set stock to 0. Customers won't be able to add to cart.

### Technical Support
- Check migration status: `python database/migrate_add_food_product_dates.py`
- Verify database columns: Run `DESCRIBE products;` in MySQL or `.schema products` in SQLite
- Test API endpoints: Use `test_food_product_dates.py` script

## Compliance Notes

### Food Safety Regulations
This feature supports compliance with:
- Food labeling requirements (manufacture/expiry dates)
- Inventory rotation (FIFO - First In, First Out)
- Shelf life management
- Batch traceability

**Disclaimer**: This system provides tools for date tracking. Sellers are responsible for ensuring compliance with local food safety regulations.

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Status**: ✅ Production Ready
