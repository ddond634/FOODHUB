# Real-Time Customer-Seller Messaging System

## 📋 Overview

A complete real-time messaging system enabling direct communication between customers and sellers on the Hub e-commerce platform.

## ✅ Implementation Complete

### Database Tables Created
- **conversations**: Stores customer-seller conversation threads
  - `id`, `customer_id`, `seller_id`, `last_message_at`, `created_at`
  - Unique constraint on (customer_id, seller_id)
  - Indexed for fast lookups

- **messages**: Stores individual messages
  - `id`, `conversation_id`, `sender_id`, `sender_role`, `message_text`, `read_status`, `created_at`
  - Indexed on conversation_id, sender_id, read_status

### Backend API Endpoints (7 total)

#### 1. Get Customer Conversations
```http
GET /api/conversations
Authorization: Bearer {customer_token}
```
Returns all conversations for the logged-in customer with seller info, last message, and unread count.

#### 2. Get Seller Conversations
```http
GET /api/conversations/seller
Authorization: Bearer {seller_token}
```
Returns all conversations for the logged-in seller with customer info and unread count.

#### 3. Create/Get Conversation
```http
POST /api/conversations/create
Authorization: Bearer {customer_token}
Content-Type: application/json

{
  "seller_id": 1
}
```
Creates a new conversation or returns existing one between customer and seller.

#### 4. Get Messages
```http
GET /api/messages/{conversation_id}
Authorization: Bearer {token}
```
Returns all messages in a conversation (chronological order).

#### 5. Send Message
```http
POST /api/messages/send
Authorization: Bearer {token}
Content-Type: application/json

{
  "conversation_id": 1,
  "message_text": "Hello, is this product available?"
}
```
Sends a new message in a conversation.

#### 6. Mark Messages as Read
```http
PATCH /api/messages/read/{conversation_id}
Authorization: Bearer {token}
```
Marks all unread messages in a conversation as read.

#### 7. Get Unread Count
```http
GET /api/messages/unread-count
Authorization: Bearer {token}
```
Returns total unread message count for badge notifications.

### Frontend Components

#### Customer Messaging (`customer-messaging.js`)
- **Functions**:
  - `initializeMessaging()` - Initialize messaging system
  - `loadConversations()` - Load all conversations
  - `openConversation(id, sellerName)` - Open a specific conversation
  - `sendMessage()` - Send a new message
  - `messageSellerFromProduct(sellerId, sellerName)` - Start conversation from product page
  - `updateUnreadBadge()` - Update unread count badge
  
- **Auto-refresh**: Polls every 3 seconds for new messages, 6 seconds for conversation updates

#### Seller Messaging (`seller-messaging.js`)
- **Functions**:
  - `initializeSellerMessaging()` - Initialize seller messaging
  - `loadSellerConversations()` - Load customer conversations
  - `openSellerConversation(id, customerName)` - Open conversation
  - `sendSellerMessage()` - Send message to customer
  - `updateSellerUnreadBadge()` - Update seller's unread badge

- **Auto-refresh**: Same polling intervals as customer

#### UI Integration

**Customer Dashboard (account.html)**:
- Added Messages section in account grid
- Two-panel layout: conversations list + chat window
- Shows seller name, avatar, last message, time ago
- Unread message badges
- Real-time message display
- Message input with send button

**Seller Dashboard (seller_dashboard.html)**:
- Integrated into existing Messages section
- Replaced placeholder HTML with dynamic components
- Shows customer name, last message, unread count
- Chat interface with message history
- Message input and send functionality

**Product Pages (shop.html)**:
- Added "Message Seller" button in product modal
- Button only shown when user is logged in
- Clicking opens Messages tab and starts conversation
- Stores seller_id and seller_name for easy access

### CSS Styling

Complete responsive styles added to `account.html`:
- `.messages-container` - Main container
- `.messages-layout` - Two-column grid (350px + flex)
- `.conversations-panel` - Left sidebar with list
- `.chat-panel` - Right chat window
- `.conversation-item` - Individual conversation card
- `.message-bubble` - Chat message styling
- Own messages: green gradient (right-aligned)
- Other messages: gray background (left-aligned)
- Mobile responsive: stacks vertically on small screens

### Real-Time Updates

**Polling Strategy**:
- Messages in active conversation: Every 3 seconds
- Conversations list: Every 6 seconds
- Unread badge: Every 6 seconds
- Stops polling when leaving section

**Auto-scroll**:
- Automatically scrolls to bottom when new messages arrive
- Smooth scrolling with 100ms delay

**Instant Updates**:
- Sending message immediately updates UI
- No wait for next poll cycle
- Optimistic UI updates

## 🚀 Usage Guide

### For Customers

1. **Start Conversation**:
   - Click "Message Seller" on any product
   - Opens Messages section automatically
   - Creates conversation if doesn't exist

2. **View Messages**:
   - Go to Account page
   - Messages section shows all conversations
   - Click conversation to open chat

3. **Send Messages**:
   - Type message in input field
   - Click Send or press Enter
   - Message appears instantly

4. **Unread Notifications**:
   - Red badge shows unread count
   - Auto-clears when viewing conversation

### For Sellers

1. **View Customer Messages**:
   - Go to Seller Dashboard
   - Click "Messages" in sidebar
   - See all customer conversations

2. **Reply to Customers**:
   - Click conversation to open
   - Type and send reply
   - Customer sees message in real-time

3. **Unread Badge**:
   - Shows total unread messages
   - Updates automatically
   - Clears when viewing conversation

## 🔧 Configuration

