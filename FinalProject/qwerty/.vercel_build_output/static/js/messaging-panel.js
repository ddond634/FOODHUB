/**
 * Enhanced Messaging Panel Handler
 * Handles the blue messenger icon chat window with API integration
 */

// Use existing global API_BASE if already defined by another script to avoid redeclaration SyntaxError
// Fallback to origin-based default
if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = window.location.origin;
}
// Use window.API_BASE directly to avoid redeclaration issues
// Create a local reference only if needed, but prefer using window.API_BASE directly

// State variables - check if already declared to avoid redeclaration errors
// These may be declared in customer-messaging.js or other scripts
if (typeof currentConversationId === 'undefined') {
    var currentConversationId = null;
}
if (typeof currentSellerId === 'undefined') {
    var currentSellerId = null;
}
if (typeof currentSellerName === 'undefined') {
    var currentSellerName = null;
}
if (typeof messagePollingInterval === 'undefined') {
    var messagePollingInterval = null;
}
if (typeof conversationPollingInterval === 'undefined') {
    var conversationPollingInterval = null;
}

/**
 * Open messaging panel and start conversation with a seller
 * Called when customer clicks "Message Seller" on seller.html
 */
async function openMessengerPanelWithSeller(sellerId, sellerName) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            if (window.notify) {
                window.notify.warning('Please sign in to message sellers');
            } else {
                alert('Please sign in to message sellers');
            }
            localStorage.setItem('returnUrl', window.location.href);
            setTimeout(() => {
                window.location.href = 'loginregister.html';
            }, 1500);
            return;
        }

        // Store seller info
        currentSellerId = sellerId;
        currentSellerName = sellerName;

        // Open the messaging panel
        const panel = document.getElementById('messagesPanel');
        const btn = document.querySelector('.messages-btn');
        
        if (panel) {
            panel.hidden = false;
            if (btn) btn.setAttribute('aria-expanded', 'true');
        }

        // Create or get conversation
        const response = await fetch(`${window.API_BASE}/api/conversations/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ seller_id: sellerId })
        });

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response:', text.substring(0, 200));
            throw new Error(`Server returned ${response.status}: ${response.statusText}. Response: ${text.substring(0, 100)}`);
        }

        const data = await response.json();

        if (data.success && data.data) {
            currentConversationId = data.data.conversation_id;
            
            // Switch to chat view
            showChatView(sellerName);
            
            // Load messages
            await loadPanelMessages(currentConversationId);
            
            // Send greeting message if this is a new conversation
            if (data.data.created) {
                await sendGreetingMessage(currentConversationId, sellerId);
            }
            
            // Mark messages as read
            await markPanelMessagesAsRead(currentConversationId);
            
            // Reload conversation list to update unread badges
            loadPanelConversations();
            
            // Start polling for new messages
            startPanelMessagePolling();
        } else {
            console.error('Failed to create conversation:', data.message);
            if (window.notify) {
                window.notify.error('Failed to start conversation: ' + (data.message || 'Unknown error'));
            }
        }

    } catch (error) {
        console.error('Error opening messenger panel:', error);
        if (window.notify) {
            window.notify.error('Failed to open chat. Please try again.');
        }
    }
}

/**
 * Show chat view in the panel
 */
function showChatView(sellerName) {
    const list = document.getElementById('messagesList');
    const searchBar = document.getElementById('messagesSearchBar');
    const chatView = document.getElementById('chatView');
    const title = document.getElementById('messagesPanelTitle');
    const backBtn = document.querySelector('.back-to-list');

    if (list) list.style.display = 'none';
    if (searchBar) searchBar.style.display = 'none';
    if (chatView) chatView.style.display = 'flex';
    if (backBtn) backBtn.style.display = 'block';
    if (title) title.textContent = sellerName || 'Chat';
}

/**
 * Load messages for a conversation in the panel
 */
async function loadPanelMessages(conversationId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.warn('No token found, cannot load messages');
            return;
        }

        console.log(`📥 Loading messages for conversation ${conversationId}...`);
        const apiBase = window.API_BASE || window.location.origin;
        const response = await fetch(`${apiBase}/api/messages/${conversationId}`, {
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
        console.log('📥 Messages response:', data);
        
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            console.error('chatMessages container not found');
            return;
        }

        if (!response.ok) {
            console.error('API error:', response.status, data);
            chatMessages.innerHTML = `
                <div style="text-align: center; padding: 40px 20px; color: #999;">
                    <i class="fa fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 12px; color: #e74c3c;"></i>
                    <p>Error loading messages: ${data.message || 'Unknown error'}</p>
                </div>
            `;
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
            displayPanelMessages(messages);
        } else {
            console.log('No messages found');
            chatMessages.innerHTML = `
                <div style="text-align: center; padding: 40px 20px; color: #999;">
                    <i class="fa fa-comment-dots" style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;"></i>
                    <p>No messages yet. Start the conversation!</p>
                </div>
            `;
        }

    } catch (error) {
        console.error('❌ Error loading panel messages:', error);
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = `
                <div style="text-align: center; padding: 40px 20px; color: #999;">
                    <i class="fa fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 12px; color: #e74c3c;"></i>
                    <p>Failed to load messages</p>
                    <p style="font-size: 0.9em; color: #bbb;">${error.message || 'Network error'}</p>
                </div>
            `;
        }
    }
}

/**
 * Display messages in the panel
 */
function displayPanelMessages(messages) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const token = localStorage.getItem('hub_access_token');
    let currentUserId = null;
    let currentUserRole = null;

    try {
        const payload = parseJwt(token);
        currentUserId = payload?.user_id || payload?.id;
        currentUserRole = payload?.role;
    } catch (e) {
        console.error('Error parsing token:', e);
    }

    if (!messages || messages.length === 0) {
        chatMessages.innerHTML = `
            <div style="text-align: center; padding: 40px 20px; color: #999;">
                <i class="fa fa-comment-dots" style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;"></i>
                <p>No messages yet. Start the conversation!</p>
            </div>
        `;
        return;
    }

    let html = '';
    messages.forEach(msg => {
        // Determine if message is from current user
        const isOwnMessage = (msg.sender_type === 'customer' && currentUserRole === 'customer') ||
                            (msg.sender_type === 'seller' && currentUserRole === 'seller');
        
        const alignment = isOwnMessage ? 'flex-end' : 'flex-start';
        const bgColor = isOwnMessage ? '#3498db' : '#ecf0f1';
        const textColor = isOwnMessage ? 'white' : '#2c3e50';
        
        // Format time
        const time = formatMessageTime(new Date(msg.created_at));
        
        // Handle attachments
        let attachmentHtml = '';
        if (msg.attachment_url) {
            const fileType = msg.attachment_type || 'image';
            if (fileType.startsWith('image/')) {
                attachmentHtml = `
                    <div style="margin-top: 8px; border-radius: 8px; overflow: hidden;">
                        <img src="${escapeHtml(msg.attachment_url)}" 
                             alt="Attachment" 
                             style="max-width: 200px; max-height: 200px; border-radius: 8px; cursor: pointer;"
                             onclick="window.open('${escapeHtml(msg.attachment_url)}', '_blank')">
                    </div>
                `;
            } else if (fileType.startsWith('video/')) {
                attachmentHtml = `
                    <div style="margin-top: 8px; border-radius: 8px; overflow: hidden;">
                        <video controls style="max-width: 200px; max-height: 200px; border-radius: 8px;">
                            <source src="${escapeHtml(msg.attachment_url)}" type="${escapeHtml(fileType)}">
                            Your browser does not support the video tag.
                        </video>
                    </div>
                `;
            } else {
                attachmentHtml = `
                    <div style="margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                        <a href="${escapeHtml(msg.attachment_url)}" target="_blank" style="color: inherit; text-decoration: none;">
                            <i class="fa fa-paperclip"></i> Attachment
                        </a>
                    </div>
                `;
            }
        }
        
        html += `
            <div style="display: flex; justify-content: ${alignment}; margin-bottom: 12px;">
                <div style="max-width: 70%; padding: 10px 14px; border-radius: 18px; background: ${bgColor}; color: ${textColor};">
                    ${msg.message ? `<div style="word-wrap: break-word; white-space: pre-wrap;">${escapeHtml(msg.message)}</div>` : ''}
                    ${attachmentHtml}
                    <div style="font-size: 0.7rem; margin-top: 4px; opacity: 0.7;">${time}</div>
                </div>
            </div>
        `;
    });

    chatMessages.innerHTML = html;
    
    // Scroll to bottom
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

/**
 * Send greeting message when conversation is first created
 */
async function sendGreetingMessage(conversationId, sellerId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;

        // Fetch seller greeting message
        const greetingResponse = await fetch(`${window.API_BASE}/api/sellers/${sellerId}/greeting`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        let greetingText = 'Hello! Thank you for your interest. How can I help you today?';
        
        if (greetingResponse.ok) {
            const greetingData = await greetingResponse.json();
            if (greetingData.success && greetingData.data && greetingData.data.greeting_message) {
                greetingText = greetingData.data.greeting_message;
            }
        }

        // Send greeting as seller message
        // Note: This would typically be sent by the seller's system, but for now we'll send it automatically
        // In production, you might want to trigger this on the seller's side
        
    } catch (error) {
        console.error('Error sending greeting message:', error);
        // Don't show error to user - greeting is optional
    }
}

/**
 * Send message from panel
 */
async function sendMessageInPanel() {
    const input = document.getElementById('chatInput');
    const fileInput = document.getElementById('chatFileInput');
    
    if (!input || !currentConversationId) return;

    const messageText = input.value.trim();
    const file = fileInput?.files?.[0];

    if (!messageText && !file) return;

    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;

        input.disabled = true;
        if (fileInput) fileInput.disabled = true;

        let response;
        
        if (file) {
            // Send message with attachment
            const formData = new FormData();
            formData.append('message', messageText || '');
            formData.append('attachment', file);
            
            response = await fetch(`${window.API_BASE}/api/messages/${currentConversationId}/send`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
        } else {
            // Send text-only message
            response = await fetch(`${window.API_BASE}/api/messages/${currentConversationId}/send`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: messageText
                })
            });
        }

        const data = await response.json();

        if (data.success) {
            input.value = '';
            if (fileInput) {
                fileInput.value = '';
                // Hide file preview if exists
                const filePreview = document.getElementById('filePreview');
                if (filePreview) filePreview.style.display = 'none';
            }
            
            // Reload messages
            await loadPanelMessages(currentConversationId);
            
            // Reload conversations list
            await loadPanelConversations();
        } else {
            if (window.notify) {
                window.notify.error(data.message || 'Failed to send message');
            } else {
                alert(data.message || 'Failed to send message');
            }
        }

    } catch (error) {
        console.error('Error sending message:', error);
        if (window.notify) {
            window.notify.error('Failed to send message. Please try again.');
        }
    } finally {
        input.disabled = false;
        if (fileInput) fileInput.disabled = false;
        input.focus();
    }
}

/**
 * Load conversations list for the panel
 */
async function loadPanelConversations() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.warn('No token found, cannot load conversations');
            const messagesList = document.getElementById('messagesList');
            if (messagesList) {
                messagesList.innerHTML = `
                    <div class="no-messages">
                        <i class="fa fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 12px;"></i>
                        <p style="color: #999; font-size: 14px;">Please log in to view messages</p>
                    </div>
                `;
            }
            return;
        }

        console.log('📥 Loading panel conversations...');
        const apiBase = window.API_BASE || window.location.origin;
        const response = await fetch(`${apiBase}/api/conversations`, {
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
        console.log('📥 Conversations response:', data);
        
        const messagesList = document.getElementById('messagesList');
        if (!messagesList) {
            console.error('messagesList container not found');
            return;
        }

        if (!response.ok) {
            console.error('API error:', response.status, data);
            messagesList.innerHTML = `
                <div class="no-messages">
                    <i class="fa fa-exclamation-triangle" style="font-size: 48px; color: #e74c3c; margin-bottom: 12px;"></i>
                    <p style="color: #999; font-size: 14px;">Error loading conversations</p>
                    <p style="color: #bbb; font-size: 12px;">${data.message || 'Please try again later'}</p>
                </div>
            `;
            return;
        }

        // Handle different response structures
        let conversations = null;
        if (data.success && data.data) {
            if (data.data.conversations) {
                conversations = data.data.conversations;
            } else if (Array.isArray(data.data)) {
                conversations = data.data;
            }
        } else if (Array.isArray(data)) {
            conversations = data;
        } else if (data.conversations) {
            conversations = data.conversations;
        } else if (data.data && Array.isArray(data.data)) {
            conversations = data.data;
        }

        if (conversations !== null && Array.isArray(conversations)) {
            console.log(`✅ Loaded ${conversations.length} conversations:`, conversations);
            if (conversations.length > 0) {
                // Log each conversation to see if last_message is null
                conversations.forEach((conv, idx) => {
                    console.log(`Conversation ${idx + 1}:`, {
                        id: conv.id,
                        seller_name: conv.seller_name,
                        last_message: conv.last_message,
                        last_message_at: conv.last_message_at,
                        unread_count: conv.unread_count
                    });
                });
                displayPanelConversations(conversations);
            } else {
                console.log('Conversations array is empty');
                messagesList.innerHTML = `
                    <div class="no-messages">
                        <i class="fa fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 12px;"></i>
                        <p style="color: #999; font-size: 14px;">No messages yet</p>
                        <p style="color: #bbb; font-size: 12px;">Start chatting with sellers!</p>
                    </div>
                `;
            }
        } else {
            console.warn('Unexpected response structure or conversations is not an array:', data);
            console.log('Full response data:', JSON.stringify(data, null, 2));
            messagesList.innerHTML = `
                <div class="no-messages">
                    <i class="fa fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 12px;"></i>
                    <p style="color: #999; font-size: 14px;">No messages yet</p>
                    <p style="color: #bbb; font-size: 12px;">Start chatting with sellers!</p>
                </div>
            `;
        }

        // Update unread badge
        if (typeof updatePanelUnreadBadge === 'function') {
            updatePanelUnreadBadge();
        }

    } catch (error) {
        console.error('❌ Error loading panel conversations:', error);
        const messagesList = document.getElementById('messagesList');
        if (messagesList) {
            messagesList.innerHTML = `
                <div class="no-messages">
                    <i class="fa fa-exclamation-triangle" style="font-size: 48px; color: #e74c3c; margin-bottom: 12px;"></i>
                    <p style="color: #999; font-size: 14px;">Failed to load conversations</p>
                    <p style="color: #bbb; font-size: 12px;">${error.message || 'Network error'}</p>
                </div>
            `;
        }
    }
}

/**
 * Display conversations in the panel
 */
function displayPanelConversations(conversations) {
    const messagesList = document.getElementById('messagesList');
    if (!messagesList) return;

    if (!conversations || conversations.length === 0) {
        messagesList.innerHTML = `
            <div class="no-messages">
                <i class="fa fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 12px;"></i>
                <p style="color: #999; font-size: 14px;">No messages yet</p>
                <p style="color: #bbb; font-size: 12px;">Start chatting with sellers!</p>
            </div>
        `;
        return;
    }

    let html = '';
    conversations.forEach(conv => {
        const unreadBadge = conv.unread_count > 0 
            ? `<span class="messages-badge" style="position: absolute; top: 8px; right: 8px; background: #e74c3c; color: white; border-radius: 12px; padding: 2px 6px; font-size: 0.7rem; min-width: 18px; text-align: center;">${conv.unread_count > 99 ? '99+' : conv.unread_count}</span>` 
            : '';
        
        // Show last message or indicate if conversation exists but has no messages
        const lastMessage = conv.last_message 
            ? truncateText(conv.last_message, 40)
            : 'Click to start conversation';
        
        const timeAgo = conv.last_message_at 
            ? formatTimeAgo(new Date(conv.last_message_at))
            : '';

        html += `
            <div class="message-item" 
                 style="display: flex; align-items: center; padding: 12px; border-bottom: 1px solid #ecf0f1; cursor: pointer; position: relative;"
                 onclick="openPanelConversation(${conv.id}, '${escapeHtml(conv.seller_name)}')"
                 onmouseover="this.style.background='#f8f9fa'"
                 onmouseout="this.style.background='white'">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #3498db, #2980b9); display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; margin-right: 12px; flex-shrink: 0;">
                    <i class="fa fa-store"></i>
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-weight: 600; color: #2c3e50; font-size: 14px;">${escapeHtml(conv.seller_name)}</span>
                        ${timeAgo ? `<span style="font-size: 0.75rem; color: #999;">${timeAgo}</span>` : ''}
                    </div>
                    <div style="font-size: 0.85rem; color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${escapeHtml(lastMessage)}
                    </div>
                </div>
                ${unreadBadge}
            </div>
        `;
    });

    messagesList.innerHTML = html;
}

/**
 * Open a conversation in the panel
 */
async function openPanelConversation(conversationId, sellerName) {
    currentConversationId = conversationId;
    currentSellerName = sellerName;
    
    showChatView(sellerName);
    await loadPanelMessages(conversationId);
    await markPanelMessagesAsRead(conversationId);
    startPanelMessagePolling();
}

/**
 * Mark messages as read
 */
async function markPanelMessagesAsRead(conversationId) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;

        await fetch(`${window.API_BASE}/api/messages/read/${conversationId}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        // Update unread badge and reload conversation list to update unread counts
        updatePanelUnreadBadge();
        loadPanelConversations();  // Reload to update unread badges in the list

    } catch (error) {
        console.error('Error marking messages as read:', error);
    }
}

