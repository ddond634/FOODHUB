/**
 * Seller Ratings Module
 * Handles dynamic rating display and updates in seller dashboard
 */

// API_BASE is already declared in seller_dashboard.js

// Load seller ratings on page load
async function loadSellerRatings() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.error('No authentication token found');
            return;
        }

        const response = await fetch(`${API_BASE}/api/sellers/my-ratings`, {
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
        
        console.log('Ratings API response:', data); // Debug log
        
        if (data.status === 'success' || data.success === true) {
            // Normalize backend stub shape to expected frontend shape
            const payload = data.data || data;
            const normalized = {
                overall_rating: payload.overall_rating ?? payload.average_rating ?? 0,
                total_reviews: payload.total_reviews ?? 0,
                rating_breakdown: payload.rating_breakdown ?? payload.breakdown ?? [],
                reviews: payload.reviews ?? payload.recent ?? []
            };
            updateRatingDisplay(normalized);
            updateDashboardRating(normalized.overall_rating);
        } else {
            console.error('Failed to load ratings:', data.message || data.error || 'Unknown error');
        }
    } catch (error) {
        console.error('Error loading seller ratings:', error);
    }
}

// Update rating display in reviews section
function updateRatingDisplay(ratingsData) {
    const { overall_rating = 0, total_reviews = 0, rating_breakdown = [], reviews = [] } = ratingsData || {};

    // Update overall rating
    const ratingNumber = document.querySelector('.reviews-summary .rating-number');
    if (ratingNumber) {
        ratingNumber.textContent = Number(overall_rating).toFixed(1);
    }

    // Update review count
    const reviewCount = document.querySelector('.reviews-summary .review-count');
    if (reviewCount) {
        reviewCount.textContent = `Based on ${total_reviews} review${total_reviews !== 1 ? 's' : ''}`;
    }

    // Update star display based on rating
    updateStarDisplay('.reviews-summary .rating-stars', Number(overall_rating));

    // Update rating breakdown bars
    updateRatingBreakdown(rating_breakdown || [], total_reviews || 0);

    // Display reviews list
    displayReviewsList(reviews || []);
}

// Update star display based on rating value
function updateStarDisplay(selector, rating) {
    const starsContainer = document.querySelector(selector);
    if (!starsContainer) return;

    const stars = starsContainer.querySelectorAll('i');
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    stars.forEach((star, index) => {
        star.classList.remove('fa-solid', 'fa-regular', 'fa-star-half-stroke');
        
        if (index < fullStars) {
            star.classList.add('fa-solid', 'fa-star');
        } else if (index === fullStars && hasHalfStar) {
            star.classList.add('fa-solid', 'fa-star-half-stroke');
        } else {
            star.classList.add('fa-regular', 'fa-star');
        }
    });
}

// Update rating breakdown bars
function updateRatingBreakdown(breakdown, totalReviews) {
    const ratingBars = document.querySelectorAll('.rating-bar-item');
    
    // Order: 5 star, 4 star, 3 star, 2 star, 1 star
    const starLevels = ['5', '4', '3', '2', '1'];
    
    ratingBars.forEach((barItem, index) => {
        const starLevel = starLevels[index];
        const ratingData = breakdown[starLevel];
        
        if (ratingData) {
            const percentage = ratingData.percentage;
            const count = ratingData.count;
            
            // Update bar width
            const fill = barItem.querySelector('.rating-fill');
            if (fill) {
                fill.style.width = `${percentage}%`;
            }
            
            // Update percentage text
            const percentText = barItem.querySelector('.rating-percent');
            if (percentText) {
                percentText.textContent = `${percentage}% (${count})`;
            }
        }
    });
}

