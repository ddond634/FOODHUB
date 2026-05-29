"""
Review Insights API
Provides analytics and keyword extraction from customer reviews
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from backend.auth import role_required
from backend.api_utils import success_response, error_response
import os
import re
from collections import Counter

insights_bp = Blueprint('insights', __name__, url_prefix='/api/sellers')

# Get DB_ENGINE from environment
DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def get_db_connection():
    """Get database connection using the same method as server.py"""
    from backend.server import get_db
    return get_db()


# Common positive and negative keywords for sentiment analysis
POSITIVE_KEYWORDS = [
    'excellent', 'great', 'amazing', 'perfect', 'love', 'best', 'good', 'fantastic',
    'awesome', 'wonderful', 'outstanding', 'quality', 'fast', 'quick', 'beautiful',
    'recommend', 'satisfied', 'happy', 'pleased', 'impressive', 'reliable', 'durable',
    'comfortable', 'efficient', 'professional', 'friendly', 'helpful', 'value',
    'affordable', 'worth', 'exceeded expectations'
]

NEGATIVE_KEYWORDS = [
    'poor', 'bad', 'terrible', 'awful', 'worst', 'disappointed', 'broken', 'defective',
    'late', 'slow', 'damaged', 'wrong', 'missing', 'problem', 'issue', 'difficult',
    'uncomfortable', 'cheap', 'overpriced', 'waste', 'refund', 'return', 'complaint',
    'packaging', 'sizing', 'instructions', 'delayed', 'small', 'large', 'tight', 'loose'
]

# Common improvement phrases
IMPROVEMENT_PHRASES = [
    'packaging', 'size', 'sizing', 'instructions', 'manual', 'delivery', 'shipping',
    'communication', 'quality', 'durability', 'color', 'description', 'price',
    'customer service', 'response time', 'fit', 'material', 'design'
]


def extract_keywords(text, keyword_list):
    """Extract keywords from text and return with counts"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in keyword_list:
        # Use word boundaries to match whole words
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            found_keywords.append(keyword)
    
    return found_keywords


def extract_phrases(text):
    """Extract common phrases from review text"""
    if not text:
        return []
    
    text_lower = text.lower()
    
    # Common positive phrases
    positive_phrases = [
        ('great quality', r'great\s+quality'),
        ('fast delivery', r'fast\s+delivery|quick\s+delivery|fast\s+shipping|quick\s+shipping'),
        ('good value', r'good\s+value|great\s+value|worth\s+(?:the\s+)?money'),
        ('excellent service', r'excellent\s+service|great\s+service'),
        ('highly recommend', r'highly\s+recommend|would\s+recommend'),
        ('as described', r'as\s+described|exactly\s+as\s+described'),
        ('good quality', r'good\s+quality|nice\s+quality'),
        ('easy to use', r'easy\s+to\s+use|simple\s+to\s+use'),
        ('looks great', r'looks\s+great|looks\s+good|looks\s+nice'),
        ('perfect fit', r'perfect\s+fit|fits\s+perfectly'),
    ]
    
    found_phrases = []
    for phrase_name, pattern in positive_phrases:
        if re.search(pattern, text_lower):
            found_phrases.append(phrase_name)
    
    return found_phrases


def analyze_sentiment(rating, comment):
    """Determine if review is positive, neutral, or negative"""
    if rating >= 4:
        return 'positive'
    elif rating <= 2:
        return 'negative'
    else:
        return 'neutral'


