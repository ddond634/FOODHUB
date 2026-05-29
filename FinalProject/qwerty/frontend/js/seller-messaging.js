/**
 * Seller Messaging Module
 * Handles real-time messaging between sellers and customers
 */

// Configuration
const SELLER_POLL_INTERVAL = 3000; // Poll every 3 seconds
const SELLER_API_BASE = window.location.origin;

// State
let sellerCurrentConversationId = null;
let sellerMessagePollingInterval = null;
let sellerConversationPollingInterval = null;
let isSellerMessagingInitialized = false;

/**
 * Initialize seller messaging system
 */
function initializeSellerMessaging() {
    if (isSellerMessagingInitialized) {
        console.log('⚠️ Seller messaging already initialized, reloading conversations...');
        loadSellerConversations();
        return;
    }
    
    console.log('🔧 Initializing seller messaging system...');
    
    // Ensure container exists
    const container = document.getElementById('sellerConversationsList');
    if (!container) {
        console.error('❌ sellerConversationsList container not found!');
        return;
    }
    
    // Show loading state
    container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">Loading conversations...</p>';
    
    // Load conversations
    loadSellerConversations();
    
    // Set up auto-refresh
    startSellerConversationsPolling();
    
    // Update unread count badge
    updateSellerUnreadBadge();
    
    isSellerMessagingInitialized = true;
    console.log('✅ Seller messaging system initialized');
}

/**
 * Load all conversations for the seller
 */
async function loadSellerConversations() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.warn('No token found, cannot load seller conversations');
            const container = document.getElementById('sellerConversationsList');
            if (container) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Please log in to view conversations</p>
                    </div>
                `;
            }
            return;
        }
        
        console.log('📥 Loading seller conversations...');
        const response = await fetch(`${SELLER_API_BASE}/api/conversations/seller`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response from server:', text.substring(0, 200));
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📥 Seller conversations response:', data);
        
        if (!response.ok) {
            console.error('API error:', response.status, data);
            const container = document.getElementById('sellerConversationsList');
            if (container) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Error loading conversations: ${data.message || 'Unknown error'}</p>
                    </div>
                `;
            }
            return;
        }
        
        // Handle different response structures
        let conversations = null;
        if (data.success && data.data && data.data.conversations) {
            conversations = data.data.conversations;
        } else if (data.conversations) {
            conversations = data.conversations;
        } else if (Array.isArray(data)) {
            conversations = data;
        } else if (data.data && Array.isArray(data.data)) {
            conversations = data.data;
        }
        
        if (conversations !== null) {
            console.log(`✅ Loaded ${conversations.length} conversations`);
            displaySellerConversations(conversations);
        } else {
            console.error('Unexpected response structure:', data);
            const container = document.getElementById('sellerConversationsList');
            if (container) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Unexpected response format from server</p>
                    </div>
                `;
            }
        }
        
    } catch (error) {
        console.error('❌ Error loading seller conversations:', error);
        const container = document.getElementById('sellerConversationsList');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load conversations</p>
                    <p class="text-muted">${error.message || 'Network error'}</p>
                </div>
            `;
        }
    }
}

/**
 * Display seller conversations list
 */
function displaySellerConversations(conversations) {
    const container = document.getElementById('sellerConversationsList');
    if (!container) return;
    
    if (!conversations || conversations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comments"></i>
                <p>No customer messages yet</p>
                <p class="text-muted">Customers can message you about products</p>
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
            ? truncateSellerText(conv.last_message, 50)
            : 'No messages yet';
        
        const timeAgo = conv.last_message_at 
            ? formatSellerTimeAgo(new Date(conv.last_message_at))
            : '';
        
        html += `
            <div class="conversation-item ${sellerCurrentConversationId === conv.id ? 'active' : ''}" 
                 onclick="openSellerConversation(${conv.id}, '${escapeSellerHtml(conv.customer_name || 'Customer')}')">
                <div class="conversation-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="conversation-content">
                    <div class="conversation-header">
                        <span class="customer-name">${conv.customer_name}</span>
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
 * Open a conversation and load messages
 */
async function openSellerConversation(conversationId, customerName) {
    console.log(`💬 Opening conversation ${conversationId} with ${customerName}`);
    sellerCurrentConversationId = conversationId;
    
    // Update UI
    const chatContainer = document.getElementById('sellerChatContainer');
    if (chatContainer) {
        chatContainer.style.display = 'block';
        
        const customerNameEl = document.getElementById('chatCustomerName');
        if (customerNameEl) {
            customerNameEl.textContent = customerName;
        }
        
        // Show loading state
        const messagesContainer = document.getElementById('sellerMessagesContainer');
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="empty-messages">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading messages...</p>
                </div>
            `;
        }
    }
    
    // Highlight selected conversation
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
    const clickedItem = event?.target?.closest('.conversation-item');
    if (clickedItem) {
        clickedItem.classList.add('active');
    }
    
    // Load messages
    await loadSellerMessages(conversationId);
    
    // Mark as read
    await markSellerMessagesAsRead(conversationId);
    
    // Start polling
    startSellerMessagePolling(conversationId);
    
    // Refresh conversation list to update unread counts
    loadSellerConversations();
}

