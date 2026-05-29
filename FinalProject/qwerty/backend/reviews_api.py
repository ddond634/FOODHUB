"""
Customer Reviews API
Handles customer review submission and retrieval
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from backend.auth import role_required
from backend.api_utils import success_response, error_response
import os
import json

reviews_bp = Blueprint('reviews', __name__, url_prefix='/api/customer')

# Get DB_ENGINE from environment
DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def get_db_connection():
    """Get database connection using the same method as server.py"""
    from backend.server import get_db
    return get_db()

@reviews_bp.route('/reviews', methods=['GET'])
@role_required('customer')
def get_customer_reviews():
    """
    Get all reviews submitted by the logged-in customer
    Returns: List of reviews with product/seller details
    """
    try:
        customer_id = g.user_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    r.id,
                    r.order_id,
                    r.product_id,
                    r.seller_id,
                    r.rating,
                    r.comment,
                    r.images,
                    r.created_at,
                    r.updated_at,
                    p.title as product_name,
                    p.img_url as product_image,
                    s.business_name as seller_name,
                    u.first_name as seller_first_name,
                    u.last_name as seller_last_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                JOIN users u ON r.seller_id = u.id
                LEFT JOIN sellers s ON u.id = s.user_id
                WHERE r.customer_id = %s
                ORDER BY r.created_at DESC
            ''', (customer_id,))
        else:
            cursor.execute('''
                SELECT 
                    r.id,
                    r.order_id,
                    r.product_id,
                    r.seller_id,
                    r.rating,
                    r.comment,
                    r.images,
                    r.created_at,
                    r.updated_at,
                    p.title as product_name,
                    p.img_url as product_image,
                    s.business_name as seller_name,
                    u.first_name as seller_first_name,
                    u.last_name as seller_last_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                JOIN users u ON r.seller_id = u.id
                LEFT JOIN sellers s ON u.id = s.user_id
                WHERE r.customer_id = ?
                ORDER BY r.created_at DESC
            ''', (customer_id,))
        
        rows = cursor.fetchall()
        
        reviews = []
        for row in rows:
            if DB_ENGINE == 'mysql':
                review_data = {
                    'id': row['id'],
                    'order_id': row['order_id'],
                    'product_id': row['product_id'],
                    'seller_id': row['seller_id'],
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'images': json.loads(row['images']) if row['images'] else [],
                    'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                    'updated_at': row['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if row['updated_at'] else None,
                    'product_name': row['product_name'],
                    'product_image': row['product_image'],
                    'seller_name': row['seller_name'] or f"{row['seller_first_name']} {row['seller_last_name']}"
                }
            else:
                review_data = {
                    'id': row['id'],
                    'order_id': row['order_id'],
                    'product_id': row['product_id'],
                    'seller_id': row['seller_id'],
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'images': json.loads(row['images']) if row['images'] else [],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'product_name': row['product_name'],
                    'product_image': row['product_image'],
                    'seller_name': row['seller_name'] or f"{row['seller_first_name']} {row['seller_last_name']}"
                }
            
            reviews.append(review_data)
        
        conn.close()
        
        return success_response({
            'reviews': reviews,
            'total': len(reviews)
        })
        
    except Exception as e:
        print(f"Error in get_customer_reviews: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to fetch reviews: {str(e)}", 500)


@reviews_bp.route('/reviews', methods=['POST'])
@role_required('customer')
def submit_review():
    """
    Submit a new review for a delivered order
    Required: order_id, product_id, rating
    Optional: comment, images
    """
    try:
        customer_id = g.user_id
        data = request.get_json()
        
        # Validate required fields
        order_id = data.get('order_id')
        product_id = data.get('product_id')
        rating = data.get('rating')
        
        if not all([order_id, product_id, rating]):
            return error_response("Missing required fields: order_id, product_id, rating", 400)
        
        # Validate rating range
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return error_response("Rating must be between 1 and 5", 400)
        except ValueError:
            return error_response("Invalid rating value", 400)
        
        # Optional fields
        comment = data.get('comment', '').strip()
        images = data.get('images', [])
        
        # Validate comment length
        if comment and len(comment) > 500:
            return error_response("Comment must not exceed 500 characters", 400)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Verify order exists and belongs to customer
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT status, customer_id FROM orders WHERE id = %s
            ''', (order_id,))
        else:
            cursor.execute('''
                SELECT status, customer_id FROM orders WHERE id = ?
            ''', (order_id,))
        
        order = cursor.fetchone()
        
        if not order:
            conn.close()
            return error_response("Order not found", 404)
        
        if DB_ENGINE == 'mysql':
            order_status = order['status']
            order_customer_id = order['customer_id']
        else:
            order_status = order['status']
            order_customer_id = order['customer_id']
        
        if order_customer_id != customer_id:
            conn.close()
            return error_response("Unauthorized: This order does not belong to you", 403)
        
        # 2. Verify order is delivered
        if order_status != 'delivered':
            conn.close()
            return error_response("Reviews can only be submitted for delivered orders", 400)
        
        # 3. Verify product exists in the order
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT oi.product_id, p.seller_id 
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s AND oi.product_id = %s
            ''', (order_id, product_id))
        else:
            cursor.execute('''
                SELECT oi.product_id, p.seller_id 
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ? AND oi.product_id = ?
            ''', (order_id, product_id))
        
        product_info = cursor.fetchone()
        
        if not product_info:
            conn.close()
            return error_response("Product not found in this order", 404)
        
        if DB_ENGINE == 'mysql':
            seller_id = product_info['seller_id']
        else:
            seller_id = product_info['seller_id']
        
        # 4. Check if review already exists
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT id FROM reviews 
                WHERE customer_id = %s AND order_id = %s AND product_id = %s
            ''', (customer_id, order_id, product_id))
        else:
            cursor.execute('''
                SELECT id FROM reviews 
                WHERE customer_id = ? AND order_id = ? AND product_id = ?
            ''', (customer_id, order_id, product_id))
        
        existing_review = cursor.fetchone()
        
        if existing_review:
            conn.close()
            return error_response("You have already reviewed this product", 400)
        
        # 5. Insert review
        images_json = json.dumps(images) if images else None
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                INSERT INTO reviews (customer_id, order_id, product_id, seller_id, rating, comment, images)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (customer_id, order_id, product_id, seller_id, rating, comment or None, images_json))
        else:
            cursor.execute('''
                INSERT INTO reviews (customer_id, order_id, product_id, seller_id, rating, comment, images)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (customer_id, order_id, product_id, seller_id, rating, comment or None, images_json))
        
        review_id = cursor.lastrowid
        conn.commit()
        
        # 6. Optional: Create notification for seller
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    INSERT INTO notifications (user_id, type, message, related_id, is_read)
                    VALUES (%s, 'review', %s, %s, 0)
                ''', (seller_id, f"New {rating}-star review received on your product", review_id))
            else:
                cursor.execute('''
                    INSERT INTO notifications (user_id, type, message, related_id, is_read)
                    VALUES (?, 'review', ?, ?, 0)
                ''', (seller_id, f"New {rating}-star review received on your product", review_id))
            conn.commit()
        except:
            # Notifications are optional, continue if table doesn't exist
            pass
        
        conn.close()
        
        return success_response({
            'review_id': review_id,
            'message': 'Review submitted successfully'
        }, 201)
        
    except Exception as e:
        print(f"Error in submit_review: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to submit review: {str(e)}", 500)


@reviews_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@role_required('customer')
def delete_review(review_id):
    """
    Delete a review (only by the customer who created it)
    """
    try:
        customer_id = g.user_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify review belongs to customer
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT customer_id FROM reviews WHERE id = %s
            ''', (review_id,))
        else:
            cursor.execute('''
                SELECT customer_id FROM reviews WHERE id = ?
            ''', (review_id,))
        
        review = cursor.fetchone()
        
        if not review:
            conn.close()
            return error_response("Review not found", 404)
        
        if DB_ENGINE == 'mysql':
            review_customer_id = review['customer_id']
        else:
            review_customer_id = review['customer_id']
        
        if review_customer_id != customer_id:
            conn.close()
            return error_response("Unauthorized: You can only delete your own reviews", 403)
        
        # Delete review
        if DB_ENGINE == 'mysql':
            cursor.execute('DELETE FROM reviews WHERE id = %s', (review_id,))
        else:
            cursor.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
        
        conn.commit()
        conn.close()
        
        return success_response({'message': 'Review deleted successfully'})
        
    except Exception as e:
        print(f"Error in delete_review: {str(e)}")
        return error_response(f"Failed to delete review: {str(e)}", 500)


@reviews_bp.route('/orders/reviewable', methods=['GET'])
@role_required('customer')
def get_reviewable_orders():
    """
    Get all delivered orders that can be reviewed
    Returns orders with products that haven't been reviewed yet
    """
    try:
        customer_id = g.user_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT DISTINCT
                    o.id as order_id,
                    o.created_at as order_date,
                    oi.product_id,
                    p.title as product_name,
                    p.img_url as product_image,
                    p.seller_id,
                    s.business_name as seller_name,
                    u.first_name as seller_first_name,
                    u.last_name as seller_last_name
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                JOIN users u ON p.seller_id = u.id
                LEFT JOIN sellers s ON u.id = s.user_id
                LEFT JOIN reviews r ON (r.order_id = o.id AND r.product_id = p.id AND r.customer_id = %s)
                WHERE o.customer_id = %s 
                AND o.status = 'delivered'
                AND r.id IS NULL
                ORDER BY o.created_at DESC
            ''', (customer_id, customer_id))
        else:
            cursor.execute('''
                SELECT DISTINCT
                    o.id as order_id,
                    o.created_at as order_date,
                    oi.product_id,
                    p.title as product_name,
                    p.img_url as product_image,
                    p.seller_id,
                    s.business_name as seller_name,
                    u.first_name as seller_first_name,
                    u.last_name as seller_last_name
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                JOIN users u ON p.seller_id = u.id
                LEFT JOIN sellers s ON u.id = s.user_id
                LEFT JOIN reviews r ON (r.order_id = o.id AND r.product_id = p.id AND r.customer_id = ?)
                WHERE o.customer_id = ? 
                AND o.status = 'delivered'
                AND r.id IS NULL
                ORDER BY o.created_at DESC
            ''', (customer_id, customer_id))
        
        rows = cursor.fetchall()
        
        reviewable_items = []
        for row in rows:
            if DB_ENGINE == 'mysql':
                item = {
                    'order_id': row['order_id'],
                    'order_date': row['order_date'].strftime('%Y-%m-%d') if row['order_date'] else None,
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'product_image': row['product_image'],
                    'seller_id': row['seller_id'],
                    'seller_name': row['seller_name'] or f"{row['seller_first_name']} {row['seller_last_name']}"
                }
            else:
                item = {
                    'order_id': row['order_id'],
                    'order_date': row['order_date'],
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'product_image': row['product_image'],
                    'seller_id': row['seller_id'],
                    'seller_name': row['seller_name'] or f"{row['seller_first_name']} {row['seller_last_name']}"
                }
            
            reviewable_items.append(item)
        
        conn.close()
        
        return success_response({
            'reviewable_items': reviewable_items,
            'total': len(reviewable_items)
        })
        
    except Exception as e:
        print(f"Error in get_reviewable_orders: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to fetch reviewable orders: {str(e)}", 500)
