"""
Sales System API - Smart Discount Logic for Expiring Products
Handles seller requests, admin approvals, and automatic suggestions
"""
from flask import request, jsonify
from datetime import datetime, timedelta
import math

# ============== DISCOUNT CALCULATION LOGIC ==============

def calculate_smart_discount(product_price, days_until_expiry, cost_ratio=0.65, platform_commission=None):
    """
    Calculate optimal discount that balances seller profit and customer value
    
    Logic:
    - Seller cost estimated at 60-70% of retail price
    - Platform commission from settings (default 10%)
    - Seller needs minimum 10% profit margin to break even
    - Discount increases as expiry approaches
    - Never discount below cost + commission
    
    Args:
        product_price: Original product price
        days_until_expiry: Days remaining until expiry
        cost_ratio: Estimated product cost as % of price (default 65%)
        platform_commission: Platform commission rate as decimal (if None, gets from platform settings)
    
    Returns:
        dict with suggested_discount, sale_price, seller_margin, rationale
    """
    # Get platform commission from settings if not provided
    if platform_commission is None:
        try:
            from backend.server import get_platform_commission_rate
            platform_commission = get_platform_commission_rate()
        except Exception:
            platform_commission = 0.10  # Default 10% if can't get from settings
    
    # Estimate costs
    estimated_cost = product_price * cost_ratio
    commission_amount = product_price * platform_commission
    minimum_price = estimated_cost + commission_amount  # Break-even price
    
    # Calculate discount based on urgency
    if days_until_expiry >= 14:
        # Not urgent, small discount to move inventory
        discount_pct = 10.0
        rationale = "Early discount to promote fresh product"
    elif days_until_expiry >= 10:
        # 10-14 days: moderate discount
        discount_pct = 15.0
        rationale = "Moderate discount - 2 weeks until expiry"
    elif days_until_expiry >= 7:
        # 7-10 days: significant discount
        discount_pct = 20.0
        rationale = "Significant discount - 1 week until expiry"
    elif days_until_expiry >= 5:
        # 5-7 days: steep discount
        discount_pct = 25.0
        rationale = "Steep discount - less than 1 week remaining"
    elif days_until_expiry >= 3:
        # 3-5 days: urgent discount
        discount_pct = 30.0
        rationale = "Urgent discount - expiring very soon"
    elif days_until_expiry >= 1:
        # 1-3 days: maximum discount
        discount_pct = 35.0
        rationale = "Maximum discount - expiring within days"
    else:
        # Last day: clearance
        discount_pct = 40.0
        rationale = "Clearance - expires today/tomorrow"
    
    # Calculate sale price
    sale_price = product_price * (1 - discount_pct / 100.0)
    
    # Ensure we don't go below minimum profitable price
    if sale_price < minimum_price:
        sale_price = minimum_price * 1.10  # Add 10% margin above break-even
        discount_pct = ((product_price - sale_price) / product_price) * 100.0
        rationale += " (adjusted to maintain minimum margin)"
    
    # Calculate actual seller profit margin
    seller_revenue = sale_price * (1 - platform_commission)
    seller_profit = seller_revenue - estimated_cost
    seller_margin_pct = (seller_profit / estimated_cost) * 100.0 if estimated_cost > 0 else 0
    
    return {
        'suggested_discount': round(discount_pct, 2),
        'original_price': round(product_price, 2),
        'sale_price': round(sale_price, 2),
        'seller_profit_margin': round(seller_margin_pct, 2),
        'platform_commission_pct': platform_commission * 100,
        'estimated_cost': round(estimated_cost, 2),
        'seller_revenue': round(seller_revenue, 2),
        'seller_profit': round(seller_profit, 2),
        'rationale': rationale,
        'days_until_expiry': days_until_expiry
    }


def get_expiring_products(seller_id=None, min_days=1, max_days=14):
    """
    Find products expiring within specified timeframe
    
    Args:
        seller_id: Filter by seller (None for all)
        min_days: Minimum days until expiry
        max_days: Maximum days until expiry
    
    Returns:
        List of products with expiry info
    """
    from backend.server import get_db, DB_ENGINE
    
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    min_date = today + timedelta(days=min_days)
    max_date = today + timedelta(days=max_days)
    
    if DB_ENGINE == 'mysql':
        if seller_id:
            query = """
                SELECT id, seller_id, title, price, stock, expiry_date,
                       DATEDIFF(expiry_date, CURDATE()) as days_until_expiry
                FROM products
                WHERE seller_id = %s
                  AND expiry_date IS NOT NULL
                  AND expiry_date BETWEEN %s AND %s
                  AND stock > 0
                  AND id NOT IN (
                      SELECT product_id FROM product_sales 
                      WHERE is_active = 1
                  )
                ORDER BY expiry_date ASC
            """
            cursor.execute(query, (seller_id, min_date, max_date))
        else:
            query = """
                SELECT id, seller_id, title, price, stock, expiry_date,
                       DATEDIFF(expiry_date, CURDATE()) as days_until_expiry
                FROM products
                WHERE expiry_date IS NOT NULL
                  AND expiry_date BETWEEN %s AND %s
                  AND stock > 0
                  AND id NOT IN (
                      SELECT product_id FROM product_sales 
                      WHERE is_active = 1
                  )
                ORDER BY expiry_date ASC
            """
            cursor.execute(query, (min_date, max_date))
    else:
        if seller_id:
            query = """
                SELECT id, seller_id, title, price, stock, expiry_date,
                       CAST((julianday(expiry_date) - julianday('now')) AS INTEGER) as days_until_expiry
                FROM products
                WHERE seller_id = ?
                  AND expiry_date IS NOT NULL
                  AND date(expiry_date) BETWEEN date(?) AND date(?)
                  AND stock > 0
                  AND id NOT IN (
                      SELECT product_id FROM product_sales 
                      WHERE is_active = 1
                  )
                ORDER BY expiry_date ASC
            """
            cursor.execute(query, (seller_id, min_date, max_date))
        else:
            query = """
                SELECT id, seller_id, title, price, stock, expiry_date,
                       CAST((julianday(expiry_date) - julianday('now')) AS INTEGER) as days_until_expiry
                FROM products
                WHERE expiry_date IS NOT NULL
                  AND date(expiry_date) BETWEEN date(?) AND date(?)
                  AND stock > 0
                  AND id NOT IN (
                      SELECT product_id FROM product_sales 
                      WHERE is_active = 1
                  )
                ORDER BY expiry_date ASC
            """
            cursor.execute(query, (min_date, max_date))
    
    rows = cursor.fetchall()
    cursor.close()
    
    products = []
    for row in rows:
        if hasattr(row, 'keys'):
            product = dict(row)
        else:
            product = {
                'id': row[0],
                'seller_id': row[1],
                'title': row[2],
                'price': float(row[3]),
                'stock': row[4],
                'expiry_date': str(row[5]),
                'days_until_expiry': row[6]
            }
        products.append(product)
    
    return products


# This file contains the core logic functions
# API endpoints will be added to backend/server.py
