"""
Order Management System
Handles order lifecycle, validations, and state transitions
"""
from backend.db_pool import transaction, get_db_connection, DB_ENGINE
from backend.error_handler import BusinessLogicError, ValidationError, db_logger
from backend.stock_manager import StockManager
from datetime import datetime


class OrderManager:
    """Centralized order management"""
    
    # Valid order status transitions
    STATUS_TRANSITIONS = {
        'placed': ['processing', 'cancelled'],
        'processing': ['dispatched', 'cancelled'],
        'dispatched': ['delivered', 'cancelled'],
        'delivered': [],  # Terminal state
        'cancelled': []   # Terminal state
    }
    
    @staticmethod
    def create_order(customer_data, items, payment_method, delivery_method, customer_id=None):
        """
        Create a new order with proper validation and stock reservation
        
        Args:
            customer_data: Dict with name, phone, address
            items: List of dicts with product_id, quantity, price, variation_id (optional)
            payment_method: Payment method string
            delivery_method: Delivery method string
            customer_id: Optional customer user ID
        
        Returns:
            order_id
        """
        # Validate inputs
        if not customer_data.get('name'):
            raise ValidationError("Customer name is required")
        
        if not customer_data.get('phone'):
            raise ValidationError("Customer phone is required")
        
        if not customer_data.get('address'):
            raise ValidationError("Customer address is required")
        
        if not items or len(items) == 0:
            raise ValidationError("Order must contain at least one item")
        
        try:
            with transaction() as (conn, cursor):
                # Calculate totals
                subtotal = sum(float(item['price']) * int(item['quantity']) for item in items)
                delivery_fee = OrderManager._calculate_delivery_fee(delivery_method)
                total = subtotal + delivery_fee
                
                # Create order
                if DB_ENGINE == 'mysql':
                    cursor.execute(
                        '''INSERT INTO orders 
                           (customer_id, customer_name, customer_phone, customer_address, 
                            subtotal, delivery_fee, total, payment, status, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())''',
                        (customer_id, customer_data['name'], customer_data['phone'],
                         customer_data['address'], subtotal, delivery_fee, total,
                         payment_method, 'placed')
                    )
                else:
                    cursor.execute(
                        '''INSERT INTO orders 
                           (customer_id, customer_name, customer_phone, customer_address, 
                            subtotal, delivery_fee, total, payment, status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (customer_id, customer_data['name'], customer_data['phone'],
                         customer_data['address'], subtotal, delivery_fee, total,
                         payment_method, 'placed', datetime.now().isoformat())
                    )
                
                order_id = cursor.lastrowid
                
                # Add order items and reserve stock
                for item in items:
                    product_id = int(item['product_id'])
                    quantity = int(item['quantity'])
                    price = float(item['price'])
                    variation_id = item.get('variation_id')
                    
                    # Validate stock availability and reserve
                    try:
                        StockManager.reserve_stock(
                            product_id, quantity, variation_id, order_id
                        )
                    except BusinessLogicError as e:
                        # Get product title for error message
                        if DB_ENGINE == 'mysql':
                            cursor.execute('SELECT title FROM products WHERE id = %s', (product_id,))
                        else:
                            cursor.execute('SELECT title FROM products WHERE id = ?', (product_id,))
                        
                        product = cursor.fetchone()
                        product_title = product['title'] if product else f'Product #{product_id}'
                        
                        raise ValidationError(
                            f"Insufficient stock for {product_title}. {str(e)}"
                        )
                    
                    # Insert order item
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            '''INSERT INTO order_items 
                               (order_id, product_id, quantity, price) 
                               VALUES (%s, %s, %s, %s)''',
                            (order_id, product_id, quantity, price)
                        )
                    else:
                        cursor.execute(
                            '''INSERT INTO order_items 
                               (order_id, product_id, quantity, price) 
                               VALUES (?, ?, ?, ?)''',
                            (order_id, product_id, quantity, price)
                        )
                
                db_logger.info(f"Created order #{order_id} with {len(items)} items")
                
                return order_id
        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            db_logger.error(f"Error creating order: {e}")
            raise BusinessLogicError(f"Failed to create order: {str(e)}")
    
    @staticmethod
    def update_order_status(order_id, new_status, updated_by=None):
        """
        Update order status with validation of state transitions
        
        Args:
            order_id: Order ID
            new_status: New status
            updated_by: User ID making the change
        
        Returns:
            True if successful
        """
        valid_statuses = ['placed', 'processing', 'dispatched', 'delivered', 'cancelled']
        
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status: {new_status}")
        
        try:
            with transaction() as (conn, cursor):
                # Get current status
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT status FROM orders WHERE id = %s', (order_id,))
                else:
                    cursor.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
                
                result = cursor.fetchone()
                
                if not result:
                    raise BusinessLogicError(f"Order #{order_id} not found")
                
                current_status = result['status'] if isinstance(result, dict) else result[0]
                
                # Validate transition
                if new_status not in OrderManager.STATUS_TRANSITIONS.get(current_status, []):
                    if current_status == new_status:
                        return True  # Already in the desired state
                    
                    raise BusinessLogicError(
                        f"Cannot transition order from '{current_status}' to '{new_status}'"
                    )
                
                # Update status
                if DB_ENGINE == 'mysql':
                    cursor.execute(
                        'UPDATE orders SET status = %s WHERE id = %s',
                        (new_status, order_id)
                    )
                else:
                    cursor.execute(
                        'UPDATE orders SET status = ? WHERE id = ?',
                        (new_status, order_id)
                    )
                
                db_logger.info(
                    f"Order #{order_id} status updated: {current_status} -> {new_status}"
                    f"{f' by user #{updated_by}' if updated_by else ''}"
                )
                
                return True
        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            db_logger.error(f"Error updating order status: {e}")
            raise BusinessLogicError(f"Failed to update order status: {str(e)}")
    
    @staticmethod
    def cancel_order(order_id, reason=None, cancelled_by=None):
        """
        Cancel an order and release stock
        
        Args:
            order_id: Order ID
            reason: Cancellation reason
            cancelled_by: User ID who cancelled
        
        Returns:
            True if successful
        """
        try:
            with transaction() as (conn, cursor):
                # Get order details
                if DB_ENGINE == 'mysql':
                    cursor.execute(
                        'SELECT status FROM orders WHERE id = %s',
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        'SELECT status FROM orders WHERE id = ?',
                        (order_id,)
                    )
                
                result = cursor.fetchone()
                
                if not result:
                    raise BusinessLogicError(f"Order #{order_id} not found")
                
                current_status = result['status'] if isinstance(result, dict) else result[0]
                
                # Check if order can be cancelled
                if current_status in ['delivered', 'cancelled']:
                    raise BusinessLogicError(
                        f"Cannot cancel order with status '{current_status}'"
                    )
                
                # Get order items to release stock
                if DB_ENGINE == 'mysql':
                    cursor.execute(
                        'SELECT product_id, quantity FROM order_items WHERE order_id = %s',
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        'SELECT product_id, quantity FROM order_items WHERE order_id = ?',
                        (order_id,)
                    )
                
                items = cursor.fetchall()
                
                # Release stock for each item
                for item in items:
                    product_id = item['product_id'] if isinstance(item, dict) else item[0]
                    quantity = item['quantity'] if isinstance(item, dict) else item[1]
                    
                    try:
                        StockManager.release_stock(
                            product_id, quantity, None,
                            f"Order #{order_id} cancelled: {reason or 'No reason'}"
                        )
                    except Exception as e:
                        db_logger.warning(
                            f"Failed to release stock for product {product_id}: {e}"
                        )
                
                # Update order status
                if DB_ENGINE == 'mysql':
                    cursor.execute(
                        'UPDATE orders SET status = %s WHERE id = %s',
                        ('cancelled', order_id)
                    )
                else:
                    cursor.execute(
                        'UPDATE orders SET status = ? WHERE id = ?',
                        ('cancelled', order_id)
                    )
                
                db_logger.info(
                    f"Order #{order_id} cancelled. Reason: {reason or 'Not specified'}"
                    f"{f' by user #{cancelled_by}' if cancelled_by else ''}"
                )
                
                return True
        except BusinessLogicError:
            raise
        except Exception as e:
            db_logger.error(f"Error cancelling order: {e}")
            raise BusinessLogicError(f"Failed to cancel order: {str(e)}")
    
    @staticmethod
    def _calculate_delivery_fee(delivery_method):
        """Calculate delivery fee based on method"""
        fees = {
            'standard': 50.0,
            'express': 100.0,
            'pickup': 0.0,
            'same-day': 150.0
        }
        
        return fees.get(delivery_method, 50.0)
    
    @staticmethod
    def get_order_details(order_id):
        """Get complete order details including items"""
        try:
            with get_db_connection() as (conn, cursor):
                # Get order
                if DB_ENGINE == 'mysql':
                    cursor.execute(
                        '''SELECT * FROM orders WHERE id = %s''',
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        '''SELECT * FROM orders WHERE id = ?''',
                        (order_id,)
                    )
                
                order = cursor.fetchone()
                
                if not order:
                    return None
                
                # Get order items
                if DB_ENGINE == 'mysql':
                    cursor.execute(
                        '''SELECT oi.*, p.title, p.img_url 
                           FROM order_items oi
                           LEFT JOIN products p ON oi.product_id = p.id
                           WHERE oi.order_id = %s''',
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        '''SELECT oi.*, p.title, p.img_url 
                           FROM order_items oi
                           LEFT JOIN products p ON oi.product_id = p.id
                           WHERE oi.order_id = ?''',
                        (order_id,)
                    )
                
                items = cursor.fetchall()
                
                # Convert to dict
                order_dict = dict(order) if hasattr(order, 'keys') else {
                    'id': order[0], 'customer_id': order[1], 'customer_name': order[2],
                    'customer_phone': order[3], 'customer_address': order[4],
                    'subtotal': order[5], 'delivery_fee': order[6], 'total': order[7],
                    'payment': order[8], 'status': order[9], 'created_at': order[10]
                }
                
                order_dict['items'] = [dict(item) if hasattr(item, 'keys') else item for item in items]
                
                return order_dict
        except Exception as e:
            db_logger.error(f"Error getting order details: {e}")
            return None


# Export
__all__ = ['OrderManager']
