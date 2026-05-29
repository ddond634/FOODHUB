"""
Seller Ratings API
Provides seller rating analytics and statistics based on customer reviews
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from backend.auth import role_required
from backend.api_utils import success_response, error_response
import os

ratings_bp = Blueprint('ratings', __name__, url_prefix='/api/sellers')

# Get DB_ENGINE from environment
DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def get_db_connection():
    """Get database connection using the same method as server.py"""
    from backend.server import get_db
    return get_db()


@ratings_bp.route('/<int:seller_id>/ratings', methods=['GET'])
def get_seller_ratings(seller_id):
    """
    Get comprehensive rating statistics for a seller
    Returns: overall rating, total reviews, star breakdown, recent reviews
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get overall rating statistics
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_reviews,
                    COALESCE(AVG(rating), 0) as average_rating,
                    COALESCE(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END), 0) as five_star,
                    COALESCE(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END), 0) as four_star,
                    COALESCE(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END), 0) as three_star,
                    COALESCE(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END), 0) as two_star,
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as one_star
                FROM reviews
                WHERE seller_id = %s
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_reviews,
                    COALESCE(AVG(rating), 0) as average_rating,
                    COALESCE(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END), 0) as five_star,
                    COALESCE(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END), 0) as four_star,
                    COALESCE(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END), 0) as three_star,
                    COALESCE(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END), 0) as two_star,
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as one_star
                FROM reviews
                WHERE seller_id = ?
            ''', (seller_id,))
        
        result = cursor.fetchone()
        
        if DB_ENGINE == 'mysql':
            total_reviews = int(result['total_reviews'])
            average_rating = float(result['average_rating'])
            five_star = int(result['five_star'])
            four_star = int(result['four_star'])
            three_star = int(result['three_star'])
            two_star = int(result['two_star'])
            one_star = int(result['one_star'])
        else:
            total_reviews = int(result['total_reviews'])
            average_rating = float(result['average_rating'])
            five_star = int(result['five_star'])
            four_star = int(result['four_star'])
            three_star = int(result['three_star'])
            two_star = int(result['two_star'])
            one_star = int(result['one_star'])
        
        # Calculate percentages
        if total_reviews > 0:
            five_star_percent = round((five_star / total_reviews) * 100, 1)
            four_star_percent = round((four_star / total_reviews) * 100, 1)
            three_star_percent = round((three_star / total_reviews) * 100, 1)
            two_star_percent = round((two_star / total_reviews) * 100, 1)
            one_star_percent = round((one_star / total_reviews) * 100, 1)
        else:
            five_star_percent = 0
            four_star_percent = 0
            three_star_percent = 0
            two_star_percent = 0
            one_star_percent = 0
        
        # Get recent reviews (last 5)
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    r.rating,
                    r.comment,
                    r.created_at,
                    p.title as product_name,
                    u.first_name,
                    u.last_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                JOIN users u ON r.customer_id = u.id
                WHERE r.seller_id = %s
                ORDER BY r.created_at DESC
                LIMIT 5
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT 
                    r.rating,
                    r.comment,
                    r.created_at,
                    p.title as product_name,
                    u.first_name,
                    u.last_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                JOIN users u ON r.customer_id = u.id
                WHERE r.seller_id = ?
                ORDER BY r.created_at DESC
                LIMIT 5
            ''', (seller_id,))
        
        recent_reviews_rows = cursor.fetchall()
        recent_reviews = []
        
        for row in recent_reviews_rows:
            if DB_ENGINE == 'mysql':
                review = {
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                    'product_name': row['product_name'],
                    'customer_name': f"{row['first_name']} {row['last_name']}"
                }
            else:
                review = {
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'created_at': row['created_at'],
                    'product_name': row['product_name'],
                    'customer_name': f"{row['first_name']} {row['last_name']}"
                }
            recent_reviews.append(review)
        
        conn.close()
        
        return success_response({
            'overall_rating': round(average_rating, 2),
            'total_reviews': total_reviews,
            'rating_breakdown': {
                '5': {
                    'count': five_star,
                    'percentage': five_star_percent
                },
                '4': {
                    'count': four_star,
                    'percentage': four_star_percent
                },
                '3': {
                    'count': three_star,
                    'percentage': three_star_percent
                },
                '2': {
                    'count': two_star,
                    'percentage': two_star_percent
                },
                '1': {
                    'count': one_star,
                    'percentage': one_star_percent
                }
            },
            'recent_reviews': recent_reviews
        })
        
    except Exception as e:
        print(f"Error in get_seller_ratings: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to fetch seller ratings: {str(e)}", 500)