/**
 * Load messages for a conversation
 */
async function loadSellerMessages(conversationId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.warn('No token found, cannot load messages');
            return;
        }
        
        console.log(`📥 Loading messages for conversation ${conversationId}...`);
        const response = await fetch(`${SELLER_API_BASE}/api/messages/${conversationId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response from server:', text.substring(0, 200));
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📥 Seller messages response:', data);
        
        if (!response.ok) {
            console.error('API error:', response.status, data);
            const container = document.getElementById('sellerMessagesContainer');
            if (container) {
                container.innerHTML = `
                    <div class="empty-messages">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Error loading messages: ${data.message || 'Unknown error'}</p>
                    </div>
                `;
            }
            return;
        }
        
        // Handle different response structures
        let messages = null;
        if (data.success && data.data) {
            if (data.data.messages) {
                messages = data.data.messages;
            } else if (Array.isArray(data.data)) {
                messages = data.data;
            }
        } else if (Array.isArray(data)) {
            messages = data;
        } else if (data.messages) {
            messages = data.messages;
        }
        
        if (messages !== null) {
            console.log(`✅ Loaded ${messages.length} messages`);
            displaySellerMessages(messages);
        } else {
            console.error('Unexpected response structure:', data);
            const container = document.getElementById('sellerMessagesContainer');
            if (container) {
                container.innerHTML = `
                    <div class="empty-messages">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Unexpected response format from server</p>
                    </div>
                `;
            }
        }
        
    } catch (error) {
        console.error('❌ Error loading seller messages:', error);
        const container = document.getElementById('sellerMessagesContainer');
        if (container) {
            container.innerHTML = `
                <div class="empty-messages">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load messages</p>
                    <p class="text-muted">${error.message || 'Network error'}</p>
                </div>
            `;
        }
    }
}

/**
 * Display messages in seller chat window
 */
function displaySellerMessages(messages) {
    const container = document.getElementById('sellerMessagesContainer');
    if (!container) return;
    
    const token = localStorage.getItem('hub_access_token');
    const payload = parseSellerJwt(token);
    const currentUserId = payload?.id;
    const currentUserRole = payload?.role;
    
    if (!messages || messages.length === 0) {
        container.innerHTML = `
            <div class="empty-messages">
                <i class="fas fa-comment-dots"></i>
                <p>No messages yet</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    messages.forEach(msg => {
        // Fix: Use sender_type instead of sender_role, and message instead of message_text
        const senderType = msg.sender_type || msg.sender_role;
        const messageText = msg.message || msg.message_text || '';
        const senderId = msg.sender_id;
        
        // Determine if message is from current user (seller)
        // For seller: if sender_type is 'seller', check if sender_id matches seller's user_id
        // For customer: if sender_type is 'customer', it's not the seller's message
        const isOwnMessage = senderType === 'seller';
        const messageClass = isOwnMessage ? 'message-own' : 'message-other';
        const senderLabel = senderType === 'customer' ? 'Customer' : 'You';
        const time = formatSellerMessageTime(new Date(msg.created_at));
        
        // Handle attachments
        let attachmentHtml = '';
        if (msg.attachment_url) {
            const fileType = msg.attachment_type || 'image';
            if (fileType.startsWith('image/')) {
                attachmentHtml = `
                    <div style="margin-top: 8px; border-radius: 8px; overflow: hidden;">
                        <img src="${escapeSellerHtml(msg.attachment_url)}" 
                             alt="Attachment" 
                             style="max-width: 200px; max-height: 200px; border-radius: 8px; cursor: pointer;"
                             onclick="window.open('${escapeSellerHtml(msg.attachment_url)}', '_blank')">
                    </div>
                `;
            } else if (fileType.startsWith('video/')) {
                attachmentHtml = `
                    <div style="margin-top: 8px; border-radius: 8px; overflow: hidden;">
                        <video controls style="max-width: 200px; max-height: 200px; border-radius: 8px;">
                            <source src="${escapeSellerHtml(msg.attachment_url)}" type="${escapeSellerHtml(fileType)}">
                            Your browser does not support the video tag.
                        </video>
                    </div>
                `;
            } else {
                attachmentHtml = `
                    <div style="margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                        <a href="${escapeSellerHtml(msg.attachment_url)}" target="_blank" style="color: inherit; text-decoration: none;">
                            <i class="fa fa-paperclip"></i> Attachment
                        </a>
                    </div>
                `;
            }
        }
        
        // Fix alignment: seller messages on right, customer on left
        const alignment = isOwnMessage ? 'flex-end' : 'flex-start';
        const bgColor = isOwnMessage ? '#3498db' : '#ecf0f1';
        const textColor = isOwnMessage ? 'white' : '#2c3e50';
        
        html += `
            <div style="display: flex; justify-content: ${alignment}; margin-bottom: 12px;">
                <div style="max-width: 70%; padding: 10px 14px; border-radius: 18px; background: ${bgColor}; color: ${textColor};">
                    <div style="font-size: 0.75rem; opacity: 0.8; margin-bottom: 4px;">${senderLabel}</div>
                    ${messageText ? `<div style="word-wrap: break-word; white-space: pre-wrap; margin-bottom: 4px;">${escapeSellerHtml(messageText)}</div>` : ''}
                    ${attachmentHtml}
                    <div style="font-size: 0.7rem; margin-top: 4px; opacity: 0.7;">${time}</div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    scrollSellerToBottom();
}

/**
 * Send a message from seller
 */
async function sendSellerMessage() {
    const input = document.getElementById('sellerMessageInput');
    if (!input) return;
    
    const messageText = input.value.trim();
    if (!messageText || !sellerCurrentConversationId) return;
    
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        input.disabled = true;
        
        const response = await fetch(`${SELLER_API_BASE}/api/messages/send`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: sellerCurrentConversationId,
                message_text: messageText
            })
        });
        
        const data = await response.json();
        
        if (data.success || data.status === 'success') {
            input.value = '';
            await loadSellerMessages(sellerCurrentConversationId);
            await loadSellerConversations();
        } else {
            alert('Failed to send message: ' + data.message);
        }
        
    } catch (error) {
        console.error('Error sending seller message:', error);
        alert('Failed to send message');
    } finally {
        input.disabled = false;
        input.focus();
    }
}

/**
 * Mark messages as read
 */
async function markSellerMessagesAsRead(conversationId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        console.log(`📖 Marking messages as read for conversation ${conversationId}`);
        const response = await fetch(`${SELLER_API_BASE}/api/messages/read/${conversationId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            console.log('✅ Messages marked as read');
            // Update badge and refresh conversation list
            await updateSellerUnreadBadge();
            await loadSellerConversations(); // Refresh to update unread counts in list
        } else {
            console.error('Failed to mark messages as read:', response.status);
        }
        
    } catch (error) {
        console.error('Error marking seller messages as read:', error);
    }
}

/**
 * Update unread messages badge for seller
 */
async function updateSellerUnreadBadge() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;
        
        const response = await fetch(`${SELLER_API_BASE}/api/messages/unread-count`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success || data.status === 'success') {
            const count = data.data.unread_count;
            
            const badge = document.getElementById('sellerMessagesBadge');
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
        console.error('Error updating seller unread badge:', error);
    }
}

