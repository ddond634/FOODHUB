"""
Messaging API
Endpoints for real-time customer-seller messaging
"""

from flask import Blueprint, request, jsonify, g
from backend.auth import role_required, token_required, JWT_SECRET
from backend.api_utils import success_response, error_response
from datetime import datetime
import os

def get_db():
    """Get database connection from Flask g object"""
    if not hasattr(g, 'db'):
        import pymysql
        import sqlite3
        
        DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()
        
        if DB_ENGINE == 'mysql':
            g.db = pymysql.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASS', '') or os.environ.get('DB_PASSWORD', ''),
                database=os.environ.get('DB_NAME', 'qwerty'),
                port=int(os.environ.get('DB_PORT', 3306)),
                cursorclass=pymysql.cursors.DictCursor,
                charset='utf8mb4'
            )
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(BASE_DIR, 'qwerty.db')
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
    
    return g.db

messaging_bp = Blueprint('messaging', __name__, url_prefix='')
DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

# Helper function to get DictCursor
def get_dict_cursor(conn):
    """Get dictionary cursor based on database engine"""
    if DB_ENGINE == 'mysql':
        import pymysql.cursors
        return conn.cursor(pymysql.cursors.DictCursor)
    else:
        import sqlite3
        conn.row_factory = sqlite3.Row
        return conn.cursor()