/**
 * Update unread badge
 */
async function updatePanelUnreadBadge() {
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
        const badge = document.getElementById('messagesBadge');
        
        if (badge && data.success) {
            const count = data.data?.unread_count || 0;
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }

    } catch (error) {
        console.error('Error updating unread badge:', error);
    }
}

/**
 * Start polling for new messages
 */
function startPanelMessagePolling() {
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
    }

    messagePollingInterval = setInterval(() => {
        if (currentConversationId) {
            loadPanelMessages(currentConversationId);
        }
    }, 3000); // Poll every 3 seconds
}

/**
 * Start polling for conversations updates
 */
function startPanelConversationsPolling() {
    if (conversationPollingInterval) {
        clearInterval(conversationPollingInterval);
    }

    conversationPollingInterval = setInterval(() => {
        loadPanelConversations();
        updatePanelUnreadBadge();
    }, 6000); // Poll every 6 seconds
}

/**
 * Filter conversations by search term
 */
function filterMessageConversations() {
    const searchTerm = document.getElementById('messagesSearch')?.value.toLowerCase() || '';
    const items = document.querySelectorAll('.message-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(searchTerm) ? 'flex' : 'none';
    });
}

/**
 * Toggle messages panel
 */
function toggleMessagesPanel() {
    const panel = document.getElementById('messagesPanel');
    const btn = document.querySelector('.messages-btn');
    
    if (!panel) return;
    
    if (panel.hidden) {
        panel.hidden = false;
        if (btn) btn.setAttribute('aria-expanded', 'true');
        
        // Load conversations if not in chat view
        const chatView = document.getElementById('chatView');
        if (chatView && chatView.style.display === 'none') {
            loadPanelConversations();
            startPanelConversationsPolling();
        }
    } else {
        panel.hidden = true;
        if (btn) btn.setAttribute('aria-expanded', 'false');
        
        // Stop polling when panel is closed
        if (messagePollingInterval) {
            clearInterval(messagePollingInterval);
            messagePollingInterval = null;
        }
    }
}