// Display reviews list
function displayReviewsList(reviews) {
    const reviewsContainer = document.querySelector('.reviews-container');
    if (!reviewsContainer) return;

    if (!reviews || reviews.length === 0) {
        reviewsContainer.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-star-half-stroke" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                <p style="color: #666;">No reviews yet</p>
                <p style="color: #999; font-size: 14px;">Customer reviews will appear here once they start rating your products.</p>
            </div>
        `;
        return;
    }

    // Group reviews by product
    const reviewsByProduct = {};
    reviews.forEach(review => {
        const productName = review.product_name;
        if (!reviewsByProduct[productName]) {
            reviewsByProduct[productName] = [];
        }
        reviewsByProduct[productName].push(review);
    });

    // Build HTML for each product's reviews
    let html = '';
    
    for (const [productName, productReviews] of Object.entries(reviewsByProduct)) {
        // Calculate average rating for this product
        const avgRating = productReviews.reduce((sum, r) => sum + r.rating, 0) / productReviews.length;
        
        html += `
            <div class="product-review-section">
                <div class="product-review-header">
                    <div class="product-info-review">
                        <h4>${escapeHtml(productName)}</h4>
                        <div class="product-rating">
                            <span class="rating-stars" data-rating="${avgRating.toFixed(1)}">
                                ${generateStarHTML(avgRating)}
                            </span>
                            <span class="rating-avg">${avgRating.toFixed(1)} / 5.0</span>
                            <span class="review-count">(${productReviews.length} review${productReviews.length !== 1 ? 's' : ''})</span>
                        </div>
                    </div>
                </div>
                <div class="review-items">
        `;
        
        // Add each review
        productReviews.forEach(review => {
            html += generateReviewHTML(review);
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    reviewsContainer.innerHTML = html;
}

// Generate star HTML for rating
function generateStarHTML(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    let html = '';
    
    for (let i = 0; i < 5; i++) {
        if (i < fullStars) {
            html += '<i class="fa-solid fa-star"></i>';
        } else if (i === fullStars && hasHalfStar) {
            html += '<i class="fa-solid fa-star-half-stroke"></i>';
        } else {
            html += '<i class="fa-regular fa-star"></i>';
        }
    }
    
    return html;
}

// Generate HTML for a single review
function generateReviewHTML(review) {
    const date = new Date(review.created_at);
    const formattedDate = date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
    
    const productImage = review.product_image || '/uploads/products/default.jpg';
    
    return `
        <div class="review-item" data-rating="${review.rating}">
            <div class="review-header">
                <div class="customer-info">
                    <span class="customer-name">${escapeHtml(review.customer_name)}</span>
                    <span class="review-date">${formattedDate}</span>
                </div>
                <div class="review-rating">
                    ${generateStarHTML(review.rating)}
                    <span class="rating-number">${review.rating}.0</span>
                </div>
            </div>
            ${review.product_image ? `
            <div class="review-product-info">
                <img src="${productImage}" alt="Product" class="review-product-img" onerror="this.src='/uploads/products/default.jpg'">
                <span class="review-product-name">${escapeHtml(review.product_name)}</span>
            </div>
            ` : ''}
            ${review.comment ? `
            <div class="review-content">
                <p>${escapeHtml(review.comment)}</p>
            </div>
            ` : ''}
        </div>
    `;
}

// Update dashboard stat card rating
function updateDashboardRating(rating) {
    const avgRatingElement = document.getElementById('avgRating');
    if (avgRatingElement) {
        avgRatingElement.textContent = rating.toFixed(1);
    }
}

// Filter reviews by rating
let currentFilter = 'all';

function filterReviewsByRating(rating) {
    currentFilter = rating;
    
    // Update filter button states
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.classList.remove('active');
        const btnText = btn.textContent.trim();
        if ((rating === 'all' && btnText === 'All') || 
            (rating !== 'all' && btnText.startsWith(rating))) {
            btn.classList.add('active');
        }
    });
    
    // Filter review items
    const reviewItems = document.querySelectorAll('.review-item');
    reviewItems.forEach(item => {
        const itemRating = item.getAttribute('data-rating');
        if (rating === 'all' || itemRating === rating) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// Search/filter reviews
function filterReviews() {
    const searchTerm = document.getElementById('reviewSearch').value.toLowerCase();
    const reviewSections = document.querySelectorAll('.product-review-section');
    
    reviewSections.forEach(section => {
        const productName = section.querySelector('h4').textContent.toLowerCase();
        const reviewItems = section.querySelectorAll('.review-item');
        let hasVisibleReviews = false;
        
        reviewItems.forEach(item => {
            const customerName = item.querySelector('.customer-name').textContent.toLowerCase();
            const reviewContent = item.querySelector('.review-content p')?.textContent.toLowerCase() || '';
            const itemRating = item.getAttribute('data-rating');
            
            const matchesSearch = productName.includes(searchTerm) || 
                                customerName.includes(searchTerm) || 
                                reviewContent.includes(searchTerm);
            
            const matchesFilter = currentFilter === 'all' || itemRating === currentFilter;
            
            if (matchesSearch && matchesFilter) {
                item.style.display = 'block';
                hasVisibleReviews = true;
            } else {
                item.style.display = 'none';
            }
        });
        
        // Hide product section if no reviews match
        section.style.display = hasVisibleReviews ? 'block' : 'none';
    });
}

// HTML escape helper
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-refresh ratings every 30 seconds when on reviews section
let ratingsRefreshInterval = null;

function startRatingsAutoRefresh() {
    // Clear any existing interval
    if (ratingsRefreshInterval) {
        clearInterval(ratingsRefreshInterval);
    }
    
    // Refresh every 30 seconds
    ratingsRefreshInterval = setInterval(() => {
        const reviewsSection = document.getElementById('reviewsSection');
        if (reviewsSection && reviewsSection.classList.contains('active')) {
            loadSellerRatings();
        }
    }, 30000);
}

function stopRatingsAutoRefresh() {
    if (ratingsRefreshInterval) {
        clearInterval(ratingsRefreshInterval);
        ratingsRefreshInterval = null;
    }
}

// Don't auto-load on page load - let seller_dashboard.js handle it
// This script provides helper functions but doesn't override the main loadReviews
// Only initialize if we're explicitly called

// Clean up on page unload
window.addEventListener('beforeunload', stopRatingsAutoRefresh);

// Don't override window.loadReviews - let seller_dashboard.js handle it
// This script just provides additional rating display functionality
// The main loadReviews() in seller_dashboard.js will call the real endpoints
