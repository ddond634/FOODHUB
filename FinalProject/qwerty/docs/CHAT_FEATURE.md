# 💬 Customer-to-Seller Chat Feature Documentation

## Overview
Real-time customer-to-seller messaging system with MySQL database support, automatic conversation creation, read status tracking, and chronological message ordering.

---

## 🗄️ Database Schema

### Conversations Table
Stores unique chat sessions between customers and sellers.

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    seller_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_conversation (customer_id, seller_id),
    INDEX idx_customer (customer_id),
    INDEX idx_seller (seller_id)
) ENGINE=InnoDB;
```

**Key Features:**
- **Unique constraint:** One conversation per customer-seller pair
- **Auto-update:** `updated_at` refreshes on any change
- **Cascading delete:** Conversation deleted if either user is deleted
- **Indexed:** Fast lookups by customer or seller

---

### Messages Table
Stores individual chat messages within conversations.

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_id INT NOT NULL,
    sender_type ENUM('customer','seller') NOT NULL,
    message TEXT NOT NULL,
    is_read TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_conversation (conversation_id),
    INDEX idx_sender (sender_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;
```

**Key Features:**
- **sender_type:** Explicitly identifies if sender is customer or seller
- **is_read:** Tracks read status (0 = unread, 1 = read)
- **Cascading delete:** Messages deleted if conversation is deleted
- **Indexed:** Fast queries by conversation, sender, and time

---

## 🛠️ API Endpoints

### 1. Get All Conversations
**Endpoint:** `GET /api/chat/conversations`  
**Auth:** Customer or Seller authentication required  
**Description:** Lists all conversations for the current user with unread counts

**Request:**
```http
GET /api/chat/conversations
Authorization: Bearer {token}
```

**Response (Customer):**
```json
{
  "success": true,
  "message": "Found 3 conversations",
  "data": [
    {
      "id": 5,
      "customer_id": 10,
      "seller_id": 15,
      "created_at": "2025-11-20T10:30:00",
      "updated_at": "2025-11-22T14:25:00",
      "seller_first_name": "John",
      "seller_last_name": "Doe",
      "seller_email": "seller@example.com",
      "seller_business_name": "John's Electronics",
      "unread_count": 2,
      "last_message": "Your order is ready for pickup",
      "last_message_time": "2025-11-22T14:25:00"
    }
  ]
}
```

**Response (Seller):**
```json
{
  "success": true,
  "message": "Found 5 conversations",
  "data": [
    {
      "id": 5,
      "customer_id": 10,
      "seller_id": 15,
      "created_at": "2025-11-20T10:30:00",
      "updated_at": "2025-11-22T14:25:00",
      "customer_first_name": "Jane",
      "customer_last_name": "Smith",
      "customer_email": "customer@example.com",
      "unread_count": 1,
      "last_message": "Do you have this in blue?",
      "last_message_time": "2025-11-22T14:20:00"
    }
  ]
}
```

**Features:**
- Sorted by `updated_at DESC` (most recent first)
- Shows unread message count per conversation
- Includes last message preview
- Different data for customers vs sellers

---

### 2. Get or Create Conversation
**Endpoint:** `GET /api/chat/conversations/{other_user_id}`  
**Auth:** Customer or Seller authentication required  
**Description:** Gets existing conversation or creates new one

**Request (Customer to Seller):**
```http
GET /api/chat/conversations/15
Authorization: Bearer {customer_token}
```

**Request (Seller to Customer):**
```http
GET /api/chat/conversations/10
Authorization: Bearer {seller_token}
```

**Response (Existing):**
```json
{
  "success": true,
  "message": "Conversation found",
  "data": {
    "id": 5,
    "customer_id": 10,
    "seller_id": 15,
    "created_at": "2025-11-20T10:30:00",
    "updated_at": "2025-11-22T14:25:00"
  }
}
```

**Response (New):**
```json
{
  "success": true,
  "message": "New conversation created",
  "data": {
    "id": 8,
    "customer_id": 10,
    "seller_id": 15,
    "created_at": "2025-11-22T15:00:00",
    "updated_at": "2025-11-22T15:00:00"
  }
}
```