/**
 * Close messages panel
 */
function closeMessagesPanel() {
    const panel = document.getElementById('messagesPanel');
    const btn = document.querySelector('.messages-btn');
    
    if (panel) panel.hidden = true;
    if (btn) btn.setAttribute('aria-expanded', 'false');
    
    // Stop polling
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
        messagePollingInterval = null;
    }
}

/**
 * Go back to conversations list
 */
function backToConversationsList() {
    const list = document.getElementById('messagesList');
    const searchBar = document.getElementById('messagesSearchBar');
    const chatView = document.getElementById('chatView');
    const title = document.getElementById('messagesPanelTitle');
    const backBtn = document.querySelector('.back-to-list');

    if (list) list.style.display = 'block';
    if (searchBar) searchBar.style.display = 'block';
    if (chatView) chatView.style.display = 'none';
    if (backBtn) backBtn.style.display = 'none';
    if (title) title.textContent = 'Messages';
    
    currentConversationId = null;
    
    // Stop message polling, start conversations polling
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
        messagePollingInterval = null;
    }
    startPanelConversationsPolling();
}

/**
 * Handle file input for attachments
 */
function handleFileInput(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    const filePreview = document.getElementById('filePreview');
    if (!filePreview) return;

    // Validate file type
    const validImageTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    const validVideoTypes = ['video/mp4', 'video/webm', 'video/ogg'];
    
    if (!validImageTypes.includes(file.type) && !validVideoTypes.includes(file.type)) {
        if (window.notify) {
            window.notify.warning('Please select an image or video file');
        }
        event.target.value = '';
        return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        if (window.notify) {
            window.notify.warning('File size must be less than 10MB');
        }
        event.target.value = '';
        return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        if (validImageTypes.includes(file.type)) {
            filePreview.innerHTML = `
                <div style="position: relative; display: inline-block; margin-top: 8px;">
                    <img src="${e.target.result}" alt="Preview" style="max-width: 150px; max-height: 150px; border-radius: 8px;">
                    <button onclick="clearFilePreview()" style="position: absolute; top: -8px; right: -8px; background: #e74c3c; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 12px;">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
            `;
        } else {
            filePreview.innerHTML = `
                <div style="position: relative; display: inline-block; margin-top: 8px;">
                    <div style="padding: 12px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; gap: 8px;">
                        <i class="fa fa-video" style="font-size: 24px; color: #3498db;"></i>
                        <div>
                            <div style="font-weight: 600; font-size: 14px;">${escapeHtml(file.name)}</div>
                            <div style="font-size: 12px; color: #666;">${(file.size / 1024 / 1024).toFixed(2)} MB</div>
                        </div>
                        <button onclick="clearFilePreview()" style="background: #e74c3c; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 12px; margin-left: 8px;">
                            <i class="fa fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        }
        filePreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

/**
 * Clear file preview
 */
function clearFilePreview() {
    const filePreview = document.getElementById('filePreview');
    const fileInput = document.getElementById('chatFileInput');
    
    if (filePreview) filePreview.style.display = 'none';
    if (fileInput) fileInput.value = '';
}

// Utility functions
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

function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
}

function formatMessageTime(date) {
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// Export functions globally
window.openMessengerPanelWithSeller = openMessengerPanelWithSeller;
window.sendMessageInPanel = sendMessageInPanel;
window.toggleMessagesPanel = toggleMessagesPanel;
window.closeMessagesPanel = closeMessagesPanel;
window.backToConversationsList = backToConversationsList;
window.filterMessageConversations = filterMessageConversations;
window.openPanelConversation = openPanelConversation;
window.handleFileInput = handleFileInput;
window.clearFilePreview = clearFilePreview;

