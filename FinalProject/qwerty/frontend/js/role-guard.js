/**
 * Role-Based Access Control Guard
 * Prevents Admin, Seller, and Rider from accessing public pages
 * Automatically redirects them to their respective dashboards
 */

(function() {
    'use strict';
    
    // Role to dashboard mapping
    const ROLE_DASHBOARDS = {
        'admin': '/admin_dashboard.html',
        'seller': '/seller_dashboard.html',
        'rider': '/rider_dashboard.html',
        'customer': '/account.html',
        'buyer': '/account.html'
    };
    
    // Pages that should be restricted for system users (admin, seller, rider)
    const PUBLIC_PAGES = [
        '/index.html',
        '/',
        '/about_us.html',
        '/our_services.html',
        '/contact_us.html'
    ];
    
    // Pages that don't require any checks (auth pages)
    const AUTH_PAGES = [
        '/loginregister.html',
        '/login.html',
        '/register.html'
    ];
    
    /**
     * Get current user info from token
     */
    function getCurrentUser() {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return null;
        
        try {
            // Decode JWT token (format: header.payload.signature)
            const payload = token.split('.')[1];
            const decoded = JSON.parse(atob(payload));
            return {
                id: decoded.user_id,
                role: decoded.role,
                email: decoded.email
            };
        } catch (error) {
            console.error('Error decoding token:', error);
            return null;
        }
    }
    
    /**
     * Check if current page is a public page
     */
    function isPublicPage() {
        const currentPath = window.location.pathname.toLowerCase();
        
        // Exact match or root
        if (currentPath === '/' || currentPath === '' || currentPath === '/index.html') {
            return true;
        }
        
        // Check if it's in public pages list
        return PUBLIC_PAGES.some(page => currentPath.endsWith(page.toLowerCase()));
    }
    
    /**
     * Check if current page is an auth page
     */
    function isAuthPage() {
        const currentPath = window.location.pathname.toLowerCase();
        return AUTH_PAGES.some(page => currentPath.includes(page.toLowerCase()));
    }
    
    /**
     * Check if current page is a dashboard
     */
    function isDashboardPage() {
        const currentPath = window.location.pathname.toLowerCase();
        return currentPath.includes('dashboard') || 
               currentPath.includes('account.html');
    }
    
    /**
     * Redirect user to their appropriate dashboard
     */
    function redirectToDashboard(role) {
        const dashboard = ROLE_DASHBOARDS[role];
        if (dashboard && window.location.pathname !== dashboard) {
            console.log(`🔒 Redirecting ${role} to dashboard: ${dashboard}`);
            window.location.replace(dashboard); // Use replace to prevent back button bypass
        }
    }
    
    /**
     * Check if user should be blocked from current page
     */
    function checkAccess() {
        const user = getCurrentUser();
        
        // No user logged in - allow access to public pages
        if (!user) {
            return true;
        }
        
        const currentPath = window.location.pathname.toLowerCase();
        
        // Skip checks for auth pages
        if (isAuthPage()) {
            return true;
        }
        
        // Check if system user (admin, seller, rider) is trying to access public pages
        const isSystemUser = ['admin', 'seller', 'rider'].includes(user.role);
        const onPublicPage = isPublicPage();
        
        if (isSystemUser && onPublicPage) {
            console.warn(`⚠️ ${user.role} attempting to access public page - redirecting to dashboard`);
            redirectToDashboard(user.role);
            return false;
        }
        
        // Check if user is on wrong dashboard
        if (isDashboardPage()) {
            const expectedDashboard = ROLE_DASHBOARDS[user.role];
            
            // Customer trying to access dashboards (except account.html)
            if (user.role === 'customer' && !currentPath.includes('account.html')) {
                const isDashboardAttempt = currentPath.includes('admin_dashboard') || 
                                          currentPath.includes('seller_dashboard') || 
                                          currentPath.includes('rider_dashboard');
                
                if (isDashboardAttempt) {
                    console.warn('⚠️ Customer attempting to access system dashboard - redirecting to homepage');
                    window.location.replace('/index.html');
                    return false;
                }
            }
            
            // System users on wrong dashboard
            if (expectedDashboard && !currentPath.includes(expectedDashboard.replace('/', ''))) {
                console.warn(`⚠️ ${user.role} on wrong dashboard - redirecting to correct one`);
                redirectToDashboard(user.role);
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Prevent back button bypass
     */
    function preventBackButtonBypass() {
        window.addEventListener('popstate', function(event) {
            const user = getCurrentUser();
            if (user && ['admin', 'seller', 'rider'].includes(user.role)) {
                if (isPublicPage()) {
                    console.log('🔒 Back button blocked - redirecting to dashboard');
                    event.preventDefault();
                    redirectToDashboard(user.role);
                }
            }
        });
        
        // Push state to prevent direct back navigation
        if (isPublicPage()) {
            const user = getCurrentUser();
            if (user && ['admin', 'seller', 'rider'].includes(user.role)) {
                history.pushState(null, null, window.location.href);
            }
        }
    }
    
    /**
     * Initialize role guard
     */
    function initRoleGuard() {
        const hasAccess = checkAccess();
        
        if (hasAccess) {
            preventBackButtonBypass();
            
            // Skip periodic re-checks on dashboards — avoids unnecessary work / flicker
            if (!isDashboardPage()) {
                setInterval(checkAccess, 30000);
            }
        }
    }
    
    // Run immediately if DOM is ready, otherwise wait
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRoleGuard);
    } else {
        initRoleGuard();
    }
    
    // Also check on page visibility change (tab switching)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            checkAccess();
        }
    });
    
    // Expose for debugging
    window.hubRoleGuard = {
        check: checkAccess,
        getUser: getCurrentUser,
        redirect: redirectToDashboard
    };
    
    console.log('✅ Role-based access control initialized');
    
})();
