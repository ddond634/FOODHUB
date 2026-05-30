/**
 * Session Manager - Auto-logout on server restart
 * This script validates sessions against the server instance
 * and clears all local data if server has restarted
 */

(function() {
    'use strict';

    // Static/Vercel + Supabase deploy has no Flask server — disable all session polling
    if (window.SUPABASE_AUTH_API && !window.location.hostname.match(/^(localhost|127\.0\.0\.1)$/)) {
        console.log('Static Supabase deploy — session validator disabled');
        return;
    }
    
    const SESSION_CHECK_KEY = 'hub_server_instance';
    const LAST_CHECK_KEY = 'hub_last_session_check';
    const CHECK_INTERVAL = 15 * 60 * 1000; // Check every 15 minutes
    
    /**
     * Clear all session data
     */
    function clearAllSessionData() {
        console.log('🔒 Clearing all session data due to server restart');
        
        // Clear all localStorage items (not just hub_ prefixed)
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            // Remove all keys except those we want to preserve
            if (key && !key.includes('_cookie_consent') && !key.includes('_preferences')) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(key => localStorage.removeItem(key));
        
        // Clear sessionStorage
        sessionStorage.clear();
        
        // Clear cookies
        document.cookie.split(";").forEach(function(c) {
            document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
        
        // Force reset badges to 0
        const cartBadge = document.querySelector('#cartBtn .badge');
        const wishlistBadge = document.querySelector('#wishlistBtn .badge');
        if (cartBadge) cartBadge.textContent = '0';
        if (wishlistBadge) wishlistBadge.textContent = '0';
        
        console.log('✅ Session data cleared');
    }
    
    /**
     * Check if server has restarted
     */
    async function checkServerInstance() {
        // Static/Vercel deploy has no Flask server — skip instance checks
        if (window.SUPABASE_AUTH_API && !window.location.hostname.match(/^(localhost|127\.0\.0\.1)$/)) {
            return true;
        }
        try {
            const response = await fetch('/api/server/instance');
            if (!response.ok) {
                console.warn('Failed to check server instance');
                return true; // Assume valid if can't check
            }
            
            const data = await response.json();
            const currentInstanceId = data.instance_id;
            const storedInstanceId = localStorage.getItem(SESSION_CHECK_KEY);
            
            // If no stored instance, this is first visit - store it
            if (!storedInstanceId) {
                localStorage.setItem(SESSION_CHECK_KEY, currentInstanceId);
                localStorage.setItem(LAST_CHECK_KEY, Date.now().toString());
                console.log('✅ Server instance stored:', currentInstanceId);
                return true;
            }
            
            // If instance ID changed, server has restarted
            if (storedInstanceId !== currentInstanceId) {
                console.warn('⚠️ Server instance changed - clearing old session');
                
                // Only clear if user was actually logged in
                const hasToken = localStorage.getItem('hub_access_token');
                if (hasToken) {
                    clearAllSessionData();
                }
                
                // Update to new instance
                localStorage.setItem(SESSION_CHECK_KEY, currentInstanceId);
                return false;
            }
            
            // Update last check time
            localStorage.setItem(LAST_CHECK_KEY, Date.now().toString());
            return true;
            
        } catch (error) {
            console.error('Error checking server instance:', error);
            return true; // Don't invalidate on error
        }
    }
    
    /**
     * Validate current session
     */
    async function validateSession() {
        const token = localStorage.getItem('hub_access_token');
        
        // If no token, no session to validate
        if (!token) {
            return true;
        }
        
        // Check if server has restarted
        const isValid = await checkServerInstance();
        
        if (!isValid) {
            // Session invalidated - redirect to home with message
            const currentPath = window.location.pathname.toLowerCase();
            const isAuthPage = currentPath.includes('loginregister') || 
                              currentPath.includes('login') || 
                              currentPath.includes('register');
            const isDashboard = currentPath.includes('dashboard') || 
                               currentPath.includes('seller') || 
                               currentPath.includes('rider') || 
                               currentPath.includes('admin');
            
            // Don't redirect if on auth page or dashboard (user will be prompted on next protected action)
            if (isDashboard && !isAuthPage) {
                localStorage.setItem('hub_session_expired', 'true');
                window.location.href = '/index.html';
            }
        }
        
        return isValid;
    }
    
    /**
     * Check if session validation is needed
     */
    function shouldCheckSession() {
        const lastCheck = localStorage.getItem(LAST_CHECK_KEY);
        if (!lastCheck) return true;
        
        const timeSinceLastCheck = Date.now() - parseInt(lastCheck);
        return timeSinceLastCheck > CHECK_INTERVAL;
    }
    
    /**
     * Initialize session validator
     */
    async function initSessionValidator() {
        // Check on page load
        if (shouldCheckSession()) {
            await validateSession();
        }
        
        // Set up periodic checks
        setInterval(async () => {
            if (shouldCheckSession()) {
                await validateSession();
            }
        }, CHECK_INTERVAL);
        
        // Check on visibility change (when tab becomes active)
        document.addEventListener('visibilitychange', async () => {
            if (!document.hidden && shouldCheckSession()) {
                await validateSession();
            }
        });
    }
    
    /**
     * Show session expired message on index page
     */
    function showSessionExpiredMessage() {
        if (localStorage.getItem('hub_session_expired') === 'true') {
            localStorage.removeItem('hub_session_expired');
            
            // Create notification
            const notification = document.createElement('div');
            notification.className = 'session-expired-notification';
            notification.innerHTML = `
                <div style="
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #f59e0b;
                    color: white;
                    padding: 15px 25px;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    z-index: 10000;
                    font-size: 14px;
                    max-width: 400px;
                    animation: slideIn 0.3s ease-out;
                ">
                    ⚠️ Session expired. Please log in again.
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Remove after 5 seconds
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => notification.remove(), 300);
            }, 5000);
        }
    }
    
    /**
     * Protect dashboard pages - redirect if no valid session
     */
    function protectDashboardPage() {
        const currentPath = window.location.pathname;
        const isProtectedPage = currentPath.includes('dashboard') || 
                               currentPath.includes('seller_dashboard') || 
                               currentPath.includes('rider_dashboard') || 
                               currentPath.includes('admin_dashboard') ||
                               currentPath.includes('account.html');
        
        if (isProtectedPage) {
            const token = localStorage.getItem('hub_access_token');
            if (!token) {
                console.warn('No valid token - redirecting to login');
                localStorage.setItem('hub_session_expired', 'true');
                window.location.href = '/loginregister.html';
                return false;
            }
        }
        
        return true;
    }
    
    // Initialize on page load
    // SKIP initialization on login/register pages
    const currentPath = window.location.pathname.toLowerCase();
    const isAuthPage = currentPath.includes('loginregister') || 
                      currentPath.includes('login.html') || 
                      currentPath.includes('register.html');
    
    if (!isAuthPage) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                protectDashboardPage();
                initSessionValidator();
                showSessionExpiredMessage();
            });
        } else {
            protectDashboardPage();
            initSessionValidator();
            showSessionExpiredMessage();
        }
    } else {
        console.log('✅ Auth page detected - skipping session validator');
    }
    
    // Add slide animations
    if (!document.getElementById('session-validator-styles')) {
        const style = document.createElement('style');
        style.id = 'session-validator-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(400px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(400px); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Expose for manual validation if needed
    window.hubSessionValidator = {
        validate: validateSession,
        clear: clearAllSessionData,
        check: checkServerInstance
    };
    
})();