**Validation:**
- Customer can only chat with sellers
- Seller can only chat with customers
- Returns 400 if target user has wrong role
- Automatically creates conversation if none exists

---

### 3. Get Messages in Conversation
**Endpoint:** `GET /api/chat/conversations/{conversation_id}/messages`  
**Auth:** Customer or Seller authentication required  
**Description:** Gets all messages and marks opposite sender's messages as read

**Request:**
```http
GET /api/chat/conversations/5/messages
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "message": "Found 12 messages",
  "data": [
    {
      "id": 45,
      "conversation_id": 5,
      "sender_id": 10,
      "sender_type": "customer",
      "message": "Hi, do you have this product in stock?",
      "is_read": 1,
      "created_at": "2025-11-20T10:35:00",
      "first_name": "Jane",
      "last_name": "Smith",
      "email": "customer@example.com"
    },
    {
      "id": 46,
      "conversation_id": 5,
      "sender_id": 15,
      "sender_type": "seller",
      "message": "Yes! We have 10 units available.",
      "is_read": 1,
      "created_at": "2025-11-20T10:40:00",
      "first_name": "John",
      "last_name": "Doe",
      "email": "seller@example.com"
    },
    {
      "id": 47,
      "conversation_id": 5,
      "sender_id": 10,
      "sender_type": "customer",
      "message": "Great! I'll order 2.",
      "is_read": 1,
      "created_at": "2025-11-20T10:42:00",
      "first_name": "Jane",
      "last_name": "Smith",
      "email": "customer@example.com"
    }
  ]
}
```

**Features:**
- Messages ordered chronologically (`ORDER BY created_at ASC`)
- Automatically marks opposite sender's unread messages as read
- Includes sender information (name, email)
- Verifies user is part of conversation (403 if not)

---

### 4. Send Message
**Endpoint:** `POST /api/chat/conversations/{conversation_id}/messages`  
**Auth:** Customer or Seller authentication required  
**Description:** Sends a message in an existing conversation

**Request:**
```http
POST /api/chat/conversations/5/messages
Authorization: Bearer {token}
Content-Type: application/json

{
  "message": "Your order is ready for pickup!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message sent successfully",
  "data": {
    "id": 48,
    "conversation_id": 5,
    "sender_id": 15,
    "sender_type": "seller",
    "message": "Your order is ready for pickup!",
    "is_read": 0,
    "created_at": "2025-11-22T15:10:00"
  }
}
```

**Validation:**
- Message cannot be empty (400 error)
- Message max length: 5000 characters (400 error)
- User must be part of conversation (403 error)
- Automatically sets correct `sender_type` based on user role
- Updates conversation's `updated_at` timestamp

---

### 5. Get Unread Count
**Endpoint:** `GET /api/chat/unread-count`  
**Auth:** Customer or Seller authentication required  
**Description:** Gets total unread message count across all conversations

**Request:**
```http
GET /api/chat/unread-count
Authorization: Bearer {token}
```

**Response:**
```json
{
  "success": true,
  "message": "Unread count retrieved",
  "data": {
    "unread_count": 5
  }
}
```

**Features:**
- Counts unread messages from opposite sender type
- Customer sees unread messages from sellers
- Seller sees unread messages from customers
- Useful for notification badges

---

## 🔄 How It Works

### Conversation Flow

