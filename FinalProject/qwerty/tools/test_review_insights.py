"""
Test script for Review Insights System
Demonstrates the insights API and shows sample output
"""

import requests
import json

API_BASE = 'http://127.0.0.1:5000/api'

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_insights_api(token=None):
    """Test the review insights endpoint"""
    print_section("🔍 REVIEW INSIGHTS SYSTEM TEST")
    
    if token:
        print("\n Testing authenticated endpoint (my-insights)...")
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(f'{API_BASE}/sellers/my-insights', headers=headers)
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    display_insights(data['data'])
                else:
                    print(f"✗ Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"✗ HTTP Error: {response.text}")
        except Exception as e:
            print(f"✗ Request failed: {str(e)}")
    else:
        print("\n Testing public endpoint (seller insights)...")
        try:
            response = requests.get(f'{API_BASE}/sellers/1/insights')
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    display_public_insights(data['data'])
                else:
                    print(f"✗ Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"✗ HTTP Error: {response.text}")
        except Exception as e:
            print(f"✗ Request failed: {str(e)}")

def display_insights(insights):
    """Display detailed insights data"""
    print("\n" + "─"*70)
    print("📊 REVIEW INSIGHTS REPORT")
    print("─"*70)
    
    # Customer Satisfaction
    print(f"\n😊 Customer Satisfaction")
    print(f"   {insights['customer_satisfaction']}% Satisfied")
    print(f"   ({insights['satisfied_count']} out of {insights['total_reviews']} customers)")
    
    if insights.get('recent_trends'):
        trend = insights['recent_trends']['trend']
        direction_symbol = {
            'up': '↑',
            'down': '↓',
            'stable': '→'
        }.get(trend['direction'], '→')
        
        print(f"   {direction_symbol} {trend['satisfaction_change']:+.1f}% vs last week")
    
    # Most Mentioned (Positive)
    print(f"\n👍 Most Mentioned (Top Positive Keywords)")
    if insights['most_mentioned']:
        for i, item in enumerate(insights['most_mentioned'][:5], 1):
            keyword = item['keyword'].title()
            count = item['count']
            bar = '█' * min(count, 50)
            print(f"   {i}. {keyword:<25} {bar} ({count})")
    else:
        print("   No positive mentions found")
    
    # Areas to Improve
    print(f"\n🔧 Areas to Improve (Top Issues)")
    if insights['areas_to_improve']:
        for i, item in enumerate(insights['areas_to_improve'][:5], 1):
            keyword = item['keyword'].title()
            count = item['count']
            bar = '▓' * min(count, 30)
            print(f"   {i}. {keyword:<25} {bar} ({count})")
    else:
        print("   No improvement areas identified")
    
    # Sentiment Distribution
    if insights.get('sentiment_distribution'):
        sent = insights['sentiment_distribution']
        print(f"\n📈 Sentiment Distribution")
        print(f"   ● Positive: {sent['positive']} ({sent['positive_percentage']:.1f}%)")
        print(f"   ● Neutral:  {sent['neutral']} ({sent['neutral_percentage']:.1f}%)")
        print(f"   ● Negative: {sent['negative']} ({sent['negative_percentage']:.1f}%)")
    
    # Recent Trends
    if insights.get('recent_trends'):
        trends = insights['recent_trends']
        print(f"\n📅 Recent Trends")
        print(f"   Last 7 Days:")
        print(f"      Reviews: {trends['last_7_days']['total_reviews']}")
        print(f"      Satisfaction: {trends['last_7_days']['satisfaction']}%")
        print(f"      Avg Rating: {trends['last_7_days']['average_rating']}/5.0")
        
        if trends['previous_7_days']['total_reviews'] > 0:
            print(f"   Previous 7 Days:")
            print(f"      Reviews: {trends['previous_7_days']['total_reviews']}")
            print(f"      Satisfaction: {trends['previous_7_days']['satisfaction']}%")
            print(f"      Avg Rating: {trends['previous_7_days']['average_rating']}/5.0")

def display_public_insights(insights):
    """Display public insights data (limited)"""
    print("\n" + "─"*70)
    print("📊 PUBLIC INSIGHTS")
    print("─"*70)
    
    print(f"\n Total Reviews: {insights['total_reviews']}")
    print(f" Customer Satisfaction: {insights['customer_satisfaction']}%")
    
    if insights['most_mentioned']:
        print(f"\n Top Positive Mentions:")
        for item in insights['most_mentioned']:
            print(f"   • {item['keyword'].title()} ({item['count']})")

def display_sample_data():
    """Show sample review data and expected insights"""
    print_section("📝 SAMPLE DATA & EXPECTED OUTPUT")
    
    sample_reviews = [
        {
            "rating": 5,
            "comment": "Excellent product! Great quality and fast delivery. Highly recommend!",
            "expected_keywords": ["excellent", "great quality", "fast delivery", "recommend"]
        },
        {
            "rating": 4,
            "comment": "Good value for money. Easy to use and looks great.",
            "expected_keywords": ["good value", "easy to use", "looks great"]
        },
        {
            "rating": 2,
            "comment": "Poor packaging. Item arrived with damaged box. Sizing is also off.",
            "expected_keywords": ["packaging", "damaged", "sizing"]
        },
        {
            "rating": 5,
            "comment": "Perfect fit! Exactly as described. Fast shipping.",
            "expected_keywords": ["perfect fit", "as described", "fast"]
        }
    ]
    
    print("\nSample Reviews:")
    for i, review in enumerate(sample_reviews, 1):
        stars = "★" * review['rating'] + "☆" * (5 - review['rating'])
        print(f"\n{i}. {stars} ({review['rating']}/5)")
        print(f"   \"{review['comment']}\"")
        print(f"   Expected keywords: {', '.join(review['expected_keywords'])}")
    
    # Calculate expected insights
    total = len(sample_reviews)
    satisfied = sum(1 for r in sample_reviews if r['rating'] >= 4)
    satisfaction = (satisfied / total) * 100
    
    print(f"\n📊 Expected Insights Calculation:")
    print(f"   Total Reviews: {total}")
    print(f"   Satisfied (4-5 stars): {satisfied}")
    print(f"   Customer Satisfaction: {satisfaction:.1f}%")
    print(f"\n   Positive sentiment: {sum(1 for r in sample_reviews if r['rating'] >= 4)} ({sum(1 for r in sample_reviews if r['rating'] >= 4) / total * 100:.1f}%)")
    print(f"   Neutral sentiment: {sum(1 for r in sample_reviews if r['rating'] == 3)} ({sum(1 for r in sample_reviews if r['rating'] == 3) / total * 100:.1f}%)")
    print(f"   Negative sentiment: {sum(1 for r in sample_reviews if r['rating'] <= 2)} ({sum(1 for r in sample_reviews if r['rating'] <= 2) / total * 100:.1f}%)")

def main():
    """Main test function"""
    print_section("🌟 REVIEW INSIGHTS SYSTEM 🌟")
    print("\nThis script tests the Review Insights API")
    print("and demonstrates keyword extraction and analytics.")
    
    # Show sample data
    display_sample_data()
    
    # Test public API
    print("\n" + "─"*70)
    test_insights_api()
    
    print("\n" + "="*70)
    print("\n💡 To test authenticated endpoint:")
    print("  1. Log in as a seller at http://127.0.0.1:5000/seller_dashboard.html")
    print("  2. Open browser DevTools (F12)")
    print("  3. Console: localStorage.getItem('hub_access_token')")
    print("  4. Run: test_insights_api(your_token)")
    
    print("\n💡 To create test review data:")
    print("  1. Log in as customer")
    print("  2. Place and complete orders")
    print("  3. Write reviews with specific keywords:")
    print("     - Positive: 'excellent', 'great quality', 'fast delivery'")
    print("     - Negative: 'packaging', 'sizing', 'damaged'")
    
    print("\n✅ Review Insights system is ready!")
    print("   Navigate to: http://127.0.0.1:5000/seller_dashboard.html")
    print("   Click 'Reviews' tab to see insights\n")

if __name__ == '__main__':
    main()
