# Food & Beverage Seller - Quick Start Guide

## Adding a Food/Beverage Product

### Step 1: Access Product Form
1. Login to your seller account
2. Navigate to "My Products" tab in seller dashboard
3. Click "Add New Product" button

### Step 2: Fill Product Details

#### Basic Information
```
Product Name*:     Fresh Orange Juice
Category*:         Beverages
Base Price (₱)*:   80.00
Base Stock*:       0 (if using variations) or actual count
Description*:      100% freshly squeezed orange juice, no preservatives
```

#### Food Safety Information (NEW!)
```
📅 Manufacture Date:  [Date Picker] → Select: 2024-12-01
📅 Expiry Date:       [Date Picker] → Select: 2024-12-15

💡 These fields are optional but highly recommended for food products!
```

#### Product Image
- Upload a clear, high-quality image (JPG, PNG, WEBP)
- Maximum file size: 5MB
- Shows preview after selection

### Step 3: Add Product Variations (Optional)

Click "Add Variation" to create different options:

#### Example 1: Size Variations
```
┌─────────────────────────────────────────────────┐
│ Variation 1                                  [×]│
│ Type:            Size                            │
│ Value:           Small (250ml)                   │
│ Price Adj (₱):   0.00                            │
│ Stock:           30                              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Variation 2                                  [×]│
│ Type:            Size                            │
│ Value:           Medium (500ml)                  │
│ Price Adj (₱):   30.00                           │
│ Stock:           20                              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Variation 3                                  [×]│
│ Type:            Size                            │
│ Value:           Large (1L)                      │
│ Price Adj (₱):   60.00                           │
│ Stock:           10                              │
└─────────────────────────────────────────────────┘
```

**Result**: Customers will see:
- Small (250ml) - ₱80.00 → 30 available
- Medium (500ml) - ₱110.00 → 20 available
- Large (1L) - ₱140.00 → 10 available

#### Example 2: Flavor Variations
```
┌─────────────────────────────────────────────────┐
│ Variation 1                                  [×]│
│ Type:            Flavor                          │
│ Value:           Original                        │
│ Price Adj (₱):   0.00                            │
│ Stock:           25                              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Variation 2                                  [×]│
│ Type:            Flavor                          │
│ Value:           Mango                           │
│ Price Adj (₱):   10.00                           │
│ Stock:           15                              │
└─────────────────────────────────────────────────┘
```

**Result**: Customers will see:
- Original - ₱80.00 → 25 available
- Mango - ₱90.00 → 15 available

### Step 4: Save Product
Click "Save Product" button at the bottom of the form.

---

## Complete Product Example

Here's a fully filled-out product form for a coffee product:

```
===========================================
      ADD NEW PRODUCT - COFFEE SHOP
===========================================

PRODUCT DETAILS
---------------
Product Name:         Premium Arabica Coffee Beans
Category:             Coffee
Base Price (₱):       250.00
Base Stock:           0
Description:          Single-origin Arabica beans from Benguet.
                      Medium roast with chocolate and caramel notes.

FOOD SAFETY (NEW!)
------------------
📅 Manufacture Date:  December 1, 2024
📅 Expiry Date:       June 1, 2025
💡 Help: Track product freshness for food safety

PRODUCT IMAGE
-------------
[✓] coffee-beans.jpg (2.3 MB)
[Preview showing roasted coffee beans]

VARIATIONS
----------
Variation 1
  Type:         Size
  Value:        250g
  Price Adj:    ₱0.00
  Stock:        30

Variation 2
  Type:         Size
  Value:        500g
  Price Adj:    ₱200.00
  Stock:        20

Variation 3
  Type:         Size
  Value:        1kg
  Price Adj:    ₱450.00
  Stock:        10

Variation 4
  Type:         Grind
  Value:        Whole Bean
  Price Adj:    ₱0.00
  Stock:        25

Variation 5
  Type:         Grind
  Value:        Ground (Medium)
  Price Adj:    ₱10.00
  Stock:        20

Variation 6
  Type:         Grind
  Value:        Ground (Fine)
  Price Adj:    ₱10.00
  Stock:        15

💡 Help: Different variations allow customers to
         choose their preferred option

[Add Variation]  [Save Product]  [Cancel]
===========================================
```

**What customers see**:
- 250g Whole Bean - ₱250.00
- 250g Ground (Medium) - ₱260.00
- 250g Ground (Fine) - ₱260.00
- 500g Whole Bean - ₱450.00
- 500g Ground (Medium) - ₱460.00
- etc.

---

## Tips for Food & Beverage Sellers

### ✅ Best Practices

1. **Always include dates for perishables**
   - Fresh juices: 7-14 days shelf life
   - Baked goods: 3-7 days
   - Packaged foods: Check manufacturer label
   - Coffee/Tea: Several months when sealed

2. **Use variations strategically**
   - Size: For different quantities (250g, 500g, 1kg)
   - Flavor: For different tastes (Original, Chocolate, Vanilla)
   - Type: For different preparations (Whole, Ground, Instant)
   - Package: For different bundle sizes (Single, Pack of 3, Box of 12)