@insights_bp.route('/my-insights', methods=['GET'])
@role_required('seller')
def get_my_insights():
    """
    Get review insights for the logged-in seller
    Includes: Most Mentioned, Areas to Improve, Customer Satisfaction
    """
    try:
        seller_id = g.user_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all reviews for the seller
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    r.rating,
                    r.comment,
                    r.created_at,
                    p.title as product_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                WHERE r.seller_id = %s
                ORDER BY r.created_at DESC
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT 
                    r.rating,
                    r.comment,
                    r.created_at,
                    p.title as product_name
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                WHERE r.seller_id = ?
                ORDER BY r.created_at DESC
            ''', (seller_id,))
        
        reviews = cursor.fetchall()
        conn.close()
        
        if not reviews or len(reviews) == 0:
            return success_response({
                'total_reviews': 0,
                'customer_satisfaction': 0,
                'satisfied_count': 0,
                'most_mentioned': [],
                'areas_to_improve': [],
                'sentiment_distribution': {
                    'positive': 0,
                    'neutral': 0,
                    'negative': 0,
                    'positive_percentage': 0,
                    'neutral_percentage': 0,
                    'negative_percentage': 0
                },
                'recent_trends': {
                    'last_7_days': {
                        'total_reviews': 0,
                        'satisfaction': 0,
                        'average_rating': 0
                    },
                    'previous_7_days': {
                        'total_reviews': 0,
                        'satisfaction': 0,
                        'average_rating': 0
                    },
                    'trend': {
                        'satisfaction_change': 0,
                        'direction': 'stable'
                    }
                }
            })
        
        # Initialize counters
        total_reviews = len(reviews)
        satisfied_count = 0
        positive_keywords_counter = Counter()
        positive_phrases_counter = Counter()
        negative_keywords_counter = Counter()
        improvement_areas_counter = Counter()
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        
        # Analyze each review
        for review in reviews:
            if DB_ENGINE == 'mysql':
                rating = review['rating']
                comment = review['comment'] or ''
            else:
                rating = review['rating']
                comment = review['comment'] or ''
            
            # Count satisfied customers (4-5 stars)
            if rating >= 4:
                satisfied_count += 1
            
            # Determine sentiment
            sentiment = analyze_sentiment(rating, comment)
            sentiment_counts[sentiment] += 1
            
            # Extract keywords and phrases
            if sentiment == 'positive':
                # Extract positive keywords
                keywords = extract_keywords(comment, POSITIVE_KEYWORDS)
                positive_keywords_counter.update(keywords)
                
                # Extract positive phrases
                phrases = extract_phrases(comment)
                positive_phrases_counter.update(phrases)
            
            elif sentiment == 'negative':
                # Extract negative keywords
                keywords = extract_keywords(comment, NEGATIVE_KEYWORDS)
                negative_keywords_counter.update(keywords)
                
                # Extract improvement areas
                improvements = extract_keywords(comment, IMPROVEMENT_PHRASES)
                improvement_areas_counter.update(improvements)
        
        # Calculate customer satisfaction percentage
        satisfaction_percentage = round((satisfied_count / total_reviews) * 100, 1) if total_reviews > 0 else 0
        
        # Get top most mentioned (combine keywords and phrases)
        all_positive_mentions = positive_keywords_counter + positive_phrases_counter
        most_mentioned = [
            {'keyword': keyword, 'count': count}
            for keyword, count in all_positive_mentions.most_common(10)
        ]
        
        # Get top areas to improve (combine negative keywords and improvement phrases)
        all_negative_mentions = negative_keywords_counter + improvement_areas_counter
        areas_to_improve = [
            {'keyword': keyword, 'count': count}
            for keyword, count in all_negative_mentions.most_common(10)
        ]
        
        # Calculate recent trends (last 7 days vs previous 7 days)
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)
        
        recent_reviews = []
        previous_reviews = []
        
        for review in reviews:
            if DB_ENGINE == 'mysql':
                review_date = review['created_at']
            else:
                review_date = datetime.strptime(review['created_at'], '%Y-%m-%d %H:%M:%S')
            
            if review_date >= seven_days_ago:
                recent_reviews.append(review)
            elif review_date >= fourteen_days_ago:
                previous_reviews.append(review)
        
        # Calculate trend metrics
        recent_satisfied = sum(1 for r in recent_reviews if (r['rating'] if DB_ENGINE == 'mysql' else r['rating']) >= 4)
        previous_satisfied = sum(1 for r in previous_reviews if (r['rating'] if DB_ENGINE == 'mysql' else r['rating']) >= 4)
        
        recent_satisfaction = round((recent_satisfied / len(recent_reviews)) * 100, 1) if recent_reviews else 0
        previous_satisfaction = round((previous_satisfied / len(previous_reviews)) * 100, 1) if previous_reviews else 0
        
        satisfaction_trend = round(recent_satisfaction - previous_satisfaction, 1)
        
        recent_trends = {
            'last_7_days': {
                'total_reviews': len(recent_reviews),
                'satisfaction': recent_satisfaction,
                'average_rating': round(sum((r['rating'] if DB_ENGINE == 'mysql' else r['rating']) for r in recent_reviews) / len(recent_reviews), 2) if recent_reviews else 0
            },
            'previous_7_days': {
                'total_reviews': len(previous_reviews),
                'satisfaction': previous_satisfaction,
                'average_rating': round(sum((r['rating'] if DB_ENGINE == 'mysql' else r['rating']) for r in previous_reviews) / len(previous_reviews), 2) if previous_reviews else 0
            },
            'trend': {
                'satisfaction_change': satisfaction_trend,
                'direction': 'up' if satisfaction_trend > 0 else 'down' if satisfaction_trend < 0 else 'stable'
            }
        }
        
        return success_response({
            'total_reviews': total_reviews,
            'customer_satisfaction': satisfaction_percentage,
            'satisfied_count': satisfied_count,
            'most_mentioned': most_mentioned,
            'areas_to_improve': areas_to_improve,
            'sentiment_distribution': {
                'positive': sentiment_counts['positive'],
                'neutral': sentiment_counts['neutral'],
                'negative': sentiment_counts['negative'],
                'positive_percentage': round((sentiment_counts['positive'] / total_reviews) * 100, 1) if total_reviews > 0 else 0,
                'neutral_percentage': round((sentiment_counts['neutral'] / total_reviews) * 100, 1) if total_reviews > 0 else 0,
                'negative_percentage': round((sentiment_counts['negative'] / total_reviews) * 100, 1) if total_reviews > 0 else 0
            },
            'recent_trends': recent_trends
        })
        
    except Exception as e:
        print(f"Error in get_my_insights: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to fetch insights: {str(e)}", 500)


@insights_bp.route('/<int:seller_id>/insights', methods=['GET'])
def get_seller_insights(seller_id):
    """
    Get public review insights for any seller
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all reviews for the seller
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    r.rating,
                    r.comment
                FROM reviews r
                WHERE r.seller_id = %s
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT 
                    r.rating,
                    r.comment
                FROM reviews r
                WHERE r.seller_id = ?
            ''', (seller_id,))
        
        reviews = cursor.fetchall()
        conn.close()
        
        if not reviews or len(reviews) == 0:
            return success_response({
                'total_reviews': 0,
                'customer_satisfaction': 0,
                'most_mentioned': [],
                'sentiment_distribution': {
                    'positive': 0,
                    'neutral': 0,
                    'negative': 0
                }
            })
        
        total_reviews = len(reviews)
        satisfied_count = sum(1 for r in reviews if (r['rating'] if DB_ENGINE == 'mysql' else r['rating']) >= 4)
        satisfaction_percentage = round((satisfied_count / total_reviews) * 100, 1)
        
        # Basic sentiment counts
        positive = sum(1 for r in reviews if (r['rating'] if DB_ENGINE == 'mysql' else r['rating']) >= 4)
        neutral = sum(1 for r in reviews if (r['rating'] if DB_ENGINE == 'mysql' else r['rating']) == 3)
        negative = sum(1 for r in reviews if (r['rating'] if DB_ENGINE == 'mysql' else r['rating']) <= 2)
        
        # Extract top positive mentions
        positive_counter = Counter()
        for review in reviews:
            rating = review['rating'] if DB_ENGINE == 'mysql' else review['rating']
            comment = review['comment'] if DB_ENGINE == 'mysql' else review['comment']
            
            if rating >= 4 and comment:
                phrases = extract_phrases(comment)
                positive_counter.update(phrases)
        
        most_mentioned = [
            {'keyword': keyword, 'count': count}
            for keyword, count in positive_counter.most_common(5)
        ]
        
        return success_response({
            'total_reviews': total_reviews,
            'customer_satisfaction': satisfaction_percentage,
            'most_mentioned': most_mentioned,
            'sentiment_distribution': {
                'positive': positive,
                'neutral': neutral,
                'negative': negative
            }
        })
        
    except Exception as e:
        print(f"Error in get_seller_insights: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"Failed to fetch insights: {str(e)}", 500)
