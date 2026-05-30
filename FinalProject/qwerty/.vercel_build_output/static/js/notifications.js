/**
 * Notification System
 * Beautiful toast notifications for user feedback
 */

(function() {
    'use strict';
    
    // Create notification container
    function createNotificationContainer() {
        if (document.getElementById('hub-notifications-container')) return;
        
        const container = document.createElement('div');
        container.id = 'hub-notifications-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 999999;
            max-width: 400px;
            pointer-events: none;
        `;
        document.body.appendChild(container);
    }
    
    /**
     * Show notification
     * @param {string} message - The message to display
     * @param {string} type - Type: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in ms (0 = no auto-dismiss)
     */
    function showNotification(message, type = 'info', duration = 4000) {
        createNotificationContainer();
        
        const container = document.getElementById('hub-notifications-container');
        const notification = document.createElement('div');
        
        // Icons and colors for different types
        const config = {
            success: {
                icon: '✓',
                bg: 'linear-gradient(135deg, #28a745 0%, #218838 100%)',
                iconBg: '#1e7e34'
            },
            error: {
                icon: '✕',
                bg: 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)',
                iconBg: '#bd2130'
            },
            warning: {
                icon: '⚠',
                bg: 'linear-gradient(135deg, #ffc107 0%, #e0a800 100%)',
                iconBg: '#d39e00'
            },
            info: {
                icon: 'ℹ',
                bg: 'linear-gradient(135deg, #17a2b8 0%, #138496 100%)',
                iconBg: '#117a8b'
            }
        };
        
        const settings = config[type] || config.info;
        
        notification.style.cssText = `
            display: flex;
            align-items: center;
            gap: 15px;
            background: ${settings.bg};
            color: white;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
            margin-bottom: 12px;
            font-size: 15px;
            font-weight: 500;
            pointer-events: auto;
            animation: slideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            max-width: 100%;
            word-wrap: break-word;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        `;
        
        notification.innerHTML = `
            <div style="
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: ${settings.iconBg};
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                font-weight: bold;
                flex-shrink: 0;
            ">${settings.icon}</div>
            <div style="flex: 1; line-height: 1.4;">${message}</div>
            <button onclick="this.parentElement.remove()" style="
                background: rgba(255, 255, 255, 0.2);
                border: none;
                color: white;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                transition: background 0.2s;
                flex-shrink: 0;
            " onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">×</button>
        `;
        
        container.appendChild(notification);
        
        // Auto-dismiss if duration is set
        if (duration > 0) {
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                setTimeout(() => notification.remove(), 300);
            }, duration);
        }
        
        return notification;
    }
    
    /**
     * Convenience methods
     */
    function success(message, duration = 4000) {
        return showNotification(message, 'success', duration);
    }
    
    function error(message, duration = 5000) {
        return showNotification(message, 'error', duration);
    }
    
    function warning(message, duration = 4500) {
        return showNotification(message, 'warning', duration);
    }
    
    function info(message, duration = 4000) {
        return showNotification(message, 'info', duration);
    }
    
    /**
     * Add CSS animations
     */
    function addStyles() {
        if (document.getElementById('hub-notification-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'hub-notification-styles';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOut {
                from {
                    transform: translateX(0) scale(1);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px) scale(0.8);
                    opacity: 0;
                }
            }
            
            @media (max-width: 768px) {
                #hub-notifications-container {
                    left: 10px;
                    right: 10px;
                    top: 10px;
                    max-width: none;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Initialize
    addStyles();
    
    // Expose to window
    window.hubNotify = {
        show: showNotification,
        success: success,
        error: error,
        warning: warning,
        info: info
    };
    
    // Also expose as simpler API
    window.notify = {
        success: success,
        error: error,
        warning: warning,
        info: info
    };
    
})();