```
┌─────────────────────────────────────────────────────────────┐
│ CUSTOMER INITIATES CHAT                                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ GET /api/chat/conversations/{seller_id}                      │
│ • Check if conversation exists (customer_id + seller_id)     │
│ • If exists: Return conversation                             │
│ • If not: Create new conversation                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ POST /api/chat/conversations/{conv_id}/messages              │
│ • Insert message with sender_id, sender_type='customer'      │
│ • Message marked as is_read=0                                │
│ • Update conversation.updated_at                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ SELLER OPENS CHAT                                            │
│ GET /api/chat/conversations/{conv_id}/messages               │
│ • Fetch all messages ORDER BY created_at ASC                 │
│ • Mark all customer messages as is_read=1                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ SELLER REPLIES                                               │
│ POST /api/chat/conversations/{conv_id}/messages              │
│ • Insert message with sender_id, sender_type='seller'        │
│ • Message marked as is_read=0                                │
│ • Same conversation_id used                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ CUSTOMER SEES REPLY                                          │
│ GET /api/chat/conversations/{conv_id}/messages               │
│ • Fetch all messages chronologically                         │
│ • Mark all seller messages as is_read=1                      │
└─────────────────────────────────────────────────────────────┘
```

---

### Message Read Logic

**When Customer Opens Chat:**
```sql
UPDATE messages
SET is_read = 1
WHERE conversation_id = ?
AND sender_type = 'seller'  -- Mark seller's messages as read
AND is_read = 0
```

**When Seller Opens Chat:**
```sql
UPDATE messages
SET is_read = 1
WHERE conversation_id = ?
AND sender_type = 'customer'  -- Mark customer's messages as read
AND is_read = 0
```

---

## 🔄 Real-Time Updates

### Option 1: Polling (Simple)
Client polls for new messages every 3-5 seconds:

```javascript
// Customer chat component
function pollMessages(conversationId) {
  setInterval(async () => {
    const response = await fetch(
      `/api/chat/conversations/${conversationId}/messages`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    const data = await response.json();
    updateMessagesUI(data.data);
  }, 3000); // Poll every 3 seconds
}
```

### Option 2: Long Polling
Client holds connection until new message arrives or timeout.

### Option 3: WebSockets (Advanced)
Real-time bidirectional communication (requires additional setup).

---

## 🧪 Testing Procedures

### Test Scenario 1: Customer Initiates Chat

```bash
# 1. Customer gets or creates conversation with seller (ID: 15)
GET /api/chat/conversations/15
Authorization: Bearer {customer_token}
# Expected: Conversation created or existing returned

# 2. Customer sends first message
POST /api/chat/conversations/5/messages
{
  "message": "Hi! Is this product available?"
}
# Expected: Message sent, is_read=0

# 3. Verify message in database
SELECT * FROM messages WHERE conversation_id = 5;
# Expected: sender_type='customer', is_read=0

# 4. Seller opens chat
GET /api/chat/conversations/5/messages
Authorization: Bearer {seller_token}
# Expected: All messages returned, customer message marked is_read=1

# 5. Verify read status updated
SELECT is_read FROM messages WHERE conversation_id = 5 AND sender_type = 'customer';
# Expected: is_read=1
```

---

### Test Scenario 2: Seller Replies

```bash
# 1. Seller sends reply
POST /api/chat/conversations/5/messages
Authorization: Bearer {seller_token}
{
  "message": "Yes, we have 5 units in stock!"
}
# Expected: Message sent, sender_type='seller', is_read=0

# 2. Customer opens chat
GET /api/chat/conversations/5/messages
Authorization: Bearer {customer_token}
# Expected: Both messages returned chronologically, seller message marked read

# 3. Verify chronological order
SELECT message, created_at FROM messages 
WHERE conversation_id = 5 
ORDER BY created_at ASC;
# Expected: Customer message first, seller message second
```

---

### Test Scenario 3: Unread Count

```bash
# 1. Seller sends 3 messages
POST /api/chat/conversations/5/messages (3 times)
# Expected: 3 messages created, all is_read=0

# 2. Customer checks unread count
GET /api/chat/unread-count
Authorization: Bearer {customer_token}
# Expected: unread_count >= 3

# 3. Customer opens chat
GET /api/chat/conversations/5/messages
# Expected: All seller messages marked read

# 4. Customer checks unread count again
GET /api/chat/unread-count
# Expected: unread_count decreased by 3
```

---

### Test Scenario 4: Unique Conversation Constraint

