/**
 * Customer Reviews System - Frontend JavaScript
 * Handles review submission, display, and management
 */

if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = window.location.origin;
}
if (typeof API_BASE === 'undefined') {
    var API_BASE = window.API_BASE;
}

// Load customer reviews on page load
async function loadCustomerReviews() {
    const token = localStorage.getItem('hub_access_token');
    if (!token) return;

    // Check if user is customer
    const role = getRoleFromToken();
    if (role !== 'customer') {
        document.getElementById('reviewsSection').style.display = 'none';
        return;
    }

    try {
        // Load existing reviews
        const reviewsResponse = await fetch(`${API_BASE}/api/customer/reviews`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (reviewsResponse.ok) {
            const reviewsData = await reviewsResponse.json();
            displayReviews(reviewsData.data.reviews || []);
        } else {
            document.getElementById('reviewsContainer').innerHTML = '<p style="text-align: center; color: #666;">Failed to load reviews.</p>';
        }

        // Load reviewable products (using new endpoint)
        const reviewableResponse = await fetch(`${API_BASE}/api/customer/products/reviewable`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (reviewableResponse.ok) {
            const reviewableData = await reviewableResponse.json();
            // New endpoint returns products array directly in data.products
            const products = reviewableData.data?.products || reviewableData.products || [];
            // Convert products to reviewable_items format for compatibility
            const reviewableItems = products.map(p => ({
                order_id: p.order_id,
                product_id: p.product_id,
                product_name: p.product_name,
                product_image: p.product_image,
                seller_name: p.seller_name
            }));
            displayReviewableOrders(reviewableItems);
        }

    } catch (error) {
        console.error('Error loading reviews:', error);
        document.getElementById('reviewsContainer').innerHTML = '<p style="text-align: center; color: #d32f2f;">Error loading reviews.</p>';
    }
}

// Display existing reviews
function displayReviews(reviews) {
    const container = document.getElementById('reviewsContainer');
    
    if (reviews.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No reviews yet. Purchase and review products to see them here!</p>';
        return;
    }

    container.innerHTML = reviews.map(review => `
        <div class="review-card">
            <div class="review-header">
                <div class="review-product-info">
                    <img src="${review.product_image || 'https://via.placeholder.com/60'}" 
                         alt="${review.product_name}" 
                         class="review-product-image">
                    <div class="review-product-details">
                        <h4>${review.product_name}</h4>
                        <p>Sold by: ${review.seller_name}</p>
                    </div>
                </div>
                <div class="review-rating">
                    ${generateStarRating(review.rating)}
                </div>
            </div>
            ${review.comment ? `<div class="review-content">${escapeHtml(review.comment)}</div>` : ''}
            <div class="review-meta">
                <span><i class="far fa-calendar"></i> ${formatDate(review.created_at)}</span>
                <div class="review-actions">
                    <button class="btn-delete" onclick="deleteReview(${review.id})">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// Display reviewable orders
function displayReviewableOrders(items) {
    const container = document.getElementById('reviewableOrdersContainer');
    const section = document.getElementById('reviewableOrdersSection');
    
    if (items.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = items.map(item => `
        <div class="reviewable-item">
            <div class="reviewable-info">
                <img src="${item.product_image || 'https://via.placeholder.com/50'}" 
                     alt="${item.product_name}">
                <div>
                    <strong>${item.product_name}</strong>
                    <p style="margin: 4px 0 0 0; font-size: 0.9em; color: #666;">
                        Order #${item.order_id} • ${item.seller_name}
                    </p>
                </div>
            </div>
            <button class="btn-write-review" onclick="openReviewModal(${item.order_id}, ${item.product_id}, '${escapeHtml(item.product_name)}', '${item.product_image || ''}', '${escapeHtml(item.seller_name)}')">
                <i class="fas fa-pen"></i> Write Review
            </button>
        </div>
    `).join('');
}

// Generate star rating HTML
function generateStarRating(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= rating) {
            stars += '<i class="fas fa-star star"></i>';
        } else {
            stars += '<i class="far fa-star star-empty"></i>';
        }
    }
    return stars;
}

// Open review modal
function openReviewModal(orderId, productId, productName, productImage, sellerName) {
    document.getElementById('reviewModal').classList.add('active');
    document.getElementById('reviewOrderId').value = orderId;
    document.getElementById('reviewProductId').value = productId;
    document.getElementById('reviewProductName').textContent = productName;
    document.getElementById('reviewSellerName').textContent = `Sold by: ${sellerName}`;
    document.getElementById('reviewProductImage').src = productImage || 'https://via.placeholder.com/60';
    document.getElementById('reviewComment').value = '';
    document.getElementById('charCount').textContent = '0/500';
    setRating(0);
}

// Close review modal
function closeReviewModal() {
    document.getElementById('reviewModal').classList.remove('active');
}

// Set rating
function setRating(rating) {
    document.getElementById('reviewRatingValue').value = rating;
    const stars = document.querySelectorAll('.rating-input .star');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
}

// Update character count
function updateCharCount() {
    const textarea = document.getElementById('reviewComment');
    const count = textarea.value.length;
    document.getElementById('charCount').textContent = `${count}/500`;
    
    if (count > 500) {
        document.getElementById('charCount').style.color = '#d32f2f';
    } else {
        document.getElementById('charCount').style.color = '#888';
    }
}

// Submit review
async function submitReview(event) {
    event.preventDefault();
    
    const token = localStorage.getItem('hub_access_token');
    if (!token) {
        alert('Please log in to submit a review');
        return;
    }

    const orderId = document.getElementById('reviewOrderId').value;
    const productId = document.getElementById('reviewProductId').value;
    const rating = parseInt(document.getElementById('reviewRatingValue').value);
    const comment = document.getElementById('reviewComment').value.trim();

    // Validation
    if (!rating || rating < 1 || rating > 5) {
        alert('Please select a rating (1-5 stars)');
        return;
    }

    if (comment.length > 500) {
        alert('Comment must not exceed 500 characters');
        return;
    }

    // Disable submit button
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    try {
        const response = await fetch(`${API_BASE}/api/customer/reviews`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                order_id: parseInt(orderId),
                product_id: parseInt(productId),
                rating: rating,
                comment: comment || null,
                images: []
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            alert('Review submitted successfully!');
            closeReviewModal();
            loadCustomerReviews(); // Reload reviews
        } else {
            alert(data.message || 'Failed to submit review. Please try again.');
        }

    } catch (error) {
        console.error('Error submitting review:', error);
        alert('Error submitting review. Please try again.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Review';
    }
}

// Delete review
async function deleteReview(reviewId) {
    if (!confirm('Are you sure you want to delete this review? This action cannot be undone.')) {
        return;
    }

    const token = localStorage.getItem('hub_access_token');
    if (!token) return;

    try {
        const response = await fetch(`${API_BASE}/api/customer/reviews/${reviewId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const data = await response.json();

        if (response.ok && data.success) {
            alert('Review deleted successfully');
            loadCustomerReviews(); // Reload reviews
        } else {
            alert(data.message || 'Failed to delete review');
        }

    } catch (error) {
        console.error('Error deleting review:', error);
        alert('Error deleting review. Please try again.');
    }
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function getRoleFromToken() {
    const token = localStorage.getItem('hub_access_token');
    if (!token) return 'customer';
    try {
        const parts = token.split('.');
        const decoded = JSON.parse(atob(parts[1]));
        return decoded.role || 'customer';
    } catch (e) {
        return 'customer';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load reviews if on account page and user is customer
    if (document.getElementById('reviewsSection')) {
        setTimeout(loadCustomerReviews, 500); // Slight delay to ensure token is loaded
    }
});
