/**
 * Authentication Guard
 * Ensures clean authentication state across all pages
 */

(function() {
    'use strict';
    
    /**
     * Clean up any orphaned or invalid authentication data
     */
    function cleanupOrphanedAuthData() {
        const token = localStorage.getItem('hub_access_token');
        
        // If no token exists, ensure ALL user-related data is cleared
        if (!token) {
            // Clear ALL cart and wishlist data when logged out
            Object.keys(localStorage).forEach(key => {
                if (key.includes('hub_cart') || key.includes('hub_wishlist')) {
                    console.log('🧹 Removing cart/wishlist data:', key);
                    localStorage.removeItem(key);
                }
            });
            
            const userDataKeys = [
                'hub_refresh_token',
                'hub_user_id',
                'hub_user_role',
                'hub_user_email',
                'customer_name',
                'seller_id',
                'rider_id',
                'user_data',
                'current_user'
            ];
            
            userDataKeys.forEach(key => {
                if (localStorage.getItem(key)) {
                    console.log('🧹 Removing orphaned data:', key);
                    localStorage.removeItem(key);
                }
            });
            
            // Clear any session storage
            sessionStorage.clear();
        }
    }
    
    /**
     * Validate token format (basic check)
     */
    function isValidTokenFormat(token) {
        if (!token || typeof token !== 'string') return false;
        // JWT tokens have 3 parts separated by dots
        const parts = token.split('.');
        return parts.length === 3;
    }
    
    /**
     * Check if token is expired (without API call)
     */
    function isTokenExpired(token) {
        try {
            const parts = token.split('.');
            if (parts.length !== 3) return true;
            
            const payload = JSON.parse(atob(parts[1]));
            if (!payload.exp) return false; // No expiry set
            
            // Check if expired (with 30 second buffer)
            const now = Math.floor(Date.now() / 1000);
            return payload.exp < (now + 30);
        } catch (e) {
            console.error('Error checking token expiry:', e);
            return true; // Assume expired if we can't parse
        }
    }
    
    /**
     * Validate authentication state
     */
    function validateAuthState() {
        const token = localStorage.getItem('hub_access_token');
        
        if (token) {
            // Token exists - validate format and expiry
            if (!isValidTokenFormat(token)) {
                console.warn('⚠️ Invalid token format detected - clearing auth data');
                clearAuthState();
                return false;
            }
            
            if (isTokenExpired(token)) {
                console.warn('⚠️ Expired token detected - clearing auth data');
                clearAuthState();
                return false;
            }
            
            return true;
        }
        
        // No token - ensure clean state
        cleanupOrphanedAuthData();
        return false;
    }
    
    /**
     * Clear all authentication state
     */
    function clearAuthState() {
        // Clear tokens
        localStorage.removeItem('hub_access_token');
        localStorage.removeItem('hub_refresh_token');
        
        // Clear cart and wishlist data (all user-specific versions)
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('hub_cart_v1') || key.startsWith('hub_wishlist_v1')) {
                localStorage.removeItem(key);
            }
        });
        
        // Clear user data
        cleanupOrphanedAuthData();
    }
    
    /**
     * Get user role from token
     */
    function getUserRole() {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return null;
        
        try {
            const parts = token.split('.');
            if (parts.length !== 3) return null;
            const decoded = JSON.parse(atob(parts[1]));
            return decoded.role || null;
        } catch (e) {
            console.error('Error decoding token for role:', e);
            return null;
        }
    }
    
    /**
     * Protect page - redirect to login if not authenticated
     */
    function protectPage() {
        const currentPath = window.location.pathname.toLowerCase();
        const protectedPages = [
            'account.html',
            'seller_dashboard.html',
            'rider_dashboard.html',
            'admin_dashboard.html',
            'seller_inventory.html'
        ];
        
        const isProtected = protectedPages.some(page => currentPath.includes(page.toLowerCase()));
        
        if (isProtected) {
            const isAuthenticated = validateAuthState();
            
            if (!isAuthenticated) {
                console.log('🔒 Protected page accessed without authentication - redirecting to login');
                window.location.href = '/loginregister.html';
                return false;
            }
        }
        
        // Check if admin is trying to access customer pages
        const role = getUserRole();
        if (role === 'admin') {
            const customerPages = ['index.html', 'shop.html', 'cart.html', 'wishlist.html', 'checkout.html'];
            const isCustomerPage = customerPages.some(page => currentPath.includes(page.toLowerCase()));
            
            if (isCustomerPage) {
                console.log('🔒 Admin detected on customer page - redirecting to admin dashboard');
                window.location.href = '/admin_dashboard.html';
                return false;
            }
        }
        
        // For public pages, just validate and clean up
        if (!isProtected) {
            validateAuthState();
        }
        
        return true;
    }
    
    /**
     * Initialize on page load
     */
    function init() {
        // SKIP auth pages - don't run protection or cleanup
        const currentPath = window.location.pathname.toLowerCase();
        const isAuthPage = currentPath.includes('loginregister') || 
                          currentPath.includes('login.html') || 
                          currentPath.includes('register.html');
        
        if (isAuthPage) {
            console.log('✅ Auth page detected - skipping auth guard');
            return;
        }
        
        // Run cleanup and validation for other pages
        protectPage();
        
        // Monitor storage changes from other tabs
        window.addEventListener('storage', function(e) {
            if (e.key === 'hub_access_token' && !e.newValue) {
                // Token was removed in another tab
                console.log('🔒 Token removed in another tab - logging out');
                clearAuthState();
                
                // Redirect if on protected page
                const currentPath = window.location.pathname.toLowerCase();
                const protectedPages = ['account', 'dashboard', 'seller', 'rider', 'admin'];
                const isProtected = protectedPages.some(page => currentPath.includes(page));
                
                if (isProtected) {
                    window.location.href = '/loginregister.html';
                }
            }
        });
    }
    
    // Initialize immediately (synchronous)
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Expose utilities for manual use
    window.hubAuthGuard = {
        validate: validateAuthState,
        clear: clearAuthState,
        protect: protectPage,
        cleanup: cleanupOrphanedAuthData
    };
    
})();