@messaging_bp.route('/api/conversations', methods=['GET'])
@role_required('customer')
def get_customer_conversations():
    """
    Get all conversations for the authenticated customer
    Returns conversations with last message preview and unread count
    """
    try:
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Get conversations with seller info and last message
        cursor.execute('''
            SELECT 
                c.id,
                c.customer_id,
                c.seller_id,
                COALESCE(c.updated_at, c.created_at) as last_message_at,
                c.created_at,
                COALESCE(s.business_name, CONCAT(u.first_name, ' ', u.last_name), u.email, 'Seller') as seller_name,
                u.email as seller_email,
                (SELECT COUNT(*) FROM messages 
                 WHERE conversation_id = c.id 
                 AND sender_type = 'seller' 
                 AND is_read = FALSE) as unread_count,
                (SELECT message FROM messages 
                 WHERE conversation_id = c.id 
                 ORDER BY created_at DESC LIMIT 1) as last_message
            FROM conversations c
            JOIN users u ON c.seller_id = u.id
            INNER JOIN sellers s ON s.user_id = u.id
            WHERE c.customer_id = %s
            AND u.role = 'seller'
            ORDER BY COALESCE(c.updated_at, c.created_at) DESC
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT 
                c.id,
                c.customer_id,
                c.seller_id,
                COALESCE(c.updated_at, c.created_at) as last_message_at,
                c.created_at,
                COALESCE(s.business_name, (u.first_name || ' ' || u.last_name), u.email, 'Seller') as seller_name,
                u.email as seller_email,
                (SELECT COUNT(*) FROM messages 
                 WHERE conversation_id = c.id 
                 AND sender_type = 'seller' 
                 AND is_read = 0) as unread_count,
                (SELECT message FROM messages 
                 WHERE conversation_id = c.id 
                 ORDER BY created_at DESC LIMIT 1) as last_message
            FROM conversations c
            JOIN users u ON c.seller_id = u.id
            INNER JOIN sellers s ON s.user_id = u.id
            WHERE c.customer_id = ?
            AND u.role = 'seller'
            ORDER BY COALESCE(c.updated_at, c.created_at) DESC
        ''', (g.user_id,))
        
        conversations = cursor.fetchall()
        print(f"📥 Found {len(conversations)} conversations in database")
        
        # Convert to list of dicts for consistent format
        result = []
        for conv in conversations:
            conv_dict = conv if isinstance(conv, dict) else {
                'id': conv[0],
                'customer_id': conv[1],
                'seller_id': conv[2],
                'last_message_at': conv[3],
                'created_at': conv[4],
                'seller_name': conv[5] if len(conv) > 5 else None,
                'seller_email': conv[6] if len(conv) > 6 else None,
                'unread_count': conv[7] if len(conv) > 7 else 0,
                'last_message': conv[8] if len(conv) > 8 else None
            }
            
            last_msg_at = conv_dict.get('last_message_at') if isinstance(conv_dict, dict) else conv_dict['last_message_at']
            created_at_val = conv_dict.get('created_at') if isinstance(conv_dict, dict) else conv_dict['created_at']
            
            result.append({
                'id': conv_dict.get('id') if isinstance(conv_dict, dict) else conv_dict['id'],
                'customer_id': conv_dict.get('customer_id') if isinstance(conv_dict, dict) else conv_dict['customer_id'],
                'seller_id': conv_dict.get('seller_id') if isinstance(conv_dict, dict) else conv_dict['seller_id'],
                'seller_name': conv_dict.get('seller_name') or 'Seller',
                'seller_email': conv_dict.get('seller_email') or '',
                'last_message': conv_dict.get('last_message'),
                'last_message_at': (last_msg_at.isoformat() if hasattr(last_msg_at, 'isoformat') else str(last_msg_at)) if last_msg_at else None,
                'unread_count': int(conv_dict.get('unread_count', 0)) if conv_dict.get('unread_count') else 0,
                'created_at': (created_at_val.isoformat() if hasattr(created_at_val, 'isoformat') else str(created_at_val)) if created_at_val else None
            })
        
        print(f"✅ Returning {len(result)} conversations to frontend")
        return success_response({
            'conversations': result,
            'total': len(result)
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error fetching conversations: {str(e)}")
        traceback.print_exc()
        return error_response(f'Failed to fetch conversations: {str(e)}', 500)

@messaging_bp.route('/api/conversations/seller', methods=['GET'])
@role_required('seller')
def get_seller_conversations():
    """
    Get all conversations for the authenticated seller - supports store_id filtering
    Returns conversations with customer info and unread count
    """
    try:
        # Get seller ID from user_id
        user_id = g.user_id
        store_id = request.args.get('store_id', type=int)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Check if store_id column exists in conversations table
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM conversations LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(conversations)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build filter condition
        if store_id and store_id_column_exists:
            store_filter = 'c.seller_id = %s AND c.store_id = %s' if DB_ENGINE == 'mysql' else 'c.seller_id = ? AND c.store_id = ?'
            filter_params = (user_id, store_id)
        elif store_id_column_exists:
            # If store_id column exists but no store_id provided, only show conversations without store_id (main seller conversations)
            store_filter = 'c.seller_id = %s AND (c.store_id IS NULL OR c.store_id = 0)' if DB_ENGINE == 'mysql' else 'c.seller_id = ? AND (c.store_id IS NULL OR c.store_id = 0)'
            filter_params = (user_id,)
        else:
            # No store_id column - show all conversations for seller
            store_filter = 'c.seller_id = %s' if DB_ENGINE == 'mysql' else 'c.seller_id = ?'
            filter_params = (user_id,)
        
        # conversations.seller_id references users.id, not sellers.id
        # So we can directly use user_id to match conversations
        # Get conversations with customer info and last message
        # Handle both schemas - some have last_message_at, some don't
        # Use updated_at or created_at instead of last_message_at if it doesn't exist
        cursor.execute(f'''
            SELECT 
                c.id,
                c.customer_id,
                c.seller_id,
                COALESCE(c.updated_at, c.created_at) as last_message_at,
                c.created_at,
                COALESCE(CONCAT(u.first_name, ' ', u.last_name), u.email, 'Customer') as customer_name,
                u.email as customer_email,
                (SELECT COUNT(*) FROM messages 
                 WHERE conversation_id = c.id 
                 AND sender_type = 'customer' 
                 AND is_read = FALSE) as unread_count,
                (SELECT message FROM messages 
                 WHERE conversation_id = c.id 
                 ORDER BY created_at DESC LIMIT 1) as last_message
            FROM conversations c
            JOIN users u ON c.customer_id = u.id
            WHERE {store_filter}
            ORDER BY COALESCE(c.updated_at, c.created_at) DESC
        ''' if DB_ENGINE == 'mysql' else f'''
            SELECT 
                c.id,
                c.customer_id,
                c.seller_id,
                COALESCE(c.updated_at, c.created_at) as last_message_at,
                c.created_at,
                COALESCE(u.first_name || ' ' || u.last_name, u.email, 'Customer') as customer_name,
                u.email as customer_email,
                (SELECT COUNT(*) FROM messages 
                 WHERE conversation_id = c.id 
                 AND sender_type = 'customer' 
                 AND is_read = 0) as unread_count,
                (SELECT message FROM messages 
                 WHERE conversation_id = c.id 
                 ORDER BY created_at DESC LIMIT 1) as last_message
            FROM conversations c
            JOIN users u ON c.customer_id = u.id
            WHERE {store_filter}
            ORDER BY COALESCE(c.updated_at, c.created_at) DESC
        ''', filter_params)
        
        conversations = cursor.fetchall()
        
        # Convert to list of dicts
        result = []
        for conv in conversations:
            conv_dict = conv if isinstance(conv, dict) else {
                'id': conv[0],
                'customer_id': conv[1],
                'seller_id': conv[2],
                'last_message_at': conv[3],
                'created_at': conv[4],
                'customer_name': conv[5] if len(conv) > 5 else None,
                'customer_email': conv[6] if len(conv) > 6 else None,
                'unread_count': conv[7] if len(conv) > 7 else 0,
                'last_message': conv[8] if len(conv) > 8 else None
            }
            
            result.append({
                'id': conv_dict.get('id') if isinstance(conv_dict, dict) else conv_dict['id'],
                'customer_id': conv_dict.get('customer_id') if isinstance(conv_dict, dict) else conv_dict['customer_id'],
                'seller_id': conv_dict.get('seller_id') if isinstance(conv_dict, dict) else conv_dict['seller_id'],
                'customer_name': conv_dict.get('customer_name') or 'Customer',
                'customer_email': conv_dict.get('customer_email') or '',
                'last_message': conv_dict.get('last_message'),
                'last_message_at': (conv_dict.get('last_message_at').isoformat() if isinstance(conv_dict.get('last_message_at'), datetime) else conv_dict.get('last_message_at')) if conv_dict.get('last_message_at') else None,
                'unread_count': int(conv_dict.get('unread_count', 0)) if conv_dict.get('unread_count') else 0,
                'created_at': (conv_dict.get('created_at').isoformat() if isinstance(conv_dict.get('created_at'), datetime) else conv_dict.get('created_at')) if conv_dict.get('created_at') else None
            })
        
        return success_response({
            'conversations': result,
            'total': len(result)
        })
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return error_response(f'Failed to fetch conversations: {error_msg}', 500)

@messaging_bp.route('/api/conversations/create', methods=['POST'], strict_slashes=False)
@role_required('customer')
def create_conversation():
    """
    Create or fetch existing conversation with a seller
    Used when customer clicks "Message Seller"
    """
    try:
        data = request.get_json()
        seller_id_param = data.get('seller_id')  # This is sellers.id
        
        if not seller_id_param:
            return error_response('Seller ID is required', 400)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Get seller's user_id from sellers table
        # conversations.seller_id references users.id, not sellers.id
        cursor.execute('''
            SELECT user_id FROM sellers WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT user_id FROM sellers WHERE id = ?
        ''', (seller_id_param,))
        
        seller = cursor.fetchone()
        if not seller:
            return error_response('Seller not found', 404)
        
        seller_user_id = seller.get('user_id') if isinstance(seller, dict) else seller[0]
        
        # Check if conversation already exists
        cursor.execute('''
            SELECT id FROM conversations 
            WHERE customer_id = %s AND seller_id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT id FROM conversations 
            WHERE customer_id = ? AND seller_id = ?
        ''', (g.user_id, seller_user_id))
        
        existing = cursor.fetchone()
        
        if existing:
            conversation_id = existing.get('id') if isinstance(existing, dict) else existing[0]
            is_new = False
        else:
            # Create new conversation
            # Use seller_user_id (users.id) not seller_id_param (sellers.id)
            cursor.execute('''
                INSERT INTO conversations (customer_id, seller_id, created_at, updated_at) 
                VALUES (%s, %s, NOW(), NOW())
            ''' if DB_ENGINE == 'mysql' else '''
                INSERT INTO conversations (customer_id, seller_id, created_at, updated_at) 
                VALUES (?, ?, ?, ?)
            ''', (g.user_id, seller_user_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()) if DB_ENGINE != 'mysql' else (g.user_id, seller_user_id))
            
            conn.commit()
            conversation_id = cursor.lastrowid
            is_new = True
            
            # Send automated greeting message if this is a new conversation
            try:
                # Get seller greeting message
                cursor.execute('''
                    SELECT greeting_message, user_id FROM sellers WHERE id = %s
                ''' if DB_ENGINE == 'mysql' else '''
                    SELECT greeting_message, user_id FROM sellers WHERE id = ?
                ''', (seller_id_param,))
                
                seller_data = cursor.fetchone()
                greeting_text = 'Hello! Thank you for your interest. How can I help you today?'
                seller_user_id = None
                
                if seller_data:
                    if isinstance(seller_data, dict):
                        greeting_text = seller_data.get('greeting_message') or greeting_text
                        seller_user_id = seller_data.get('user_id')
                    elif len(seller_data) > 0:
                        if seller_data[0]:  # greeting_message
                            greeting_text = seller_data[0]
                        if len(seller_data) > 1 and seller_data[1]:  # user_id
                            seller_user_id = seller_data[1]
                
                if seller_user_id:
                    # Insert greeting message as seller message
                    cursor.execute('''
                        INSERT INTO messages (conversation_id, sender_id, sender_type, message, is_read, created_at)
                        VALUES (%s, %s, 'seller', %s, 0, NOW())
                    ''' if DB_ENGINE == 'mysql' else '''
                        INSERT INTO messages (conversation_id, sender_id, sender_type, message, is_read, created_at)
                        VALUES (?, ?, 'seller', ?, 0, ?)
                    ''', (conversation_id, seller_user_id, greeting_text, datetime.utcnow().isoformat()) if DB_ENGINE != 'mysql' else (conversation_id, seller_user_id, greeting_text))
                    
                    conn.commit()
            except Exception as greeting_err:
                # Don't fail conversation creation if greeting fails
                print(f"Warning: Could not send greeting message: {greeting_err}")
                import traceback
                traceback.print_exc()
        
        # Get seller info
        cursor.execute('''
            SELECT s.business_name, u.email as business_email 
            FROM sellers s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT s.business_name, u.email as business_email 
            FROM sellers s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (seller_id_param,))
        
        seller = cursor.fetchone()
        
        seller_name = None
        seller_email = None
        if seller:
            if isinstance(seller, dict):
                seller_name = seller.get('business_name')
                seller_email = seller.get('business_email')
            else:
                seller_name = seller[0] if len(seller) > 0 else None
                seller_email = seller[1] if len(seller) > 1 else None
        
        return success_response({
            'conversation_id': conversation_id,
            'seller_id': seller_id_param,  # Return the original sellers.id for frontend reference
            'seller_name': seller_name,
            'seller_email': seller_email,
            'created': is_new
        })
        
    except Exception as e:
        return error_response(f'Failed to create conversation: {str(e)}', 500)

@messaging_bp.route('/api/messages/<int:conversation_id>', methods=['GET'])
def get_messages(conversation_id):
    """
    Get all messages in a conversation
    Accessible by both customer and seller in the conversation
    """
    try:
        # Get current user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return error_response('Authorization required', 401)
        
        token = auth_header.replace('Bearer ', '')
        
        # Import JWT decode
        import jwt
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_role = payload.get('role')
            user_id = payload.get('user_id')
        except:
            return error_response('Invalid token', 401)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Verify user has access to this conversation
        cursor.execute('''
            SELECT customer_id, seller_id FROM conversations WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT customer_id, seller_id FROM conversations WHERE id = ?
        ''', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            return error_response('Conversation not found', 404)
        
        # Check authorization based on role
        conv_dict = conversation if isinstance(conversation, dict) else {
            'customer_id': conversation[0],
            'seller_id': conversation[1]
        }
        
        if user_role == 'customer':
            # For customer, check if their user_id matches the customer_id
            conv_customer_id = conv_dict.get('customer_id') if isinstance(conv_dict, dict) else conv_dict['customer_id']
            if conv_customer_id != user_id:
                return error_response('Unauthorized', 403)
        elif user_role == 'seller':
            # For seller: conversations.seller_id references users.id, not sellers.id
            # So we compare conversation.seller_id directly with user_id
            conv_seller_id = conv_dict.get('seller_id') if isinstance(conv_dict, dict) else conv_dict['seller_id']
            if conv_seller_id != user_id:
                return error_response('Unauthorized', 403)
        
        # Get messages (try to include attachment fields if they exist)
        try:
            cursor.execute('''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at,
                    attachment_url,
                    attachment_type
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at,
                    attachment_url,
                    attachment_type
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            ''', (conversation_id,))
        except:
            # If attachment columns don't exist, select without them
            cursor.execute('''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            ''', (conversation_id,))
        
        messages = cursor.fetchall()
        
        # Convert to list of dicts
        result = []
        for msg in messages:
            msg_dict = msg if isinstance(msg, dict) else {
                'id': msg[0],
                'conversation_id': msg[1],
                'sender_id': msg[2],
                'sender_type': msg[3],
                'message': msg[4],
                'is_read': msg[5],
                'created_at': msg[6],
                'attachment_url': msg[7] if len(msg) > 7 else None,
                'attachment_type': msg[8] if len(msg) > 8 else None
            }
            
            result.append({
                'id': msg_dict.get('id') if isinstance(msg_dict, dict) else msg_dict['id'],
                'conversation_id': msg_dict.get('conversation_id') if isinstance(msg_dict, dict) else msg_dict['conversation_id'],
                'sender_id': msg_dict.get('sender_id') if isinstance(msg_dict, dict) else msg_dict['sender_id'],
                'sender_type': msg_dict.get('sender_type') if isinstance(msg_dict, dict) else msg_dict['sender_type'],
                'message': msg_dict.get('message') if isinstance(msg_dict, dict) else msg_dict['message'],
                'is_read': bool(msg_dict.get('is_read') if isinstance(msg_dict, dict) else msg_dict['is_read']),
                'created_at': (msg_dict.get('created_at').isoformat() if isinstance(msg_dict.get('created_at'), datetime) else str(msg_dict.get('created_at'))) if msg_dict.get('created_at') else None,
                'attachment_url': msg_dict.get('attachment_url') if isinstance(msg_dict, dict) else (msg_dict.get('attachment_url') if 'attachment_url' in msg_dict else None),
                'attachment_type': msg_dict.get('attachment_type') if isinstance(msg_dict, dict) else (msg_dict.get('attachment_type') if 'attachment_type' in msg_dict else None)
            })
        
        return success_response({
            'messages': result,
            'total': len(result)
        })
        
    except Exception as e:
        print(f"ERROR in get_messages: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f'Failed to fetch messages: {str(e)}', 500)

@messaging_bp.route('/api/messages/<int:conversation_id>/send', methods=['POST'])
def send_message(conversation_id):
    """
    Send a new message in a conversation (supports text and attachments)
    Accessible by both customer and seller
    """
    try:
        # Get current user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return error_response('Authorization required', 401)
        
        token = auth_header.replace('Bearer ', '')
        
        # Import JWT decode
        import jwt
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_role = payload.get('role')
            user_id = payload.get('user_id')
        except:
            return error_response('Invalid token', 401)
        
        # Handle both JSON and FormData (for attachments)
        message_text = ''
        attachment_url = None
        attachment_type = None
        
        if request.is_json:
            data = request.get_json()
            message_text = data.get('message', '').strip()
        else:
            # Handle multipart/form-data for file uploads
            message_text = request.form.get('message', '').strip()
            
            if 'attachment' in request.files:
                file = request.files['attachment']
                if file and file.filename:
                    # Save file
                    import os
                    from werkzeug.utils import secure_filename
                    
                    upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'messages')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{user_id}_{filename}"
                    filepath = os.path.join(upload_folder, unique_filename)
                    
                    file.save(filepath)
                    
                    # Store relative path
                    attachment_url = f"/uploads/messages/{unique_filename}"
                    attachment_type = file.content_type or 'application/octet-stream'
        
        # Message or attachment is required
        if not message_text and not attachment_url:
            return error_response('Message text or attachment is required', 400)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Verify user is part of this conversation
        cursor.execute('''
            SELECT customer_id, seller_id FROM conversations WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT customer_id, seller_id FROM conversations WHERE id = ?
        ''', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            return error_response('Conversation not found', 404)
        
        # Check authorization based on role
        conv_dict = conversation if isinstance(conversation, dict) else {
            'customer_id': conversation[0],
            'seller_id': conversation[1]
        }
        
        if user_role == 'customer':
            # For customer, check if their user_id matches the customer_id
            conv_customer_id = conv_dict.get('customer_id') if isinstance(conv_dict, dict) else conv_dict['customer_id']
            if conv_customer_id != user_id:
                return error_response('Unauthorized', 403)
        elif user_role == 'seller':
            # For seller: conversations.seller_id references users.id, not sellers.id
            # So we compare conversation.seller_id directly with user_id
            conv_seller_id = conv_dict.get('seller_id') if isinstance(conv_dict, dict) else conv_dict['seller_id']
            if conv_seller_id != user_id:
                return error_response('Unauthorized', 403)
        
        # Check if attachment columns exist, if not, use NULL
        # Insert message (with or without attachment)
        try:
            if attachment_url:
                # Try to insert with attachment fields
                cursor.execute('''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message, attachment_url, attachment_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''' if DB_ENGINE == 'mysql' else '''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message, attachment_url, attachment_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (conversation_id, user_id, user_role, message_text or '', attachment_url, attachment_type))
            else:
                # Insert without attachment
                cursor.execute('''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (%s, %s, %s, %s)
                ''' if DB_ENGINE == 'mysql' else '''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (?, ?, ?, ?)
                ''', (conversation_id, user_id, user_role, message_text))
        except Exception as insert_error:
            # If attachment columns don't exist, insert without them
            if 'attachment' in str(insert_error).lower():
                cursor.execute('''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (%s, %s, %s, %s)
                ''' if DB_ENGINE == 'mysql' else '''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (?, ?, ?, ?)
                ''', (conversation_id, user_id, user_role, message_text))
            else:
                raise
        
        message_id = cursor.lastrowid
        
        # Update conversation's updated_at (don't try to update last_message_at if it doesn't exist)
        try:
            cursor.execute('''
                UPDATE conversations 
                SET updated_at = NOW()
                WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                UPDATE conversations 
                SET updated_at = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), conversation_id) if DB_ENGINE != 'mysql' else (conversation_id,))
        except Exception as update_err:
            # If updated_at doesn't exist or there's an error, just continue
            print(f"Warning: Could not update conversation timestamp: {update_err}")
            pass
        
        conn.commit()
        
        # Get the created message (without attachment columns first to avoid errors)
        try:
            cursor.execute('''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at,
                    attachment_url,
                    attachment_type
                FROM messages
                WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at,
                    attachment_url,
                    attachment_type
                FROM messages
                WHERE id = ?
            ''', (message_id,))
        except:
            # If attachment columns don't exist, select without them
            cursor.execute('''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at
                FROM messages
                WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT 
                    id,
                    conversation_id,
                    sender_id,
                    sender_type,
                    message,
                    is_read,
                    created_at
                FROM messages
                WHERE id = ?
            ''', (message_id,))
        
        message = cursor.fetchone()
        
        # Format message response
        msg_dict = {
            'id': message.get('id') if isinstance(message, dict) else message[0],
            'conversation_id': message.get('conversation_id') if isinstance(message, dict) else message[1],
            'sender_id': message.get('sender_id') if isinstance(message, dict) else message[2],
            'sender_type': message.get('sender_type') if isinstance(message, dict) else message[3],
            'message': message.get('message') if isinstance(message, dict) else message[4],
            'is_read': bool(message.get('is_read') if isinstance(message, dict) else message[5]),
            'created_at': (message.get('created_at').isoformat() if isinstance(message, dict) and message.get('created_at') else (message[6].isoformat() if len(message) > 6 and message[6] else None))
        }
        
        # Try to get attachment fields if they exist
        if len(message) > 7 or (isinstance(message, dict) and 'attachment_url' in message):
            if isinstance(message, dict):
                msg_dict['attachment_url'] = message.get('attachment_url')
                msg_dict['attachment_type'] = message.get('attachment_type')
            else:
                msg_dict['attachment_url'] = message[7] if len(message) > 7 else None
                msg_dict['attachment_type'] = message[8] if len(message) > 8 else None
        
        return success_response({'message': msg_dict}, 'Message sent successfully', 201)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(f'Failed to send message: {str(e)}', 500)

@messaging_bp.route('/api/messages/send', methods=['POST'])
def send_message_alt():
    """
    Alternative route for sending messages - accepts conversation_id in request body
    This matches the frontend API call format
    """
    try:
        # Get current user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return error_response('Authorization required', 401)
        
        token = auth_header.replace('Bearer ', '')
        
        # Import JWT decode
        import jwt
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_role = payload.get('role')
            user_id = payload.get('user_id')
        except:
            return error_response('Invalid token', 401)
        
        # Handle both JSON and FormData (for attachments)
        conversation_id = None
        message_text = ''
        attachment_url = None
        attachment_type = None
        
        if request.is_json:
            data = request.get_json()
            conversation_id = data.get('conversation_id')
            message_text = data.get('message', '').strip() or data.get('message_text', '').strip()
        else:
            # Handle multipart/form-data for file uploads
            conversation_id = request.form.get('conversation_id')
            message_text = request.form.get('message', '').strip() or request.form.get('message_text', '').strip()
            
            if 'attachment' in request.files:
                file = request.files['attachment']
                if file and file.filename:
                    # Save file
                    import os
                    from werkzeug.utils import secure_filename
                    
                    upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'messages')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{user_id}_{filename}"
                    filepath = os.path.join(upload_folder, unique_filename)
                    
                    file.save(filepath)
                    
                    # Store relative path
                    attachment_url = f"/uploads/messages/{unique_filename}"
                    attachment_type = file.content_type or 'application/octet-stream'
        
        if not conversation_id:
            return error_response('Conversation ID is required', 400)
        
        # Message or attachment is required
        if not message_text and not attachment_url:
            return error_response('Message text or attachment is required', 400)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Verify user is part of this conversation
        cursor.execute('''
            SELECT customer_id, seller_id FROM conversations WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT customer_id, seller_id FROM conversations WHERE id = ?
        ''', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            return error_response('Conversation not found', 404)
        
        # Check authorization based on role
        conv_dict = conversation if isinstance(conversation, dict) else {
            'customer_id': conversation[0],
            'seller_id': conversation[1]
        }
        
        if user_role == 'customer':
            # For customer, check if their user_id matches the customer_id
            conv_customer_id = conv_dict.get('customer_id') if isinstance(conv_dict, dict) else conv_dict['customer_id']
            if conv_customer_id != user_id:
                return error_response('Unauthorized', 403)
        elif user_role == 'seller':
            # For seller: conversations.seller_id references users.id, not sellers.id
            # So we compare conversation.seller_id directly with user_id
            conv_seller_id = conv_dict.get('seller_id') if isinstance(conv_dict, dict) else conv_dict['seller_id']
            if conv_seller_id != user_id:
                return error_response('Unauthorized', 403)
        
        # Insert message (with or without attachment)
        try:
            if attachment_url:
                # Try to insert with attachment fields
                cursor.execute('''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message, attachment_url, attachment_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''' if DB_ENGINE == 'mysql' else '''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message, attachment_url, attachment_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (conversation_id, user_id, user_role, message_text or '', attachment_url, attachment_type))
            else:
                # Insert without attachment
                cursor.execute('''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (%s, %s, %s, %s)
                ''' if DB_ENGINE == 'mysql' else '''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (?, ?, ?, ?)
                ''', (conversation_id, user_id, user_role, message_text))
        except Exception as insert_error:
            # If attachment columns don't exist, insert without them
            if 'attachment' in str(insert_error).lower():
                cursor.execute('''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (%s, %s, %s, %s)
                ''' if DB_ENGINE == 'mysql' else '''
                    INSERT INTO messages (conversation_id, sender_id, sender_type, message)
                    VALUES (?, ?, ?, ?)
                ''', (conversation_id, user_id, user_role, message_text))
            else:
                raise
        
        message_id = cursor.lastrowid
        
        # Update conversation's updated_at (don't try to update last_message_at if it doesn't exist)
        try:
            cursor.execute('''
                UPDATE conversations 
                SET updated_at = NOW()
                WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                UPDATE conversations 
                SET updated_at = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), conversation_id) if DB_ENGINE != 'mysql' else (conversation_id,))
        except:
            # If updated_at doesn't exist, just continue
            pass
        
        conn.commit()
        
        # Get the created message
        cursor.execute('''
            SELECT 
                id,
                conversation_id,
                sender_id,
                sender_type,
                message,
                is_read,
                created_at
            FROM messages
            WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT 
                id,
                conversation_id,
                sender_id,
                sender_type,
                message,
                is_read,
                created_at
            FROM messages
            WHERE id = ?
        ''', (message_id,))
        
        message = cursor.fetchone()
        
        # Format message response
        msg_dict = {
            'id': message.get('id') if isinstance(message, dict) else message[0],
            'conversation_id': message.get('conversation_id') if isinstance(message, dict) else message[1],
            'sender_id': message.get('sender_id') if isinstance(message, dict) else message[2],
            'sender_type': message.get('sender_type') if isinstance(message, dict) else message[3],
            'message': message.get('message') if isinstance(message, dict) else message[4],
            'is_read': bool(message.get('is_read') if isinstance(message, dict) else message[5]),
            'created_at': (message.get('created_at').isoformat() if isinstance(message, dict) and message.get('created_at') else (message[6].isoformat() if len(message) > 6 and message[6] else None))
        }
        
        # Try to get attachment fields if they exist
        try:
            cursor.execute('''
                SELECT attachment_url, attachment_type
                FROM messages
                WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT attachment_url, attachment_type
                FROM messages
                WHERE id = ?
            ''', (message_id,))
            att_result = cursor.fetchone()
            if att_result:
                if isinstance(att_result, dict):
                    msg_dict['attachment_url'] = att_result.get('attachment_url')
                    msg_dict['attachment_type'] = att_result.get('attachment_type')
                else:
                    msg_dict['attachment_url'] = att_result[0] if len(att_result) > 0 else None
                    msg_dict['attachment_type'] = att_result[1] if len(att_result) > 1 else None
        except:
            # Attachment columns don't exist, skip
            pass
        
        return success_response({'message': msg_dict}, 'Message sent successfully', 201)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(f'Failed to send message: {str(e)}', 500)

@messaging_bp.route('/api/messages/read/<int:conversation_id>', methods=['PATCH'])
def mark_messages_read(conversation_id):
    """
    Mark all messages in a conversation as read for the current user
    """
    try:
        # Get current user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return error_response('Authorization required', 401)
        
        token = auth_header.replace('Bearer ', '')
        
        # Import JWT decode
        import jwt
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_role = payload.get('role')
            user_id = payload.get('user_id')
        except Exception as jwt_error:
            print(f"❌ JWT decode error: {jwt_error}")
            return error_response('Invalid token', 401)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Verify user is part of this conversation
        cursor.execute('''
            SELECT customer_id, seller_id FROM conversations WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT customer_id, seller_id FROM conversations WHERE id = ?
        ''', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            return error_response('Conversation not found', 404)
        
        # Format conversation data (handle both dict and tuple formats)
        if isinstance(conversation, dict):
            customer_id = conversation.get('customer_id')
            seller_id = conversation.get('seller_id')
        else:
            customer_id = conversation[0] if len(conversation) > 0 else None
            seller_id = conversation[1] if len(conversation) > 1 else None
        
        # Check authorization based on role
        if user_role == 'customer':
            # For customer, check if their user_id matches the customer_id
            if customer_id != user_id:
                return error_response('Unauthorized', 403)
        elif user_role == 'seller':
            # For seller: conversations.seller_id references users.id, not sellers.id
            # So we compare conversation.seller_id directly with user_id
            if seller_id != user_id:
                return error_response('Unauthorized', 403)
        
        # Mark messages as read (messages sent by the OTHER party)
        opposite_role = 'seller' if user_role == 'customer' else 'customer'
        
        cursor.execute('''
            UPDATE messages 
            SET is_read = TRUE 
            WHERE conversation_id = %s AND sender_type = %s AND is_read = FALSE
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE messages 
            SET is_read = 1 
            WHERE conversation_id = ? AND sender_type = ? AND is_read = 0
        ''', (conversation_id, opposite_role))
        
        conn.commit()
        updated_count = cursor.rowcount
        
        return success_response({
            'marked_read': updated_count
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Mark messages read error: {str(e)}")
        traceback.print_exc()
        return error_response(f'Failed to mark messages as read: {str(e)}', 500)

@messaging_bp.route('/api/sellers/<int:seller_id>/greeting', methods=['GET'])
@token_required
def get_seller_greeting(seller_id):
    """
    Get seller's greeting message
    """
    try:
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # First, get the seller's user_id to verify authorization
        cursor.execute('''
            SELECT user_id FROM sellers WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT user_id FROM sellers WHERE id = ?
        ''', (seller_id,))
        
        seller_check = cursor.fetchone()
        if not seller_check:
            return error_response('Seller not found', 404)
        
        seller_user_id = seller_check.get('user_id') if isinstance(seller_check, dict) else seller_check[0]
        
        # Verify the authenticated user owns this seller account
        if seller_user_id != g.user_id:
            return error_response('Unauthorized', 403)
        
        # Get greeting message - handle case where column might not exist
        try:
            cursor.execute('''
                SELECT greeting_message FROM sellers WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT greeting_message FROM sellers WHERE id = ?
            ''', (seller_id,))
            
            seller = cursor.fetchone()
            
            if not seller:
                return error_response('Seller not found', 404)
            
            greeting = None
            if isinstance(seller, dict):
                greeting = seller.get('greeting_message')
            elif len(seller) > 0:
                greeting = seller[0]
            
            return success_response({
                'greeting_message': greeting or 'Hello! Thank you for your interest. How can I help you today?'
            })
        except Exception as col_err:
            # If greeting_message column doesn't exist, return default
            error_msg = str(col_err)
            print(f"Warning: Error fetching greeting_message: {error_msg}")
            # Check if it's a column error
            if 'greeting_message' in error_msg.lower() or 'column' in error_msg.lower() or 'unknown' in error_msg.lower():
                print("greeting_message column might not exist, returning default")
                return success_response({
                    'greeting_message': 'Hello! Thank you for your interest. How can I help you today?'
                })
            else:
                # Re-raise if it's a different error
                raise
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"❌ Error fetching seller greeting: {error_msg}")
        traceback.print_exc()
        return error_response(f'Failed to fetch greeting: {error_msg}', 500)

@messaging_bp.route('/api/sellers/greeting', methods=['PUT'])
@role_required('seller')
def update_seller_greeting():
    """
    Update seller's greeting message
    Only accessible by the seller themselves
    """
    try:
        data = request.get_json()
        greeting_message = data.get('greeting_message', '').strip()
        
        if len(greeting_message) > 500:
            return error_response('Greeting message too long (max 500 characters)', 400)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        # Get seller ID from user_id
        cursor.execute('''
            SELECT id FROM sellers WHERE user_id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT id FROM sellers WHERE user_id = ?
        ''', (g.user_id,))
        
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller profile not found', 404)
        
        seller_id = seller.get('id') if isinstance(seller, dict) else seller[0]
        
        # Update greeting message
        cursor.execute('''
            UPDATE sellers SET greeting_message = %s WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE sellers SET greeting_message = ? WHERE id = ?
        ''', (greeting_message, seller_id))
        
        conn.commit()
        
        return success_response({
            'greeting_message': greeting_message
        }, 'Greeting message updated successfully')
        
    except Exception as e:
        return error_response(f'Failed to update greeting: {str(e)}', 500)

@messaging_bp.route('/api/messages/unread-count', methods=['GET'])
def get_unread_count():
    """
    Get total unread message count for current user
    Used for badge notifications
    """
    try:
        # Get current user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return error_response('Authorization required', 401)
        
        token = auth_header.replace('Bearer ', '')
        
        # Import JWT decode
        import jwt
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_role = payload.get('role')
            user_id = payload.get('user_id')
        except:
            return error_response('Invalid token', 401)
        
        conn = get_db()
        cursor = get_dict_cursor(conn)
        
        if user_role == 'customer':
            # Count unread messages from sellers
            cursor.execute('''
                SELECT COUNT(*) as count FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.customer_id = %s 
                AND m.sender_type = 'seller' 
                AND m.is_read = FALSE
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT COUNT(*) as count FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.customer_id = ? 
                AND m.sender_type = 'seller' 
                AND m.is_read = 0
            ''', (user_id,))
        else:  # seller
            # For sellers, c.seller_id references users.id (the seller's user_id)
            # So we can directly use user_id to match conversations
            # Count unread messages from customers
            cursor.execute('''
                SELECT COUNT(*) as count FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.seller_id = %s 
                AND m.sender_type = 'customer' 
                AND m.is_read = FALSE
            ''' if DB_ENGINE == 'mysql' else '''
                SELECT COUNT(*) as count FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.seller_id = ? 
                AND m.sender_type = 'customer' 
                AND m.is_read = 0
            ''', (user_id,))
        
        result = cursor.fetchone()
        if not result:
            count = 0
        elif isinstance(result, dict):
            count = result.get('count', 0)
        else:
            count = result[0] if len(result) > 0 else 0
        
        return success_response({
            'unread_count': int(count) if count else 0
        })
        
    except Exception as e:
        return error_response(f'Failed to get unread count: {str(e)}', 500)
