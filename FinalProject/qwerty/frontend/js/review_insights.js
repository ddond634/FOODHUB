/**
 * Review Insights Module
 * Provides analytics and keyword extraction from customer reviews
 */

// Load review insights
async function loadReviewInsights() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.error('No authentication token found');
            return;
        }

        const response = await fetch(`${API_BASE}/api/sellers/my-insights`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        console.log('Insights API response:', data); // Debug log
        
        if (data.success === true) {
            const insightsData = data.data || data;
            // Ensure recent_trends exists with default structure if missing
            if (!insightsData.recent_trends) {
                insightsData.recent_trends = {
                    last_7_days: { total_reviews: 0, satisfaction: 0, average_rating: 0 },
                    previous_7_days: { total_reviews: 0, satisfaction: 0, average_rating: 0 },
                    trend: { satisfaction_change: 0, direction: 'stable' }
                };
            }
            console.log('Recent trends:', insightsData.recent_trends); // Debug recent_trends
            displayReviewInsights(insightsData);
        } else {
            console.error('Failed to load insights:', data.message || data.error || 'Unknown error');
        }
    } catch (error) {
        console.error('Error loading review insights:', error);
    }
}

// Display review insights in the UI
function displayReviewInsights(insights) {
    const insightsContainer = document.getElementById('reviewInsightsContainer');
    if (!insightsContainer) {
        console.warn('Review insights container not found');
        return;
    }

    const {
        total_reviews,
        customer_satisfaction,
        satisfied_count,
        most_mentioned,
        areas_to_improve,
        sentiment_distribution,
        recent_trends
    } = insights;

    // Build HTML for insights
    let html = '';

    // Customer Satisfaction Section
    html += `
        <div class="insight-card satisfaction-card">
            <div class="insight-header">
                <i class="fa-solid fa-face-smile"></i>
                <h3>Customer Satisfaction</h3>
            </div>
            <div class="satisfaction-display">
                <div class="satisfaction-percentage">
                    <span class="percentage-number">${customer_satisfaction}%</span>
                    <span class="percentage-label">Satisfied</span>
                </div>
                <div class="satisfaction-bar-container">
                    <div class="satisfaction-bar" style="width: ${customer_satisfaction}%"></div>
                </div>
                <p class="satisfaction-text">${satisfied_count} out of ${total_reviews} customers rated 4-5 stars</p>
            </div>
            ${recent_trends && recent_trends.trend ? `
            <div class="trend-indicator ${recent_trends.trend.direction}">
                <i class="fa-solid fa-arrow-${recent_trends.trend.direction === 'up' ? 'up' : recent_trends.trend.direction === 'down' ? 'down' : 'right'}"></i>
                ${recent_trends.trend.satisfaction_change > 0 ? '+' : ''}${recent_trends.trend.satisfaction_change}% vs last week
            </div>
            ` : ''}
        </div>
    `;

    // Most Mentioned (Positive) Section
    html += `
        <div class="insight-card positive-card">
            <div class="insight-header">
                <i class="fa-solid fa-thumbs-up"></i>
                <h3>Most Mentioned</h3>
            </div>
            <div class="keyword-list positive-keywords">
    `;

    if (most_mentioned && most_mentioned.length > 0) {
        most_mentioned.forEach((item, index) => {
            const keyword = capitalizeWords(item.keyword);
            const count = item.count;
            html += `
                <div class="keyword-item" style="animation-delay: ${index * 0.1}s">
                    <span class="keyword-text">${escapeHtml(keyword)}</span>
                    <span class="keyword-badge positive-badge">${count}</span>
                </div>
            `;
        });
    } else {
        html += `
            <p class="no-data">No positive mentions yet</p>
        `;
    }

    html += `
            </div>
        </div>
    `;

    // Areas to Improve (Negative) Section
    html += `
        <div class="insight-card improvement-card">
            <div class="insight-header">
                <i class="fa-solid fa-wrench"></i>
                <h3>Areas to Improve</h3>
            </div>
            <div class="keyword-list improvement-keywords">
    `;

    if (areas_to_improve && areas_to_improve.length > 0) {
        areas_to_improve.forEach((item, index) => {
            const keyword = capitalizeWords(item.keyword);
            const count = item.count;
            html += `
                <div class="keyword-item" style="animation-delay: ${index * 0.1}s">
                    <span class="keyword-text">${escapeHtml(keyword)}</span>
                    <span class="keyword-badge warning-badge">${count}</span>
                </div>
            `;
        });
    } else {
        html += `
            <p class="no-data">No improvement areas identified</p>
        `;
    }

    html += `
            </div>
        </div>
    `;

    // Sentiment Distribution Section
    if (sentiment_distribution) {
        const { positive, neutral, negative, positive_percentage, neutral_percentage, negative_percentage } = sentiment_distribution;
        
        html += `
            <div class="insight-card sentiment-card">
                <div class="insight-header">
                    <i class="fa-solid fa-chart-pie"></i>
                    <h3>Sentiment Distribution</h3>
                </div>
                <div class="sentiment-bars">
                    <div class="sentiment-bar-item positive">
                        <div class="sentiment-label">
                            <i class="fa-solid fa-face-smile"></i>
                            <span>Positive</span>
                        </div>
                        <div class="sentiment-bar-bg">
                            <div class="sentiment-bar-fill" style="width: ${positive_percentage}%"></div>
                        </div>
                        <span class="sentiment-count">${positive} (${positive_percentage}%)</span>
                    </div>
                    <div class="sentiment-bar-item neutral">
                        <div class="sentiment-label">
                            <i class="fa-solid fa-face-meh"></i>
                            <span>Neutral</span>
                        </div>
                        <div class="sentiment-bar-bg">
                            <div class="sentiment-bar-fill" style="width: ${neutral_percentage}%"></div>
                        </div>
                        <span class="sentiment-count">${neutral} (${neutral_percentage}%)</span>
                    </div>
                    <div class="sentiment-bar-item negative">
                        <div class="sentiment-label">
                            <i class="fa-solid fa-face-frown"></i>
                            <span>Negative</span>
                        </div>
                        <div class="sentiment-bar-bg">
                            <div class="sentiment-bar-fill" style="width: ${negative_percentage}%"></div>
                        </div>
                        <span class="sentiment-count">${negative} (${negative_percentage}%)</span>
                    </div>
                </div>
            </div>
        `;
    }

    // Recent Trends Section
    if (recent_trends && recent_trends.last_7_days && recent_trends.last_7_days.total_reviews > 0) {
        html += `
            <div class="insight-card trends-card">
                <div class="insight-header">
                    <i class="fa-solid fa-chart-line"></i>
                    <h3>Recent Trends</h3>
                </div>
                <div class="trends-comparison">
                    <div class="trend-period">
                        <h4>Last 7 Days</h4>
                        <div class="trend-stats">
                            <div class="trend-stat">
                                <span class="stat-label">Reviews</span>
                                <span class="stat-value">${recent_trends.last_7_days.total_reviews}</span>
                            </div>
                            <div class="trend-stat">
                                <span class="stat-label">Satisfaction</span>
                                <span class="stat-value">${recent_trends.last_7_days.satisfaction}%</span>
                            </div>
                            <div class="trend-stat">
                                <span class="stat-label">Avg Rating</span>
                                <span class="stat-value">${recent_trends.last_7_days.average_rating}</span>
                            </div>
                        </div>
                    </div>
                    ${recent_trends.previous_7_days ? `
                    <div class="trend-period">
                        <h4>Previous 7 Days</h4>
                        <div class="trend-stats">
                            <div class="trend-stat">
                                <span class="stat-label">Reviews</span>
                                <span class="stat-value">${recent_trends.previous_7_days.total_reviews}</span>
                            </div>
                            <div class="trend-stat">
                                <span class="stat-label">Satisfaction</span>
                                <span class="stat-value">${recent_trends.previous_7_days.satisfaction}%</span>
                            </div>
                            <div class="trend-stat">
                                <span class="stat-label">Avg Rating</span>
                                <span class="stat-value">${recent_trends.previous_7_days.average_rating}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    insightsContainer.innerHTML = html;
}

// Helper function to capitalize words
function capitalizeWords(str) {
    return str.replace(/\b\w/g, char => char.toUpperCase());
}

// HTML escape helper (reuse from seller_ratings.js if available)
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-refresh insights every 60 seconds when on reviews section
let insightsRefreshInterval = null;

function startInsightsAutoRefresh() {
    // Clear any existing interval
    if (insightsRefreshInterval) {
        clearInterval(insightsRefreshInterval);
    }
    
    // Refresh every 60 seconds
    insightsRefreshInterval = setInterval(() => {
        const reviewsSection = document.getElementById('reviewsSection');
        if (reviewsSection && reviewsSection.classList.contains('active')) {
            loadReviewInsights();
        }
    }, 60000);
}

function stopInsightsAutoRefresh() {
    if (insightsRefreshInterval) {
        clearInterval(insightsRefreshInterval);
        insightsRefreshInterval = null;
    }
}

// Don't auto-load on page load - let seller_dashboard.js handle it via loadReviews()
// The main loadReviews() function already loads analytics from /api/sellers/reviews/analytics
// This script provides helper functions but the primary data loading is handled by seller_dashboard.js

// Clean up on page unload
window.addEventListener('beforeunload', stopInsightsAutoRefresh);

// Expose loadInsights - but the main loadReviews() in seller_dashboard.js already loads analytics
// This function can be used for manual refresh, but it will use the updated endpoint that now returns real data
window.loadInsights = function() {
    loadReviewInsights();
};
