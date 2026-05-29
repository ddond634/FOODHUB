/**
 * Global Messenger Icon Injector
 * Automatically adds the blue messenger icon to all pages if it doesn't exist
 * This ensures consistent messaging functionality across the entire site
 */

(function() {
    'use strict';
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMessenger);
    } else {
        initMessenger();
    }
    
    function initMessenger() {
        // Check if messenger icon already exists
        if (document.getElementById('messagesPanel') && document.querySelector('.messages-btn')) {
            // Messenger already exists, just ensure scripts are loaded
            ensureMessengerScripts();
            return;
        }
        
        // Inject messenger HTML before closing body tag or before footer
        injectMessengerHTML();
        
        // Ensure necessary scripts are loaded
        ensureMessengerScripts();
    }
    
    function injectMessengerHTML() {
        // Find insertion point (before footer or before closing body tag)
        const footer = document.querySelector('footer');
        const insertionPoint = footer || document.body;
        
        // Create messenger button
        const messengerBtn = document.createElement('button');
        messengerBtn.className = 'messages-btn';
        messengerBtn.setAttribute('aria-haspopup', 'true');
        messengerBtn.setAttribute('aria-expanded', 'false');
        messengerBtn.setAttribute('aria-controls', 'messagesPanel');
        messengerBtn.setAttribute('onclick', 'toggleMessagesPanel()');
        messengerBtn.innerHTML = `
            <i class="fa fa-message"></i>
            <span class="messages-badge" id="messagesBadge" style="display:none;">0</span>
        `;
        
        // Create messenger panel
        const messengerPanel = document.createElement('div');
        messengerPanel.id = 'messagesPanel';
        messengerPanel.className = 'messages-panel';
        messengerPanel.setAttribute('hidden', '');
        messengerPanel.innerHTML = `
            <div class="messages-header">
                <button class="back-to-list" onclick="backToConversationsList()" style="display:none;">
                    <i class="fa fa-arrow-left"></i>
                </button>
                <h3 id="messagesPanelTitle">Messages</h3>
                <button class="close-messages" aria-label="Close messages panel" onclick="closeMessagesPanel()">
                    <i class="fa fa-times"></i>
                </button>
            </div>
            
            <div class="messages-search" id="messagesSearchBar">
                <input type="text" id="messagesSearch" placeholder="Search name" onkeyup="filterMessageConversations()">
            </div>
            
            <div class="messages-list" id="messagesList">
                <!-- Messages will be dynamically loaded here -->
                <div class="no-messages">
                    <i class="fa fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 12px;"></i>
                    <p style="color: #999; font-size: 14px;">No messages yet</p>
                    <p style="color: #bbb; font-size: 12px;">Start chatting with sellers!</p>
                </div>
            </div>

            <!-- Chat View (hidden by default) -->
            <div id="chatView" style="display:none; flex-direction: column; height: 100%;">
                <div id="chatMessages" style="flex: 1; overflow-y: auto; padding: 16px;"></div>
                <div style="padding: 12px; border-top: 1px solid #ecf0f1; background: white;">
                    <div id="filePreview" style="display: none; margin-bottom: 8px;"></div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <label for="chatFileInput" style="cursor: pointer; width: 40px; height: 40px; border-radius: 50%; background: #95a5a6; color: white; border: none; display: flex; align-items: center; justify-content: center; flex-shrink: 0;" title="Attach file">
                            <i class="fa fa-paperclip"></i>
                            <input type="file" id="chatFileInput" accept="image/*,video/*" style="display: none;" onchange="if(typeof handleFileInput === 'function') handleFileInput(event)">
                        </label>
                        <input type="text" id="chatInput" placeholder="Type a message..." 
                               style="flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 20px; outline: none;"
                               onkeypress="if(event.key==='Enter' && !event.shiftKey) { event.preventDefault(); if(typeof sendMessageInPanel === 'function') sendMessageInPanel(); }">
                        <button onclick="if(typeof sendMessageInPanel === 'function') sendMessageInPanel()" 
                                style="width: 40px; height: 40px; border-radius: 50%; background: #3498db; color: white; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            <i class="fa fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Insert before footer or at end of body
        insertionPoint.parentNode.insertBefore(messengerBtn, insertionPoint);
        insertionPoint.parentNode.insertBefore(messengerPanel, insertionPoint);
    }
    
    function ensureMessengerScripts() {
        // List of required scripts for messenger functionality
        const requiredScripts = [
            'js/customer-messaging.js',
            'js/messaging-panel.js'
        ];
        
        const scriptsToLoad = [];
        
        requiredScripts.forEach(scriptPath => {
            // Check if script is already loaded
            const scriptExists = Array.from(document.querySelectorAll('script[src]'))
                .some(script => {
                    const src = script.src || script.getAttribute('src') || '';
                    return src.includes(scriptPath) || src.endsWith(scriptPath);
                });
            
            if (!scriptExists) {
                scriptsToLoad.push(scriptPath);
            }
        });
        
        // Load scripts and wait for them to be ready
        if (scriptsToLoad.length > 0) {
            loadScriptsSequentially(scriptsToLoad, () => {
                initializeMessengerAfterLoad();
            });
        } else {
            // Scripts already loaded, initialize immediately
            initializeMessengerAfterLoad();
        }
    }
    
    function loadScriptsSequentially(scripts, callback) {
        let index = 0;
        
        function loadNext() {
            if (index >= scripts.length) {
                // All scripts loaded, wait a bit for them to execute
                setTimeout(callback, 500);
                return;
            }
            
            const scriptPath = scripts[index];
            const script = document.createElement('script');
            script.src = scriptPath;
            script.async = false; // Load sequentially, not in parallel
            script.onload = () => {
                index++;
                loadNext();
            };
            script.onerror = () => {
                console.error(`Failed to load script: ${scriptPath}`);
                index++;
                loadNext(); // Continue loading other scripts even if one fails
            };
            document.body.appendChild(script);
        }
        
        loadNext();
    }
    
    function initializeMessengerAfterLoad() {
        // Wait for functions to be available
        const maxAttempts = 10;
        let attempts = 0;
        
        function tryInitialize() {
            attempts++;
            
            // Check if required functions are available
            const functionsReady = 
                typeof loadPanelConversations === 'function' &&
                typeof updatePanelUnreadBadge === 'function' &&
                typeof toggleMessagesPanel === 'function';
            
            if (functionsReady || attempts >= maxAttempts) {
                if (functionsReady) {
                    console.log('✅ Messenger scripts loaded and ready');
                    
                    // Load conversations and update badge if user is logged in
                    const token = localStorage.getItem('hub_access_token');
                    if (token) {
                        // Update badge immediately
                        if (typeof updatePanelUnreadBadge === 'function') {
                            updatePanelUnreadBadge();
                            
                            // Set up periodic badge updates
                            setInterval(() => {
                                if (typeof updatePanelUnreadBadge === 'function') {
                                    updatePanelUnreadBadge();
                                }
                            }, 10000); // Update every 10 seconds
                        }
                    }
                    
                    // Override toggleMessagesPanel to ensure conversations load when panel opens
                    const originalToggle = window.toggleMessagesPanel;
                    if (originalToggle) {
                        window.toggleMessagesPanel = function() {
                            const panel = document.getElementById('messagesPanel');
                            const btn = document.querySelector('.messages-btn');
                            
                            if (!panel) {
                                console.error('Messages panel not found');
                                return;
                            }
                            
                            if (panel.hidden) {
                                panel.hidden = false;
                                if (btn) btn.setAttribute('aria-expanded', 'true');
                                
                                // Always load conversations when panel opens
                                const chatView = document.getElementById('chatView');
                                const isInChatView = chatView && chatView.style.display !== 'none';
                                
                                if (!isInChatView) {
                                    // Load conversations list
                                    if (typeof loadPanelConversations === 'function') {
                                        console.log('📥 Loading conversations when panel opens...');
                                        loadPanelConversations();
                                    }
                                    
                                    // Start conversations polling
                                    if (typeof startPanelConversationsPolling === 'function') {
                                        startPanelConversationsPolling();
                                    }
                                }
                            } else {
                                panel.hidden = true;
                                if (btn) btn.setAttribute('aria-expanded', 'false');
                                
                                // Stop polling when panel is closed
                                if (typeof messagePollingInterval !== 'undefined' && messagePollingInterval) {
                                    clearInterval(messagePollingInterval);
                                    messagePollingInterval = null;
                                }
                            }
                        };
                    }
                } else {
                    console.warn('⚠️ Messenger functions not available after loading scripts');
                }
            } else {
                // Try again after a short delay
                setTimeout(tryInitialize, 200);
            }
        }
        
        tryInitialize();
    }
})();