```bash
# 1. Customer creates conversation with seller
GET /api/chat/conversations/15
# Expected: Conversation ID: 5 created

# 2. Customer tries to create again
GET /api/chat/conversations/15
# Expected: Same conversation ID: 5 returned (not duplicate)

# 3. Verify database
SELECT COUNT(*) FROM conversations 
WHERE customer_id = 10 AND seller_id = 15;
# Expected: COUNT = 1 (unique constraint enforced)
```

---

## 🔗 Integration Examples

### Customer Chat Interface

```javascript
// customer_chat.js

// Initialize chat with seller
async function startChat(sellerId) {
  // Get or create conversation
  const convResponse = await fetch(`/api/chat/conversations/${sellerId}`, {
    headers: {
      'Authorization': `Bearer ${customerToken}`
    }
  });
  const convData = await convResponse.json();
  const conversationId = convData.data.id;
  
  // Load messages
  loadMessages(conversationId);
  
  // Start polling for new messages
  startPolling(conversationId);
}

// Load messages
async function loadMessages(conversationId) {
  const response = await fetch(
    `/api/chat/conversations/${conversationId}/messages`,
    {
      headers: {
        'Authorization': `Bearer ${customerToken}`
      }
    }
  );
  const data = await response.json();
  
  const chatWindow = document.getElementById('chat-messages');
  chatWindow.innerHTML = '';
  
  data.data.forEach(msg => {
    const msgDiv = document.createElement('div');
    msgDiv.className = msg.sender_type === 'customer' ? 'msg-sent' : 'msg-received';
    msgDiv.innerHTML = `
      <p><strong>${msg.first_name}:</strong> ${msg.message}</p>
      <small>${new Date(msg.created_at).toLocaleString()}</small>
    `;
    chatWindow.appendChild(msgDiv);
  });
  
  // Scroll to bottom
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Send message
async function sendMessage(conversationId) {
  const input = document.getElementById('message-input');
  const message = input.value.trim();
  
  if (!message) return;
  
  const response = await fetch(
    `/api/chat/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${customerToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    }
  );
  
  if (response.ok) {
    input.value = '';
    loadMessages(conversationId); // Refresh messages
  }
}

// Poll for new messages
function startPolling(conversationId) {
  setInterval(() => {
    loadMessages(conversationId);
  }, 3000); // Poll every 3 seconds
}

// Show unread count in navbar
async function updateUnreadBadge() {
  const response = await fetch('/api/chat/unread-count', {
    headers: {
      'Authorization': `Bearer ${customerToken}`
    }
  });
  const data = await response.json();
  
  const badge = document.getElementById('unread-badge');
  if (data.data.unread_count > 0) {
    badge.textContent = data.data.unread_count;
    badge.style.display = 'inline';
  } else {
    badge.style.display = 'none';
  }
}

// Update badge every 5 seconds
setInterval(updateUnreadBadge, 5000);
```

---

### Seller Chat Interface

```javascript
// seller_chat.js

// Load all conversations
async function loadConversations() {
  const response = await fetch('/api/chat/conversations', {
    headers: {
      'Authorization': `Bearer ${sellerToken}`
    }
  });
  const data = await response.json();
  
  const listDiv = document.getElementById('conversations-list');
  listDiv.innerHTML = '';
  
  data.data.forEach(conv => {
    const convDiv = document.createElement('div');
    convDiv.className = 'conversation-item';
    convDiv.onclick = () => openChat(conv.id);
    
    const unreadBadge = conv.unread_count > 0 
      ? `<span class="badge">${conv.unread_count}</span>` 
      : '';
    
    convDiv.innerHTML = `
      <h4>${conv.customer_first_name} ${conv.customer_last_name} ${unreadBadge}</h4>
      <p>${conv.last_message || 'No messages yet'}</p>
      <small>${new Date(conv.last_message_time).toLocaleString()}</small>
    `;
    
    listDiv.appendChild(convDiv);
  });
}

