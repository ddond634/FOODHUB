// Real-time Reviews System for Seller Dashboard

let reviewsCache = [];
let reviewFilters = {
    rating: null,
    dateFrom: null,
    dateTo: null,
    productId: null
};

// Load seller reviews with filters
async function loadSellerReviews() {
    try {
        // Build query parameters
        const params = new URLSearchParams();
        if (reviewFilters.rating) params.append('rating', reviewFilters.rating);
        if (reviewFilters.dateFrom) params.append('date_from', reviewFilters.dateFrom);
        if (reviewFilters.dateTo) params.append('date_to', reviewFilters.dateTo);
        if (reviewFilters.productId) params.append('product_id', reviewFilters.productId);
        
        const url = `/api/seller/reviews?${params.toString()}`;
        const response = await authFetch(url);
        
        if (!response.ok) {
            throw new Error('Failed to load reviews');
        }
        
        const data = await response.json();
        
        if (data.success && data.data) {
            reviewsCache = data.data.reviews || [];
            displaySellerReviews(reviewsCache);
            updateReviewsStats(reviewsCache);
        }
    } catch (error) {
        console.error('Error loading reviews:', error);
        showReviewsError('Failed to load reviews. Please try again.');
    }
}

// Display reviews in a clean, readable format
function displaySellerReviews(reviews) {
    const container = document.getElementById('sellerReviewsContainer');
    if (!container) return;
    
    if (!reviews || reviews.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: #999;">
                <div style="font-size: 48px; margin-bottom: 15px; opacity: 0.3;">
                    <i class="fas fa-star"></i>
                </div>
                <p style="font-size: 18px; margin: 0; font-weight: 600;">No Reviews Yet</p>
                <p style="font-size: 14px; margin: 8px 0 0 0;">Customer reviews will appear here</p>
            </div>
        `;
        return;
    }
    
    // Sort by most recent first
    reviews.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    const reviewsHTML = reviews.map(review => createReviewCard(review)).join('');
    container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 15px;">
            ${reviewsHTML}
        </div>
    `;
}

// Create individual review card
function createReviewCard(review) {
    const stars = '⭐'.repeat(review.rating) + '☆'.repeat(5 - review.rating);
    const reviewDate = new Date(review.created_at);
    const formattedDate = reviewDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    const ratingColorClass = review.rating >= 4 ? 'rating-good' : review.rating >= 3 ? 'rating-neutral' : 'rating-bad';
    
    return `
        <div class="review-card" style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s; border-left: 4px solid ${review.rating >= 4 ? '#27ae60' : review.rating >= 3 ? '#f39c12' : '#e74c3c'};">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 16px;">
                            ${review.customer_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <div style="font-weight: 600; color: #2c3e50; font-size: 15px;">${review.customer_name}</div>
                            <div style="font-size: 12px; color: #95a5a6;">Order #${review.order_id}</div>
                        </div>
                    </div>
                    <div style="font-size: 13px; color: #7f8c8d; margin-bottom: 8px;">
                        <i class="fas fa-box"></i> ${review.product_name}
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
function updateReviewsStats(reviews) {
    const totalReviews = reviews.length;
    const avgRating = reviews.length > 0 
        ? (reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length).toFixed(1)
        : '0.0';
    
    const ratingCounts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0};
    reviews.forEach(r => ratingCounts[r.rating]++);
    
    // Update stat cards if they exist
    const totalEl = document.getElementById('totalReviewsCount');
    const avgEl = document.getElementById('avgRatingValue');
    
    if (totalEl) totalEl.textContent = totalReviews;
    if (avgEl) avgEl.textContent = avgRating;
    
    // Update rating distribution
    for (let i = 1; i <= 5; i++) {
        const countEl = document.getElementById(`rating${i}Count`);
        const barEl = document.getElementById(`rating${i}Bar`);
        if (countEl) countEl.textContent = ratingCounts[i];
        if (barEl) {
            const percentage = totalReviews > 0 ? (ratingCounts[i] / totalReviews) * 100 : 0;
            barEl.style.width = `${percentage}%`;
        }
    }
}

// Apply filters
function applyReviewFilters() {
    // Get filter values from UI
    const ratingSelect = document.getElementById('reviewRatingFilter');
    const dateFromInput = document.getElementById('reviewDateFrom');
    const dateToInput = document.getElementById('reviewDateTo');
    const productSelect = document.getElementById('reviewProductFilter');
    
    reviewFilters.rating = ratingSelect ? ratingSelect.value || null : null;
    reviewFilters.dateFrom = dateFromInput ? dateFromInput.value || null : null;
    reviewFilters.dateTo = dateToInput ? dateToInput.value || null : null;
    reviewFilters.productId = productSelect ? productSelect.value || null : null;
    
    // Reload reviews with new filters
    loadSellerReviews();
}

// Clear all filters
function clearReviewFilters() {
    reviewFilters = {
        rating: null,
        dateFrom: null,
        dateTo: null,
        productId: null
    };
    
    // Clear UI
    const ratingSelect = document.getElementById('reviewRatingFilter');
    const dateFromInput = document.getElementById('reviewDateFrom');
    const dateToInput = document.getElementById('reviewDateTo');
    const productSelect = document.getElementById('reviewProductFilter');
    
    if (ratingSelect) ratingSelect.value = '';
    if (dateFromInput) dateFromInput.value = '';
    if (dateToInput) dateToInput.value = '';
    if (productSelect) productSelect.value = '';
    
    loadSellerReviews();
}

// Show error message
function showReviewsError(message) {
    const container = document.getElementById('sellerReviewsContainer');
    if (!container) return;
    
    container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: #e74c3c;">
            <div style="font-size: 40px; margin-bottom: 12px;">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <p style="font-size: 16px; margin: 0; font-weight: 600;">${message}</p>
            <button onclick="loadSellerReviews()" style="margin-top: 15px; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
                <i class="fas fa-sync"></i> Try Again
            </button>
        </div>
    `;
}

// Auto-refresh every 30 seconds for real-time updates
let reviewsRefreshInterval = null;

function startReviewsAutoRefresh() {
    if (reviewsRefreshInterval) {
        clearInterval(reviewsRefreshInterval);
    }
    reviewsRefreshInterval = setInterval(() => {
        loadSellerReviews();
    }, 30000); // Refresh every 30 seconds
}

function stopReviewsAutoRefresh() {
    if (reviewsRefreshInterval) {
        clearInterval(reviewsRefreshInterval);
        reviewsRefreshInterval = null;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the reviews section
    const reviewsContainer = document.getElementById('sellerReviewsContainer');
    if (reviewsContainer) {
        loadSellerReviews();
        startReviewsAutoRefresh();
    }
});

// Export functions for use in other scripts
window.loadSellerReviews = loadSellerReviews;
window.applyReviewFilters = applyReviewFilters;
window.clearReviewFilters = clearReviewFilters;
