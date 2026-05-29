"""
Inventory and Stock Management System
Handles stock tracking, reservations, and inventory consistency
"""
from backend.db_pool import transaction, get_db_connection, DB_ENGINE
from backend.error_handler import BusinessLogicError, db_logger
from datetime import datetime


class StockManager:
    """Centralized stock management"""
    
    @staticmethod
    def check_stock_availability(product_id, quantity, variation_id=None):
        """
        Check if sufficient stock is available
        Returns: (available, current_stock)
        """
        try:
            with get_db_connection() as (conn, cursor):
                if variation_id:
                    # Check variation stock
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            'SELECT stock FROM product_variations WHERE id = %s AND product_id = %s',
                            (variation_id, product_id)
                        )
                    else:
                        cursor.execute(
                            'SELECT stock FROM product_variations WHERE id = ? AND product_id = ?',
                            (variation_id, product_id)
                        )
                else:
                    # Check product stock
                    if DB_ENGINE == 'mysql':
                        cursor.execute('SELECT stock FROM products WHERE id = %s', (product_id,))
                    else:
                        cursor.execute('SELECT stock FROM products WHERE id = ?', (product_id,))
                
                result = cursor.fetchone()
                
                if not result:
                    return False, 0
                
                current_stock = result['stock'] if isinstance(result, dict) else result[0]
                return current_stock >= quantity, current_stock
        except Exception as e:
            db_logger.error(f"Error checking stock: {e}")
            return False, 0
    
    @staticmethod
    def reserve_stock(product_id, quantity, variation_id=None, order_id=None):
        """
        Reserve stock for an order (decrease stock)
        Returns: True if successful, raises BusinessLogicError if not
        """
        try:
            with transaction() as (conn, cursor):
                # Check and reserve stock atomically
                available, current_stock = StockManager.check_stock_availability(
                    product_id, quantity, variation_id
                )
                
                if not available:
                    raise BusinessLogicError(
                        f"Insufficient stock. Requested: {quantity}, Available: {current_stock}",
                        error_code='INSUFFICIENT_STOCK'
                    )
                
                # Decrease stock
                new_stock = current_stock - quantity
                
                if variation_id:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            'UPDATE product_variations SET stock = %s WHERE id = %s AND product_id = %s',
                            (new_stock, variation_id, product_id)
                        )
                    else:
                        cursor.execute(
                            'UPDATE product_variations SET stock = ? WHERE id = ? AND product_id = ?',
                            (new_stock, variation_id, product_id)
                        )
                else:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            'UPDATE products SET stock = %s WHERE id = %s',
                            (new_stock, product_id)
                        )
                    else:
                        cursor.execute(
                            'UPDATE products SET stock = ? WHERE id = ?',
                            (new_stock, product_id)
                        )
                
                # Log inventory movement
                StockManager._log_inventory_movement(
                    cursor, product_id, -quantity, 'sale', f'Order #{order_id}' if order_id else None
                )
                
                db_logger.info(
                    f"Reserved {quantity} units of product {product_id}"
                    f"{f' (variation {variation_id})' if variation_id else ''}"
                )
                
                return True
        except BusinessLogicError:
            raise
        except Exception as e:
            db_logger.error(f"Error reserving stock: {e}")
            raise BusinessLogicError(f"Failed to reserve stock: {str(e)}")
    
    @staticmethod
    def release_stock(product_id, quantity, variation_id=None, reason=None):
        """
        Release reserved stock (increase stock back)
        Used for order cancellations or refunds
        """
        try:
            with transaction() as (conn, cursor):
                # Get current stock
                if variation_id:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            'SELECT stock FROM product_variations WHERE id = %s AND product_id = %s',
                            (variation_id, product_id)
                        )
                    else:
                        cursor.execute(
                            'SELECT stock FROM product_variations WHERE id = ? AND product_id = ?',
                            (variation_id, product_id)
                        )
                else:
                    if DB_ENGINE == 'mysql':
                        cursor.execute('SELECT stock FROM products WHERE id = %s', (product_id,))
                    else:
                        cursor.execute('SELECT stock FROM products WHERE id = ?', (product_id,))
                
                result = cursor.fetchone()
                
                if not result:
                    raise BusinessLogicError(f"Product {product_id} not found")
                
                current_stock = result['stock'] if isinstance(result, dict) else result[0]
                new_stock = current_stock + quantity
                
                # Increase stock
                if variation_id:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            'UPDATE product_variations SET stock = %s WHERE id = %s AND product_id = %s',
                            (new_stock, variation_id, product_id)
                        )
                    else:
                        cursor.execute(
                            'UPDATE product_variations SET stock = ? WHERE id = ? AND product_id = ?',
                            (new_stock, variation_id, product_id)
                        )
                else:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            'UPDATE products SET stock = %s WHERE id = %s',
                            (new_stock, product_id)
                        )
                    else:
                        cursor.execute(
                            'UPDATE products SET stock = ? WHERE id = ?',
                            (new_stock, product_id)
                        )
                
                # Log inventory movement
                StockManager._log_inventory_movement(
                    cursor, product_id, quantity, 'adjustment', reason or 'Stock release'
                )
                
                db_logger.info(
                    f"Released {quantity} units of product {product_id}"
                    f"{f' (variation {variation_id})' if variation_id else ''}"
                )
                
                return True
        except Exception as e:
            db_logger.error(f"Error releasing stock: {e}")
            raise BusinessLogicError(f"Failed to release stock: {str(e)}")
    
    @staticmethod
    def _log_inventory_movement(cursor, product_id, quantity, movement_type, reference):
        """Log inventory movement for audit trail"""
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute(
                    '''INSERT INTO inventory_movements 
                       (product_id, qty, movement_type, ref, created_at) 
                       VALUES (%s, %s, %s, %s, NOW())''',
                    (product_id, quantity, movement_type, reference)
                )
            else:
                cursor.execute(
                    '''INSERT INTO inventory_movements 
                       (product_id, qty, movement_type, ref, created_at) 
                       VALUES (?, ?, ?, ?, ?)''',
                    (product_id, quantity, movement_type, reference, datetime.now().isoformat())
                )
        except Exception as e:
            # Don't fail the transaction if logging fails
            db_logger.warning(f"Failed to log inventory movement: {e}")
    
    @staticmethod
    def get_low_stock_products(threshold=10, seller_id=None):
        """Get products with low stock"""
        try:
            with get_db_connection() as (conn, cursor):
                if seller_id:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            '''SELECT id, title, stock, category 
                               FROM products 
                               WHERE seller_id = %s AND stock <= %s AND stock > 0
                               ORDER BY stock ASC''',
                            (seller_id, threshold)
                        )
                    else:
                        cursor.execute(
                            '''SELECT id, title, stock, category 
                               FROM products 
                               WHERE seller_id = ? AND stock <= ? AND stock > 0
                               ORDER BY stock ASC''',
                            (seller_id, threshold)
                        )
                else:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            '''SELECT id, title, stock, category, seller_id 
                               FROM products 
                               WHERE stock <= %s AND stock > 0
                               ORDER BY stock ASC''',
                            (threshold,)
                        )
                    else:
                        cursor.execute(
                            '''SELECT id, title, stock, category, seller_id 
                               FROM products 
                               WHERE stock <= ? AND stock > 0
                               ORDER BY stock ASC''',
                            (threshold,)
                        )
                
                return cursor.fetchall()
        except Exception as e:
            db_logger.error(f"Error fetching low stock products: {e}")
            return []
    
    @staticmethod
    def get_out_of_stock_products(seller_id=None):
        """Get products that are out of stock"""
        try:
            with get_db_connection() as (conn, cursor):
                if seller_id:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            '''SELECT id, title, category 
                               FROM products 
                               WHERE seller_id = %s AND stock = 0
                               ORDER BY title ASC''',
                            (seller_id,)
                        )
                    else:
                        cursor.execute(
                            '''SELECT id, title, category 
                               FROM products 
                               WHERE seller_id = ? AND stock = 0
                               ORDER BY title ASC''',
                            (seller_id,)
                        )
                else:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            '''SELECT id, title, category, seller_id 
                               FROM products 
                               WHERE stock = 0
                               ORDER BY title ASC'''
                        )
                    else:
                        cursor.execute(
                            '''SELECT id, title, category, seller_id 
                               FROM products 
                               WHERE stock = 0
                               ORDER BY title ASC'''
                        )
                
                return cursor.fetchall()
        except Exception as e:
            db_logger.error(f"Error fetching out of stock products: {e}")
            return []


# Export
__all__ = ['StockManager']