### Polling Intervals (adjustable)

```javascript
// In customer-messaging.js and seller-messaging.js
const POLL_INTERVAL = 3000; // 3 seconds for messages
const CONVERSATION_POLL = 6000; // 6 seconds for list
```

### API Base URL

```javascript
const API_BASE = window.location.origin; // Auto-detects
```

## 🔒 Security Features

1. **Authentication**:
   - All endpoints require valid JWT token
   - Role-based access control (@role_required decorator)
   - Customer can only access their own conversations
   - Seller can only access their own conversations

2. **Authorization Checks**:
   - Conversation ownership verified on every request
   - Cannot access other users' messages
   - Cannot send messages to conversations not owned

3. **Input Validation**:
   - Message text required and trimmed
   - Conversation ID validated
   - HTML escaped on frontend display
   - SQL injection prevention via parameterized queries

4. **XSS Prevention**:
   - All user input escaped with `escapeHtml()`
   - No innerHTML for user content
   - textContent used for message display

## 📊 Database Indexes

For optimal performance:
```sql
-- conversations table
INDEX idx_customer_id (customer_id)
INDEX idx_seller_id (seller_id)
INDEX idx_last_message_at (last_message_at)
UNIQUE KEY unique_conversation (customer_id, seller_id)

-- messages table
INDEX idx_conversation_id (conversation_id)
INDEX idx_sender_id (sender_id)
INDEX idx_created_at (created_at)
INDEX idx_read_status (read_status)
```

## 🧪 Testing

### Manual Testing Steps

1. **Create Test Accounts**:
   ```bash
   # Customer: test_customer@hub.com
   # Seller: test_seller@hub.com
   ```

2. **Test Flow**:
   - Login as customer
   - Browse products
   - Click "Message Seller"
   - Send message
   - Login as seller (different browser)
   - See message in Messages section
   - Reply to customer
   - Switch back to customer view
   - See seller's reply

3. **Test Auto-refresh**:
   - Open conversation as customer
   - Send message as seller (different device/browser)
   - Watch customer's view update within 3 seconds

### Automated Test

Run the test script:
```bash
python tools/test_messaging_system.py
```

Tests:
- Customer registration/login
- Conversation creation
- Message sending
- Message retrieval
- Unread count
- Mark as read

## 🎯 Features Summary

✅ **Real-time messaging** - 3-second polling
✅ **Unread badges** - Visual notification system
✅ **Two-way communication** - Customer ↔ Seller
✅ **Conversation threading** - Organized by seller
✅ **Message history** - All messages stored
✅ **Read receipts** - Track message read status
✅ **Auto-scroll** - Always see latest messages
✅ **Responsive design** - Works on all devices
✅ **Keyboard shortcuts** - Enter to send
✅ **Empty states** - Helpful messages when no data
✅ **Time stamps** - "Just now", "2m ago", etc.
✅ **Avatar placeholders** - Visual user representation
✅ **Message Seller button** - Quick conversation start

## 🔄 Data Flow

```
Customer clicks "Message Seller" 
  → Creates conversation (if new)
  → Opens Messages tab
  → Loads conversation
  → Customer types message
  → POST /api/messages/send
  → Message stored in database
  → Updates last_message_at
  → Seller's dashboard polls
  → Seller sees new message
  → Seller replies
  → Customer's view polls
  → Customer sees reply
  → Marks as read on view
  → Badge count updates
```

## 📱 Mobile Responsive

- Conversations list stacks above chat on small screens
- Touch-friendly button sizes
- Swipe-friendly layout
- Optimized for portrait orientation

## 🚧 Future Enhancements

Potential improvements (not yet implemented):
- WebSocket support for instant delivery
- Message delivery status (sent/delivered/read)
- Typing indicators
- Image/file attachments
- Message search
- Conversation archiving
- Block/report functionality
- Push notifications
- Message reactions/emojis
- Conversation muting

## 📝 Files Modified/Created

### Database
- `database/migrate_add_messaging_system.py` ✨ NEW

### Backend
- `backend/messaging_api.py` ✨ NEW (683 lines)
- `backend/server.py` ✏️ MODIFIED (added messaging_bp registration)

### Frontend JavaScript
- `frontend/js/customer-messaging.js` ✨ NEW (449 lines)
- `frontend/js/seller-messaging.js` ✨ NEW (391 lines)

### Frontend HTML
- `frontend/account.html` ✏️ MODIFIED (added Messages section + CSS)
- `frontend/seller_dashboard.html` ✏️ MODIFIED (replaced Messages section)
- `frontend/shop.html` ✏️ MODIFIED (added Message Seller button)

### Testing
- `tools/test_messaging_system.py` ✨ NEW

## ✅ Implementation Status

| Component | Status | Lines of Code |
|-----------|--------|---------------|
| Database Migration | ✅ Complete | 115 |
| Backend API | ✅ Complete | 683 |
| Customer Frontend | ✅ Complete | 449 |
| Seller Frontend | ✅ Complete | 391 |
| CSS Styling | ✅ Complete | 250+ |
| Integration | ✅ Complete | - |
| Testing | ✅ Complete | 165 |
| **TOTAL** | **✅ COMPLETE** | **~2,053 lines** |

---

## 🎉 System Ready!

The messaging system is fully implemented and ready for production use. All conversations are stored in the database, messages sync in real-time via polling, and the UI is polished and responsive.

**Quick Start**:
1. Server already has messaging_bp registered ✅
2. Database tables created ✅
3. Frontend files in place ✅
4. Navigate to any product → Click "Message Seller" → Start chatting! 💬
