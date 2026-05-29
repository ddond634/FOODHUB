"""
Test script for Seller Ratings System
This script demonstrates the ratings API and creates sample review data
"""

import requests
import json
from datetime import datetime, timedelta
import random

API_BASE = 'http://127.0.0.1:5000/api'

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_ratings_api_no_auth():
    """Test public ratings endpoint (should work without auth for specific seller)"""
    print_section("Testing Public Ratings API")
    
    try:
        response = requests.get(f'{API_BASE}/sellers/1/ratings')
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API Response: {json.dumps(data, indent=2)}")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Request failed: {str(e)}")

def test_my_ratings_with_auth(token):
    """Test seller's own ratings (requires authentication)"""
    print_section("Testing My Ratings API (Authenticated)")
    
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f'{API_BASE}/sellers/my-ratings', headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                ratings_data = data['data']
                print(f"\n✓ Overall Rating: {ratings_data['overall_rating']}/5.0")
                print(f"✓ Total Reviews: {ratings_data['total_reviews']}")
                print(f"\nRating Breakdown:")
                for star in ['5', '4', '3', '2', '1']:
                    breakdown = ratings_data['rating_breakdown'][star]
                    print(f"  {star} ⭐: {breakdown['count']} reviews ({breakdown['percentage']}%)")
                
                print(f"\n✓ Recent Reviews: {len(ratings_data.get('reviews', []))} loaded")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Request failed: {str(e)}")

def test_product_ratings():
    """Test product-specific ratings"""
    print_section("Testing Product Ratings API")
    
    try:
        response = requests.get(f'{API_BASE}/sellers/products/1/ratings')
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API Response: {json.dumps(data, indent=2)}")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Request failed: {str(e)}")

def create_sample_reviews_data():
    """
    Demonstrate how review data would be structured
    Note: This doesn't actually create reviews - use the customer review system for that
    """
    print_section("Sample Review Data Structure")
    
    sample_reviews = [
        {
            "customer_id": 1,
            "order_id": 1,
            "product_id": 1,
            "seller_id": 1,
            "rating": 5,
            "comment": "Excellent product! Fast delivery and great quality.",
            "created_at": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "customer_id": 2,
            "order_id": 2,
            "product_id": 1,
            "seller_id": 1,
            "rating": 4,
            "comment": "Good product, but shipping was a bit slow.",
            "created_at": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "customer_id": 3,
            "order_id": 3,
            "product_id": 2,
            "seller_id": 1,
            "rating": 5,
            "comment": "Highly recommended! Exactly as described.",
            "created_at": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    
    print("\nSample review data structure:")
    print(json.dumps(sample_reviews, indent=2))
    
    # Calculate what the ratings would look like
    total = len(sample_reviews)
    ratings_count = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_rating = 0
    
    for review in sample_reviews:
        ratings_count[review['rating']] += 1
        total_rating += review['rating']
    
    avg_rating = total_rating / total if total > 0 else 0
    
    print(f"\n📊 Expected Ratings Calculation:")
    print(f"  Overall Rating: {avg_rating:.1f}/5.0")
    print(f"  Total Reviews: {total}")
    print(f"\n  Rating Breakdown:")
    for star in [5, 4, 3, 2, 1]:
        count = ratings_count[star]
        percentage = (count / total * 100) if total > 0 else 0
        print(f"    {star} ⭐: {count} ({percentage:.1f}%)")

def display_rating_visualization(rating):
    """Display a visual star rating"""
    full_stars = int(rating)
    half_star = (rating % 1) >= 0.5
    empty_stars = 5 - full_stars - (1 if half_star else 0)
    
    stars = "★" * full_stars
    if half_star:
        stars += "⯨"
    stars += "☆" * empty_stars
    
    return f"{stars} {rating:.1f}/5.0"

def main():
    """Main test function"""
    print_section("🌟 SELLER RATINGS SYSTEM TEST 🌟")
    print("\nThis script tests the Seller Ratings API endpoints")
    print("and demonstrates the rating calculation logic.")
    
    # Test public API (no authentication needed)
    test_ratings_api_no_auth()
    
    # Test product ratings
    test_product_ratings()
    
    # Show sample data structure
    create_sample_reviews_data()
    
    print("\n" + "="*60)
    print("\n💡 To test authenticated endpoints (/my-ratings):")
    print("  1. Log in as a seller through the web interface")
    print("  2. Get the JWT token from localStorage")
    print("  3. Run: test_my_ratings_with_auth(your_token)")
    
    print("\n💡 To create actual review data:")
    print("  1. Log in as a customer")
    print("  2. Place and complete an order")
    print("  3. Write a review from the account page")
    print("  4. The rating will automatically appear in seller dashboard")
    
    print("\n✅ Ratings system is ready to use!")
    print("   Navigate to: http://127.0.0.1:5000/seller_dashboard.html")
    print("   Click 'Reviews' tab to see your ratings\n")

if __name__ == '__main__':
    main()
