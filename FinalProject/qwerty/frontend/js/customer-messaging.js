/**
 * Customer Messaging Module
 * Handles real-time messaging between customers and sellers
 */

// Configuration
const POLL_INTERVAL = 3000; // Poll every 3 seconds for new messages

// Use existing global API_BASE if already defined by another script to avoid redeclaration SyntaxError
// Fallback to origin-based default
if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = window.location.origin;
}
// Use window.API_BASE directly to avoid redeclaration issues
// Create a local reference only if needed, but prefer using window.API_BASE directly

// State - check if already declared to avoid redeclaration errors
if (typeof currentConversationId === 'undefined') {
    var currentConversationId = null;
}
if (typeof messagePollingInterval === 'undefined') {
    var messagePollingInterval = null;
}
if (typeof conversationPollingInterval === 'undefined') {
    var conversationPollingInterval = null;
}
let isMessagingInitialized = false;

/**
 * Initialize messaging system
 */
function initializeMessaging() {
    if (isMessagingInitialized) return;
    
    console.log('🔧 Initializing customer messaging system...');
    
    // Load conversations when messages tab is active
    loadConversations();
    
    // Set up auto-refresh for conversations list
    startConversationsPolling();
    
    // Update unread count badge
    updateUnreadBadge();
    
    isMessagingInitialized = true;
    console.log('✅ Messaging system initialized');
}

/**
 * Load all conversations for the customer
 */
async function loadConversations() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.error('No authentication token');
            return;
        }
        
        const response = await fetch(`${window.API_BASE}/api/conversations`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success || data.status === 'success') {
            displayConversations(data.data.conversations);
        } else {
            console.error('Failed to load conversations:', data.message);
        }
        
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

/**
 * Display conversations list
 */
function displayConversations(conversations) {
    const container = document.getElementById('conversationsList');
    if (!container) return;
    
    if (!conversations || conversations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comments"></i>
                <p>No conversations yet</p>
                <p class="text-muted">Start a conversation with a seller by clicking "Message Seller" on any product</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    conversations.forEach(conv => {
        const unreadBadge = conv.unread_count > 0 
            ? `<span class="unread-badge">${conv.unread_count}</span>` 
            : '';
        
        const lastMessage = conv.last_message 
            ? truncateText(conv.last_message, 50)
            : 'No messages yet';
        
        const timeAgo = conv.last_message_at 
            ? formatTimeAgo(new Date(conv.last_message_at))
            : '';
        
        html += `
            <div class="conversation-item ${currentConversationId === conv.id ? 'active' : ''}" 
                 onclick="openConversation(${conv.id}, '${conv.seller_name}')">
                <div class="conversation-avatar">
                    <i class="fas fa-store"></i>
                </div>
                <div class="conversation-content">
                    <div class="conversation-header">
                        <span class="seller-name">${conv.seller_name}</span>
                        ${unreadBadge}
                    </div>
                    <div class="last-message">${lastMessage}</div>
                    ${timeAgo ? `<div class="message-time">${timeAgo}</div>` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

/**
 * Create or open conversation with a seller
 * Called when customer clicks "Message Seller"
 * Now opens the blue messenger panel instead of redirecting
 */
async function messageSellerFromProduct(sellerId, sellerName) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            if (window.notify) {
                window.notify.warning('Please log in to message sellers');
            } else {
                alert('Please log in to message sellers');
            }
            localStorage.setItem('returnUrl', window.location.href);
            setTimeout(() => {
                window.location.href = 'loginregister.html';
            }, 1500);
            return;
        }
        
        // Use the new messaging panel function if available
        if (typeof openMessengerPanelWithSeller === 'function') {
            openMessengerPanelWithSeller(sellerId, sellerName);
            return;
        }
        
        // Fallback to old behavior (for account.html messages tab)
        // Create or fetch conversation
        const response = await fetch(`${window.API_BASE}/api/conversations/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ seller_id: sellerId })
        });
        
        const data = await response.json();
        
        if (data.success || data.status === 'success') {
            // Switch to messages tab
            const messagesTab = document.querySelector('[onclick*="messages"]');
            if (messagesTab) {
                messagesTab.click();
            }
            
            // Open the conversation
            setTimeout(() => {
                openConversation(data.data.conversation_id, sellerName);
            }, 100);
        } else {
            if (window.notify) {
                window.notify.error('Failed to start conversation: ' + data.message);
            } else {
                alert('Failed to start conversation: ' + data.message);
            }
        }
        
    } catch (error) {
        console.error('Error creating conversation:', error);
        if (window.notify) {
            window.notify.error('Failed to start conversation. Please try again.');
        } else {
            alert('Failed to start conversation. Please try again.');
        }
    }
}

/**
 * Open a conversation and load messages
 */
async function openConversation(conversationId, sellerName) {
    currentConversationId = conversationId;
    
    // Update UI to show chat window
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) {
        chatContainer.style.display = 'block';
        
        // Set seller name in header
        const sellerNameEl = document.getElementById('chatSellerName');
        if (sellerNameEl) {
            sellerNameEl.textContent = sellerName;
        }
    }
    
    // Highlight selected conversation
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
    event?.target?.closest('.conversation-item')?.classList.add('active');
    
    // Load messages
    await loadMessages(conversationId);
    
    // Mark messages as read
    markMessagesAsRead(conversationId);
    
    // Start polling for new messages
    startMessagePolling(conversationId);
}