3. **Stock management**
   - Set Base Stock to 0 if ALL items have variations
   - Track each variation's stock separately
   - Update stock after each sale or restock

4. **Pricing variations**
   - Larger sizes usually cost more (positive adjustment)
   - Premium flavors can have higher prices
   - Bulk packages can have discounts (negative adjustment)
   - Standard option should have ₱0.00 adjustment

5. **Product descriptions**
   - Mention ingredients or allergens
   - Include nutritional information if available
   - Specify storage instructions
   - Highlight unique selling points (organic, local, handmade)

### ❌ Common Mistakes to Avoid

1. ❌ Leaving dates blank for food products
   ✅ Always fill manufacture and expiry dates

2. ❌ Inconsistent variation naming
   ✅ Use consistent terms: "Small/Medium/Large" not "Sm/Med/Lg"

3. ❌ Wrong price adjustments
   ✅ Remember: adjustment is ADDED to base price
   - Base: ₱100, Adjustment: ₱20 = Final: ₱120
   - Base: ₱100, Adjustment: -₱10 = Final: ₱90

4. ❌ Forgetting to set variation stock
   ✅ Each variation needs its own stock count

5. ❌ Overlapping variations
   ✅ Make variations clear and distinct
   - Bad: "Small", "Small Size", "Small Pack"
   - Good: "Small (250ml)", "Medium (500ml)", "Large (1L)"

---

## Stock Management Scenarios

### Scenario 1: Simple Product (No Variations)
```
Product: Bottled Water
Base Stock: 100
Variations: None

➜ Customers can buy: 100 units total
```

### Scenario 2: All Variations
```
Product: Flavored Tea
Base Stock: 0
Variations:
  - Green Tea: 30 units
  - Black Tea: 25 units
  - Oolong Tea: 15 units

➜ Customers can buy: 70 units total (30+25+15)
➜ Must select a flavor to purchase
```

### Scenario 3: Mixed Stock
```
Product: Coffee
Base Stock: 10 (generic/unsorted)
Variations:
  - Espresso: 20 units
  - Americano: 15 units

➜ Total available: 45 units (10+20+15)
➜ Can buy generic coffee OR specific variation
```

---

## Editing Products

### To Update Dates
1. Go to "My Products" tab
2. Click "Edit" (✏️) on the product
3. Change manufacture/expiry dates
4. Click "Save Product"

### To Add/Remove Variations
1. Edit the product
2. Existing variations will load automatically
3. Click "Add Variation" for new ones
4. Click [×] to remove unwanted variations
5. Save changes

### To Update Stock
1. Edit the product
2. Modify stock values in:
   - Base Stock field
   - Individual variation stock fields
3. Save changes

---

## Customer View Examples

### Product Card in Shop
```
┌─────────────────────────────────────┐
│  [Product Image]                    │
│                                     │
│  Fresh Orange Juice                 │
│  ₱80.00                             │
│                                     │
│  📅 Mfg: Dec 1, 2024                │
│  📅 Exp: Dec 15, 2024               │
│                                     │
│  Options: Small, Medium, Large      │
│                                     │
│  [Add to Cart]                      │
└─────────────────────────────────────┘
```

### Product Details Modal
```
================================
  FRESH ORANGE JUICE
================================

100% freshly squeezed orange juice
No preservatives, no added sugar

Price: From ₱80.00

📅 Manufacture: December 1, 2024
📅 Expiry: December 15, 2024

Choose Size:
○ Small (250ml) - ₱80.00 ✓ In Stock
○ Medium (500ml) - ₱110.00 ✓ In Stock  
○ Large (1L) - ₱140.00 ✓ In Stock

Quantity: [1] [Add to Cart]

Sold by: Fresh Juice Co.
================================
```

---

## FAQ

**Q: Are dates required?**
A: No, but highly recommended for food/beverage products for safety and compliance.

**Q: Can I change dates after creating a product?**
A: Yes, use the Edit function to update dates anytime.

**Q: What date format should I use?**
A: The date picker handles this automatically. Just select from the calendar.

**Q: Can I add variations later?**
A: Yes, edit the product and add new variations anytime.

**Q: How do I remove a variation?**
A: Click the [×] button on the variation when editing the product.

**Q: Can variations have negative price adjustments?**
A: Yes! Use negative values for discounts. Example: -₱10 for a sale item.

**Q: What happens if a variation runs out of stock?**
A: Customers can't select it, but other variations remain available.

**Q: Can I have both base stock and variations?**
A: Yes, but usually set base stock to 0 if all items have variations.

---

## Need Help?

Contact technical support or refer to:
- Full documentation: `/docs/FOOD_PRODUCT_FEATURES.md`
- API documentation: `/docs/API_DOCUMENTATION.md`
- General guide: `/docs/DOCUMENTATION_INDEX.md`

**Server running at**: http://127.0.0.1:5000

Happy selling! 🛒🍊☕
