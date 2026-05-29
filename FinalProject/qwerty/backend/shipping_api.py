"""
Shipping Preferences API
Handles seller shipping settings and checkout calculations
"""

from flask import Blueprint, request, jsonify, g
from backend.auth import role_required
from backend.api_utils import success_response, error_response
import os

shipping_bp = Blueprint('shipping', __name__, url_prefix='/api')

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def get_db():
    """Get database connection from Flask g object"""
    if not hasattr(g, 'db'):
        import pymysql
        import sqlite3
        
        if DB_ENGINE == 'mysql':
            g.db = pymysql.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASSWORD', ''),
                database=os.environ.get('DB_NAME', 'qwerty'),
                port=int(os.environ.get('DB_PORT', 3306)),
                cursorclass=pymysql.cursors.DictCursor
            )
        else:
            g.db = sqlite3.connect('qwerty.db')
            g.db.row_factory = sqlite3.Row
    
    return g.db

@shipping_bp.route('/seller/settings/shipping', methods=['GET'])
@role_required('seller')
def get_shipping_settings():
    """
    Get seller's current shipping preferences
    """
    try:
        seller_id = g.user_id
        
        conn = get_db()
        cursor = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    s.id,
                    s.business_name,
                    s.free_shipping_threshold,
                    s.standard_shipping_fee
                FROM sellers s
                WHERE s.user_id = %s
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT 
                    s.id,
                    s.business_name,
                    s.free_shipping_threshold,
                    s.standard_shipping_fee
                FROM sellers s
                WHERE s.user_id = ?
            ''', (seller_id,))
        
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller not found', 404)
        
        return success_response({
            'seller_id': seller['id'],
            'business_name': seller['business_name'],
            'free_shipping_threshold': float(seller['free_shipping_threshold']) if seller['free_shipping_threshold'] else 500.00,
            'standard_shipping_fee': float(seller['standard_shipping_fee']) if seller['standard_shipping_fee'] else 50.00
        })
        
    except Exception as e:
        return error_response(f'Failed to fetch shipping settings: {str(e)}', 500)

@shipping_bp.route('/seller/settings/shipping', methods=['POST'])
@role_required('seller')
def update_shipping_settings():
    """
    Update seller's shipping preferences
    """
    try:
        seller_id = g.user_id
        data = request.get_json()
        
        free_shipping_threshold = data.get('free_shipping_threshold')
        standard_shipping_fee = data.get('standard_shipping_fee')
        
        # Validation
        if free_shipping_threshold is None or standard_shipping_fee is None:
            return error_response('Both free_shipping_threshold and standard_shipping_fee are required', 400)
        
        try:
            free_shipping_threshold = float(free_shipping_threshold)
            standard_shipping_fee = float(standard_shipping_fee)
        except (ValueError, TypeError):
            return error_response('Shipping values must be valid numbers', 400)
        
        if free_shipping_threshold < 0 or standard_shipping_fee < 0:
            return error_response('Shipping values cannot be negative', 400)
        
        if standard_shipping_fee > 10000:
            return error_response('Standard shipping fee seems too high (max ₱10,000)', 400)
        
        if free_shipping_threshold > 1000000:
            return error_response('Free shipping threshold seems too high (max ₱1,000,000)', 400)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get seller ID from user ID
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM sellers WHERE user_id = %s', (seller_id,))
        else:
            cursor.execute('SELECT id FROM sellers WHERE user_id = ?', (seller_id,))
        
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller not found', 404)
        
        # Update shipping settings
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE sellers 
                SET free_shipping_threshold = %s,
                    standard_shipping_fee = %s
                WHERE user_id = %s
            ''', (free_shipping_threshold, standard_shipping_fee, seller_id))
        else:
            cursor.execute('''
                UPDATE sellers 
                SET free_shipping_threshold = ?,
                    standard_shipping_fee = ?
                WHERE user_id = ?
            ''', (free_shipping_threshold, standard_shipping_fee, seller_id))
        
        conn.commit()
        
        return success_response({
            'message': 'Shipping settings updated successfully',
            'free_shipping_threshold': free_shipping_threshold,
            'standard_shipping_fee': standard_shipping_fee
        })
        
    except Exception as e:
        return error_response(f'Failed to update shipping settings: {str(e)}', 500)