// Open specific chat
async function openChat(conversationId) {
  // Load messages (same as customer)
  const response = await fetch(
    `/api/chat/conversations/${conversationId}/messages`,
    {
      headers: {
        'Authorization': `Bearer ${sellerToken}`
      }
    }
  );
  const data = await response.json();
  
  // Render messages
  renderMessages(data.data);
  
  // Refresh conversations list (unread count updated)
  loadConversations();
}

// Reply to customer
async function replyToCustomer(conversationId, message) {
  const response = await fetch(
    `/api/chat/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sellerToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    }
  );
  
  if (response.ok) {
    openChat(conversationId); // Refresh chat
  }
}
```

---

## 📋 SQL Maintenance Queries

### View All Conversations
```sql
SELECT 
    c.id,
    c.customer_id,
    c.seller_id,
    CONCAT(cu.first_name, ' ', cu.last_name) as customer_name,
    CONCAT(su.first_name, ' ', su.last_name) as seller_name,
    s.business_name,
    c.created_at,
    c.updated_at
FROM conversations c
JOIN users cu ON c.customer_id = cu.id
JOIN users su ON c.seller_id = su.id
LEFT JOIN sellers s ON su.id = s.user_id
ORDER BY c.updated_at DESC;
```

---

### View Messages with Sender Info
```sql
SELECT 
    m.id,
    m.conversation_id,
    m.sender_type,
    CONCAT(u.first_name, ' ', u.last_name) as sender_name,
    m.message,
    m.is_read,
    m.created_at
FROM messages m
JOIN users u ON m.sender_id = u.id
WHERE m.conversation_id = ?
ORDER BY m.created_at ASC;
```

---

### Unread Messages Per Seller
```sql
SELECT 
    c.seller_id,
    CONCAT(u.first_name, ' ', u.last_name) as seller_name,
    COUNT(m.id) as unread_count
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
JOIN users u ON c.seller_id = u.id
WHERE m.sender_type = 'customer'
AND m.is_read = 0
GROUP BY c.seller_id, u.first_name, u.last_name
ORDER BY unread_count DESC;
```

---

### Chat Activity Statistics
```sql
-- Total conversations
SELECT COUNT(*) as total_conversations FROM conversations;

-- Total messages
SELECT COUNT(*) as total_messages FROM messages;

-- Messages by type
SELECT sender_type, COUNT(*) as count
FROM messages
GROUP BY sender_type;

-- Most active conversations
SELECT 
    conversation_id,
    COUNT(*) as message_count
FROM messages
GROUP BY conversation_id
ORDER BY message_count DESC
LIMIT 10;
```

---

## 🎯 Summary

### Key Features Implemented
✅ **Unique Conversations:** One conversation per customer-seller pair  
✅ **Auto-Creation:** Conversation created on first message  
✅ **Sender Tracking:** Explicit `sender_type` field (customer/seller)  
✅ **Chronological Ordering:** Messages always `ORDER BY created_at ASC`  
✅ **Read Status:** Auto-mark opposite sender's messages as read  
✅ **Bidirectional:** Both sides see same conversation  
✅ **Unread Counts:** Track unread messages per conversation  
✅ **Updated Timestamps:** Conversation `updated_at` refreshes on new message  
✅ **Role Validation:** Only customers and sellers can chat  
✅ **Real-Time Support:** Compatible with polling or WebSockets  

### Database Optimizations
- Unique constraint prevents duplicate conversations
- Indexes on customer_id, seller_id, conversation_id, created_at
- Cascading deletes maintain referential integrity
- Auto-updating timestamps reduce manual updates

### API Endpoints (5 Total)
1. GET `/api/chat/conversations` - List all conversations
2. GET `/api/chat/conversations/{other_user_id}` - Get/create conversation
3. GET `/api/chat/conversations/{id}/messages` - Get messages + mark read
4. POST `/api/chat/conversations/{id}/messages` - Send message
5. GET `/api/chat/unread-count` - Get total unread count

---

**📅 Last Updated:** November 22, 2025  
**📝 Version:** 1.0  
**👨‍💻 Maintainer:** Hub E-Commerce Development Team