@ratings_bp.route('/my-ratings', methods=['GET'])
@role_required('seller')
def get_my_ratings():
    """
    Get rating statistics for the logged-in seller
    """
    try:
        seller_id = g.user_id
        
        # Use the same logic as get_seller_ratings
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_reviews,
                    COALESCE(AVG(rating), 0) as average_rating,
                    COALESCE(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END), 0) as five_star,
                    COALESCE(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END), 0) as four_star,
                    COALESCE(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END), 0) as three_star,
                    COALESCE(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END), 0) as two_star,
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as one_star
                FROM reviews
                WHERE seller_id = %s
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_reviews,
                    COALESCE(AVG(rating), 0) as average_rating,
                    COALESCE(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END), 0) as five_star,
                    COALESCE(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END), 0) as four_star,
                    COALESCE(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END), 0) as three_star,
                    COALESCE(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END), 0) as two_star,
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as one_star
                FROM reviews
                WHERE seller_id = ?
            ''', (seller_id,))
        
        result = cursor.fetchone()
        
        if DB_ENGINE == 'mysql':
            total_reviews = int(result['total_reviews'])
            average_rating = float(result['average_rating'])
            five_star = int(result['five_star'])
            four_star = int(result['four_star'])
            three_star = int(result['three_star'])
            two_star = int(result['two_star'])
            one_star = int(result['one_star'])
        else:
            total_reviews = int(result['total_reviews'])
            average_rating = float(result['average_rating'])
            five_star = int(result['five_star'])
            four_star = int(result['four_star'])
            three_star = int(result['three_star'])
            two_star = int(result['two_star'])
            one_star = int(result['one_star'])
        
        # Calculate percentages
        if total_reviews > 0:
            five_star_percent = round((five_star / total_reviews) * 100, 1)
            four_star_percent = round((four_star / total_reviews) * 100, 1)
            three_star_percent = round((three_star / total_reviews) * 100, 1)
            two_star_percent = round((two_star / total_reviews) * 100, 1)
            one_star_percent = round((one_star / total_reviews) * 100, 1)
        else:
            five_star_percent = 0
            four_star_percent = 0
            three_star_percent = 0
            two_star_percent = 0
            one_star_percent = 0
        
        # Get all reviews for the seller
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    r.id,
                    r.rating,
                    r.comment,
                    r.created_at,
                    p.title as product_name,
                    p.img_url as product_image,
                    u.first_name,
                    u.last_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                JOIN users u ON r.customer_id = u.id
                WHERE r.seller_id = %s
                ORDER BY r.created_at DESC
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT 
                    r.id,
                    r.rating,
                    r.comment,
                    r.created_at,
                    p.title as product_name,
                    p.img_url as product_image,
                    u.first_name,
                    u.last_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                JOIN users u ON r.customer_id = u.id
                WHERE r.seller_id = ?
                ORDER BY r.created_at DESC
            ''', (seller_id,))
        
        reviews_rows = cursor.fetchall()
        reviews = []
        
        for row in reviews_rows:
            if DB_ENGINE == 'mysql':
                review = {
                    'id': row['id'],
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                    'product_name': row['product_name'],
                    'product_image': row['product_image'],
                    'customer_name': f"{row['first_name']} {row['last_name']}"
                }
            else:
                review = {
                    'id': row['id'],
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'created_at': row['created_at'],
                    'product_name': row['product_name'],
                    'product_image': row['product_image'],
                    'customer_name': f"{row['first_name']} {row['last_name']}"
                }
            reviews.append(review)
        
        conn.close()
        
        return success_response({
            'overall_rating': round(average_rating, 2),
            'total_reviews': total_reviews,
            'rating_breakdown': {
                '5': {
                    'count': five_star,
                    'percentage': five_star_percent
                },
                '4': {
                    'count': four_star,
                    'percentage': four_star_percent
                },
                '3': {
                    'count': three_star,
                    'percentage': three_star_percent
                },
                '2': {
                    'count': two_star,
                    'percentage': two_star_percent
                },
                '1': {
                    'count': one_star,
                    'percentage': one_star_percent
                }
            },
            'reviews': reviews
        })
        
    except Exception as e:
        print(f"Error in get_my_ratings: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to fetch ratings: {str(e)}", 500)


