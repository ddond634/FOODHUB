// Cart/Wishlist badge and dropdown sync script
// This script adds event listeners to sync badges after cart/wishlist operations

(function() {
    'use strict';
    
    if (typeof window.API_BASE === 'undefined' || window.API_BASE === window.location.origin) {
        window.API_BASE = window.SUPABASE_COMMERCE_API || `${window.location.origin}/api`;
    }
    if (typeof API_BASE === 'undefined') {
        var API_BASE = window.API_BASE;
    }
    
    // Helper to check if user is logged in
    function isLoggedIn() {
        return !!localStorage.getItem('hub_access_token');
    }
    
    // Update cart badge from backend
    async function syncCartBadge() {
        const badge = document.querySelector('#cartBtn .badge');
        
        if (!isLoggedIn()) {
            // Hide badge when not logged in
            if (badge) {
                badge.style.display = 'none';
            }
            return;
        }
        
        try {
            const token = localStorage.getItem('hub_access_token');
            const response = await fetch(`${API_BASE}/cart`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            
            // Backend returns { success: true, data: { items: [...] }, message: '...' }
            if (data.success && data.data && data.data.items) {
                const totalItems = data.data.items.reduce((sum, item) => sum + (item.quantity || 0), 0);
                if (badge) {
                    badge.textContent = totalItems;
                    // Show badge only if there are items
                    badge.style.display = totalItems > 0 ? 'inline-block' : 'none';
                    badge.classList.add('pulse');
                    setTimeout(() => badge.classList.remove('pulse'), 600);
                }
            } else if (badge) {
                // No items or error - hide badge
                badge.style.display = 'none';
            }
        } catch (error) {
            console.error('Error syncing cart badge:', error);
            if (badge) {
                badge.style.display = 'none';
            }
        }
    }
    
    // Update wishlist badge from backend
    async function syncWishlistBadge() {
        const badge = document.querySelector('#wishlistBtn .badge');
        
        if (!isLoggedIn()) {
            // Hide badge when not logged in
            if (badge) {
                badge.style.display = 'none';
            }
            return;
        }
        
        try {
            const token = localStorage.getItem('hub_access_token');
            const response = await fetch(`${API_BASE}/wishlist`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            
            if (data.success && data.items) {
                if (badge) {
                    badge.textContent = data.items.length;
                    // Show badge only if there are items
                    badge.style.display = data.items.length > 0 ? 'inline-block' : 'none';
                    badge.classList.add('pulse');
                    setTimeout(() => badge.classList.remove('pulse'), 600);
                }
            } else if (badge) {
                // No items or error - hide badge
                badge.style.display = 'none';
            }
        } catch (error) {
            console.error('Error syncing wishlist badge:', error);
            if (badge) {
                badge.style.display = 'none';
            }
        }
    }
    
    // Sync cart dropdown
    async function syncCartDropdown() {
        if (!isLoggedIn()) return;
        
        const dd = document.querySelector('#cartDropdown');
        if (!dd) return;
        
        try {
            const token = localStorage.getItem('hub_access_token');
            const response = await fetch(`${API_BASE}/cart`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            
            const itemsEl = dd.querySelector('.dropdown-items');
            const footerCount = dd.querySelector('.items-count');
            if (!itemsEl) return;
            
            // Backend returns { success: true, data: { items: [...] }, message: '...' }
            const items = (data.success && data.data && data.data.items) ? data.data.items : [];
            
            if (items.length === 0) {
                itemsEl.innerHTML = '<div style="padding:18px;color:#666">Your cart is empty</div>';
                if (footerCount) footerCount.textContent = '0 items in cart';
                return;
            }
            
            const imageBase = window.SUPABASE_COMMERCE_API || API_BASE.replace('/api', '');
            const cartItems = items.slice(0, 5);
            itemsEl.innerHTML = cartItems.map(item => {
                const imageUrl = item.img_url && item.img_url.startsWith('http')
                    ? item.img_url
                    : `${imageBase}${item.img_url || '/uploads/placeholder.jpg'}`;

                return `
                <div class="dropdown-item">
                    <img src="${imageUrl}"
                         alt="${item.title}" loading="lazy"
                         onerror="this.src='https://via.placeholder.com/60'">
                    <div class="item-details">
                        <p class="item-name">${item.title}</p>
                        <p class="item-price">₱${parseFloat(item.unit_price).toFixed(2)} × ${item.quantity}</p>
                    </div>
                </div>
            `;
            }).join('');
            
            const totalQty = items.reduce((sum, item) => sum + item.quantity, 0);
            if (footerCount) footerCount.textContent = `${totalQty} items in cart`;
        } catch (error) {
            console.error('Error syncing cart dropdown:', error);
        }
    }
    
    // Sync wishlist dropdown
    async function syncWishlistDropdown() {
        if (!isLoggedIn()) return;
        
        const dd = document.querySelector('#wishlistDropdown');
        if (!dd) return;
        
        try {
            const token = localStorage.getItem('hub_access_token');
            const response = await fetch(`${API_BASE}/wishlist`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            
            const header = '<div class="dropdown-header">Recently Added to Wishlist</div>';
            let items = '<div class="dropdown-items">';
            
            if (!data.success || !data.items || data.items.length === 0) {
                items += '<div style="padding:18px;color:#666">Your wishlist is empty</div>';
            } else {
                const recentItems = data.items.slice(0, 5);
                items += recentItems.map(item => {
                    // Handle price - use price if available, otherwise use price_total, fallback to 0
                    let price = 0;
                    if (item.price && !isNaN(parseFloat(item.price))) {
                        price = parseFloat(item.price);
                    } else if (item.price_total && !isNaN(parseFloat(item.price_total))) {
                        const quantity = parseInt(item.quantity) || 1;
                        price = parseFloat(item.price_total) / quantity;
                    }
                    
                    const wishlistImageBase = window.SUPABASE_COMMERCE_API || API_BASE.replace('/api', '');
                    return `
                    <div class="dropdown-item">
                        <img src="${item.image_url && item.image_url.startsWith('http') ? item.image_url : `${wishlistImageBase}/${item.image_url || 'uploads/placeholder.jpg'}`}" 
                             alt="${item.name || 'Product'}" loading="lazy"
                             onerror="this.src='https://via.placeholder.com/60'">
                        <div class="item-details">
                            <p class="item-name">${item.name || 'Unknown Product'}</p>
                            <p class="item-price">₱${price.toFixed(2)}</p>
                        </div>
                    </div>
                `;
                }).join('');
            }
            items += '</div>';
            
            const footer = `<div class="dropdown-footer"><p class="items-count">${data.items ? data.items.length : 0} item(s) in wishlist</p><button class="view-btn" onclick="window.location.href='wishlist.html'">View My Wishlist</button></div>`;
            dd.innerHTML = header + items + footer;
        } catch (error) {
            console.error('Error syncing wishlist dropdown:', error);
        }
    }
    
    // Expose sync functions globally
    window.syncCartBadge = syncCartBadge;
    window.syncWishlistBadge = syncWishlistBadge;
    window.syncCartDropdown = syncCartDropdown;
    window.syncWishlistDropdown = syncWishlistDropdown;
    
    // Auto-sync on page load
    document.addEventListener('DOMContentLoaded', function() {
        // Always call sync functions - they will hide badges if not logged in
        syncCartBadge();
        syncWishlistBadge();
    });
    
    console.log('✅ Cart/Wishlist sync module loaded');
})();