/**
 * Start polling for new messages
 */
function startSellerMessagePolling(conversationId) {
    if (sellerMessagePollingInterval) {
        clearInterval(sellerMessagePollingInterval);
    }
    
    sellerMessagePollingInterval = setInterval(() => {
        if (sellerCurrentConversationId === conversationId) {
            loadSellerMessages(conversationId);
        }
    }, SELLER_POLL_INTERVAL);
}

/**
 * Start polling for conversations updates
 */
function startSellerConversationsPolling() {
    if (sellerConversationPollingInterval) {
        clearInterval(sellerConversationPollingInterval);
    }
    
    sellerConversationPollingInterval = setInterval(() => {
        loadSellerConversations();
        updateSellerUnreadBadge();
    }, SELLER_POLL_INTERVAL * 2);
}

/**
 * Stop all polling
 */
function stopSellerMessagingPolling() {
    if (sellerMessagePollingInterval) {
        clearInterval(sellerMessagePollingInterval);
        sellerMessagePollingInterval = null;
    }
    
    if (sellerConversationPollingInterval) {
        clearInterval(sellerConversationPollingInterval);
        sellerConversationPollingInterval = null;
    }
}

/**
 * Handle Enter key
 */
function handleSellerMessageKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendSellerMessage();
    }
}

/**
 * Scroll to bottom
 */
function scrollSellerToBottom() {
    const container = document.getElementById('sellerMessagesContainer');
    if (container) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
}

// Utility functions
function parseSellerJwt(token) {
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

function formatSellerTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
}

function formatSellerMessageTime(date) {
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

function truncateSellerText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function escapeSellerHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export for global access
window.initializeSellerMessaging = initializeSellerMessaging;
window.openSellerConversation = openSellerConversation;
window.sendSellerMessage = sendSellerMessage;
window.handleSellerMessageKeyPress = handleSellerMessageKeyPress;
window.stopSellerMessagingPolling = stopSellerMessagingPolling;