/**
 * Load messages for a conversation
 */
async function loadMessages(conversationId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        const response = await fetch(`${window.API_BASE}/api/messages/${conversationId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success || data.status === 'success') {
            displayMessages(data.data.messages);
        } else {
            console.error('Failed to load messages:', data.message);
        }
        
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

/**
 * Mark messages as read
 */
async function markMessagesAsRead(conversationId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        await fetch(`${window.API_BASE}/api/messages/read/${conversationId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
    } catch (error) {
        console.error('Failed to mark messages as read:', error);
    }
}

/**
 * Display messages in chat window
 */
function displayMessages(messages) {
    const container = document.getElementById('messagesContainer');
    if (!container) return;
    
    const token = localStorage.getItem('hub_access_token');
    const payload = parseJwt(token);
    const currentUserId = payload?.id;
    const currentUserRole = payload?.role;
    
    if (!messages || messages.length === 0) {
        container.innerHTML = `
            <div class="empty-messages">
                <i class="fas fa-comment-dots"></i>
                <p>No messages yet. Start the conversation!</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    messages.forEach(msg => {
        const isOwnMessage = msg.sender_role === currentUserRole && msg.sender_id === currentUserId;
        const messageClass = isOwnMessage ? 'message-own' : 'message-other';
        const senderLabel = msg.sender_role === 'seller' ? 'Seller' : 'You';
        const time = formatMessageTime(new Date(msg.created_at));
        
        html += `
            <div class="message ${messageClass}">
                <div class="message-bubble">
                    <div class="message-sender">${senderLabel}</div>
                    <div class="message-text">${escapeHtml(msg.message_text)}</div>
                    <div class="message-time">${time}</div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // Scroll to bottom
    scrollToBottom();
}

/**
 * Send a message
 */
async function sendMessage() {
    const input = document.getElementById('messageInput');
    if (!input) return;
    
    const messageText = input.value.trim();
    if (!messageText || !currentConversationId) return;
    
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        // Disable input while sending
        input.disabled = true;
        
        const response = await fetch(`${window.API_BASE}/api/messages/send`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message_text: messageText
            })
        });
        
        const data = await response.json();
        
        if (data.success || data.status === 'success') {
            // Clear input
            input.value = '';
            
            // Reload messages to show new message
            await loadMessages(currentConversationId);
            
            // Reload conversations list to update last message
            await loadConversations();
        } else {
            alert('Failed to send message: ' + data.message);
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Failed to send message. Please try again.');
    } finally {
        input.disabled = false;
        input.focus();
    }
}

/**
 * Mark messages as read
 */
async function markAsRead(conversationId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        await fetch(`${window.API_BASE}/api/messages/read/${conversationId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Update unread badge
        updateUnreadBadge();
        
    } catch (error) {
        console.error('Error marking messages as read:', error);
    }
}

/**
 * Update unread messages badge
 */
async function updateUnreadBadge() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        const response = await fetch(`${window.API_BASE}/api/messages/unread-count`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success || data.status === 'success') {
            const count = data.data.unread_count;
            
            // Update badge in navbar
            const badge = document.getElementById('messagesBadge');
            if (badge) {
                if (count > 0) {
                    badge.textContent = count > 99 ? '99+' : count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
        }
        
    } catch (error) {
        console.error('Error updating unread badge:', error);
    }
}

/**
 * Start polling for new messages in current conversation
 */
function startMessagePolling(conversationId) {
    // Clear existing interval
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
    }
    
    // Poll for new messages
    messagePollingInterval = setInterval(() => {
        if (currentConversationId === conversationId) {
            loadMessages(conversationId);
        }
    }, POLL_INTERVAL);
}

/**
 * Start polling for conversations updates
 */
function startConversationsPolling() {
    // Clear existing interval
    if (conversationPollingInterval) {
        clearInterval(conversationPollingInterval);
    }
    
    // Poll for conversations updates
    conversationPollingInterval = setInterval(() => {
        loadConversations();
        updateUnreadBadge();
    }, POLL_INTERVAL * 2); // Poll less frequently for conversations
}

/**
 * Stop all polling
 */
function stopMessagingPolling() {
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
        messagePollingInterval = null;
    }
    
    if (conversationPollingInterval) {
        clearInterval(conversationPollingInterval);
        conversationPollingInterval = null;
    }
}

/**
 * Handle Enter key in message input
 */
function handleMessageKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
}

/**
 * Utility: Parse JWT token
 */
function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

/**
 * Utility: Format time ago
 */
function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    
    return date.toLocaleDateString();
}

/**
 * Utility: Format message time
 */
function formatMessageTime(date) {
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

/**
 * Utility: Truncate text
 */
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Utility: Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions for global access
window.initializeMessaging = initializeMessaging;
window.messageSellerFromProduct = messageSellerFromProduct;
window.openConversation = openConversation;
window.sendMessage = sendMessage;
window.handleMessageKeyPress = handleMessageKeyPress;
window.stopMessagingPolling = stopMessagingPolling;