@shipping_bp.route('/store/<int:store_id>/shipping', methods=['GET'])
def get_store_shipping(store_id):
    """
    Get shipping preferences for a specific store (for checkout calculations)
    Public endpoint - customers need this for checkout
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    id,
                    business_name,
                    free_shipping_threshold,
                    standard_shipping_fee
                FROM sellers
                WHERE id = %s
            ''', (store_id,))
        else:
            cursor.execute('''
                SELECT 
                    id,
                    business_name,
                    free_shipping_threshold,
                    standard_shipping_fee
                FROM sellers
                WHERE id = ?
            ''', (store_id,))
        
        store = cursor.fetchone()
        
        if not store:
            return error_response('Store not found', 404)
        
        return success_response({
            'store_id': store['id'],
            'business_name': store['business_name'],
            'free_shipping_threshold': float(store['free_shipping_threshold']) if store['free_shipping_threshold'] else 500.00,
            'standard_shipping_fee': float(store['standard_shipping_fee']) if store['standard_shipping_fee'] else 50.00
        })
        
    except Exception as e:
        return error_response(f'Failed to fetch store shipping info: {str(e)}', 500)

@shipping_bp.route('/checkout/calculate-shipping', methods=['POST'])
def calculate_shipping():
    """
    Calculate shipping costs for checkout
    Accepts cart items grouped by store
    """
    try:
        data = request.get_json()
        stores = data.get('stores', [])  # Array of {store_id, items: [{product_id, quantity, price}]}
        
        if not stores:
            return error_response('No stores provided', 400)
        
        conn = get_db()
        cursor = conn.cursor()
        
        shipping_breakdown = []
        total_shipping = 0
        
        for store_data in stores:
            store_id = store_data.get('store_id')
            items = store_data.get('items', [])
            
            if not store_id or not items:
                continue
            
            # Get store shipping settings
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT 
                        id,
                        business_name,
                        free_shipping_threshold,
                        standard_shipping_fee
                    FROM sellers
                    WHERE id = %s
                ''', (int(store_id),))
            else:
                cursor.execute('''
                    SELECT 
                        id,
                        business_name,
                        free_shipping_threshold,
                        standard_shipping_fee
                    FROM sellers
                    WHERE id = ?
                ''', (int(store_id),))
            
            store = cursor.fetchone()
            
            if not store:
                continue
            
            # Calculate subtotal for this store
            subtotal = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in items)
            total_items = sum(int(item.get('quantity', 1)) for item in items)
            
            free_threshold = float(store['free_shipping_threshold']) if store['free_shipping_threshold'] else 500.00
            shipping_fee = float(store['standard_shipping_fee']) if store['standard_shipping_fee'] else 50.00
            
            # Apply shipping logic
            if subtotal >= free_threshold:
                store_shipping = 0
                free_shipping = True
            else:
                store_shipping = shipping_fee * total_items
                free_shipping = False
            
            shipping_breakdown.append({
                'store_id': store['id'],
                'store_name': store['business_name'],
                'subtotal': round(subtotal, 2),
                'items_count': total_items,
                'shipping_fee': round(store_shipping, 2),
                'free_shipping': free_shipping,
                'free_shipping_threshold': round(free_threshold, 2),
                'amount_until_free_shipping': round(max(0, free_threshold - subtotal), 2) if not free_shipping else 0
            })
            
            total_shipping += store_shipping
        
        return success_response({
            'stores': shipping_breakdown,
            'total_shipping': round(total_shipping, 2),
            'calculation_timestamp': g.get('request_time', None)
        })
        
    except Exception as e:
        return error_response(f'Failed to calculate shipping: {str(e)}', 500)
