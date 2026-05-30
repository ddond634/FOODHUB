// Real-time Reviews System for Rider Dashboard

let riderReviewsCache = [];
let riderReviewFilters = {
    rating: null,
    dateFrom: null,
    dateTo: null
};

// Load rider reviews with filters
async function loadRiderReviews() {
    try {
        // Build query parameters
        const params = new URLSearchParams();
        if (riderReviewFilters.rating) params.append('rating', riderReviewFilters.rating);
        if (riderReviewFilters.dateFrom) params.append('date_from', riderReviewFilters.dateFrom);
        if (riderReviewFilters.dateTo) params.append('date_to', riderReviewFilters.dateTo);
        
        const url = `/api/rider/reviews?${params.toString()}`;
        const response = await authFetch(url);
        
        if (!response.ok) {
            throw new Error('Failed to load reviews');
        }
        
        const data = await response.json();
        
        if (data.success && data.data) {
            riderReviewsCache = data.data.reviews || [];
            displayRiderReviews(riderReviewsCache);
            updateRiderReviewsStats(riderReviewsCache);
        }
    } catch (error) {
        console.error('Error loading rider reviews:', error);
        showRiderReviewsError('Failed to load reviews. Please try again.');
    }
}

// Display reviews in a clean, readable format
function displayRiderReviews(reviews) {
    const container = document.getElementById('riderReviewsContainer');
    if (!container) return;
    
    if (!reviews || reviews.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: #999;">
                <div style="font-size: 48px; margin-bottom: 15px; opacity: 0.3;">
                    <i class="fas fa-motorcycle"></i>
                </div>
                <p style="font-size: 18px; margin: 0; font-weight: 600;">No Reviews Yet</p>
                <p style="font-size: 14px; margin: 8px 0 0 0;">Customer reviews will appear here</p>
            </div>
        `;
        return;
    }
    
    // Sort by most recent first
    reviews.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    const reviewsHTML = reviews.map(review => createRiderReviewCard(review)).join('');
    container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 15px;">
            ${reviewsHTML}
        </div>
    `;
}

// Create individual review card for rider
function createRiderReviewCard(review) {
    const stars = '⭐'.repeat(review.rating) + '☆'.repeat(5 - review.rating);
    const reviewDate = new Date(review.created_at);
    const formattedDate = reviewDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    const reviewTypeLabel = review.review_type === 'delivery' ? '📦 Delivery Service' : '🏍️ Rider Service';
    
    return `
        <div class="review-card" style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s; border-left: 4px solid ${review.rating >= 4 ? '#27ae60' : review.rating >= 3 ? '#f39c12' : '#e74c3c'};">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #f093fb, #f5576c); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 16px;">
                            ${review.customer_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <div style="font-weight: 600; color: #2c3e50; font-size: 15px;">${review.customer_name}</div>
                            <div style="font-size: 12px; color: #95a5a6;">Order #${review.order_id}</div>
                        </div>
                    </div>
                    <div style="font-size: 13px; color: #7f8c8d; margin-bottom: 5px;">
                        ${reviewTypeLabel}
                    </div>
                    <div style="font-size: 12px; color: #95a5a6;">
                        Order Total: ₱${parseFloat(review.order_total || 0).toFixed(2)}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 24px; line-height: 1; margin-bottom: 5px;">${stars}</div>
                    <div style="font-size: 12px; color: #95a5a6;">
                        <i class="far fa-clock"></i> ${formattedDate}
                    </div>
                </div>
            </div>
            ${review.comment ? `
                <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin-top: 12px; border-left: 3px solid #ddd;">
                    <div style="color: #34495e; line-height: 1.6; font-size: 14px;">"${review.comment}"</div>
                </div>
            ` : ''}
        </div>
    `;
}

// Update statistics display
function updateRiderReviewsStats(reviews) {
    const totalReviews = reviews.length;
    const avgRating = reviews.length > 0 
        ? (reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length).toFixed(1)
        : '0.0';
    
    const ratingCounts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0};
    reviews.forEach(r => ratingCounts[r.rating]++);
    
    // Update stat cards if they exist
    const totalEl = document.getElementById('riderTotalReviewsCount');
    const avgEl = document.getElementById('riderAvgRatingValue');
    
    if (totalEl) totalEl.textContent = totalReviews;
    if (avgEl) avgEl.textContent = avgRating;
    
    // Update rating distribution
    for (let i = 1; i <= 5; i++) {
        const countEl = document.getElementById(`riderRating${i}Count`);
        const barEl = document.getElementById(`riderRating${i}Bar`);
        if (countEl) countEl.textContent = ratingCounts[i];
        if (barEl) {
            const percentage = totalReviews > 0 ? (ratingCounts[i] / totalReviews) * 100 : 0;
            barEl.style.width = `${percentage}%`;
        }
    }
}

// Apply filters
function applyRiderReviewFilters() {
    // Get filter values from UI
    const ratingSelect = document.getElementById('riderReviewRatingFilter');
    const dateFromInput = document.getElementById('riderReviewDateFrom');
    const dateToInput = document.getElementById('riderReviewDateTo');
    
    riderReviewFilters.rating = ratingSelect ? ratingSelect.value || null : null;
    riderReviewFilters.dateFrom = dateFromInput ? dateFromInput.value || null : null;
    riderReviewFilters.dateTo = dateToInput ? dateToInput.value || null : null;
    
    // Reload reviews with new filters
    loadRiderReviews();
}

// Clear all filters
function clearRiderReviewFilters() {
    riderReviewFilters = {
        rating: null,
        dateFrom: null,
        dateTo: null
    };
    
    // Clear UI
    const ratingSelect = document.getElementById('riderReviewRatingFilter');
    const dateFromInput = document.getElementById('riderReviewDateFrom');
    const dateToInput = document.getElementById('riderReviewDateTo');
    
    if (ratingSelect) ratingSelect.value = '';
    if (dateFromInput) dateFromInput.value = '';
    if (dateToInput) dateToInput.value = '';
    
    loadRiderReviews();
}

// Show error message
function showRiderReviewsError(message) {
    const container = document.getElementById('riderReviewsContainer');
    if (!container) return;
    
    container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: #e74c3c;">
            <div style="font-size: 40px; margin-bottom: 12px;">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <p style="font-size: 16px; margin: 0; font-weight: 600;">${message}</p>
            <button onclick="loadRiderReviews()" style="margin-top: 15px; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
                <i class="fas fa-sync"></i> Try Again
            </button>
        </div>
    `;
}

// Auto-refresh every 30 seconds for real-time updates
let riderReviewsRefreshInterval = null;

function startRiderReviewsAutoRefresh() {
    if (riderReviewsRefreshInterval) {
        clearInterval(riderReviewsRefreshInterval);
    }
    riderReviewsRefreshInterval = setInterval(() => {
        loadRiderReviews();
    }, 30000); // Refresh every 30 seconds
}

function stopRiderReviewsAutoRefresh() {
    if (riderReviewsRefreshInterval) {
        clearInterval(riderReviewsRefreshInterval);
        riderReviewsRefreshInterval = null;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the rider reviews section
    const reviewsContainer = document.getElementById('riderReviewsContainer');
    if (reviewsContainer) {
        loadRiderReviews();
        startRiderReviewsAutoRefresh();
    }
});

// Export functions for use in other scripts
window.loadRiderReviews = loadRiderReviews;
window.applyRiderReviewFilters = applyRiderReviewFilters;
window.clearRiderReviewFilters = clearRiderReviewFilters;