@ratings_bp.route('/products/<int:product_id>/ratings', methods=['GET'])
def get_product_ratings(product_id):
    """
    Get rating statistics for a specific product
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_reviews,
                    COALESCE(AVG(rating), 0) as average_rating,
                    COALESCE(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END), 0) as five_star,
                    COALESCE(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END), 0) as four_star,
                    COALESCE(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END), 0) as three_star,
                    COALESCE(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END), 0) as two_star,
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as one_star
                FROM reviews
                WHERE product_id = %s
            ''', (product_id,))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_reviews,
                    COALESCE(AVG(rating), 0) as average_rating,
                    COALESCE(SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END), 0) as five_star,
                    COALESCE(SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END), 0) as four_star,
                    COALESCE(SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END), 0) as three_star,
                    COALESCE(SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END), 0) as two_star,
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as one_star
                FROM reviews
                WHERE product_id = ?
            ''', (product_id,))
        
        result = cursor.fetchone()
        
        if DB_ENGINE == 'mysql':
            total_reviews = int(result['total_reviews'])
            average_rating = float(result['average_rating'])
            five_star = int(result['five_star'])
            four_star = int(result['four_star'])
            three_star = int(result['three_star'])
            two_star = int(result['two_star'])
            one_star = int(result['one_star'])
        else:
            total_reviews = int(result['total_reviews'])
            average_rating = float(result['average_rating'])
            five_star = int(result['five_star'])
            four_star = int(result['four_star'])
            three_star = int(result['three_star'])
            two_star = int(result['two_star'])
            one_star = int(result['one_star'])
        
        # Calculate percentages
        if total_reviews > 0:
            five_star_percent = round((five_star / total_reviews) * 100, 1)
            four_star_percent = round((four_star / total_reviews) * 100, 1)
            three_star_percent = round((three_star / total_reviews) * 100, 1)
            two_star_percent = round((two_star / total_reviews) * 100, 1)
            one_star_percent = round((one_star / total_reviews) * 100, 1)
        else:
            five_star_percent = 0
            four_star_percent = 0
            three_star_percent = 0
            two_star_percent = 0
            one_star_percent = 0
        
        conn.close()
        
        return success_response({
            'overall_rating': round(average_rating, 2),
            'total_reviews': total_reviews,
            'rating_breakdown': {
                '5': {
                    'count': five_star,
                    'percentage': five_star_percent
                },
                '4': {
                    'count': four_star,
                    'percentage': four_star_percent
                },
                '3': {
                    'count': three_star,
                    'percentage': three_star_percent
                },
                '2': {
                    'count': two_star,
                    'percentage': two_star_percent
                },
                '1': {
                    'count': one_star,
                    'percentage': one_star_percent
                }
            }
        })
        
    except Exception as e:
        print(f"Error in get_product_ratings: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to fetch product ratings: {str(e)}", 500)
