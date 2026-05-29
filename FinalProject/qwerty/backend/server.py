# -*- coding: utf-8 -*-
"""
Hub E-Commerce Platform - Flask Application
Configured for UTF-8 encoding to support Unicode characters on all platforms
"""

# Core imports and initialization placed early so decorators can reference `app` and auth helpers
from flask import Flask, request, jsonify, send_from_directory, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS
from .auth import generate_token, token_required, role_required, REFRESH_TOKEN_EXP_DAYS, verify_token, get_token_from_request
from .api_utils import success_response, error_response, format_row, format_rows
from .validators import validate_email, validate_password, validate_name
from .email_service import generate_otp, store_otp, send_otp_email, verify_otp, revoke_otp, send_welcome_email
import os
import pymysql
import pymysql.cursors
# SQLite removed - MySQL only
from datetime import datetime, timedelta
import hashlib
import secrets
import uuid
import atexit
from dotenv import load_dotenv

# Detect templates/static folders (basic detection)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
load_dotenv(os.path.join(BASE_DIR,'.env'))
TEMPLATES_DIR = None
STATIC_DIR = None
# Legacy UI aliases used in multiple places later in the file
UI_TEMPLATES_DIR = None
UI_STATIC_DIR = None
try:
    frontend_dir = os.path.join(BASE_DIR, 'frontend')
    tdir = os.path.join(frontend_dir, 'templates')
    if os.path.exists(frontend_dir):
        if not os.path.exists(tdir):
            tdir = frontend_dir
        TEMPLATES_DIR = tdir
        STATIC_DIR = frontend_dir
except Exception:
    TEMPLATES_DIR = None
    STATIC_DIR = None
    UI_TEMPLATES_DIR = None
    UI_STATIC_DIR = None

# Ensure UI_* aliases exist for legacy code paths
if UI_TEMPLATES_DIR is None:
    UI_TEMPLATES_DIR = TEMPLATES_DIR
if UI_STATIC_DIR is None:
    UI_STATIC_DIR = STATIC_DIR

# Create Flask app so decorators below work
app = Flask(__name__, template_folder=TEMPLATES_DIR or None, static_folder=STATIC_DIR or None)
CORS(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

# Uploads configuration (used by file upload helpers)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'products')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Server instance metadata for client session validation
SERVER_INSTANCE_ID = str(uuid.uuid4())
SERVER_START_TIME = datetime.utcnow().isoformat()

# Database connection helpers - MySQL only
# Force MySQL database (SQLite support removed)
DB_ENGINE = 'mysql'

def get_db_connection():
    """Get MySQL database connection"""
    try:
        import pymysql
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', ''),
            db=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', '3306')),
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )
        return conn
    except Exception as e:
        app.logger.error(f"MySQL connection error: {e}")
        raise

def close_db_connection(conn):
    try:
        if conn:
            conn.close()
    except Exception:
        pass

# Cancel Order Endpoint
@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
@token_required
def api_cancel_order(order_id):
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        db = get_db()
        cursor = db.cursor()
        # Get order info
        cursor.execute('SELECT * FROM orders WHERE id=?', (order_id,))
        order = cursor.fetchone()
        if not order:
            return error_response('Order not found', 404)
        # Only allow owner or admin
        if role != 'admin' and order['customer_id'] != user_id:
            return error_response('Forbidden', 403)
        # Only allow cancellation if order is not delivered or already cancelled
        if order['status'] in ('delivered', 'cancelled'):
            return error_response('Order cannot be cancelled', 400)
        data = request.json or {}
        reason = data.get('reason', 'Customer cancelled')
        cursor.execute('UPDATE orders SET status=?, cancellation_reason=? WHERE id=?', ('cancelled', reason, order_id))
        db.commit()
        return success_response({'order_id': order_id, 'status': 'cancelled', 'reason': reason}, 'Order cancelled')
    except Exception as e:
        return error_response(str(e), 500)
# Get Order Invoice Endpoint
@app.route('/api/orders/<int:order_id>/invoice', methods=['GET'])
@token_required
def api_order_invoice(order_id):
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        db = get_db()
        cursor = db.cursor()
        # Get order info
        cursor.execute('SELECT * FROM orders WHERE id=?', (order_id,))
        order = cursor.fetchone()
        if not order:
            return error_response('Order not found', 404)
        # Only allow owner or admin
        if role != 'admin' and order['customer_id'] != user_id:
            return error_response('Forbidden', 403)
        # Get order items
        cursor.execute('SELECT * FROM order_items WHERE order_id=?', (order_id,))
        items = [dict(row) for row in cursor.fetchall()]
        invoice = {
            'order_id': order_id,
            'customer': {
                'id': order['customer_id'],
                'name': order.get('customer_name'),
                'address': order.get('customer_address'),
                'phone': order.get('customer_phone')
            },
            'items': items,
            'subtotal': order.get('subtotal'),
            'delivery_fee': order.get('delivery_fee'),
            'total': order.get('total'),
            'status': order.get('status'),
            'created_at': order.get('created_at')
        }
        return success_response(invoice, 'Order invoice')
    except Exception as e:
        return error_response(str(e), 500)
# Assign Rider to Order (Admin) Endpoint
@app.route('/api/orders/<int:order_id>/assign-rider', methods=['POST'])
@token_required
def api_assign_rider_admin(order_id):
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        role = payload.get('role')
        if role != 'admin':
            return error_response('Forbidden', 403)
        db = get_db()
        cursor = db.cursor()
        data = request.json or {}
        rider_id = data.get('rider_id')
        if not rider_id:
            return error_response('Missing rider_id', 400)
        # Check order exists
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT * FROM orders WHERE id=%s', (order_id,))
        else:
            cursor.execute('SELECT * FROM orders WHERE id=?', (order_id,))
        order = cursor.fetchone()
        if not order:
            return error_response('Order not found', 404)
        
        if DB_ENGINE == 'mysql':
            cursor.execute('UPDATE orders SET rider_id=%s, status=%s WHERE id=%s', (rider_id, 'dispatched', order_id))
        else:
            cursor.execute('UPDATE orders SET rider_id=?, status=? WHERE id=?', (rider_id, 'dispatched', order_id))
        db.commit()
        cursor.close()
        return success_response({'order_id': order_id, 'rider_id': rider_id, 'status': 'dispatched'}, 'Rider assigned')
    except Exception as e:
        return error_response(str(e), 500)

# Account: fetch current user's profile
@app.route('/api/account/me', methods=['GET'])
@token_required
def api_account_me():
    try:
        token = get_token_from_request()
        payload = verify_token(token)
        if not payload:
            return error_response('Unauthorized', 401)
        user_id = payload.get('user_id')
        role = payload.get('role')

        conn = get_db_connection()
        cur = conn.cursor()

        # Base user
        if DB_ENGINE == 'mysql':
            cur.execute('SELECT * FROM users WHERE id=%s', (user_id,))
        else:
            cur.execute('SELECT * FROM users WHERE id=?', (user_id,))
        user = cur.fetchone() or {}

        profile = dict(user) if isinstance(user, dict) else {}

        # Role-specific additions
        if role == 'seller':
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT * FROM sellers WHERE user_id=%s', (user_id,))
            else:
                cur.execute('SELECT * FROM sellers WHERE user_id=?', (user_id,))
            seller = cur.fetchone() or {}
            profile['seller'] = dict(seller) if isinstance(seller, dict) else {}
        elif role == 'rider':
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT * FROM riders WHERE user_id=%s', (user_id,))
            else:
                cur.execute('SELECT * FROM riders WHERE user_id=?', (user_id,))
            rider = cur.fetchone() or {}
            profile['rider'] = dict(rider) if isinstance(rider, dict) else {}

        close_db_connection(conn)
        # Remove sensitive fields
        for key in ['password_hash', 'otp_code']:
            if key in profile:
                profile.pop(key)
        return success_response(profile)
    except Exception as e:
        app.logger.error(f"/api/account/me failed: {e}")
        return error_response('Failed to fetch account')

# Account: update current user's profile
@app.route('/api/account/me', methods=['PUT'])
@token_required
def api_account_update():
    try:
        token = get_token_from_request()
        payload = verify_token(token)
        if not payload:
            return error_response('Unauthorized', 401)
        user_id = payload.get('user_id')
        role = payload.get('role')
        body = request.get_json(silent=True) or {}
        
        app.logger.info(f"/api/account/me PUT - user_id: {user_id}, role: {role}, body: {body}")
        
        # Validate that we have something to update
        if not body:
            return error_response('No data provided for update', 400)

        user_fields = {
            'first_name','middle_name','last_name','suffix','email','phone','avatar_url','gender','birthdate',
            'address_line1','address_line2','city','province','region','postal_code'
        }
        seller_fields = {
            'business_name','category','region','province','city','shop_status',
            'store_name','store_description','store_logo','store_banner',
            'support_phone','support_email','tax_id','payout_method','bank_account_name','bank_account_number'
        }
        rider_fields = {
            'vehicle_type','driver_license','plate_number','phone','avatar_url',
            'address_line1','city','province','region','status','license_expiry'
        }

        conn = get_db()
        cur = conn.cursor()

        # Initialize variables
        user_updated = False
        rup = {}  # Initialize rider updates dict
        
        # Update users - check which columns exist first
        updates = {k:v for k,v in body.items() if k in user_fields}
        if updates:
            try:
                # Check which columns actually exist in the database
                if DB_ENGINE == 'mysql':
                    cur.execute("SHOW COLUMNS FROM users")
                    columns_result = cur.fetchall()
                    # DictCursor returns dicts, so access by key name
                    existing_cols = {row['Field'] for row in columns_result}
                else:
                    cur.execute("PRAGMA table_info(users)")
                    columns_result = cur.fetchall()
                    # sqlite3.Row supports both index and key access
                    existing_cols = {row[1] if isinstance(row, (tuple, list)) else row['name'] for row in columns_result}
                
                app.logger.info(f"User update requested: {list(updates.keys())}, Existing columns: {list(existing_cols)}")
                
                # Only update columns that exist
                valid_updates = {k: v for k, v in updates.items() if k in existing_cols}
                
                if valid_updates:
                    # Validate email if it's being updated
                    if 'email' in valid_updates:
                        email = valid_updates['email']
                        if email and not validate_email(email):
                            raise ValueError('Invalid email format')
                        # Check if email is already taken by another user
                        if DB_ENGINE == 'mysql':
                            cur.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (email, user_id))
                        else:
                            cur.execute("SELECT id FROM users WHERE email=? AND id!=?", (email, user_id))
                        if cur.fetchone():
                            raise ValueError('Email already in use by another user')
                    
                    cols = []
                    params = []
                    for k,v in valid_updates.items():
                        cols.append(f"{k}=%s" if DB_ENGINE=='mysql' else f"{k}=?")
                        params.append(v)
                    params.append(user_id)
                    sql = f"UPDATE users SET {', '.join(cols)} WHERE id={'%s' if DB_ENGINE=='mysql' else '?'}"
                    try:
                        cur.execute(sql, params)
                        # Check if update actually affected any rows
                        if cur.rowcount == 0:
                            app.logger.warning(f"User update affected 0 rows for user_id {user_id} - user may not exist")
                        else:
                            app.logger.info(f"User update successful for user_id {user_id}: {list(valid_updates.keys())}")
                    except Exception as exec_error:
                        app.logger.error(f"Error executing user update: {exec_error}")
                        app.logger.error(f"Exception type: {type(exec_error).__name__}")
                        app.logger.error(f"Exception args: {exec_error.args if hasattr(exec_error, 'args') else 'N/A'}")
                        if hasattr(exec_error, 'msg'):
                            app.logger.error(f"Exception msg: {exec_error.msg}")
                        app.logger.error(f"SQL: {sql}")
                        app.logger.error(f"Params: {params}")
                        raise
                    user_updated = True
                else:
                    # No valid columns to update, but that's okay - just log it
                    app.logger.info(f"No valid columns to update for user {user_id}. Requested: {list(updates.keys())}, Existing: {list(existing_cols)}")
            except Exception as e:
                app.logger.error(f"Error updating user: {e}")
                import traceback
                app.logger.error(traceback.format_exc())
                raise

        # Role specific
        if role == 'seller':
            sup = {k:v for k,v in body.items() if k in seller_fields}
            if sup:
                try:
                    # Check which columns exist in sellers table
                    if DB_ENGINE == 'mysql':
                        cur.execute("SHOW COLUMNS FROM sellers")
                        columns_result = cur.fetchall()
                        # DictCursor returns dicts, so access by key name
                        existing_cols = {row['Field'] for row in columns_result}
                    else:
                        cur.execute("PRAGMA table_info(sellers)")
                        columns_result = cur.fetchall()
                        # sqlite3.Row supports both index and key access
                        existing_cols = {row[1] if isinstance(row, (tuple, list)) else row['name'] for row in columns_result}
                    
                    valid_updates = {k: v for k, v in sup.items() if k in existing_cols}
                    if valid_updates:
                        cols = []
                        params = []
                        for k,v in valid_updates.items():
                            cols.append(f"{k}=%s" if DB_ENGINE=='mysql' else f"{k}=?")
                            params.append(v)
                        params.append(user_id)
                        sql = f"UPDATE sellers SET {', '.join(cols)} WHERE user_id={'%s' if DB_ENGINE=='mysql' else '?'}"
                        cur.execute(sql, params)
                    else:
                        app.logger.info(f"No valid columns to update for seller {user_id}. Requested: {list(sup.keys())}, Existing: {list(existing_cols)}")
                except Exception as seller_update_error:
                    app.logger.error(f"Error updating seller fields: {seller_update_error}")
                    import traceback
                    app.logger.error(traceback.format_exc())
                    raise
        elif role == 'rider':
            # For riders, phone can be in both user_fields and rider_fields
            # Remove phone from rider_fields if it's being updated in user_fields
            rup = {k:v for k,v in body.items() if k in rider_fields and k != 'phone'}
            if rup:
                try:
                    # Check which columns exist in riders table
                    if DB_ENGINE == 'mysql':
                        cur.execute("SHOW COLUMNS FROM riders")
                        columns_result = cur.fetchall()
                        # DictCursor returns dicts, so access by key name
                        existing_cols = {row['Field'] for row in columns_result}
                    else:
                        cur.execute("PRAGMA table_info(riders)")
                        columns_result = cur.fetchall()
                        # sqlite3.Row supports both index and key access
                        existing_cols = {row[1] if isinstance(row, (tuple, list)) else row['name'] for row in columns_result}
                    
                    app.logger.debug(f"Rider update requested: {list(rup.keys())}, Existing columns: {list(existing_cols)}")
                    
                    valid_updates = {k: v for k, v in rup.items() if k in existing_cols}
                    if valid_updates:
                        # Check if rider record exists
                        if DB_ENGINE == 'mysql':
                            cur.execute("SELECT id FROM riders WHERE user_id=%s", (user_id,))
                        else:
                            cur.execute("SELECT id FROM riders WHERE user_id=?", (user_id,))
                        rider_exists = cur.fetchone() is not None
                        
                        if rider_exists:
                            # Update existing rider record
                            cols = []
                            params = []
                            for k,v in valid_updates.items():
                                cols.append(f"{k}=%s" if DB_ENGINE=='mysql' else f"{k}=?")
                                params.append(v)
                            params.append(user_id)
                            sql = f"UPDATE riders SET {', '.join(cols)} WHERE user_id={'%s' if DB_ENGINE=='mysql' else '?'}"
                            cur.execute(sql, params)
                            app.logger.info(f"Updated rider record for user_id {user_id}: {list(valid_updates.keys())}")
                        else:
                            # Create new rider record
                            # Include required/default fields if they exist in the table
                            cols = ['user_id'] + list(valid_updates.keys())
                            values = [user_id] + list(valid_updates.values())
                            
                            # Add default values for required fields if they don't exist
                            if 'verified' in existing_cols and 'verified' not in valid_updates:
                                cols.append('verified')
                                values.append(0)
                            if 'status' in existing_cols and 'status' not in valid_updates:
                                cols.append('status')
                                values.append('active')
                            elif 'rider_status' in existing_cols and 'rider_status' not in valid_updates:
                                cols.append('rider_status')
                                values.append('pending')
                            
                            placeholders = ['%s' if DB_ENGINE=='mysql' else '?' for _ in cols]
                            sql = f"INSERT INTO riders ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                            try:
                                cur.execute(sql, values)
                                app.logger.info(f"Created rider record for user_id {user_id}: {list(valid_updates.keys())}")
                            except Exception as insert_err:
                                app.logger.error(f"Failed to insert rider record: {insert_err}")
                                app.logger.error(f"SQL: {sql}")
                                app.logger.error(f"Values: {values}")
                                raise
                    else:
                        app.logger.info(f"No valid columns to update for rider {user_id}. Requested: {list(rup.keys())}, Existing: {list(existing_cols)}")
                except Exception as rider_update_error:
                    app.logger.error(f"Error updating rider fields: {rider_update_error}")
                    app.logger.error(f"Exception type: {type(rider_update_error).__name__}")
                    app.logger.error(f"Exception args: {rider_update_error.args if hasattr(rider_update_error, 'args') else 'N/A'}")
                    if hasattr(rider_update_error, 'msg'):
                        app.logger.error(f"Exception msg: {rider_update_error.msg}")
                    import traceback
                    app.logger.error(traceback.format_exc())
                    # Re-raise to return error to client
                    raise
            else:
                # No rider fields to update - that's okay if we updated user fields
                app.logger.debug(f"No rider fields to update for user_id {user_id}")

        # Check if we actually updated anything
        if not user_updated and role == 'rider' and len(rup) == 0:
            app.logger.warning(f"No fields to update for user_id {user_id}, role: {role}, body: {body}")
            # This is not necessarily an error - maybe they only sent fields that don't exist
            # But we should still return success if the request was valid
            if 'cur' in locals():
                cur.close()
            return success_response({'updated': False, 'message': 'No valid fields to update'}, 'No updates needed')

        conn.commit()
        app.logger.info(f"Account update successful for user_id {user_id}, role: {role}")
        if 'cur' in locals():
            cur.close()
        return success_response({'updated': True}, 'Account updated')
    except Exception as e:
        app.logger.error(f"/api/account/me PUT failed: {e}")
        app.logger.error(f"Exception type: {type(e).__name__}")
        app.logger.error(f"Exception args: {e.args if hasattr(e, 'args') else 'N/A'}")
        if hasattr(e, 'msg'):
            app.logger.error(f"Exception msg: {e.msg}")
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(error_trace)
        try:
            if 'conn' in locals():
                conn.rollback()
            if 'cur' in locals():
                cur.close()
        except Exception as cleanup_err:
            app.logger.error(f"Cleanup failed: {cleanup_err}")
        # Get proper error message - handle different exception types
        error_msg = None
        try:
            # First, try to get error message from exception
            # For pymysql errors, get the actual error message
            # pymysql errors have format: (error_code, error_message)
            if hasattr(e, 'args') and e.args:
                # Try to get error message (usually second arg for pymysql)
                if len(e.args) >= 2:
                    # Second arg is usually the error message
                    msg = e.args[1]
                    if msg:
                        error_msg = str(msg)
                    elif e.args[0]:
                        # If no message, use error code with description
                        error_code = e.args[0]
                        error_msg = f"MySQL error {error_code}"
                elif len(e.args) == 1:
                    # Only one arg - use it if it's meaningful
                    arg_str = str(e.args[0])
                    if arg_str and arg_str != '0':
                        error_msg = arg_str
            
            # If we don't have an error message yet, try other attributes
            if not error_msg:
                if hasattr(e, 'msg') and e.msg:
                    error_msg = str(e.msg)
                elif hasattr(e, 'message'):
                    error_msg = str(e.message)
                else:
                    error_str = str(e)
                    if error_str and error_str != '0':
                        error_msg = error_str
            
            # If we still don't have a message, use exception type
            if not error_msg or error_msg == '0':
                error_msg = f"Database error: {type(e).__name__}"
        except Exception as err_parse_err:
            error_msg = f"Error type: {type(e).__name__} (failed to parse: {err_parse_err})"
        
        # Log full exception details for debugging
        app.logger.error(f"Final error message: {error_msg}")
        app.logger.error(f"Exception type: {type(e).__name__}")
        app.logger.error(f"Exception args: {e.args if hasattr(e, 'args') else 'N/A'}")
        if hasattr(e, 'msg'):
            app.logger.error(f"Exception msg: {e.msg}")
        if hasattr(e, '__dict__'):
            app.logger.error(f"Exception dict: {e.__dict__}")
        
        # Return a more user-friendly error message
        return error_response(f'Failed to update account: {error_msg}', 400)
# Update Order (Customer Notes) Endpoint
@app.route('/api/orders/<int:order_id>', methods=['PUT'])
@token_required
def api_update_order(order_id):
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        db = get_db()
        cursor = db.cursor()
        # Get order info
        cursor.execute('SELECT * FROM orders WHERE id=?', (order_id,))
        order = cursor.fetchone()
        if not order:
            return error_response('Order not found', 404)
        # Only allow owner or admin
        if role != 'admin' and order['customer_id'] != user_id:
            return error_response('Forbidden', 403)
        data = request.json or {}
        notes = data.get('customer_notes')
        if not notes:
            return error_response('No notes provided', 400)
        cursor.execute('UPDATE orders SET customer_notes=? WHERE id=?', (notes, order_id))
        db.commit()
        return success_response({'order_id': order_id, 'customer_notes': notes}, 'Order updated')
    except Exception as e:
        return error_response(str(e), 500)
# Order Tracking Endpoint
@app.route('/api/orders/<int:order_id>/track', methods=['GET'])
@token_required
def api_order_track(order_id):
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        db = get_db()
        cursor = db.cursor()
        # Get order info
        cursor.execute('SELECT * FROM orders WHERE id=?', (order_id,))
        order = cursor.fetchone()
        if not order:
            return error_response('Order not found', 404)
        # Only allow owner, assigned rider, or admin
        if role != 'admin' and order['customer_id'] != user_id and (order.get('rider_id') != user_id if 'rider_id' in order else False):
            return error_response('Forbidden', 403)
        # Get tracking updates if available
        tracking_updates = []
        if 'tracking_updates' in order and order['tracking_updates']:
            import json
            try:
                tracking_updates = json.loads(order['tracking_updates'])
            except Exception:
                tracking_updates = []
        result = {
            'order_id': order_id,
            'status': order['status'],
            'created_at': order['created_at'],
            'tracking_updates': tracking_updates
        }
        return success_response(result, 'Order tracking info')
    except Exception as e:
        return error_response(str(e), 500)
# Admin: Suspend Seller
@app.route('/api/sellers/<int:seller_id>/suspend', methods=['POST'])
@role_required('admin')
def api_admin_suspend_seller(seller_id):
    try:
        db = get_db()
        cursor = db.cursor()
        # Try to set suspended=1, if column does not exist, ignore error
        try:
            cursor.execute('UPDATE sellers SET suspended=1 WHERE id=?', (seller_id,))
        except Exception as e:
            # If column does not exist, add it (SQLite only)
            if 'no such column: suspended' in str(e):
                cursor.execute('ALTER TABLE sellers ADD COLUMN suspended INTEGER DEFAULT 0')
                db.commit()
                cursor.execute('UPDATE sellers SET suspended=1 WHERE id=?', (seller_id,))
            else:
                raise
        db.commit()
        return success_response({'seller_id': seller_id}, 'Seller suspended')
    except Exception as e:
        return error_response(str(e), 500)
# Admin: Verify Seller
@app.route('/api/sellers/<int:seller_id>/verify', methods=['POST'])
@role_required('admin')
def api_admin_verify_seller_new(seller_id):
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get seller info before update
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT user_id, business_name FROM sellers WHERE id=%s', (seller_id,))
        else:
            cursor.execute('SELECT user_id, business_name FROM sellers WHERE id=?', (seller_id,))
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller not found', 404)
        
        # Update seller: verify and activate shop
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'UPDATE sellers SET verified=1, shop_status=%s, approved_at=NOW() WHERE id=%s',
                ('active', seller_id)
            )
        else:
            cursor.execute(
                'UPDATE sellers SET verified=1, shop_status=?, approved_at=? WHERE id=?',
                ('active', datetime.utcnow().isoformat(), seller_id)
            )
        
        db.commit()
        
        # Get user email for notification
        user_id = seller['user_id'] if isinstance(seller, dict) else seller[0]
        business_name = seller['business_name'] if isinstance(seller, dict) else seller[1]
        
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT email, first_name FROM users WHERE id=%s', (user_id,))
        else:
            cursor.execute('SELECT email, first_name FROM users WHERE id=?', (user_id,))
        user = cursor.fetchone()
        
        # Send approval notification email
        if user:
            try:
                from backend.email_service import send_email
                email = user['email'] if isinstance(user, dict) else user[0]
                first_name = user['first_name'] if isinstance(user, dict) else user[1]
                
                subject = "🎉 Your Seller Account Has Been Approved!"
                body = f"""Dear {first_name},

Congratulations! Your seller account for "{business_name}" has been approved by our admin team.

✅ Your shop is now ACTIVE
✅ You can start adding products immediately
✅ Your products will appear in the marketplace

Next Steps:
1. Login to your seller dashboard
2. Add your first products
3. Start receiving orders

Thank you for joining Hub E-Commerce!

Best regards,
Hub Team
"""
                send_email(email, subject, body)
            except Exception as email_error:
                # Don't fail the approval if email fails
                print(f"Email notification failed: {email_error}")
        
        return success_response({
            'seller_id': seller_id,
            'shop_status': 'active',
            'verified': True,
            'message': 'Seller verified and shop activated'
        }, 'Seller approved successfully')
    except Exception as e:
        return error_response(str(e), 500)
# Admin: List All Sellers
@app.route('/api/sellers', methods=['GET'])
@role_required('admin')
def api_admin_list_sellers():
    try:
        db = get_db()
        cursor = db.cursor()
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT s.id as seller_id, u.id as user_id, u.email, u.first_name, u.last_name, 
                       s.business_name, s.category, s.verified, s.shop_status, s.approved_at,
                       s.suspended, u.created_at
                FROM sellers s
                INNER JOIN users u ON s.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT s.id as seller_id, u.id as user_id, u.email, u.first_name, u.last_name, 
                       s.business_name, s.category, s.verified, s.shop_status, s.approved_at,
                       s.suspended, u.created_at
                FROM sellers s
                INNER JOIN users u ON s.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        sellers = [dict(zip(['seller_id','user_id','email','first_name','last_name','business_name','category','verified','shop_status','approved_at','suspended','created_at'], row)) for row in cursor.fetchall()]
        return success_response(sellers, 'Sellers fetched')
    except Exception as e:
        return error_response(str(e), 500)
# Seller Analytics Endpoint
@app.route('/api/sellers/<int:seller_id>/analytics', methods=['GET'])
@token_required
def api_seller_analytics(seller_id):
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        # Only allow seller to view their own analytics or admin
        if payload.get('role') != 'seller' and payload.get('role') != 'admin':
            return error_response('Forbidden', 403)
        db = get_db()
        cursor = db.cursor()
        # Get seller info
        cursor.execute('SELECT * FROM sellers WHERE id=?', (seller_id,))
        seller = cursor.fetchone()
        if not seller:
            return error_response('Seller not found', 404)
        # Get analytics: total orders, total revenue, recent orders
        if DB_ENGINE == 'mysql':
            cursor.execute('''SELECT COUNT(*) as total_orders, COALESCE(SUM(o.total), 0) as total_revenue FROM order_items oi JOIN orders o ON oi.order_id = o.id JOIN products p ON oi.product_id = p.id WHERE p.seller_id=%s''', (seller_id,))
        else:
            cursor.execute('''SELECT COUNT(*) as total_orders, COALESCE(SUM(o.total), 0) as total_revenue FROM order_items oi JOIN orders o ON oi.order_id = o.id JOIN products p ON oi.product_id = p.id WHERE p.seller_id=?''', (seller_id,))
        row = cursor.fetchone()
        total_orders = row[0] if row else 0
        total_revenue = float(row[1] if row else 0)
        # Recent orders (last 5)
        if DB_ENGINE == 'mysql':
            cursor.execute('''SELECT o.id, o.total, o.status, o.created_at FROM order_items oi JOIN orders o ON oi.order_id = o.id JOIN products p ON oi.product_id = p.id WHERE p.seller_id=%s ORDER BY o.created_at DESC LIMIT 5''', (seller_id,))
        else:
            cursor.execute('''SELECT o.id, o.total, o.status, o.created_at FROM order_items oi JOIN orders o ON oi.order_id = o.id JOIN products p ON oi.product_id = p.id WHERE p.seller_id=? ORDER BY o.created_at DESC LIMIT 5''', (seller_id,))
        recent_orders = [dict(zip(['id','total','status','created_at'], r)) for r in cursor.fetchall()]
        return success_response({
            'total_orders': total_orders,
            'total_revenue': round(total_revenue, 2),
            'recent_orders': recent_orders
        }, 'Seller analytics fetched')
    except Exception as e:
        return error_response(str(e), 500)
# Seller Profile Endpoints
@app.route('/api/sellers/<int:seller_id>', methods=['GET'])
def api_get_seller_profile(seller_id):
    """Get seller profile - Public endpoint for viewing seller shops"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get seller info
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT * FROM sellers WHERE id=%s', (seller_id,))
        else:
            cursor.execute('SELECT * FROM sellers WHERE id=?', (seller_id,))
        
        seller = cursor.fetchone()
        if not seller:
            return error_response('Seller not found', 404)
        
        # Get user info for email
        user_id = seller['user_id'] if isinstance(seller, dict) else seller[1]
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT email, first_name, last_name FROM users WHERE id=%s', (user_id,))
        else:
            cursor.execute('SELECT email, first_name, last_name FROM users WHERE id=?', (user_id,))
        
        user = cursor.fetchone()
        
        result = dict(seller) if isinstance(seller, dict) else {
            'id': seller[0],
            'user_id': seller[1],
            'business_name': seller[2],
            'category': seller[3],
            'verified': seller[7] if len(seller) > 7 else 0,
            'shop_status': seller[8] if len(seller) > 8 else 'pending',
            'approved_at': seller[9] if len(seller) > 9 else None
        }
        
        # Add store branding fields if they exist
        if isinstance(seller, dict):
            if 'store_name' in seller:
                result['store_name'] = seller['store_name']
            if 'store_description' in seller:
                result['store_description'] = seller['store_description']
            if 'store_logo' in seller:
                result['store_logo'] = seller['store_logo']
            if 'store_banner' in seller:
                result['store_banner'] = seller['store_banner']
        if user:
            if isinstance(user, dict):
                result['email'] = user['email']
                result['first_name'] = user['first_name']
                result['last_name'] = user['last_name']
            else:
                result['email'] = user[1]
                result['first_name'] = user[3]
                result['last_name'] = user[4]
        return success_response(result, 'Seller profile fetched')
    except Exception as e:
        return error_response(str(e), 500)


# Current user profile endpoints
@app.route('/api/me', methods=['GET'])
@token_required
def api_get_current_user():
    cursor = None
    try:
        user_id = g.user_id
        db = get_db()
        cursor = db.cursor()

        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))
        else:
            cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))

        user = cursor.fetchone()
        if not user:
            if cursor:
                cursor.close()
            return error_response('User not found', 404)

        result = format_row(user)
        app.logger.debug(f'/api/me - user avatar_url: {result.get("avatar_url")}')

        # Attach role-specific info
        role = getattr(g, 'role', result.get('role') if isinstance(result, dict) else None)
        try:
            if role == 'seller':
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT * FROM sellers WHERE user_id=%s', (user_id,))
                else:
                    cursor.execute('SELECT * FROM sellers WHERE user_id=?', (user_id,))
                seller = cursor.fetchone()
                result['seller'] = format_row(seller) if seller else None
            elif role == 'rider':
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT * FROM riders WHERE user_id=%s', (user_id,))
                else:
                    cursor.execute('SELECT * FROM riders WHERE user_id=?', (user_id,))
                rider = cursor.fetchone()
                result['rider'] = format_row(rider) if rider else None
                app.logger.debug(f'/api/me - rider avatar_url: {result.get("rider", {}).get("avatar_url") if result.get("rider") else None}')
        except Exception as role_error:
            # Non-fatal: continue without role-specific details
            app.logger.warning(f'Error fetching role-specific info for user {user_id}: {role_error}')

        if cursor:
            cursor.close()
        return success_response(result, 'Current user profile')
    except Exception as e:
        app.logger.error(f"Error in api_get_current_user: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        if cursor:
            try:
                cursor.close()
            except:
                pass
        return error_response(str(e), 500)


@app.route('/api/me', methods=['PUT'])
@token_required
def api_update_current_user():
    try:
        body = request.get_json() or {}
        allowed = ['first_name', 'middle_name', 'last_name', 'suffix', 'email', 'phone', 
                   'address_line1', 'address_line2', 'city', 'province', 'region', 'postal_code']
        updates = {k: body[k] for k in allowed if k in body}
        if not updates:
            return error_response('No updatable fields provided', 400)

        user_id = g.user_id
        db = get_db()
        cursor = db.cursor()

        # Check which columns actually exist in the database
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM users")
                columns_result = cursor.fetchall()
                existing_cols = {row['Field'] for row in columns_result}
            else:
                cursor.execute("PRAGMA table_info(users)")
                columns_result = cursor.fetchall()
                existing_cols = {row[1] if isinstance(row, (tuple, list)) else row['name'] for row in columns_result}
            
            # Auto-add missing columns for user profile fields (both SQLite and MySQL)
            columns_to_add = {
                'middle_name': 'VARCHAR(255)' if DB_ENGINE == 'mysql' else 'TEXT',
                'suffix': 'VARCHAR(50)' if DB_ENGINE == 'mysql' else 'TEXT',
                'phone': 'VARCHAR(50)' if DB_ENGINE == 'mysql' else 'TEXT',
                'address_line1': 'VARCHAR(255)' if DB_ENGINE == 'mysql' else 'TEXT',
                'address_line2': 'VARCHAR(255)' if DB_ENGINE == 'mysql' else 'TEXT',
                'city': 'VARCHAR(100)' if DB_ENGINE == 'mysql' else 'TEXT',
                'province': 'VARCHAR(100)' if DB_ENGINE == 'mysql' else 'TEXT',
                'region': 'VARCHAR(100)' if DB_ENGINE == 'mysql' else 'TEXT',
                'postal_code': 'VARCHAR(20)' if DB_ENGINE == 'mysql' else 'TEXT',
            }
            
            for col_name, col_type in columns_to_add.items():
                if col_name not in existing_cols and col_name in updates:
                    try:
                        if DB_ENGINE == 'mysql':
                            # MySQL: Use IF NOT EXISTS equivalent by checking first, or use ALTER TABLE with error handling
                            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                        else:
                            # SQLite: ALTER TABLE ADD COLUMN
                            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                        app.logger.info(f"✅ Auto-added missing column: {col_name} ({col_type})")
                        existing_cols.add(col_name)
                    except Exception as add_error:
                        # Column might already exist or there's another issue
                        error_msg = str(add_error).lower()
                        if 'duplicate column' in error_msg or 'already exists' in error_msg:
                            app.logger.info(f"Column {col_name} already exists, skipping")
                            existing_cols.add(col_name)
                        else:
                            app.logger.warning(f"Could not add column {col_name}: {add_error}")
            
            # Only update columns that exist
            valid_updates = {k: v for k, v in updates.items() if k in existing_cols}
            
            # Log what columns exist and what we're trying to update
            app.logger.info(f"User {user_id} update request - Requested fields: {list(updates.keys())}")
            app.logger.info(f"User {user_id} update request - Existing columns: {list(existing_cols)}")
            app.logger.info(f"User {user_id} update request - Valid updates: {list(valid_updates.keys())}")
            
            if not valid_updates:
                app.logger.error(f"❌ No valid columns to update for user_id {user_id}!")
                app.logger.error(f"Requested fields: {list(updates.keys())}")
                app.logger.error(f"Existing columns: {list(existing_cols)}")
                app.logger.error(f"Missing columns: {set(updates.keys()) - existing_cols}")
                # Still return success but log the issue
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))
                else:
                    cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
                user = cursor.fetchone()
                return error_response(f'No valid columns to update. Requested: {list(updates.keys())}, Existing: {list(existing_cols)}', 400)
            
            # Validate email if it's being updated
            if 'email' in valid_updates:
                email = valid_updates['email']
                if email and not validate_email(email):
                    return error_response('Invalid email format', 400)
                # Check if email is already taken by another user
                if DB_ENGINE == 'mysql':
                    cursor.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (email, user_id))
                else:
                    cursor.execute("SELECT id FROM users WHERE email=? AND id!=?", (email, user_id))
                if cursor.fetchone():
                    return error_response('Email already in use by another user', 400)
            
            # Build and execute update query
            app.logger.info(f"✅ Updating user {user_id} with fields: {list(valid_updates.keys())}")
            app.logger.info(f"Update values: {valid_updates}")
            
            if DB_ENGINE == 'mysql':
                set_clause = ', '.join(f"{k}=%s" for k in valid_updates.keys())
                params = list(valid_updates.values()) + [user_id]
                update_query = f'UPDATE users SET {set_clause} WHERE id=%s'
            else:
                set_clause = ', '.join(f"{k}=?" for k in valid_updates.keys())
                params = list(valid_updates.values()) + [user_id]
                update_query = f'UPDATE users SET {set_clause} WHERE id=?'
            
            app.logger.info(f"Executing SQL: {update_query}")
            app.logger.info(f"With parameters: {params}")
            
            try:
                cursor.execute(update_query, params)
                rows_affected = cursor.rowcount
                app.logger.info(f"✅ UPDATE executed. Rows affected: {rows_affected}")
                
                if rows_affected == 0:
                    app.logger.warning(f"⚠️ No rows were updated! User {user_id} may not exist.")
                
                # Commit the transaction
                db.commit()
                app.logger.info(f"✅ Transaction committed successfully for user {user_id}")
            except Exception as execute_error:
                app.logger.error(f"❌ Error executing UPDATE query: {execute_error}")
                import traceback
                app.logger.error(traceback.format_exc())
                db.rollback()
                raise
            
        except Exception as db_error:
            app.logger.error(f"Database error in api_update_current_user: {db_error}")
            import traceback
            app.logger.error(traceback.format_exc())
            db.rollback()
            raise

        # Return updated profile - fetch fresh from database to confirm save
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))
            else:
                cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                app.logger.error(f"User {user_id} not found after update!")
                cursor.close()
                return error_response('User not found after update', 500)
            
            user_dict = format_row(user)
            
            # Log the returned data for debugging - show ALL fields
            app.logger.info(f"Returning updated user data for user {user_id}")
            app.logger.info(f"✅ Updated user data fields: {list(user_dict.keys())}")
            app.logger.info(f"Updated user data values: first_name={user_dict.get('first_name')}, "
                           f"middle_name={user_dict.get('middle_name')}, "
                           f"last_name={user_dict.get('last_name')}, "
                           f"suffix={user_dict.get('suffix')}, "
                           f"phone={user_dict.get('phone')}, email={user_dict.get('email')}, "
                           f"address_line1={user_dict.get('address_line1')}, "
                           f"address_line2={user_dict.get('address_line2')}, "
                           f"province={user_dict.get('province')}, "
                           f"city={user_dict.get('city')}, "
                           f"region={user_dict.get('region')}, "
                           f"postal_code={user_dict.get('postal_code')}")
            
            cursor.close()
            return success_response(user_dict, 'Profile updated')
        except Exception as fetch_error:
            app.logger.error(f"Error fetching updated user: {fetch_error}")
            import traceback
            app.logger.error(traceback.format_exc())
            if cursor:
                cursor.close()
            return error_response('Profile updated but failed to fetch updated data', 500)
    except Exception as e:
        app.logger.error(f"Error in api_update_current_user: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

# Get Active Sellers (Public endpoint for shop.html)
# This endpoint returns both main seller profiles AND approved stores
@app.route('/api/sellers/active', methods=['GET'])
def api_get_active_sellers():
    """Get all active sellers for public shop listing page"""
    try:
        db = get_db()
        cursor = db.cursor()
        result = []
        
        # First, get all active main seller profiles
        try:
            # Check if store_* columns exist in sellers table
            store_columns_exist = False
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute("SHOW COLUMNS FROM sellers LIKE 'store_name'")
                    store_columns_exist = cursor.fetchone() is not None
                else:
                    cursor.execute("PRAGMA table_info(sellers)")
                    columns = cursor.fetchall()
                    store_columns_exist = any(col[1] == 'store_name' for col in columns)
            except Exception:
                pass
            
            # Check if store_id column exists in products table
            products_store_id_exists = False
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                    products_store_id_exists = cursor.fetchone() is not None
                else:
                    cursor.execute("PRAGMA table_info(products)")
                    columns = cursor.fetchall()
                    products_store_id_exists = any(col[1] == 'store_id' for col in columns)
            except Exception:
                pass
            
            # Build product filter for LEFT JOIN
            if products_store_id_exists:
                product_join_condition = 'p.seller_id = s.user_id AND (p.store_id IS NULL OR p.store_id = 0)'
                product_count_expr = 'COUNT(DISTINCT CASE WHEN p.store_id IS NULL OR p.store_id = 0 THEN p.id END)'
            else:
                product_join_condition = 'p.seller_id = s.user_id'
                product_count_expr = 'COUNT(DISTINCT p.id)'
            
            if store_columns_exist:
                # Query with store_* columns
                if DB_ENGINE == 'mysql':
                    cursor.execute(f'''
                        SELECT 
                            s.id as seller_id,
                            s.user_id,
                            s.business_name,
                            s.store_name,
                            s.store_logo,
                            s.store_banner,
                            s.category,
                            s.region,
                            s.province,
                            s.city,
                            s.approved_at,
                            u.email,
                            u.first_name,
                            u.last_name,
                            {product_count_expr} as total_products,
                            NULL as store_id,
                            'seller' as shop_type
                        FROM sellers s
                        INNER JOIN users u ON s.user_id = u.id
                        LEFT JOIN products p ON {product_join_condition}
                        WHERE s.shop_status IN ('active', 'warning', 'suspended')
                          AND s.verified = 1
                        GROUP BY s.id, s.user_id, s.business_name, s.store_name, s.store_logo, 
                                 s.store_banner, s.category, s.region, 
                                 s.province, s.city, s.approved_at, u.email, u.first_name, u.last_name
                        ORDER BY s.approved_at DESC
                    ''')
                else:
                    cursor.execute(f'''
                        SELECT 
                            s.id as seller_id,
                            s.user_id,
                            s.business_name,
                            s.store_name,
                            s.store_logo,
                            s.store_banner,
                            s.category,
                            s.region,
                            s.province,
                            s.city,
                            s.approved_at,
                            u.email,
                            u.first_name,
                            u.last_name,
                            {product_count_expr} as total_products,
                            NULL as store_id,
                            'seller' as shop_type
                        FROM sellers s
                        INNER JOIN users u ON s.user_id = u.id
                        LEFT JOIN products p ON {product_join_condition}
                        WHERE s.shop_status IN ('active', 'warning', 'suspended')
                          AND s.verified = 1
                        GROUP BY s.id
                        ORDER BY s.approved_at DESC
                    ''')
            else:
                # Query without store_* columns (fallback)
                if DB_ENGINE == 'mysql':
                    cursor.execute(f'''
                        SELECT 
                            s.id as seller_id,
                            s.user_id,
                            s.business_name,
                            NULL as store_name,
                            NULL as store_logo,
                            NULL as store_banner,
                            s.category,
                            s.region,
                            s.province,
                            s.city,
                            s.approved_at,
                            u.email,
                            u.first_name,
                            u.last_name,
                            {product_count_expr} as total_products,
                            NULL as store_id,
                            'seller' as shop_type
                        FROM sellers s
                        INNER JOIN users u ON s.user_id = u.id
                        LEFT JOIN products p ON {product_join_condition}
                        WHERE s.shop_status IN ('active', 'warning', 'suspended')
                          AND s.verified = 1
                        GROUP BY s.id, s.user_id, s.business_name, s.category, s.region, 
                                 s.province, s.city, s.approved_at, u.email, u.first_name, u.last_name
                        ORDER BY s.approved_at DESC
                    ''')
                else:
                    cursor.execute(f'''
                        SELECT 
                            s.id as seller_id,
                            s.user_id,
                            s.business_name,
                            NULL as store_name,
                            NULL as store_logo,
                            NULL as store_banner,
                            s.category,
                            s.region,
                            s.province,
                            s.city,
                            s.approved_at,
                            u.email,
                            u.first_name,
                            u.last_name,
                            {product_count_expr} as total_products,
                            NULL as store_id,
                            'seller' as shop_type
                        FROM sellers s
                        INNER JOIN users u ON s.user_id = u.id
                        LEFT JOIN products p ON {product_join_condition}
                        WHERE s.shop_status IN ('active', 'warning', 'suspended')
                          AND s.verified = 1
                        GROUP BY s.id
                        ORDER BY s.approved_at DESC
                    ''')
            
            sellers = cursor.fetchall()
            app.logger.info(f'Found {len(sellers)} active sellers')
            
            # Format main seller profiles
            for row in sellers:
                if isinstance(row, dict):
                    seller_dict = row
                else:
                    seller_dict = dict(zip([
                        'seller_id', 'user_id', 'business_name', 'store_name', 'store_logo',
                        'store_banner', 'category', 'region', 'province', 'city', 'approved_at',
                        'email', 'first_name', 'last_name', 'total_products', 'store_id', 'shop_type'
                    ], row))
                
                seller_dict['display_name'] = seller_dict.get('store_name') or seller_dict.get('business_name') or 'Unnamed Store'
                address_parts = []
                if seller_dict.get('city'): address_parts.append(seller_dict['city'])
                if seller_dict.get('province'): address_parts.append(seller_dict['province'])
                if seller_dict.get('region'): address_parts.append(seller_dict['region'])
                seller_dict['full_address'] = ', '.join(address_parts) if address_parts else 'No address provided'
                seller_dict['owner_name'] = f"{seller_dict.get('first_name', '')} {seller_dict.get('last_name', '')}".strip()
                result.append(seller_dict)
        except Exception as e:
            app.logger.error(f'Error fetching main sellers: {e}', exc_info=True)
        
        # Multi-store functionality removed - only return main seller profiles
        cursor.close()
        
        app.logger.info(f'Total active sellers found: {len(result)}')
        return success_response(result, f'{len(result)} active sellers found')
        
    except Exception as e:
        app.logger.error(f'Error fetching active sellers/stores: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

# Get Best Selling Products
@app.route('/api/products/best-sellers', methods=['GET'])
def api_get_best_sellers():
    """Get top selling products based on completed orders"""
    try:
        # Get query parameters (use safe helper)
        limit = get_query_param('limit', default=10, cast=int)
        if not isinstance(limit, int) or limit <= 0:
            limit = 10
        category = get_query_param('category', default='', cast=str, max_len=100) or ''
        timeframe = get_query_param('timeframe', default='all', cast=str, allowed=['all', 'daily', 'weekly', 'monthly']) or 'all'
        
        db = get_db()
        cursor = db.cursor()
        
        # Build time filter
        time_filter = ""
        if timeframe == 'daily':
            time_filter = "AND o.created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)" if DB_ENGINE == 'mysql' else "AND o.created_at >= datetime('now', '-1 day')"
        elif timeframe == 'weekly':
            time_filter = "AND o.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)" if DB_ENGINE == 'mysql' else "AND o.created_at >= datetime('now', '-7 days')"
        elif timeframe == 'monthly':
            time_filter = "AND o.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)" if DB_ENGINE == 'mysql' else "AND o.created_at >= datetime('now', '-30 days')"
        
        # Build category filter
        category_filter = ""
        category_param = None
        if category:
            if DB_ENGINE == 'mysql':
                category_filter = "AND p.category = %s"
                category_param = category
            else:
                category_filter = "AND p.category = ?"
                category_param = category
        
        # Build query
        if DB_ENGINE == 'mysql':
            query = f'''
                SELECT 
                    p.id,
                    p.title,
                    p.description,
                    p.price,
                    p.img_url,
                    p.category,
                    p.stock,
                    s.business_name as seller_name,
                    s.user_id as seller_id,
                    u.first_name as seller_first_name,
                    u.last_name as seller_last_name,
                    SUM(oi.quantity) as total_sold,
                    COUNT(DISTINCT o.id) as order_count
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                INNER JOIN sellers s ON p.seller_id = s.user_id
                INNER JOIN users u ON s.user_id = u.id
                WHERE o.status IN ('placed', 'confirmed', 'delivered', 'completed')
                  AND s.shop_status = 'active'
                  AND s.verified = 1
                  AND p.stock > 0
                  {time_filter}
                  {category_filter}
                GROUP BY p.id, p.title, p.description, p.price, p.img_url, p.category, 
                         p.stock, s.business_name, s.user_id, u.first_name, u.last_name
                ORDER BY total_sold DESC, order_count DESC
                LIMIT %s
            '''
            params = [category_param, limit] if category_param else [limit]
        else:
            query = f'''
                SELECT 
                    p.id,
                    p.title,
                    p.description,
                    p.price,
                    p.img_url,
                    p.category,
                    p.stock,
                    s.business_name as seller_name,
                    s.user_id as seller_id,
                    u.first_name as seller_first_name,
                    u.last_name as seller_last_name,
                    SUM(oi.quantity) as total_sold,
                    COUNT(DISTINCT o.id) as order_count
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                INNER JOIN sellers s ON p.seller_id = s.user_id
                INNER JOIN users u ON s.user_id = u.id
                WHERE o.status IN ('placed', 'confirmed', 'delivered', 'completed')
                  AND s.shop_status = 'active'
                  AND s.verified = 1
                  AND p.stock > 0
                  {time_filter}
                  {category_filter}
                GROUP BY p.id, p.title, p.description, p.price, p.img_url, p.category, 
                         p.stock, s.business_name, s.user_id, u.first_name, u.last_name
                ORDER BY total_sold DESC, order_count DESC
                LIMIT ?
            '''
            params = [category_param, limit] if category_param else [limit]
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except Exception as qerr:
            # Fallback: if schema doesn't have some joins/columns, degrade gracefully
            app.logger.warning(f"Best-sellers primary query failed, using simplified fallback: {qerr}")
            if DB_ENGINE == 'mysql':
                fallback = f'''
                    SELECT 
                        p.id,
                        p.title,
                        p.description,
                        p.price,
                        p.img_url,
                        p.category,
                        p.stock,
                        COALESCE(s.business_name, 'Unknown Seller') as seller_name,
                        COALESCE(s.user_id, 0) as seller_id,
                        0 as total_sold,
                        0 as order_count
                    FROM products p
                    LEFT JOIN sellers s ON p.seller_id = s.user_id
                    WHERE p.stock > 0
                      {category_filter}
                    ORDER BY COALESCE(p.created_at, p.id) DESC
                    LIMIT %s
                '''
                fparams = [category_param, limit] if category_param else [limit]
                cursor.execute(fallback, fparams)
                rows = cursor.fetchall()
            else:
                fallback = f'''
                    SELECT 
                        p.id,
                        p.title,
                        p.description,
                        p.price,
                        p.img_url,
                        p.category,
                        p.stock,
                        COALESCE(s.business_name, 'Unknown Seller') as seller_name,
                        COALESCE(s.user_id, 0) as seller_id,
                        0 as total_sold,
                        0 as order_count
                    FROM products p
                    LEFT JOIN sellers s ON p.seller_id = s.user_id
                    WHERE p.stock > 0
                      {category_filter}
                    ORDER BY COALESCE(p.created_at, p.id) DESC
                    LIMIT ?
                '''
                fparams = [category_param, limit] if category_param else [limit]
                cursor.execute(fallback, fparams)
                rows = cursor.fetchall()

        # Ensure rows are always a list
        rows = rows or []

        # Normalize row access for dict/tuple
        def get_val(row, key, idx=None, default=None):
            if isinstance(row, dict):
                return row.get(key, default)
            try:
                return row[idx] if idx is not None else default
            except Exception:
                return default

        try:
            # Category normalization map
            category_map = {
                'baking': 'Baking',
                'coffee': 'Coffee & Tea',
                'tea': 'Coffee & Tea',
                'coffee & tea': 'Coffee & Tea',
                'snacks': 'Snacks',
                'specialty': 'Specialty',
                'organic': 'Organic',
                'meal kits': 'Meal Kits',
                'meal kit': 'Meal Kits',
                'mealkits': 'Meal Kits'
            }
            
            result = []
            for r in rows:
                category = get_val(r, 'category', 5, None) or ''
                category_lower = category.lower().strip()
                category_normalized = category_map.get(category_lower, category or 'Other')
                
                product = {
                    'id': get_val(r, 'id', 0),
                    'title': get_val(r, 'title', 1, ''),
                    'description': get_val(r, 'description', 2, ''),
                    'price': get_val(r, 'price', 3, 0),
                    'img_url': get_val(r, 'img_url', 4, None),
                    'category': category,
                    'category_normalized': category_normalized,
                    'stock': get_val(r, 'stock', 6, 0),
                    'seller_name': get_val(r, 'seller_name', 7, 'Unknown Seller'),
                    'seller_id': get_val(r, 'seller_id', 8, None),
                    'total_sold': int(get_val(r, 'total_sold', 9, 0) or 0),
                    'order_count': int(get_val(r, 'order_count', 10, 0) or 0)
                }
                # Add expiry_date and manufacture_date if available (for food products)
                expiry_date = get_val(r, 'expiry_date', None, None)
                manufacture_date = get_val(r, 'manufacture_date', None, None)
                if expiry_date:
                    product['expiry_date'] = expiry_date
                if manufacture_date:
                    product['manufacture_date'] = manufacture_date
                    
                result.append(product)
            return success_response({'products': result, 'count': len(result)})
        except Exception as fmt_err:
            app.logger.error(f"Best-sellers formatting failed: {fmt_err}")
            return success_response({'products': [], 'count': 0})
    except Exception as e:
        app.logger.error(f'Error fetching best sellers: {e}')
        return error_response(str(e), 500)
    finally:
        # Close the cursor if it was created; do not attempt to close the Flask-managed DB connection (`g.db`)
        try:
            if 'cursor' in locals() and cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
        except Exception:
            pass

# Gracefully handle favicon requests to avoid 500 noise
@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory('frontend', 'favicon.ico')
    except Exception:
        return ('', 204)

# Duplicate endpoint removed - using api_get_active_sellers above
        if 'conn' in locals():
            conn.close()

# Customer reviews listing with safe fallbacks
@app.route('/api/customer/reviews', methods=['GET'])
@token_required
def customer_reviews():
    try:
        user_id = request.user_id if hasattr(request, 'user_id') else None
        conn = get_db_connection()
        cursor = conn.cursor()
        if DB_ENGINE == 'mysql':
            query = '''
                SELECT r.id, r.order_id, r.product_id, r.rating, r.comment, r.created_at
                FROM customer_reviews r
                ORDER BY COALESCE(r.created_at, r.id) DESC
                LIMIT 100
            '''
            cursor.execute(query)
        else:
            query = '''
                SELECT r.id, r.order_id, r.product_id, r.rating, r.comment, r.created_at
                FROM customer_reviews r
                ORDER BY COALESCE(r.created_at, r.id) DESC
                LIMIT 100
            '''
            cursor.execute(query)
        rows = cursor.fetchall() or []
        data = []
        for r in rows:
            if isinstance(r, dict):
                data.append(r)
            else:
                data.append({
                    'id': r[0] if len(r) > 0 else None,
                    'order_id': r[1] if len(r) > 1 else None,
                    'product_id': r[2] if len(r) > 2 else None,
                    'rating': r[3] if len(r) > 3 else None,
                    'comment': r[4] if len(r) > 4 else '',
                    'created_at': r[5] if len(r) > 5 else None,
                })
        return success_response({'reviews': data, 'user_id': user_id})
    except Exception as err:
        app.logger.error(f"/api/customer/reviews failed: {err}")
        return success_response({'reviews': []})
    finally:
        if 'conn' in locals():
            conn.close()

# Reviewable products endpoint - returns products from delivered orders that can be reviewed
@app.route('/api/customer/products/reviewable', methods=['GET'])
@token_required
def customer_reviewable_products():
    """Get products from delivered orders that can be reviewed"""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data:
            return error_response('Unauthorized', 401)
        
        user_id = token_data.get('user_id')
        role = token_data.get('role')
        
        if role != 'customer':
            return error_response('Only customers can review products', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get products from delivered/completed orders that haven't been reviewed yet
        if DB_ENGINE == 'mysql':
            query = '''
                SELECT DISTINCT
                    oi.id as order_item_id,
                    oi.order_id,
                    oi.product_id,
                    oi.quantity,
                    oi.price,
                    p.title as product_name,
                    p.img_url as product_image,
                    o.delivered_at,
                    o.created_at as order_date,
                    s.business_name as seller_name,
                    r.id as review_id,
                    r.rating as existing_rating,
                    r.comment as existing_comment
                FROM order_items oi
                INNER JOIN orders o ON oi.order_id = o.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN sellers s ON p.seller_id = s.user_id
                LEFT JOIN reviews r ON r.order_id = o.id AND r.product_id = p.id AND r.customer_id = %s
                WHERE o.customer_id = %s
                  AND o.status IN ('delivered', 'completed')
                  AND o.delivered_at IS NOT NULL
                ORDER BY o.delivered_at DESC, o.id DESC
            '''
            cursor.execute(query, (user_id, user_id))
        else:
            query = '''
                SELECT DISTINCT
                    oi.id as order_item_id,
                    oi.order_id,
                    oi.product_id,
                    oi.quantity,
                    oi.price,
                    p.title as product_name,
                    p.img_url as product_image,
                    o.delivered_at,
                    o.created_at as order_date,
                    s.business_name as seller_name,
                    r.id as review_id,
                    r.rating as existing_rating,
                    r.comment as existing_comment
                FROM order_items oi
                INNER JOIN orders o ON oi.order_id = o.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN sellers s ON p.seller_id = s.user_id
                LEFT JOIN reviews r ON r.order_id = o.id AND r.product_id = p.id AND r.customer_id = ?
                WHERE o.customer_id = ?
                  AND o.status IN ('delivered', 'completed')
                  AND o.delivered_at IS NOT NULL
                ORDER BY o.delivered_at DESC, o.id DESC
            '''
            cursor.execute(query, (user_id, user_id))
        
        rows = cursor.fetchall()
        products = []
        
        for row in rows:
            try:
                product = format_row(row)
                # Check if return/refund request exists (only if table exists)
                try:
                    if DB_ENGINE == 'mysql':
                        cursor.execute('''
                            SELECT id, request_type, status, seller_response, rejection_reason,
                                   pickup_rider_id, pickup_scheduled_at, pickup_completed_at,
                                   item_received_at, refund_processed_at, evidence_images, created_at
                            FROM return_refund_requests
                            WHERE order_id = %s AND order_item_id = %s AND customer_id = %s
                            ORDER BY created_at DESC
                            LIMIT 1
                        ''', (product.get('order_id'), product.get('order_item_id'), user_id))
                    else:
                        cursor.execute('''
                            SELECT id, request_type, status, seller_response, rejection_reason,
                                   pickup_rider_id, pickup_scheduled_at, pickup_completed_at,
                                   item_received_at, refund_processed_at, evidence_images, created_at
                            FROM return_refund_requests
                            WHERE order_id = ? AND order_item_id = ? AND customer_id = ?
                            ORDER BY created_at DESC
                            LIMIT 1
                        ''', (product.get('order_id'), product.get('order_item_id'), user_id))
                    
                    request_row = cursor.fetchone()
                    if request_row:
                        request_data = format_row(request_row)
                        # Parse evidence_images if present
                        evidence_images = []
                        if request_data.get('evidence_images'):
                            try:
                                import json
                                evidence_images = json.loads(request_data['evidence_images'])
                            except:
                                pass
                        
                        product['return_refund_request'] = {
                            'id': request_data.get('id'),
                            'type': request_data.get('request_type'),
                            'status': request_data.get('status'),
                            'seller_response': request_data.get('seller_response', 'pending'),
                            'rejection_reason': request_data.get('rejection_reason'),
                            'pickup_rider_id': request_data.get('pickup_rider_id'),
                            'pickup_scheduled_at': request_data.get('pickup_scheduled_at'),
                            'pickup_completed_at': request_data.get('pickup_completed_at'),
                            'item_received_at': request_data.get('item_received_at'),
                            'refund_processed_at': request_data.get('refund_processed_at'),
                            'created_at': request_data.get('created_at'),
                            'evidence_images': evidence_images
                        }
                except Exception as req_err:
                    # Table might not exist yet, skip return/refund check
                    app.logger.warning(f"Could not check return/refund requests: {req_err}")
                
                products.append(product)
            except Exception as row_err:
                app.logger.warning(f"Error processing product row: {row_err}")
                continue
        
        cursor.close()
        return success_response({'products': products})
        
    except Exception as err:
        app.logger.error(f"/api/customer/products/reviewable failed: {err}")
        import traceback
        app.logger.error(traceback.format_exc())
        if 'cursor' in locals():
            try:
                cursor.close()
            except:
                pass
        return error_response(f'Failed to fetch reviewable products: {str(err)}', 500)

# Get Seller Shop Status
@app.route('/api/sellers/shop-status', methods=['GET'])
@token_required
def api_get_seller_shop_status():
    """Get current seller's shop status"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        if payload.get('role') != 'seller':
            return error_response('Must be a seller', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'SELECT id, verified, shop_status, approved_at, business_name FROM sellers WHERE user_id=%s',
                (user_id,)
            )
        else:
            cursor.execute(
                'SELECT id, verified, shop_status, approved_at, business_name FROM sellers WHERE user_id=?',
                (user_id,)
            )
        
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller profile not found', 404)
        
        result = {
            'seller_id': seller['id'] if isinstance(seller, dict) else seller[0],
            'verified': bool(seller['verified'] if isinstance(seller, dict) else seller[1]),
            'shop_status': seller['shop_status'] if isinstance(seller, dict) else (seller[2] if len(seller) > 2 else 'pending'),
            'approved_at': seller['approved_at'] if isinstance(seller, dict) else (seller[3] if len(seller) > 3 else None),
            'business_name': seller['business_name'] if isinstance(seller, dict) else (seller[4] if len(seller) > 4 else None),
            'can_add_products': False
        }
        
        # Determine if seller can add products
        result['can_add_products'] = result['verified'] and result['shop_status'] == 'active'
        
        # Add helpful messages
        if not result['verified']:
            result['message'] = 'Your seller account is pending admin approval.'
        elif result['shop_status'] == 'suspended':
            result['message'] = 'Your shop has been suspended. Please contact admin.'
        elif result['shop_status'] == 'active':
            result['message'] = 'Your shop is active! You can add products now.'
        else:
            result['message'] = 'Your shop is pending activation.'
        
        return success_response(result, 'Shop status retrieved')
    except Exception as e:
        return error_response(str(e), 500)


# Admin: Suspend Seller Shop
@app.route('/api/sellers/<int:seller_id>/suspend-shop', methods=['POST'])
@role_required('admin')
def api_admin_suspend_seller_shop(seller_id):
    """Admin suspends a seller's shop"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        data = request.json or {}
        reason = data.get('reason', 'Violation of terms of service')
        
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'UPDATE sellers SET shop_status=%s WHERE id=%s',
                ('suspended', seller_id)
            )
        else:
            cursor.execute(
                'UPDATE sellers SET shop_status=? WHERE id=?',
                ('suspended', seller_id)
            )
        
        db.commit()
        
        return success_response({
            'seller_id': seller_id,
            'shop_status': 'suspended',
            'reason': reason
        }, 'Seller shop suspended')
    except Exception as e:
        return error_response(str(e), 500)

# Admin: Reactivate Seller Shop
@app.route('/api/sellers/<int:seller_id>/reactivate-shop', methods=['POST'])
@role_required('admin')
def api_admin_reactivate_seller_shop(seller_id):
    """Admin reactivates a suspended seller's shop - instant restoration"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get seller info
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT s.user_id, s.business_name, u.email, u.first_name, s.shop_status
                FROM sellers s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.id=%s
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT s.user_id, s.business_name, u.email, u.first_name, s.shop_status
                FROM sellers s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.id=?
            ''', (seller_id,))
        
        seller_info = cursor.fetchone()
        if not seller_info:
            return error_response('Seller not found', 404)
        
        # Clear suspension and reactivate
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE sellers 
                SET shop_status=%s, 
                    suspended_at=NULL, 
                    suspended_by=NULL, 
                    suspension_reason=NULL,
                    suspension_type=NULL
                WHERE id=%s
            ''', ('active', seller_id))
        else:
            cursor.execute('''
                UPDATE sellers 
                SET shop_status=?, 
                    suspended_at=NULL, 
                    suspended_by=NULL, 
                    suspension_reason=NULL,
                    suspension_type=NULL
                WHERE id=?
            ''', ('active', seller_id))
        
        db.commit()
        
        # Send reactivation email
        if seller_info:
            try:
                from backend.email_service import send_email
                seller_data = seller_info if isinstance(seller_info, dict) else {
                    'business_name': seller_info[1],
                    'email': seller_info[2],
                    'first_name': seller_info[3]
                }
                
                subject = "✅ Your Seller Account Has Been Reactivated!"
                body = f"""Dear {seller_data['first_name']},

Good news! Your seller account and shop "{seller_data['business_name']}" has been reactivated.

✅ Your shop is now ACTIVE
✅ Your products are visible to customers
✅ You can add and edit products
✅ You can process orders normally
✅ All permissions restored

You can now resume your business activities on Hub E-Commerce.

Please ensure you comply with our terms and conditions to avoid future suspensions.

Best regards,
Hub E-Commerce Admin Team
"""
                send_email(seller_data['email'], subject, body)
            except Exception as email_error:
                print(f"Reactivation email notification failed: {email_error}")
        
        return success_response({
            'seller_id': seller_id,
            'shop_status': 'active',
            'reactivated_at': datetime.utcnow().isoformat(),
            'effect': 'Shop and products visible to customers instantly'
        }, 'Seller shop reactivated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/sellers/<int:seller_id>', methods=['PUT'])
@token_required
def api_update_seller_profile(seller_id):
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    try:
        payload = verify_token(token)
        # Only allow seller to update their own profile
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM sellers WHERE id=?', (seller_id,))
        seller = cursor.fetchone()
        if not seller:
            return error_response('Seller not found', 404)
        if payload.get('role') != 'seller' or seller['user_id'] != payload.get('user_id'):
            return error_response('Forbidden', 403)
        data = request.json or {}
        # Update seller table
        updates = []
        params = []
        for field in ['business_name', 'category']:
            if field in data:
                updates.append(f'{field}=?')
                params.append(data[field])
        if updates:
            params.append(seller_id)
            cursor.execute(f'UPDATE sellers SET {", ".join(updates)} WHERE id=?', params)
        # Update user table
        user_updates = []
        user_params = []
        for field in ['first_name', 'last_name']:
            if field in data:
                user_updates.append(f'{field}=?')
                user_params.append(data[field])
        if user_updates:
            user_params.append(seller['user_id'])
            cursor.execute(f'UPDATE users SET {", ".join(user_updates)} WHERE id=?', user_params)
        db.commit()
        return success_response({'seller_id': seller_id}, 'Seller profile updated')
    except Exception as e:
        return error_response(str(e), 500)

# MySQL configuration (already defined above, but keeping for compatibility)
MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST','127.0.0.1'),
    'user': os.environ.get('DB_USER','root'),
    'password': os.environ.get('DB_PASS',''),
    'db': os.environ.get('DB_NAME','qwerty'),
    'port': int(os.environ.get('DB_PORT','3306')),
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False,
    'charset': 'utf8mb4'
}

# Detect templates/static folders (check both current and sibling qwerty project)
TEMPLATES_DIR = None
STATIC_DIR = None
try:
    # Look for frontend directory (new structure)
    frontend_dir = os.path.join(BASE_DIR, 'frontend')
    tdir = os.path.join(frontend_dir, 'templates')
    sdir = os.path.join(frontend_dir, 'css')  # Static files in frontend
    
    if os.path.exists(frontend_dir):
        # New structure: frontend/ has templates and static files
        if not os.path.exists(tdir):
            # If no templates subdir, use frontend root
            tdir = frontend_dir
        TEMPLATES_DIR = tdir
        STATIC_DIR = frontend_dir
    
    # Fallback to old structure for compatibility
    if not TEMPLATES_DIR:
        tdir = os.path.join(BASE_DIR, 'templates')
        if os.path.exists(tdir):
            TEMPLATES_DIR = tdir
    
    if not STATIC_DIR:
        sdir = os.path.join(BASE_DIR, 'static')
        if os.path.exists(sdir):
            STATIC_DIR = sdir
except Exception:
    TEMPLATES_DIR = None
    STATIC_DIR = None

# Register blueprints now that `app` is defined
# IMPORTANT: Register blueprints BEFORE any catch-all routes
try:
    from .messaging_api import messaging_bp
    app.register_blueprint(messaging_bp)
    print("✅ Messaging blueprint registered")
except Exception as e:
    print(f"❌ Failed to register messaging blueprint: {e}")
    import traceback
    traceback.print_exc()
# Direct route for creating conversations - ensures it works even if blueprint has issues
@app.route('/api/conversations/create', methods=['POST'])
@token_required
@role_required('customer')
def api_create_conversation_direct():
    """Direct route for creating conversations"""
    try:
        data = request.get_json()
        seller_id = data.get('seller_id') if data else None
        
        if not seller_id:
            return error_response('Seller ID is required', 400)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user_id = g.user_id
        
        # Check if conversation exists
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM conversations WHERE customer_id = %s AND seller_id = %s', (user_id, seller_id))
        else:
            cursor.execute('SELECT id FROM conversations WHERE customer_id = ? AND seller_id = ?', (user_id, seller_id))
        
        existing = cursor.fetchone()
        
        if existing:
            conversation_id = existing.get('id') if isinstance(existing, dict) else existing[0]
            is_new = False
        else:
            # Create new conversation
            if DB_ENGINE == 'mysql':
                cursor.execute('INSERT INTO conversations (customer_id, seller_id, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())', (user_id, seller_id))
            else:
                cursor.execute('INSERT INTO conversations (customer_id, seller_id, created_at, updated_at) VALUES (?, ?, ?, ?)', (user_id, seller_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            
            conn.commit()
            conversation_id = cursor.lastrowid
            is_new = True
        
        cursor.close()
        close_db_connection(conn)
        
        return success_response({
            'conversation_id': conversation_id,
            'customer_id': user_id,
            'seller_id': seller_id,
            'created': is_new
        })
    except Exception as e:
        return error_response(str(e), 500)

# Direct routes for messaging endpoints - ensures they work even if blueprint has issues
@app.route('/api/messages/<int:conversation_id>', methods=['GET'])
@token_required
def api_get_messages_direct(conversation_id):
    """Get messages for a conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user_id = g.user_id
        user_role = g.role
        
        # Verify user has access to this conversation
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT customer_id, seller_id FROM conversations WHERE id = %s', (conversation_id,))
        else:
            cursor.execute('SELECT customer_id, seller_id FROM conversations WHERE id = ?', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            cursor.close()
            close_db_connection(conn)
            return error_response('Conversation not found', 404)
        
        # Check authorization
        if user_role == 'customer':
            conv_customer_id = conversation.get('customer_id') if isinstance(conversation, dict) else conversation[0]
            if conv_customer_id != user_id:
                cursor.close()
                close_db_connection(conn)
                return error_response('Unauthorized', 403)
        elif user_role == 'seller':
            # Get seller ID from user_id
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT id FROM sellers WHERE user_id = %s', (user_id,))
            else:
                cursor.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,))
            seller = cursor.fetchone()
            if not seller:
                cursor.close()
                close_db_connection(conn)
                return error_response('Seller profile not found', 404)
            seller_id = seller.get('id') if isinstance(seller, dict) else seller[0]
            conv_seller_id = conversation.get('seller_id') if isinstance(conversation, dict) else conversation[1]
            if conv_seller_id != seller_id:
                cursor.close()
                close_db_connection(conn)
                return error_response('Unauthorized', 403)
        else:
            cursor.close()
            close_db_connection(conn)
            return error_response('Unauthorized', 403)
        
        # Get messages
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT id, conversation_id, sender_id, sender_type, message, is_read, created_at, attachment_url, attachment_type
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            ''', (conversation_id,))
        else:
            cursor.execute('''
                SELECT id, conversation_id, sender_id, sender_type, message, is_read, created_at, attachment_url, attachment_type
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            ''', (conversation_id,))
        
        messages = cursor.fetchall()
        messages_list = format_rows(messages)
        
        cursor.close()
        close_db_connection(conn)
        
        return success_response({'messages': messages_list})
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/messages/read/<int:conversation_id>', methods=['PATCH'])
@token_required
def api_mark_messages_read(conversation_id):
    """Mark messages as read in a conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user_id = g.user_id
        user_role = g.role
        
        # Verify user has access to this conversation
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT customer_id, seller_id FROM conversations WHERE id = %s', (conversation_id,))
        else:
            cursor.execute('SELECT customer_id, seller_id FROM conversations WHERE id = ?', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            cursor.close()
            close_db_connection(conn)
            return error_response('Conversation not found', 404)
        
        # Determine opposite role
        opposite_role = 'seller' if user_role == 'customer' else 'customer'
        
        # Mark messages as read
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE messages 
                SET is_read = TRUE 
                WHERE conversation_id = %s AND sender_type = %s AND is_read = FALSE
            ''', (conversation_id, opposite_role))
        else:
            cursor.execute('''
                UPDATE messages 
                SET is_read = 1 
                WHERE conversation_id = ? AND sender_type = ? AND is_read = 0
            ''', (conversation_id, opposite_role))
        
        conn.commit()
        updated_count = cursor.rowcount
        
        cursor.close()
        close_db_connection(conn)
        
        return success_response({'marked_read': updated_count})
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/messages/unread-count', methods=['GET'])
@token_required
def api_get_unread_count_direct():
    """Get total unread message count for current user - supports store_id filtering for sellers"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user_id = g.user_id
        user_role = g.role
        store_id = request.args.get('store_id', type=int)
        
        if user_role == 'customer':
            # Count unread messages from sellers
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.customer_id = %s AND m.sender_type = 'seller' AND m.is_read = FALSE
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.customer_id = ? AND m.sender_type = 'seller' AND m.is_read = 0
                ''', (user_id,))
        elif user_role == 'seller':
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
            # Note: conversations.seller_id is user_id, not sellers.id
            if store_id and store_id_column_exists:
                store_filter = 'c.seller_id = %s AND c.store_id = %s' if DB_ENGINE == 'mysql' else 'c.seller_id = ? AND c.store_id = ?'
                filter_params = (user_id, store_id)
            elif store_id_column_exists:
                store_filter = 'c.seller_id = %s AND (c.store_id IS NULL OR c.store_id = 0)' if DB_ENGINE == 'mysql' else 'c.seller_id = ? AND (c.store_id IS NULL OR c.store_id = 0)'
                filter_params = (user_id,)
            else:
                store_filter = 'c.seller_id = %s' if DB_ENGINE == 'mysql' else 'c.seller_id = ?'
                filter_params = (user_id,)
            
            # Count unread messages from customers
            if DB_ENGINE == 'mysql':
                cursor.execute(f'''
                    SELECT COUNT(*) as count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE {store_filter} AND m.sender_type = 'customer' AND m.is_read = FALSE
                ''', filter_params)
            else:
                cursor.execute(f'''
                    SELECT COUNT(*) as count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE {store_filter} AND m.sender_type = 'customer' AND m.is_read = 0
                ''', filter_params)
        else:
            cursor.close()
            close_db_connection(conn)
            return success_response({'unread_count': 0})
        
        result = cursor.fetchone()
        if not result:
            count = 0
        elif isinstance(result, dict):
            count = result.get('count', 0)
        else:
            count = result[0] if len(result) > 0 else 0
        
        cursor.close()
        close_db_connection(conn)
        
        return success_response({'unread_count': int(count) if count else 0})
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        app.logger.error(f'Error in api_get_unread_count_direct: {error_msg}')
        return error_response(f'Failed to get unread count: {error_msg}', 500)

# Direct route for seller conversations - ensures it works even if blueprint has issues
@app.route('/api/conversations/seller', methods=['GET'])
@token_required
@role_required('seller')
def api_get_seller_conversations_direct():
    """Get all conversations for the authenticated seller - supports store_id filtering"""
    try:
        # Get seller ID from user_id
        user_id = g.user_id
        store_id = request.args.get('store_id', type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        # First, get the seller ID from the user_id
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM sellers WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,))
        
        seller = cursor.fetchone()
        if not seller:
            cursor.close()
            close_db_connection(conn)
            return error_response('Seller profile not found', 404)
        
        seller_id = seller.get('id') if isinstance(seller, dict) else seller[0]
        
        # Build filter condition
        if store_id and store_id_column_exists:
            # Note: conversations.seller_id is user_id, not sellers.id
            # So we filter by user_id directly
            store_filter = 'c.seller_id = %s AND c.store_id = %s' if DB_ENGINE == 'mysql' else 'c.seller_id = ? AND c.store_id = ?'
            filter_params = (user_id, store_id)
        elif store_id_column_exists:
            store_filter = 'c.seller_id = %s AND (c.store_id IS NULL OR c.store_id = 0)' if DB_ENGINE == 'mysql' else 'c.seller_id = ? AND (c.store_id IS NULL OR c.store_id = 0)'
            filter_params = (user_id,)
        else:
            store_filter = 'c.seller_id = %s' if DB_ENGINE == 'mysql' else 'c.seller_id = ?'
            filter_params = (user_id,)
        
        # Get conversations with customer info and last message
        if DB_ENGINE == 'mysql':
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
            ''', filter_params)
        else:
            cursor.execute(f'''
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
                'customer_name': conv[5] if len(conv) > 5 else 'Customer',
                'customer_email': conv[6] if len(conv) > 6 else '',
                'unread_count': conv[7] if len(conv) > 7 else 0,
                'last_message': conv[8] if len(conv) > 8 else None
            }
            
            last_msg_at = conv_dict.get('last_message_at') if isinstance(conv_dict, dict) else conv_dict['last_message_at']
            created_at_val = conv_dict.get('created_at') if isinstance(conv_dict, dict) else conv_dict['created_at']
            
            result.append({
                'id': conv_dict.get('id') if isinstance(conv_dict, dict) else conv_dict['id'],
                'customer_id': conv_dict.get('customer_id') if isinstance(conv_dict, dict) else conv_dict['customer_id'],
                'seller_id': conv_dict.get('seller_id') if isinstance(conv_dict, dict) else conv_dict['seller_id'],
                'customer_name': conv_dict.get('customer_name') or 'Customer',
                'customer_email': conv_dict.get('customer_email') or '',
                'last_message': conv_dict.get('last_message'),
                'last_message_at': (last_msg_at.isoformat() if hasattr(last_msg_at, 'isoformat') else str(last_msg_at)) if last_msg_at else None,
                'unread_count': int(conv_dict.get('unread_count', 0)) if conv_dict.get('unread_count') else 0,
                'created_at': (created_at_val.isoformat() if hasattr(created_at_val, 'isoformat') else str(created_at_val)) if created_at_val else None
            })
        
        cursor.close()
        close_db_connection(conn)
        
        return success_response({
            'conversations': result,
            'total': len(result)
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        app.logger.error(f'Error in api_get_seller_conversations_direct: {error_msg}')
        return error_response(f'Failed to fetch conversations: {error_msg}', 500)

try:
    from .shipping_api import shipping_bp
    app.register_blueprint(shipping_bp)
except Exception:
    pass
try:
    from .earnings_api import earnings_bp
    app.register_blueprint(earnings_bp)
except Exception:
    pass

# Low-level helpers
def get_query_param(key, default=None, cast=str, min_len=None, max_len=None, allowed=None):
    """
    Safely extract and validate query parameters from request.
    
    Args:
        key: parameter name
        default: default value if not present
        cast: type to cast to (int, str, float, bool)
        min_len: minimum string length (for str)
        max_len: maximum string length (for str)
        allowed: list of allowed values
    
    Returns:
        Validated parameter value or default
    """
    try:
        val = request.args.get(key)
        if val is None:
            return default
        
        # Cast to desired type
        if cast == int:
            val = int(val)
        elif cast == float:
            val = float(val)
        elif cast == bool:
            val = val.lower() in ('true', '1', 'yes')
        else:
            val = str(val).strip()
        
        # Validate string constraints
        if cast == str and val:
            if min_len is not None and len(val) < min_len:
                return default
            if max_len is not None and len(val) > max_len:
                val = val[:max_len]
        
        # Check allowed values
        if allowed is not None and val not in allowed:
            return default
        
        return val
    except (ValueError, TypeError):
        return default

def get_db():
    """Get MySQL database connection from Flask g context"""
    if 'db' not in g:
        g.db = pymysql.connect(**MYSQL_CONFIG)
    return g.db

def get_db_connection():
    """Backward-compatible alias for older code that expects get_db_connection()."""
    # Return the same connection object managed by Flask `g`
    return get_db()


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

# Schema initialization using schema.sql
def clear_all_sessions():
    """Clear all active sessions on server startup/restart"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            # Revoke all refresh tokens
            cur.execute("UPDATE refresh_tokens SET revoked=1 WHERE revoked=0")
            rows_affected = cur.rowcount
            conn.commit()
            print(f"[SESSION] Cleared {rows_affected} active session(s) on server startup")
        else:
            # SQLite
            cur.execute("UPDATE refresh_tokens SET revoked=1 WHERE revoked=0")
            rows_affected = cur.rowcount
            conn.commit()
            print(f"[SESSION] Cleared {rows_affected} active session(s) on server startup")
        
        cur.close()
    except pymysql.err.OperationalError:
        # MySQL not running - skip silently
        pass
    except Exception as e:
        # Only log unexpected errors
        if "Can't connect" not in str(e):
            print(f"[WARN] Warning: Could not clear sessions on startup: {e}")
        # Non-fatal error, continue startup
    finally:
        # MySQL connections are managed by Flask g context
        pass

def init_db():
    """Initialize MySQL database - schema should be imported via MySQL client"""
    # For MySQL, user will import schema_mysql.sql via XAMPP or MySQL client
    # Server will only seed some data if DB exists
    schema_path = os.path.join(BASE_DIR, 'database', 'schema_mysql.sql')
    
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # MySQL migration support
        if os.environ.get('MIGRATE','0') == '1':
            mysql_sql = os.path.join(BASE_DIR, 'database', 'schema_mysql.sql')
            if os.path.exists(mysql_sql):
                with open(mysql_sql, 'r', encoding='utf-8') as f:
                    sql = f.read()
                # Execute each statement separately to avoid multi-statement failures
                for stmt in [s.strip() for s in sql.split(';') if s.strip()]:
                    cur.execute(stmt)
        # For MySQL, we assume the user runs schema_mysql.sql via client; but we create a small seed if table exists
        cur.execute("SELECT 1")
        print("[COMMIT] Committing changes...")
        conn.commit()
        print("[OK] Database commit successful")
        cur.close()
        
        # Seed data using same connection
        # For MySQL, only seed if tables exist and MIGRATE is set
        should_seed = False
        if os.environ.get('MIGRATE','0') == '1':
            # Check if users table exists before seeding
            try:
                cur.execute("SELECT 1 FROM users LIMIT 1")
                should_seed = True
            except:
                print("[WARN] Tables not found - skipping seed data. Run migrations first.")
                should_seed = False
        
        if should_seed:
            seed_data_with_conn(conn)
        
        # Ensure product_images table exists (for multiple images per product)
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS product_images (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    image_url VARCHAR(768) NOT NULL,
                    display_order INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    INDEX idx_product_images (product_id, display_order)
                ) ENGINE=InnoDB;
            """)
            conn.commit()
            cur.close()
        except Exception as e:
            app.logger.warning(f'Could not create product_images table: {e}')
    finally:
        # MySQL connections are managed by Flask g context
        pass
    
    # Clear all active sessions after DB initialization
    if not app.config.get('TESTING', False):
        with app.app_context():
            clear_all_sessions()

# Register cleanup on shutdown
@atexit.register
def cleanup_on_shutdown():
    """Clean up sessions when server shuts down"""
    try:
        print("\n[SHUTDOWN] Server shutting down - clearing all active sessions...")
        with app.app_context():
            clear_all_sessions()
    except Exception as e:
        print(f"[WARN] Error during shutdown cleanup: {e}")


# --- Session Management Endpoints ---

@app.route('/api/server/instance', methods=['GET'])
def api_server_instance():
    """Get server instance ID and start time for session validation"""
    return jsonify({
        'instance_id': SERVER_INSTANCE_ID,
        'start_time': SERVER_START_TIME,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def api_logout(current_user):
    """Logout user and revoke refresh token"""
    try:
        # Get refresh token from request body
        data = request.get_json() or {}
        refresh_token = data.get('refresh_token')
        
        # Revoke the refresh token if provided
        if refresh_token:
            try:
                revoke_refresh_token_by_hash(get_db(), refresh_token)
            except Exception as e:
                app.logger.warning(f'Failed to revoke refresh token: {e}')
        
        # Clear session
        session.clear()
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
    except Exception as e:
        app.logger.error(f'Logout error: {e}')
        return jsonify({
            'success': True,  # Still return success even if token revocation fails
            'message': 'Logged out'
        })

# --- Additional endpoints merged from additional_endpoints.py ---

@app.route('/api/users/<int:user_id>', methods=['GET'])
@token_required
def api_get_user(user_id):
    """Get user profile by ID."""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT id, email, first_name, last_name, role, created_at FROM users WHERE id=%s;", (user_id,))
        else:
            cur.execute("SELECT id, email, first_name, last_name, role, created_at FROM users WHERE id=?;", (user_id,))
        
        user = cur.fetchone()
        cur.close()
        
        if not user:
            return error_response('User not found', 404)
        
        user_dict = format_row(user)
        
        # Get role-specific data
        if user_dict.get('role') == 'seller':
            if DB_ENGINE == 'mysql':
                cur = conn.cursor()
                cur.execute("SELECT * FROM sellers WHERE user_id=%s;", (user_id,))
                seller = cur.fetchone()
                cur.close()
            else:
                cur = conn.cursor()
                cur.execute("SELECT * FROM sellers WHERE user_id=?;", (user_id,))
                seller = cur.fetchone()
                cur.close()
            
            if seller:
                user_dict['seller'] = format_row(seller)
        
        elif user_dict.get('role') == 'rider':
            if DB_ENGINE == 'mysql':
                cur = conn.cursor()
                cur.execute("SELECT * FROM riders WHERE user_id=%s;", (user_id,))
                rider = cur.fetchone()
                cur.close()
            else:
                cur = conn.cursor()
                cur.execute("SELECT * FROM riders WHERE user_id=?;", (user_id,))
                rider = cur.fetchone()
                cur.close()
            
            if rider:
                user_dict['rider'] = format_row(rider)
        
        return success_response(user_dict)
    
    except Exception as e:
        print(f"Error fetching user {user_id}: {str(e)}")
        return error_response('Server error', 500)


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@token_required
def api_update_user(user_id):
    """Update user profile."""
    try:
        body = request.json or {}
        
        # Verify user is updating their own profile
        token_data = verify_token(get_token_from_request())
        if not token_data or token_data.get('user_id') != user_id:
            return error_response('Unauthorized', 403)
        
        conn = get_db()
        cur = conn.cursor()
        
        # Build update query
        update_fields = []
        params = []
        
        if 'first_name' in body:
            update_fields.append('first_name=%s' if DB_ENGINE == 'mysql' else 'first_name=?')
            params.append(body['first_name'])
        
        if 'last_name' in body:
            update_fields.append('last_name=%s' if DB_ENGINE == 'mysql' else 'last_name=?')
            params.append(body['last_name'])
        
        if not update_fields:
            cur.close()
            return error_response('No fields to update', 400)
        
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id={'%s' if DB_ENGINE == 'mysql' else '?'};"
        cur.execute(query, params)
        conn.commit()
        cur.close()
        
        return success_response(message='Profile updated successfully')
    
    except Exception as e:
        print(f"Error updating user {user_id}: {str(e)}")
        return error_response('Server error', 500)


@app.route('/api/auth/change-password', methods=['POST'])
@token_required
def api_change_password():
    """Change user password."""
    try:
        body = request.json or {}
        current_password = body.get('current_password')
        new_password = body.get('new_password')
        
        if not current_password or not new_password:
            return error_response('Missing required fields', 400)
        
        token_data = verify_token(get_token_from_request())
        if not token_data:
            return error_response('Invalid token', 401)
        
        user_id = token_data.get('user_id')
        
        conn = get_db()
        cur = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT password_hash FROM users WHERE id=%s;", (user_id,))
        else:
            cur.execute("SELECT password_hash FROM users WHERE id=?;", (user_id,))
        
        result = cur.fetchone()
        cur.close()

        if not result:
            return error_response('Current password is incorrect', 400)

        # Normalize stored hash extraction for different cursor/row types
        stored_hash = None
        try:
            if isinstance(result, (list, tuple)):
                stored_hash = result[0]
            elif isinstance(result, dict):
                stored_hash = result.get('password_hash')
            else:
                # sqlite3.Row supports mapping access
                stored_hash = result['password_hash']
        except Exception:
            stored_hash = None

        if not stored_hash or not check_password_hash(stored_hash, current_password):
            return error_response('Current password is incorrect', 400)
        
        # Update password
        new_hash = generate_password_hash(new_password)
        cur = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s;", (new_hash, user_id))
        else:
            cur.execute("UPDATE users SET password_hash=? WHERE id=?;", (new_hash, user_id))
        
        conn.commit()
        cur.close()
        
        return success_response(message='Password changed successfully')
    
    except Exception as e:
        print(f"Error changing password: {str(e)}")
        return error_response('Server error', 500)


# WISHLIST ENDPOINTS
@app.route('/api/wishlist', methods=['GET'])
@token_required
def api_get_wishlist():
    """Get user's wishlist with quantity, total price, and wishlist_id."""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data:
            return error_response('Invalid token', 401)
        
        user_id = token_data.get('user_id')
        conn = get_db()
        cur = conn.cursor()
        
        # Table may not exist yet; return empty if so
        try:
            if DB_ENGINE == 'mysql':
                cur.execute(
                    """
                    SELECT 
                        w.id AS wishlist_id,
                        p.id AS product_id,
                        p.title AS name,
                        p.img_url AS image_url,
                        p.price AS price,
                        w.quantity,
                        w.price_total
                    FROM wishlist w 
                    JOIN products p ON p.id=w.product_id 
                    WHERE w.user_id=%s
                    ORDER BY w.id DESC
                    """,
                    (user_id,)
                )
                items = cur.fetchall()
            else:
                cur.execute(
                    """
                    SELECT 
                        w.id AS wishlist_id,
                        p.id AS product_id,
                        p.title AS name,
                        p.img_url AS image_url,
                        p.price AS price,
                        w.quantity,
                        w.price_total
                    FROM wishlist w 
                    JOIN products p ON p.id=w.product_id 
                    WHERE w.user_id=?
                    ORDER BY w.id DESC
                    """,
                    (user_id,)
                )
                items = cur.fetchall()

            # Format for frontend
            formatted_items = []
            for item in items:
                if hasattr(item, 'get'):
                    price = item.get('price')
                    price_total = item.get('price_total')
                    formatted_items.append({
                        'wishlist_id': item.get('wishlist_id'),
                        'product_id': item.get('product_id'),
                        'name': item.get('name'),
                        'image_url': item.get('image_url'),
                        'quantity': int(item.get('quantity') or 1),
                        'price': str(price or '0.00') if price is not None else '0.00',
                        'price_total': str(price_total or '0.00') if price_total is not None else '0.00'
                    })
                else:
                    price = item[4] if len(item) > 4 else None
                    price_total = item[6] if len(item) > 6 else None
                    formatted_items.append({
                        'wishlist_id': item[0],
                        'product_id': item[1],
                        'name': item[2],
                        'image_url': item[3],
                        'price': str(price or '0.00') if price is not None else '0.00',
                        'quantity': int(item[5] if len(item) > 5 else 1),
                        'price_total': str(price_total or '0.00') if price_total is not None else '0.00'
                    })
            results = formatted_items
        except Exception as e:
            print(f"Wishlist query error: {str(e)}")
            results = []
        finally:
            cur.close()

        # (logs removed)

        return jsonify({'success': True, 'items': results}), 200
    
    except Exception as e:
        print(f"Error fetching wishlist: {str(e)}")
        return error_response('Server error', 500)


@app.route('/api/wishlist/<int:product_id>', methods=['POST'])
@token_required
def api_add_to_wishlist(product_id):
    """Add or update a product in wishlist with quantity and total price."""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data:
            return error_response('Invalid token', 401)
        
        user_id = token_data.get('user_id')
        # (logs removed)
        body = request.get_json(silent=True) or {}
        try:
            qty = int(body.get('quantity') or 1)
        except Exception:
            qty = 1
        if qty < 1:
            qty = 1

        conn = get_db()
        cur = conn.cursor()
        try:
            # Get product price
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT price FROM products WHERE id=%s", (product_id,))
            else:
                cur.execute("SELECT price FROM products WHERE id=?", (product_id,))
            row = cur.fetchone()
            if not row:
                cur.close()
                return error_response('Product not found', 404)
            price = row.get('price') if hasattr(row, 'get') else row[0]

            # Check if wishlist item exists
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT id FROM wishlist WHERE user_id=%s AND product_id=%s", (user_id, product_id))
            else:
                cur.execute("SELECT id FROM wishlist WHERE user_id=? AND product_id=?", (user_id, product_id))
            existing = cur.fetchone()

            total = float(price) * qty

            if existing:
                wid = existing.get('id') if hasattr(existing, 'get') else existing[0]
                if DB_ENGINE == 'mysql':
                    cur.execute("UPDATE wishlist SET quantity=%s, price_total=%s WHERE id=%s", (qty, total, wid))
                else:
                    cur.execute("UPDATE wishlist SET quantity=?, price_total=? WHERE id=?", (qty, total, wid))
            else:
                if DB_ENGINE == 'mysql':
                    cur.execute(
                        "INSERT INTO wishlist (user_id, product_id, quantity, price_total, created_at) VALUES (%s,%s,%s,%s,%s)",
                        (user_id, product_id, qty, total, datetime.utcnow().isoformat()),
                    )
                else:
                    cur.execute(
                        "INSERT INTO wishlist (user_id, product_id, quantity, price_total, created_at) VALUES (?,?,?,?,?)",
                        (user_id, product_id, qty, total, datetime.utcnow().isoformat()),
                    )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Wishlist add error: {e}")
            return error_response('Failed to add to wishlist', 500)
        finally:
            cur.close()

        # (logs removed)
        return success_response(message='Product added to wishlist')
    
    except Exception as e:
        print(f"Error adding to wishlist: {str(e)}")
        return error_response('Server error', 500)


@app.route('/api/wishlist/<int:product_id>', methods=['DELETE'])
@token_required
def api_remove_from_wishlist(product_id):
    """Remove product from wishlist by product_id (legacy)."""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data:
            return error_response('Invalid token', 401)
        
        user_id = token_data.get('user_id')
        # (logs removed)
        conn = get_db()
        cur = conn.cursor()
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("DELETE FROM wishlist WHERE user_id=%s AND product_id=%s;", (user_id, product_id))
            else:
                cur.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?;", (user_id, product_id))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            cur.close()
        
        # (logs removed)
        return success_response(message='Product removed from wishlist')
    
    except Exception as e:
        print(f"Error removing from wishlist: {str(e)}")
        return error_response('Server error', 500)


@app.route('/api/wishlist/remove/<int:wishlist_id>', methods=['DELETE'])
@token_required
def api_remove_from_wishlist_by_id(wishlist_id):
    """Remove item from wishlist by wishlist_id (preferred)."""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data:
            return error_response('Invalid token', 401)

        user_id = token_data.get('user_id')
        # (logs removed)
        conn = get_db()
        cur = conn.cursor()
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("DELETE FROM wishlist WHERE id=%s AND user_id=%s", (wishlist_id, user_id))
            else:
                cur.execute("DELETE FROM wishlist WHERE id=? AND user_id=?", (wishlist_id, user_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Wishlist remove-by-id error: {e}")
            return error_response('Failed to remove item', 500)
        finally:
            cur.close()

        # (logs removed)
        return success_response(message='Product removed from wishlist')
    except Exception as e:
        print(f"Error removing from wishlist by id: {str(e)}")
        return error_response('Server error', 500)


# SEARCH & FILTER
@app.route('/api/products/search', methods=['GET'])
def api_search_products():
    """Search products by query."""
    try:
        # Use safe query param helper
        query = get_query_param('q', default='', cast=str, min_len=2, max_len=100)
        if not query:
            return error_response('Search query must be at least 2 characters', 400)
        # Remove SQL wildcard chars to avoid wildcard injection
        query = query.replace('%', '').replace('_', '')
        
        conn = get_db()
        cur = conn.cursor()
        
        search_pattern = f"%{query}%"
        
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT id, title, description, price, stock, seller_id, category, img_url, created_at
                FROM products
                WHERE (title LIKE %s OR description LIKE %s OR category LIKE %s)
                  AND stock > 0
                ORDER BY created_at DESC LIMIT 50;
            """, (search_pattern, search_pattern, search_pattern))
        else:
            cur.execute("""
                SELECT id, title, description, price, stock, seller_id, category, img_url, created_at
                FROM products
                WHERE (title LIKE ? OR description LIKE ? OR category LIKE ?)
                  AND stock > 0
                ORDER BY created_at DESC LIMIT 50;
            """, (search_pattern, search_pattern, search_pattern))
        
        products = cur.fetchall()
        cur.close()
        
        return success_response(format_rows(products))
    
    except Exception as e:
        print(f"Error searching products: {str(e)}")
        return error_response('Server error', 500)


@app.route('/api/products/suggestions', methods=['GET'])
def api_product_suggestions():
    """Get product name suggestions for autocomplete."""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return success_response([])
        
        # Remove SQL wildcard chars
        query = query.replace('%', '').replace('_', '')
        search_pattern = f"%{query}%"
        
        conn = get_db()
        cur = conn.cursor()
        
        # Get product titles that match, prioritizing exact matches and starts-with matches
        exact_match = query
        starts_with = f"{query}%"
        
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT DISTINCT title, category
                FROM products
                WHERE (title LIKE %s OR category LIKE %s)
                  AND stock > 0
                ORDER BY 
                  CASE 
                    WHEN LOWER(title) = %s THEN 1
                    WHEN LOWER(title) LIKE %s THEN 2
                    ELSE 3
                  END,
                  title ASC
                LIMIT 10;
            """, (search_pattern, search_pattern, exact_match.lower(), starts_with.lower()))
        else:
            cur.execute("""
                SELECT DISTINCT title, category
                FROM products
                WHERE (title LIKE ? OR category LIKE ?)
                  AND stock > 0
                ORDER BY 
                  CASE 
                    WHEN LOWER(title) = ? THEN 1
                    WHEN LOWER(title) LIKE ? THEN 2
                    ELSE 3
                  END,
                  title ASC
                LIMIT 10;
            """, (search_pattern, search_pattern, exact_match.lower(), starts_with.lower()))
        
        suggestions = cur.fetchall()
        cur.close()
        
        # Format suggestions
        result = []
        for row in suggestions:
            if hasattr(row, 'keys'):
                result.append({'title': row['title'], 'category': row.get('category', '')})
            else:
                result.append({'title': row[0], 'category': row[1] if len(row) > 1 else ''})
        
        return success_response(result)
    
    except Exception as e:
        print(f"Error getting suggestions: {str(e)}")
        return success_response([])


@app.route('/api/products/<int:product_id>/variations', methods=['GET'])
def api_get_product_variations(product_id):
    """Return variation options for a product if any exist."""
    try:
        conn = get_db()
        cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            # product_variation_options is the table created by migration
            cur.execute('''
                SELECT id, variation_type as type, variation_value as name, price_adjustment, stock, sku
                FROM product_variation_options
                WHERE product_id = %s AND is_available = 1
                ORDER BY variation_type, id
            ''', (product_id,))
        else:
            cur.execute('''
                SELECT id, variation_type as type, variation_value as name, price_adjustment, stock, sku
                FROM product_variation_options
                WHERE product_id = ? AND is_available = 1
                ORDER BY variation_type, id
            ''', (product_id,))
        rows = cur.fetchall()
        cur.close()

        # Normalize rows to list of dicts
        variations = []
        for r in rows:
            try:
                v = dict(r) if hasattr(r, 'keys') else {
                    'id': r[0], 'type': r[1], 'name': r[2], 'price_adjustment': r[3], 'stock': r[4], 'sku': r[5]
                }
            except Exception:
                v = r
            # provide defaults
            v['price_adjustment'] = float(v.get('price_adjustment') or 0)
            v['stock'] = int(v.get('stock') or 0)
            variations.append(v)

        return success_response(variations, 'Variations fetched')
    except Exception as e:
        app.logger.warning(f'No variations or error fetching variations for product {product_id}: {e}')
        return success_response([], 'No variations')


@app.route('/api/products/filter', methods=['GET'])
def api_filter_products():
    """Filter products by category, price, seller, etc."""
    try:
        # Use safe query param helper to sanitize inputs
        category = get_query_param('category', default='', cast=str, max_len=100) or ''
        seller_id_val = get_query_param('seller_id', default=None, cast=int)
        price_min_val = get_query_param('price_min', default='0', cast=str)
        price_max_val = get_query_param('price_max', default='999999', cast=str)

        seller_id_str = str(seller_id_val) if seller_id_val is not None else ''
        price_min = price_min_val.strip() if isinstance(price_min_val, str) else str(price_min_val)
        price_max = price_max_val.strip() if isinstance(price_max_val, str) else str(price_max_val)
        
        # Validate price range
        try:
            price_min = float(price_min)
            price_max = float(price_max)
            
            if price_min < 0 or price_max < 0:
                return error_response('Price cannot be negative', 400)
            
            if price_min > price_max:
                return error_response('Minimum price cannot exceed maximum price', 400)
            
            if price_max > 10000000:  # 10M limit
                return error_response('Price limit exceeded', 400)
                
        except ValueError:
            return error_response('Invalid price range format', 400)
        
        # Validate seller_id if provided
        seller_id = None
        if seller_id_str:
            try:
                seller_id = int(seller_id_str)
                if seller_id <= 0:
                    return error_response('Invalid seller ID', 400)
            except Exception:
                return error_response('Invalid seller ID format', 400)
        
        # Validate category length
        if category and len(category) > 100:
            return error_response('Category name too long', 400)
        
        conn = get_db()
        cur = conn.cursor()
        
        query = "SELECT id, title, description, price, stock, seller_id, category, img_url, created_at FROM products WHERE price BETWEEN "
        params = []
        
        if DB_ENGINE == 'mysql':
            query += "%s AND %s AND stock > 0"
            params = [price_min, price_max]
        else:
            query += "? AND ? AND stock > 0"
            params = [price_min, price_max]
        
        if category:
            if DB_ENGINE == 'mysql':
                query += " AND category = %s"
                params.append(category)
            else:
                query += " AND category = ?"
                params.append(category)
        
        if seller_id:
            if DB_ENGINE == 'mysql':
                query += " AND seller_id = %s"
                params.append(seller_id)
            else:
                query += " AND seller_id = ?"
                params.append(seller_id)
        
        query += " ORDER BY created_at DESC LIMIT 200;"
        
        cur.execute(query, params)
        products = cur.fetchall()
        cur.close()
        
        return success_response(format_rows(products))
    
    except Exception as e:
        print(f"Error filtering products: {str(e)}")
        return error_response('Server error', 500)


# ORDER HISTORY & TRACKING
@app.route('/api/users/<int:user_id>/orders', methods=['GET'])
@token_required
def api_get_user_orders(user_id):
    """Get user's order history."""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data or token_data.get('user_id') != user_id:
            return error_response('Unauthorized', 403)
        
        conn = get_db()
        cur = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT id, customer_id, customer_name, subtotal, delivery_fee, total, payment, status, created_at
                FROM orders WHERE customer_id=%s ORDER BY created_at DESC;
            """, (user_id,))
        else:
            cur.execute("""
                SELECT id, customer_id, customer_name, subtotal, delivery_fee, total, payment, status, created_at
                FROM orders WHERE customer_id=? ORDER BY created_at DESC;
            """, (user_id,))
        
        orders = cur.fetchall()
        cur.close()
        
        return success_response(format_rows(orders))
    
    except Exception as e:
        print(f"Error fetching user orders: {str(e)}")
        return error_response('Server error', 500)


@app.route('/api/cart', methods=['GET', 'POST'])
@token_required
def api_cart_endpoint(current_user=None):
    """GET: return current user's cart items. POST: add/update item in cart (supports variation_id)."""
    try:
        token = get_token_from_request()
        if not token:
            return error_response('Unauthorized', 401)
        payload = verify_token(token)
        user_id = payload.get('user_id')
        conn = get_db(); cur = conn.cursor()

        # Detect whether cart_items table has a variation_id column (migration may not have been applied)
        has_variation = False
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'cart_items' AND COLUMN_NAME = 'variation_id'
                """, (MYSQL_CONFIG.get('db'),))
                r = cur.fetchone()
                try:
                    has_variation = int(r.get('cnt') if hasattr(r, 'get') else r[0]) > 0
                except Exception:
                    has_variation = bool(r and r[0] > 0)
            else:
                # SQLite
                cur.execute("PRAGMA table_info('cart_items')")
                cols = cur.fetchall()
                for c in cols:
                    name = c.get('name') if hasattr(c, 'get') else c[1]
                    if name == 'variation_id':
                        has_variation = True
                        break
        except Exception:
            # If anything fails, assume older schema without variation support
            has_variation = False

        if request.method == 'GET':
            # Build a compatible SELECT depending on schema
            if has_variation:
                if DB_ENGINE == 'mysql':
                    cur.execute('''
                        SELECT ci.id as cart_id, ci.product_id, ci.variation_id, ci.quantity,
                               p.title as product_title, p.price as product_price, p.img_url,
                               pv.variation_value as variation_name, pv.price_adjustment
                        FROM cart_items ci
                        LEFT JOIN products p ON ci.product_id = p.id
                        LEFT JOIN product_variation_options pv ON ci.variation_id = pv.id
                        WHERE ci.user_id = %s
                        ORDER BY ci.created_at DESC
                    ''', (user_id,))
                else:
                    cur.execute('''
                        SELECT ci.id as cart_id, ci.product_id, ci.variation_id, ci.quantity,
                               p.title as product_title, p.price as product_price, p.img_url,
                               pv.variation_value as variation_name, pv.price_adjustment
                        FROM cart_items ci
                        LEFT JOIN products p ON ci.product_id = p.id
                        LEFT JOIN product_variation_options pv ON ci.variation_id = pv.id
                        WHERE ci.user_id = ?
                        ORDER BY ci.created_at DESC
                    ''', (user_id,))
            else:
                # Older schema: no variation column or variation table
                if DB_ENGINE == 'mysql':
                    cur.execute('''
                        SELECT ci.id as cart_id, ci.product_id, NULL as variation_id, ci.quantity,
                               p.title as product_title, p.price as product_price, p.img_url,
                               NULL as variation_name, 0 as price_adjustment
                        FROM cart_items ci
                        LEFT JOIN products p ON ci.product_id = p.id
                        WHERE ci.user_id = %s
                        ORDER BY ci.created_at DESC
                    ''', (user_id,))
                else:
                    cur.execute('''
                        SELECT ci.id as cart_id, ci.product_id, NULL as variation_id, ci.quantity,
                               p.title as product_title, p.price as product_price, p.img_url,
                               NULL as variation_name, 0 as price_adjustment
                        FROM cart_items ci
                        LEFT JOIN products p ON ci.product_id = p.id
                        WHERE ci.user_id = ?
                        ORDER BY ci.created_at DESC
                    ''', (user_id,))

            rows = cur.fetchall()
            items = []
            for r in rows:
                row = dict(r) if hasattr(r, 'keys') else {
                    'cart_id': r[0], 'product_id': r[1], 'variation_id': r[2], 'quantity': r[3],
                    'product_title': r[4], 'product_price': r[5], 'img_url': r[6], 'variation_name': r[7], 'price_adjustment': r[8]
                }
                product_id = row.get('product_id')
                base_price = float(row.get('product_price') or 0)
                price_adjustment = float(row.get('price_adjustment') or 0)
                
                # Check for active sale
                sale_price = None
                original_price = base_price
                discount_percentage = None
                
                try:
                    if DB_ENGINE == 'mysql':
                        cur.execute("""
                            SELECT sale_price, original_price, discount_percentage
                            FROM product_sales
                            WHERE product_id = %s
                              AND is_active = 1
                              AND status = 'approved'
                              AND (valid_until IS NULL OR valid_until > NOW())
                            LIMIT 1
                        """, (product_id,))
                    else:
                        cur.execute("""
                            SELECT sale_price, original_price, discount_percentage
                            FROM product_sales
                            WHERE product_id = ?
                              AND is_active = 1
                              AND status = 'approved'
                              AND (valid_until IS NULL OR valid_until > datetime('now'))
                            LIMIT 1
                        """, (product_id,))
                    
                    sale_row = cur.fetchone()
                    if sale_row:
                        sale_dict = format_row(sale_row)
                        sale_price = float(sale_dict.get('sale_price') or base_price)
                        original_price = float(sale_dict.get('original_price') or base_price)
                        discount_percentage = float(sale_dict.get('discount_percentage') or 0)
                except Exception as sale_err:
                    app.logger.warning(f'Error checking sale for product {product_id}: {sale_err}')
                    sale_price = None
                
                # Use sale price if available, otherwise use base price
                final_base_price = sale_price if sale_price is not None else base_price
                price = final_base_price + price_adjustment
                
                item_data = {
                    'cart_id': row.get('cart_id'),
                    'product_id': product_id,
                    'title': row.get('product_title'),
                    'img_url': row.get('img_url'),
                    'variation': row.get('variation_name'),
                    'quantity': int(row.get('quantity') or 1),
                    'unit_price': price,
                    'total_price': round(price * int(row.get('quantity') or 1), 2)
                }
                
                # Include sale information if available
                if sale_price is not None:
                    item_data['original_price'] = original_price + price_adjustment
                    item_data['sale_price'] = price
                    item_data['discount_percentage'] = discount_percentage
                    item_data['on_sale'] = True
                else:
                    item_data['on_sale'] = False
                
                items.append(item_data)
            cur.close()
            return success_response({'items': items}, 'Cart retrieved')

        # POST: add/update
        data = request.get_json(silent=True) or {}
        product_id = int(data.get('product_id') or 0)
        qty = int(data.get('quantity') or 1)
        variation_id = data.get('variation_id')
        if qty < 1:
            qty = 1

        # Validate product exists
        if DB_ENGINE == 'mysql':
            cur.execute('SELECT id, price, stock FROM products WHERE id=%s', (product_id,))
        else:
            cur.execute('SELECT id, price, stock FROM products WHERE id=?', (product_id,))
        p = cur.fetchone()
        if not p:
            cur.close()
            return error_response('Product not found', 404)

        # If variation specified and schema supports it, validate
        if variation_id and has_variation:
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT id, price_adjustment, stock, is_available FROM product_variation_options WHERE id=%s', (variation_id,))
            else:
                cur.execute('SELECT id, price_adjustment, stock, is_available FROM product_variation_options WHERE id=?', (variation_id,))
            v = cur.fetchone()
            if not v:
                cur.close()
                return error_response('Variation not found', 404)
            # check availability
            v_stock = int(v.get('stock') if hasattr(v, 'get') else v[2] or 0)
            if v_stock < qty:
                cur.close()
                return error_response('Not enough stock for selected variation', 400)

        # Insert or update cart_items (unique per user/product/variation when supported)
        if has_variation:
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT id, quantity FROM cart_items WHERE user_id=%s AND product_id=%s AND (variation_id=%s OR (variation_id IS NULL AND %s IS NULL))', (user_id, product_id, variation_id, variation_id))
            else:
                cur.execute('SELECT id, quantity FROM cart_items WHERE user_id=? AND product_id=? AND (variation_id=? OR (variation_id IS NULL AND ? IS NULL))', (user_id, product_id, variation_id, variation_id))
        else:
            # Older schema: only match by user and product
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT id, quantity FROM cart_items WHERE user_id=%s AND product_id=%s', (user_id, product_id))
            else:
                cur.execute('SELECT id, quantity FROM cart_items WHERE user_id=? AND product_id=?', (user_id, product_id))

        existing = cur.fetchone()
        try:
            if existing:
                cid = existing.get('id') if hasattr(existing, 'get') else existing[0]
                new_qty = int(existing.get('quantity') if hasattr(existing, 'get') else existing[1]) + qty
                if DB_ENGINE == 'mysql':
                    cur.execute('UPDATE cart_items SET quantity=%s, updated_at=NOW() WHERE id=%s', (new_qty, cid))
                else:
                    cur.execute('UPDATE cart_items SET quantity=?, updated_at=? WHERE id=?', (new_qty, datetime.utcnow().isoformat(), cid))
            else:
                if has_variation:
                    if DB_ENGINE == 'mysql':
                        cur.execute('INSERT INTO cart_items (user_id, product_id, variation_id, quantity, created_at, updated_at) VALUES (%s,%s,%s,%s,NOW(),NOW())', (user_id, product_id, variation_id, qty))
                    else:
                        cur.execute('INSERT INTO cart_items (user_id, product_id, variation_id, quantity, created_at, updated_at) VALUES (?,?,?,?,?,?)', (user_id, product_id, variation_id, qty, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                else:
                    if DB_ENGINE == 'mysql':
                        cur.execute('INSERT INTO cart_items (user_id, product_id, quantity, created_at, updated_at) VALUES (%s,%s,%s,NOW(),NOW())', (user_id, product_id, qty))
                    else:
                        cur.execute('INSERT INTO cart_items (user_id, product_id, quantity, created_at, updated_at) VALUES (?,?,?,?,?)', (user_id, product_id, qty, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            conn.commit()
        except Exception as e:
            conn.rollback()
            cur.close()
            return error_response('Failed to add to cart', 500)

        cur.close()
        return success_response(message='Added to cart')
    except Exception as e:
        app.logger.error(f'Cart endpoint error: {e}')
        return error_response('Server error', 500)


@app.route('/api/cart/<int:cart_item_id>', methods=['PUT', 'DELETE'])
@token_required
def api_cart_item_operations(cart_item_id):
    """Update or delete a specific cart item"""
    try:
        token = get_token_from_request()
        if not token:
            return error_response('Unauthorized', 401)
        payload = verify_token(token)
        user_id = payload.get('user_id')
        conn = get_db()
        cur = conn.cursor()

        if request.method == 'DELETE':
            # Delete cart item - ensure it belongs to current user
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT user_id FROM cart_items WHERE id=%s', (cart_item_id,))
            else:
                cur.execute('SELECT user_id FROM cart_items WHERE id=?', (cart_item_id,))
            
            item = cur.fetchone()
            if not item:
                cur.close()
                return error_response('Cart item not found', 404)
            
            item_user_id = item.get('user_id') if hasattr(item, 'get') else item[0]
            if item_user_id != user_id:
                cur.close()
                return error_response('Unauthorized', 403)
            
            if DB_ENGINE == 'mysql':
                cur.execute('DELETE FROM cart_items WHERE id=%s', (cart_item_id,))
            else:
                cur.execute('DELETE FROM cart_items WHERE id=?', (cart_item_id,))
            
            conn.commit()
            cur.close()
            return success_response(message='Item removed from cart')

        elif request.method == 'PUT':
            # Update cart item quantity - ensure it belongs to current user
            data = request.get_json(silent=True) or {}
            new_qty = int(data.get('quantity', 1))
            
            if new_qty < 1:
                return error_response('Quantity must be at least 1', 400)
            
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT user_id, product_id FROM cart_items WHERE id=%s', (cart_item_id,))
            else:
                cur.execute('SELECT user_id, product_id FROM cart_items WHERE id=?', (cart_item_id,))
            
            item = cur.fetchone()
            if not item:
                cur.close()
                return error_response('Cart item not found', 404)
            
            item_user_id = item.get('user_id') if hasattr(item, 'get') else item[0]
            product_id = item.get('product_id') if hasattr(item, 'get') else item[1]
            
            if item_user_id != user_id:
                cur.close()
                return error_response('Unauthorized', 403)
            
            # Check product stock
            if DB_ENGINE == 'mysql':
                cur.execute('SELECT stock FROM products WHERE id=%s', (product_id,))
            else:
                cur.execute('SELECT stock FROM products WHERE id=?', (product_id,))
            
            prod = cur.fetchone()
            if prod:
                stock = prod.get('stock') if hasattr(prod, 'get') else prod[0]
                if new_qty > stock:
                    cur.close()
                    return error_response(f'Only {stock} items in stock', 400)
            
            # Update quantity
            if DB_ENGINE == 'mysql':
                cur.execute('UPDATE cart_items SET quantity=%s, updated_at=NOW() WHERE id=%s', (new_qty, cart_item_id))
            else:
                cur.execute('UPDATE cart_items SET quantity=?, updated_at=? WHERE id=?', (new_qty, datetime.utcnow().isoformat(), cart_item_id))
            
            conn.commit()
            cur.close()
            return success_response(message='Cart updated')
    
    except Exception as e:
        app.logger.error(f'Cart item operation error: {e}')
        return error_response('Server error', 500)


@app.route('/api/orders/<int:order_id>/track', methods=['GET'])
def api_track_order(order_id):
    """Track order status and delivery."""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM orders WHERE id=%s;", (order_id,))
        else:
            cur.execute("SELECT * FROM orders WHERE id=?;", (order_id,))
        
        order = cur.fetchone()
        cur.close()
        
        if not order:
            return error_response('Order not found', 404)
        
        order_dict = format_row(order)
        
        # Get order items
        cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM order_items WHERE order_id=%s;", (order_id,))
        else:
            cur.execute("SELECT * FROM order_items WHERE order_id=?;", (order_id,))
        
        items = cur.fetchall()
        cur.close()
        
        order_dict['items'] = format_rows(items)
        
        return success_response(order_dict)
    
    except Exception as e:
        print(f"Error tracking order {order_id}: {str(e)}")
        return error_response('Server error', 500)


# Seed products and demo users
def seed_data_with_conn(conn):
    """Seed data using provided connection (used by init_db)."""
    cur = conn.cursor()
    # Add a simple admin and a seller if they do not exist, plus sample products
    admin_email = 'admin@hub.local'
    seller_email = 'seller@hub.local'
    admin_pw = generate_password_hash('admin123')
    seller_pw = generate_password_hash('seller123')

    # Helper to query existence
    def _exists_email(email):
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT id FROM users WHERE email=%s;", (email,))
        else:
            cur.execute("SELECT id FROM users WHERE email=?;", (email,))
        r = cur.fetchone()
        if not r:
            return None
        # pymysql.DictCursor returns dict; sqlite returns tuple-like row
        try:
            return r['id']
        except Exception:
            try:
                return r[0]
            except Exception:
                return None

    admin_id = _exists_email(admin_email)
    if not admin_id:
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,created_at) VALUES (%s,%s,%s,%s,%s,%s);",
                        (admin_email, admin_pw, 'Admin', 'User', 'admin', datetime.utcnow().isoformat()))
            admin_id = cur.lastrowid
        else:
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,created_at) VALUES (?,?,?,?,?,?);",
                        (admin_email, admin_pw, 'Admin', 'User', 'admin', datetime.utcnow().isoformat()))
            admin_id = cur.lastrowid

    seller_user_id = _exists_email(seller_email)
    if not seller_user_id:
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,created_at) VALUES (%s,%s,%s,%s,%s,%s);",
                        (seller_email, seller_pw, 'Seller', 'Store', 'seller', datetime.utcnow().isoformat()))
            seller_user_id = cur.lastrowid
        else:
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,created_at) VALUES (?,?,?,?,?,?);",
                        (seller_email, seller_pw, 'Seller', 'Store', 'seller', datetime.utcnow().isoformat()))
            seller_user_id = cur.lastrowid

        # create seller profile if not existing
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO sellers (user_id,business_name,category,verified) VALUES (%s,%s,%s,1);",
                        (seller_user_id, 'My Test Store', 'Food'))
        else:
            cur.execute("INSERT INTO sellers (user_id,business_name,category,verified) VALUES (?,?,?,1);",
                        (seller_user_id, 'My Test Store', 'Food'))

    # Ensure a supplier exists
    if DB_ENGINE == 'mysql':
        cur.execute("SELECT id FROM suppliers WHERE name=%s;", ('Local Foods Inc',))
    else:
        cur.execute("SELECT id FROM suppliers WHERE name=?;", ('Local Foods Inc',))
    srow = cur.fetchone()
    if srow:
        try:
            supplier_id = srow['id']
        except Exception:
            supplier_id = srow[0]
    else:
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO suppliers (name,contact) VALUES (%s,%s);", ('Local Foods Inc','supplier@example.com'))
            supplier_id = cur.lastrowid
        else:
            cur.execute("INSERT INTO suppliers (name,contact) VALUES (?,?);", ('Local Foods Inc','supplier@example.com'))
            supplier_id = cur.lastrowid
    supplier_id = cur.lastrowid
    # sample product
    products = [
        ('Classic Cheeseburger', 'Cheesy grilled burger', 249, 20, seller_user_id, 'food', 'https://source.unsplash.com/400x300/?burger'),
        ('Bubble Milk Tea', 'Refreshing milk tea with pearls', 150, 30, seller_user_id, 'drinks', 'https://source.unsplash.com/400x300/?milktea'),
        ('Sushi Platter', 'Assorted sushi with sashimi', 499, 10, seller_user_id, 'food', 'https://source.unsplash.com/400x300/?sushi')
    ]
    for p in products:
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO products (title,description,price,stock,seller_id,category,img_url,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);",
                        (p[0], p[1], p[2], p[3], p[4], p[5], p[6], datetime.utcnow().isoformat()))
        else:
            cur.execute("INSERT INTO products (title,description,price,stock,seller_id,category,img_url,created_at) VALUES (?,?,?,?,?,?,?,?);",
                        (p[0], p[1], p[2], p[3], p[4], p[5], p[6], datetime.utcnow().isoformat()))
    try:
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try: cur.close()
        except: pass

# --- Safe audit logging helper (audit_logs table may not exist) ---
def log_audit_event(conn, target_type, target_id, action_type, reason='', admin_id=None, **kwargs):
    """Safely log audit events - gracefully handles missing audit_logs table"""
    try:
        cur = conn.cursor()
        columns = ['target_type', 'target_id', 'action_type', 'reason', 'admin_id', 'created_at']
        values = [target_type, target_id, action_type, reason, admin_id, datetime.utcnow().isoformat()]
        
        # Add optional columns if provided
        for key, val in kwargs.items():
            if key in ['duration_days', 'amount']:
                columns.append(key)
                values.append(val)
        
        col_str = ', '.join(columns)
        placeholders = ', '.join(['%s' if DB_ENGINE == 'mysql' else '?'] * len(values))
        
        if DB_ENGINE == 'mysql':
            cur.execute(f"INSERT INTO audit_logs ({col_str}) VALUES ({placeholders})", tuple(values))
        else:
            cur.execute(f"INSERT INTO audit_logs ({col_str}) VALUES ({placeholders})", tuple(values))
        
        conn.commit()
        cur.close()
    except Exception as e:
        # Silently fail if table doesn't exist - audit_logs is optional
        if "doesn't exist" not in str(e) and "no such table" not in str(e).lower():
            print(f"[WARN] Audit log error: {e}")

# --- Refresh token helpers (DB-backed) ---
def _hash_token(t):
    return hashlib.sha256(t.encode()).hexdigest()

def create_refresh_token(conn, user_id):
    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    expires_at = (datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXP_DAYS)).isoformat()
    cur = conn.cursor()
    try:
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO refresh_tokens (user_id, token_hash, expires_at, revoked, created_at) VALUES (%s,%s,%s,0,%s);",
                        (user_id, token_hash, expires_at, datetime.utcnow().isoformat()))
        else:
            cur.execute("INSERT INTO refresh_tokens (user_id, token_hash, expires_at, revoked, created_at) VALUES (?,?,?,?,?);",
                        (user_id, token_hash, expires_at, 0, datetime.utcnow().isoformat()))
        conn.commit()
        return token
    except Exception:
        try: conn.rollback()
        except: pass
        raise
    finally:
        try: cur.close()
        except: pass

def verify_refresh_token(conn, token):
    token_hash = _hash_token(token)
    cur = conn.cursor()
    try:
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM refresh_tokens WHERE token_hash=%s AND revoked=0 AND expires_at>=%s;", (token_hash, datetime.utcnow().isoformat()))
        else:
            cur.execute("SELECT * FROM refresh_tokens WHERE token_hash=? AND revoked=0 AND expires_at>=?;", (token_hash, datetime.utcnow().isoformat()))
        row = cur.fetchone()
        return row2dict(row)
    finally:
        try: cur.close()
        except: pass

def revoke_refresh_token_by_hash(conn, token):
    token_hash = _hash_token(token)
    cur = conn.cursor()
    try:
        if DB_ENGINE == 'mysql':
            cur.execute("UPDATE refresh_tokens SET revoked=1 WHERE token_hash=%s;", (token_hash,))
        else:
            cur.execute("UPDATE refresh_tokens SET revoked=1 WHERE token_hash=?;", (token_hash,))
        conn.commit()
    finally:
        try: cur.close()
        except: pass

def revoke_all_refresh_tokens_for_user(conn, user_id):
    cur = conn.cursor()
    try:
        if DB_ENGINE == 'mysql':
            cur.execute("UPDATE refresh_tokens SET revoked=1 WHERE user_id=%s;", (user_id,))
        else:
            cur.execute("UPDATE refresh_tokens SET revoked=1 WHERE user_id=?;", (user_id,))
        conn.commit()
    finally:
        try: cur.close()
        except: pass

def seed_data():
    """Seed data using new connection (used for runtime calls)."""
    conn = get_db()
    seed_data_with_conn(conn)

# Helper to convert rows to dict
def row2dict(row):
    return dict(row) if row else None

# Serve raw html from workspace root (templates not necessarily used)
@app.route('/')
def index():
    """Serve index.html from frontend directory"""
    try:
        # Try new structure: frontend/index.html
        frontend_index = os.path.join(BASE_DIR, 'frontend', 'index.html')
        if os.path.exists(frontend_index):
            return send_from_directory(os.path.join(BASE_DIR, 'frontend'), 'index.html')
        
        # Try UI_TEMPLATES_DIR if available
        if UI_TEMPLATES_DIR:
            idx = os.path.join(UI_TEMPLATES_DIR, 'index.html')
            if os.path.exists(idx):
                return send_from_directory(UI_TEMPLATES_DIR, 'index.html')
        
        # Fallback: look in BASE_DIR/templates
        templates_index = os.path.join(BASE_DIR, 'templates', 'index.html')
        if os.path.exists(templates_index):
            return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'index.html')
        
        return "Frontend index.html not found", 404
    except Exception as e:
        return f"Error serving index: {str(e)}", 500

# Serve all built pages
@app.route('/<path:filename>', methods=['GET'])
def serve_file(filename):
    """Serve static files and HTML pages from frontend directory"""
    # Skip API routes - they should be handled by blueprints
    if filename.startswith('api/'):
        return "Not Found", 404
    try:
        # Try frontend directory first (new structure)
        frontend_path = os.path.join(BASE_DIR, 'frontend', filename)
        if os.path.exists(frontend_path):
            return send_from_directory(os.path.join(BASE_DIR, 'frontend'), filename)
        
        # Try subdirectories (css/, js/)
        for subdir in ['css', 'js']:
            subdir_path = os.path.join(BASE_DIR, 'frontend', subdir, filename)
            if os.path.exists(subdir_path):
                return send_from_directory(os.path.join(BASE_DIR, 'frontend', subdir), filename)
        
        # Try UI static files
        if UI_STATIC_DIR:
            fpath = os.path.join(UI_STATIC_DIR, filename)
            if os.path.exists(fpath):
                return send_from_directory(UI_STATIC_DIR, filename)
        
        # Try UI templates (for direct HTML files)
        if UI_TEMPLATES_DIR:
            fpath = os.path.join(UI_TEMPLATES_DIR, filename)
            if os.path.exists(fpath):
                return send_from_directory(UI_TEMPLATES_DIR, filename)
        
        # Try BASE_DIR
        path = os.path.join(BASE_DIR, filename)
        if os.path.exists(path):
            return send_from_directory(BASE_DIR, filename)
        
        return "Not Found", 404
    except Exception as e:
        return f"Error serving file: {str(e)}", 500


# Serve static assets from sibling UI static folder if present
@app.route('/static/<path:filename>')
def serve_static(filename):
    if UI_STATIC_DIR:
        f = os.path.join(UI_STATIC_DIR, filename)
        if os.path.exists(f):
            return send_from_directory(UI_STATIC_DIR, filename)
    # fallback to app static
    f = os.path.join(BASE_DIR, 'static', filename)
    if os.path.exists(f):
        return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)
    return "Not Found", 404


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products from active sellers only
    Query params:
        - search: filter products by title, category, or description (optional)
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get search parameter
        search_query = request.args.get('search', '').strip()
        # Support 'q' parameter for backward compatibility
        if not search_query:
            search_query = request.args.get('q', '').strip()
        
        # Sanitize search query - remove SQL wildcard chars to prevent injection
        if search_query:
            search_query = search_query.replace('%', '').replace('_', '')
        
        # Check if date columns exist
        has_dates = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'manufacture_date'")
                has_manufacture = cursor.fetchone() is not None
                cursor.execute("SHOW COLUMNS FROM products LIKE 'expiry_date'")
                has_expiry = cursor.fetchone() is not None
                has_dates = has_manufacture and has_expiry
            else:
                cursor.execute("PRAGMA table_info('products')")
                cols = cursor.fetchall()
                col_names = [col[1] if isinstance(col, tuple) else col['name'] for col in cols]
                has_dates = 'manufacture_date' in col_names and 'expiry_date' in col_names
        except Exception as check_err:
            app.logger.warning(f'Could not check for date columns: {check_err}')
            has_dates = False
        
        # Build query based on column existence
        if has_dates:
            date_fields = 'p.manufacture_date, p.expiry_date,'
            date_field_names = 'manufacture_date', 'expiry_date',
        else:
            date_fields = ''
            date_field_names = ()
        
        # Build search filter if search query provided
        search_filter = ""
        search_params = []
        if search_query and len(search_query) >= 2:
            search_pattern = f"%{search_query}%"
            if DB_ENGINE == 'mysql':
                search_filter = " AND (p.title LIKE %s OR p.category LIKE %s OR p.description LIKE %s)"
            else:
                search_filter = " AND (p.title LIKE ? OR p.category LIKE ? OR p.description LIKE ?)"
            search_params = [search_pattern, search_pattern, search_pattern]
        
        # Only show products from verified active sellers (not suspended)
        # Include average rating and review count from reviews table
        if DB_ENGINE == 'mysql':
            if has_dates:
                q = f"""SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id, p.manufacture_date, p.expiry_date,
                           u.first_name AS seller_first_name, 
                           u.last_name AS seller_last_name,
                           s.business_name AS seller_business_name,
                           s.shop_status,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       INNER JOIN users u ON p.seller_id=u.id
                       INNER JOIN sellers s ON u.id=s.user_id
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE s.shop_status='active' 
                         AND s.verified=1 
                         AND p.stock > 0{search_filter}
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id, p.manufacture_date, p.expiry_date,
                                u.first_name, u.last_name, s.business_name, s.shop_status
                       ORDER BY p.created_at DESC;"""
            else:
                q = f"""SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id,
                           u.first_name AS seller_first_name, 
                           u.last_name AS seller_last_name,
                           s.business_name AS seller_business_name,
                           s.shop_status,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       INNER JOIN users u ON p.seller_id=u.id
                       INNER JOIN sellers s ON u.id=s.user_id
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE s.shop_status='active' 
                         AND s.verified=1 
                         AND p.stock > 0{search_filter}
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id,
                                u.first_name, u.last_name, s.business_name, s.shop_status
                       ORDER BY p.created_at DESC;"""
        else:
            if has_dates:
                q = f"""SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id, p.manufacture_date, p.expiry_date,
                           u.first_name AS seller_first_name, 
                           u.last_name AS seller_last_name,
                           s.business_name AS seller_business_name,
                           s.shop_status,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       INNER JOIN users u ON p.seller_id=u.id
                       INNER JOIN sellers s ON u.id=s.user_id
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE s.shop_status='active' 
                         AND s.verified=1 
                         AND p.stock > 0{search_filter}
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id, p.manufacture_date, p.expiry_date,
                                u.first_name, u.last_name, s.business_name, s.shop_status
                       ORDER BY p.created_at DESC;"""
            else:
                q = f"""SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id,
                           u.first_name AS seller_first_name, 
                           u.last_name AS seller_last_name,
                           s.business_name AS seller_business_name,
                           s.shop_status,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       INNER JOIN users u ON p.seller_id=u.id
                       INNER JOIN sellers s ON u.id=s.user_id
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE s.shop_status='active' 
                         AND s.verified=1 
                         AND p.stock > 0{search_filter}
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id,
                                u.first_name, u.last_name, s.business_name, s.shop_status
                       ORDER BY p.created_at DESC;"""
        
        # Execute query with search parameters if present
        if search_params:
            cursor.execute(q, tuple(search_params))
        else:
            cursor.execute(q)
        rows = cursor.fetchall() or []
        
        # Format results
        products = []
        base_fields = ['id', 'title', 'description', 'price', 'stock', 'category',
                      'img_url', 'created_at', 'seller_id']
        if has_dates:
            field_names = base_fields + list(date_field_names) + ['seller_first_name',
                      'seller_last_name', 'seller_business_name', 'shop_status', 'average_rating', 'review_count']
        else:
            field_names = base_fields + ['seller_first_name',
                      'seller_last_name', 'seller_business_name', 'shop_status', 'average_rating', 'review_count']
        
        for row in rows:
            try:
                if hasattr(row, 'keys'):
                    product = row2dict(row)
                else:
                    product = dict(zip(field_names, row))
                
                # Add seller_store_name as alias for seller_business_name
                product['seller_store_name'] = product.get('seller_business_name')
                
                # Normalize category to match frontend filters
                if product.get('category'):
                    cat = product['category'].lower().strip()
                    # Map variations to standard categories
                    category_map = {
                        'baking': 'baking',
                        'coffee': 'coffee',
                        'tea': 'coffee',
                        'coffee & tea': 'coffee',
                        'snacks': 'snacks',
                        'specialty': 'specialty',
                        'organic': 'organic',
                        'meal kits': 'mealkits',
                        'mealkits': 'mealkits',
                        'meal kit': 'mealkits'
                    }
                    product['category_normalized'] = category_map.get(cat, cat)
                
                # Add image_urls array
                product_id = product.get('id')
                if product_id:
                    product['image_urls'] = get_product_images(cursor, product_id)
                    # Keep img_url for backward compatibility if not set
                    if not product.get('img_url') and product['image_urls']:
                        product['img_url'] = product['image_urls'][0]
                
                # Ensure average_rating and review_count are properly formatted
                product['average_rating'] = float(product.get('average_rating', 0) or 0)
                product['review_count'] = int(product.get('review_count', 0) or 0)
                
                products.append(product)
            except Exception as row_err:
                app.logger.warning(f'Error processing product row: {row_err}')
                continue
        
        cursor.close()
        return success_response(products, f'{len(products)} products found')
    except Exception as e:
        app.logger.error('get_products error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return success_response([], 'Error loading products')


@app.route('/api/sellers/<int:seller_id>/products', methods=['GET'])
def get_seller_products(seller_id):
    """Get all products from a specific seller - Public endpoint
    Query params:
        - store: filter by store_id (optional)
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Get store_id from query parameter if provided
        store_id = request.args.get('store', type=int)
        
        # Get seller's user_id first
        if DB_ENGINE == 'mysql':
            cur.execute('SELECT user_id FROM sellers WHERE id = %s', (seller_id,))
        else:
            cur.execute('SELECT user_id FROM sellers WHERE id = ?', (seller_id,))
        
        seller_row = cur.fetchone()
        if not seller_row:
            return error_response('Seller not found', 404)
        
        user_id = seller_row['user_id'] if isinstance(seller_row, dict) else seller_row[0]
        
        # Check if store_id column exists in products table
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cur.fetchone() is not None
            else:
                cur.execute("PRAGMA table_info('products')")
                cols = cur.fetchall()
                col_names = [col[1] if isinstance(col, tuple) else col.get('name', '') for col in cols]
                store_id_column_exists = 'store_id' in col_names
        except Exception as e:
            app.logger.warning(f'Could not check for store_id column: {e}')
            store_id_column_exists = False
        
        # Build query with optional store_id filter
        if store_id and store_id_column_exists:
            # Filter products by store_id
            if DB_ENGINE == 'mysql':
                query = """SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE p.seller_id = %s AND p.store_id = %s
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id
                       ORDER BY p.created_at DESC"""
                cur.execute(query, (user_id, store_id))
            else:
                query = """SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE p.seller_id = ? AND p.store_id = ?
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id
                       ORDER BY p.created_at DESC"""
                cur.execute(query, (user_id, store_id))
        else:
            # Get all products for this seller (no store filter)
            if DB_ENGINE == 'mysql':
                query = """SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE p.seller_id = %s
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id
                       ORDER BY p.created_at DESC"""
                cur.execute(query, (user_id,))
            else:
                query = """SELECT 
                           p.id, p.title, p.description, p.price, p.stock, p.category, 
                           p.img_url, p.created_at, p.seller_id,
                           COALESCE(AVG(r.rating), 0) AS average_rating,
                           COUNT(r.id) AS review_count
                       FROM products p 
                       LEFT JOIN reviews r ON p.id = r.product_id AND r.product_id IS NOT NULL
                       WHERE p.seller_id = ?
                       GROUP BY p.id, p.title, p.description, p.price, p.stock, p.category, 
                                p.img_url, p.created_at, p.seller_id
                       ORDER BY p.created_at DESC"""
                cur.execute(query, (user_id,))
        
        rows = cur.fetchall()
        
        # Format results
        products = []
        for row in rows:
            if isinstance(row, dict):
                product = dict(row)
            else:
                # Handle tuple result with additional fields
                product = dict(zip([
                    'id', 'title', 'description', 'price', 'stock', 'category',
                    'img_url', 'created_at', 'seller_id', 'average_rating', 'review_count'
                ], row))
            
            # Convert rating and review count to proper types
            product['average_rating'] = float(product.get('average_rating', 0) or 0)
            product['review_count'] = int(product.get('review_count', 0) or 0)
            
            # Add image_urls array (cursor still open)
            product_id = product.get('id')
            if product_id:
                product['image_urls'] = get_product_images(cur, product_id)
                # Keep img_url for backward compatibility if not set
                if not product.get('img_url') and product['image_urls']:
                    product['img_url'] = product['image_urls'][0]
            
            products.append(product)
        
        cur.close()
        
        return success_response(products, f'{len(products)} products found')
    except Exception as e:
        app.logger.error('get_seller_products error: %s', e)
        return error_response(str(e), 500)


@app.route('/api/health')
def api_health():
    """Basic health check endpoint - enhanced version"""
    try:
        # Test database connection
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        
        return jsonify({
            'ok': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'server_instance': SERVER_INSTANCE_ID
        })
    except Exception as e:
        app.logger.error('health check failed: %s', e)
        return jsonify({
            'ok': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/products/<int:pid>', methods=['GET'])
def api_product(pid):
    try:
        conn = get_db(); cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM products WHERE id=%s;", (pid,))
        else:
            cur.execute("SELECT * FROM products WHERE id=?;", (pid,))
        p = row2dict(cur.fetchone())
        
        # Add image_urls array
        if p and p.get('id'):
            p['image_urls'] = get_product_images(cur, p['id'])
            # Keep img_url for backward compatibility if not set
            if not p.get('img_url') and p['image_urls']:
                p['img_url'] = p['image_urls'][0]
        
        cur.close()
    except Exception as e:
        app.logger.error('api_product error: %s', e)
        return jsonify({'error':'server_error'}), 500
    if not p:
        return jsonify({'error':'Not Found'}), 404
    return jsonify(p)

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    body = request.json or {}
    email = body.get('email')
    password = body.get('password')
    role = body.get('role','customer')
    first = body.get('first_name','')
    last = body.get('last_name','')
    if not email or not password:
        return jsonify({'error':'missing email or password'}), 400

    ok, msg = validate_email(email)
    if not ok:
        return jsonify({'error':'validation', 'field':'email', 'message': msg}), 400

    ok, msg = validate_password(password)
    if not ok:
        return jsonify({'error':'validation', 'field':'password', 'message': msg}), 400

    if first:
        ok, msg = validate_name(first, 'First name')
        if not ok:
            return jsonify({'error':'validation', 'field':'first_name', 'message': msg}), 400
    if last:
        ok, msg = validate_name(last, 'Last name')
        if not ok:
            return jsonify({'error':'validation', 'field':'last_name', 'message': msg}), 400
    try:
        conn = get_db(); cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT id FROM users WHERE email=%s;", (email,))
        else:
            cur.execute("SELECT id FROM users WHERE email=?;", (email,))
        if cur.fetchone():
            cur.close()
            return jsonify({'error':'User exists'}), 400
        
        # Generate OTP and store in database
        otp_code = generate_otp()
        pw_hash = generate_password_hash(password)
        
        # Create user as unverified (is_verified=0) with OTP stored
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,otp_code,is_verified,created_at) VALUES (%s,%s,%s,%s,%s,%s,0,%s);",
                        (email,pw_hash,first,last,role,otp_code,datetime.utcnow().isoformat()))
        else:
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,otp_code,is_verified,created_at) VALUES (?,?,?,?,?,?,0,?);",
                        (email,pw_hash,first,last,role,otp_code,datetime.utcnow().isoformat()))
        uid = cur.lastrowid

        if role=='seller':
            # Check if seller approval is required
            approval_required = True  # Default to required
            try:
                if DB_ENGINE == 'mysql':
                    cur.execute("SELECT setting_value FROM platform_settings WHERE setting_key = 'seller_approval_required'")
                else:
                    cur.execute("SELECT setting_value FROM platform_settings WHERE setting_key = 'seller_approval_required'")
                approval_setting = cur.fetchone()
                if approval_setting:
                    approval_setting = format_row(approval_setting)
                    approval_required = approval_setting.get('setting_value') == '1'
            except:
                # If setting doesn't exist, default to required
                pass
            
            # Set status based on approval requirement
            shop_status = 'active' if not approval_required else 'pending'
            verified = 1 if not approval_required else 0
            
            if DB_ENGINE == 'mysql':
                cur.execute("INSERT INTO sellers (user_id,business_name,category,verified,shop_status) VALUES (%s,%s,%s,%s,%s);",
                            (uid, body.get('business_name',''), body.get('category',''), verified, shop_status))
            else:
                cur.execute("INSERT INTO sellers (user_id,business_name,category,verified,shop_status) VALUES (?,?,?,?,?);",
                            (uid, body.get('business_name',''), body.get('category',''), verified, shop_status))
        if role=='rider':
            if DB_ENGINE == 'mysql':
                cur.execute("INSERT INTO riders (user_id,vehicle_type,driver_license,verified,rider_status) VALUES (%s,%s,%s,0,'pending');",
                            (uid, body.get('vehicle_type',''), body.get('driver_license','')))
            else:
                cur.execute("INSERT INTO riders (user_id,vehicle_type,driver_license,verified,rider_status) VALUES (?,?,?,0,'pending');",
                            (uid, body.get('vehicle_type',''), body.get('driver_license','')))
        conn.commit()
        
        # Send OTP email
        send_otp_email(email, otp_code, role)
        
        cur.close()
        # Generate JWT token for new user (unverified)
        token = generate_token(uid, role, email)
        
        # Create refresh token with fresh connection
        try:
            refresh_conn = get_db()
            refresh_token = create_refresh_token(refresh_conn, uid)
        except Exception as rte:
            print(f"[WARN] Failed to create refresh token during registration: {rte}")
            refresh_token = None
        
        return jsonify({
            'success': True,
            'token': token,
            'refresh_token': refresh_token,
            'user_id': uid,
            'message': 'Registration successful. Please verify your email with the OTP sent.',
            'user': {
                'id': uid,
                'email': email,
                'first_name': first,
                'role': role,
                'is_verified': False
            }
        })
    except Exception as e:
        app.logger.error('register error: %s', e)
        try:
            conn.rollback()
        except: pass
        try: cur.close()
        except: pass
        return jsonify({'error':'server_error'}), 500


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    body = request.json or {}
    email = body.get('email')
    password = body.get('password')
    if not email or not password:
        return jsonify({'error':'Missing email or password'}), 400
    try:
        conn = get_db(); cur = conn.cursor();
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM users WHERE email=%s;", (email,))
        else:
            cur.execute("SELECT * FROM users WHERE email=?;", (email,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            return jsonify({'error':'Invalid credentials'}), 401
            
        # Convert to dict format
        user = format_row(user)
        
        if not check_password_hash(user.get('password_hash'), password):
            cur.close()
            return jsonify({'error':'Invalid credentials'}), 401
        
        user_id = user.get('id')
        user_role = user.get('role')
        
        # Check seller approval status
        if user_role == 'seller':
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT shop_status FROM sellers WHERE user_id=%s;", (user_id,))
            else:
                cur.execute("SELECT shop_status FROM sellers WHERE user_id=?;", (user_id,))
            
            seller_row = cur.fetchone()
            if seller_row:
                seller_status = format_row(seller_row).get('shop_status')
                
                # Block login if not approved
                if seller_status != 'active':
                    cur.close()
                    if seller_status == 'pending':
                        return jsonify({
                            'error': 'account_pending',
                            'message': 'Your seller account is not approved yet. Please wait for admin verification.'
                        }), 403
                    elif seller_status == 'declined':
                        return jsonify({
                            'error': 'account_declined',
                            'message': 'Your seller account has been declined. Please contact support for more information.'
                        }), 403
                    else:
                        return jsonify({
                            'error': 'account_inactive',
                            'message': 'Your seller account is not active. Please contact support.'
                        }), 403
        
        # Check rider approval status
        if user_role == 'rider':
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT rider_status FROM riders WHERE user_id=%s;", (user_id,))
            else:
                cur.execute("SELECT rider_status FROM riders WHERE user_id=?;", (user_id,))
            rider_row = cur.fetchone()
            if rider_row:
                rider_status = format_row(rider_row).get('rider_status')
                
                # Block login if not approved
                if rider_status != 'active':
                    cur.close()
                    if rider_status == 'pending':
                        return jsonify({
                            'error': 'account_pending',
                            'message': 'Your rider account is not approved yet. Please wait for admin verification.'
                        }), 403
                    elif rider_status == 'declined':
                        return jsonify({
                            'error': 'account_declined',
                            'message': 'Your rider account has been declined. Please contact support for more information.'
                        }), 403
                    else:
                        return jsonify({
                            'error': 'account_inactive',
                            'message': 'Your rider account is not active. Please contact support.'
                        }), 403
        
        # Update last_login timestamp
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
            else:
                cur.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user_id,))
            conn.commit()
        except Exception as login_update_err:
            app.logger.warning(f'Could not update last_login: {login_update_err}')
            # Non-fatal, continue with login
        
        cur.close()
        
    except Exception as e:
        app.logger.error('login error: %s', e)
        return jsonify({'error':'server_error'}), 500
    
    # Generate JWT token
    user_email = user.get('email')
    token = generate_token(user_id, user_role, user_email)
    # Create refresh token and store it
    try:
        refresh = create_refresh_token(get_db(), user_id)
    except Exception:
        refresh = None
    # set session for backward compatibility
    session['user_id'] = user_id
    session['role'] = user_role
    return jsonify({
        'success': True,
        'token': token,
        'refresh_token': refresh,
        'user': {
            'id': user_id,
            'email': user_email,
            'first_name': user.get('first_name'),
            'role': user_role
        }
    })


@app.route('/api/auth/send-otp', methods=['POST'])
def api_send_otp():
    body = request.json or {}
    email = body.get('email')
    user_type = body.get('type','customer')
    if not email:
        return jsonify({'error':'Missing email'}), 400
    try:
        conn = get_db(); cur = conn.cursor()
        
        # Check if user exists
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT id FROM users WHERE email=%s;", (email,))
        else:
            cur.execute("SELECT id FROM users WHERE email=?;", (email,))
        
        user_row = cur.fetchone()
        if not user_row:
            cur.close()
            return jsonify({'error':'User not found'}), 404
        
        # Generate new OTP and update in database
        code = generate_otp()
        if DB_ENGINE == 'mysql':
            cur.execute("UPDATE users SET otp_code=%s WHERE email=%s;", (code, email))
        else:
            cur.execute("UPDATE users SET otp_code=? WHERE email=?;", (code, email))
        
        conn.commit()
        cur.close()
        
        # Send OTP email
        send_otp_email(email, code, user_type)
        
        return jsonify({'success': True, 'message': 'OTP sent to your email'})
    except Exception as e:
        app.logger.error('send_otp error: %s', e)
        return jsonify({'error':'server_error'}), 500


@app.route('/api/auth/verify-otp', methods=['POST'])
def api_verify_otp():
    body = request.json or {}
    email = body.get('email', '').strip().lower()
    code = str(body.get('code', '')).strip()
    if not email or not code:
        return jsonify({'error':'Missing parameters'}), 400
    
    try:
        conn = get_db(); cur = conn.cursor()
        
        # Fetch user and their stored OTP
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT id, otp_code, is_verified FROM users WHERE email=%s;", (email,))
        else:
            cur.execute("SELECT id, otp_code, is_verified FROM users WHERE email=?;", (email,))
        
        user_row = cur.fetchone()
        if not user_row:
            cur.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        user_dict = row2dict(user_row) if hasattr(user_row, 'keys') else dict(zip(['id', 'otp_code', 'is_verified'], user_row))
        stored_otp = str(user_dict.get('otp_code', '')).strip() if user_dict.get('otp_code') else None
        user_id = user_dict.get('id')
        
        # Check if OTP matches (case-insensitive, trimmed comparison)
        if not stored_otp or stored_otp != code:
            cur.close()
            return jsonify({'success': False, 'error': 'Invalid OTP'}), 400
        
        # Mark user as verified and clear OTP
        if DB_ENGINE == 'mysql':
            cur.execute("UPDATE users SET is_verified=1, otp_code=NULL WHERE id=%s;", (user_id,))
        else:
            cur.execute("UPDATE users SET is_verified=1, otp_code=NULL WHERE id=?;", (user_id,))
        
        conn.commit()
        cur.close()
        
        return jsonify({'success': True, 'message': 'Email verified successfully'})
    except Exception as e:
        app.logger.error('verify_otp error: %s', e)
        try: conn.rollback()
        except: pass
        return jsonify({'error':'server_error'}), 500

@app.route('/api/orders', methods=['POST'])
@token_required
def api_create_order():
    body = request.json or {}
    # expected: {customer: {name, phone, address}, items: [{title, price, quantity, product_id}], payment, delivery}
    items = body.get('items', [])
    customer = body.get('customer', {})
    payment = body.get('payment', 'Cash on Delivery')
    delivery = body.get('delivery', 50)

    # Get customer_id from token
    token = get_token_from_request()
    payload = verify_token(token)
    customer_id = payload.get('user_id') if payload else None

    if not items:
        return jsonify({'error':'No items in order', 'success': False}), 400
    
    # Validate customer data - accept either full name or separate name components
    customer_name = customer.get('name') or ' '.join(filter(None, [
        customer.get('first_name', ''),
        customer.get('middle_name', ''),
        customer.get('last_name', ''),
        customer.get('suffix', '')
    ])).strip()
    
    if not customer_name or not customer.get('phone') or not customer.get('address'):
        return jsonify({'error':'Missing customer information (name, phone, or address)', 'success': False}), 400
    
    # Build comprehensive address string with all components
    address_parts = [
        customer.get('address_line1', ''),
        customer.get('address_line2', ''),
        customer.get('city', ''),
        customer.get('province', ''),
        customer.get('region', ''),
        customer.get('postal_code', '')
    ]
    # Use provided address if available, otherwise build from components
    full_address = customer.get('address') or ', '.join(filter(None, address_parts))
    
    # Store additional customer info as JSON in customer_address for detailed access
    import json
    customer_details = {
        'first_name': customer.get('first_name'),
        'middle_name': customer.get('middle_name'),
        'last_name': customer.get('last_name'),
        'suffix': customer.get('suffix'),
        'email': customer.get('email'),
        'phone': customer.get('phone'),
        'address_line1': customer.get('address_line1'),
        'address_line2': customer.get('address_line2'),
        'region': customer.get('region'),
        'province': customer.get('province'),
        'city': customer.get('city'),
        'postal_code': customer.get('postal_code'),
        'full_address': full_address,
        'notes': customer.get('notes')
    }
    customer_address_json = json.dumps(customer_details)
    
    try:
        conn = get_db(); cur = conn.cursor()
        # begin transaction
        if DB_ENGINE == 'mysql':
            conn.begin()
        # Create order - store full address in customer_address, JSON details appended
        subtotal = sum((i.get('price',0) * i.get('quantity',1) for i in items))
        total = subtotal + delivery
        # Store address with JSON details appended (separated by ||| for parsing)
        address_with_details = f"{full_address}|||{customer_address_json}"
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO orders (customer_id,customer_name,customer_phone,customer_address,subtotal,delivery_fee,total,payment,status,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",
                        (customer_id, customer_name, customer.get('phone'), address_with_details, subtotal, delivery, total, payment, 'placed', datetime.utcnow().isoformat()))
        else:
            cur.execute("INSERT INTO orders (customer_id,customer_name,customer_phone,customer_address,subtotal,delivery_fee,total,payment,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?);",
                        (customer_id, customer_name, customer.get('phone'), address_with_details, subtotal, delivery, total, payment, 'placed', datetime.utcnow().isoformat()))
        order_id = cur.lastrowid

        # Create items and adjust stock
        for it in items:
            pid = it.get('product_id')
            variation_id = it.get('variation_id')  # NEW: Support variations
            
            # If product_id is missing, try to look it up by title
            if not pid and it.get('title'):
                title = it.get('title')
                if DB_ENGINE == 'mysql':
                    cur.execute("SELECT id FROM products WHERE title=%s LIMIT 1;", (title,))
                else:
                    cur.execute("SELECT id FROM products WHERE title=? LIMIT 1;", (title,))
                row = cur.fetchone()
                if row:
                    if isinstance(row, dict) or hasattr(row, 'keys'):
                        pid = dict(row).get('id') if hasattr(row, 'keys') else row.get('id')
                    else:
                        pid = row[0] if len(row) > 0 else None
            
            qty = int(it.get('quantity',1))
            price = it.get('price',0)
            
            # Prepare variation details for storage
            variation_details = None
            if variation_id:
                if DB_ENGINE == 'mysql':
                    cur.execute("""
                        SELECT variation_type, variation_value, price_adjustment 
                        FROM product_variation_options WHERE id = %s
                    """, (variation_id,))
                else:
                    cur.execute("""
                        SELECT variation_type, variation_value, price_adjustment 
                        FROM product_variation_options WHERE id = ?
                    """, (variation_id,))
                var_row = cur.fetchone()
                if var_row:
                    import json
                    # Handle both dict and tuple results
                    if isinstance(var_row, dict) or hasattr(var_row, 'keys'):
                        var_dict = dict(var_row) if hasattr(var_row, 'keys') else var_row
                        variation_details = json.dumps({
                            'variation_type': var_dict.get('variation_type', ''),
                            'variation_value': var_dict.get('variation_value', ''),
                            'price_adjustment': float(var_dict.get('price_adjustment', 0) or 0)
                        })
                    else:
                        variation_details = json.dumps({
                            'variation_type': var_row[0] if len(var_row) > 0 else '',
                            'variation_value': var_row[1] if len(var_row) > 1 else '',
                            'price_adjustment': float(var_row[2] if len(var_row) > 2 and var_row[2] else 0)
                        })
            
            # Insert order item with variation support
            # Check if variation columns exist in order_items table
            try:
                if DB_ENGINE == 'mysql':
                    cur.execute("SHOW COLUMNS FROM order_items LIKE 'variation_id'")
                    has_variation_cols = cur.fetchone() is not None
                else:
                    cur.execute("PRAGMA table_info(order_items)")
                    columns = cur.fetchall()
                    has_variation_cols = any(col[1] == 'variation_id' for col in columns)
                
                if has_variation_cols:
                    # Table has variation columns, use them
                    if DB_ENGINE == 'mysql':
                        cur.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, price, variation_id, variation_details) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (order_id, pid, qty, price, variation_id, variation_details))
                    else:
                        cur.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, price, variation_id, variation_details) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (order_id, pid, qty, price, variation_id, variation_details))
                else:
                    # Table doesn't have variation columns, insert without them
                    if DB_ENGINE == 'mysql':
                        cur.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, price) 
                            VALUES (%s, %s, %s, %s)
                        """, (order_id, pid, qty, price))
                    else:
                        cur.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, price) 
                            VALUES (?, ?, ?, ?)
                        """, (order_id, pid, qty, price))
            except Exception as insert_error:
                # Fallback: try without variation columns
                app.logger.warning(f"Error inserting order item with variations, trying without: {insert_error}")
                try:
                    if DB_ENGINE == 'mysql':
                        cur.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, price) 
                            VALUES (%s, %s, %s, %s)
                        """, (order_id, pid, qty, price))
                    else:
                        cur.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, price) 
                            VALUES (?, ?, ?, ?)
                        """, (order_id, pid, qty, price))
                except Exception as fallback_error:
                    app.logger.error(f"Failed to insert order item even without variations: {fallback_error}")
                    raise
            
            # Reduce inventory
            if pid:
                if variation_id:
                    # Deduct from variation stock
                    if DB_ENGINE == 'mysql':
                        cur.execute("UPDATE product_variation_options SET stock = stock - %s WHERE id = %s", (qty, variation_id))
                        # Try to insert into inventory_movements_variations if table exists
                        try:
                            cur.execute("""
                                INSERT INTO inventory_movements_variations (variation_id, qty, movement_type, ref, created_at) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, (variation_id, -qty, 'sale', f'order:{order_id}', datetime.utcnow().isoformat()))
                        except Exception as inv_err:
                            # Table might not exist, log and continue
                            app.logger.warning(f"Could not insert into inventory_movements_variations: {inv_err}")
                    else:
                        cur.execute("UPDATE product_variation_options SET stock = stock - ? WHERE id = ?", (qty, variation_id))
                        # Try to insert into inventory_movements_variations if table exists
                        try:
                            cur.execute("""
                                INSERT INTO inventory_movements_variations (variation_id, qty, movement_type, ref, created_at) 
                                VALUES (?, ?, ?, ?, ?)
                            """, (variation_id, -qty, 'sale', f'order:{order_id}', datetime.utcnow().isoformat()))
                        except Exception as inv_err:
                            # Table might not exist, log and continue
                            app.logger.warning(f"Could not insert into inventory_movements_variations: {inv_err}")
                else:
                    # Deduct from base product stock
                    if DB_ENGINE == 'mysql':
                        cur.execute("UPDATE products SET stock = stock - %s WHERE id=%s;", (qty, pid))
                    else:
                        cur.execute("UPDATE products SET stock = stock - ? WHERE id=?;", (qty, pid))
                    
                    # Try to insert into inventory_movements if table exists
                    try:
                        if DB_ENGINE == 'mysql':
                            cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (%s,%s,%s,%s,%s);",
                                        (pid, -qty, 'sale', f'order:{order_id}', datetime.utcnow().isoformat()))
                        else:
                            cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (?,?,?,?,?);",
                                        (pid, -qty, 'sale', f'order:{order_id}', datetime.utcnow().isoformat()))
                    except Exception as inv_err:
                        # Table might not exist, log and continue
                        app.logger.warning(f"Could not insert into inventory_movements: {inv_err}")
                # If stock low, create automatic purchase order to supplier (ERP automation)
                # Only do this if suppliers table exists and we have at least one supplier
                try:
                    if DB_ENGINE == 'mysql':
                        cur.execute("SELECT stock FROM products WHERE id=%s;", (pid,))
                    else:
                        cur.execute("SELECT stock FROM products WHERE id=?;", (pid,))
                    row = cur.fetchone()
                    if row:
                        if isinstance(row, dict) or hasattr(row, 'keys'):
                            stock = row.get('stock', 0) if isinstance(row, dict) else row['stock']
                        else:
                            stock = row[0] if len(row) > 0 else 0
                    else:
                        stock = 0
                    
                    # Check if suppliers table exists and has suppliers before creating PO
                    if stock < 10:
                        if DB_ENGINE == 'mysql':
                            cur.execute("SELECT COUNT(*) FROM suppliers LIMIT 1")
                        else:
                            cur.execute("SELECT COUNT(*) FROM suppliers LIMIT 1")
                        supplier_count = cur.fetchone()
                        has_suppliers = supplier_count and (supplier_count[0] if isinstance(supplier_count, tuple) else supplier_count.get('COUNT(*)', 0) if isinstance(supplier_count, dict) else 0) > 0
                        
                        if has_suppliers:
                            if DB_ENGINE == 'mysql':
                                cur.execute("INSERT INTO purchase_orders (supplier_id,status,created_at) VALUES (%s,%s,%s);", (1, 'draft', datetime.utcnow().isoformat()))
                            else:
                                cur.execute("INSERT INTO purchase_orders (supplier_id,status,created_at) VALUES (?,?,?);", (1, 'draft', datetime.utcnow().isoformat()))
                            po_id = cur.lastrowid
                            if DB_ENGINE == 'mysql':
                                cur.execute("INSERT INTO purchase_order_items (po_id,product_id,quantity,price) VALUES (%s,%s,%s,%s);", (po_id, pid, 50, price*0.8))
                            else:
                                cur.execute("INSERT INTO purchase_order_items (po_id,product_id,quantity,price) VALUES (?,?,?,?);", (po_id, pid, 50, price*0.8))
                            if DB_ENGINE == 'mysql':
                                cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (%s,%s,%s,%s,%s);",
                                            (pid, 50, 'purchase', f'po:{po_id}', datetime.utcnow().isoformat()))
                            else:
                                cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (?,?,?,?,?);",
                                            (pid, 50, 'purchase', f'po:{po_id}', datetime.utcnow().isoformat()))
                except Exception as po_error:
                    # Don't fail order creation if purchase order creation fails
                    app.logger.warning(f"Could not create purchase order for low stock: {po_error}")
        conn.commit()
        if 'cur' in locals():
            cur.close()
        return jsonify({'success':True, 'order_id':order_id, 'total': total, 'message': 'Order created successfully'})
    except Exception as e:
        app.logger.error('create order failed: %s', e)
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(error_trace)
        try:
            if 'conn' in locals():
                conn.rollback()
        except Exception as rollback_err:
            app.logger.error(f"Rollback failed: {rollback_err}")
        try:
            if 'cur' in locals():
                cur.close()
        except: pass
        # Get proper error message
        error_msg = 'Unknown error'
        try:
            if hasattr(e, 'args') and e.args:
                for arg in e.args:
                    if arg and str(arg) and str(arg) != '0':
                        error_msg = str(arg)
                        break
                if error_msg == 'Unknown error':
                    error_msg = str(e.args[0]) if len(e.args) > 0 else str(e)
            elif hasattr(e, 'message'):
                error_msg = str(e.message)
            else:
                error_msg = str(e) if e else 'Unknown error'
        except:
            error_msg = f"Error type: {type(e).__name__}"
        return jsonify({'error': error_msg, 'success': False}), 500


@app.route('/api/auth/refresh', methods=['POST'])
def api_auth_refresh():
    body = request.json or {}
    refresh_token = body.get('refresh_token')
    if not refresh_token:
        return jsonify({'error':'missing_refresh_token'}), 400
    try:
        conn = get_db()
        row = verify_refresh_token(conn, refresh_token)
        if not row:
            return jsonify({'error':'invalid_or_expired_refresh_token'}), 401
        user_id = row.get('user_id')
        # fetch user to construct new access token
        cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM users WHERE id=%s;", (user_id,))
        else:
            cur.execute("SELECT * FROM users WHERE id=?;", (user_id,))
        u = cur.fetchone()
        cur.close()
        if not u:
            return jsonify({'error':'user_not_found'}), 404
        u = row2dict(u)
        # revoke old refresh token and rotate
        try:
            revoke_refresh_token_by_hash(conn, refresh_token)
        except Exception:
            pass
        new_refresh = create_refresh_token(conn, user_id)
        new_access = generate_token(u['id'], u['role'], u['email'])
        return jsonify({'token': new_access, 'refresh_token': new_refresh})
    except Exception as e:
        app.logger.error('refresh token error: %s', e)
        return jsonify({'error':'server_error'}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    body = request.json or {}
    refresh_token = body.get('refresh_token')
    # If a refresh token provided, revoke it
    try:
        conn = get_db()
        if refresh_token:
            revoke_refresh_token_by_hash(conn, refresh_token)
            return jsonify({'success':True})
        # optionally revoke all tokens if access token provided
        token = None
        auth_header = request.headers.get('Authorization','')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        if token:
            payload = verify_token(token)
            if payload:
                revoke_all_refresh_tokens_for_user(conn, payload.get('user_id'))
                return jsonify({'success':True})
        return jsonify({'error':'no_token_provided'}), 400
    except Exception as e:
        app.logger.error('logout error: %s', e)
        return jsonify({'error':'server_error'}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['POST'])
@token_required
def api_update_order_status(order_id):
    """Update order status - allows sellers, customers, and admins"""
    try:
        token = get_token_from_request()
        payload = verify_token(token)
        if not payload:
            return error_response('Unauthorized', 401)
        
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        body = request.json or {}
        new_status = body.get('status')
        notes = body.get('notes')
        
        # Validate and normalize status
        if not new_status or (isinstance(new_status, str) and not new_status.strip()):
            return jsonify({'error':'Status cannot be empty', 'success': False}), 400
        
        # Trim whitespace
        new_status = new_status.strip() if isinstance(new_status, str) else new_status
        
        # Validate status
        valid_statuses = ('placed', 'pending', 'processing', 'ready', 'dispatched', 'in-transit', 'shipped', 'delivered', 'completed', 'cancelled')
        if new_status not in valid_statuses:
            return jsonify({'error':'Invalid status', 'success': False}), 400
        
        conn = get_db()
        cur = conn.cursor()
        
        # Verify order exists and user has permission
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT customer_id FROM orders WHERE id=%s", (order_id,))
        else:
            cur.execute("SELECT customer_id FROM orders WHERE id=?", (order_id,))
        order_row = cur.fetchone()
        
        if not order_row:
            return error_response('Order not found', 404)
        
        order_dict = format_row(order_row)
        order_customer_id = order_dict.get('customer_id')
        
        # Check if user is seller with products in this order
        is_seller = False
        if role == 'seller':
            if DB_ENGINE == 'mysql':
                cur.execute('''
                    SELECT COUNT(*) as count
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s AND p.seller_id = %s
                ''', (order_id, user_id))
            else:
                cur.execute('''
                    SELECT COUNT(*) as count
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = ? AND p.seller_id = ?
                ''', (order_id, user_id))
            count_row = cur.fetchone()
            count = count_row[0] if isinstance(count_row, tuple) else (count_row.get('count', 0) if isinstance(count_row, dict) else 0)
            is_seller = count > 0
        
        # Role-based status restrictions
        # Sellers can only update: pending, processing, ready, cancelled
        seller_allowed_statuses = ('pending', 'processing', 'ready', 'cancelled')
        if role == 'seller' and new_status not in seller_allowed_statuses:
            return error_response(f'Sellers can only update status to: {", ".join(seller_allowed_statuses)}. Delivery statuses must be updated by the assigned rider.', 403)
        
        # Riders should use the delivery-update endpoint, not this one
        # But we'll allow them here for backwards compatibility if needed
        rider_statuses = ('dispatched', 'in-transit', 'delivered', 'completed')
        if role == 'rider' and new_status in rider_statuses:
            # Suggest using the delivery-update endpoint instead
            app.logger.warning(f'Rider {user_id} used status endpoint instead of delivery-update for order {order_id}')
        
        # Allow update if: user is admin, customer owns order, or seller has products in order
        if role != 'admin' and order_customer_id != user_id and not is_seller:
            return error_response('Forbidden: You do not have permission to update this order', 403)
        
        # When status is set to 'ready', clear rider_id to make order available for pickup
        # Check if rider_id column exists
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("SHOW COLUMNS FROM orders LIKE 'rider_id'")
                has_rider_id = cur.fetchone() is not None
            else:
                cur.execute("PRAGMA table_info(orders)")
                columns = cur.fetchall()
                has_rider_id = any(col[1] == 'rider_id' if isinstance(col, tuple) else col.get('name') == 'rider_id' for col in columns)
        except Exception:
            has_rider_id = False
        
        # Update order status and clear rider_id if status is 'ready'
        # This ensures orders marked as ready are available for riders to pick up
        app.logger.info(f'Order #{order_id}: Attempting to update status to "{new_status}" (type: {type(new_status)}, repr: {repr(new_status)})')
        
        if new_status == 'ready' and has_rider_id:
            if DB_ENGINE == 'mysql':
                cur.execute("UPDATE orders SET status=%s, rider_id=NULL WHERE id=%s;", (new_status, order_id))
            else:
                cur.execute("UPDATE orders SET status=?, rider_id=NULL WHERE id=?;", (new_status, order_id))
            app.logger.info(f'Order #{order_id} status updated to "ready" and rider_id cleared (rows affected: {cur.rowcount})')
        else:
            if DB_ENGINE == 'mysql':
                cur.execute("UPDATE orders SET status=%s WHERE id=%s;", (new_status, order_id))
            else:
                cur.execute("UPDATE orders SET status=? WHERE id=?;", (new_status, order_id))
            app.logger.info(f'Order #{order_id} status updated to "{new_status}" (rows affected: {cur.rowcount})')
        
        # Check if the update actually affected any rows
        if cur.rowcount == 0:
            app.logger.warning(f'Order #{order_id}: UPDATE query affected 0 rows - order may not exist or status was already "{new_status}"')
        
        try:
            conn.commit()
            app.logger.info(f'Order #{order_id} status update committed to database: "{new_status}"')
        except Exception as commit_err:
            app.logger.error(f'Failed to commit status update: {commit_err}')
            conn.rollback()
            cur.close()
            return error_response('Failed to save status update', 500)
        
        # Close the update cursor before verification
        cur.close()
        
        # Verify the update was successful by fetching the updated order with a fresh cursor
        # Use the same connection to ensure we see the committed data
        try:
            verify_cur = conn.cursor()
            if DB_ENGINE == 'mysql':
                verify_cur.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
            else:
                verify_cur.execute("SELECT status FROM orders WHERE id=?", (order_id,))
            verify_row = verify_cur.fetchone()
            updated_status = None
            if verify_row:
                if isinstance(verify_row, tuple):
                    updated_status = verify_row[0]
                elif isinstance(verify_row, dict):
                    updated_status = verify_row.get('status')
                elif hasattr(verify_row, 'keys'):
                    updated_status = dict(verify_row).get('status')
                
                app.logger.info(f'Order #{order_id} verification: Raw verify_row = {verify_row}, extracted status = "{updated_status}" (type: {type(updated_status)})')
            else:
                app.logger.error(f'Order #{order_id} verification: No row found after update!')
            
            verify_cur.close()
            
            if updated_status != new_status:
                app.logger.error(f'Order #{order_id} STATUS MISMATCH: Expected "{new_status}" (type: {type(new_status)}), but database has "{updated_status}" (type: {type(updated_status)})')
            else:
                app.logger.info(f'Order #{order_id} status verified successfully: "{updated_status}"')
        except Exception as verify_err:
            app.logger.error(f'Could not verify status update for order #{order_id}: {verify_err}')
            import traceback
            app.logger.error(traceback.format_exc())
            updated_status = new_status  # Assume it worked
        
        return jsonify({
            'success': True, 
            'message': 'Order status updated successfully',
            'order_id': order_id,
            'new_status': updated_status or new_status
        })
    except Exception as e:
        app.logger.error('update order status error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        try:
            if 'conn' in locals():
                conn.rollback()
        except: pass
        try:
            if 'cur' in locals():
                cur.close()
        except: pass
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/suppliers', methods=['GET'])
@role_required('admin', 'seller')
def api_get_suppliers():
    """Get suppliers list - Admin and Sellers only"""
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM suppliers")
        rows = [row2dict(r) for r in cur.fetchall()]
        cur.close()
        return jsonify(rows)
    except Exception as e:
        app.logger.error('suppliers error: %s', e)
        return jsonify({'error':'server_error'}), 500


@app.route('/api/inventory/movements', methods=['GET'])
@role_required('admin', 'seller')
def api_inventory_movements():
    """Get inventory movements - Admin and Sellers only"""
    pid = request.args.get('product_id', '').strip()
    
    # Validate product_id if provided
    if pid:
        try:
            pid = int(pid)
            if pid <= 0:
                return jsonify({'error': 'invalid_product_id'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'invalid_product_id'}), 400
    
    try:
        conn = get_db(); cur = conn.cursor()
        if pid:
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT * FROM inventory_movements WHERE product_id=%s ORDER BY created_at DESC LIMIT 1000", (pid,))
            else:
                cur.execute("SELECT * FROM inventory_movements WHERE product_id=? ORDER BY created_at DESC LIMIT 1000", (pid,))
        else:
            cur.execute("SELECT * FROM inventory_movements ORDER BY created_at DESC LIMIT 1000")
        rows = [row2dict(r) for r in cur.fetchall()]
        cur.close()
        return jsonify(rows)
    except Exception as e:
        app.logger.error('movements error: %s', e)
        return jsonify({'error':'server_error'}), 500


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@token_required
def api_get_order(order_id):
    """Get order details - owner or admin only"""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data:
            return jsonify({'error': 'unauthorized'}), 401
        
        user_id = token_data.get('user_id')
        role = token_data.get('role')
        
        conn = get_db(); cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
        else:
            cur.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        
        o = cur.fetchone()
        if not o:
            cur.close()
            return jsonify({'error':'Not found'}), 404
        
        # Check authorization: must be owner or admin
        order_dict = row2dict(o)
        if role != 'admin' and order_dict.get('customer_id') != user_id:
            cur.close()
            return jsonify({'error': 'forbidden'}), 403
        
        # Get order items
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT oi.*, p.title, p.img_url FROM order_items oi LEFT JOIN products p ON oi.product_id = p.id WHERE oi.order_id=%s", (order_id,))
        else:
            cur.execute("SELECT oi.*, p.title, p.img_url FROM order_items oi LEFT JOIN products p ON oi.product_id = p.id WHERE oi.order_id=?", (order_id,))
        items = [row2dict(r) for r in cur.fetchall()]
        
        # Get rider information if order has a rider
        if order_dict.get('rider_id'):
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    SELECT r.id, u.first_name, u.last_name, u.phone, r.vehicle_type
                    FROM riders r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.id = %s
                """, (order_dict['rider_id'],))
            else:
                cur.execute("""
                    SELECT r.id, u.first_name, u.last_name, u.phone, r.vehicle_type
                    FROM riders r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.id = ?
                """, (order_dict['rider_id'],))
            rider_row = cur.fetchone()
            if rider_row:
                rider_dict = format_row(rider_row)
                order_dict['rider'] = {
                    'id': rider_dict.get('id'),
                    'name': f"{rider_dict.get('first_name', '')} {rider_dict.get('last_name', '')}".strip(),
                    'phone': rider_dict.get('phone'),
                    'vehicle_type': rider_dict.get('vehicle_type')
                }
        
        # Check if customer has already rated this order
        if order_dict.get('customer_id') == user_id:
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT id, rating, comment FROM rider_reviews WHERE order_id = %s", (order_id,))
            else:
                cur.execute("SELECT id, rating, comment FROM rider_reviews WHERE order_id = ?", (order_id,))
            review_row = cur.fetchone()
            if review_row:
                review_dict = format_row(review_row)
                order_dict['review'] = {
                    'id': review_dict.get('id'),
                    'rating': review_dict.get('rating'),
                    'comment': review_dict.get('comment')
                }
        
        cur.close()
        
        order_dict['items'] = items
        return jsonify(order_dict)
    except Exception as e:
        app.logger.error('get order error: %s', e)
        return jsonify({'error':'server_error'}), 500

# Seller endpoints
@app.route('/api/erp/po/<int:po_id>/confirm', methods=['POST'])
@role_required('admin')
def api_erp_confirm_po(po_id):
    try:
        conn = get_db(); cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("UPDATE purchase_orders SET status='ordered' WHERE id=%s;", (po_id,))
            cur.execute("SELECT * FROM purchase_order_items WHERE po_id=%s;", (po_id,))
        else:
            cur.execute("UPDATE purchase_orders SET status='ordered' WHERE id=?;", (po_id,))
            cur.execute("SELECT * FROM purchase_order_items WHERE po_id=?;", (po_id,))
        items = cur.fetchall()
        for it in items:
            if DB_ENGINE == 'mysql':
                cur.execute("UPDATE products SET stock = stock + %s WHERE id=%s;", (it['quantity'], it['product_id']))
                cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (%s,%s,%s,%s,%s);",
                            (it['product_id'], it['quantity'], 'purchase', f'po:{po_id}', datetime.utcnow().isoformat()))
            else:
                cur.execute("UPDATE products SET stock = stock + ? WHERE id=?;", (it['quantity'], it['product_id']))
                cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (?,?,?,?,?);",
                            (it['product_id'], it['quantity'], 'purchase', f'po:{po_id}', datetime.utcnow().isoformat()))
        conn.commit(); cur.close()
        return jsonify({'success':True})
    except Exception as e:
        app.logger.error('confirm po error: %s', e)
        try: conn.rollback()
        except: pass
        try: cur.close()
        except: pass
        return jsonify({'error':'server_error'}), 500


@app.route('/api/erp/po/<int:po_id>/receive', methods=['POST'])
@role_required('admin')
def api_erp_receive_po(po_id):
    try:
        conn = get_db(); cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT * FROM purchase_order_items WHERE po_id=%s;", (po_id,))
        else:
            cur.execute("SELECT * FROM purchase_order_items WHERE po_id=?;", (po_id,))
        items = cur.fetchall()
        for it in items:
            if DB_ENGINE == 'mysql':
                cur.execute("UPDATE products SET stock = stock + %s WHERE id=%s;", (it['quantity'], it['product_id']))
                cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (%s,%s,%s,%s,%s);",
                            (it['product_id'], it['quantity'], 'purchase', f'po:{po_id}', datetime.utcnow().isoformat()))
            else:
                cur.execute("UPDATE products SET stock = stock + ? WHERE id=?;", (it['quantity'], it['product_id']))
                cur.execute("INSERT INTO inventory_movements (product_id, qty, movement_type, ref, created_at) VALUES (?,?,?,?,?);",
                            (it['product_id'], it['quantity'], 'purchase', f'po:{po_id}', datetime.utcnow().isoformat()))
        if DB_ENGINE=='mysql':
            cur.execute("UPDATE purchase_orders SET status='received' WHERE id=%s;", (po_id,))
        else:
            cur.execute("UPDATE purchase_orders SET status='received' WHERE id=?;", (po_id,))
        conn.commit(); cur.close()
        return jsonify({'success':True})
    except Exception as e:
        app.logger.error('receive po error: %s', e)
        try: conn.rollback()
        except: pass
        try: cur.close()
        except: pass
        return jsonify({'error':'server_error'}), 500
@app.route('/api/erp/purchase_orders', methods=['GET'])
@role_required('admin', 'seller')
def api_list_purchase_orders():
    """List purchase orders - Admin and Sellers only"""
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT po.*, s.name as supplier_name FROM purchase_orders po LEFT JOIN suppliers s ON s.id=po.supplier_id ORDER BY po.created_at DESC LIMIT 500")
    rows=[row2dict(r) for r in cur.fetchall()]
    cur.close()
    return jsonify(rows)


@app.route('/api/users', methods=['GET'])
@role_required('admin')
def api_list_users():
    """List users - Admin only. Optional query param: role=seller|rider|admin|customer"""
    role = request.args.get('role', '').strip()
    
    # Validate role parameter
    valid_roles = ['customer', 'seller', 'rider', 'admin']
    if role and role not in valid_roles:
        return jsonify({'error': 'invalid_role', 'valid_roles': valid_roles}), 400
    
    try:
        conn = get_db(); cur = conn.cursor()
        if role:
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT id, email, first_name, last_name, role, is_verified, created_at FROM users WHERE role=%s ORDER BY created_at DESC LIMIT 1000;", (role,))
            else:
                cur.execute("SELECT id, email, first_name, last_name, role, is_verified, created_at FROM users WHERE role=? ORDER BY created_at DESC LIMIT 1000;", (role,))
        else:
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT id, email, first_name, last_name, role, is_verified, created_at FROM users ORDER BY created_at DESC LIMIT 1000;")
            else:
                cur.execute("SELECT id, email, first_name, last_name, role, is_verified, created_at FROM users ORDER BY created_at DESC LIMIT 1000;")
        rows = [row2dict(r) for r in cur.fetchall()]
        cur.close()
        return jsonify(rows)
    except Exception as e:
        app.logger.error('list users error: %s', e)
        try: cur.close()
        except: pass
        return jsonify({'error':'server_error'}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)



# ==================== SELLER ENDPOINTS ====================

# Seller Registration Endpoint
@app.route('/api/sellers/register', methods=['POST'])
def api_seller_register():
    body = request.json or {}
    email = body.get('email')
    password = body.get('password')
    business_name = body.get('business_name', '')
    category = body.get('category', '')
    first = body.get('first_name', '')
    last = body.get('last_name', '')
    if not email or not password or not business_name:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        conn = get_db(); cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT id FROM users WHERE email=%s;", (email,))
        else:
            cur.execute("SELECT id FROM users WHERE email=?;", (email,))
        if cur.fetchone():
            cur.close()
            return jsonify({'error': 'User exists'}), 400

        # Generate OTP and store in database
        otp_code = generate_otp()
        pw_hash = generate_password_hash(password)

        # Create user as unverified (is_verified=0) with OTP stored
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,otp_code,is_verified,created_at) VALUES (%s,%s,%s,%s,%s,%s,0,%s);",
                        (email, pw_hash, first, last, 'seller', otp_code, datetime.utcnow().isoformat()))
        else:
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,otp_code,is_verified,created_at) VALUES (?,?,?,?,?,?,0,?);",
                        (email, pw_hash, first, last, 'seller', otp_code, datetime.utcnow().isoformat()))
        uid = cur.lastrowid

        # Check if seller approval is required
        approval_required = True  # Default to required
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT setting_value FROM platform_settings WHERE setting_key = 'seller_approval_required'")
            else:
                cur.execute("SELECT setting_value FROM platform_settings WHERE setting_key = 'seller_approval_required'")
            approval_setting = cur.fetchone()
            if approval_setting:
                approval_setting = format_row(approval_setting)
                approval_required = approval_setting.get('setting_value') == '1'
        except:
            # If setting doesn't exist, default to required
            pass
        
        # Set status based on approval requirement
        shop_status = 'active' if not approval_required else 'pending'
        verified = 1 if not approval_required else 0

        # Create seller profile
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO sellers (user_id,business_name,category,verified,shop_status) VALUES (%s,%s,%s,%s,%s);",
                        (uid, business_name, category, verified, shop_status))
        else:
            cur.execute("INSERT INTO sellers (user_id,business_name,category,verified,shop_status) VALUES (?,?,?,?,?);",
                        (uid, business_name, category, verified, shop_status))
        conn.commit()

        # Send OTP email
        send_otp_email(email, otp_code, 'seller')

        # Generate JWT token for new user (unverified)
        token = generate_token(uid, 'seller', email)
        
        # Create refresh token with fresh connection
        try:
            refresh_conn = get_db()
            refresh_token = create_refresh_token(refresh_conn, uid)
        except Exception as rte:
            print(f"[WARN] Failed to create refresh token during registration: {rte}")
            refresh_token = None
        
        cur.close()
        return jsonify({
            'success': True,
            'token': token,
            'refresh_token': refresh_token,
            'user_id': uid,
            'message': 'Registration successful. Please verify your email with the OTP sent.',
            'is_verified': False
        })
    except Exception as e:
        app.logger.error('seller_register error: %s', e)
        try:
            conn.rollback()
        except: pass
        try: cur.close()
        except: pass
        return jsonify({'error': 'server_error'}), 500

# Rider Registration Endpoint
@app.route('/api/riders/register', methods=['POST'])
def api_rider_register():
    body = request.json or {}
    email = body.get('email')
    password = body.get('password')
    vehicle_type = body.get('vehicle_type', '')
    driver_license = body.get('driver_license', '')
    first = body.get('first_name', '')
    last = body.get('last_name', '')
    if not email or not password or not vehicle_type or not driver_license:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        conn = get_db(); cur = conn.cursor()
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT id FROM users WHERE email=%s;", (email,))
        else:
            cur.execute("SELECT id FROM users WHERE email=?;", (email,))
        if cur.fetchone():
            cur.close()
            return jsonify({'error': 'User exists'}), 400

        # Generate OTP and store in database
        otp_code = generate_otp()
        pw_hash = generate_password_hash(password)

        # Create user as unverified (is_verified=0) with OTP stored
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,otp_code,is_verified,created_at) VALUES (%s,%s,%s,%s,%s,%s,0,%s);",
                        (email, pw_hash, first, last, 'rider', otp_code, datetime.utcnow().isoformat()))
        else:
            cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,otp_code,is_verified,created_at) VALUES (?,?,?,?,?,?,0,?);",
                        (email, pw_hash, first, last, 'rider', otp_code, datetime.utcnow().isoformat()))
        uid = cur.lastrowid

        # Create rider profile
        if DB_ENGINE == 'mysql':
            cur.execute("INSERT INTO riders (user_id,vehicle_type,driver_license,verified,rider_status) VALUES (%s,%s,%s,0,'pending');",
                        (uid, vehicle_type, driver_license))
        else:
            cur.execute("INSERT INTO riders (user_id,vehicle_type,driver_license,verified,rider_status) VALUES (?,?,?,0,'pending');",
                        (uid, vehicle_type, driver_license))
        conn.commit()

        # Send OTP email
        send_otp_email(email, otp_code, 'rider')

        # Generate JWT token for new user (unverified)
        token = generate_token(uid, 'rider', email)
        
        # Create refresh token with fresh connection
        try:
            refresh_conn = get_db()
            refresh_token = create_refresh_token(refresh_conn, uid)
        except Exception as rte:
            print(f"[WARN] Failed to create refresh token during rider registration: {rte}")
            refresh_token = None
        
        cur.close()
        return jsonify({
            'success': True,
            'token': token,
            'refresh_token': refresh_token,
            'user_id': uid,
            'message': 'Registration successful. Please verify your email with the OTP sent.',
            'is_verified': False
        })
    except Exception as e:
        app.logger.error('rider_register error: %s', e)
        try:
            conn.rollback()
        except: pass
        try: cur.close()
        except: pass
        return jsonify({'error': 'server_error'}), 500

# ============== File Upload Helpers ==============

def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename or not isinstance(filename, str):
        return False
    
    # Prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check extension
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

# ============== Multi-Store Endpoints ==============

# Store management endpoints removed - single store per seller (no multi-store functionality)


# ============== Compatibility Alias & Stub Endpoints ==============

@app.route('/api/me', methods=['GET'])
@token_required
def api_me_alias():
    """Backward-compatible alias to /api/account/me for older frontends."""
    return api_account_me()

@app.route('/api/sellers/my-ratings', methods=['GET'])
@token_required
def api_seller_my_ratings():
    """Get seller ratings - redirects to real reviews endpoint"""
    # This endpoint is called by seller_ratings.js, but we should use the real endpoint
    # For now, redirect to the real reviews endpoint
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'seller':
            return error_response('Only sellers can access this endpoint', 403)
        
        # Call the real reviews endpoint logic
        db = get_db()
        if DB_ENGINE == 'mysql':
            cursor = db.cursor(pymysql.cursors.DictCursor)
        else:
            cursor = db.cursor()
        
        # Get reviews
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    r.id,
                    r.order_id,
                    r.product_id,
                    r.customer_id,
                    r.seller_id,
                    r.rating,
                    r.comment,
                    r.created_at,
                    r.updated_at,
                    p.title as product_title,
                    p.img_url as product_image,
                    p.seller_id as product_seller_id,
                    u.first_name,
                    u.last_name,
                    u.email as customer_email
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                LEFT JOIN users u ON r.customer_id = u.id
                WHERE p.seller_id = %s
                  AND r.product_id IS NOT NULL
                ORDER BY r.created_at DESC
                LIMIT 50
            ''', (seller_user_id,))
        else:
            cursor.execute('''
                SELECT 
                    r.id,
                    r.order_id,
                    r.product_id,
                    r.customer_id,
                    r.seller_id,
                    r.rating,
                    r.comment,
                    r.created_at,
                    r.updated_at,
                    p.title as product_title,
                    p.img_url as product_image,
                    p.seller_id as product_seller_id,
                    u.first_name,
                    u.last_name,
                    u.email as customer_email
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                LEFT JOIN users u ON r.customer_id = u.id
                WHERE p.seller_id = ?
                  AND r.product_id IS NOT NULL
                ORDER BY r.created_at DESC
                LIMIT 50
            ''', (seller_user_id,))
        
        reviews = cursor.fetchall()
        
        # Calculate stats
        total_reviews = len(reviews)
        avg_rating = 0.0
        if total_reviews > 0:
            avg_rating = sum(format_row(r).get('rating', 0) for r in reviews) / total_reviews
        
        # Rating breakdown
        breakdown = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
        for review in reviews:
            rating = format_row(review).get('rating', 0)
            if 1 <= rating <= 5:
                breakdown[str(rating)] += 1
        
        # Format reviews for response
        formatted_reviews = []
        for review in reviews:
            r_dict = format_row(review)
            first_name = r_dict.get('first_name', '')
            last_name = r_dict.get('last_name', '')
            customer_name = f"{first_name} {last_name}".strip() or r_dict.get('customer_email', 'Customer')
            formatted_reviews.append({
                'id': r_dict.get('id'),
                'product_id': r_dict.get('product_id'),
                'product_name': r_dict.get('product_title', 'Unknown Product'),
                'product_image': r_dict.get('product_image'),
                'customer_name': customer_name,
                'rating': r_dict.get('rating'),
                'comment': r_dict.get('comment'),
                'created_at': r_dict.get('created_at')
            })
        
        cursor.close()
        
        return success_response({
            'overall_rating': round(avg_rating, 1),
            'average_rating': round(avg_rating, 1),
            'total_reviews': total_reviews,
            'rating_breakdown': {
                '5': {'count': breakdown['5'], 'percentage': round((breakdown['5'] / total_reviews * 100) if total_reviews > 0 else 0, 1)},
                '4': {'count': breakdown['4'], 'percentage': round((breakdown['4'] / total_reviews * 100) if total_reviews > 0 else 0, 1)},
                '3': {'count': breakdown['3'], 'percentage': round((breakdown['3'] / total_reviews * 100) if total_reviews > 0 else 0, 1)},
                '2': {'count': breakdown['2'], 'percentage': round((breakdown['2'] / total_reviews * 100) if total_reviews > 0 else 0, 1)},
                '1': {'count': breakdown['1'], 'percentage': round((breakdown['1'] / total_reviews * 100) if total_reviews > 0 else 0, 1)}
            },
            'breakdown': [
                {'rating': 5, 'count': breakdown['5']},
                {'rating': 4, 'count': breakdown['4']},
                {'rating': 3, 'count': breakdown['3']},
                {'rating': 2, 'count': breakdown['2']},
                {'rating': 1, 'count': breakdown['1']}
            ],
            'reviews': formatted_reviews,
            'recent': formatted_reviews[:10]
        }, 'Ratings fetched successfully')
        
    except Exception as e:
        app.logger.error(f'Error fetching seller ratings: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/my-insights', methods=['GET'])
@token_required
def api_seller_my_insights():
    """Get seller review insights - uses real analytics data"""
    # This endpoint is called by review_insights.js, redirect to real analytics
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'seller':
            return error_response('Only sellers can access this endpoint', 403)
        
        # Call the real analytics endpoint logic
        db = get_db()
        if DB_ENGINE == 'mysql':
            cursor = db.cursor(pymysql.cursors.DictCursor)
        else:
            cursor = db.cursor()
        
        # Get analytics (same as /api/sellers/reviews/analytics)
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    AVG(r.rating) as avg_rating,
                    COUNT(*) as total_reviews,
                    SUM(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END) as rating_5,
                    SUM(CASE WHEN r.rating = 4 THEN 1 ELSE 0 END) as rating_4,
                    SUM(CASE WHEN r.rating = 3 THEN 1 ELSE 0 END) as rating_3,
                    SUM(CASE WHEN r.rating = 2 THEN 1 ELSE 0 END) as rating_2,
                    SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END) as rating_1
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = %s
                  AND r.product_id IS NOT NULL
            ''', (seller_user_id,))
        else:
            cursor.execute('''
                SELECT 
                    AVG(r.rating) as avg_rating,
                    COUNT(*) as total_reviews,
                    SUM(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END) as rating_5,
                    SUM(CASE WHEN r.rating = 4 THEN 1 ELSE 0 END) as rating_4,
                    SUM(CASE WHEN r.rating = 3 THEN 1 ELSE 0 END) as rating_3,
                    SUM(CASE WHEN r.rating = 2 THEN 1 ELSE 0 END) as rating_2,
                    SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END) as rating_1
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = ?
                  AND r.product_id IS NOT NULL
            ''', (seller_user_id,))
        
        stats = cursor.fetchone()
        stats_dict = format_row(stats)
        
        avg_rating = float(stats_dict.get('avg_rating', 0) or 0)
        total_reviews = int(stats_dict.get('total_reviews', 0) or 0)
        
        rating_5 = int(stats_dict.get('rating_5', 0) or 0)
        rating_4 = int(stats_dict.get('rating_4', 0) or 0)
        rating_3 = int(stats_dict.get('rating_3', 0) or 0)
        rating_2 = int(stats_dict.get('rating_2', 0) or 0)
        rating_1 = int(stats_dict.get('rating_1', 0) or 0)
        
        satisfaction_score = round(((rating_5 + rating_4) / total_reviews * 100) if total_reviews > 0 else 0, 1)
        satisfied_count = rating_5 + rating_4
        
        # Get keywords (simplified version)
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT r.comment
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = %s 
                  AND r.product_id IS NOT NULL
                  AND r.comment IS NOT NULL 
                  AND r.comment != ''
            ''', (seller_user_id,))
        else:
            cursor.execute('''
                SELECT r.comment
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = ? 
                  AND r.product_id IS NOT NULL
                  AND r.comment IS NOT NULL 
                  AND r.comment != ''
            ''', (seller_user_id,))
        
        comments = cursor.fetchall()
        
        # Extract keywords
        import re
        from collections import Counter
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'very', 'really', 'quite', 'too', 'so', 'just', 'only', 'also', 'even', 'still', 'yet', 'already', 'product', 'item', 'order', 'delivery', 'shipping'}
        
        all_words = []
        for comment_row in comments:
            comment = comment_row[0] if isinstance(comment_row, tuple) else comment_row.get('comment', '')
            if comment:
                words = re.findall(r'\b[a-zA-Z]{3,}\b', comment.lower())
                all_words.extend([w for w in words if w not in stop_words])
        
        keyword_counts = Counter(all_words)
        most_mentioned = [{'keyword': word, 'count': count} for word, count in keyword_counts.most_common(10)]
        
        # Areas to improve (from low ratings)
        areas_to_improve = []
        if rating_1 + rating_2 + rating_3 > 0:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT r.comment
                    FROM reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE p.seller_id = %s AND r.rating <= 3 AND r.comment IS NOT NULL AND r.comment != ''
                    ORDER BY r.rating ASC, r.created_at DESC
                    LIMIT 20
                ''', (seller_user_id,))
            else:
                cursor.execute('''
                    SELECT r.comment
                    FROM reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE p.seller_id = ? AND r.rating <= 3 AND r.comment IS NOT NULL AND r.comment != ''
                    ORDER BY r.rating ASC, r.created_at DESC
                    LIMIT 20
                ''', (seller_user_id,))
            
            low_rating_comments = cursor.fetchall()
            low_words = []
            for comment_row in low_rating_comments:
                comment = comment_row[0] if isinstance(comment_row, tuple) else comment_row.get('comment', '')
                if comment:
                    words = re.findall(r'\b[a-zA-Z]{3,}\b', comment.lower())
                    low_words.extend([w for w in words if w not in stop_words])
            
            low_keyword_counts = Counter(low_words)
            areas_to_improve = [{'keyword': word, 'count': count} for word, count in low_keyword_counts.most_common(5)]
        
        cursor.close()
        
        return success_response({
            'total_reviews': total_reviews,
            'customer_satisfaction': satisfaction_score,
            'satisfied_count': satisfied_count,
            'most_mentioned': most_mentioned,
            'top_positive_keywords': most_mentioned[:5],
            'areas_to_improve': areas_to_improve,
            'top_negative_keywords': areas_to_improve,
            'recent_trends': {
                'last_7_days': {
                    'total_reviews': total_reviews,
                    'satisfaction': satisfaction_score,
                    'average_rating': round(avg_rating, 1)
                },
                'previous_7_days': {
                    'total_reviews': 0,
                    'satisfaction': 0,
                    'average_rating': 0
                },
                'trend': {
                    'satisfaction_change': 0,
                    'direction': 'stable'
                }
            },
            'sentiment_distribution': {
                'positive': rating_5 + rating_4,
                'neutral': rating_3,
                'negative': rating_1 + rating_2,
                'positive_percentage': round(((rating_5 + rating_4) / total_reviews * 100) if total_reviews > 0 else 0, 1),
                'neutral_percentage': round((rating_3 / total_reviews * 100) if total_reviews > 0 else 0, 1),
                'negative_percentage': round(((rating_1 + rating_2) / total_reviews * 100) if total_reviews > 0 else 0, 1)
            }
        }, 'Insights fetched successfully')
        
    except Exception as e:
        app.logger.error(f'Error fetching seller insights: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

def validate_file_upload(file, max_size=MAX_FILE_SIZE):
    """Comprehensive file upload validation"""
    if not file:
        return False, 'No file provided'
    
    if file.filename == '':
        return False, 'No file selected'
    
    # Check filename security
    if not allowed_file(file.filename):
        return False, f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
    
    # Read first chunk to check size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > max_size:
        return False, f'File too large. Maximum size: {max_size / (1024*1024):.1f}MB'
    
    if file_size == 0:
        return False, 'File is empty'
    
    return True, None

@app.route('/api/upload/product-image', methods=['POST'])
@token_required
def api_upload_product_image():
    """Upload a product image - Sellers only"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        # Only sellers can upload product images
        if role not in ['seller', 'admin']:
            return error_response('Only sellers can upload product images', 403)
        
        # Check if file is in request
        if 'image' not in request.files:
            return error_response('No image file provided', 400)
        
        file = request.files['image']
        
        # Comprehensive validation
        is_valid, error_msg = validate_file_upload(file)
        if not is_valid:
            return error_response(error_msg, 400)
        
        # Generate secure filename with timestamp
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"seller{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(8)}.{file_ext}"
        
        # Ensure upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Return relative path for database storage
        relative_path = f"/uploads/products/{unique_filename}"
        
        return success_response({
            'filename': unique_filename,
            'path': relative_path,
            'url': relative_path
        }, 'Image uploaded successfully')
        
    except Exception as e:
        app.logger.error(f'Image upload error: {e}')
        return error_response('Upload failed', 500)

@app.route('/uploads/products/<filename>')
def serve_product_image(filename):
    """Serve uploaded product images"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/upload/store-logo', methods=['POST'])
@token_required
def api_upload_store_logo():
    """Upload store logo"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        # Debug logging
        app.logger.info(f"Store logo upload - Files: {request.files.keys()}")
        
        # Check if file is in request
        if 'logo' not in request.files:
            app.logger.error(f"No 'logo' key in request.files. Available keys: {list(request.files.keys())}")
            return error_response('No logo file provided', 400)
        
        file = request.files['logo']
        
        # Check if file was selected
        if file.filename == '':
            return error_response('No file selected', 400)
        
        # Validate file type
        if not allowed_file(file.filename):
            allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
            return error_response(f'Invalid file type. Only {allowed_list} allowed', 400)
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"logo_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}.{file_ext}"
        
        # Save file to uploads/stores folder
        store_upload_folder = os.path.join(BASE_DIR, 'uploads', 'stores')
        os.makedirs(store_upload_folder, exist_ok=True)
        file_path = os.path.join(store_upload_folder, unique_filename)
        file.save(file_path)
        
        # Return relative path
        relative_path = f"/uploads/stores/{unique_filename}"
        
        return success_response({
            'filename': unique_filename,
            'path': relative_path,
            'url': relative_path
        }, 'Logo uploaded successfully')
        
    except Exception as e:
        app.logger.error(f'Logo upload error: {e}')
        return error_response(str(e), 500)

@app.route('/api/upload/store-banner', methods=['POST'])
@token_required
def api_upload_store_banner():
    """Upload store banner"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        # Debug logging
        app.logger.info(f"Store banner upload - Files: {request.files.keys()}")
        
        # Check if file is in request
        if 'banner' not in request.files:
            app.logger.error(f"No 'banner' key in request.files. Available keys: {list(request.files.keys())}")
            return error_response('No banner file provided', 400)
        
        file = request.files['banner']
        
        # Check if file was selected
        if file.filename == '':
            return error_response('No file selected', 400)
        
        # Validate file type
        if not allowed_file(file.filename):
            allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
            return error_response(f'Invalid file type. Only {allowed_list} allowed', 400)
        
        # Check file size (10MB max for banners)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        max_banner_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_banner_size:
            return error_response('File too large. Maximum size is 10MB', 400)
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"banner_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}.{file_ext}"
        
        # Save file to uploads/stores folder
        store_upload_folder = os.path.join(BASE_DIR, 'uploads', 'stores')
        os.makedirs(store_upload_folder, exist_ok=True)
        file_path = os.path.join(store_upload_folder, unique_filename)
        file.save(file_path)
        
        # Return relative path
        relative_path = f"/uploads/stores/{unique_filename}"
        
        return success_response({
            'filename': unique_filename,
            'path': relative_path,
            'url': relative_path
        }, 'Banner uploaded successfully')
        
    except Exception as e:
        app.logger.error(f'Banner upload error: {e}')
        return error_response(str(e), 500)

@app.route('/uploads/stores/<filename>')
def serve_store_image(filename):
    """Serve uploaded store images (logos and banners)"""
    try:
        store_folder = os.path.join(BASE_DIR, 'uploads', 'stores')
        file_path = os.path.join(store_folder, filename)
        
        # Check if file exists before trying to serve it
        if not os.path.exists(file_path):
            app.logger.warning(f'Store image not found: {filename}')
            return "Not Found", 404
        
        return send_from_directory(store_folder, filename)
    except Exception as e:
        app.logger.error(f'Error serving store image {filename}: {e}')
        return "Not Found", 404

@app.route('/api/upload/profile-picture', methods=['POST'])
@token_required
def api_upload_profile_picture():
    """Upload profile picture for users/riders"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        # Check if file is in request
        if 'picture' not in request.files:
            return error_response('No picture file provided', 400)
        
        file = request.files['picture']
        
        # Check if file was selected
        if file.filename == '':
            return error_response('No file selected', 400)
        
        # Validate file
        is_valid, error_msg = validate_file_upload(file)
        if not is_valid:
            return error_response(error_msg, 400)
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"profile_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(8)}.{file_ext}"
        
        # Save file to uploads/profiles folder
        profile_upload_folder = os.path.join(BASE_DIR, 'uploads', 'profiles')
        os.makedirs(profile_upload_folder, exist_ok=True)
        file_path = os.path.join(profile_upload_folder, unique_filename)
        file.save(file_path)
        
        # Return relative path
        relative_path = f"/uploads/profiles/{unique_filename}"
        
        # Update avatar_url in database
        conn = get_db()
        cur = conn.cursor()
        
        try:
            # Update users table
            if DB_ENGINE == 'mysql':
                cur.execute("UPDATE users SET avatar_url=%s WHERE id=%s", (relative_path, user_id))
                # Also update riders table if rider
                if role == 'rider':
                    cur.execute("UPDATE riders SET avatar_url=%s WHERE user_id=%s", (relative_path, user_id))
            else:
                cur.execute("UPDATE users SET avatar_url=? WHERE id=?", (relative_path, user_id))
                if role == 'rider':
                    cur.execute("UPDATE riders SET avatar_url=? WHERE user_id=?", (relative_path, user_id))
            
            conn.commit()
            app.logger.info(f'Successfully updated avatar_url to {relative_path} for user_id {user_id}, role {role}')
            # Verify the update
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT avatar_url FROM users WHERE id=%s", (user_id,))
            else:
                cur.execute("SELECT avatar_url FROM users WHERE id=?", (user_id,))
            verify_row = cur.fetchone()
            if verify_row:
                verify_dict = format_row(verify_row)
                app.logger.info(f'Verified avatar_url in users table: {verify_dict.get("avatar_url")}')
        except Exception as db_err:
            conn.rollback()
            app.logger.error(f'Error updating avatar_url in database: {db_err}')
            import traceback
            app.logger.error(traceback.format_exc())
            # Don't fail the upload, just log the error
        finally:
            cur.close()
        
        return success_response({
            'filename': unique_filename,
            'path': relative_path,
            'url': relative_path
        }, 'Profile picture uploaded successfully')
        
    except Exception as e:
        app.logger.error(f'Profile picture upload error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/uploads/profiles/<filename>')
def serve_profile_picture(filename):
    """Serve uploaded profile pictures"""
    try:
        profile_folder = os.path.join(BASE_DIR, 'uploads', 'profiles')
        file_path = os.path.join(profile_folder, filename)
        
        # Check if file exists before trying to serve it
        if not os.path.exists(file_path):
            app.logger.warning(f'Profile picture not found: {filename}')
            return "Not Found", 404
        
        return send_from_directory(profile_folder, filename)
    except Exception as e:
        app.logger.error(f'Error serving profile picture {filename}: {e}')
        return "Not Found", 404

@app.route('/uploads/messages/<filename>')
def serve_message_attachment(filename):
    """Serve uploaded message attachments (images and videos)"""
    try:
        messages_folder = os.path.join(BASE_DIR, 'uploads', 'messages')
        file_path = os.path.join(messages_folder, filename)
        
        # Check if file exists before trying to serve it
        if not os.path.exists(file_path):
            app.logger.warning(f'Message attachment not found: {filename}')
            return "Not Found", 404
        
        return send_from_directory(messages_folder, filename)
    except Exception as e:
        app.logger.error(f'Error serving message attachment {filename}: {e}')
        return "Not Found", 404

@app.route('/api/sellers/settings', methods=['POST'])
@token_required
def api_seller_save_settings():
    """Save seller settings including store info"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        # Verify user is a seller
        if DB_ENGINE == 'mysql':
            cursor = get_db().cursor(pymysql.cursors.DictCursor)
        else:
            cursor = get_db().cursor()
        
        cursor.execute('SELECT id FROM sellers WHERE user_id = %s' if DB_ENGINE == 'mysql' 
                      else 'SELECT id FROM sellers WHERE user_id = ?', (user_id,))
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Only sellers can access this endpoint', 403)
        
        seller_id = seller['id'] if isinstance(seller, dict) else seller[0]
        
        # Get settings from request
        data = request.get_json()
        
        # Build update query for all settings
        updates = []
        params = []
        
        # Store information (now these columns exist!)
        if 'storeName' in data:
            updates.append('store_name = %s' if DB_ENGINE == 'mysql' else 'store_name = ?')
            params.append(data['storeName'])
        
        if 'storeDescription' in data:
            updates.append('store_description = %s' if DB_ENGINE == 'mysql' else 'store_description = ?')
            params.append(data['storeDescription'])
        
        if 'storeLogo' in data:
            updates.append('store_logo = %s' if DB_ENGINE == 'mysql' else 'store_logo = ?')
            params.append(data['storeLogo'])
        
        if 'storeBanner' in data:
            updates.append('store_banner = %s' if DB_ENGINE == 'mysql' else 'store_banner = ?')
            params.append(data['storeBanner'])
        
        if 'storeCategory' in data:
            updates.append('category = %s' if DB_ENGINE == 'mysql' else 'category = ?')
            params.append(data['storeCategory'])
        
        if 'businessName' in data:
            updates.append('business_name = %s' if DB_ENGINE == 'mysql' else 'business_name = ?')
            params.append(data['businessName'])
        
        # Execute update if there are changes
        if updates:
            params.append(seller_id)
            placeholder = '%s' if DB_ENGINE == 'mysql' else '?'
            query = f"UPDATE sellers SET {', '.join(updates)} WHERE id = {placeholder}"
            cursor.execute(query, tuple(params))
            get_db().commit()
        
        return success_response('Settings saved successfully')
        
    except Exception as e:
        app.logger.error(f"Error saving seller settings: {e}")
        return error_response(str(e), 500)

@app.route('/api/seller/me', methods=['GET'])
@token_required
def api_seller_get_me():
    """Get current seller's information"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        # Get seller info
        db = get_db()
        if DB_ENGINE == 'mysql':
            cursor = db.cursor(pymysql.cursors.DictCursor)
        else:
            cursor = db.cursor()
        
        cursor.execute('''
            SELECT id, user_id, business_name, store_name, store_description, 
                   store_logo, store_banner, category, region, province, city, 
                   verified, shop_status, approved_at
            FROM sellers 
            WHERE user_id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            SELECT id, user_id, business_name, store_name, store_description,
                   store_logo, store_banner, category, region, province, city, 
                   verified, shop_status, approved_at
            FROM sellers 
            WHERE user_id = ?
        ''', (user_id,))
        
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller profile not found', 404)
        
        # Convert to dict if needed
        if not isinstance(seller, dict):
            seller = {
                'id': seller[0],
                'user_id': seller[1],
                'business_name': seller[2],
                'store_name': seller[3],
                'store_description': seller[4],
                'store_logo': seller[5],
                'store_banner': seller[6],
                'category': seller[7],
                'region': seller[8],
                'province': seller[9],
                'city': seller[10],
                'verified': seller[11],
                'shop_status': seller[12],
                'approved_at': seller[13]
            }
        
        return success_response(seller)
        
    except Exception as e:
        app.logger.error(f"Error getting seller info: {e}")
        return error_response(str(e), 500)

@app.route('/api/seller/profile/stats', methods=['GET'])
@token_required
def api_seller_profile_stats():
    """Get seller profile statistics (orders, earnings, ratings, etc.) - supports store_id filtering"""
    try:
        payload = verify_token(get_token_from_request())
        user_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get seller ID
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM sellers WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('SELECT id FROM sellers WHERE user_id = ?', (user_id,))
        seller_row = cursor.fetchone()
        if not seller_row:
            return error_response('Seller profile not found', 404)
        
        seller_id = seller_row[0] if isinstance(seller_row, (tuple, list)) else seller_row.get('id')
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id)
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id,)
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id,)
        
        # Get total orders count
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COUNT(*) as total_orders
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND o.status IN ('delivered', 'completed')
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT COUNT(DISTINCT o.id) as total_orders
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND o.status IN ('delivered', 'completed')
            ''', product_params)
        
        orders_result = cursor.fetchone()
        total_orders = orders_result[0] if isinstance(orders_result, (tuple, list)) else orders_result.get('total_orders', 0)
        
        # Get total earnings
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.quantity * oi.price), 0) as total_earnings
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND o.status IN ('delivered', 'completed')
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.quantity * oi.price), 0) as total_earnings
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND o.status IN ('delivered', 'completed')
            ''', product_params)
        
        earnings_result = cursor.fetchone()
        total_earnings = float(earnings_result[0] if isinstance(earnings_result, (tuple, list)) else earnings_result.get('total_earnings', 0))
        
        # Get average rating
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT COALESCE(AVG(r.rating), 0) as avg_rating, COUNT(r.id) as rating_count
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = %s
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT COALESCE(AVG(r.rating), 0) as avg_rating, COUNT(r.id) as rating_count
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = ?
            ''', (seller_id,))
        
        rating_result = cursor.fetchone()
        avg_rating = float(rating_result[0] if isinstance(rating_result, (tuple, list)) else rating_result.get('avg_rating', 0))
        rating_count = rating_result[1] if isinstance(rating_result, (tuple, list)) else rating_result.get('rating_count', 0)
        
        # Get member since date
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT created_at FROM users WHERE id = %s', (user_id,))
        else:
            cursor.execute('SELECT created_at FROM users WHERE id = ?', (user_id,))
        
        user_result = cursor.fetchone()
        member_since = user_result[0] if isinstance(user_result, (tuple, list)) else user_result.get('created_at') if user_result else None
        
        cursor.close()
        
        return success_response({
            'total_orders': int(total_orders),
            'total_earnings': round(total_earnings, 2),
            'average_rating': round(avg_rating, 1),
            'rating_count': int(rating_count),
            'member_since': member_since
        }, 'Profile stats retrieved successfully')
        
    except Exception as e:
        app.logger.error(f"Error getting seller profile stats: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

# ============== Seller Products API ==============

@app.route('/api/sellers/products', methods=['POST'])
@token_required
def api_seller_create_product():
    """Seller creates a new product listing"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        # Verify user is a seller
        db = get_db()
        cursor = db.cursor()
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT role FROM users WHERE id=%s', (user_id,))
        else:
            cursor.execute('SELECT role FROM users WHERE id=?', (user_id,))
        result = cursor.fetchone()
        if not result:
            return error_response('User not found', 404)
        
        role = result['role'] if isinstance(result, dict) else result[0]
        if role != 'seller':
            return error_response('Must be a seller', 403)
        
        # Check if seller is verified and shop is active
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'SELECT id, verified, shop_status, business_name FROM sellers WHERE user_id=%s',
                (user_id,)
            )
        else:
            cursor.execute(
                'SELECT id, verified, shop_status, business_name FROM sellers WHERE user_id=?',
                (user_id,)
            )
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller profile not found', 404)
        
        seller_id = seller['id'] if isinstance(seller, dict) else seller[0]
        verified = seller['verified'] if isinstance(seller, dict) else seller[1]
        shop_status = seller['shop_status'] if isinstance(seller, dict) else (seller[2] if len(seller) > 2 else 'pending')
        
        # Check if seller is verified
        if not verified:
            return error_response(
                'Your seller account is pending approval. Please wait for admin verification.',
                403
            )
        
        # Check if shop is active
        if shop_status != 'active':
            if shop_status == 'suspended':
                return error_response(
                    'Your shop has been suspended. Please contact admin for assistance.',
                    403
                )
            else:
                return error_response(
                    'Your shop is not active yet. Please wait for admin approval.',
                    403
                )
        
        # Validate product data
        data = request.json
        required = ['title', 'price', 'stock']
        if not all(k in data for k in required):
            return error_response(f'Required fields: {", ".join(required)}', 400)
        
        title = data.get('title')
        description = data.get('description', '')
        price = float(data.get('price', 0))
        stock = int(data.get('stock', 0))
        category = data.get('category', 'General')
        img_url = data.get('img_url', '')
        manufacture_date = data.get('manufacture_date') or None
        expiry_date = data.get('expiry_date') or None
        
        # Validate price and stock
        if price <= 0:
            return error_response('Price must be greater than 0', 400)
        if stock < 0:
            return error_response('Stock cannot be negative', 400)
        
        # Optional store_id (must belong to this seller and be approved)
        store_id = data.get('store_id')
        if store_id is not None:
            try:
                store_id = int(store_id)
            except ValueError:
                return error_response('Invalid store_id', 400)
            # Verify store ownership & status
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT seller_user_id,status FROM stores WHERE id=%s', (store_id,))
            else:
                cursor.execute('SELECT seller_user_id,status FROM stores WHERE id=?', (store_id,))
            srow = cursor.fetchone()
            if not srow:
                return error_response('Store not found', 404)
            s_owner = srow[0] if isinstance(srow, (list, tuple)) else srow['seller_user_id']
            s_status = srow[1] if isinstance(srow, (list, tuple)) else srow['status']
            if s_owner != user_id:
                return error_response('Store does not belong to you', 403)
            if s_status != 'approved':
                return error_response('Store is not approved yet', 403)

        # Check if date columns exist (for both MySQL and SQLite)
        has_dates = False
        has_store = False
        
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'manufacture_date'")
                has_manufacture = cursor.fetchone() is not None
                cursor.execute("SHOW COLUMNS FROM products LIKE 'expiry_date'")
                has_expiry = cursor.fetchone() is not None
                has_dates = has_manufacture and has_expiry
                
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                has_store = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info('products')")
                cols = cursor.fetchall()
                col_names = [col[1] if isinstance(col, tuple) else col['name'] for col in cols]
                has_dates = 'manufacture_date' in col_names and 'expiry_date' in col_names
                has_store = 'store_id' in col_names
        except Exception as check_err:
            app.logger.warning(f'Could not check for date columns: {check_err}')
            has_dates = False
            has_store = False

        # Create product with proper field handling
        if DB_ENGINE == 'mysql':
            if has_dates and has_store and store_id is not None:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, 
                       manufacture_date, expiry_date, store_id, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())''',
                    (title, description, price, stock, user_id, category, img_url, manufacture_date, expiry_date, store_id)
                )
            elif has_dates and has_store:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, 
                       manufacture_date, expiry_date, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())''',
                    (title, description, price, stock, user_id, category, img_url, manufacture_date, expiry_date)
                )
            elif has_dates and store_id is not None:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, 
                       manufacture_date, expiry_date, store_id, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())''',
                    (title, description, price, stock, user_id, category, img_url, manufacture_date, expiry_date, store_id)
                )
            elif has_dates:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, 
                       manufacture_date, expiry_date, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())''',
                    (title, description, price, stock, user_id, category, img_url, manufacture_date, expiry_date)
                )
            elif has_store and store_id is not None:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, store_id, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())''',
                    (title, description, price, stock, user_id, category, img_url, store_id)
                )
            else:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())''',
                    (title, description, price, stock, user_id, category, img_url)
                )
        else:
            # SQLite - check if date columns exist
            cursor.execute("PRAGMA table_info('products')")
            cols = cursor.fetchall()
            col_names = [col[1] if isinstance(col, tuple) else col['name'] for col in cols]
            
            has_dates = 'manufacture_date' in col_names and 'expiry_date' in col_names
            has_store = 'store_id' in col_names
            now_iso = datetime.now().isoformat()
            if has_dates and has_store and store_id is not None:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, 
                       manufacture_date, expiry_date, store_id, created_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (title, description, price, stock, user_id, category, img_url,
                     manufacture_date, expiry_date, store_id, now_iso)
                )
            elif has_dates and has_store:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, 
                       manufacture_date, expiry_date, created_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (title, description, price, stock, user_id, category, img_url,
                     manufacture_date, expiry_date, now_iso)
                )
            elif has_store and store_id is not None:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, store_id, created_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (title, description, price, stock, user_id, category, img_url, store_id, now_iso)
                )
            else:
                cursor.execute(
                    '''INSERT INTO products (title, description, price, stock, seller_id, category, img_url, created_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (title, description, price, stock, user_id, category, img_url, now_iso)
                )
        
        db.commit()
        product_id = cursor.lastrowid
        
        # Handle multiple images if provided
        image_urls = data.get('image_urls', [])
        app.logger.info(f'[CREATE PRODUCT] Received image_urls: {image_urls} (type: {type(image_urls)})')
        
        if isinstance(image_urls, str):
            # If single string, convert to list
            image_urls = [image_urls] if image_urls else []
        elif not isinstance(image_urls, list):
            image_urls = []
        
        # If img_url is provided but not in image_urls, add it as the first image
        if img_url and img_url not in image_urls:
            image_urls.insert(0, img_url)
        
        app.logger.info(f'[CREATE PRODUCT] Final image_urls to save: {image_urls} for product {product_id}')
        
        # Insert images into product_images table
        if image_urls:
            try:
                # Check if table exists first
                if DB_ENGINE == 'mysql':
                    cursor.execute("SHOW TABLES LIKE 'product_images'")
                    table_exists = cursor.fetchone() is not None
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_images'")
                    table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    app.logger.error('[CREATE PRODUCT] product_images table does not exist!')
                else:
                    for idx, img_url_val in enumerate(image_urls):
                        if img_url_val and img_url_val.strip():
                            try:
                                if DB_ENGINE == 'mysql':
                                    cursor.execute(
                                        'INSERT INTO product_images (product_id, image_url, display_order) VALUES (%s, %s, %s)',
                                        (product_id, img_url_val.strip(), idx)
                                    )
                                else:
                                    cursor.execute(
                                        'INSERT INTO product_images (product_id, image_url, display_order) VALUES (?, ?, ?)',
                                        (product_id, img_url_val.strip(), idx)
                                    )
                                app.logger.info(f'[CREATE PRODUCT] Inserted image {idx}: {img_url_val.strip()}')
                            except Exception as insert_err:
                                app.logger.error(f'[CREATE PRODUCT] Failed to insert image {idx} ({img_url_val}): {insert_err}')
                    db.commit()
                    app.logger.info(f'[CREATE PRODUCT] Successfully saved {len(image_urls)} images for product {product_id}')
            except Exception as img_err:
                app.logger.error(f'[CREATE PRODUCT] Could not save product images: {img_err}')
                import traceback
                app.logger.error(traceback.format_exc())
                # Continue even if images fail to save
        
        return success_response({
            'product_id': product_id,
            'title': title,
            'price': price,
            'stock': stock,
            'category': category,
            'seller_id': user_id,
            'store_id': store_id,
            'image_urls': image_urls,
            'created_at': datetime.now().isoformat()
        }, 'Product created and added to your shop')
    except ValueError as ve:
        return error_response(f'Invalid data: {str(ve)}', 400)
    except Exception as e:
        return error_response(str(e), 500)

def get_product_images(cursor, product_id):
    """Helper function to fetch all images for a product"""
    try:
        # Check if product_images table exists
        if DB_ENGINE == 'mysql':
            cursor.execute("SHOW TABLES LIKE 'product_images'")
            table_exists = cursor.fetchone() is not None
        else:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_images'")
            table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            app.logger.warning(f'[GET IMAGES] product_images table does not exist for product {product_id}')
            return []
        
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'SELECT image_url FROM product_images WHERE product_id=%s ORDER BY display_order ASC',
                (product_id,)
            )
        else:
            cursor.execute(
                'SELECT image_url FROM product_images WHERE product_id=? ORDER BY display_order ASC',
                (product_id,)
            )
        images = cursor.fetchall()
        
        if not images:
            app.logger.debug(f'[GET IMAGES] No images found for product {product_id}')
            return []
        
        result = []
        if isinstance(images[0], dict):
            result = [img['image_url'] for img in images]
        else:
            result = [img[0] for img in images]
        
        app.logger.debug(f'[GET IMAGES] Found {len(result)} images for product {product_id}: {result}')
        return result
    except Exception as e:
        app.logger.error(f'[GET IMAGES] Error fetching product images for product {product_id}: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return []

@app.route('/api/sellers/products', methods=['GET'])
@token_required
def api_seller_list_products():
    """Seller views their products - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)  # Get store_id from query params
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists in products table
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build query based on whether store_id is provided and column exists
        if store_id and store_id_column_exists:
            # Filter by both seller_id and store_id
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT * FROM products WHERE seller_id=%s AND store_id=%s ORDER BY created_at DESC', (seller_id, store_id))
            else:
                cursor.execute('SELECT * FROM products WHERE seller_id=? AND store_id=? ORDER BY created_at DESC', (seller_id, store_id))
        else:
            # Filter by seller_id only, and if store_id column exists, only get products without store_id or with store_id=0
            if store_id_column_exists:
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT * FROM products WHERE seller_id=%s AND (store_id IS NULL OR store_id=0) ORDER BY created_at DESC', (seller_id,))
                else:
                    cursor.execute('SELECT * FROM products WHERE seller_id=? AND (store_id IS NULL OR store_id=0) ORDER BY created_at DESC', (seller_id,))
            else:
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT * FROM products WHERE seller_id=%s ORDER BY created_at DESC', (seller_id,))
                else:
                    cursor.execute('SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC', (seller_id,))
        
        products = cursor.fetchall()
        formatted_products = format_rows(products)
        
        # Add image_urls to each product
        for product in formatted_products:
            product_id = product.get('id')
            if product_id:
                product['image_urls'] = get_product_images(cursor, product_id)
                # Keep img_url for backward compatibility
                if not product.get('img_url') and product['image_urls']:
                    product['img_url'] = product['image_urls'][0]
        
        cursor.close()
        
        return success_response(formatted_products, 'Products fetched')
    except Exception as e:
        app.logger.error(f'list_products error: {e}')
        return error_response(str(e), 500)

@app.route('/api/sellers/products/<int:product_id>', methods=['GET'])
@token_required
def api_seller_get_product(product_id):
    """Seller gets a single product"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get product and verify ownership
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT * FROM products WHERE id=%s', (product_id,))
        else:
            cursor.execute('SELECT * FROM products WHERE id=?', (product_id,))
        
        product_row = cursor.fetchone()
        if not product_row:
            cursor.close()
            return error_response('Product not found', 404)
        
        product = format_row(product_row)
        
        # Verify ownership
        if product.get('seller_id') != seller_id:
            cursor.close()
            return error_response('Not authorized', 403)
        
        # Add image_urls array
        product_id_val = product.get('id')
        if product_id_val:
            product['image_urls'] = get_product_images(cursor, product_id_val)
            # Keep img_url for backward compatibility if not set
            if not product.get('img_url') and product['image_urls']:
                product['img_url'] = product['image_urls'][0]
        
        cursor.close()
        
        return success_response(product, 'Product fetched')
    except Exception as e:
        app.logger.error(f'get_product error: {e}')
        return error_response(str(e), 500)

@app.route('/api/sellers/products/<int:product_id>', methods=['PUT'])
@token_required
def api_seller_update_product(product_id):
    """Seller edits a product"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify ownership
        ownership_query = 'SELECT seller_id FROM products WHERE id=%s' if DB_ENGINE == 'mysql' else 'SELECT seller_id FROM products WHERE id=?'
        cursor.execute(ownership_query, (product_id,))
        result = cursor.fetchone()
        owner_id = result[0] if isinstance(result, (tuple, list)) else result.get('seller_id')
        if not owner_id or owner_id != seller_id:
            return error_response('Not authorized', 403)
        
        data = request.json
        
        # Check if date columns exist
        has_dates = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'manufacture_date'")
                has_manufacture = cursor.fetchone() is not None
                cursor.execute("SHOW COLUMNS FROM products LIKE 'expiry_date'")
                has_expiry = cursor.fetchone() is not None
                has_dates = has_manufacture and has_expiry
            else:
                cursor.execute("PRAGMA table_info('products')")
                cols = cursor.fetchall()
                col_names = [col[1] if isinstance(col, tuple) else col['name'] for col in cols]
                has_dates = 'manufacture_date' in col_names and 'expiry_date' in col_names
        except Exception as check_err:
            app.logger.warning(f'Could not check for date columns: {check_err}')
            has_dates = False
        
        updates = []
        params = []
        
        placeholder = '%s' if DB_ENGINE == 'mysql' else '?'
        # Base fields that should always exist
        base_fields = ['title', 'description', 'price', 'stock', 'category', 'img_url']
        for field in base_fields:
            if field in data:
                updates.append(f'{field}={placeholder}')
                params.append(data[field])
        
        # Date fields - only include if columns exist
        if has_dates:
            for field in ['manufacture_date', 'expiry_date']:
                if field in data:
                    updates.append(f'{field}={placeholder}')
                    params.append(data[field])
        
        # Store ID if provided
        if 'store_id' in data:
            # Check if store_id column exists
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                    has_store = cursor.fetchone() is not None
                else:
                    cursor.execute("PRAGMA table_info('products')")
                    cols = cursor.fetchall()
                    col_names = [col[1] if isinstance(col, tuple) else col['name'] for col in cols]
                    has_store = 'store_id' in col_names
                
                if has_store:
                    updates.append(f'store_id={placeholder}')
                    params.append(data['store_id'])
            except Exception:
                pass  # Skip store_id if column doesn't exist
        
        if not updates:
            return error_response('No fields to update', 400)
        
        params.append(product_id)
        query = f'UPDATE products SET {", ".join(updates)} WHERE id={placeholder}'
        cursor.execute(query, tuple(params))
        db.commit()
        
        # Handle multiple images if provided
        image_urls = data.get('image_urls', None)
        app.logger.info(f'[UPDATE PRODUCT] Received image_urls: {image_urls} (type: {type(image_urls)}) for product {product_id}')
        
        if image_urls is not None:
            # Delete existing images
            try:
                # Check if table exists first
                if DB_ENGINE == 'mysql':
                    cursor.execute("SHOW TABLES LIKE 'product_images'")
                    table_exists = cursor.fetchone() is not None
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_images'")
                    table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    app.logger.error('[UPDATE PRODUCT] product_images table does not exist!')
                else:
                    # Delete existing images
                    if DB_ENGINE == 'mysql':
                        cursor.execute('DELETE FROM product_images WHERE product_id=%s', (product_id,))
                    else:
                        cursor.execute('DELETE FROM product_images WHERE product_id=?', (product_id,))
                    app.logger.info(f'[UPDATE PRODUCT] Deleted existing images for product {product_id}')
                    
                    # Insert new images
                    if isinstance(image_urls, str):
                        image_urls = [image_urls] if image_urls else []
                    elif not isinstance(image_urls, list):
                        image_urls = []
                    
                    # If img_url is provided but not in image_urls, add it as the first image
                    img_url = data.get('img_url')
                    if img_url and img_url not in image_urls:
                        image_urls.insert(0, img_url)
                    
                    app.logger.info(f'[UPDATE PRODUCT] Inserting {len(image_urls)} images for product {product_id}')
                    
                    for idx, img_url_val in enumerate(image_urls):
                        if img_url_val and img_url_val.strip():
                            try:
                                if DB_ENGINE == 'mysql':
                                    cursor.execute(
                                        'INSERT INTO product_images (product_id, image_url, display_order) VALUES (%s, %s, %s)',
                                        (product_id, img_url_val.strip(), idx)
                                    )
                                else:
                                    cursor.execute(
                                        'INSERT INTO product_images (product_id, image_url, display_order) VALUES (?, ?, ?)',
                                        (product_id, img_url_val.strip(), idx)
                                    )
                                app.logger.info(f'[UPDATE PRODUCT] Inserted image {idx}: {img_url_val.strip()}')
                            except Exception as insert_err:
                                app.logger.error(f'[UPDATE PRODUCT] Failed to insert image {idx} ({img_url_val}): {insert_err}')
                    db.commit()
                    app.logger.info(f'[UPDATE PRODUCT] Successfully updated {len(image_urls)} images for product {product_id}')
            except Exception as img_err:
                app.logger.error(f'[UPDATE PRODUCT] Could not update product images: {img_err}')
                import traceback
                app.logger.error(traceback.format_exc())
                # Continue even if images fail to save
        
        return success_response({'product_id': product_id}, 'Product updated')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/sellers/products/<int:product_id>', methods=['DELETE'])
@token_required
def api_seller_delete_product(product_id):
    """Seller delists a product"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify ownership
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT seller_id FROM products WHERE id=%s', (product_id,))
        else:
            cursor.execute('SELECT seller_id FROM products WHERE id=?', (product_id,))
        result = cursor.fetchone()
        
        if not result:
            return error_response('Product not found', 404)
        
        owner_id = result['seller_id'] if isinstance(result, dict) else result[0]
        if owner_id != seller_id:
            return error_response('Not authorized', 403)
        
        # Delete product
        if DB_ENGINE == 'mysql':
            cursor.execute('DELETE FROM products WHERE id=%s', (product_id,))
        else:
            cursor.execute('DELETE FROM products WHERE id=?', (product_id,))
        db.commit()
        cursor.close()
        
        return success_response({'product_id': product_id}, 'Product deleted successfully')
    except Exception as e:
        app.logger.error(f'Delete product error: {e}')
        return error_response(str(e), 500)

# ============== Product Variations API ==============
# Variations endpoint implemented earlier in this file at `api_get_product_variations`.
# Seller/admin variation management endpoints follow.
@app.route('/api/sellers/products/<int:product_id>/variations', methods=['POST'])
@token_required
def api_seller_add_variation(product_id):
    """Seller adds a variation to their product"""
    app.logger.info(f'[VARIATION] POST request for product {product_id}')
    token = get_token_from_request()
    if not token:
        app.logger.error('[VARIATION] No token provided')
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        app.logger.info(f'[VARIATION] Seller {seller_id} adding variation to product {product_id}')
        
        # Verify product ownership
        conn = get_db()
        cur = conn.cursor()
        
        if DB_ENGINE == 'mysql':
            cur.execute('SELECT seller_id FROM products WHERE id=%s', (product_id,))
        else:
            cur.execute('SELECT seller_id FROM products WHERE id=?', (product_id,))
        
        product = cur.fetchone()
        if not product:
            app.logger.error(f'[VARIATION] Product {product_id} not found')
            return error_response('Product not found', 404)
        # Handle both tuple and dict cursor rows
        owner_id = product['seller_id'] if isinstance(product, dict) else product[0]
        if owner_id != seller_id:
            app.logger.error(f'[VARIATION] Seller {seller_id} does not own product {product_id} (owned by {product[0]})')
            return error_response('Not authorized', 403)
        
        data = request.json
        app.logger.info(f'[VARIATION] Received data: {data}')
        variation_type = data.get('variation_type', '').strip()
        variation_value = data.get('variation_value', '').strip()
        price_adjustment = float(data.get('price_adjustment', 0))
        stock = int(data.get('stock', 0))
        sku = data.get('sku', '').strip() or None
        
        if not variation_type or not variation_value:
            app.logger.error(f'[VARIATION] Missing required fields: type={variation_type}, value={variation_value}')
            return error_response('variation_type and variation_value required', 400)
        
        # Insert variation
        app.logger.info(f'[VARIATION] Inserting: type={variation_type}, value={variation_value}, price={price_adjustment}, stock={stock}, sku={sku}')
        if DB_ENGINE == 'mysql':
            cur.execute("""
                INSERT INTO product_variation_options 
                (product_id, variation_type, variation_value, price_adjustment, stock, sku, is_available)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
            """, (product_id, variation_type, variation_value, price_adjustment, stock, sku))
        else:
            cur.execute("""
                INSERT INTO product_variation_options 
                (product_id, variation_type, variation_value, price_adjustment, stock, sku, is_available)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (product_id, variation_type, variation_value, price_adjustment, stock, sku))
        
        variation_id = cur.lastrowid
        conn.commit()
        cur.close()
        
        app.logger.info(f'[VARIATION] Successfully saved variation ID {variation_id}')
        return success_response({
            'variation_id': variation_id,
            'product_id': product_id,
            'variation_type': variation_type,
            'variation_value': variation_value,
            'price_adjustment': price_adjustment,
            'stock': stock
        }, 'Variation added successfully')
        
    except Exception as e:
        app.logger.error(f'[VARIATION] Error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/products/<int:product_id>/variations', methods=['GET'])
@token_required
def api_seller_get_variations(product_id):
    """Seller views variations for their product"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        conn = get_db()
        cur = conn.cursor()
        
        # Verify product ownership
        if DB_ENGINE == 'mysql':
            cur.execute('SELECT seller_id FROM products WHERE id=%s', (product_id,))
        else:
            cur.execute('SELECT seller_id FROM products WHERE id=?', (product_id,))
        
        product = cur.fetchone()
        if not product:
            return error_response('Product not found', 404)
        
        owner_id = product['seller_id'] if isinstance(product, dict) else product[0]
        if owner_id != seller_id:
            return error_response('Not authorized', 403)
        
        # Fetch variations
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT id, product_id, variation_type, variation_value, 
                       price_adjustment, stock, sku, is_available, created_at
                FROM product_variation_options 
                WHERE product_id = %s
                ORDER BY variation_type, variation_value
            """, (product_id,))
        else:
            cur.execute("""
                SELECT id, product_id, variation_type, variation_value, 
                       price_adjustment, stock, sku, is_available, created_at
                FROM product_variation_options 
                WHERE product_id = ?
                ORDER BY variation_type, variation_value
            """, (product_id,))
        
        variations = cur.fetchall()
        cur.close()
        
        variations_list = []
        for row in variations:
            var = row2dict(row) if hasattr(row, 'keys') else dict(zip([
                'id', 'product_id', 'variation_type', 'variation_value',
                'price_adjustment', 'stock', 'sku', 'is_available', 'created_at'
            ], row))
            variations_list.append(var)
        
        return success_response(variations_list, 'Variations fetched')
        
    except Exception as e:
        app.logger.error(f'get_variations error: {e}')
        return error_response(str(e), 500)

@app.route('/api/sellers/products/<int:product_id>/variations/<int:variation_id>', methods=['PUT'])
@token_required
def api_seller_update_variation(product_id, variation_id):
    """Seller updates a variation"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        conn = get_db()
        cur = conn.cursor()
        
        # Verify ownership
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT p.seller_id 
                FROM products p
                INNER JOIN product_variation_options v ON p.id = v.product_id
                WHERE p.id = %s AND v.id = %s
            """, (product_id, variation_id))
        else:
            cur.execute("""
                SELECT p.seller_id 
                FROM products p
                INNER JOIN product_variation_options v ON p.id = v.product_id
                WHERE p.id = ? AND v.id = ?
            """, (product_id, variation_id))
        
        result = cur.fetchone()
        if not result or result[0] != seller_id:
            return error_response('Not authorized', 403)
        
        data = request.json
        updates = []
        params = []
        
        if 'variation_value' in data:
            updates.append('variation_value = %s' if DB_ENGINE == 'mysql' else 'variation_value = ?')
            params.append(data['variation_value'])
        if 'price_adjustment' in data:
            updates.append('price_adjustment = %s' if DB_ENGINE == 'mysql' else 'price_adjustment = ?')
            params.append(float(data['price_adjustment']))
        if 'stock' in data:
            updates.append('stock = %s' if DB_ENGINE == 'mysql' else 'stock = ?')
            params.append(int(data['stock']))
        if 'is_available' in data:
            updates.append('is_available = %s' if DB_ENGINE == 'mysql' else 'is_available = ?')
            params.append(1 if data['is_available'] else 0)
        
        if not updates:
            return error_response('No fields to update', 400)
        
        params.append(variation_id)
        query = f"UPDATE product_variation_options SET {', '.join(updates)} WHERE id = {'%s' if DB_ENGINE == 'mysql' else '?'}"
        cur.execute(query, tuple(params))
        conn.commit()
        cur.close()
        
        return success_response({'variation_id': variation_id}, 'Variation updated')
        
    except Exception as e:
        app.logger.error(f'update_variation error: {e}')
        return error_response(str(e), 500)

@app.route('/api/sellers/products/<int:product_id>/variations/<int:variation_id>', methods=['DELETE'])
@token_required
def api_seller_delete_variation(product_id, variation_id):
    """Seller deletes a variation"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        conn = get_db()
        cur = conn.cursor()
        
        # Verify ownership
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT p.seller_id 
                FROM products p
                INNER JOIN product_variation_options v ON p.id = v.product_id
                WHERE p.id = %s AND v.id = %s
            """, (product_id, variation_id))
        else:
            cur.execute("""
                SELECT p.seller_id 
                FROM products p
                INNER JOIN product_variation_options v ON p.id = v.product_id
                WHERE p.id = ? AND v.id = ?
            """, (product_id, variation_id))
        
        result = cur.fetchone()
        if not result:
            return error_response('Variation not found', 404)
        
        # Handle both dict and tuple cursor results
        owner_id = result['seller_id'] if isinstance(result, dict) else result[0]
        if owner_id != seller_id:
            return error_response('Not authorized', 403)
        
        if DB_ENGINE == 'mysql':
            cur.execute('DELETE FROM product_variation_options WHERE id = %s', (variation_id,))
        else:
            cur.execute('DELETE FROM product_variation_options WHERE id = ?', (variation_id,))
        
        conn.commit()
        cur.close()
        
        return success_response({'variation_id': variation_id}, 'Variation deleted')
        
    except Exception as e:
        app.logger.error(f'delete_variation error: {e}')
        return error_response(str(e), 500)

@app.route('/api/sellers/orders', methods=['GET'])
@token_required
def api_seller_get_orders():
    """Seller views their incoming orders - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)  # Get store_id from query params
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists in products table
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build query based on whether store_id is provided and column exists
        if store_id and store_id_column_exists:
            # Filter by both seller_id and store_id
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT DISTINCT o.id, o.customer_id, o.customer_name, o.customer_phone, 
                           o.customer_address, o.subtotal, o.delivery_fee, o.total, 
                           o.status, o.created_at
                    FROM orders o
                    INNER JOIN order_items oi ON o.id = oi.order_id
                    INNER JOIN products p ON oi.product_id = p.id
                    WHERE p.seller_id = %s AND p.store_id = %s
                    ORDER BY o.created_at DESC
                ''', (seller_id, store_id))
            else:
                cursor.execute('''
                    SELECT DISTINCT o.id, o.customer_id, o.customer_name, o.customer_phone, 
                           o.customer_address, o.subtotal, o.delivery_fee, o.total, 
                           o.status, o.created_at
                    FROM orders o
                    INNER JOIN order_items oi ON o.id = oi.order_id
                    INNER JOIN products p ON oi.product_id = p.id
                    WHERE p.seller_id = ? AND p.store_id = ?
                    ORDER BY o.created_at DESC
                ''', (seller_id, store_id))
        else:
            # Filter by seller_id only, and if store_id column exists, only get orders for products without store_id or with store_id=0
            if store_id_column_exists:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        SELECT DISTINCT o.id, o.customer_id, o.customer_name, o.customer_phone, 
                               o.customer_address, o.subtotal, o.delivery_fee, o.total, 
                               o.status, o.created_at
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)
                        ORDER BY o.created_at DESC
                    ''', (seller_id,))
                else:
                    cursor.execute('''
                        SELECT DISTINCT o.id, o.customer_id, o.customer_name, o.customer_phone, 
                               o.customer_address, o.subtotal, o.delivery_fee, o.total, 
                               o.status, o.created_at
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)
                        ORDER BY o.created_at DESC
                    ''', (seller_id,))
            else:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        SELECT DISTINCT o.id, o.customer_id, o.customer_name, o.customer_phone, 
                               o.customer_address, o.subtotal, o.delivery_fee, o.total, 
                               o.status, o.created_at
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = %s
                        ORDER BY o.created_at DESC
                    ''', (seller_id,))
                else:
                    cursor.execute('''
                        SELECT DISTINCT o.id, o.customer_id, o.customer_name, o.customer_phone, 
                               o.customer_address, o.subtotal, o.delivery_fee, o.total, 
                               o.status, o.created_at
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = ?
                        ORDER BY o.created_at DESC
                    ''', (seller_id,))
        
        orders = cursor.fetchall()
        result = []
        
        app.logger.info(f'api_seller_get_orders: Fetched {len(orders)} orders from database')
        
        for order in orders:
            order_dict = format_row(order)
            
            # Log raw order data for debugging
            order_id = order_dict.get('id') or (order[0] if isinstance(order, tuple) else None)
            app.logger.debug(f'Processing order #{order_id}, raw order type: {type(order)}, order_dict keys: {list(order_dict.keys()) if isinstance(order_dict, dict) else "N/A"}')
            
            # Ensure status is properly extracted
            # Handle both dict and tuple formats
            if isinstance(order, tuple):
                # Map tuple indices to field names based on SELECT order
                # SELECT: o.id, o.customer_id, o.customer_name, o.customer_phone, 
                #         o.customer_address, o.subtotal, o.delivery_fee, o.total, 
                #         COALESCE(NULLIF(TRIM(o.status), ''), 'pending') as status, o.created_at
                if len(order) >= 9:
                    raw_status = order[8] if len(order) > 8 else 'pending'
                    app.logger.debug(f'Order #{order_id}: Extracted status from tuple index 8: "{raw_status}" (type: {type(raw_status)})')
                    # Ensure status is not None, empty string, or whitespace-only
                    if not raw_status or (isinstance(raw_status, str) and not raw_status.strip()):
                        raw_status = 'pending'
                        app.logger.warning(f'Order #{order_id}: Status from tuple was empty/None, defaulted to "pending"')
                    order_dict = {
                        'id': order[0],
                        'customer_id': order[1],
                        'customer_name': order[2],
                        'customer_phone': order[3],
                        'customer_address': order[4],
                        'subtotal': order[5],
                        'delivery_fee': order[6],
                        'total': order[7],
                        'status': raw_status,
                        'created_at': order[9] if len(order) > 9 else None
                    }
            else:
                # For dict-like rows, ensure status is extracted correctly
                # The SQL query aliases the status column, so it should be in the dict
                raw_status = order_dict.get('status')
                app.logger.debug(f'Order #{order_id}: Extracted status from dict: "{raw_status}" (type: {type(raw_status)})')
            
            # Ensure status field exists and is not None, empty, or whitespace-only
            status_value = order_dict.get('status')
            if not status_value or (isinstance(status_value, str) and not status_value.strip()):
                order_dict['status'] = 'pending'
                app.logger.warning(f'Order #{order_dict.get("id")}: Status was empty/None after format_row, defaulted to "pending". Raw value was: {repr(status_value)}')
            else:
                # Trim whitespace only (preserve case)
                order_dict['status'] = status_value.strip() if isinstance(status_value, str) else status_value
                app.logger.info(f'Order #{order_dict.get("id")}: Final status = "{order_dict["status"]}"')
            
            # Get items for this order
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT oi.product_id, oi.quantity, oi.price, p.title
                    FROM order_items oi
                    INNER JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s AND p.seller_id = %s
                ''', (order_dict['id'], seller_id))
            else:
                cursor.execute('''
                    SELECT oi.product_id, oi.quantity, oi.price, p.title
                    FROM order_items oi
                    INNER JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = ? AND p.seller_id = ?
                ''', (order_dict['id'], seller_id))
            
            items = cursor.fetchall()
            order_dict['items'] = format_rows(items)
            result.append(order_dict)
        
        cursor.close()
        return success_response(result, 'Seller orders fetched')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/sellers/orders/new-count', methods=['GET'])
@token_required
def api_seller_new_orders_count():
    """Get count of new/pending orders for seller badge - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build query with store_id filter if applicable
        if store_id and store_id_column_exists:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT COUNT(DISTINCT o.id) as count
                    FROM orders o
                    INNER JOIN order_items oi ON o.id = oi.order_id
                    INNER JOIN products p ON oi.product_id = p.id
                    WHERE p.seller_id = %s AND p.store_id = %s
                    AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
                ''', (seller_id, store_id))
            else:
                cursor.execute('''
                    SELECT COUNT(DISTINCT o.id) as count
                    FROM orders o
                    INNER JOIN order_items oi ON o.id = oi.order_id
                    INNER JOIN products p ON oi.product_id = p.id
                    WHERE p.seller_id = ? AND p.store_id = ?
                    AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
                ''', (seller_id, store_id))
        else:
            # Filter by seller_id only, exclude store products if column exists
            if store_id_column_exists:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        SELECT COUNT(DISTINCT o.id) as count
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)
                        AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
                    ''', (seller_id,))
                else:
                    cursor.execute('''
                        SELECT COUNT(DISTINCT o.id) as count
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)
                        AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
                    ''', (seller_id,))
            else:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        SELECT COUNT(DISTINCT o.id) as count
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = %s
                        AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
                    ''', (seller_id,))
                else:
                    cursor.execute('''
                        SELECT COUNT(DISTINCT o.id) as count
                        FROM orders o
                        INNER JOIN order_items oi ON o.id = oi.order_id
                        INNER JOIN products p ON oi.product_id = p.id
                        WHERE p.seller_id = ?
                        AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
                    ''', (seller_id,))
        
        result = cursor.fetchone()
        count = result[0] if isinstance(result, tuple) else (result.get('count') if isinstance(result, dict) else 0)
        
        cursor.close()
        return success_response({'new_orders_count': count or 0}, 'New orders count fetched')
    except Exception as e:
        app.logger.error(f'Error fetching new orders count: {e}')
        return error_response(str(e), 500)

@app.route('/api/sellers/reviews/new-count', methods=['GET'])
@token_required
def api_seller_new_reviews_count():
    """Get count of new reviews for seller badge - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id)
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id,)
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id,)
        
        # Count reviews for products belonging to this seller
        # Consider reviews from the last 7 days as "new" (or all if no viewed_at tracking)
        # Try reviews table first (product reviews), fallback to customer_reviews if needed
        count = 0
        try:
            # Try reviews table (product reviews)
            if DB_ENGINE == 'mysql':
                cursor.execute(f'''
                    SELECT COUNT(DISTINCT r.id) as count
                    FROM reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE {product_filter}
                    AND r.product_id IS NOT NULL
                    AND r.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ''', product_params)
            else:
                cursor.execute(f'''
                    SELECT COUNT(DISTINCT r.id) as count
                    FROM reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE {product_filter}
                    AND r.product_id IS NOT NULL
                    AND r.created_at >= datetime('now', '-7 days')
                ''', product_params)
            
            result = cursor.fetchone()
            if isinstance(result, dict):
                count = result.get('count', 0)
            elif isinstance(result, tuple):
                count = result[0] if len(result) > 0 else 0
        except Exception as query_err:
            # Fallback to customer_reviews table if reviews table doesn't exist
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute(f'''
                        SELECT COUNT(DISTINCT r.id) as count
                        FROM customer_reviews r
                        INNER JOIN products p ON r.product_id = p.id
                        WHERE {product_filter}
                        AND r.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    ''', product_params)
                else:
                    cursor.execute(f'''
                        SELECT COUNT(DISTINCT r.id) as count
                        FROM customer_reviews r
                        INNER JOIN products p ON r.product_id = p.id
                        WHERE {product_filter}
                        AND r.created_at >= datetime('now', '-7 days')
                    ''', product_params)
                
                result = cursor.fetchone()
                if isinstance(result, dict):
                    count = result.get('count', 0)
                elif isinstance(result, tuple):
                    count = result[0] if len(result) > 0 else 0
            except Exception as fallback_err:
                app.logger.warning(f'Could not fetch reviews count: {fallback_err}')
                count = 0
        
        cursor.close()
        return success_response({'new_reviews_count': count or 0}, 'New reviews count fetched')
    except Exception as e:
        app.logger.error(f'Error fetching new reviews count: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/notifications/summary', methods=['GET'])
@token_required
def api_seller_notifications_summary():
    """Get summary of all notifications for seller (orders, reviews, messages)"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get new orders count
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT COUNT(DISTINCT o.id) as count
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE p.seller_id = %s
                AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT COUNT(DISTINCT o.id) as count
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE p.seller_id = ?
                AND (LOWER(COALESCE(o.status, '')) IN ('pending', 'processing', 'confirmed') OR COALESCE(o.status, '') = '')
            ''', (seller_id,))
        
        orders_result = cursor.fetchone()
        new_orders = orders_result[0] if isinstance(orders_result, tuple) else (orders_result.get('count') if isinstance(orders_result, dict) else 0)
        
        # Get new reviews count
        new_reviews = 0
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT COUNT(DISTINCT r.id) as count
                    FROM customer_reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE p.seller_id = %s
                    AND r.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ''', (seller_id,))
            else:
                cursor.execute('''
                    SELECT COUNT(DISTINCT r.id) as count
                    FROM customer_reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE p.seller_id = ?
                    AND r.created_at >= datetime('now', '-7 days')
                ''', (seller_id,))
            
            reviews_result = cursor.fetchone()
            if isinstance(reviews_result, dict):
                new_reviews = reviews_result.get('count', 0)
            elif isinstance(reviews_result, tuple):
                new_reviews = reviews_result[0] if len(reviews_result) > 0 else 0
        except Exception as reviews_err:
            # If table doesn't exist or query fails, return 0
            app.logger.warning(f'Could not fetch reviews count (table may not exist): {reviews_err}')
            new_reviews = 0
        
        # Get unread messages count (from messaging API)
        unread_messages = 0
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT COUNT(*) as count FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.seller_id = %s
                    AND m.sender_type = 'customer'
                    AND m.is_read = FALSE
                ''', (seller_id,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.seller_id = ?
                    AND m.sender_type = 'customer'
                    AND m.is_read = 0
                ''', (seller_id,))
            
            messages_result = cursor.fetchone()
            if isinstance(messages_result, dict):
                unread_messages = messages_result.get('count', 0)
            elif isinstance(messages_result, tuple):
                unread_messages = messages_result[0] if len(messages_result) > 0 else 0
        except Exception as msg_err:
            # If messages table doesn't exist or query fails, return 0
            app.logger.warning(f'Could not fetch unread messages count (table may not exist): {msg_err}')
            unread_messages = 0
        
        cursor.close()
        
        return success_response({
            'new_orders': new_orders or 0,
            'new_reviews': new_reviews or 0,
            'unread_messages': unread_messages or 0
        }, 'Notifications summary fetched')
    except Exception as e:
        app.logger.error(f'Error fetching notifications summary: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/orders/<int:order_id>', methods=['GET'])
@token_required
def api_seller_get_order_details(order_id):
    """Get detailed information about a specific order"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get order details
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT o.*, u.email as customer_email
                FROM orders o
                LEFT JOIN users u ON o.customer_id = u.id
                WHERE o.id = %s
            ''', (order_id,))
        else:
            cursor.execute('''
                SELECT o.*, u.email as customer_email
                FROM orders o
                LEFT JOIN users u ON o.customer_id = u.id
                WHERE o.id = ?
            ''', (order_id,))
        
        order = cursor.fetchone()
        if not order:
            return error_response('Order not found', 404)
        
        order_dict = format_row(order)
        
        # Verify this order contains items from this seller
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s AND p.seller_id = %s
            ''', (order_id, seller_id))
            count_row = cursor.fetchone()
            has_items = count_row['count'] > 0 if DB_ENGINE == 'mysql' else count_row[0] > 0
        else:
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ? AND p.seller_id = ?
            ''', (order_id, seller_id))
            count_row = cursor.fetchone()
            has_items = count_row[0] > 0
        
        if not has_items:
            return error_response('Order not found', 404)
        
        # Get items
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT oi.*, p.title, p.img_url
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s AND p.seller_id = %s
            ''', (order_id, seller_id))
        else:
            cursor.execute('''
                SELECT oi.*, p.title, p.img_url
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ? AND p.seller_id = ?
            ''', (order_id, seller_id))
        
        items = cursor.fetchall()
        order_dict['items'] = format_rows(items)
        
        # Parse address for shipping details (if stored as combined string)
        address = order_dict.get('customer_address', '')
        order_dict['shipping_address'] = address
        order_dict['shipping_city'] = order_dict.get('city', '')
        order_dict['shipping_postal'] = order_dict.get('postal_code', '')
        
        return success_response(order_dict)
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/sellers/orders/<int:order_id>/confirm', methods=['POST'])
@token_required
def api_seller_confirm_order(order_id):
    """Seller confirms they are processing the order"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify seller owns items in order
        cursor.execute('''
            SELECT COUNT(*) FROM order_items oi
            INNER JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ? AND p.seller_id = ?
        ''', (order_id, seller_id))
        
        if cursor.fetchone()[0] == 0:
            return error_response('Not authorized', 403)
        
        # Update order status
        cursor.execute('UPDATE orders SET status=? WHERE id=?', ('processing', order_id))
        db.commit()
        
        return success_response({'order_id': order_id, 'status': 'processing'}, 'Order confirmed')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/sellers/orders/<int:order_id>/ready', methods=['POST'])
@token_required
def api_seller_mark_ready(order_id):
    """Seller marks items as ready for pickup/delivery"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify seller owns items
        cursor.execute('''
            SELECT COUNT(*) FROM order_items oi
            INNER JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ? AND p.seller_id = ?
        ''', (order_id, seller_id))
        
        if cursor.fetchone()[0] == 0:
            return error_response('Not authorized', 403)
        
        cursor.execute('UPDATE orders SET status=? WHERE id=?', ('ready', order_id))
        db.commit()
        
        return success_response({'order_id': order_id, 'status': 'ready'}, 'Order marked ready')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/sellers/dashboard', methods=['GET'])
@token_required
def api_sellers_dashboard():
    """Seller views sales dashboard with comprehensive metrics - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        
        # Debug logging
        app.logger.info(f'[DASHBOARD] Request: seller_id={seller_id}, store_id={store_id} (type: {type(store_id).__name__}), args={dict(request.args)}')
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter condition
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id)
            app.logger.info(f'[DASHBOARD] ✅ Filtering by store_id={store_id} (product_filter: {product_filter}, params: {product_params})')
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id,)
            app.logger.info(f'[DASHBOARD] ⚠️ Filtering by main seller profile only (no store_id provided, store_id={store_id})')
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id,)
            app.logger.info(f'[DASHBOARD] ⚠️ No store_id column exists, filtering by seller_id only (store_id={store_id})')
        
        # Verify store_id_column_exists status
        app.logger.info(f'[DASHBOARD] store_id_column_exists={store_id_column_exists}, store_id={store_id}, seller_id={seller_id}')
        
        # Build products count filter
        if store_id and store_id_column_exists:
            products_filter = 'seller_id = %s AND store_id = %s' if DB_ENGINE == 'mysql' else 'seller_id = ? AND store_id = ?'
            products_params = (seller_id, store_id)
        elif store_id_column_exists:
            products_filter = 'seller_id = %s AND (store_id IS NULL OR store_id = 0)' if DB_ENGINE == 'mysql' else 'seller_id = ? AND (store_id IS NULL OR store_id = 0)'
            products_params = (seller_id,)
        else:
            products_filter = 'seller_id = %s' if DB_ENGINE == 'mysql' else 'seller_id = ?'
            products_params = (seller_id,)
        
        # Sales Today
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.price * oi.quantity), 0) 
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter}
                AND DATE(o.created_at) = CURDATE()
                AND o.status IN ('delivered', 'dispatched', 'processing')
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.price * oi.quantity), 0) 
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter}
                AND DATE(o.created_at) = DATE('now')
                AND o.status IN ('delivered', 'dispatched', 'processing')
            ''', product_params)
        result = cursor.fetchone()
        sales_today = float(result[0] if isinstance(result, (tuple, list)) else (result.get(list(result.keys())[0]) if result else 0))
        
        # Sales This Month
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.price * oi.quantity), 0) 
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter}
                AND YEAR(o.created_at) = YEAR(CURDATE())
                AND MONTH(o.created_at) = MONTH(CURDATE())
                AND o.status IN ('delivered', 'dispatched', 'processing')
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.price * oi.quantity), 0) 
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter}
                AND strftime('%Y-%m', o.created_at) = strftime('%Y-%m', 'now')
                AND o.status IN ('delivered', 'dispatched', 'processing')
            ''', product_params)
        result = cursor.fetchone()
        sales_month = float(result[0] if isinstance(result, (tuple, list)) else (result.get(list(result.keys())[0]) if result else 0))
        
        # Total Revenue (All Time)
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.price * oi.quantity), 0) 
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter} AND o.status IN ('delivered', 'dispatched', 'processing')
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT COALESCE(SUM(oi.price * oi.quantity), 0) 
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter} AND o.status IN ('delivered', 'dispatched', 'processing')
            ''', product_params)
        result = cursor.fetchone()
        total_revenue = float(result[0] if isinstance(result, (tuple, list)) else (result.get(list(result.keys())[0]) if result else 0))
        
        # Pending Orders
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COUNT(DISTINCT o.id) FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND o.status IN ('placed', 'processing')
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT COUNT(DISTINCT o.id) FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND o.status IN ('placed', 'processing')
            ''', product_params)
        result = cursor.fetchone()
        pending_orders = int(result[0] if isinstance(result, (tuple, list)) else (result.get(list(result.keys())[0]) if result else 0))
        
        # Total Orders
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COUNT(DISTINCT o.id) FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT COUNT(DISTINCT o.id) FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
            ''', product_params)
        result = cursor.fetchone()
        total_orders = int(result[0] if isinstance(result, (tuple, list)) else (result.get(list(result.keys())[0]) if result else 0))
        app.logger.info(f'[DASHBOARD] Total Orders: {total_orders} (filter: {product_filter}, params: {product_params})')
        
        # Average Rating (placeholder - would use reviews table)
        avg_rating = 4.5  # Default rating
        
        # Products count
        if DB_ENGINE == 'mysql':
            cursor.execute(f'SELECT COUNT(*) FROM products WHERE {products_filter}', products_params)
        else:
            cursor.execute(f'SELECT COUNT(*) FROM products WHERE {products_filter}', products_params)
        result = cursor.fetchone()
        products_count = int(result[0] if isinstance(result, (tuple, list)) else (result.get(list(result.keys())[0]) if result else 0))
        app.logger.info(f'[DASHBOARD] Products Count: {products_count} (filter: {products_filter}, params: {products_params})')
        
        # Seller info
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT s.business_name, s.verified FROM sellers s WHERE s.user_id=%s', (seller_id,))
        else:
            cursor.execute('SELECT s.business_name, s.verified FROM sellers s WHERE s.user_id=?', (seller_id,))
        seller_info = cursor.fetchone()
        if seller_info:
            business_name = seller_info['business_name'] if isinstance(seller_info, dict) else seller_info[0]
            verified = seller_info['verified'] if isinstance(seller_info, dict) else seller_info[1]
        else:
            business_name = 'N/A'
            verified = 0
        
        cursor.close()
        
        # Log final results
        app.logger.info(f'[DASHBOARD] Final Results for store_id={store_id}: orders={total_orders}, pending={pending_orders}, sales_today={sales_today}, sales_month={sales_month}, products={products_count}')
        
        return success_response({
            'sales_today': round(sales_today, 2),
            'sales_month': round(sales_month, 2),
            'total_revenue': round(total_revenue, 2),
            'pending_orders': pending_orders,
            'total_orders': total_orders,
            'avg_rating': round(avg_rating, 1),
            'verified': bool(verified),
            'business_name': business_name,
            'products_count': products_count
        }, 'Dashboard data')
    except Exception as e:
        app.logger.error('sellers_dashboard error: %s', e, exc_info=True)
        return error_response(str(e), 500)

@app.route('/api/sellers/top-products', methods=['GET'])
@token_required
def api_seller_top_products():
    """Get top-selling products for seller - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        limit = int(request.args.get('limit', 10))
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id, limit)
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id, limit)
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id, limit)
        
        # Get top products by quantity sold
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT p.id, p.title, p.img_url, p.category, p.price, p.stock,
                       COALESCE(SUM(oi.quantity), 0) as total_sold,
                       COALESCE(SUM(oi.price * oi.quantity), 0) as total_revenue
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter}
                AND (o.status IN ('delivered', 'dispatched', 'processing') OR o.status IS NULL)
                GROUP BY p.id, p.title, p.img_url, p.category, p.price, p.stock
                ORDER BY total_sold DESC
                LIMIT %s
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT p.id, p.title, p.img_url, p.category, p.price, p.stock,
                       COALESCE(SUM(oi.quantity), 0) as total_sold,
                       COALESCE(SUM(oi.price * oi.quantity), 0) as total_revenue
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id
                WHERE {product_filter}
                AND (o.status IN ('delivered', 'dispatched', 'processing') OR o.status IS NULL)
                GROUP BY p.id
                ORDER BY total_sold DESC
                LIMIT ?
            ''', product_params)
        
        products = []
        for row in cursor.fetchall():
            product = row2dict(row) if hasattr(row, 'keys') else {
                'id': row[0],
                'title': row[1],
                'img_url': row[2],
                'category': row[3],
                'price': float(row[4]),
                'stock': int(row[5]),
                'total_sold': int(row[6]),
                'total_revenue': float(row[7])
            }
            products.append(product)
        
        cursor.close()
        return success_response(products, f'{len(products)} top products')
    except Exception as e:
        app.logger.error('top_products error: %s', e, exc_info=True)
        return error_response(str(e), 500)

@app.route('/api/sellers/recent-activities', methods=['GET'])
@token_required
def api_seller_recent_activities():
    """Get recent customer activities for seller - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        limit = int(request.args.get('limit', 20))
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter condition
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id, limit)
            app.logger.info(f'[RECENT_ACTIVITIES] Filtering by store_id={store_id}')
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id, limit)
            app.logger.info(f'[RECENT_ACTIVITIES] Filtering by main seller profile only (no store_id provided)')
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id, limit)
            app.logger.info(f'[RECENT_ACTIVITIES] No store_id column exists, filtering by seller_id only')
        
        # Get recent orders
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT DISTINCT o.id, o.customer_name, o.status, o.total, o.created_at,
                       'order' as activity_type
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                ORDER BY o.created_at DESC
                LIMIT %s
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT DISTINCT o.id, o.customer_name, o.status, o.total, o.created_at,
                       'order' as activity_type
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                ORDER BY o.created_at DESC
                LIMIT ?
            ''', product_params)
        
        activities = []
        for row in cursor.fetchall():
            activity = row2dict(row) if hasattr(row, 'keys') else {
                'id': row[0],
                'customer_name': row[1],
                'status': row[2],
                'total': float(row[3]),
                'created_at': str(row[4]),
                'activity_type': row[5]
            }
            activities.append(activity)
        
        app.logger.info(f'[RECENT_ACTIVITIES] Found {len(activities)} activities for store_id={store_id} (filter: {product_filter})')
        cursor.close()
        return success_response(activities, f'{len(activities)} recent activities')
    except Exception as e:
        app.logger.error('recent_activities error: %s', e, exc_info=True)
        return error_response(str(e), 500)

@app.route('/api/sellers/revenue-trend', methods=['GET'])
@token_required
def api_seller_revenue_trend():
    """Get revenue trend data for charts - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        period = request.args.get('period', '30')  # days
        days = int(period)
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id, days) if DB_ENGINE == 'mysql' else (seller_id, store_id, f'-{days}')
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id, days) if DB_ENGINE == 'mysql' else (seller_id, f'-{days}')
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id, days) if DB_ENGINE == 'mysql' else (seller_id, f'-{days}')
        
        # Get daily revenue for the period
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT DATE(o.created_at) as date, 
                       COALESCE(SUM(oi.price * oi.quantity), 0) as revenue,
                       COUNT(DISTINCT o.id) as orders
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                AND o.status IN ('delivered', 'dispatched', 'processing')
                GROUP BY DATE(o.created_at)
                ORDER BY date ASC
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT DATE(o.created_at) as date, 
                       COALESCE(SUM(oi.price * oi.quantity), 0) as revenue,
                       COUNT(DISTINCT o.id) as orders
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.created_at >= date('now', ? || ' days')
                AND o.status IN ('delivered', 'dispatched', 'processing')
                GROUP BY DATE(o.created_at)
                ORDER BY date ASC
            ''', product_params)
        
        trend_data = []
        for row in cursor.fetchall():
            data = row2dict(row) if hasattr(row, 'keys') else {
                'date': str(row[0]),
                'revenue': float(row[1]),
                'orders': int(row[2])
            }
            trend_data.append(data)
        
        cursor.close()
        return success_response(trend_data, f'Revenue trend for {days} days')
    except Exception as e:
        app.logger.error('revenue_trend error: %s', e, exc_info=True)
        return error_response(str(e), 500)

@app.route('/api/sellers/order-growth', methods=['GET'])
@token_required
def api_seller_order_growth():
    """Get order growth statistics - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        store_id = request.args.get('store_id', type=int)
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id)
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id,)
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id,)
        
        # Orders this month vs last month
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT 
                    COUNT(CASE WHEN YEAR(o.created_at) = YEAR(CURDATE()) 
                              AND MONTH(o.created_at) = MONTH(CURDATE()) THEN 1 END) as this_month,
                    COUNT(CASE WHEN YEAR(o.created_at) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                              AND MONTH(o.created_at) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) THEN 1 END) as last_month
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT 
                    COUNT(CASE WHEN strftime('%Y-%m', o.created_at) = strftime('%Y-%m', 'now') THEN 1 END) as this_month,
                    COUNT(CASE WHEN strftime('%Y-%m', o.created_at) = strftime('%Y-%m', 'now', '-1 month') THEN 1 END) as last_month
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
            ''', product_params)
        
        row = cursor.fetchone()
        this_month = int(row['this_month'] if isinstance(row, dict) else row[0] or 0)
        last_month = int(row['last_month'] if isinstance(row, dict) else row[1] or 0)
        
        # Calculate growth percentage
        growth_percentage = 0
        if last_month > 0:
            growth_percentage = ((this_month - last_month) / last_month) * 100
        elif this_month > 0:
            growth_percentage = 100
        
        cursor.close()
        return success_response({
            'this_month': this_month,
            'last_month': last_month,
            'growth_percentage': round(growth_percentage, 1),
            'growth_direction': 'up' if growth_percentage > 0 else 'down' if growth_percentage < 0 else 'stable'
        }, 'Order growth data')
    except Exception as e:
        app.logger.error('order_growth error: %s', e, exc_info=True)
        return error_response(str(e), 500)

# ==================== RIDER ENDPOINTS ====================

@app.route('/api/riders/available-orders', methods=['GET'])
@token_required
def api_rider_available_orders():
    """Rider views available orders to accept"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    cursor = None
    try:
        payload = verify_token(token)
        rider_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # First, check if rider_id column exists in orders table
        # If not, we'll use a simpler query
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM orders LIKE 'rider_id'")
                has_rider_id = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(orders)")
                columns = cursor.fetchall()
                has_rider_id = any(col[1] == 'rider_id' if isinstance(col, tuple) else col.get('name') == 'rider_id' for col in columns)
        except Exception as col_check_err:
            app.logger.warning(f'Could not check for rider_id column: {col_check_err}')
            has_rider_id = False
        
        # Build the WHERE clause based on whether rider_id exists
        if has_rider_id:
            rider_condition = "AND (o.rider_id IS NULL OR o.rider_id = 0)"
        else:
            rider_condition = ""
        
        # Get orders ready for delivery (status='ready' or 'placed')
        # Use a simpler approach: get orders first, then enrich with items
        # Also include 'pending' status in case some orders are still in that state
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
            SELECT o.id, o.customer_name, o.customer_address, o.customer_phone, 
                       o.subtotal, o.delivery_fee, o.total, o.created_at, o.status
            FROM orders o
                WHERE o.status IN ('ready', 'placed', 'pending') {rider_condition}
                ORDER BY o.created_at ASC
            ''')
        else:
            cursor.execute(f'''
                SELECT o.id, o.customer_name, o.customer_address, o.customer_phone, 
                       o.subtotal, o.delivery_fee, o.total, o.created_at, o.status
                FROM orders o
                WHERE o.status IN ('ready', 'placed', 'pending') {rider_condition}
            ORDER BY o.created_at ASC
        ''')
        
        orders = cursor.fetchall()
        
        # Log for debugging
        app.logger.info(f'Found {len(orders)} available orders for riders (status: ready/placed/pending, rider_id: NULL/0)')
        
        # Format orders and enrich with items and seller names
        result = []
        for order_row in orders:
            order = format_row(order_row)
            order_id = order.get('id')
            
            # Get items for this order
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        SELECT p.title
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = %s
                    ''', (order_id,))
                else:
                    cursor.execute('''
                        SELECT p.title
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = ?
                    ''', (order_id,))
                
                items_rows = cursor.fetchall()
                items = [row[0] if isinstance(row, tuple) else row.get('title', '') for row in items_rows if row]
                order['items'] = ', '.join(items) if items else 'N/A'
                order['items_count'] = len(items)
            except Exception as items_err:
                app.logger.warning(f'Could not fetch items for order {order_id}: {items_err}')
                order['items'] = 'N/A'
                order['items_count'] = 0
            
            # Get seller name for this order
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        SELECT s.business_name
                        FROM sellers s
                        JOIN products p ON s.user_id = p.seller_id
                        JOIN order_items oi ON p.id = oi.product_id
                        WHERE oi.order_id = %s
                        LIMIT 1
                    ''', (order_id,))
                else:
                    cursor.execute('''
                        SELECT s.business_name
                        FROM sellers s
                        JOIN products p ON s.user_id = p.seller_id
                        JOIN order_items oi ON p.id = oi.product_id
                        WHERE oi.order_id = ?
                        LIMIT 1
                    ''', (order_id,))
                
                seller_row = cursor.fetchone()
                if seller_row:
                    seller_name = seller_row[0] if isinstance(seller_row, tuple) else seller_row.get('business_name', 'Seller')
                    order['seller_name'] = seller_name
                else:
                    order['seller_name'] = 'Seller'
            except Exception as seller_err:
                app.logger.warning(f'Could not fetch seller name for order {order_id}: {seller_err}')
                order['seller_name'] = 'Seller'
            
            result.append(order)
        
        if cursor:
            cursor.close()
        return success_response(result, 'Available orders')
    except Exception as e:
        app.logger.error('api_rider_available_orders error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        if cursor:
            try:
                cursor.close()
            except:
                pass
        return error_response(f'Failed to load available orders: {str(e)}', 500)

@app.route('/api/riders/accept-order', methods=['POST'])
@token_required
def api_rider_accept_order():
    """Rider accepts an order for delivery"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        data = request.json
        order_id = data.get('order_id')
        
        if not order_id:
            return error_response('Order ID required', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider_id from riders table
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM riders WHERE user_id=%s', (user_id,))
        else:
            cursor.execute('SELECT id FROM riders WHERE user_id=?', (user_id,))
        rider_row = cursor.fetchone()
        
        if not rider_row:
            return error_response('Rider profile not found', 404)
        
        rider_id = rider_row[0] if isinstance(rider_row, tuple) else (rider_row.get('id') if isinstance(rider_row, dict) else None)
        
        if not rider_id:
            return error_response('Rider ID not found', 404)
        
        # Verify order is available (status='ready' and no rider assigned)
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT status, rider_id FROM orders WHERE id=%s', (order_id,))
        else:
            cursor.execute('SELECT status, rider_id FROM orders WHERE id=?', (order_id,))
        order_row = cursor.fetchone()
        
        if not order_row:
            return error_response('Order not found', 404)
        
        order_status = order_row[0] if isinstance(order_row, tuple) else order_row.get('status')
        existing_rider_id = order_row[1] if isinstance(order_row, tuple) else order_row.get('rider_id')
        
        if order_status not in ('ready', 'placed'):
            return error_response('Order is not available for pickup', 400)
        
        if existing_rider_id is not None:
            return error_response('Order already assigned to another rider', 400)
        
        # Assign rider to order and update status
        if DB_ENGINE == 'mysql':
            cursor.execute('UPDATE orders SET rider_id=%s, status=%s WHERE id=%s', 
                          (rider_id, 'dispatched', order_id))
        else:
            cursor.execute('UPDATE orders SET rider_id=?, status=? WHERE id=?', 
                          (rider_id, 'dispatched', order_id))
        db.commit()
        cursor.close()
        
        return success_response({'order_id': order_id, 'status': 'dispatched'}, 'Order accepted')
    except Exception as e:
        app.logger.error('accept_order error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/orders/<int:order_id>/assign-rider', methods=['PUT'])
@token_required
def api_assign_rider(order_id):
    """Assign a rider to an order"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        data = request.json
        rider_id = data.get('rider_id')
        
        if not rider_id:
            return error_response('Rider ID required', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('UPDATE orders SET rider_id=%s WHERE id=%s', (rider_id, order_id))
        else:
            cursor.execute('UPDATE orders SET rider_id=? WHERE id=?', (rider_id, order_id))
        db.commit()
        cursor.close()
        
        return success_response({'order_id': order_id, 'rider_id': rider_id}, 'Rider assigned')
    except Exception as e:
        app.logger.error('assign_rider error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/orders/<int:order_id>/delivery-update', methods=['PUT'])
@token_required
def api_delivery_update(order_id):
    """Rider updates delivery status"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        data = request.json
        new_status = data.get('status')  # in-transit, delivered, completed
        notes = data.get('notes', '')
        
        # Riders can update: in-transit (picked up and on the way), delivered, completed
        if new_status not in ('in-transit', 'delivered', 'completed'):
            return error_response('Invalid status. Riders can update to: "in-transit", "delivered", or "completed"', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider_id from riders table
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM riders WHERE user_id=%s', (user_id,))
        else:
            cursor.execute('SELECT id FROM riders WHERE user_id=?', (user_id,))
        rider_row = cursor.fetchone()
        
        if not rider_row:
            return error_response('Rider profile not found', 404)
        
        rider_id = rider_row[0] if isinstance(rider_row, tuple) else (rider_row.get('id') if isinstance(rider_row, dict) else None)
        
        # Verify rider is assigned to this order
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT rider_id, status FROM orders WHERE id=%s', (order_id,))
        else:
            cursor.execute('SELECT rider_id, status FROM orders WHERE id=?', (order_id,))
        order_row = cursor.fetchone()
        
        if not order_row:
            return error_response('Order not found', 404)
        
        order_rider_id = order_row[0] if isinstance(order_row, tuple) else order_row.get('rider_id')
        current_status = order_row[1] if isinstance(order_row, tuple) else order_row.get('status')
        
        if order_rider_id != rider_id:
            return error_response('Not authorized: You are not assigned to this order', 403)
        
        # Validate status transition
        if new_status == 'in-transit' and current_status not in ('dispatched', 'ready'):
            return error_response(f'Cannot transition from {current_status} to in-transit. Order must be dispatched or ready first.', 400)
        if new_status == 'delivered' and current_status not in ('in-transit', 'dispatched'):
            return error_response(f'Cannot transition from {current_status} to delivered. Order must be in-transit first.', 400)
        if new_status == 'completed' and current_status not in ('delivered', 'in-transit'):
            return error_response(f'Cannot transition from {current_status} to completed. Order must be delivered first.', 400)
        
        # Update order status
        if new_status == 'delivered':
            if DB_ENGINE == 'mysql':
                cursor.execute('UPDATE orders SET status=%s, delivered_at=NOW() WHERE id=%s',
                              (new_status, order_id))
            else:
                cursor.execute('UPDATE orders SET status=?, delivered_at=? WHERE id=?',
                              (new_status, datetime.now().isoformat(), order_id))
        elif new_status == 'completed':
            # When marking as completed, ensure delivered_at is set if not already
            if DB_ENGINE == 'mysql':
                cursor.execute('UPDATE orders SET status=%s, delivered_at=COALESCE(delivered_at, NOW()) WHERE id=%s',
                              (new_status, order_id))
            else:
                cursor.execute('UPDATE orders SET status=?, delivered_at=COALESCE(delivered_at, ?) WHERE id=?',
                              (new_status, datetime.now().isoformat(), order_id))
        else:
            if DB_ENGINE == 'mysql':
                cursor.execute('UPDATE orders SET status=%s WHERE id=%s', (new_status, order_id))
            else:
                cursor.execute('UPDATE orders SET status=? WHERE id=?', (new_status, order_id))
        
        db.commit()
        
        # If order is marked as delivered or completed, get customer info for notification
        if new_status in ('delivered', 'completed'):
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT customer_id, customer_name, customer_phone FROM orders WHERE id=%s', (order_id,))
                else:
                    cursor.execute('SELECT customer_id, customer_name, customer_phone FROM orders WHERE id=?', (order_id,))
                customer_row = cursor.fetchone()
                if customer_row:
                    customer = format_row(customer_row)
                    app.logger.info(f'Order #{order_id} marked as {new_status} - Customer: {customer.get("customer_name")} (ID: {customer.get("customer_id")})')
                    # TODO: Send notification to customer (email/SMS/push notification)
            except Exception as notify_err:
                app.logger.warning(f'Could not get customer info for notification: {notify_err}')
        
        # If order is marked as delivered or completed, get customer info for notification
        if new_status in ('delivered', 'completed'):
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT customer_id, customer_name, customer_phone FROM orders WHERE id=%s', (order_id,))
                else:
                    cursor.execute('SELECT customer_id, customer_name, customer_phone FROM orders WHERE id=?', (order_id,))
                customer_row = cursor.fetchone()
                if customer_row:
                    customer = format_row(customer_row)
                    app.logger.info(f'Order #{order_id} marked as {new_status} - Customer: {customer.get("customer_name")} (ID: {customer.get("customer_id")})')
                    # TODO: Send notification to customer (email/SMS/push notification)
            except Exception as notify_err:
                app.logger.warning(f'Could not get customer info for notification: {notify_err}')
        
        cursor.close()
        
        return success_response({'order_id': order_id, 'status': new_status}, 'Delivery updated')
    except Exception as e:
        app.logger.error('delivery_update error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/orders/<int:order_id>/rate-rider', methods=['POST'])
@token_required
def api_rate_rider(order_id):
    """Customer rates the rider after delivery"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        # Only customers can rate riders
        if role != 'customer':
            return error_response('Only customers can rate riders', 403)
        
        data = request.json or {}
        rating = data.get('rating')
        comment = data.get('comment', '').strip()
        
        # Validate rating
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return error_response('Rating must be between 1 and 5', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify order exists and belongs to customer
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT customer_id, rider_id, status FROM orders WHERE id=%s', (order_id,))
        else:
            cursor.execute('SELECT customer_id, rider_id, status FROM orders WHERE id=?', (order_id,))
        order_row = cursor.fetchone()
        
        if not order_row:
            return error_response('Order not found', 404)
        
        order = format_row(order_row)
        
        if order.get('customer_id') != user_id:
            return error_response('You can only rate riders for your own orders', 403)
        
        if order.get('status') not in ('delivered', 'completed'):
            return error_response('You can only rate riders for delivered or completed orders', 400)
        
        rider_id = order.get('rider_id')
        if not rider_id:
            return error_response('No rider assigned to this order', 400)
        
        # Check if review already exists
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM rider_reviews WHERE order_id=%s', (order_id,))
        else:
            cursor.execute('SELECT id FROM rider_reviews WHERE order_id=?', (order_id,))
        existing_review = cursor.fetchone()
        
        app.logger.info(f'💬 Customer {user_id} submitting RIDER review: order_id={order_id}, rider_id={rider_id}, rating={rating}')
        app.logger.debug(f'   → Storing in "rider_reviews" table (NOT reviews table)')
        
        if existing_review:
            # Update existing review
            if DB_ENGINE == 'mysql':
                cursor.execute('UPDATE rider_reviews SET rating=%s, comment=%s WHERE order_id=%s', 
                             (rating, comment, order_id))
            else:
                cursor.execute('UPDATE rider_reviews SET rating=?, comment=? WHERE order_id=?', 
                             (rating, comment, order_id))
            message = 'Review updated successfully'
            app.logger.info(f'✅ Updated rider review for order {order_id}, rider {rider_id}')
        else:
            # Create new review
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    INSERT INTO rider_reviews (order_id, rider_id, customer_id, rating, comment)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (order_id, rider_id, user_id, rating, comment))
            else:
                cursor.execute('''
                    INSERT INTO rider_reviews (order_id, rider_id, customer_id, rating, comment)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, rider_id, user_id, rating, comment))
            message = 'Review submitted successfully'
            app.logger.info(f'✅ Created new rider review for order {order_id}, rider {rider_id}')
        
        db.commit()
        cursor.close()
        
        return success_response({
            'order_id': order_id,
            'rider_id': rider_id,
            'rating': rating,
            'comment': comment
        }, message)
        
    except Exception as e:
        app.logger.error('rate_rider error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/rider/reviews', methods=['GET'])
@token_required
def api_rider_get_reviews():
    """Get all RIDER reviews for the authenticated rider (NOT product reviews)"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        rider_user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'rider':
            return error_response('Only riders can access this endpoint', 403)
        
        db = get_db()
        # Use DictCursor for MySQL, regular cursor for SQLite
        if DB_ENGINE == 'mysql':
            cursor = db.cursor(pymysql.cursors.DictCursor)
        else:
            cursor = db.cursor()
        
        # Get rider_id from riders table
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM riders WHERE user_id = %s', (rider_user_id,))
        else:
            cursor.execute('SELECT id FROM riders WHERE user_id = ?', (rider_user_id,))
        
        rider_row = cursor.fetchone()
        if not rider_row:
            cursor.close()
            return success_response({'reviews': [], 'stats': {}}, 'No rider profile found')
        
        rider_id = rider_row['id'] if isinstance(rider_row, dict) else rider_row[0]
        
        app.logger.debug(f'🔍 Fetching rider reviews for rider_id: {rider_id} (user_id: {rider_user_id})')
        
        # IMPORTANT: Query ONLY rider reviews from 'rider_reviews' table
        # NOT reviews table (product reviews). This is completely separate.
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    rr.id,
                    rr.order_id,
                    rr.rider_id,
                    rr.customer_id,
                    rr.rating,
                    rr.comment,
                    rr.created_at,
                    u.first_name,
                    u.last_name,
                    u.email as customer_email,
                    o.total as order_total,
                    o.status as order_status
                FROM rider_reviews rr
                LEFT JOIN users u ON rr.customer_id = u.id
                LEFT JOIN orders o ON rr.order_id = o.id
                WHERE rr.rider_id = %s
                ORDER BY rr.created_at DESC
            ''', (rider_id,))
        else:
            cursor.execute('''
                SELECT 
                    rr.id,
                    rr.order_id,
                    rr.rider_id,
                    rr.customer_id,
                    rr.rating,
                    rr.comment,
                    rr.created_at,
                    u.first_name,
                    u.last_name,
                    u.email as customer_email,
                    o.total as order_total,
                    o.status as order_status
                FROM rider_reviews rr
                LEFT JOIN users u ON rr.customer_id = u.id
                LEFT JOIN orders o ON rr.order_id = o.id
                WHERE rr.rider_id = ?
                ORDER BY rr.created_at DESC
            ''', (rider_id,))
        
        reviews = cursor.fetchall()
        result = []
        
        app.logger.debug(f'📥 Found {len(reviews)} rider reviews in database for rider {rider_id}')
        
        for review in reviews:
            review_dict = format_row(review)
            
            # Double-check: ensure this is a rider review, not a product review
            if not review_dict.get('rider_id'):
                app.logger.warning(f'Skipping review {review_dict.get("id")} - missing rider_id')
                continue
            
            # Format customer name
            first_name = review_dict.get('first_name', '')
            last_name = review_dict.get('last_name', '')
            customer_name = f"{first_name} {last_name}".strip() or review_dict.get('customer_email', 'Customer')
            review_dict['customer_name'] = customer_name
            
            result.append(review_dict)
        
        # Calculate stats
        total_reviews = len(result)
        avg_rating = 0.0
        if total_reviews > 0:
            avg_rating = sum(r.get('rating', 0) for r in result) / total_reviews
        
        rating_breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in result:
            rating = review.get('rating', 0)
            if 1 <= rating <= 5:
                rating_breakdown[rating] += 1
        
        stats = {
            'total_reviews': total_reviews,
            'avg_rating': round(avg_rating, 1),
            'rating_breakdown': rating_breakdown
        }
        
        app.logger.debug(f'✅ Returning {len(result)} rider reviews for rider {rider_id}')
        cursor.close()
        return success_response({
            'reviews': result,
            'stats': stats
        }, 'Rider reviews fetched successfully')
        
    except Exception as e:
        app.logger.error(f'Error fetching rider reviews: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/customer/products/<int:product_id>/review', methods=['POST'])
@token_required
def api_submit_product_review(product_id):
    """Customer submits a product review"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'customer':
            return error_response('Only customers can review products', 403)
        
        data = request.json or {}
        order_id = data.get('order_id')
        rating = data.get('rating')
        comment = data.get('comment', '').strip()
        
        if not order_id:
            return error_response('Order ID is required', 400)
        
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return error_response('Rating must be between 1 and 5', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify order exists, belongs to customer, and is delivered
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT o.customer_id, o.status, o.delivered_at, oi.product_id, p.seller_id
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE o.id = %s AND oi.product_id = %s
            ''', (order_id, product_id))
        else:
            cursor.execute('''
                SELECT o.customer_id, o.status, o.delivered_at, oi.product_id, p.seller_id
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE o.id = ? AND oi.product_id = ?
            ''', (order_id, product_id))
        
        order_row = cursor.fetchone()
        if not order_row:
            return error_response('Order or product not found', 404)
        
        order_data = format_row(order_row)
        if order_data.get('customer_id') != user_id:
            return error_response('You can only review products from your own orders', 403)
        
        if order_data.get('status') not in ('delivered', 'completed'):
            return error_response('You can only review products from delivered or completed orders', 400)
        
        seller_id = order_data.get('seller_id')
        if not seller_id:
            app.logger.error(f'❌ No seller_id found for product {product_id} in order {order_id}')
            return error_response('Seller information not found', 400)
        
        # Ensure seller_id is an integer (in case it's a string)
        try:
            seller_id = int(seller_id)
        except (ValueError, TypeError):
            app.logger.error(f'❌ Invalid seller_id type: {type(seller_id)}, value: {seller_id}')
            return error_response('Invalid seller information', 400)
        
        app.logger.info(f'💬 Customer {user_id} submitting PRODUCT review: product_id={product_id}, seller_id={seller_id} (type: {type(seller_id).__name__}), rating={rating}, order_id={order_id}')
        
        # Check if review already exists
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT id FROM reviews
                WHERE customer_id = %s AND order_id = %s AND product_id = %s
            ''', (user_id, order_id, product_id))
        else:
            cursor.execute('''
                SELECT id FROM reviews
                WHERE customer_id = ? AND order_id = ? AND product_id = ?
            ''', (user_id, order_id, product_id))
        
        existing_review = cursor.fetchone()
        
        if existing_review:
            # Update existing review
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    UPDATE reviews
                    SET rating = %s, comment = %s, seller_id = %s, updated_at = NOW()
                    WHERE customer_id = %s AND order_id = %s AND product_id = %s
                ''', (rating, comment or None, seller_id, user_id, order_id, product_id))
            else:
                cursor.execute('''
                    UPDATE reviews
                    SET rating = ?, comment = ?, seller_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = ? AND order_id = ? AND product_id = ?
                ''', (rating, comment or None, seller_id, user_id, order_id, product_id))
            message = 'Review updated successfully'
            app.logger.info(f'✅ Updated product review for product {product_id}, seller {seller_id}')
        else:
            # Create new review
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    INSERT INTO reviews (customer_id, order_id, product_id, seller_id, rating, comment)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (user_id, order_id, product_id, seller_id, rating, comment or None))
                new_review_id = cursor.lastrowid
            else:
                cursor.execute('''
                    INSERT INTO reviews (customer_id, order_id, product_id, seller_id, rating, comment)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, order_id, product_id, seller_id, rating, comment or None))
                new_review_id = cursor.lastrowid
            message = 'Review submitted successfully'
            app.logger.info(f'✅ Created new product review ID {new_review_id} for product {product_id}, seller {seller_id}, rating={rating}')
        
        db.commit()
        cursor.close()
        
        return success_response({
            'order_id': order_id,
            'product_id': product_id,
            'seller_id': seller_id,
            'rating': rating,
            'comment': comment
        }, message)
        
    except Exception as e:
        app.logger.error('submit_product_review error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/reviews', methods=['GET'])
@token_required
def api_seller_get_reviews():
    """Get all PRODUCT reviews for seller's products (NOT rider reviews) - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_user_id = payload.get('user_id')
        role = payload.get('role')
        store_id = request.args.get('store_id', type=int)
        
        if role != 'seller':
            return error_response('Only sellers can access this endpoint', 403)
        
        db = get_db()
        # Use DictCursor for MySQL, regular cursor for SQLite
        if DB_ENGINE == 'mysql':
            cursor = db.cursor(pymysql.cursors.DictCursor)
        else:
            cursor = db.cursor()
        
        app.logger.debug(f'🔍 Fetching PRODUCT reviews for seller user_id: {seller_user_id}, store_id: {store_id}')
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'seller_id = %s AND store_id = %s' if DB_ENGINE == 'mysql' else 'seller_id = ? AND store_id = ?'
            product_params = (seller_user_id, store_id)
            review_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            review_params = (seller_user_id, store_id)
        elif store_id_column_exists:
            product_filter = 'seller_id = %s AND (store_id IS NULL OR store_id = 0)' if DB_ENGINE == 'mysql' else 'seller_id = ? AND (store_id IS NULL OR store_id = 0)'
            product_params = (seller_user_id,)
            review_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            review_params = (seller_user_id,)
        else:
            product_filter = 'seller_id = %s' if DB_ENGINE == 'mysql' else 'seller_id = ?'
            product_params = (seller_user_id,)
            review_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            review_params = (seller_user_id,)
        
        # First, verify seller has products
        if DB_ENGINE == 'mysql':
            cursor.execute(f'SELECT COUNT(*) as product_count FROM products WHERE {product_filter}', product_params)
        else:
            cursor.execute(f'SELECT COUNT(*) as product_count FROM products WHERE {product_filter}', product_params)
        product_count_row = cursor.fetchone()
        product_count_dict = format_row(product_count_row)
        product_count = product_count_dict.get('product_count', 0) if isinstance(product_count_dict, dict) else (product_count_row[0] if product_count_row else 0)
        app.logger.info(f'📦 Seller {seller_user_id} has {product_count} products')
        
        # First, let's check what reviews exist for this seller's products (for debugging)
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT r.id, r.product_id, r.rating, r.seller_id, p.seller_id as product_seller_id, p.title
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = %s
                LIMIT 10
            ''', (seller_user_id,))
        else:
            cursor.execute('''
                SELECT r.id, r.product_id, r.rating, r.seller_id, p.seller_id as product_seller_id, p.title
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE p.seller_id = ?
                LIMIT 10
            ''', (seller_user_id,))
        
        debug_reviews = cursor.fetchall()
        app.logger.info(f'📊 Found {len(debug_reviews)} reviews for seller {seller_user_id} products:')
        for dbg_rev in debug_reviews:
            dbg_dict = format_row(dbg_rev)
            app.logger.info(f'   Review ID {dbg_dict.get("id")}: product_id={dbg_dict.get("product_id")}, product="{dbg_dict.get("title")}", rating={dbg_dict.get("rating")}, r.seller_id={dbg_dict.get("seller_id")}, p.seller_id={dbg_dict.get("product_seller_id")}')
        
        # CRITICAL: Query ONLY product reviews from 'reviews' table
        # NEVER query 'rider_reviews' table - that is for rider reviews only
        # Ensure product_id is NOT NULL to exclude any edge cases
        # NOTE: Reviews are included regardless of order status (including refunded orders)
        # Refunds do NOT remove or exclude reviews from metrics
        # IMPORTANT: Match by product's seller_id (p.seller_id) which is the seller's user_id
        # Don't require r.seller_id to match - just match by product ownership
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT 
                    r.id,
                    r.order_id,
                    r.product_id,
                    r.customer_id,
                    r.seller_id,
                    r.rating,
                    r.comment,
                    r.created_at,
                    r.updated_at,
                    p.title as product_title,
                    p.img_url as product_image,
                    p.seller_id as product_seller_id,
                    u.first_name,
                    u.last_name,
                    u.email as customer_email,
                    o.status as order_status
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                LEFT JOIN users u ON r.customer_id = u.id
                LEFT JOIN orders o ON r.order_id = o.id
                WHERE {review_filter}
                  AND r.product_id IS NOT NULL
                ORDER BY r.created_at DESC
            ''', review_params)
        else:
            cursor.execute(f'''
                SELECT 
                    r.id,
                    r.order_id,
                    r.product_id,
                    r.customer_id,
                    r.seller_id,
                    r.rating,
                    r.comment,
                    r.created_at,
                    r.updated_at,
                    p.title as product_title,
                    p.img_url as product_image,
                    p.seller_id as product_seller_id,
                    u.first_name,
                    u.last_name,
                    u.email as customer_email,
                    o.status as order_status
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                LEFT JOIN users u ON r.customer_id = u.id
                LEFT JOIN orders o ON r.order_id = o.id
                WHERE {review_filter}
                  AND r.product_id IS NOT NULL
                ORDER BY r.created_at DESC
            ''', review_params)
        
        reviews = cursor.fetchall()
        result = []
        
        app.logger.debug(f'📥 Found {len(reviews)} product reviews in database for seller {seller_user_id}')
        
        for review in reviews:
            review_dict = format_row(review)
            
            # Double-check: ensure this is a product review, not a rider review
            if not review_dict.get('product_id'):
                app.logger.warning(f'Skipping review {review_dict.get("id")} - missing product_id')
                continue
            
            # Log review details for debugging
            review_id = review_dict.get('id')
            product_id = review_dict.get('product_id')
            product_seller_id = review_dict.get('product_seller_id')
            review_seller_id = review_dict.get('seller_id')
            rating = review_dict.get('rating')
            
            app.logger.debug(f'  Review {review_id}: product_id={product_id}, product_seller_id={product_seller_id}, review_seller_id={review_seller_id}, rating={rating}')
            
            # If review_seller_id is NULL or doesn't match, update it to match product's seller
            if review_seller_id != seller_user_id:
                app.logger.warning(f'Review {review_id} has mismatched seller_id: review.seller_id={review_seller_id}, expected={seller_user_id}. Updating...')
                try:
                    if DB_ENGINE == 'mysql':
                        cursor.execute('UPDATE reviews SET seller_id = %s WHERE id = %s', (seller_user_id, review_id))
                    else:
                        cursor.execute('UPDATE reviews SET seller_id = ? WHERE id = ?', (seller_user_id, review_id))
                    db.commit()
                    review_dict['seller_id'] = seller_user_id
                    app.logger.info(f'✅ Updated review {review_id} seller_id to {seller_user_id}')
                except Exception as update_err:
                    app.logger.error(f'Failed to update review {review_id} seller_id: {update_err}')
            
            # Format customer name
            first_name = review_dict.get('first_name', '')
            last_name = review_dict.get('last_name', '')
            customer_name = f"{first_name} {last_name}".strip() or review_dict.get('customer_email', 'Customer')
            review_dict['customer_name'] = customer_name
            
            # Ensure we have product info
            if not review_dict.get('product_title'):
                review_dict['product_title'] = 'Unknown Product'
            
            # Include order status (may be 'refunded', 'delivered', etc.) for display purposes
            # But this does NOT affect whether the review is included - all reviews count
            order_status = review_dict.get('order_status', 'unknown')
            review_dict['order_status'] = order_status
            review_dict['is_refunded'] = (order_status == 'refunded')
            
            result.append(review_dict)
        
        app.logger.debug(f'✅ Returning {len(result)} product reviews for seller {seller_user_id}')
        cursor.close()
        return success_response(result, 'Product reviews fetched successfully')
        
    except Exception as e:
        app.logger.error(f'Error fetching seller product reviews: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/reviews/analytics', methods=['GET'])
@token_required
def api_seller_reviews_analytics():
    """Get PRODUCT review analytics for seller (satisfaction score, rating breakdown, keywords) - NOT rider reviews - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_user_id = payload.get('user_id')
        role = payload.get('role')
        store_id = request.args.get('store_id', type=int)
        
        if role != 'seller':
            return error_response('Only sellers can access this endpoint', 403)
        
        db = get_db()
        # Use DictCursor for MySQL, regular cursor for SQLite
        if DB_ENGINE == 'mysql':
            cursor = db.cursor(pymysql.cursors.DictCursor)
        else:
            cursor = db.cursor()
        
        app.logger.debug(f'📊 Calculating PRODUCT review analytics for seller user_id: {seller_user_id}, store_id: {store_id}')
        
        # Check if store_id column exists in products table
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_user_id, store_id)
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_user_id,)
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_user_id,)
        
        # CRITICAL: Query ONLY product reviews from 'reviews' table
        # NEVER query 'rider_reviews' table - that is for rider reviews only
        # Ensure product_id is NOT NULL
        # NOTE: Reviews are included in analytics regardless of order status (including refunded orders)
        # Refunds do NOT remove or exclude reviews from metrics - all reviews count toward satisfaction score
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT 
                    AVG(r.rating) as avg_rating,
                    COUNT(*) as total_reviews,
                    SUM(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END) as rating_5,
                    SUM(CASE WHEN r.rating = 4 THEN 1 ELSE 0 END) as rating_4,
                    SUM(CASE WHEN r.rating = 3 THEN 1 ELSE 0 END) as rating_3,
                    SUM(CASE WHEN r.rating = 2 THEN 1 ELSE 0 END) as rating_2,
                    SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END) as rating_1
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE {product_filter}
                  AND r.product_id IS NOT NULL
                  -- No filter on order status - includes refunded orders
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT 
                    AVG(r.rating) as avg_rating,
                    COUNT(*) as total_reviews,
                    SUM(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END) as rating_5,
                    SUM(CASE WHEN r.rating = 4 THEN 1 ELSE 0 END) as rating_4,
                    SUM(CASE WHEN r.rating = 3 THEN 1 ELSE 0 END) as rating_3,
                    SUM(CASE WHEN r.rating = 2 THEN 1 ELSE 0 END) as rating_2,
                    SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END) as rating_1
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE {product_filter}
                  AND r.product_id IS NOT NULL
                  -- No filter on order status - includes refunded orders
            ''', product_params)
        
        stats = cursor.fetchone()
        stats_dict = format_row(stats)
        
        avg_rating = float(stats_dict.get('avg_rating', 0) or 0)
        total_reviews = int(stats_dict.get('total_reviews', 0) or 0)
        
        # Calculate rating breakdown percentages - REAL-TIME from actual product reviews
        rating_5 = int(stats_dict.get('rating_5', 0) or 0)
        rating_4 = int(stats_dict.get('rating_4', 0) or 0)
        rating_3 = int(stats_dict.get('rating_3', 0) or 0)
        rating_2 = int(stats_dict.get('rating_2', 0) or 0)
        rating_1 = int(stats_dict.get('rating_1', 0) or 0)
        
        # Verify counts add up to total (for debugging)
        calculated_total = rating_5 + rating_4 + rating_3 + rating_2 + rating_1
        if calculated_total != total_reviews and total_reviews > 0:
            app.logger.warning(f'Rating breakdown mismatch: total={total_reviews}, calculated={calculated_total}')
        
        # Calculate percentages with proper rounding
        rating_breakdown = {
            '5': {
                'count': rating_5, 
                'percentage': round((rating_5 / total_reviews * 100) if total_reviews > 0 else 0, 1)
            },
            '4': {
                'count': rating_4, 
                'percentage': round((rating_4 / total_reviews * 100) if total_reviews > 0 else 0, 1)
            },
            '3': {
                'count': rating_3, 
                'percentage': round((rating_3 / total_reviews * 100) if total_reviews > 0 else 0, 1)
            },
            '2': {
                'count': rating_2, 
                'percentage': round((rating_2 / total_reviews * 100) if total_reviews > 0 else 0, 1)
            },
            '1': {
                'count': rating_1, 
                'percentage': round((rating_1 / total_reviews * 100) if total_reviews > 0 else 0, 1)
            }
        }
        
        app.logger.debug(f'📊 Rating breakdown for seller {seller_user_id}: 5★={rating_5}({rating_breakdown["5"]["percentage"]}%), 4★={rating_4}({rating_breakdown["4"]["percentage"]}%), 3★={rating_3}({rating_breakdown["3"]["percentage"]}%), 2★={rating_2}({rating_breakdown["2"]["percentage"]}%), 1★={rating_1}({rating_breakdown["1"]["percentage"]}%)')
        
        # Calculate satisfaction score (percentage of 4 and 5 star reviews)
        satisfaction_score = round(((rating_5 + rating_4) / total_reviews * 100) if total_reviews > 0 else 0, 1)
        
        # Extract keywords from review comments (ONLY product reviews)
        # Includes reviews from refunded orders - refunds don't exclude reviews from keyword analysis
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT r.comment
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE {product_filter}
                  AND r.product_id IS NOT NULL
                  AND r.comment IS NOT NULL 
                  AND r.comment != ''
                  -- No filter on order status - includes refunded orders
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT r.comment
                FROM reviews r
                INNER JOIN products p ON r.product_id = p.id
                WHERE {product_filter}
                  AND r.product_id IS NOT NULL
                  AND r.comment IS NOT NULL 
                  AND r.comment != ''
                  -- No filter on order status - includes refunded orders
            ''', product_params)
        
        comments = cursor.fetchall()
        
        # Extract most mentioned keywords
        import re
        from collections import Counter
        
        # Common stop words to exclude
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'very', 'really', 'quite', 'too', 'so', 'just', 'only', 'also', 'even', 'still', 'yet', 'already', 'product', 'item', 'order', 'delivery', 'shipping'}
        
        all_words = []
        for comment_row in comments:
            comment = comment_row[0] if isinstance(comment_row, tuple) else comment_row.get('comment', '')
            if comment:
                # Extract words (alphanumeric, at least 3 characters)
                words = re.findall(r'\b[a-zA-Z]{3,}\b', comment.lower())
                all_words.extend([w for w in words if w not in stop_words])
        
        # Get top 10 keywords
        keyword_counts = Counter(all_words)
        top_keywords = [{'word': word, 'count': count} for word, count in keyword_counts.most_common(10)]
        
        # Identify areas to improve (from low ratings)
        areas_to_improve = []
        if rating_1 + rating_2 + rating_3 > 0:
            # Get comments from low ratings (ONLY product reviews)
            # Includes reviews from refunded orders - refunds don't exclude reviews from improvement analysis
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT r.comment
                    FROM reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE p.seller_id = %s 
                      AND r.product_id IS NOT NULL
                      AND r.seller_id = %s
                      AND r.rating <= 3 
                      AND r.comment IS NOT NULL 
                      AND r.comment != ''
                      -- No filter on order status - includes refunded orders
                    ORDER BY r.rating ASC, r.created_at DESC
                    LIMIT 20
                ''', (seller_user_id, seller_user_id))
            else:
                cursor.execute('''
                    SELECT r.comment
                    FROM reviews r
                    INNER JOIN products p ON r.product_id = p.id
                    WHERE p.seller_id = ? 
                      AND r.product_id IS NOT NULL
                      AND r.seller_id = ?
                      AND r.rating <= 3 
                      AND r.comment IS NOT NULL 
                      AND r.comment != ''
                      -- No filter on order status - includes refunded orders
                    ORDER BY r.rating ASC, r.created_at DESC
                    LIMIT 20
                ''', (seller_user_id, seller_user_id))
            
            low_rating_comments = cursor.fetchall()
            # Extract common themes from low ratings
            low_words = []
            for comment_row in low_rating_comments:
                comment = comment_row[0] if isinstance(comment_row, tuple) else comment_row.get('comment', '')
                if comment:
                    words = re.findall(r'\b[a-zA-Z]{3,}\b', comment.lower())
                    low_words.extend([w for w in words if w not in stop_words])
            
            low_keyword_counts = Counter(low_words)
            areas_to_improve = [{'word': word, 'count': count} for word, count in low_keyword_counts.most_common(5)]
        
        cursor.close()
        
        return success_response({
            'overall_rating': round(avg_rating, 1),
            'total_reviews': total_reviews,
            'satisfaction_score': satisfaction_score,
            'rating_breakdown': rating_breakdown,
            'top_keywords': top_keywords,
            'areas_to_improve': areas_to_improve
        }, 'Review analytics fetched successfully')
        
    except Exception as e:
        app.logger.error(f'Error fetching review analytics: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/customer/orders/<int:order_id>/items/<int:order_item_id>/return-refund', methods=['POST'])
@token_required
def api_request_return_refund(order_id, order_item_id):
    """Customer requests a return or refund for a product"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'customer':
            return error_response('Only customers can request returns/refunds', 403)
        
        data = request.json or {}
        request_type = data.get('request_type', 'return')  # 'return', 'refund', or 'both'
        reason = data.get('reason', '').strip()
        evidence_images = data.get('evidence_images', [])  # Array of image URLs/paths
        
        if request_type not in ('return', 'refund', 'both'):
            return error_response('Invalid request type. Must be "return", "refund", or "both"', 400)
        
        if not reason:
            return error_response('Reason is required', 400)
        
        # Convert evidence_images array to JSON string
        import json
        evidence_json = json.dumps(evidence_images) if evidence_images else None
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify order exists, belongs to customer, and is delivered
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT o.customer_id, o.status, o.delivered_at, oi.product_id, p.seller_id
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE o.id = %s AND oi.id = %s
            ''', (order_id, order_item_id))
        else:
            cursor.execute('''
                SELECT o.customer_id, o.status, o.delivered_at, oi.product_id, p.seller_id
                FROM orders o
                INNER JOIN order_items oi ON o.id = oi.order_id
                INNER JOIN products p ON oi.product_id = p.id
                WHERE o.id = ? AND oi.id = ?
            ''', (order_id, order_item_id))
        
        order_row = cursor.fetchone()
        if not order_row:
            return error_response('Order or item not found', 404)
        
        order_data = format_row(order_row)
        if order_data.get('customer_id') != user_id:
            return error_response('You can only request returns/refunds for your own orders', 403)
        
        if order_data.get('status') not in ('delivered', 'completed'):
            return error_response('You can only request returns/refunds for delivered or completed orders', 400)
        
        # Check if request already exists
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT id, status FROM return_refund_requests
                WHERE order_id = %s AND order_item_id = %s AND customer_id = %s
                AND status NOT IN ('completed', 'cancelled')
            ''', (order_id, order_item_id, user_id))
        else:
            cursor.execute('''
                SELECT id, status FROM return_refund_requests
                WHERE order_id = ? AND order_item_id = ? AND customer_id = ?
                AND status NOT IN ('completed', 'cancelled')
            ''', (order_id, order_item_id, user_id))
        
        existing_request = cursor.fetchone()
        if existing_request:
            return error_response('A return/refund request already exists for this item', 400)
        
        seller_id = order_data.get('seller_id')
        if not seller_id:
            return error_response('Seller information not found', 400)
        
        # Create return/refund request
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                INSERT INTO return_refund_requests (order_id, order_item_id, customer_id, seller_id, request_type, reason, evidence_images, status, seller_response)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', 'pending')
            ''', (order_id, order_item_id, user_id, seller_id, request_type, reason, evidence_json))
        else:
            cursor.execute('''
                INSERT INTO return_refund_requests (order_id, order_item_id, customer_id, seller_id, request_type, reason, evidence_images, status, seller_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 'pending')
            ''', (order_id, order_item_id, user_id, seller_id, request_type, reason, evidence_json))
        
        request_id = cursor.lastrowid
        
        # Update order status to 'refund_requested' if not already
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE orders SET status = 'refund_requested', updated_at = NOW()
                WHERE id = %s AND status NOT IN ('refund_requested', 'refunded', 'cancelled')
            ''', (order_id,))
        else:
            cursor.execute('''
                UPDATE orders SET status = 'refund_requested', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status NOT IN ('refund_requested', 'refunded', 'cancelled')
            ''', (order_id,))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id,
            'order_id': order_id,
            'order_item_id': order_item_id,
            'request_type': request_type,
            'status': 'pending'
        }, 'Return/refund request submitted successfully')
        
    except Exception as e:
        app.logger.error('request_return_refund error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/return-refund-requests', methods=['GET'])
@token_required
def api_seller_get_return_refund_requests():
    """Seller views all return/refund requests for their products - supports store_id filtering"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        role = payload.get('role')
        store_id = request.args.get('store_id', type=int)
        
        if role != 'seller':
            return error_response('Only sellers can view return/refund requests', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'rrr.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'rrr.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id)
        elif store_id_column_exists:
            product_filter = 'rrr.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'rrr.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id,)
        else:
            product_filter = 'rrr.seller_id = %s' if DB_ENGINE == 'mysql' else 'rrr.seller_id = ?'
            product_params = (seller_id,)
        
        # Get all return/refund requests for this seller's products
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT rrr.id, rrr.order_id, rrr.order_item_id, rrr.customer_id, rrr.seller_id,
                       rrr.request_type, rrr.reason, rrr.status, rrr.seller_response, rrr.rejection_reason,
                       rrr.evidence_images, rrr.pickup_rider_id, rrr.pickup_scheduled_at,
                       rrr.pickup_completed_at, rrr.item_received_at, rrr.refund_processed_at,
                       rrr.created_at, rrr.updated_at,
                       o.customer_name, o.customer_phone, o.customer_address,
                       p.title as product_name, p.img_url as product_image,
                       u.first_name as customer_first_name, u.last_name as customer_last_name,
                       u.email as customer_email
                FROM return_refund_requests rrr
                INNER JOIN orders o ON rrr.order_id = o.id
                INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN users u ON rrr.customer_id = u.id
                WHERE {product_filter}
                ORDER BY rrr.created_at DESC
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT rrr.id, rrr.order_id, rrr.order_item_id, rrr.customer_id, rrr.seller_id,
                       rrr.request_type, rrr.reason, rrr.status, rrr.seller_response, rrr.rejection_reason,
                       rrr.evidence_images, rrr.pickup_rider_id, rrr.pickup_scheduled_at,
                       rrr.pickup_completed_at, rrr.item_received_at, rrr.refund_processed_at,
                       rrr.created_at, rrr.updated_at,
                       o.customer_name, o.customer_phone, o.customer_address,
                       p.title as product_name, p.img_url as product_image,
                       u.first_name as customer_first_name, u.last_name as customer_last_name,
                       u.email as customer_email
                FROM return_refund_requests rrr
                INNER JOIN orders o ON rrr.order_id = o.id
                INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN users u ON rrr.customer_id = u.id
                WHERE {product_filter}
                ORDER BY rrr.created_at DESC
            ''', product_params)
        
        rows = cursor.fetchall()
        requests = []
        
        for row in rows:
            req = format_row(row)
            # Parse evidence_images JSON if present
            if req.get('evidence_images'):
                try:
                    import json
                    req['evidence_images'] = json.loads(req['evidence_images'])
                except:
                    req['evidence_images'] = []
            else:
                req['evidence_images'] = []
            
            requests.append(req)
        
        cursor.close()
        return success_response({'requests': requests})
        
    except Exception as e:
        app.logger.error('api_seller_get_return_refund_requests error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/return-refund-requests/<int:request_id>/respond', methods=['POST'])
@token_required
def api_seller_respond_to_request(request_id):
    """Seller approves, rejects, or requests more info for a return/refund request"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'seller':
            return error_response('Only sellers can respond to requests', 403)
        
        data = request.json or {}
        response_type = data.get('response')  # 'approved', 'rejected', 'request_info'
        rejection_reason = data.get('rejection_reason', '').strip()
        admin_notes = data.get('admin_notes', '').strip()
        
        if response_type not in ('approved', 'rejected', 'request_info'):
            return error_response('Invalid response type. Must be "approved", "rejected", or "request_info"', 400)
        
        if response_type == 'rejected' and not rejection_reason:
            return error_response('Rejection reason is required when rejecting a request', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify request exists and belongs to this seller
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT seller_id, request_type, status, order_id FROM return_refund_requests WHERE id = %s', (request_id,))
        else:
            cursor.execute('SELECT seller_id, request_type, status, order_id FROM return_refund_requests WHERE id = ?', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            return error_response('Request not found', 404)
        
        req_data = format_row(req_row)
        if req_data.get('seller_id') != seller_id:
            return error_response('You can only respond to requests for your own products', 403)
        
        # Update request
        new_status = 'pending'
        request_type = req_data.get('request_type')
        order_id = req_data.get('order_id')
        
        if response_type == 'approved':
            # For refund-only requests, set status to 'processing' (skip rider pickup)
            # For return/both requests, set status to 'approved' (waiting for rider pickup)
            if request_type == 'refund':
                new_status = 'processing'
            else:
                new_status = 'approved'
        elif response_type == 'rejected':
            new_status = 'rejected'
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE return_refund_requests
                SET seller_response = %s, status = %s, rejection_reason = %s, admin_notes = %s, updated_at = NOW()
                WHERE id = %s
            ''', (response_type, new_status, rejection_reason or None, admin_notes or None, request_id))
        else:
            cursor.execute('''
                UPDATE return_refund_requests
                SET seller_response = ?, status = ?, rejection_reason = ?, admin_notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (response_type, new_status, rejection_reason or None, admin_notes or None, request_id))
        
        # If rejected, update order status back to delivered/completed
        if response_type == 'rejected' and order_id:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    UPDATE orders SET status = 'delivered', updated_at = NOW()
                    WHERE id = %s
                ''', (order_id,))
            else:
                cursor.execute('''
                    UPDATE orders SET status = 'delivered', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (order_id,))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id,
            'response': response_type,
            'status': new_status
        }, f'Request {response_type} successfully')
        
    except Exception as e:
        app.logger.error('api_seller_respond_to_request error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/sellers/return-refund-requests/<int:request_id>/confirm-received', methods=['POST'])
@token_required
def api_seller_confirm_item_received(request_id):
    """Seller confirms they received the returned item"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        seller_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'seller':
            return error_response('Only sellers can confirm item receipt', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify request exists, belongs to seller, and is a return request
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT seller_id, request_type, status, seller_response, pickup_completed_at
                FROM return_refund_requests WHERE id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                SELECT seller_id, request_type, status, seller_response, pickup_completed_at
                FROM return_refund_requests WHERE id = ?
            ''', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            return error_response('Request not found', 404)
        
        req_data = format_row(req_row)
        if req_data.get('seller_id') != seller_id:
            return error_response('You can only confirm receipt for your own products', 403)
        
        if req_data.get('request_type') not in ('return', 'both'):
            return error_response('This request is not a return request', 400)
        
        if req_data.get('seller_response') != 'approved':
            return error_response('Request must be approved before confirming receipt', 400)
        
        if not req_data.get('pickup_completed_at'):
            return error_response('Item must be picked up by rider before confirming receipt', 400)
        
        # Update request
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE return_refund_requests
                SET item_received_at = NOW(), status = 'processing', updated_at = NOW()
                WHERE id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                UPDATE return_refund_requests
                SET item_received_at = CURRENT_TIMESTAMP, status = 'processing', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (request_id,))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id,
            'status': 'processing'
        }, 'Item receipt confirmed. Refund will be processed.')
        
    except Exception as e:
        app.logger.error('api_seller_confirm_item_received error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/riders/return-pickups', methods=['GET'])
@token_required
def api_rider_get_return_pickups():
    """Rider views available return pickup tasks"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'rider':
            return error_response('Only riders can view return pickups', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider_id
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM riders WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('SELECT id FROM riders WHERE user_id = ?', (user_id,))
        
        rider_row = cursor.fetchone()
        if not rider_row:
            return success_response({'pickups': []})
        
        rider_id = format_row(rider_row).get('id')
        
        # Get return pickup tasks (approved return requests that need pickup)
        # First check if return_refund_requests table exists
        try:
            if DB_ENGINE == 'mysql':
                # Check if table exists
                cursor.execute("SHOW TABLES LIKE 'return_refund_requests'")
                if not cursor.fetchone():
                    app.logger.warning('return_refund_requests table does not exist')
                    cursor.close()
                    return success_response({'pickups': []})
                
                # Check if seller_response column exists
                cursor.execute("SHOW COLUMNS FROM return_refund_requests LIKE 'seller_response'")
                has_seller_response = cursor.fetchone() is not None
                
                # Build WHERE clause based on available columns
                where_clause = "rrr.request_type IN ('return', 'both')"
                if has_seller_response:
                    where_clause += " AND rrr.seller_response = 'approved'"
                else:
                    where_clause += " AND rrr.status = 'approved'"
                
                # Check if item_received_at exists
                cursor.execute("SHOW COLUMNS FROM return_refund_requests LIKE 'item_received_at'")
                has_item_received_at = cursor.fetchone() is not None
                if has_item_received_at:
                    where_clause += " AND rrr.item_received_at IS NULL"
                
                # Check if pickup_rider_id exists
                cursor.execute("SHOW COLUMNS FROM return_refund_requests LIKE 'pickup_rider_id'")
                has_pickup_rider_id = cursor.fetchone() is not None
                if has_pickup_rider_id:
                    where_clause += " AND (rrr.pickup_rider_id IS NULL OR rrr.pickup_rider_id = %s)"
                    params = (rider_id,)
                else:
                    params = ()
                
                # Build SELECT columns list
                select_parts = [
                    'rrr.id', 'rrr.order_id', 'rrr.order_item_id', 'rrr.customer_id',
                    'rrr.request_type', 'rrr.reason', 'rrr.status'
                ]
                if has_seller_response:
                    select_parts.append('rrr.seller_response')
                if has_pickup_rider_id:
                    select_parts.append('rrr.pickup_rider_id')
                    cursor.execute("SHOW COLUMNS FROM return_refund_requests LIKE 'pickup_scheduled_at'")
                    if cursor.fetchone():
                        select_parts.append('rrr.pickup_scheduled_at')
                    cursor.execute("SHOW COLUMNS FROM return_refund_requests LIKE 'pickup_completed_at'")
                    if cursor.fetchone():
                        select_parts.append('rrr.pickup_completed_at')
                if has_item_received_at:
                    select_parts.append('rrr.item_received_at')
                cursor.execute("SHOW COLUMNS FROM return_refund_requests LIKE 'evidence_images'")
                if cursor.fetchone():
                    select_parts.append('rrr.evidence_images')
                select_parts.extend([
                    'rrr.created_at', 'rrr.updated_at',
                    'o.customer_name', 'o.customer_phone', 'o.customer_address',
                    'p.title as product_name', 'p.img_url as product_image',
                    'u.first_name as customer_first_name', 'u.last_name as customer_last_name',
                    'u.email as customer_email',
                    's.business_name as seller_name',
                    "CONCAT_WS(', ', NULLIF(TRIM(s.city), ''), NULLIF(TRIM(s.province), ''), NULLIF(TRIM(s.region), '')) as seller_address"
                ])
                
                query = f'''
                    SELECT {', '.join(select_parts)}
                    FROM return_refund_requests rrr
                    INNER JOIN orders o ON rrr.order_id = o.id
                    INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                    INNER JOIN products p ON oi.product_id = p.id
                    INNER JOIN users u ON rrr.customer_id = u.id
                    INNER JOIN sellers s ON rrr.seller_id = s.user_id
                    WHERE {where_clause}
                    ORDER BY rrr.created_at ASC
                '''
                
                app.logger.debug(f'Return pickups MySQL query: {query[:200]}...')
                cursor.execute(query, params)
            else:
                # SQLite: Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='return_refund_requests'")
                if not cursor.fetchone():
                    app.logger.warning('return_refund_requests table does not exist')
                    cursor.close()
                    return success_response({'pickups': []})
                
                # Check columns
                cursor.execute("PRAGMA table_info(return_refund_requests)")
                columns = [row[1] for row in cursor.fetchall()]
                has_seller_response = 'seller_response' in columns
                has_pickup_rider_id = 'pickup_rider_id' in columns
                has_item_received_at = 'item_received_at' in columns
                has_pickup_scheduled_at = 'pickup_scheduled_at' in columns
                has_pickup_completed_at = 'pickup_completed_at' in columns
                has_evidence_images = 'evidence_images' in columns
                
                # Build SELECT clause
                select_cols = ['rrr.id', 'rrr.order_id', 'rrr.order_item_id', 'rrr.customer_id',
                              'rrr.request_type', 'rrr.reason', 'rrr.status']
                if has_seller_response:
                    select_cols.append('rrr.seller_response')
                if has_pickup_rider_id:
                    select_cols.append('rrr.pickup_rider_id')
                if has_pickup_scheduled_at:
                    select_cols.append('rrr.pickup_scheduled_at')
                if has_pickup_completed_at:
                    select_cols.append('rrr.pickup_completed_at')
                if has_item_received_at:
                    select_cols.append('rrr.item_received_at')
                if has_evidence_images:
                    select_cols.append('rrr.evidence_images')
                select_cols.extend(['rrr.created_at', 'rrr.updated_at',
                                   'o.customer_name', 'o.customer_phone', 'o.customer_address',
                                   'p.title as product_name', 'p.img_url as product_image',
                                   'u.first_name as customer_first_name', 'u.last_name as customer_last_name',
                                   'u.email as customer_email',
                                   's.business_name as seller_name'])
                
                # Build seller address
                seller_addr = '''CASE 
                    WHEN s.city IS NOT NULL AND s.city != '' THEN
                        s.city || 
                        CASE WHEN s.province IS NOT NULL AND s.province != '' THEN ', ' || s.province ELSE '' END ||
                        CASE WHEN s.region IS NOT NULL AND s.region != '' THEN ', ' || s.region ELSE '' END
                    WHEN s.province IS NOT NULL AND s.province != '' THEN
                        s.province ||
                        CASE WHEN s.region IS NOT NULL AND s.region != '' THEN ', ' || s.region ELSE '' END
                    WHEN s.region IS NOT NULL AND s.region != '' THEN s.region
                    ELSE NULL
                END as seller_address'''
                select_cols.append(seller_addr)
                
                # Build WHERE clause
                where_parts = ["rrr.request_type IN ('return', 'both')"]
                if has_seller_response:
                    where_parts.append("rrr.seller_response = 'approved'")
                else:
                    where_parts.append("rrr.status = 'approved'")
                if has_item_received_at:
                    where_parts.append("rrr.item_received_at IS NULL")
                if has_pickup_rider_id:
                    where_parts.append("(rrr.pickup_rider_id IS NULL OR rrr.pickup_rider_id = ?)")
                    params = (rider_id,)
                else:
                    params = ()
                
                query = f'''
                    SELECT {', '.join(select_cols)}
                    FROM return_refund_requests rrr
                    INNER JOIN orders o ON rrr.order_id = o.id
                    INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                    INNER JOIN products p ON oi.product_id = p.id
                    INNER JOIN users u ON rrr.customer_id = u.id
                    INNER JOIN sellers s ON rrr.seller_id = s.user_id
                    WHERE {' AND '.join(where_parts)}
                    ORDER BY rrr.created_at ASC
                '''
                
                cursor.execute(query, params)
        except Exception as query_err:
            app.logger.error(f'Error executing return pickups query: {query_err}')
            import traceback
            app.logger.error(traceback.format_exc())
            if cursor:
                cursor.close()
            # Return empty list if query fails (table might not exist or columns missing)
            return success_response({'pickups': []})
        
        rows = cursor.fetchall()
        pickups = []
        for row in rows:
            try:
                pickup = format_row(row)
                # Set defaults for optional fields
                if 'seller_response' not in pickup:
                    pickup['seller_response'] = pickup.get('status', 'pending')
                if 'pickup_rider_id' not in pickup:
                    pickup['pickup_rider_id'] = None
                if 'pickup_scheduled_at' not in pickup:
                    pickup['pickup_scheduled_at'] = None
                if 'pickup_completed_at' not in pickup:
                    pickup['pickup_completed_at'] = None
                if 'item_received_at' not in pickup:
                    pickup['item_received_at'] = None
                
                # Parse evidence_images JSON if present
                if pickup.get('evidence_images'):
                    try:
                        import json
                        pickup['evidence_images'] = json.loads(pickup['evidence_images'])
                    except:
                        pickup['evidence_images'] = []
                else:
                    pickup['evidence_images'] = []
                pickups.append(pickup)
            except Exception as row_err:
                app.logger.error(f'Error processing return pickup row: {row_err}')
                import traceback
                app.logger.error(traceback.format_exc())
                # Continue to next row even if one fails
                continue
        
        if cursor:
            cursor.close()
        return success_response({'pickups': pickups})
        
    except Exception as e:
        app.logger.error('api_rider_get_return_pickups error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        # Return empty list instead of error to prevent UI breakage
        return success_response({'pickups': []})

@app.route('/api/riders/return-pickups/<int:request_id>/accept', methods=['POST'])
@token_required
def api_rider_accept_return_pickup(request_id):
    """Rider accepts a return pickup task"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'rider':
            return error_response('Only riders can accept return pickups', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider_id
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM riders WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('SELECT id FROM riders WHERE user_id = ?', (user_id,))
        
        rider_row = cursor.fetchone()
        if not rider_row:
            return error_response('Rider profile not found', 404)
        
        rider_id = format_row(rider_row).get('id')
        
        # Verify request exists and is available
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT pickup_rider_id, seller_response, request_type, pickup_completed_at
                FROM return_refund_requests WHERE id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                SELECT pickup_rider_id, seller_response, request_type, pickup_completed_at
                FROM return_refund_requests WHERE id = ?
            ''', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            return error_response('Request not found', 404)
        
        req_data = format_row(req_row)
        if req_data.get('seller_response') != 'approved':
            return error_response('Request must be approved by seller first', 400)
        
        if req_data.get('request_type') not in ('return', 'both'):
            return error_response('This is not a return request', 400)
        
        if req_data.get('pickup_completed_at'):
            return error_response('This pickup has already been completed', 400)
        
        if req_data.get('pickup_rider_id') and req_data.get('pickup_rider_id') != rider_id:
            return error_response('This pickup has already been assigned to another rider', 400)
        
        # Assign pickup to rider
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE return_refund_requests
                SET pickup_rider_id = %s, pickup_scheduled_at = NOW(), updated_at = NOW()
                WHERE id = %s
            ''', (rider_id, request_id))
        else:
            cursor.execute('''
                UPDATE return_refund_requests
                SET pickup_rider_id = ?, pickup_scheduled_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (rider_id, request_id))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id,
            'rider_id': rider_id
        }, 'Return pickup accepted successfully')
        
    except Exception as e:
        app.logger.error('api_rider_accept_return_pickup error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/riders/return-pickups/<int:request_id>/complete', methods=['POST'])
@token_required
def api_rider_complete_return_pickup(request_id):
    """Rider marks return pickup as completed"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'rider':
            return error_response('Only riders can complete return pickups', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider_id
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM riders WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('SELECT id FROM riders WHERE user_id = ?', (user_id,))
        
        rider_row = cursor.fetchone()
        if not rider_row:
            return error_response('Rider profile not found', 404)
        
        rider_id = format_row(rider_row).get('id')
        
        # Verify request exists and is assigned to this rider
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT pickup_rider_id, pickup_completed_at
                FROM return_refund_requests WHERE id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                SELECT pickup_rider_id, pickup_completed_at
                FROM return_refund_requests WHERE id = ?
            ''', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            return error_response('Request not found', 404)
        
        req_data = format_row(req_row)
        if req_data.get('pickup_rider_id') != rider_id:
            return error_response('This pickup is not assigned to you', 403)
        
        if req_data.get('pickup_completed_at'):
            return error_response('This pickup has already been completed', 400)
        
        # Mark pickup as completed
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE return_refund_requests
                SET pickup_completed_at = NOW(), updated_at = NOW()
                WHERE id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                UPDATE return_refund_requests
                SET pickup_completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (request_id,))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id
        }, 'Return pickup completed successfully')
        
    except Exception as e:
        app.logger.error('api_rider_complete_return_pickup error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/riders/return-pickups/<int:request_id>/mark-delivered', methods=['POST'])
@token_required
def api_rider_mark_delivered_to_seller(request_id):
    """Rider marks return item as delivered to seller"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'rider':
            return error_response('Only riders can mark items as delivered', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider_id
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM riders WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('SELECT id FROM riders WHERE user_id = ?', (user_id,))
        
        rider_row = cursor.fetchone()
        if not rider_row:
            return error_response('Rider profile not found', 404)
        
        rider_id = format_row(rider_row).get('id')
        
        # Verify request exists, is assigned to this rider, and has been picked up
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT pickup_rider_id, pickup_completed_at, seller_response, status
                FROM return_refund_requests WHERE id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                SELECT pickup_rider_id, pickup_completed_at, seller_response, status
                FROM return_refund_requests WHERE id = ?
            ''', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            return error_response('Request not found', 404)
        
        req_data = format_row(req_row)
        if req_data.get('pickup_rider_id') != rider_id:
            return error_response('This pickup is not assigned to you', 403)
        
        if not req_data.get('pickup_completed_at'):
            return error_response('Item must be picked up before marking as delivered to seller', 400)
        
        if req_data.get('seller_response') != 'approved':
            return error_response('Request must be approved by seller before delivery', 400)
        
        # Update status to indicate it's been delivered to seller and waiting for seller confirmation
        # The status will be updated to 'processing' when seller confirms receipt
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE return_refund_requests
                SET status = 'processing', updated_at = NOW()
                WHERE id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                UPDATE return_refund_requests
                SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (request_id,))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id,
            'status': 'processing'
        }, 'Item marked as delivered to seller. Waiting for seller confirmation.')
        
    except Exception as e:
        app.logger.error('api_rider_mark_delivered_to_seller error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/customer/return-refund-requests/<int:request_id>', methods=['GET'])
@token_required
def api_customer_get_request_details(request_id):
    """Customer views detailed status of their return/refund request"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        if role != 'customer':
            return error_response('Only customers can view their requests', 403)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get request details
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT rrr.*, o.customer_name, o.customer_address,
                       p.title as product_name, p.img_url as product_image,
                       s.business_name as seller_name
                FROM return_refund_requests rrr
                INNER JOIN orders o ON rrr.order_id = o.id
                INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN sellers s ON rrr.seller_id = s.user_id
                WHERE rrr.id = %s AND rrr.customer_id = %s
            ''', (request_id, user_id))
        else:
            cursor.execute('''
                SELECT rrr.*, o.customer_name, o.customer_address,
                       p.title as product_name, p.img_url as product_image,
                       s.business_name as seller_name
                FROM return_refund_requests rrr
                INNER JOIN orders o ON rrr.order_id = o.id
                INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN sellers s ON rrr.seller_id = s.user_id
                WHERE rrr.id = ? AND rrr.customer_id = ?
            ''', (request_id, user_id))
        
        req_row = cursor.fetchone()
        if not req_row:
            return error_response('Request not found', 404)
        
        request_data = format_row(req_row)
        
        # Parse evidence_images JSON if present
        if request_data.get('evidence_images'):
            try:
                import json
                request_data['evidence_images'] = json.loads(request_data['evidence_images'])
            except:
                request_data['evidence_images'] = []
        else:
            request_data['evidence_images'] = []
        
        cursor.close()
        return success_response({'request': request_data})
        
    except Exception as e:
        app.logger.error('api_customer_get_request_details error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/admin/return-refund-requests/<int:request_id>/approve', methods=['POST'])
@token_required
@role_required('admin')
def api_admin_approve_return_request(request_id):
    """Admin approves a return/refund request and verifies returned item"""
    try:
        admin_id = g.user_id
        db = get_db()
        cursor = db.cursor()
        
        # Get request with full details
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT rrr.*, oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal
                FROM return_refund_requests rrr
                LEFT JOIN order_items oi ON rrr.order_item_id = oi.id
                WHERE rrr.id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                SELECT rrr.*, oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal
                FROM return_refund_requests rrr
                LEFT JOIN order_items oi ON rrr.order_item_id = oi.id
                WHERE rrr.id = ?
            ''', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            cursor.close()
            return error_response('Request not found', 404)
        
        req_data = format_row(req_row)
        request_type = req_data.get('request_type', 'refund')
        
        # For return/both requests, check if item was received
        # If item_received_at exists, admin is verifying and approving for refund
        # If not, this is initial approval (waiting for rider pickup)
        has_item_received = req_data.get('item_received_at') and req_data.get('item_received_at') not in (None, '', 'None')
        
        if request_type in ('return', 'both') and has_item_received:
            # Item has been received - admin is verifying and approving for refund
            # Set status to 'processing' so refund can be processed
            new_status = 'processing'
            app.logger.info(f'Admin approving request #{request_id} after item verification - setting status to processing')
        else:
            # Initial approval or refund-only request
            new_status = 'approved'
            app.logger.info(f'Admin approving request #{request_id} - setting status to approved')
        
        # Update request - admin can approve even if seller hasn't responded
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE return_refund_requests
                SET seller_response = 'approved', status = %s, updated_at = NOW()
                WHERE id = %s
            ''', (new_status, request_id))
        else:
            cursor.execute('''
                UPDATE return_refund_requests
                SET seller_response = 'approved', status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, request_id))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id,
            'status': new_status,
            'message': 'Request approved successfully. Ready for refund processing.' if new_status == 'processing' else 'Request approved successfully.'
        }, 'Request approved successfully')
        
    except Exception as e:
        app.logger.error('api_admin_approve_return_request error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/admin/return-refund-requests/<int:request_id>/reject', methods=['POST'])
@token_required
@role_required('admin')
def api_admin_reject_return_request(request_id):
    """Admin rejects a return/refund request"""
    try:
        admin_id = g.user_id
        data = request.json or {}
        rejection_reason = data.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            return error_response('Rejection reason is required', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get request
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id, status FROM return_refund_requests WHERE id = %s', (request_id,))
        else:
            cursor.execute('SELECT id, status FROM return_refund_requests WHERE id = ?', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            cursor.close()
            return error_response('Request not found', 404)
        
        # Update request
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE return_refund_requests
                SET seller_response = 'rejected', status = 'rejected', rejection_reason = %s, updated_at = NOW()
                WHERE id = %s
            ''', (rejection_reason, request_id))
        else:
            cursor.execute('''
                UPDATE return_refund_requests
                SET seller_response = 'rejected', status = 'rejected', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (rejection_reason, request_id))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'request_id': request_id,
            'status': 'rejected'
        }, 'Request rejected successfully')
        
    except Exception as e:
        app.logger.error('api_admin_reject_return_request error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/admin/return-refund-requests/<int:request_id>/process-refund', methods=['POST'])
@token_required
def api_admin_process_refund(request_id):
    """Admin or Seller processes a refund for a return/refund request"""
    try:
        user_id = g.user_id
        user_role = g.role
        
        # Allow both admin and seller roles
        if user_role not in ('admin', 'seller'):
            return error_response('Only admins and sellers can process refunds', 403)
        db = get_db()
        cursor = db.cursor()
        
        # Get request details with order and item information
        # Note: rrr.seller_id is the user_id of the seller
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT rrr.*, o.id as order_id, o.total as order_total,
                       oi.id as order_item_id, oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal,
                       p.title as product_name, u.email as customer_email, u.first_name as customer_name
                FROM return_refund_requests rrr
                INNER JOIN orders o ON rrr.order_id = o.id
                INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN users u ON rrr.customer_id = u.id
                WHERE rrr.id = %s
            ''', (request_id,))
        else:
            cursor.execute('''
                SELECT rrr.*, o.id as order_id, o.total as order_total,
                       oi.id as order_item_id, oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal,
                       p.title as product_name, u.email as customer_email, u.first_name as customer_name
                FROM return_refund_requests rrr
                INNER JOIN orders o ON rrr.order_id = o.id
                INNER JOIN order_items oi ON rrr.order_item_id = oi.id
                INNER JOIN products p ON oi.product_id = p.id
                INNER JOIN users u ON rrr.customer_id = u.id
                WHERE rrr.id = ?
            ''', (request_id,))
        
        req_row = cursor.fetchone()
        if not req_row:
            cursor.close()
            return error_response('Request not found', 404)
        
        req_data = format_row(req_row)
        
        app.logger.info(f'Processing refund for request #{request_id}. Request data: {req_data}')
        
        # If user is a seller, verify they own this request
        # seller_id in return_refund_requests table is the user_id of the seller
        if user_role == 'seller':
            seller_id = req_data.get('seller_id')
            if not seller_id or int(seller_id) != int(user_id):
                cursor.close()
                return error_response('You can only process refunds for your own return/refund requests', 403)
        
        # Verify request is in processing status
        current_status = req_data.get('status')
        if current_status != 'processing':
            cursor.close()
            app.logger.warning(f'Request #{request_id} status is "{current_status}", expected "processing"')
            return error_response(f'Request must be in "processing" status to process refund. Current status: {current_status}', 400)
        
        # Verify request is approved
        if req_data.get('seller_response') != 'approved':
            cursor.close()
            return error_response('Request must be approved by seller before processing refund', 400)
        
        # For return requests, verify item was received
        if req_data.get('request_type') in ('return', 'both'):
            if not req_data.get('item_received_at'):
                cursor.close()
                return error_response('Item must be received by seller before processing refund', 400)
        
        # Calculate refund amount (use order item subtotal)
        subtotal = req_data.get('subtotal', 0)
        app.logger.info(f'Request #{request_id} subtotal: {subtotal} (type: {type(subtotal)})')
        
        try:
            refund_amount = float(subtotal) if subtotal else 0.0
        except (ValueError, TypeError) as e:
            cursor.close()
            app.logger.error(f'Invalid subtotal value for request #{request_id}: {subtotal}, error: {e}')
            return error_response(f'Invalid refund amount: {subtotal}', 400)
        
        if refund_amount <= 0:
            cursor.close()
            app.logger.error(f'Refund amount is 0 or negative for request #{request_id}: {refund_amount}')
            return error_response(f'Invalid refund amount: {refund_amount}', 400)
        
        # Process refund through payment service
        order_id = req_data.get('order_id')
        if not order_id:
            cursor.close()
            app.logger.error(f'Order ID is missing for request #{request_id}')
            return error_response('Order ID not found', 400)
        
        # Generate coupon code instead of cash refund
        import random
        import string
        customer_id = req_data.get('customer_id')
        product_name = req_data.get('product_name', 'Product')
        
        # Generate unique coupon code
        def generate_coupon_code():
            """Generate a unique 8-character alphanumeric coupon code"""
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                # Check if code already exists
                if DB_ENGINE == 'mysql':
                    cursor.execute('SELECT id FROM coupons WHERE code = %s', (code,))
                else:
                    cursor.execute('SELECT id FROM coupons WHERE code = ?', (code,))
                if not cursor.fetchone():
                    return code
        
        coupon_code = generate_coupon_code()
        
        # Set coupon expiration to 90 days from now
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(days=90)
        
        # Check if coupons table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'coupons'")
                coupons_table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coupons'")
                coupons_table_exists = cursor.fetchone() is not None
            
            if not coupons_table_exists:
                cursor.close()
                app.logger.warning('Coupons table does not exist. Please run migration: python qwerty/database/migrate_add_coupons.py')
                return error_response('Coupons system not initialized. Please contact administrator.', 500)
            
            # Create coupon
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    INSERT INTO coupons (code, customer_id, amount, status, issued_for, return_refund_request_id, expires_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ''', (coupon_code, customer_id, refund_amount, 'active', f'Refund for {product_name}', request_id, expires_at))
            else:
                cursor.execute('''
                    INSERT INTO coupons (code, customer_id, amount, status, issued_for, return_refund_request_id, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (coupon_code, customer_id, refund_amount, 'active', f'Refund for {product_name}', request_id, expires_at))
            
            coupon_id = cursor.lastrowid
            app.logger.info(f'Coupon created for request #{request_id}: Code={coupon_code}, Amount={refund_amount}, Customer={customer_id}')
            
        except Exception as coupon_error:
            db.rollback()
            cursor.close()
            app.logger.error(f'Error creating coupon for request #{request_id}: {coupon_error}')
            import traceback
            app.logger.error(traceback.format_exc())
            return error_response(f'Failed to create coupon: {str(coupon_error)}', 500)
        
        # Update request with refund processed timestamp and status
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    UPDATE return_refund_requests
                    SET refund_processed_at = NOW(), status = 'completed', updated_at = NOW()
                    WHERE id = %s
                ''', (request_id,))
                
                # Store coupon code in admin_notes or create a separate field
                # For now, we'll add it to admin_notes
                cursor.execute('''
                    UPDATE return_refund_requests
                    SET admin_notes = CONCAT(COALESCE(admin_notes, ''), '\nCoupon Code: ', %s)
                    WHERE id = %s AND (admin_notes IS NULL OR admin_notes NOT LIKE %s)
                ''', (coupon_code, request_id, f'%{coupon_code}%'))
                
                # Update order status to 'refunded' (orders table may not have updated_at column)
                try:
                    cursor.execute('''
                        UPDATE orders SET status = 'refunded', updated_at = NOW()
                        WHERE id = %s
                    ''', (order_id,))
                except Exception as order_update_error:
                    # If updated_at doesn't exist, try without it
                    app.logger.warning(f'Could not update orders.updated_at, trying without it: {order_update_error}')
                    cursor.execute('''
                        UPDATE orders SET status = 'refunded'
                        WHERE id = %s
                    ''', (order_id,))
            else:
                cursor.execute('''
                    UPDATE return_refund_requests
                    SET refund_processed_at = CURRENT_TIMESTAMP, status = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (request_id,))
                
                # Store coupon code in admin_notes for SQLite
                cursor.execute('''
                    UPDATE return_refund_requests
                    SET admin_notes = COALESCE(admin_notes, '') || '\nCoupon Code: ' || ?
                    WHERE id = ? AND (admin_notes IS NULL OR admin_notes NOT LIKE ?)
                ''', (coupon_code, request_id, f'%{coupon_code}%'))
                
                # Update order status to 'refunded' (orders table may not have updated_at column)
                try:
                    cursor.execute('''
                        UPDATE orders SET status = 'refunded', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (order_id,))
                except Exception as order_update_error:
                    # If updated_at doesn't exist, try without it
                    app.logger.warning(f'Could not update orders.updated_at, trying without it: {order_update_error}')
                    cursor.execute('''
                        UPDATE orders SET status = 'refunded'
                        WHERE id = ?
                    ''', (order_id,))
            
            db.commit()
            app.logger.info(f'Successfully updated request #{request_id} and order #{order_id} to refunded status')
        except Exception as db_error:
            db.rollback()
            cursor.close()
            app.logger.error(f'Database error updating refund status for request #{request_id}: {db_error}')
            import traceback
            app.logger.error(traceback.format_exc())
            return error_response(f'Database error: {str(db_error)}', 500)
        
        cursor.close()
        
        # TODO: Send notification email to customer with coupon code
        customer_email = req_data.get('customer_email')
        customer_name = req_data.get('customer_name')
        app.logger.info(f'Coupon issued for request #{request_id}. Code: {coupon_code}, Amount: {refund_amount}, Customer: {customer_email}')
        
        return success_response({
            'request_id': request_id,
            'coupon_code': coupon_code,
            'coupon_amount': refund_amount,
            'status': 'completed',
            'message': f'Coupon code {coupon_code} worth ₱{refund_amount:.2f} has been issued to customer'
        }, 'Coupon issued successfully')
        
    except Exception as e:
        app.logger.error('api_admin_process_refund error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)


@app.route('/api/customer/coupons', methods=['GET'])
@token_required
def api_customer_get_coupons():
    """Customer: Get all their coupons"""
    try:
        customer_id = g.user_id
        db = get_db()
        cursor = db.cursor()
        
        # Check if coupons table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'coupons'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coupons'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return success_response([], 'No coupons found')
        except Exception:
            cursor.close()
            return success_response([], 'No coupons found')
        
        # Get active coupons
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                SELECT * FROM coupons
                WHERE customer_id = %s
                ORDER BY created_at DESC
            """, (customer_id,))
        else:
            cursor.execute("""
                SELECT * FROM coupons
                WHERE customer_id = ?
                ORDER BY created_at DESC
            """, (customer_id,))
        
        coupons = cursor.fetchall()
        cursor.close()
        
        formatted_coupons = []
        for coupon in coupons:
            coupon_dict = format_row(coupon)
            # Check if coupon is expired
            if coupon_dict.get('expires_at'):
                from datetime import datetime
                expires_at = coupon_dict.get('expires_at')
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_at < datetime.utcnow():
                    coupon_dict['status'] = 'expired'
            formatted_coupons.append(coupon_dict)
        
        return success_response(formatted_coupons, 'Coupons retrieved successfully')
    except Exception as e:
        app.logger.error(f'Get customer coupons error: {e}')
        return error_response(str(e), 500)


@app.route('/api/coupons/<coupon_code>/validate', methods=['GET'])
@token_required
def api_validate_coupon(coupon_code):
    """Validate a coupon code for the current user"""
    try:
        customer_id = g.user_id
        db = get_db()
        cursor = db.cursor()
        
        # Check if coupons table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'coupons'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coupons'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return error_response('Coupons system not available', 404)
        except Exception:
            cursor.close()
            return error_response('Coupons system not available', 404)
        
        # Get coupon
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                SELECT * FROM coupons
                WHERE code = %s AND customer_id = %s
            """, (coupon_code, customer_id))
        else:
            cursor.execute("""
                SELECT * FROM coupons
                WHERE code = ? AND customer_id = ?
            """, (coupon_code, customer_id))
        
        coupon = cursor.fetchone()
        cursor.close()
        
        if not coupon:
            return error_response('Coupon not found', 404)
        
        coupon_dict = format_row(coupon)
        
        # Check if expired
        if coupon_dict.get('expires_at'):
            from datetime import datetime
            expires_at = coupon_dict.get('expires_at')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expires_at < datetime.utcnow():
                return error_response('Coupon has expired', 400)
        
        # Check if already used
        if coupon_dict.get('status') == 'used':
            return error_response('Coupon has already been used', 400)
        
        # Check remaining balance
        amount = float(coupon_dict.get('amount', 0))
        used_amount = float(coupon_dict.get('used_amount', 0))
        remaining = amount - used_amount
        
        if remaining <= 0:
            return error_response('Coupon balance is zero', 400)
        
        return success_response({
            'code': coupon_code,
            'amount': amount,
            'used_amount': used_amount,
            'remaining': remaining,
            'expires_at': coupon_dict.get('expires_at'),
            'status': coupon_dict.get('status')
        }, 'Coupon is valid')
    except Exception as e:
        app.logger.error(f'Validate coupon error: {e}')
        return error_response(str(e), 500)
        
    except Exception as e:
        app.logger.error('api_admin_process_refund error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(str(e), 500)

@app.route('/api/admin/return-refund-requests', methods=['GET'])
@token_required
@role_required('admin')
def api_admin_get_return_refund_requests():
    """Admin views all return/refund requests"""
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'return_refund_requests'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='return_refund_requests'")
                table_exists = cursor.fetchone() is not None
        except Exception as table_check_err:
            app.logger.warning(f'Error checking table existence: {table_check_err}')
            table_exists = False
        
        if not table_exists:
            if cursor:
                cursor.close()
            return success_response({'requests': []}, 'Return/refund requests table does not exist yet')
        
        # Get filter parameters
        status_filter = request.args.get('status')
        
        # Use a simple query with only basic columns first
        # We'll add optional columns in a try-except if they exist
        try:
            if DB_ENGINE == 'mysql':
                # Start with basic query
                base_query = '''
                    SELECT rrr.id, rrr.order_id, rrr.order_item_id, rrr.customer_id, rrr.seller_id,
                           rrr.request_type, rrr.reason, rrr.status, rrr.seller_response, rrr.rejection_reason,
                           rrr.pickup_rider_id, rrr.pickup_scheduled_at, rrr.pickup_completed_at,
                           rrr.item_received_at, rrr.refund_processed_at, rrr.created_at, rrr.updated_at,
                           o.customer_name, o.customer_phone, o.customer_address, o.total as order_total,
                           oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal,
                           p.title as product_name, p.img_url as product_image,
                           s.business_name as seller_name, s.user_id as seller_user_id,
                           u.first_name as customer_first_name, u.last_name as customer_last_name,
                           u.email as customer_email
                    FROM return_refund_requests rrr
                    LEFT JOIN orders o ON rrr.order_id = o.id
                    LEFT JOIN order_items oi ON rrr.order_item_id = oi.id
                    LEFT JOIN products p ON oi.product_id = p.id
                    LEFT JOIN sellers s ON rrr.seller_id = s.user_id
                    LEFT JOIN users u ON rrr.customer_id = u.id
                '''
                where_clause = ''
                params = []
                
                if status_filter and status_filter != 'all':
                    where_clause = 'WHERE rrr.status = %s'
                    params.append(status_filter)
                
                query = base_query + where_clause + ' ORDER BY rrr.created_at DESC'
                app.logger.debug(f'Executing basic query: {query[:200]}... with params: {params}')
                cursor.execute(query, params)
            else:
                base_query = '''
                    SELECT rrr.id, rrr.order_id, rrr.order_item_id, rrr.customer_id, rrr.seller_id,
                           rrr.request_type, rrr.reason, rrr.status, rrr.seller_response, rrr.rejection_reason,
                           rrr.pickup_rider_id, rrr.pickup_scheduled_at, rrr.pickup_completed_at,
                           rrr.item_received_at, rrr.refund_processed_at, rrr.created_at, rrr.updated_at,
                           o.customer_name, o.customer_phone, o.customer_address, o.total as order_total,
                           oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal,
                           p.title as product_name, p.img_url as product_image,
                           s.business_name as seller_name, s.user_id as seller_user_id,
                           u.first_name as customer_first_name, u.last_name as customer_last_name,
                           u.email as customer_email
                    FROM return_refund_requests rrr
                    LEFT JOIN orders o ON rrr.order_id = o.id
                    LEFT JOIN order_items oi ON rrr.order_item_id = oi.id
                    LEFT JOIN products p ON oi.product_id = p.id
                    LEFT JOIN sellers s ON rrr.seller_id = s.user_id
                    LEFT JOIN users u ON rrr.customer_id = u.id
                '''
                where_clause = ''
                params = []
                
                if status_filter and status_filter != 'all':
                    where_clause = 'WHERE rrr.status = ?'
                    params.append(status_filter)
                
                query = base_query + where_clause + ' ORDER BY rrr.created_at DESC'
                app.logger.debug(f'Executing basic query: {query[:200]}... with params: {params}')
                cursor.execute(query, params)
        except Exception as query_err:
            app.logger.error(f'Query execution error: {query_err}')
            import traceback
            app.logger.error(traceback.format_exc())
            # Try a simpler query without optional columns
            try:
                if cursor:
                    cursor.close()
                cursor = db.cursor()
                
                if DB_ENGINE == 'mysql':
                    simple_query = '''
                        SELECT rrr.id, rrr.order_id, rrr.order_item_id, rrr.customer_id, rrr.seller_id,
                               rrr.request_type, rrr.reason, rrr.status, rrr.seller_response, rrr.rejection_reason,
                           rrr.pickup_rider_id, rrr.pickup_scheduled_at, rrr.pickup_completed_at,
                           rrr.item_received_at, rrr.refund_processed_at, rrr.created_at, rrr.updated_at,
                               o.customer_name, o.customer_phone, o.customer_address, o.total as order_total,
                               oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal,
                               p.title as product_name, p.img_url as product_image,
                               s.business_name as seller_name, s.user_id as seller_user_id,
                               u.first_name as customer_first_name, u.last_name as customer_last_name,
                               u.email as customer_email
                        FROM return_refund_requests rrr
                        LEFT JOIN orders o ON rrr.order_id = o.id
                        LEFT JOIN order_items oi ON rrr.order_item_id = oi.id
                        LEFT JOIN products p ON oi.product_id = p.id
                        LEFT JOIN sellers s ON rrr.seller_id = s.user_id
                        LEFT JOIN users u ON rrr.customer_id = u.id
                    '''
                    if status_filter and status_filter != 'all':
                        simple_query += ' WHERE rrr.status = %s'
                        cursor.execute(simple_query + ' ORDER BY rrr.created_at DESC', (status_filter,))
                    else:
                        cursor.execute(simple_query + ' ORDER BY rrr.created_at DESC')
                else:
                    simple_query = '''
                        SELECT rrr.id, rrr.order_id, rrr.order_item_id, rrr.customer_id, rrr.seller_id,
                               rrr.request_type, rrr.reason, rrr.status, rrr.seller_response, rrr.rejection_reason,
                           rrr.pickup_rider_id, rrr.pickup_scheduled_at, rrr.pickup_completed_at,
                           rrr.item_received_at, rrr.refund_processed_at, rrr.created_at, rrr.updated_at,
                               o.customer_name, o.customer_phone, o.customer_address, o.total as order_total,
                               oi.quantity, oi.price, (oi.quantity * oi.price) as subtotal,
                               p.title as product_name, p.img_url as product_image,
                               s.business_name as seller_name, s.user_id as seller_user_id,
                               u.first_name as customer_first_name, u.last_name as customer_last_name,
                               u.email as customer_email
                        FROM return_refund_requests rrr
                        LEFT JOIN orders o ON rrr.order_id = o.id
                        LEFT JOIN order_items oi ON rrr.order_item_id = oi.id
                        LEFT JOIN products p ON oi.product_id = p.id
                        LEFT JOIN sellers s ON rrr.seller_id = s.user_id
                        LEFT JOIN users u ON rrr.customer_id = u.id
                    '''
                    if status_filter and status_filter != 'all':
                        simple_query += ' WHERE rrr.status = ?'
                        cursor.execute(simple_query + ' ORDER BY rrr.created_at DESC', (status_filter,))
                    else:
                        cursor.execute(simple_query + ' ORDER BY rrr.created_at DESC')
            except Exception as simple_query_err:
                app.logger.error(f'Simple query also failed: {simple_query_err}')
                if cursor:
                    cursor.close()
                return error_response(f'Database query error: {str(query_err)}', 500)
        
        rows = cursor.fetchall()
        requests = []
        
        for row in rows:
            try:
                req_data = format_row(row)
                
                # Set default values for missing columns
                if 'seller_response' not in req_data:
                    req_data['seller_response'] = None
                if 'rejection_reason' not in req_data:
                    req_data['rejection_reason'] = None
                if 'pickup_rider_id' not in req_data:
                    req_data['pickup_rider_id'] = None
                if 'pickup_scheduled_at' not in req_data:
                    req_data['pickup_scheduled_at'] = None
                if 'pickup_completed_at' not in req_data:
                    req_data['pickup_completed_at'] = None
                if 'item_received_at' not in req_data:
                    req_data['item_received_at'] = None
                if 'refund_processed_at' not in req_data:
                    req_data['refund_processed_at'] = None
                if 'admin_notes' not in req_data:
                    req_data['admin_notes'] = None
                
                # Fix: If item_received_at exists but status is still 'approved', update status to 'processing'
                # This handles cases where the status wasn't updated correctly
                if req_data.get('item_received_at') and req_data.get('status') == 'approved':
                    app.logger.warning(f'Request #{req_data.get("id")} has item_received_at but status is still "approved". Fixing...')
                    if DB_ENGINE == 'mysql':
                        cursor.execute('''
                            UPDATE return_refund_requests
                            SET status = 'processing', updated_at = NOW()
                            WHERE id = %s AND status = 'approved'
                        ''', (req_data.get('id'),))
                    else:
                        cursor.execute('''
                            UPDATE return_refund_requests
                            SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ? AND status = 'approved'
                        ''', (req_data.get('id'),))
                    db.commit()
                    req_data['status'] = 'processing'
                
                # Parse evidence_images JSON if present
                if req_data.get('evidence_images'):
                    try:
                        import json
                        if isinstance(req_data['evidence_images'], str):
                            req_data['evidence_images'] = json.loads(req_data['evidence_images'])
                    except:
                        req_data['evidence_images'] = []
                else:
                    req_data['evidence_images'] = []
                
                # Set defaults for joined data
                req_data['customer_name'] = req_data.get('customer_name') or ''
                req_data['product_name'] = req_data.get('product_name') or 'Unknown Product'
                req_data['seller_name'] = req_data.get('seller_name') or 'Unknown Seller'
                req_data['subtotal'] = req_data.get('subtotal') or 0
                
                requests.append(req_data)
            except Exception as row_err:
                app.logger.warning(f'Error processing return/refund request row: {row_err}')
                import traceback
                app.logger.warning(traceback.format_exc())
                continue
        
        if cursor:
            cursor.close()
        return success_response({'requests': requests}, 'Return/refund requests retrieved successfully')
        
    except Exception as e:
        app.logger.error('api_admin_get_return_refund_requests error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        if cursor:
            try:
                cursor.close()
            except:
                pass
        return error_response(f'Failed to load return/refund requests: {str(e)}', 500)

@app.route('/api/riders/earnings', methods=['GET'])
@token_required
def api_rider_earnings():
    """Rider views earnings"""
    token = get_token_from_request()
    if not token:
        return error_response('Unauthorized', 401)
    
    try:
        payload = verify_token(token)
        rider_id = payload.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Total earnings (delivery fees from completed orders)
        cursor.execute('''
            SELECT SUM(delivery_fee) FROM orders 
            WHERE rider_id=? AND status='delivered'
        ''', (rider_id,))
        total_earnings = cursor.fetchone()[0] or 0
        
        # Completed deliveries
        cursor.execute('SELECT COUNT(*) FROM orders WHERE rider_id=? AND status=?', 
                      (rider_id, 'delivered'))
        completed = cursor.fetchone()[0]
        
        # Active deliveries
        cursor.execute('SELECT COUNT(*) FROM orders WHERE rider_id=? AND status IN (?, ?)', 
                      (rider_id, 'dispatched', 'in-transit'))
        active = cursor.fetchone()[0]
        
        # Average rating (from reviews if implemented)
        rating = 4.8  # placeholder
        
        return success_response({
            'total_earnings': round(total_earnings, 2),
            'completed_deliveries': completed,
            'active_deliveries': active,
            'rating': rating
        }, 'Earnings data')
    except Exception as e:
        return error_response(str(e), 500)

# ==================== ADMIN ENDPOINTS ====================

@app.route('/api/admin/dashboard', methods=['GET'])
@role_required('admin')
def api_admin_dashboard():
    """Admin views comprehensive platform dashboard with real-time metrics"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Total users by role
        cursor.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role')
        rows = cursor.fetchall()
        user_counts = {row['role']: row['count'] for row in rows} if rows else {}
        
        # Sales Today
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total
                FROM orders 
                WHERE DATE(created_at) = CURDATE()
                AND status IN ('delivered', 'dispatched', 'processing')
            ''')
        else:
            cursor.execute('''
                SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total
                FROM orders 
                WHERE DATE(created_at) = DATE('now')
                AND status IN ('delivered', 'dispatched', 'processing')
            ''')
        row = cursor.fetchone()
        sales_today_count = int(row['count']) if row else 0
        sales_today_amount = float(row['total']) if row else 0.0
        
        # Sales This Month
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total
                FROM orders 
                WHERE YEAR(created_at) = YEAR(CURDATE())
                AND MONTH(created_at) = MONTH(CURDATE())
                AND status IN ('delivered', 'dispatched', 'processing')
            ''')
        else:
            cursor.execute('''
                SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total
                FROM orders 
                WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                AND status IN ('delivered', 'dispatched', 'processing')
            ''')
        row = cursor.fetchone()
        sales_month_count = int(row['count']) if row else 0
        sales_month_amount = float(row['total']) if row else 0.0
        
        # Pending Orders - orders that are placed but not yet processing/dispatched
        if DB_ENGINE == 'mysql':
            cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")
        row = cursor.fetchone()
        pending_orders = int(row['count']) if row else 0
        
        # Total orders and revenue (completed)
        if DB_ENGINE == 'mysql':
            cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total FROM orders WHERE status='delivered'")
        else:
            cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total FROM orders WHERE status='delivered'")
        row = cursor.fetchone()
        completed_orders = int(row['count']) if row else 0
        total_revenue = float(row['total']) if row else 0.0
        
        # Total orders (all statuses)
        cursor.execute('SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total FROM orders')
        row = cursor.fetchone()
        total_orders = int(row['count']) if row else 0
        total_volume = float(row['total']) if row else 0.0
        
        # Pending verifications
        if DB_ENGINE == 'mysql':
            cursor.execute("SELECT COUNT(*) as count FROM sellers WHERE shop_status='pending'")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM sellers WHERE shop_status='pending'")
        row = cursor.fetchone()
        pending_sellers = int(row['count']) if row else 0
        
        if DB_ENGINE == 'mysql':
            cursor.execute("SELECT COUNT(*) as count FROM riders WHERE rider_status='pending'")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM riders WHERE rider_status='pending'")
        row = cursor.fetchone()
        pending_riders = int(row['count']) if row else 0
        
        # Active orders
        if DB_ENGINE == 'mysql':
            cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status IN ('dispatched', 'processing')")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status IN ('dispatched', 'processing')")
        row = cursor.fetchone()
        active_orders = int(row['count']) if row else 0
        
        # Average order value
        avg_order_value = total_volume / total_orders if total_orders > 0 else 0
        
        # Average rating - calculate from reviews table
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT COALESCE(AVG(rating), 0) as avg_rating FROM reviews')
            else:
                cursor.execute('SELECT COALESCE(AVG(rating), 0) as avg_rating FROM reviews')
            rating_row = cursor.fetchone()
            avg_rating = float(rating_row['avg_rating'] or 0) if rating_row else 0.0
        except Exception as rating_err:
            app.logger.warning(f'Could not calculate average rating: {rating_err}')
            avg_rating = 0.0
        
        # Total sellers - count unique sellers (not stores)
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT COUNT(DISTINCT id) as count FROM sellers WHERE COALESCE(shop_status, \'pending\') = \'active\'')
            else:
                cursor.execute('SELECT COUNT(DISTINCT id) as count FROM sellers WHERE COALESCE(shop_status, \'pending\') = \'active\'')
            seller_row = cursor.fetchone()
            active_sellers_count = int(seller_row['count'] or 0) if seller_row else 0
        except Exception as seller_err:
            app.logger.warning(f'Could not count active sellers: {seller_err}')
            active_sellers_count = user_counts.get('seller', 0)
        
        # Total riders - count active riders
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT COUNT(DISTINCT id) as count FROM riders WHERE COALESCE(rider_status, \'pending\') = \'active\'')
            else:
                cursor.execute('SELECT COUNT(DISTINCT id) as count FROM riders WHERE COALESCE(rider_status, \'pending\') = \'active\'')
            rider_row = cursor.fetchone()
            active_riders_count = int(rider_row['count'] or 0) if rider_row else 0
        except Exception as rider_err:
            app.logger.warning(f'Could not count active riders: {rider_err}')
            active_riders_count = user_counts.get('rider', 0)
        
        cursor.close()
        
        dashboard_data = {
            'sales_today': round(sales_today_amount, 2),
            'sales_today_count': sales_today_count,
            'sales_month': round(sales_month_amount, 2),
            'sales_month_count': sales_month_count,
            'pending_orders': pending_orders,
            'avg_rating': round(avg_rating, 1),
            'total_users': sum(user_counts.values()),
            'total_sellers': active_sellers_count,
            'total_riders': active_riders_count,
            'total_customers': user_counts.get('customer', 0),
            'total_admins': user_counts.get('admin', 0),
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'active_orders': active_orders,
            'total_revenue': round(total_revenue, 2),
            'total_volume': round(total_volume, 2),
            'avg_order_value': round(avg_order_value, 2),
            'pending_verifications': pending_sellers + pending_riders,
            'pending_sellers': pending_sellers,
            'pending_riders': pending_riders
        }
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
    except Exception as e:
        app.logger.error('admin_dashboard error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/top-products', methods=['GET'])
@role_required('admin')
def api_admin_top_products():
    """Get top-selling products across all sellers"""
    try:
        limit = int(request.args.get('limit', 10))
        
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT p.id, p.title, p.img_url, p.category, p.price, p.stock,
                       COALESCE(SUM(oi.quantity), 0) as total_sold,
                       COALESCE(SUM(oi.price * oi.quantity), 0) as total_revenue,
                       s.business_name as seller_name
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id
                LEFT JOIN sellers s ON p.seller_id = s.user_id
                WHERE o.status IN ('delivered', 'dispatched', 'processing') OR o.status IS NULL
                GROUP BY p.id, p.title, p.img_url, p.category, p.price, p.stock, s.business_name
                ORDER BY total_sold DESC
                LIMIT %s
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT p.id, p.title, p.img_url, p.category, p.price, p.stock,
                       COALESCE(SUM(oi.quantity), 0) as total_sold,
                       COALESCE(SUM(oi.price * oi.quantity), 0) as total_revenue,
                       s.business_name as seller_name
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id
                LEFT JOIN sellers s ON p.seller_id = s.user_id
                WHERE o.status IN ('delivered', 'dispatched', 'processing') OR o.status IS NULL
                GROUP BY p.id
                ORDER BY total_sold DESC
                LIMIT ?
            ''', (limit,))
        
        products = []
        for row in cursor.fetchall():
            product = row2dict(row) if hasattr(row, 'keys') else {
                'id': row[0],
                'title': row[1],
                'img_url': row[2],
                'category': row[3],
                'price': float(row[4]),
                'stock': int(row[5]),
                'total_sold': int(row[6]),
                'total_revenue': float(row[7]),
                'seller_name': row[8]
            }
            products.append(product)
        
        cursor.close()
        return jsonify({'success': True, 'data': products})
    except Exception as e:
        app.logger.error('admin_top_products error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/recent-activities', methods=['GET'])
@role_required('admin')
def api_admin_recent_activities():
    """Get recent activities across platform"""
    try:
        limit = int(request.args.get('limit', 20))
        
        db = get_db()
        cursor = db.cursor()
        
        activities = []
        
        # Get recent orders
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT o.id, o.customer_name, o.status, o.total, o.created_at,
                       'order' as activity_type, NULL as rating, NULL as review_text
                FROM orders o
                ORDER BY o.created_at DESC
                LIMIT %s
            ''', (limit // 2,))
        else:
            cursor.execute('''
                SELECT o.id, o.customer_name, o.status, o.total, o.created_at,
                       'order' as activity_type, NULL as rating, NULL as review_text
                FROM orders o
                ORDER BY o.created_at DESC
                LIMIT ?
            ''', (limit // 2,))
        
        for row in cursor.fetchall():
            activity = format_row(row)
            activities.append({
                'id': activity.get('id'),
                'customer_name': activity.get('customer_name'),
                'status': activity.get('status'),
                'total': float(activity.get('total', 0)),
                'created_at': activity.get('created_at'),
                'activity_type': 'order'
            })
        
        # Get recent reviews
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT r.id, u.first_name, u.last_name, r.rating, r.comment, r.created_at,
                           p.title as product_name
                    FROM reviews r
                    LEFT JOIN users u ON r.user_id = u.id
                    LEFT JOIN products p ON r.product_id = p.id
                    ORDER BY r.created_at DESC
                    LIMIT %s
                ''', (limit // 2,))
            else:
                cursor.execute('''
                    SELECT r.id, u.first_name, u.last_name, r.rating, r.comment, r.created_at,
                           p.title as product_name
                    FROM reviews r
                    LEFT JOIN users u ON r.user_id = u.id
                    LEFT JOIN products p ON r.product_id = p.id
                    ORDER BY r.created_at DESC
                    LIMIT ?
                ''', (limit // 2,))
            
            for row in cursor.fetchall():
                review = format_row(row)
                customer_name = f"{review.get('first_name', '')} {review.get('last_name', '')}".strip() or 'Customer'
                activities.append({
                    'id': review.get('id'),
                    'customer_name': customer_name,
                    'rating': int(review.get('rating', 0)),
                    'comment': review.get('comment'),
                    'product_name': review.get('product_name'),
                    'created_at': review.get('created_at'),
                    'activity_type': 'review'
                })
        except Exception as review_err:
            app.logger.warning(f'Could not fetch reviews: {review_err}')
        
        # Get recent user registrations
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT id, first_name, last_name, email, role, created_at
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT %s
                ''', (limit // 4,))
            else:
                cursor.execute('''
                    SELECT id, first_name, last_name, email, role, created_at
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit // 4,))
            
            for row in cursor.fetchall():
                user = format_row(row)
                customer_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('email', 'User')
                activities.append({
                    'id': user.get('id'),
                    'customer_name': customer_name,
                    'role': user.get('role'),
                    'created_at': user.get('created_at'),
                    'activity_type': 'registration'
                })
        except Exception as user_err:
            app.logger.warning(f'Could not fetch user registrations: {user_err}')
        
        # Sort all activities by created_at descending and limit
        activities.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        activities = activities[:limit]
        
        cursor.close()
        return jsonify({'success': True, 'data': activities})
    except Exception as e:
        app.logger.error('admin_recent_activities error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/revenue-trend', methods=['GET'])
@role_required('admin')
def api_admin_revenue_trend():
    """Get platform-wide revenue trend"""
    try:
        period = request.args.get('period', '30')
        days = int(period)
        
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT DATE(created_at) as date, 
                       COALESCE(SUM(total), 0) as revenue,
                       COUNT(*) as orders
                FROM orders
                WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                AND status IN ('delivered', 'dispatched', 'processing')
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (days,))
        else:
            cursor.execute(f'''
                SELECT DATE(created_at) as date, 
                       COALESCE(SUM(total), 0) as revenue,
                       COUNT(*) as orders
                FROM orders
                WHERE created_at >= date('now', '-{days} days')
                AND status IN ('delivered', 'dispatched', 'processing')
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''')
        
        trend_data = []
        for row in cursor.fetchall():
            data = row2dict(row) if hasattr(row, 'keys') else {
                'date': str(row[0]),
                'revenue': float(row[1]),
                'orders': int(row[2])
            }
            trend_data.append(data)
        
        cursor.close()
        return jsonify({'success': True, 'data': trend_data})
    except Exception as e:
        app.logger.error('admin_revenue_trend error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/user-growth', methods=['GET'])
@role_required('admin')
def api_admin_user_growth():
    """Get user growth trend over time"""
    try:
        days = int(request.args.get('days', 30))
        
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT DATE(created_at) as date,
                       COUNT(*) as new_users
                FROM users
                WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''', (days,))
        else:
            cursor.execute(f'''
                SELECT DATE(created_at) as date,
                       COUNT(*) as new_users
                FROM users
                WHERE created_at >= date('now', '-{days} days')
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            ''')
        
        growth_data = []
        for row in cursor.fetchall():
            data = format_row(row)
            growth_data.append({
                'date': str(data.get('date', '')),
                'new_users': int(data.get('new_users', 0))
            })
        
        cursor.close()
        return jsonify({'success': True, 'data': growth_data})
    except Exception as e:
        app.logger.error('admin_user_growth error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/approval-breakdown', methods=['GET'])
@role_required('admin')
def api_admin_approval_breakdown():
    """Get approval status breakdown for sellers, stores, and sales"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Sellers breakdown
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'pending' THEN 1 ELSE 0 END) as sellers_pending,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'active' THEN 1 ELSE 0 END) as sellers_approved,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'suspended' THEN 1 ELSE 0 END) as sellers_rejected
                FROM sellers
            ''')
        else:
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'pending' THEN 1 ELSE 0 END) as sellers_pending,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'active' THEN 1 ELSE 0 END) as sellers_approved,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'suspended' THEN 1 ELSE 0 END) as sellers_rejected
                FROM sellers
            ''')
        seller_breakdown = format_row(cursor.fetchone())
        
        # Stores breakdown
        stores_pending = 0
        stores_approved = 0
        stores_rejected = 0
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                    FROM stores
                ''')
            else:
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                    FROM stores
                ''')
            store_row = cursor.fetchone()
            if store_row:
                store_breakdown = format_row(store_row)
                stores_pending = int(store_breakdown.get('pending', 0) or 0)
                stores_approved = int(store_breakdown.get('approved', 0) or 0)
                stores_rejected = int(store_breakdown.get('rejected', 0) or 0)
        except Exception as store_err:
            app.logger.warning(f'Could not get store breakdown: {store_err}')
        
        # Sales/discounts breakdown
        sales_pending = 0
        sales_approved = 0
        sales_rejected = 0
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                        SUM(CASE WHEN status IN ('rejected', 'declined') THEN 1 ELSE 0 END) as rejected
                    FROM product_sales
                ''')
            else:
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                        SUM(CASE WHEN status IN ('rejected', 'declined') THEN 1 ELSE 0 END) as rejected
                    FROM product_sales
                ''')
            sales_row = cursor.fetchone()
            if sales_row:
                sales_breakdown = format_row(sales_row)
                sales_pending = int(sales_breakdown.get('pending', 0) or 0)
                sales_approved = int(sales_breakdown.get('approved', 0) or 0)
                sales_rejected = int(sales_breakdown.get('rejected', 0) or 0)
        except Exception as sales_err:
            app.logger.warning(f'Could not get sales breakdown: {sales_err}')
        
        # Total breakdown
        total_pending = (int(seller_breakdown.get('sellers_pending', 0) or 0) + 
                        stores_pending + sales_pending)
        total_approved = (int(seller_breakdown.get('sellers_approved', 0) or 0) + 
                         stores_approved + sales_approved)
        total_rejected = (int(seller_breakdown.get('sellers_rejected', 0) or 0) + 
                         stores_rejected + sales_rejected)
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'data': {
                'sellers': {
                    'pending': int(seller_breakdown.get('sellers_pending', 0) or 0),
                    'approved': int(seller_breakdown.get('sellers_approved', 0) or 0),
                    'rejected': int(seller_breakdown.get('sellers_rejected', 0) or 0)
                },
                'stores': {
                    'pending': stores_pending,
                    'approved': stores_approved,
                    'rejected': stores_rejected
                },
                'sales': {
                    'pending': sales_pending,
                    'approved': sales_approved,
                    'rejected': sales_rejected
                },
                'total': {
                    'pending': total_pending,
                    'approved': total_approved,
                    'rejected': total_rejected
                }
            }
        })
    except Exception as e:
        app.logger.error('admin_approval_breakdown error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/order-growth', methods=['GET'])
@role_required('admin')
def api_admin_order_growth():
    """Get platform order growth statistics"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN YEAR(created_at) = YEAR(CURDATE()) 
                              AND MONTH(created_at) = MONTH(CURDATE()) THEN 1 END) as this_month,
                    COUNT(CASE WHEN YEAR(created_at) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                              AND MONTH(created_at) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) THEN 1 END) as last_month
                FROM orders
            ''')
        else:
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now') THEN 1 END) as this_month,
                    COUNT(CASE WHEN strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', '-1 month') THEN 1 END) as last_month
                FROM orders
            ''')
        
        row = cursor.fetchone()
        this_month = int(row['this_month'] or 0)
        last_month = int(row['last_month'] or 0)
        
        growth_percentage = 0
        if last_month > 0:
            growth_percentage = ((this_month - last_month) / last_month) * 100
        elif this_month > 0:
            growth_percentage = 100
        
        cursor.close()
        return jsonify({
            'success': True,
            'data': {
                'this_month': this_month,
                'last_month': last_month,
                'growth_percentage': round(growth_percentage, 1),
                'growth_direction': 'up' if growth_percentage > 0 else 'down' if growth_percentage < 0 else 'stable'
            }
        })
    except Exception as e:
        app.logger.error('admin_order_growth error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/sellers', methods=['GET'])
@role_required('admin')
def api_admin_sellers():
    """Admin views all sellers"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT s.id, u.id as user_id, u.email, u.first_name, u.last_name, 
                       s.business_name, s.category, s.verified, u.created_at,
                       s.business_permit, s.valid_id, s.address_proof, s.business_logo,
                       COALESCE(s.shop_status, 'pending') as account_status,
                       s.shop_status, s.missing_requirements, s.declined_at, s.decline_reason,
                FROM sellers s
                INNER JOIN users u ON s.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT s.id, u.id as user_id, u.email, u.first_name, u.last_name, 
                       s.business_name, s.category, s.verified, u.created_at,
                       s.business_permit, s.valid_id, s.address_proof, s.business_logo,
                       COALESCE(s.shop_status, 'pending') as account_status,
                       s.shop_status, s.missing_requirements, s.declined_at, s.decline_reason,
                FROM sellers s
                INNER JOIN users u ON s.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        
        sellers = [format_row(row) for row in cursor.fetchall()]
        cursor.close()
        
        return jsonify({'success': True, 'sellers': sellers})
    except Exception as e:
        app.logger.error('admin_sellers error: %s', e)
        return jsonify({'error': 'server_error'}), 500


@app.route('/api/admin/riders', methods=['GET'])
@role_required('admin')
def api_admin_riders():
    """Admin views all riders"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT r.id, u.id as user_id, u.email, u.first_name, u.last_name,
                       r.vehicle_type, r.driver_license, r.verified, u.created_at,
                       r.valid_id, r.vehicle_or_cr, r.profile_photo, r.plate_number,
                       r.rider_status, r.missing_requirements, r.declined_at, r.decline_reason
                FROM riders r
                INNER JOIN users u ON r.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT r.id, u.id as user_id, u.email, u.first_name, u.last_name,
                       r.vehicle_type, r.driver_license, r.verified, u.created_at,
                       r.valid_id, r.vehicle_or_cr, r.profile_photo, r.plate_number,
                       r.rider_status, r.missing_requirements, r.declined_at, r.decline_reason
                FROM riders r
                INNER JOIN users u ON r.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        
        riders = [format_row(row) for row in cursor.fetchall()]
        cursor.close()
        
        return jsonify({'success': True, 'riders': riders})
    except Exception as e:
        app.logger.error('admin_riders error: %s', e)
        return jsonify({'error': 'server_error'}), 500


@app.route('/api/admin/riders/<int:rider_id>', methods=['DELETE'])
@role_required('admin')
def api_admin_delete_rider(rider_id):
    """
    Delete a rider account completely from the system.
    This will also delete associated data.
    """
    try:
        # Get admin user ID from token
        admin_id = g.user_id
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider info before deletion
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT user_id, first_name, last_name FROM riders r INNER JOIN users u ON r.user_id = u.id WHERE r.id = %s', (rider_id,))
        else:
            cursor.execute('SELECT user_id, first_name, last_name FROM riders r INNER JOIN users u ON r.user_id = u.id WHERE r.id = ?', (rider_id,))
        
        rider_row = cursor.fetchone()
        if not rider_row:
            cursor.close()
            return jsonify({'error': 'not_found', 'message': 'Rider not found'}), 404
        
        rider = format_row(rider_row)
        rider_user_id = rider.get('user_id')
        rider_name = f"{rider.get('first_name', '')} {rider.get('last_name', '')}".strip() or 'Unknown'
        
        # Delete related data (in order to avoid foreign key constraints)
        # Handle deletions with try-except to gracefully handle missing tables/columns
        
        # 1. Delete rider record
        if DB_ENGINE == 'mysql':
            cursor.execute('DELETE FROM riders WHERE id = %s', (rider_id,))
        else:
            cursor.execute('DELETE FROM riders WHERE id = ?', (rider_id,))
        
        # 2. Optionally delete user account (commented out to preserve user data)
        # cursor.execute('DELETE FROM users WHERE id = %s', (rider_user_id,))
        
        # Commit the transaction
        try:
            db.commit()
            app.logger.info(f'Rider {rider_id} ({rider_name}) deleted by admin {admin_id}')
        except Exception as commit_error:
            app.logger.error('Failed to commit rider deletion: %s', commit_error)
            cursor.close()
            return jsonify({'error': 'commit_failed', 'message': 'Failed to delete rider'}), 500
        
        cursor.close()
        
        return jsonify({
            'success': True, 
            'message': f'Rider "{rider_name}" deleted successfully',
            'rider_id': rider_id
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error('admin_delete_rider error: %s', e)
        app.logger.error('Full traceback: %s', error_trace)
        return jsonify({
            'error': 'server_error', 
            'message': str(e),
            'details': error_trace if app.debug else 'Check server logs for details'
        }), 500


@app.route('/api/admin/orders', methods=['GET'])
@role_required('admin')
def api_admin_orders():
    """Admin views all orders"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT id, customer_name, customer_phone, subtotal, delivery_fee, total, 
                       payment, status, created_at
                FROM orders
                ORDER BY created_at DESC LIMIT 100
            ''')
        else:
            cursor.execute('''
                SELECT id, customer_name, customer_phone, subtotal, delivery_fee, total, 
                       payment, status, created_at
                FROM orders
                ORDER BY created_at DESC LIMIT 100
            ''')
        
        orders = [format_row(row) for row in cursor.fetchall()]
        cursor.close()
        
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        app.logger.error('admin_orders error: %s', e)
        return jsonify({'error': 'server_error'}), 500


# ============================================================================
# SELLER REVIEW SYSTEM - Admin endpoints for reviewing seller applications
# ============================================================================

@app.route('/api/admin/sellers/pending', methods=['GET'])
@role_required('admin')
def api_admin_sellers_pending():
    """
    Get all sellers with pending or declined status for admin review.
    Query params:
        - status: filter by status (pending, declined, active) - default: pending,declined
        - search: search by business name, email, or name
        - sort: sort field (created_at, business_name) - default: created_at
        - order: sort order (asc, desc) - default: desc
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get query parameters
        status_filter = request.args.get('status', 'pending,declined')
        search = request.args.get('search', '').strip()
        sort_field = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc').upper()
        
        # Build status filter - handle 'all' case
        # Note: shop_status in sellers table represents seller account status, not store status
        # Map filter values to seller account statuses
        status_map = {
            'pending': 'pending',
            'active': 'active',
            'approved': 'active',  # approved sellers are active
            'declined': 'declined',  # declined sellers
            'suspended': 'suspended',
            'warning': 'warning',
            'banned': 'banned'
        }
        
        if status_filter == 'all':
            status_where = ''
            params = []
        else:
            statuses = [s.strip() for s in status_filter.split(',')]
            # Map filter statuses to seller account statuses
            mapped_statuses = [status_map.get(s, s) for s in statuses]
            status_placeholders = ','.join(['%s'] * len(mapped_statuses)) if DB_ENGINE == 'mysql' else ','.join(['?'] * len(mapped_statuses))
            status_where = f'WHERE COALESCE(s.shop_status, \'pending\') IN ({status_placeholders})'
            params = mapped_statuses.copy()
        
        # Base query - single store per seller (no store count needed)
        query = f'''
            SELECT s.id, s.user_id, s.business_name, s.category, s.region, s.province, s.city,
                   COALESCE(s.shop_status, 'pending') as account_status,
                   s.shop_status, s.verified, s.approved_at,
                   u.email, u.first_name, u.last_name, u.created_at
            FROM sellers s
            INNER JOIN users u ON s.user_id = u.id
            {status_where}
        '''
        
        # Add search filter
        if search:
            search_connector = 'WHERE' if not status_where else 'AND'
            if DB_ENGINE == 'mysql':
                query += f''' {search_connector} (s.business_name LIKE %s OR u.email LIKE %s 
                               OR u.first_name LIKE %s OR u.last_name LIKE %s)'''
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param, search_param])
            else:
                query += f''' {search_connector} (s.business_name LIKE ? OR u.email LIKE ? 
                               OR u.first_name LIKE ? OR u.last_name LIKE ?)'''
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param, search_param])
        
        # Add sorting
        valid_sort_fields = ['created_at', 'business_name', 'status', 'reviewed_at']
        if sort_field not in valid_sort_fields:
            sort_field = 'created_at'
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'DESC'
        
        if sort_field == 'created_at':
            query += f' ORDER BY u.created_at {sort_order}'
        elif sort_field == 'business_name':
            query += f' ORDER BY s.business_name {sort_order}'
        elif sort_field == 'status':
            query += f' ORDER BY COALESCE(s.shop_status, \'pending\') {sort_order}, u.created_at DESC'
        elif sort_field == 'reviewed_at':
            query += f' ORDER BY s.approved_at {sort_order}'
        
        cursor.execute(query, params)
        sellers = [format_row(row) for row in cursor.fetchall()]
        cursor.close()
        
        return jsonify({'success': True, 'sellers': sellers, 'count': len(sellers)})
    except Exception as e:
        app.logger.error('admin_sellers_pending error: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/sellers/<int:seller_id>', methods=['GET'])
@role_required('admin')
def api_admin_seller_details(seller_id):
    """Get detailed information about a specific seller for review, including all their stores"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get seller details
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT s.id, s.user_id, s.business_name, s.category, s.region, s.province, s.city,
                       s.shop_status, s.verified, s.approved_at,
                       u.email, u.first_name, u.last_name, u.created_at, u.is_verified
                FROM sellers s
                INNER JOIN users u ON s.user_id = u.id
                WHERE s.id = %s
            ''', (seller_id,))
        else:
            cursor.execute('''
                SELECT s.id, s.user_id, s.business_name, s.category, s.region, s.province, s.city,
                       s.shop_status, s.verified, s.approved_at,
                       u.email, u.first_name, u.last_name, u.created_at, u.is_verified
                FROM sellers s
                INNER JOIN users u ON s.user_id = u.id
                WHERE s.id = ?
            ''', (seller_id,))
        
        seller = format_row(cursor.fetchone())
        
        if not seller:
            cursor.close()
            return jsonify({'error': 'not_found', 'message': 'Seller not found'}), 404
        
        # Get product count for this seller
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT COUNT(*) as count FROM products WHERE seller_id = %s', (seller['user_id'],))
        else:
            cursor.execute('SELECT COUNT(*) as count FROM products WHERE seller_id = ?', (seller['user_id'],))
        
        product_count_row = cursor.fetchone()
        seller['product_count'] = product_count_row['count'] if product_count_row else 0
        
        # Multi-store functionality removed - single store per seller
        # Add account_status field for consistency
        seller['account_status'] = seller.get('shop_status') or 'pending'
        
        cursor.close()
        
        return jsonify({'success': True, 'seller': seller, 'audit_log': []})
    except Exception as e:
        app.logger.error('admin_seller_details error: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/sellers/<int:seller_id>/status', methods=['PUT'])
@role_required('admin')
def api_admin_update_seller_status(seller_id):
    """
    Update seller account status.
    Request body:
        - status: 'active', 'declined', 'warning', 'suspended', or 'banned' - required
        - reason: reason for status change (required for declined, suspended, banned, warning)
        - duration_days: suspension duration in days (optional, for suspended status)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'invalid_request', 'message': 'Request body is required'}), 400
        
        new_status = data.get('status', '').lower()
        reason = data.get('reason', '').strip()
        duration_days = data.get('duration_days')
        
        app.logger.info(f'Updating seller {seller_id} status to: {new_status}, reason: {reason[:50] if reason else "none"}')
        
        # Validation
        valid_statuses = ['active', 'declined', 'warning', 'suspended', 'banned']
        if new_status not in valid_statuses:
            return jsonify({'error': 'invalid_status', 'message': f'Status must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Require reason for status changes that need explanation
        if new_status in ['declined', 'suspended', 'banned', 'warning'] and not reason:
            return jsonify({'error': 'reason_required', 'message': f'Reason is required when setting status to "{new_status}"'}), 400
        
        # Get admin user ID from token
        admin_id = g.user_id
        if not admin_id:
            return jsonify({'error': 'unauthorized', 'message': 'Admin ID not found in token'}), 401
        
        db = get_db()
        cursor = db.cursor()
        
        # Get current seller status - use shop_status column
        try:
            cursor.execute('SELECT shop_status, user_id, business_name FROM sellers WHERE id = %s', (seller_id,))
            
            seller_row = cursor.fetchone()
            if not seller_row:
                cursor.close()
                return jsonify({'error': 'not_found', 'message': 'Seller not found'}), 404
            
            seller = format_row(seller_row)
            previous_status = seller.get('shop_status') or 'pending'
            seller_user_id = seller.get('user_id')
            business_name = seller.get('business_name', 'Unknown')
        except Exception as fetch_error:
            app.logger.error(f'Error fetching seller data: {fetch_error}')
            cursor.close()
            return jsonify({'error': 'server_error', 'message': f'Failed to fetch seller data: {str(fetch_error)}'}), 500
        
        # Map status to shop_status values
        status_mapping = {
            'active': 'active',
            'declined': 'declined',
            'warning': 'warning',
            'suspended': 'suspended',
            'banned': 'banned'
        }
        shop_status_value = status_mapping.get(new_status, new_status)
        
        # Update seller status based on new status (MySQL only)
        if new_status == 'active':
            try:
                cursor.execute('''
                    UPDATE sellers 
                    SET shop_status = %s, verified = 1, reviewed_by = %s, 
                        reviewed_at = NOW(), rejection_reason = NULL, suspended_until = NULL
                    WHERE id = %s
                ''', (shop_status_value, admin_id, seller_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in active update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, verified = 1
                        WHERE id = %s
                    ''', (shop_status_value, seller_id))
                except Exception as col_error2:
                    app.logger.error(f'All active update attempts failed: {col_error2}')
                    raise
        elif new_status == 'suspended':
            # Handle suspension with optional duration
            try:
                if duration_days:
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, verified = 0, reviewed_by = %s, 
                            reviewed_at = NOW(), rejection_reason = %s,
                            suspended_until = DATE_ADD(NOW(), INTERVAL %s DAY)
                        WHERE id = %s
                    ''', (shop_status_value, admin_id, reason, duration_days, seller_id))
                else:
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, verified = 0, reviewed_by = %s, 
                            reviewed_at = NOW(), rejection_reason = %s
                        WHERE id = %s
                    ''', (shop_status_value, admin_id, reason, seller_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in suspended update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, verified = 0
                        WHERE id = %s
                    ''', (shop_status_value, seller_id))
                except Exception as col_error2:
                    app.logger.error(f'All suspended update attempts failed: {col_error2}')
                    raise
        elif new_status == 'banned':
            # Try to update with all columns, but handle missing columns gracefully
            try:
                cursor.execute('''
                    UPDATE sellers 
                    SET shop_status = %s, verified = 0, reviewed_by = %s, 
                        reviewed_at = NOW(), rejection_reason = %s, suspended_until = NULL
                    WHERE id = %s
                ''', (shop_status_value, admin_id, reason, seller_id))
            except Exception as col_error:
                # If some columns don't exist, try without them
                app.logger.warning(f'Column error (trying without optional columns): {col_error}')
                try:
                    # Try without reviewed_by, suspended_until, and rejection_reason
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, verified = 0, reviewed_at = NOW()
                        WHERE id = %s
                    ''', (shop_status_value, seller_id))
                except Exception as col_error2:
                    # If reviewed_at doesn't exist either, try minimal update
                    app.logger.warning(f'Column error (trying minimal update): {col_error2}')
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, verified = 0
                        WHERE id = %s
                    ''', (shop_status_value, seller_id))
            
            # Deactivate the user account when seller is banned
            try:
                if seller_user_id:
                    cursor.execute('UPDATE users SET is_active = 0 WHERE id = %s', (seller_user_id,))
            except Exception as user_update_error:
                app.logger.warning(f'Failed to deactivate user account for banned seller: {user_update_error}')
        elif new_status == 'warning':
            # Warning updates status but doesn't block account access
            try:
                cursor.execute('''
                    UPDATE sellers 
                    SET shop_status = %s, reviewed_by = %s, reviewed_at = NOW(), rejection_reason = %s
                    WHERE id = %s
                ''', (shop_status_value, admin_id, reason, seller_id))
            except Exception as col_error:
                # If some columns don't exist, try without them
                app.logger.warning(f'Column error in warning update (trying without optional columns): {col_error}')
                try:
                    # Try without reviewed_by and reviewed_at
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, rejection_reason = %s
                        WHERE id = %s
                    ''', (shop_status_value, reason, seller_id))
                except Exception as col_error2:
                    # If rejection_reason doesn't exist, just update shop_status
                    app.logger.warning(f'Column error in warning update (trying minimal update): {col_error2}')
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s
                        WHERE id = %s
                    ''', (shop_status_value, seller_id))
        else:  # declined
            try:
                cursor.execute('''
                    UPDATE sellers 
                    SET shop_status = %s, verified = 0, reviewed_by = %s, 
                        reviewed_at = NOW(), rejection_reason = %s
                    WHERE id = %s
                ''', (shop_status_value, admin_id, reason, seller_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in declined update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE sellers 
                        SET shop_status = %s, verified = 0
                        WHERE id = %s
                    ''', (shop_status_value, seller_id))
                except Exception as col_error2:
                    app.logger.error(f'All declined update attempts failed: {col_error2}')
                    raise
        
        # Map status to action name for audit log
        action_map = {
            'active': 'APPROVED',
            'declined': 'DECLINED',
            'warning': 'WARNING',
            'suspended': 'SUSPENSION',
            'banned': 'BAN'
        }
        action = action_map.get(new_status, new_status.upper())
        
        # Log the action in audit log (optional - don't fail if table doesn't exist)
        try:
            cursor.execute('''
                INSERT INTO seller_audit_log (seller_id, admin_id, action, previous_status, new_status, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ''', (seller_id, admin_id, action, previous_status, shop_status_value, reason))
        except Exception as audit_error:
            # Audit log is optional - just log warning and continue
            app.logger.warning('Failed to log to seller_audit_log (table may not exist): %s', audit_error)
            # Try to log to generic audit_logs table as fallback
            try:
                # Use the correct column names for audit_logs table
                cursor.execute('''
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                ''', ('seller', seller_id, action.lower(), reason, admin_id))
            except Exception as fallback_error:
                # Both audit log attempts failed - that's okay, just log it
                app.logger.warning('Failed to log to audit_logs fallback (table may not exist): %s', fallback_error)
        
        # Commit the transaction
        try:
            db.commit()
            app.logger.info(f'Seller {seller_id} status updated from "{previous_status}" to "{shop_status_value}" by admin {admin_id}')
            
            # Verify the update was successful
            cursor.execute('SELECT shop_status FROM sellers WHERE id = %s', (seller_id,))
            verify_row = cursor.fetchone()
            if verify_row:
                verify_status = format_row(verify_row).get('shop_status')
                app.logger.info(f'Verified: Seller {seller_id} shop_status is now: {verify_status}')
                if verify_status != shop_status_value:
                    app.logger.error(f'ERROR: Expected shop_status={shop_status_value}, but database shows {verify_status}')
        except Exception as commit_error:
            app.logger.error('Failed to commit status update: %s', commit_error)
            db.rollback()
            cursor.close()
            return jsonify({'error': 'commit_failed', 'message': 'Failed to save status update'}), 500
        
        # Send notification to seller
        try:
            notification_titles = {
                'active': '🎉 Seller Account Approved!',
                'declined': '❌ Seller Account Declined',
                'warning': '⚠️ Warning Issued',
                'suspended': '⏸️ Account Suspended',
                'banned': '🔨 Account Banned'
            }
            notification_bodies = {
                'active': f'Congratulations! Your seller account "{business_name}" has been approved. You can now start selling on our platform.',
                'declined': f'Your seller account application for "{business_name}" has been declined. Reason: {reason}',
                'warning': f'A warning has been issued for your seller account "{business_name}". Reason: {reason}',
                'suspended': f'Your seller account "{business_name}" has been suspended. Reason: {reason}' + (f' Duration: {duration_days} days' if duration_days else ''),
                'banned': f'Your seller account "{business_name}" has been permanently banned. Reason: {reason}'
            }
            
            notification_title = notification_titles.get(new_status, 'Account Status Updated')
            notification_body = notification_bodies.get(new_status, f'Your seller account status has been updated to: {new_status}')
            
            cursor.execute('''
                INSERT INTO notifications (user_id, title, body, `read`, created_at)
                VALUES (%s, %s, %s, 0, NOW())
            ''', (seller_user_id, notification_title, notification_body))
            
            # Commit the notification separately (it's optional)
            db.commit()
        except Exception as notif_error:
            # Notification is optional - just log warning and continue
            app.logger.warning('Failed to send notification (table may not exist): %s', notif_error)
            # Don't rollback - the main update was already committed
        
        cursor.close()
        
        return jsonify({
            'success': True, 
            'message': f'Seller status updated to "{new_status}" successfully',
            'seller_id': seller_id,
            'new_status': shop_status_value,
            'previous_status': previous_status
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error('admin_update_seller_status error: %s', e)
        app.logger.error('Full traceback: %s', error_trace)
        return jsonify({
            'error': 'server_error', 
            'message': str(e),
            'details': error_trace if app.debug else 'Check server logs for details'
        }), 500


@app.route('/api/admin/sellers/<int:seller_id>', methods=['DELETE'])
@role_required('admin')
def api_admin_delete_seller(seller_id):
    """
    Delete a seller account completely from the system.
    This will also delete associated products, orders, and other related data.
    """
    try:
        # Get admin user ID from token
        admin_id = g.user_id
        
        db = get_db()
        cursor = db.cursor()
        
        # Get seller info before deletion
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT user_id, business_name FROM sellers WHERE id = %s', (seller_id,))
        else:
            cursor.execute('SELECT user_id, business_name FROM sellers WHERE id = ?', (seller_id,))
        
        seller_row = cursor.fetchone()
        if not seller_row:
            cursor.close()
            return jsonify({'error': 'not_found', 'message': 'Seller not found'}), 404
        
        seller = format_row(seller_row)
        seller_user_id = seller.get('user_id')
        business_name = seller.get('business_name', 'Unknown')
        
        # Delete related data (in order to avoid foreign key constraints)
        # Handle deletions with try-except to gracefully handle missing tables/columns
        
        # 1. Delete reviews for seller's products first (before products are deleted)
        try:
            if DB_ENGINE == 'mysql':
                # Get product IDs first, then delete reviews
                cursor.execute('SELECT id FROM products WHERE seller_id = %s', (seller_user_id,))
                product_ids = [row[0] if isinstance(row, (list, tuple)) else row.get('id') for row in cursor.fetchall()]
                if product_ids:
                    placeholders = ','.join(['%s'] * len(product_ids))
                    cursor.execute(f'DELETE FROM reviews WHERE product_id IN ({placeholders})', product_ids)
            else:
                cursor.execute('SELECT id FROM products WHERE seller_id = ?', (seller_user_id,))
                product_ids = [row[0] if isinstance(row, (list, tuple)) else row.get('id') for row in cursor.fetchall()]
                if product_ids:
                    placeholders = ','.join(['?'] * len(product_ids))
                    cursor.execute(f'DELETE FROM reviews WHERE product_id IN ({placeholders})', product_ids)
        except Exception as review_error:
            app.logger.warning(f'Error deleting reviews (may not exist): {review_error}')
        
        # 2. Delete products
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('DELETE FROM products WHERE seller_id = %s', (seller_user_id,))
            else:
                cursor.execute('DELETE FROM products WHERE seller_id = ?', (seller_user_id,))
        except Exception as product_error:
            app.logger.warning(f'Error deleting products: {product_error}')
            # Continue anyway
        
        # 3. Delete seller audit logs (table may not exist)
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('DELETE FROM seller_audit_log WHERE seller_id = %s', (seller_id,))
            else:
                cursor.execute('DELETE FROM seller_audit_log WHERE seller_id = ?', (seller_id,))
        except Exception as audit_error:
            app.logger.warning(f'Error deleting audit logs (table may not exist): {audit_error}')
            # Continue anyway - audit log is optional
        
        # 4. Delete seller record
        if DB_ENGINE == 'mysql':
            cursor.execute('DELETE FROM sellers WHERE id = %s', (seller_id,))
        else:
            cursor.execute('DELETE FROM sellers WHERE id = ?', (seller_id,))
        
        # 5. Optionally delete user account (commented out to preserve user data)
        # cursor.execute('DELETE FROM users WHERE id = %s', (seller_user_id,))
        
        # Commit the transaction
        try:
            db.commit()
            app.logger.info(f'Seller {seller_id} ({business_name}) deleted by admin {admin_id}')
        except Exception as commit_error:
            app.logger.error('Failed to commit seller deletion: %s', commit_error)
            cursor.close()
            return jsonify({'error': 'commit_failed', 'message': 'Failed to delete seller'}), 500
        
        cursor.close()
        
        return jsonify({
            'success': True, 
            'message': f'Seller "{business_name}" deleted successfully',
            'seller_id': seller_id
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error('admin_delete_seller error: %s', e)
        app.logger.error('Full traceback: %s', error_trace)
        return jsonify({
            'error': 'server_error', 
            'message': str(e),
            'details': error_trace if app.debug else 'Check server logs for details'
        }), 500


@app.route('/api/admin/sellers/<int:seller_id>/approve', methods=['POST'])
@role_required('admin')
def api_admin_seller_approve(seller_id):
    """Admin approves a seller application"""
    try:
        db = get_db()
        cur = db.cursor()
        
        # Get current user (admin)
        admin_id = g.current_user_id
        
        # Get seller info
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT s.*, u.email, u.first_name 
                FROM sellers s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.id = %s
            """, (seller_id,))
        else:
            cur.execute("""
                SELECT s.*, u.email, u.first_name 
                FROM sellers s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.id = ?
            """, (seller_id,))
        
        seller = cur.fetchone()
        if not seller:
            return jsonify({'error': 'Seller not found'}), 404
        
        seller_dict = row2dict(seller)
        
        # Update seller status to active
        if DB_ENGINE == 'mysql':
            cur.execute("""
                UPDATE sellers 
                SET verified = 1, shop_status = 'active', approved_at = NOW()
                WHERE id = %s
            """, (seller_id,))
        else:
            cur.execute("""
                UPDATE sellers 
                SET verified = 1, shop_status = 'active', approved_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), seller_id))
        
        # Log to audit_logs
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('seller', %s, 'approve', 'Seller application approved', %s, NOW())
                """, (seller_id, admin_id))
            else:
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('seller', ?, 'approve', 'Seller application approved', ?, ?)
                """, (seller_id, admin_id, datetime.utcnow().isoformat()))
        except Exception:
            pass  # audit_logs might not exist yet
        
        db.commit()
        
        # Send notification email
        try:
            from backend.email_service import send_email
            subject = "🎉 Your Seller Account Has Been Approved!"
            body = f"""Dear {seller_dict.get('first_name', 'Seller')},

Congratulations! Your seller account for "{seller_dict.get('business_name', 'your shop')}" has been approved.

✅ Your shop is now ACTIVE
✅ You can start adding products immediately
✅ Your products will appear in the marketplace

Next Steps:
1. Login to your seller dashboard
2. Add your first products
3. Start receiving orders

Thank you for joining Hub E-Commerce!

Best regards,
Hub Team
"""
            send_email(seller_dict.get('email'), subject, body)
        except Exception as e:
            print(f"[WARN] Failed to send approval email: {e}")
        
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Seller approved successfully',
            'seller_id': seller_id,
            'shop_status': 'active'
        })
    except Exception as e:
        app.logger.error('Error approving seller: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/sellers/<int:seller_id>/decline', methods=['POST'])
@role_required('admin')
def api_admin_seller_decline(seller_id):
    """Admin declines a seller application"""
    try:
        db = get_db()
        cur = db.cursor()
        
        body = request.json or {}
        missing_requirements = body.get('missing_requirements', [])
        reason = body.get('reason', 'Application does not meet requirements')
        
        # Get current user (admin)
        admin_id = g.current_user_id
        
        # Get seller info
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT s.*, u.email, u.first_name 
                FROM sellers s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.id = %s
            """, (seller_id,))
        else:
            cur.execute("""
                SELECT s.*, u.email, u.first_name 
                FROM sellers s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.id = ?
            """, (seller_id,))
        
        seller = cur.fetchone()
        if not seller:
            return jsonify({'error': 'Seller not found'}), 404
        
        seller_dict = row2dict(seller)
        
        # Convert missing_requirements list to comma-separated string
        missing_req_str = ', '.join(missing_requirements) if missing_requirements else None
        
        # Update seller status to suspended/declined
        if DB_ENGINE == 'mysql':
            cur.execute("""
                UPDATE sellers 
                SET verified = 0, shop_status = 'suspended', missing_requirements = %s
                WHERE id = %s
            """, (missing_req_str, seller_id))
        else:
            cur.execute("""
                UPDATE sellers 
                SET verified = 0, shop_status = 'suspended', missing_requirements = ?
                WHERE id = ?
            """, (missing_req_str, seller_id))
        
        # Log to audit_logs
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('seller', %s, 'suspend', %s, %s, NOW())
                """, (seller_id, reason, admin_id))
            else:
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('seller', ?, 'suspend', ?, ?, ?)
                """, (seller_id, reason, admin_id, datetime.utcnow().isoformat()))
        except Exception:
            pass  # audit_logs might not exist yet
        
        db.commit()
        
        # Send notification email
        try:
            from backend.email_service import send_email
            subject = "Application Update - Hub E-Commerce"
            
            missing_list = '\n'.join([f"• {req}" for req in missing_requirements]) if missing_requirements else "See admin message below"
            
            body = f"""Dear {seller_dict.get('first_name', 'Seller')},

Thank you for your interest in becoming a seller on Hub E-Commerce.

We have reviewed your application for "{seller_dict.get('business_name', 'your shop')}" and need additional information or documentation.

Missing Requirements:
{missing_list}

Additional Notes:
{reason}

Please update your application with the required information and resubmit.

If you have questions, please contact our support team.

Best regards,
Hub Team
"""
            send_email(seller_dict.get('email'), subject, body)
        except Exception as e:
            print(f"[WARN] Failed to send decline email: {e}")
        
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Seller application declined',
            'seller_id': seller_id,
            'shop_status': 'suspended'
        })
    except Exception as e:
        app.logger.error('Error declining seller: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/sellers/<int:seller_id>/request-documents', methods=['POST'])
@role_required('admin')
def api_admin_request_seller_documents(seller_id):
    """Admin requests seller to submit additional documents"""
    try:
        db = get_db()
        cur = db.cursor()
        
        body = request.json or {}
        document_types = body.get('document_types', [])
        reason = body.get('reason', 'Additional verification required')
        
        if not document_types:
            return jsonify({'error': 'No document types specified'}), 400
        
        # Get seller info
        if DB_ENGINE == 'mysql':
            cur.execute("SELECT s.*, u.email FROM sellers s JOIN users u ON s.user_id=u.id WHERE s.id=%s", (seller_id,))
        else:
            cur.execute("SELECT s.*, u.email FROM sellers s JOIN users u ON s.user_id=u.id WHERE s.id=?", (seller_id,))
        
        seller = cur.fetchone()
        if not seller:
            return jsonify({'error': 'Seller not found'}), 404
        
        seller_dict = row2dict(seller)
        
        # Store document request in database (if table exists)
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    INSERT INTO seller_document_requests 
                    (seller_id, document_types, reason, requested_at, status) 
                    VALUES (%s, %s, %s, %s, 'pending')
                """, (seller_id, ','.join(document_types), reason, datetime.utcnow().isoformat()))
            else:
                cur.execute("""
                    INSERT INTO seller_document_requests 
                    (seller_id, document_types, reason, requested_at, status) 
                    VALUES (?, ?, ?, ?, 'pending')
                """, (seller_id, ','.join(document_types), reason, datetime.utcnow().isoformat()))
            db.commit()
        except Exception:
            # Table might not exist, that's okay - just log the request
            pass
        
        # Send email to seller
        try:
            subject = "Additional Documents Required - Hub E-Commerce"
            doc_list = ', '.join(document_types)
            body_text = f"""
Dear {seller_dict.get('business_name', 'Seller')},

We need additional documents to complete your seller verification:

Required Documents: {doc_list}
Reason: {reason}

Please upload these documents through your seller dashboard or reply to this email.

Best regards,
Hub E-Commerce Team
            """
            send_otp_email(seller_dict.get('email'), '', 'seller_doc_request', subject=subject, body=body_text)
        except Exception as e:
            print(f"[WARN] Failed to send document request email: {e}")
        
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Document request sent to seller',
            'seller_id': seller_id,
            'documents_requested': document_types
        })
    except Exception as e:
        app.logger.error('admin_request_documents error: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/sellers/stats', methods=['GET'])
@role_required('admin')
def api_admin_seller_stats():
    """Get statistics about seller accounts (pending, active, declined counts)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'suspended' THEN 1 ELSE 0 END) as declined
                FROM sellers
            ''')
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN COALESCE(shop_status, 'pending') = 'suspended' THEN 1 ELSE 0 END) as declined
                FROM sellers
            ''')
        
        stats = format_row(cursor.fetchone())
        cursor.close()
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        app.logger.error('admin_seller_stats error: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


# ==========================================
# SELLER ACTION ENDPOINTS
# ==========================================

@app.route('/api/admin/seller/warning', methods=['POST'])
@role_required('admin')
def api_admin_seller_warning():
    """Issue a warning to a seller"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        seller_id = data.get('seller_id')
        warning_type = data.get('warning_type')
        message = data.get('message')
        
        if not seller_id or not message:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Log audit event (safely handles missing table)
        log_audit_event(db, 'seller', seller_id, f'WARNING: {warning_type}', message, admin_id)
        
        # Update seller warning count
        try:
            cursor.execute('''
                UPDATE sellers SET warning_count = COALESCE(warning_count, 0) + 1 WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                UPDATE sellers SET warning_count = COALESCE(warning_count, 0) + 1 WHERE id = ?
            ''', (seller_id,))
            db.commit()
        except Exception as col_err:
            # Column might not exist, continue anyway
            print(f"[WARN] Could not update warning_count: {col_err}")
        
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Warning issued successfully'})
    except Exception as e:
        app.logger.error('admin_seller_warning error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/seller/suspend', methods=['POST'])
@role_required('admin')
def api_admin_seller_suspend():
    """Suspend a seller account"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        seller_id = data.get('seller_id')
        duration_days = data.get('duration_days')
        reason = data.get('reason')
        
        if not seller_id or not duration_days or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Calculate suspension end date
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE sellers 
                SET shop_status = 'suspended', suspended_until = DATE_ADD(NOW(), INTERVAL %s DAY)
                WHERE id = %s
            ''', (duration_days, seller_id))
        else:
            cursor.execute('''
                UPDATE sellers 
                SET shop_status = 'suspended', suspended_until = datetime('now', '+' || ? || ' days')
                WHERE id = ?
            ''', (duration_days, seller_id))
        
        # Log audit event (safely handles missing table)
        log_audit_event(db, 'seller', seller_id, 'SUSPENSION', reason, admin_id, duration_days=duration_days)
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Seller suspended successfully'})
    except Exception as e:
        app.logger.error('admin_seller_suspend error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/seller/fine', methods=['POST'])
@role_required('admin')
def api_admin_seller_fine():
    """Apply a fine to a seller"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        seller_id = data.get('seller_id')
        amount = data.get('amount')
        fine_type = data.get('fine_type')
        reason = data.get('reason')
        
        if not seller_id or not amount or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Update seller total fines
        cursor.execute('''
            UPDATE sellers SET total_fines = COALESCE(total_fines, 0) + %s WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE sellers SET total_fines = COALESCE(total_fines, 0) + ? WHERE id = ?
        ''', (amount, seller_id))
        
        # Insert into audit log
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, amount, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, amount, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', ('seller', seller_id, f'FINE: {fine_type}', reason, amount, admin_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Fine applied successfully'})
    except Exception as e:
        app.logger.error('admin_seller_fine error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/seller/restrict', methods=['POST'])
@role_required('admin')
def api_admin_seller_restrict():
    """Apply restrictions to a seller"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        seller_id = data.get('seller_id')
        restriction_type = data.get('restriction_type')
        details = data.get('details', '')
        reason = data.get('reason')
        
        if not seller_id or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Update seller restriction level
        cursor.execute('''
            UPDATE sellers SET restriction_level = COALESCE(restriction_level, 0) + 1 WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE sellers SET restriction_level = COALESCE(restriction_level, 0) + 1 WHERE id = ?
        ''', (seller_id,))
        
        # Insert into audit log
        full_reason = f"{restriction_type}: {details} - {reason}" if details else reason
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', ('seller', seller_id, f'RESTRICTION: {restriction_type}', full_reason, admin_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Restriction applied successfully'})
    except Exception as e:
        app.logger.error('admin_seller_restrict error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/seller/ban', methods=['POST'])
@role_required('admin')
def api_admin_seller_ban():
    """Permanently ban a seller"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        seller_id = data.get('seller_id')
        reason = data.get('reason')
        
        if not seller_id or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Update seller status to banned
        cursor.execute('''
            UPDATE sellers SET shop_status = 'banned' WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE sellers SET shop_status = 'banned' WHERE id = ?
        ''', (seller_id,))
        
        # Get user_id for the seller
        cursor.execute('SELECT user_id FROM sellers WHERE id = %s' if DB_ENGINE == 'mysql' else 'SELECT user_id FROM sellers WHERE id = ?', (seller_id,))
        result = cursor.fetchone()
        if result:
            user_id = result[0] if isinstance(result, tuple) else result.get('user_id')
            # Also update user account status
            cursor.execute('''
                UPDATE users SET is_active = 0 WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                UPDATE users SET is_active = 0 WHERE id = ?
            ''', (user_id,))
        
        # Insert into audit log
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', ('seller', seller_id, 'PERMANENT BAN', reason, admin_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Seller banned permanently'})
    except Exception as e:
        app.logger.error('admin_seller_ban error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/seller/<int:seller_id>/audit-log', methods=['GET'])
@role_required('admin')
def api_admin_seller_audit_log(seller_id):
    """Get audit log for a seller"""
    try:
        # Audit logs table may not exist - return empty list
        return jsonify({'success': True, 'audit_logs': []})
    except Exception as e:
        app.logger.error('admin_seller_audit_log error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


# ==========================================
# RIDER ACTION ENDPOINTS
# ==========================================

@app.route('/api/admin/rider/warning', methods=['POST'])
@role_required('admin')
def api_admin_rider_warning():
    """Issue a warning to a rider"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        rider_id = data.get('rider_id')
        warning_type = data.get('warning_type')
        message = data.get('message')
        
        if not rider_id or not message:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Insert into audit log
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', ('rider', rider_id, f'WARNING: {warning_type}', message, admin_id))
        
        # Update rider warning count
        cursor.execute('''
            UPDATE riders SET warning_count = COALESCE(warning_count, 0) + 1 WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE riders SET warning_count = COALESCE(warning_count, 0) + 1 WHERE id = ?
        ''', (rider_id,))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Warning issued successfully'})
    except Exception as e:
        app.logger.error('admin_rider_warning error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/rider/suspend', methods=['POST'])
@role_required('admin')
def api_admin_rider_suspend():
    """Suspend a rider account"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        rider_id = data.get('rider_id')
        duration_days = data.get('duration_days')
        reason = data.get('reason')
        
        if not rider_id or not duration_days or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Calculate suspension end date
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE riders 
                SET rider_status = 'suspended', suspended_until = DATE_ADD(NOW(), INTERVAL %s DAY)
                WHERE id = %s
            ''', (duration_days, rider_id))
        else:
            cursor.execute('''
                UPDATE riders 
                SET rider_status = 'suspended', suspended_until = datetime('now', '+' || ? || ' days')
                WHERE id = ?
            ''', (duration_days, rider_id))
        
        # Insert into audit log
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, duration_days, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, duration_days, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', ('rider', rider_id, 'SUSPENSION', reason, duration_days, admin_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Rider suspended successfully'})
    except Exception as e:
        app.logger.error('admin_rider_suspend error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/rider/cooldown', methods=['POST'])
@role_required('admin')
def api_admin_rider_cooldown():
    """Apply cooldown to a rider"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        rider_id = data.get('rider_id')
        duration_hours = data.get('duration_hours')
        reason = data.get('reason')
        
        if not rider_id or not duration_hours or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Calculate cooldown end time
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE riders 
                SET cooldown_until = DATE_ADD(NOW(), INTERVAL %s HOUR)
                WHERE id = %s
            ''', (duration_hours, rider_id))
        else:
            cursor.execute('''
                UPDATE riders 
                SET cooldown_until = datetime('now', '+' || ? || ' hours')
                WHERE id = ?
            ''', (duration_hours, rider_id))
        
        # Insert into audit log
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', ('rider', rider_id, f'COOLDOWN: {duration_hours}h', reason, admin_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Cooldown applied successfully'})
    except Exception as e:
        app.logger.error('admin_rider_cooldown error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/rider/deduction', methods=['POST'])
@role_required('admin')
def api_admin_rider_deduction():
    """Apply earnings deduction to a rider"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        rider_id = data.get('rider_id')
        amount = data.get('amount')
        deduction_type = data.get('deduction_type')
        reason = data.get('reason')
        
        if not rider_id or not amount or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Update rider earnings deducted
        cursor.execute('''
            UPDATE riders SET earnings_deducted = COALESCE(earnings_deducted, 0) + %s WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE riders SET earnings_deducted = COALESCE(earnings_deducted, 0) + ? WHERE id = ?
        ''', (amount, rider_id))
        
        # Insert into audit log
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, amount, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, amount, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', ('rider', rider_id, f'DEDUCTION: {deduction_type}', reason, amount, admin_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Earnings deduction applied successfully'})
    except Exception as e:
        app.logger.error('admin_rider_deduction error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/rider/ban', methods=['POST'])
@role_required('admin')
def api_admin_rider_ban():
    """Permanently ban a rider"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        rider_id = data.get('rider_id')
        reason = data.get('reason')
        
        if not rider_id or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Update rider status to banned
        cursor.execute('''
            UPDATE riders SET rider_status = 'banned' WHERE id = %s
        ''' if DB_ENGINE == 'mysql' else '''
            UPDATE riders SET rider_status = 'banned' WHERE id = ?
        ''', (rider_id,))
        
        # Get user_id for the rider
        cursor.execute('SELECT user_id FROM riders WHERE id = %s' if DB_ENGINE == 'mysql' else 'SELECT user_id FROM riders WHERE id = ?', (rider_id,))
        result = cursor.fetchone()
        if result:
            user_id = result[0] if isinstance(result, tuple) else result.get('user_id')
            # Also update user account status
            cursor.execute('''
                UPDATE users SET is_active = 0 WHERE id = %s
            ''' if DB_ENGINE == 'mysql' else '''
                UPDATE users SET is_active = 0 WHERE id = ?
            ''', (user_id,))
        
        # Insert into audit log
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''' if DB_ENGINE == 'mysql' else '''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', ('rider', rider_id, 'PERMANENT BAN', reason, admin_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Rider banned permanently'})
    except Exception as e:
        app.logger.error('admin_rider_ban error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/rider/<int:rider_id>/audit-log', methods=['GET'])
@role_required('admin')
def api_admin_rider_audit_log(rider_id):
    """Get audit log for a rider"""
    try:
        # Audit logs table may not exist - return empty list
        return jsonify({'success': True, 'audit_logs': []})
    except Exception as e:
        app.logger.error('admin_rider_audit_log error: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 500


# Seller Dashboard API
@app.route('/api/seller/dashboard', methods=['GET'])
@token_required
def api_seller_dashboard():
    """Seller views their dashboard"""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data or token_data.get('role') != 'seller':
            return jsonify({'error': 'Unauthorized'}), 403
        
        user_id = token_data.get('user_id')
        db = get_db()
        cursor = db.cursor()
        
        # Get seller info
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT * FROM sellers WHERE user_id=%s', (user_id,))
        else:
            cursor.execute('SELECT * FROM sellers WHERE user_id=?', (user_id,))
        
        seller = format_row(cursor.fetchone())
        seller_id = seller.get('id') if seller else None
        
        if not seller_id:
            cursor.close()
            return jsonify({'error': 'Seller profile not found'}), 404
        
        # Get seller's products
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT COUNT(*) FROM products WHERE seller_id=%s', (seller_id,))
        else:
            cursor.execute('SELECT COUNT(*) FROM products WHERE seller_id=?', (seller_id,))
        
        total_products = cursor.fetchone()[0]
        
        # Get seller's total sales
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT COUNT(*) as total_orders, COALESCE(SUM(o.total), 0) as total_revenue
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE p.seller_id=%s AND o.status=%s
            ''', (seller_id, 'delivered'))
        else:
            cursor.execute('''
                SELECT COUNT(*) as total_orders, COALESCE(SUM(o.total), 0) as total_revenue
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE p.seller_id=? AND o.status=?
            ''', (seller_id, 'delivered'))
        
        row = cursor.fetchone()
        total_orders = row[0] if row else 0
        total_revenue = float(row[1] if row else 0)
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'dashboard': {
                'seller_info': seller,
                'total_products': total_products,
                'total_orders': total_orders,
                'total_revenue': round(total_revenue, 2)
            }
        })
    except Exception as e:
        app.logger.error('seller_dashboard error: %s', e)
        return jsonify({'error': 'server_error'}), 500


@app.route('/api/seller/products', methods=['GET'])
@token_required
def api_seller_products():
    """Get seller's products"""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data or token_data.get('role') != 'seller':
            return jsonify({'error': 'Unauthorized'}), 403
        
        user_id = token_data.get('user_id')
        db = get_db()
        cursor = db.cursor()
        
        # Get seller_id
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id FROM sellers WHERE user_id=%s', (user_id,))
        else:
            cursor.execute('SELECT id FROM sellers WHERE user_id=?', (user_id,))
        
        seller_row = cursor.fetchone()
        if not seller_row:
            cursor.close()
            return jsonify({'error': 'Seller profile not found'}), 404
        
        seller_id = seller_row[0]
        
        # Get products
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT * FROM products WHERE seller_id=%s ORDER BY created_at DESC', (seller_id,))
        else:
            cursor.execute('SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC', (seller_id,))
        
        products = [format_row(row) for row in cursor.fetchall()]
        cursor.close()
        
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        app.logger.error('seller_products error: %s', e)
        return jsonify({'error': 'server_error'}), 500


# Rider Dashboard API
@app.route('/api/rider/dashboard', methods=['GET'])
@token_required
def api_rider_dashboard():
    """Rider views their dashboard"""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data or token_data.get('role') != 'rider':
            return jsonify({'error': 'Unauthorized'}), 403
        
        user_id = token_data.get('user_id')
        db = get_db()
        cursor = db.cursor()
        
        # Check if riders table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'riders'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='riders'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return jsonify({
                    'success': True,
                    'dashboard': {
                        'rider_info': {},
                        'completed_deliveries': 0,
                        'active_deliveries': 0,
                        'total_earnings': 0
                    }
                })
        except Exception as check_err:
            app.logger.warning(f'Could not check for riders table: {check_err}')
        
        # Get rider info
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT r.*, u.avatar_url as user_avatar_url FROM riders r LEFT JOIN users u ON r.user_id = u.id WHERE r.user_id=%s', (user_id,))
            else:
                cursor.execute('SELECT r.*, u.avatar_url as user_avatar_url FROM riders r LEFT JOIN users u ON r.user_id = u.id WHERE r.user_id=?', (user_id,))
            
            rider_row = cursor.fetchone()
            rider = format_row(rider_row) if rider_row else {}
            # Always use user avatar_url (it's the source of truth), fall back to rider avatar_url if user doesn't have one
            if rider:
                user_avatar = rider.get('user_avatar_url')
                rider_avatar = rider.get('avatar_url')
                app.logger.debug(f'Rider dashboard - user_avatar_url: {user_avatar}, rider_avatar_url: {rider_avatar}')
                # Prefer user_avatar_url, but use rider_avatar_url as fallback
                rider['avatar_url'] = user_avatar if user_avatar else rider_avatar
                app.logger.debug(f'Rider dashboard - Final avatar_url: {rider.get("avatar_url")}')
            rider_id = rider.get('id') if rider else None
            
            if not rider_id:
                cursor.close()
                return jsonify({
                    'success': True,
                    'dashboard': {
                        'rider_info': {},
                        'completed_deliveries': 0,
                        'active_deliveries': 0,
                        'total_earnings': 0
                    }
                })
        except Exception as rider_err:
            app.logger.warning(f'Error fetching rider info: {rider_err}')
            cursor.close()
            return jsonify({
                'success': True,
                'dashboard': {
                    'rider_info': {},
                    'completed_deliveries': 0,
                    'active_deliveries': 0,
                    'total_earnings': 0
                }
            })
        
        # Helper function to safely get count
        def get_count(query, params):
            try:
                cursor.execute(query, params)
                result = cursor.fetchone()
                if isinstance(result, (list, tuple)):
                    return int(result[0] or 0)
                elif isinstance(result, dict):
                    return int(result.get('COUNT(*)', result.get(list(result.keys())[0], 0)) or 0)
                else:
                    return 0
            except Exception:
                return 0
        
        # Helper function to safely get sum
        def get_sum(query, params):
            try:
                cursor.execute(query, params)
                result = cursor.fetchone()
                if isinstance(result, (list, tuple)):
                    return float(result[0] or 0)
                elif isinstance(result, dict):
                    return float(result.get('COALESCE(SUM(delivery_fee), 0)', result.get(list(result.keys())[0], 0)) or 0)
                else:
                    return 0.0
            except Exception:
                return 0.0
        
        # Get completed deliveries (all time)
        if DB_ENGINE == 'mysql':
            completed_deliveries = get_count('''
                SELECT COUNT(*) FROM orders 
                WHERE rider_id=%s AND status IN (%s, %s)
            ''', (rider_id, 'delivered', 'completed'))
        else:
            completed_deliveries = get_count('''
                SELECT COUNT(*) FROM orders 
                WHERE rider_id=? AND status IN (?, ?)
            ''', (rider_id, 'delivered', 'completed'))
        
        # Get completed deliveries today
        from datetime import datetime, date
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
        
        if DB_ENGINE == 'mysql':
            completed_today = get_count('''
                SELECT COUNT(*) FROM orders 
                WHERE rider_id=%s AND status IN (%s, %s) 
                AND DATE(delivered_at) = CURDATE()
            ''', (rider_id, 'delivered', 'completed'))
        else:
            completed_today = get_count('''
                SELECT COUNT(*) FROM orders 
                WHERE rider_id=? AND status IN (?, ?) 
                AND DATE(delivered_at) = DATE('now')
            ''', (rider_id, 'delivered', 'completed'))
        
        # Get active deliveries
        if DB_ENGINE == 'mysql':
            active_deliveries = get_count('''
                SELECT COUNT(*) FROM orders 
                WHERE rider_id=%s AND status IN (%s, %s)
            ''', (rider_id, 'dispatched', 'in-transit'))
        else:
            active_deliveries = get_count('''
                SELECT COUNT(*) FROM orders 
                WHERE rider_id=? AND status IN (?, ?)
            ''', (rider_id, 'dispatched', 'in-transit'))
        
        # Get total earnings (all time)
        if DB_ENGINE == 'mysql':
            total_earnings = get_sum('''
                SELECT COALESCE(SUM(delivery_fee), 0) FROM orders
                WHERE rider_id=%s AND status IN (%s, %s)
            ''', (rider_id, 'delivered', 'completed'))
        else:
            total_earnings = get_sum('''
                SELECT COALESCE(SUM(delivery_fee), 0) FROM orders
                WHERE rider_id=? AND status IN (?, ?)
            ''', (rider_id, 'delivered', 'completed'))
        
        # Get earnings today
        if DB_ENGINE == 'mysql':
            earnings_today = get_sum('''
                SELECT COALESCE(SUM(delivery_fee), 0) FROM orders
                WHERE rider_id=%s AND status IN (%s, %s) 
                AND DATE(delivered_at) = CURDATE()
            ''', (rider_id, 'delivered', 'completed'))
        else:
            earnings_today = get_sum('''
                SELECT COALESCE(SUM(delivery_fee), 0) FROM orders
                WHERE rider_id=? AND status IN (?, ?) 
                AND DATE(delivered_at) = DATE('now')
            ''', (rider_id, 'delivered', 'completed'))
        
        # Get average rating (check if rider_reviews table exists, otherwise default to 0)
        average_rating = 0.0
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'rider_reviews'")
                has_rider_reviews = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rider_reviews'")
                has_rider_reviews = cursor.fetchone() is not None
            
            if has_rider_reviews:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        SELECT COALESCE(AVG(rating), 0) FROM rider_reviews
                        WHERE rider_id=%s
                    ''', (rider_id,))
                else:
                    cursor.execute('''
                        SELECT COALESCE(AVG(rating), 0) FROM rider_reviews
                        WHERE rider_id=?
                    ''', (rider_id,))
                rating_result = cursor.fetchone()
                if rating_result:
                    average_rating = float(rating_result[0] if isinstance(rating_result, tuple) else rating_result.get('COALESCE(AVG(rating), 0)', 0) or 0)
        except Exception as rating_err:
            app.logger.debug(f'Could not fetch rider rating: {rating_err}')
            average_rating = 0.0
        
        # Get next delivery (first active delivery)
        next_delivery = None
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT id, customer_name, customer_address, status, created_at
                    FROM orders
                    WHERE rider_id=%s AND status IN (%s, %s, %s)
                    ORDER BY created_at ASC
                    LIMIT 1
                ''', (rider_id, 'dispatched', 'in-transit', 'ready'))
            else:
                cursor.execute('''
                    SELECT id, customer_name, customer_address, status, created_at
                    FROM orders
                    WHERE rider_id=? AND status IN (?, ?, ?)
                    ORDER BY created_at ASC
                    LIMIT 1
                ''', (rider_id, 'dispatched', 'in-transit', 'ready'))
            
            next_delivery_row = cursor.fetchone()
            if next_delivery_row:
                next_delivery = format_row(next_delivery_row)
        except Exception as next_err:
            app.logger.debug(f'Could not fetch next delivery: {next_err}')
        
        # Get rider service fee rate from platform settings
        rider_service_fee_rate = get_rider_service_fee_rate()
        rider_service_fee_percentage = rider_service_fee_rate * 100
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'dashboard': {
                'rider_info': rider,
                'completed_deliveries': completed_deliveries,
                'completed_today': completed_today,
                'active_deliveries': active_deliveries,
                'total_earnings': round(total_earnings, 2),
                'earnings_today': round(earnings_today, 2),
                'average_rating': round(average_rating, 1),
                'next_delivery': next_delivery,
                'rider_service_fee_rate': rider_service_fee_rate,
                'rider_service_fee_percentage': round(rider_service_fee_percentage, 2)
            }
        })
    except Exception as e:
        app.logger.error('rider_dashboard error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': True,
            'dashboard': {
                'rider_info': {},
                'completed_deliveries': 0,
                'active_deliveries': 0,
                'total_earnings': 0
            }
        })


@app.route('/api/rider/orders', methods=['GET'])
@token_required
def api_rider_orders():
    """Get rider's delivery orders"""
    try:
        token_data = verify_token(get_token_from_request())
        if not token_data or token_data.get('role') != 'rider':
            return jsonify({'error': 'Unauthorized'}), 403
        
        user_id = token_data.get('user_id')
        db = get_db()
        cursor = db.cursor()
        
        # Check if riders table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'riders'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='riders'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return jsonify({'success': True, 'orders': []})
        except Exception as check_err:
            app.logger.warning(f'Could not check for riders table: {check_err}')
        
        # Get rider_id
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT id FROM riders WHERE user_id=%s', (user_id,))
            else:
                cursor.execute('SELECT id FROM riders WHERE user_id=?', (user_id,))
            
            rider_row = cursor.fetchone()
            if not rider_row:
                cursor.close()
                return jsonify({'success': True, 'orders': []})
            
            # Handle both dict and tuple row formats
            if isinstance(rider_row, dict):
                rider_id = rider_row.get('id')
            elif isinstance(rider_row, (list, tuple)):
                rider_id = rider_row[0]
            else:
                rider_id = None
            
            if not rider_id:
                cursor.close()
                return jsonify({'success': True, 'orders': []})
        except Exception as rider_err:
            app.logger.warning(f'Error fetching rider ID: {rider_err}')
            cursor.close()
            return jsonify({'success': True, 'orders': []})
        
        # Get orders
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT id, customer_name, customer_phone, customer_address, 
                           subtotal, delivery_fee, total, payment, status, created_at
                    FROM orders
                    WHERE rider_id=%s
                    ORDER BY created_at DESC
                ''', (rider_id,))
            else:
                cursor.execute('''
                    SELECT id, customer_name, customer_phone, customer_address, 
                           subtotal, delivery_fee, total, payment, status, created_at
                    FROM orders
                    WHERE rider_id=?
                    ORDER BY created_at DESC
                ''', (rider_id,))
            
            orders_rows = cursor.fetchall() or []
            orders = [format_row(row) for row in orders_rows]
        except Exception as orders_err:
            app.logger.warning(f'Error fetching orders: {orders_err}')
            orders = []
        finally:
            cursor.close()
        
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        app.logger.error('rider_orders error: %s', e)
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'success': True, 'orders': []})


# Duplicate route removed - using the more complete version at line 5065

@app.route('/api/admin/users', methods=['GET'])
@role_required('admin')
def api_admin_list_users():
    """Admin views all users"""
    try:
        db = get_db()
        cursor = db.cursor()
        role_filter = request.args.get('role')
        
        if role_filter:
            cursor.execute('SELECT * FROM users WHERE role=? ORDER BY created_at DESC', (role_filter,))
        else:
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        
        users = cursor.fetchall()
        result = format_rows(users)
        
        return success_response(result, 'Users fetched')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/sellers/<int:seller_id>/verify', methods=['PUT'])
@role_required('admin')
def api_admin_verify_seller(seller_id):
    """Admin verifies a seller and activates their shop"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get seller info before update
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT user_id, business_name FROM sellers WHERE id=%s', (seller_id,))
        else:
            cursor.execute('SELECT user_id, business_name FROM sellers WHERE id=?', (seller_id,))
        seller = cursor.fetchone()
        
        if not seller:
            return error_response('Seller not found', 404)
        
        # Update seller: verify and activate shop
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'UPDATE sellers SET verified=1, shop_status=%s, approved_at=NOW() WHERE id=%s',
                ('active', seller_id)
            )
        else:
            cursor.execute(
                'UPDATE sellers SET verified=1, shop_status=?, approved_at=? WHERE id=?',
                ('active', datetime.utcnow().isoformat(), seller_id)
            )
        
        db.commit()
        
        # Get user email for notification
        user_id = seller['user_id'] if isinstance(seller, dict) else seller[0]
        business_name = seller['business_name'] if isinstance(seller, dict) else seller[1]
        
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT email, first_name FROM users WHERE id=%s', (user_id,))
        else:
            cursor.execute('SELECT email, first_name FROM users WHERE id=?', (user_id,))
        user = cursor.fetchone()
        
        # Send approval notification email
        if user:
            try:
                from backend.email_service import send_email
                email = user['email'] if isinstance(user, dict) else user[0]
                first_name = user['first_name'] if isinstance(user, dict) else user[1]
                
                subject = "🎉 Your Seller Account Has Been Approved!"
                body = f"""Dear {first_name},

Congratulations! Your seller account for "{business_name}" has been approved by our admin team.

✅ Your shop is now ACTIVE
✅ You can start adding products immediately
✅ Your products will appear in the marketplace

Next Steps:
1. Login to your seller dashboard
2. Add your first products
3. Start receiving orders

Thank you for joining Hub E-Commerce!

Best regards,
Hub Team
"""
                send_email(email, subject, body)
            except Exception as email_error:
                print(f"Email notification failed: {email_error}")
        
        return success_response({
            'seller_id': seller_id,
            'shop_status': 'active',
            'verified': True
        }, 'Seller verified and shop activated')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/riders/pending', methods=['GET'])
@role_required('admin')
def api_admin_pending_riders():
    """Admin views riders with optional status filtering"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get status filter from query params (default to 'pending')
        status = request.args.get('status', 'pending').lower()
        
        # Handle 'all' status - show all riders
        if status == 'all':
            status_where = ''
            params = []
        else:
            status_where = 'WHERE r.rider_status = %s' if DB_ENGINE == 'mysql' else 'WHERE r.rider_status = ?'
            params = [status]
        
        # Get search query if provided
        search = request.args.get('search', '').strip()
        if search:
            connector = 'AND' if status_where else 'WHERE'
            if DB_ENGINE == 'mysql':
                status_where += f" {connector} (u.email LIKE %s OR u.first_name LIKE %s OR u.last_name LIKE %s OR r.vehicle_type LIKE %s)"
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param, search_param])
            else:
                status_where += f" {connector} (u.email LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ? OR r.vehicle_type LIKE ?)"
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param, search_param])
        
        # MySQL only - removed SQLite code
        query = f'''
            SELECT r.id, r.user_id, u.email, u.first_name, u.last_name,
                   r.vehicle_type, r.driver_license, r.plate_number, 
                   r.rider_status, r.verified, r.approved_at,
                   u.created_at
            FROM riders r
            INNER JOIN users u ON r.user_id = u.id
            {status_where}
            ORDER BY u.created_at DESC
        '''
        cursor.execute(query, params)
        
        riders = cursor.fetchall()
        result = format_rows(riders)
        
        cursor.close()
        
        # Return in format expected by frontend
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
    except Exception as e:
        app.logger.error(f'Error in api_admin_pending_riders: {e}')
        return error_response(str(e), 500)


@app.route('/api/admin/riders/<int:rider_id>/approve', methods=['POST'])
@role_required('admin')
def api_admin_rider_approve(rider_id):
    """Admin approves a rider application"""
    try:
        db = get_db()
        cur = db.cursor()
        
        # Get current user (admin)
        admin_id = g.current_user_id
        
        # Get rider info
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT r.*, u.email, u.first_name 
                FROM riders r 
                JOIN users u ON r.user_id = u.id 
                WHERE r.id = %s
            """, (rider_id,))
        else:
            cur.execute("""
                SELECT r.*, u.email, u.first_name 
                FROM riders r 
                JOIN users u ON r.user_id = u.id 
                WHERE r.id = ?
            """, (rider_id,))
        
        rider = cur.fetchone()
        if not rider:
            return jsonify({'error': 'Rider not found'}), 404
        
        rider_dict = row2dict(rider)
        
        # Update rider status to active
        if DB_ENGINE == 'mysql':
            cur.execute("""
                UPDATE riders 
                SET verified = 1, rider_status = 'active', availability = 'available', 
                    approved_at = NOW(), last_active = NOW()
                WHERE id = %s
            """, (rider_id,))
        else:
            cur.execute("""
                UPDATE riders 
                SET verified = 1, rider_status = 'active', availability = 'available', 
                    approved_at = ?, last_active = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), rider_id))
        
        # Log to audit_logs
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('rider', %s, 'approve', 'Rider application approved', %s, NOW())
                """, (rider_id, admin_id))
            else:
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('rider', ?, 'approve', 'Rider application approved', ?, ?)
                """, (rider_id, admin_id, datetime.utcnow().isoformat()))
        except Exception:
            pass  # audit_logs might not exist yet
        
        db.commit()
        
        # Send notification email
        try:
            from backend.email_service import send_email
            subject = "🎉 Your Rider Account Has Been Approved!"
            body = f"""Dear {rider_dict.get('first_name', 'Rider')},

Congratulations! Your rider account has been approved.

✅ Your account is now ACTIVE
✅ You can start accepting delivery orders
✅ Your vehicle ({rider_dict.get('vehicle_type', 'vehicle')}) is registered

Next Steps:
1. Login to your rider dashboard
2. Set your availability status
3. Start accepting delivery requests

Thank you for joining Hub E-Commerce!

Best regards,
Hub Team
"""
            send_email(rider_dict.get('email'), subject, body)
        except Exception as e:
            print(f"[WARN] Failed to send approval email: {e}")
        
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Rider approved successfully',
            'rider_id': rider_id,
            'rider_status': 'active'
        })
    except Exception as e:
        app.logger.error('Error approving rider: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/riders/<int:rider_id>/decline', methods=['POST'])
@role_required('admin')
def api_admin_rider_decline(rider_id):
    """Admin declines a rider application"""
    try:
        db = get_db()
        cur = db.cursor()
        
        body = request.json or {}
        missing_requirements = body.get('missing_requirements', [])
        reason = body.get('reason', 'Application does not meet requirements')
        
        # Get current user (admin)
        admin_id = g.current_user_id
        
        # Get rider info
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT r.*, u.email, u.first_name 
                FROM riders r 
                JOIN users u ON r.user_id = u.id 
                WHERE r.id = %s
            """, (rider_id,))
        else:
            cur.execute("""
                SELECT r.*, u.email, u.first_name 
                FROM riders r 
                JOIN users u ON r.user_id = u.id 
                WHERE r.id = ?
            """, (rider_id,))
        
        rider = cur.fetchone()
        if not rider:
            return jsonify({'error': 'Rider not found'}), 404
        
        rider_dict = row2dict(rider)
        
        # Update rider status to suspended/declined
        if DB_ENGINE == 'mysql':
            cur.execute("""
                UPDATE riders 
                SET verified = 0, rider_status = 'suspended'
                WHERE id = %s
            """, (rider_id,))
        else:
            cur.execute("""
                UPDATE riders 
                SET verified = 0, rider_status = 'suspended'
                WHERE id = ?
            """, (rider_id,))
        
        # Log to audit_logs
        try:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('rider', %s, 'suspend', %s, %s, NOW())
                """, (rider_id, reason, admin_id))
            else:
                cur.execute("""
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES ('rider', ?, 'suspend', ?, ?, ?)
                """, (rider_id, reason, admin_id, datetime.utcnow().isoformat()))
        except Exception:
            pass  # audit_logs might not exist yet
        
        db.commit()
        
        # Send notification email
        try:
            from backend.email_service import send_email
            subject = "Application Update - Hub E-Commerce"
            
            missing_list = '\n'.join([f"• {req}" for req in missing_requirements]) if missing_requirements else "See admin message below"
            
            body = f"""Dear {rider_dict.get('first_name', 'Rider')},

Thank you for your interest in becoming a delivery rider on Hub E-Commerce.

We have reviewed your application and need additional information or documentation.

Missing Requirements:
{missing_list}

Additional Notes:
{reason}

Please update your application with the required information and resubmit.

If you have questions, please contact our support team.

Best regards,
Hub Team
"""
            send_email(rider_dict.get('email'), subject, body)
        except Exception as e:
            print(f"[WARN] Failed to send decline email: {e}")
        
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Rider application declined',
            'rider_id': rider_id,
            'rider_status': 'suspended'
        })
    except Exception as e:
        app.logger.error('Error declining rider: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500


@app.route('/api/admin/riders/stats', methods=['GET'])
@role_required('admin')
def api_admin_rider_stats():
    """Get statistics about rider accounts (pending, active, declined counts)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN rider_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN rider_status = 'active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN rider_status = 'suspended' THEN 1 ELSE 0 END) as declined
                FROM riders
            ''')
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN rider_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN rider_status = 'active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN rider_status = 'suspended' THEN 1 ELSE 0 END) as declined
                FROM riders
            ''')
        
        stats = format_row(cursor.fetchone())
        cursor.close()
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        app.logger.error('admin_rider_stats error: %s', e)
        return jsonify({'error': 'server_error', 'message': str(e)}), 500

@app.route('/api/admin/riders/<int:rider_id>/verify', methods=['PUT'])
@role_required('admin')
def api_admin_verify_rider(rider_id):
    """Admin verifies a rider and activates their account"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get rider info before update
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT user_id, vehicle_type FROM riders WHERE id=%s', (rider_id,))
        else:
            cursor.execute('SELECT user_id, vehicle_type FROM riders WHERE id=?', (rider_id,))
        rider = cursor.fetchone()
        
        if not rider:
            return error_response('Rider not found', 404)
        
        # Update rider: verify and activate
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'UPDATE riders SET verified=1, rider_status=%s, availability=%s, approved_at=NOW(), last_active=NOW() WHERE id=%s',
                ('active', 'available', rider_id)
            )
        else:
            cursor.execute(
                'UPDATE riders SET verified=1, rider_status=?, availability=?, approved_at=?, last_active=? WHERE id=?',
                ('active', 'available', datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), rider_id)
            )
        
        db.commit()
        
        # Get user email for notification
        user_id = rider['user_id'] if isinstance(rider, dict) else rider[0]
        vehicle_type = rider['vehicle_type'] if isinstance(rider, dict) else rider[1]
        
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT email, first_name FROM users WHERE id=%s', (user_id,))
        else:
            cursor.execute('SELECT email, first_name FROM users WHERE id=?', (user_id,))
        user = cursor.fetchone()
        
        # Send approval notification email
        if user:
            try:
                from backend.email_service import send_email
                email = user['email'] if isinstance(user, dict) else user[0]
                first_name = user['first_name'] if isinstance(user, dict) else user[1]
                
                subject = "🎉 Your Rider Account Has Been Approved!"
                body = f"""Dear {first_name},

Congratulations! Your rider account has been approved by our admin team.

✅ Your account is now ACTIVE
✅ You can start accepting delivery orders immediately
✅ You are marked as AVAILABLE in the system
✅ Vehicle: {vehicle_type}

Next Steps:
1. Login to your rider dashboard
2. Update your availability status
3. Start accepting delivery orders
4. Update your location for better order matching

Thank you for joining Hub E-Commerce as a delivery partner!

Best regards,
Hub Team
"""
                send_email(email, subject, body)
            except Exception as email_error:
                print(f"Email notification failed: {email_error}")
        
        return success_response({
            'rider_id': rider_id,
            'rider_status': 'active',
            'availability': 'available',
            'verified': True
        }, 'Rider verified and activated')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/riders/<int:rider_id>/status', methods=['PUT'])
@role_required('admin')
def api_admin_update_rider_status(rider_id):
    """
    Update rider account status.
    Request body:
        - status: 'active', 'declined', 'warning', 'suspended', or 'banned' - required
        - reason: reason for status change (required for declined, suspended, banned, warning)
        - duration_days: suspension duration in days (optional, for suspended status)
    """
    try:
        data = request.get_json()
        new_status = data.get('status', '').lower()
        reason = data.get('reason', '').strip()
        duration_days = data.get('duration_days')
        
        # Validation
        valid_statuses = ['active', 'declined', 'warning', 'suspended', 'banned']
        if new_status not in valid_statuses:
            return jsonify({'error': 'invalid_status', 'message': f'Status must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Require reason for status changes that need explanation
        if new_status in ['declined', 'suspended', 'banned', 'warning'] and not reason:
            return jsonify({'error': 'reason_required', 'message': f'Reason is required when setting status to "{new_status}"'}), 400
        
        # Get admin user ID from token
        admin_id = g.user_id
        
        db = get_db()
        cursor = db.cursor()
        
        # Get current rider status - use rider_status column, join with users for name
        try:
            cursor.execute('''
                SELECT r.rider_status, r.user_id, u.first_name, u.last_name 
                FROM riders r 
                INNER JOIN users u ON r.user_id = u.id 
                WHERE r.id = %s
            ''', (rider_id,))
            
            rider_row = cursor.fetchone()
            if not rider_row:
                cursor.close()
                return jsonify({'error': 'not_found', 'message': 'Rider not found'}), 404
            
            rider = format_row(rider_row)
            previous_status = rider.get('rider_status') or 'pending'
            rider_user_id = rider.get('user_id')
            rider_name = f"{rider.get('first_name', '')} {rider.get('last_name', '')}".strip() or 'Unknown'
        except Exception as fetch_error:
            app.logger.error(f'Error fetching rider data: {fetch_error}')
            cursor.close()
            return jsonify({'error': 'server_error', 'message': f'Failed to fetch rider data: {str(fetch_error)}'}), 500
        
        # Map status to rider_status values
        status_mapping = {
            'active': 'active',
            'declined': 'declined',
            'warning': 'warning',
            'suspended': 'suspended',
            'banned': 'banned'
        }
        rider_status_value = status_mapping.get(new_status, new_status)
        
        # Update rider status based on new status (MySQL only)
        if new_status == 'active':
            try:
                cursor.execute('''
                    UPDATE riders 
                    SET rider_status = %s, verified = 1, reviewed_by = %s, 
                        reviewed_at = NOW(), rejection_reason = NULL, 
                        availability = 'available', approved_at = NOW(), suspended_until = NULL
                    WHERE id = %s
                ''', (rider_status_value, admin_id, rider_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in active update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE riders 
                        SET rider_status = %s, verified = 1, availability = 'available'
                        WHERE id = %s
                    ''', (rider_status_value, rider_id))
                except Exception as col_error2:
                    app.logger.error(f'All active update attempts failed: {col_error2}')
                    raise
        elif new_status == 'suspended':
            # Handle suspension with optional duration
            try:
                if duration_days:
                    cursor.execute('''
                        UPDATE riders 
                        SET rider_status = %s, verified = 0, reviewed_by = %s, 
                            reviewed_at = NOW(), rejection_reason = %s,
                            availability = 'offline', suspended_until = DATE_ADD(NOW(), INTERVAL %s DAY)
                        WHERE id = %s
                    ''', (rider_status_value, admin_id, reason, duration_days, rider_id))
                else:
                    cursor.execute('''
                        UPDATE riders 
                        SET rider_status = %s, verified = 0, reviewed_by = %s, 
                            reviewed_at = NOW(), rejection_reason = %s, availability = 'offline'
                        WHERE id = %s
                    ''', (rider_status_value, admin_id, reason, rider_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in suspended update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE riders 
                        SET rider_status = %s, verified = 0, availability = 'offline'
                        WHERE id = %s
                    ''', (rider_status_value, rider_id))
                except Exception as col_error2:
                    app.logger.error(f'All suspended update attempts failed: {col_error2}')
                    raise
        elif new_status == 'banned':
            # Update rider status to banned
            try:
                cursor.execute('''
                    UPDATE riders 
                    SET rider_status = %s, verified = 0, reviewed_by = %s, 
                        reviewed_at = NOW(), rejection_reason = %s, 
                        availability = 'offline', suspended_until = NULL
                    WHERE id = %s
                ''', (rider_status_value, admin_id, reason, rider_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in banned update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE riders 
                        SET rider_status = %s, verified = 0, availability = 'offline'
                        WHERE id = %s
                    ''', (rider_status_value, rider_id))
                except Exception as col_error2:
                    app.logger.error(f'All banned update attempts failed: {col_error2}')
                    raise
            
            # Also deactivate the user account
            if rider_user_id:
                try:
                    cursor.execute('UPDATE users SET is_active = 0 WHERE id = %s', (rider_user_id,))
                    app.logger.info(f'Deactivated user account {rider_user_id} for banned rider {rider_id}')
                except Exception as user_update_error:
                    app.logger.warning(f'Failed to update user is_active status: {user_update_error}')
        elif new_status == 'warning':
            # Warning updates status but doesn't block account access
            try:
                cursor.execute('''
                    UPDATE riders 
                    SET rider_status = %s, reviewed_by = %s, reviewed_at = NOW(), rejection_reason = %s
                    WHERE id = %s
                ''', (rider_status_value, admin_id, reason, rider_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in warning update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE riders 
                        SET rider_status = %s
                        WHERE id = %s
                    ''', (rider_status_value, rider_id))
                except Exception as col_error2:
                    app.logger.error(f'All warning update attempts failed: {col_error2}')
                    raise
        else:  # declined
            try:
                cursor.execute('''
                    UPDATE riders 
                    SET rider_status = %s, verified = 0, reviewed_by = %s, 
                        reviewed_at = NOW(), rejection_reason = %s, availability = 'offline'
                    WHERE id = %s
                ''', (rider_status_value, admin_id, reason, rider_id))
            except Exception as col_error:
                app.logger.warning(f'Column error in declined update: {col_error}')
                # Fallback to minimal update
                try:
                    cursor.execute('''
                        UPDATE riders 
                        SET rider_status = %s, verified = 0, availability = 'offline'
                        WHERE id = %s
                    ''', (rider_status_value, rider_id))
                except Exception as col_error2:
                    app.logger.error(f'All declined update attempts failed: {col_error2}')
                    raise
        # Map status to action name for audit log
        action_map = {
            'active': 'APPROVED',
            'declined': 'DECLINED',
            'warning': 'WARNING',
            'suspended': 'SUSPENSION',
            'banned': 'BAN'
        }
        action = action_map.get(new_status, new_status.upper())
        
        # Log the action in audit log (optional - don't fail if table doesn't exist)
        try:
            cursor.execute('''
                INSERT INTO rider_audit_log (rider_id, admin_id, action, previous_status, new_status, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ''', (rider_id, admin_id, action, previous_status, rider_status_value, reason))
        except Exception as audit_error:
            # Try alternative audit log table name or structure
            app.logger.warning('Failed to log to rider_audit_log (table may not exist): %s', audit_error)
            try:
                # Use the correct column names for audit_logs table
                cursor.execute('''
                    INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                ''', ('rider', rider_id, action.lower(), reason, admin_id))
            except Exception as audit_error2:
                # Both audit log attempts failed - that's okay, just log it
                app.logger.warning('Failed to log to audit_logs fallback (table may not exist): %s', audit_error2)
        
        # Commit the transaction
        try:
            db.commit()
            app.logger.info(f'Rider {rider_id} status updated from "{previous_status}" to "{rider_status_value}" by admin {admin_id}')
        except Exception as commit_error:
            app.logger.error('Failed to commit status update: %s', commit_error)
            cursor.close()
            db.rollback()
            return jsonify({'error': 'commit_failed', 'message': 'Failed to save status update'}), 500
        
        # Verify the status was actually saved by querying it back
        try:
            verify_cursor = db.cursor()
            verify_cursor.execute('SELECT rider_status FROM riders WHERE id = %s', (rider_id,))
            verify_result = verify_cursor.fetchone()
            verify_cursor.close()
            
            if verify_result:
                actual_status = format_row(verify_result).get('rider_status')
                app.logger.info(f'Verified rider {rider_id} status in DB: {actual_status} (expected: {rider_status_value})')
                if actual_status != rider_status_value:
                    app.logger.error(f'Status mismatch! Expected {rider_status_value} but got {actual_status}')
            else:
                app.logger.warning(f'Could not find rider {rider_id} for verification')
        except Exception as verify_error:
            app.logger.warning(f'Could not verify status update: {verify_error}')
        
        # Close the main cursor
        cursor.close()
        
        # Send notification to rider
        try:
            notification_titles = {
                'active': '🎉 Rider Account Approved!',
                'declined': '❌ Rider Account Declined',
                'warning': '⚠️ Warning Issued',
                'suspended': '⏸️ Account Suspended',
                'banned': '🔨 Account Banned'
            }
            notification_bodies = {
                'active': f'Congratulations! Your rider account has been approved. You can now start accepting delivery orders.',
                'declined': f'Your rider account application has been declined. Reason: {reason}',
                'warning': f'A warning has been issued for your rider account. Reason: {reason}',
                'suspended': f'Your rider account has been suspended. Reason: {reason}' + (f' Duration: {duration_days} days' if duration_days else ''),
                'banned': f'Your rider account has been permanently banned. Reason: {reason}'
            }
            
            notification_title = notification_titles.get(new_status, 'Account Status Updated')
            notification_body = notification_bodies.get(new_status, f'Your rider account status has been updated to: {new_status}')
            
            # Get a new cursor for the notification (main cursor was closed after commit)
            notif_cursor = db.cursor()
            notif_cursor.execute('''
                INSERT INTO notifications (user_id, title, body, `read`, created_at)
                VALUES (%s, %s, %s, 0, NOW())
            ''', (rider_user_id, notification_title, notification_body))
            
            # Commit the notification separately (it's optional)
            db.commit()
            notif_cursor.close()
        except Exception as notif_error:
            # Notification is optional - just log warning and continue
            app.logger.warning('Failed to send notification (table may not exist): %s', notif_error)
            # Don't rollback - the main update was already committed
        
        return jsonify({
            'success': True, 
            'message': f'Rider status updated to "{new_status}" successfully',
            'rider_id': rider_id,
            'new_status': rider_status_value,
            'previous_status': previous_status
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error('admin_update_rider_status error: %s', e)
        app.logger.error('Full traceback: %s', error_trace)
        return jsonify({
            'error': 'server_error', 
            'message': str(e),
            'details': error_trace if app.debug else 'Check server logs for details'
        }), 500

@app.route('/api/admin/verify-test-accounts', methods=['GET'])
@role_required('admin')
def api_admin_verify_test_accounts():
    """Verify if test accounts exist in the database"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        test_emails = [
            'test-seller-1@test.com', 'test-seller-2@test.com', 'test-seller-3@test.com',
            'test-rider-1@test.com', 'test-rider-2@test.com', 'test-rider-3@test.com'
        ]
        
        found_accounts = {'sellers': [], 'riders': []}
        
        for email in test_emails:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT u.id as user_id, u.email, u.first_name, u.last_name, u.role,
                           s.id as seller_id, s.business_name, s.shop_status,
                           r.id as rider_id, r.vehicle_type, r.rider_status
                    FROM users u
                    LEFT JOIN sellers s ON s.user_id = u.id
                    LEFT JOIN riders r ON r.user_id = u.id
                    WHERE u.email = %s
                ''', (email,))
            else:
                cursor.execute('''
                    SELECT u.id as user_id, u.email, u.first_name, u.last_name, u.role,
                           s.id as seller_id, s.business_name, s.shop_status,
                           r.id as rider_id, r.vehicle_type, r.rider_status
                    FROM users u
                    LEFT JOIN sellers s ON s.user_id = u.id
                    LEFT JOIN riders r ON r.user_id = u.id
                    WHERE u.email = ?
                ''', (email,))
            
            row = cursor.fetchone()
            if row:
                account = format_row(row)
                if account.get('seller_id'):
                    found_accounts['sellers'].append(account)
                if account.get('rider_id'):
                    found_accounts['riders'].append(account)
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'found': {
                'sellers_count': len(found_accounts['sellers']),
                'riders_count': len(found_accounts['riders']),
                'accounts': found_accounts
            }
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': 'server_error',
            'message': str(e),
            'details': traceback.format_exc() if app.debug else 'Check server logs'
        }), 500

@app.route('/api/admin/create-test-accounts', methods=['POST'])
@role_required('admin')
def api_admin_create_test_accounts():
    """Create dummy test accounts for sellers and riders"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        from werkzeug.security import generate_password_hash
        from datetime import datetime
        
        created_accounts = {
            'sellers': [],
            'riders': []
        }
        
        # Delete existing test accounts first to ensure fresh creation
        test_emails = [
            'test-seller-1@test.com', 'test-seller-2@test.com', 'test-seller-3@test.com',
            'test-rider-1@test.com', 'test-rider-2@test.com', 'test-rider-3@test.com'
        ]
        
        for email in test_emails:
            if DB_ENGINE == 'mysql':
                # Get user_id first
                cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
                user_row = cursor.fetchone()
                if user_row:
                    try:
                        # Handle both tuple and dict formats
                        if isinstance(user_row, tuple):
                            user_id = user_row[0]
                        elif isinstance(user_row, dict):
                            user_id = user_row.get('id')
                        else:
                            user_id = user_row[0] if hasattr(user_row, '__getitem__') else None
                        
                        if user_id:
                            # Delete seller profile if exists
                            cursor.execute('DELETE FROM sellers WHERE user_id = %s', (user_id,))
                            # Delete rider profile if exists
                            cursor.execute('DELETE FROM riders WHERE user_id = %s', (user_id,))
                            # Delete user
                            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
                    except Exception as del_err:
                        app.logger.warning(f'Error deleting existing account {email}: {del_err}')
                        # Continue anyway
            else:
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user_row = cursor.fetchone()
                if user_row:
                    try:
                        user_id = user_row[0] if isinstance(user_row, tuple) else (user_row.get('id') if hasattr(user_row, 'get') else user_row['id'])
                        cursor.execute('DELETE FROM sellers WHERE user_id = ?', (user_id,))
                        cursor.execute('DELETE FROM riders WHERE user_id = ?', (user_id,))
                        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                    except Exception as del_err:
                        app.logger.warning(f'Error deleting existing account {email}: {del_err}')
                        # Continue anyway
        
        # Create 3 test seller accounts
        seller_data = [
            {'email': 'test-seller-1@test.com', 'first_name': 'Test', 'last_name': 'Seller One', 'business_name': 'Test Store One', 'category': 'Food'},
            {'email': 'test-seller-2@test.com', 'first_name': 'Test', 'last_name': 'Seller Two', 'business_name': 'Test Store Two', 'category': 'Electronics'},
            {'email': 'test-seller-3@test.com', 'first_name': 'Test', 'last_name': 'Seller Three', 'business_name': 'Test Store Three', 'category': 'Clothing'}
        ]
        
        for seller_info in seller_data:
            email = seller_info['email']
            
            # Create user account
            password_hash = generate_password_hash('test123')
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, 1, 1, %s)
                ''', (email, password_hash, seller_info['first_name'], seller_info['last_name'], 'seller', 1, 1, datetime.utcnow().isoformat()))
                user_id = cursor.lastrowid
            else:
                cursor.execute('''
                    INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, 1, ?)
                ''', (email, password_hash, seller_info['first_name'], seller_info['last_name'], 'seller', 1, 1, datetime.utcnow().isoformat()))
                user_id = cursor.lastrowid
            
            # Create seller profile
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        INSERT INTO sellers (user_id, business_name, category, verified, shop_status, created_at)
                        VALUES (%s, %s, %s, 1, 'active', NOW())
                    ''', (user_id, seller_info['business_name'], seller_info['category']))
                    seller_id = cursor.lastrowid
                else:
                    cursor.execute('''
                        INSERT INTO sellers (user_id, business_name, category, verified, shop_status, created_at)
                        VALUES (?, ?, ?, 1, 'active', datetime('now'))
                    ''', (user_id, seller_info['business_name'], seller_info['category']))
                    seller_id = cursor.lastrowid
                
                app.logger.info(f'Created seller account: {email} (user_id: {user_id}, seller_id: {seller_id})')
                
                created_accounts['sellers'].append({
                    'email': email,
                    'password': 'test123',
                    'user_id': user_id,
                    'seller_id': seller_id,
                    'business_name': seller_info['business_name']
                })
            except Exception as seller_err:
                app.logger.error(f'Failed to create seller profile for {email}: {seller_err}')
                raise
        
        # Create 3 test rider accounts
        rider_data = [
            {'email': 'test-rider-1@test.com', 'first_name': 'Test', 'last_name': 'Rider One', 'vehicle_type': 'Motorcycle', 'driver_license': 'DL001'},
            {'email': 'test-rider-2@test.com', 'first_name': 'Test', 'last_name': 'Rider Two', 'vehicle_type': 'Bicycle', 'driver_license': 'DL002'},
            {'email': 'test-rider-3@test.com', 'first_name': 'Test', 'last_name': 'Rider Three', 'vehicle_type': 'Car', 'driver_license': 'DL003'}
        ]
        
        for rider_info in rider_data:
            email = rider_info['email']
            # Create user account (we already deleted existing ones above)
            password_hash = generate_password_hash('test123')
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, 1, 1, %s)
                ''', (email, password_hash, rider_info['first_name'], rider_info['last_name'], 'rider', 1, 1, datetime.utcnow().isoformat()))
                user_id = cursor.lastrowid
            else:
                cursor.execute('''
                    INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, 1, ?)
                ''', (email, password_hash, rider_info['first_name'], rider_info['last_name'], 'rider', 1, 1, datetime.utcnow().isoformat()))
                user_id = cursor.lastrowid
            
            # Create rider profile
            try:
                if DB_ENGINE == 'mysql':
                    cursor.execute('''
                        INSERT INTO riders (user_id, vehicle_type, driver_license, verified, rider_status, availability, created_at)
                        VALUES (%s, %s, %s, 1, 'active', 'available', NOW())
                    ''', (user_id, rider_info['vehicle_type'], rider_info['driver_license']))
                    rider_id = cursor.lastrowid
                else:
                    cursor.execute('''
                        INSERT INTO riders (user_id, vehicle_type, driver_license, verified, rider_status, availability, created_at)
                        VALUES (?, ?, ?, 1, 'active', 'available', datetime('now'))
                    ''', (user_id, rider_info['vehicle_type'], rider_info['driver_license']))
                    rider_id = cursor.lastrowid
                
                app.logger.info(f'Created rider account: {email} (user_id: {user_id}, rider_id: {rider_id})')
                
                created_accounts['riders'].append({
                    'email': email,
                    'password': 'test123',
                    'user_id': user_id,
                    'rider_id': rider_id,
                    'vehicle_type': rider_info['vehicle_type']
                })
            except Exception as rider_err:
                app.logger.error(f'Failed to create rider profile for {email}: {rider_err}')
                raise
        
        # Commit the transaction
        try:
            db.commit()
            app.logger.info('Transaction committed successfully')
        except Exception as commit_err:
            app.logger.error(f'Failed to commit transaction: {commit_err}')
            import traceback
            app.logger.error(traceback.format_exc())
            db.rollback()
            cursor.close()
            raise
        
        # Verify accounts were created by querying them
        verification = {
            'sellers_created': len(created_accounts['sellers']),
            'riders_created': len(created_accounts['riders']),
            'seller_ids': [s['user_id'] for s in created_accounts['sellers']],
            'rider_ids': [r['user_id'] for r in created_accounts['riders']]
        }
        
        # Query to verify sellers exist
        try:
            if created_accounts['sellers']:
                seller_ids = [s['user_id'] for s in created_accounts['sellers']]
                if seller_ids:
                    placeholders = ','.join(['%s'] * len(seller_ids)) if DB_ENGINE == 'mysql' else ','.join(['?'] * len(seller_ids))
                    cursor.execute(f'SELECT id, user_id, business_name, shop_status FROM sellers WHERE user_id IN ({placeholders})', seller_ids)
                    verification['sellers_verified'] = [format_row(row) for row in cursor.fetchall()]
        except Exception as verify_err:
            app.logger.warning(f'Could not verify sellers: {verify_err}')
            verification['sellers_verified'] = []
        
        # Query to verify riders exist
        try:
            if created_accounts['riders']:
                rider_ids = [r['user_id'] for r in created_accounts['riders']]
                if rider_ids:
                    placeholders = ','.join(['%s'] * len(rider_ids)) if DB_ENGINE == 'mysql' else ','.join(['?'] * len(rider_ids))
                    cursor.execute(f'SELECT id, user_id, vehicle_type, rider_status FROM riders WHERE user_id IN ({placeholders})', rider_ids)
                    verification['riders_verified'] = [format_row(row) for row in cursor.fetchall()]
        except Exception as verify_err:
            app.logger.warning(f'Could not verify riders: {verify_err}')
            verification['riders_verified'] = []
        
        cursor.close()
        
        app.logger.info(f'Test accounts created: {verification}')
        
        return jsonify({
            'success': True,
            'message': f'Created {len(created_accounts["sellers"])} seller accounts and {len(created_accounts["riders"])} rider accounts',
            'accounts': created_accounts,
            'verification': verification
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error('create_test_accounts error: %s', e)
        app.logger.error('Full traceback: %s', error_trace)
        try:
            db.rollback()
        except:
            pass
        try:
            cursor.close()
        except:
            pass
        return jsonify({
            'error': 'server_error',
            'message': str(e),
            'details': error_trace if app.debug else 'Check server logs for details'
        }), 500

# New Rider Management Endpoints

@app.route('/api/riders/status', methods=['GET'])
@token_required
def api_get_rider_status(current_user):
    """Get current rider's status and eligibility"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get rider info
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT id, verified, rider_status, availability, 
                       current_location, approved_at, last_active
                FROM riders WHERE user_id=%s
            ''', (current_user['id'],))
        else:
            cursor.execute('''
                SELECT id, verified, rider_status, availability, 
                       current_location, approved_at, last_active
                FROM riders WHERE user_id=?
            ''', (current_user['id'],))
        
        rider = cursor.fetchone()
        
        if not rider:
            return error_response('Rider profile not found', 404)
        
        rider_data = rider if isinstance(rider, dict) else {
            'id': rider[0],
            'verified': rider[1],
            'rider_status': rider[2],
            'availability': rider[3],
            'current_location': rider[4],
            'approved_at': rider[5],
            'last_active': rider[6]
        }
        
        # Determine eligibility
        can_accept_orders = (
            rider_data['verified'] == 1 and 
            rider_data['rider_status'] == 'active' and
            rider_data['availability'] == 'available'
        )
        
        # Status message
        if rider_data['rider_status'] == 'pending':
            status_message = "Your account is pending admin approval"
        elif rider_data['rider_status'] == 'suspended':
            status_message = "Your account has been suspended. Contact admin for details."
        elif rider_data['rider_status'] == 'active' and rider_data['availability'] == 'offline':
            status_message = "You are offline. Change to available to accept orders."
        elif rider_data['rider_status'] == 'active' and rider_data['availability'] == 'busy':
            status_message = "You are currently busy with a delivery."
        elif can_accept_orders:
            status_message = "You are active and can accept delivery orders!"
        else:
            status_message = "Status unknown"
        
        return success_response({
            **rider_data,
            'can_accept_orders': can_accept_orders,
            'status_message': status_message
        }, 'Rider status retrieved')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/riders/availability', methods=['PUT'])
@token_required
def api_update_rider_availability(current_user):
    """Rider updates their availability status"""
    try:
        data = request.get_json()
        availability = data.get('availability')
        
        if availability not in ['available', 'busy', 'offline']:
            return error_response('Invalid availability status', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if rider is active and not suspended
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT id, rider_status, suspension_reason FROM riders WHERE user_id=%s', (current_user['id'],))
        else:
            cursor.execute('SELECT id, rider_status, suspension_reason FROM riders WHERE user_id=?', (current_user['id'],))
        
        rider = cursor.fetchone()
        if not rider:
            return error_response('Rider profile not found', 404)
        
        rider_status = rider['rider_status'] if isinstance(rider, dict) else rider[1]
        suspension_reason = rider['suspension_reason'] if isinstance(rider, dict) else (rider[2] if len(rider) > 2 else None)
        
        if rider_status == 'suspended':
            reason_msg = f' Reason: {suspension_reason}' if suspension_reason else ''
            return error_response(f'Your account is suspended. You cannot update availability.{reason_msg}', 403)
        
        if rider_status != 'active':
            return error_response(f'Cannot update availability. Your account is {rider_status}', 403)
        
        # Update availability
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'UPDATE riders SET availability=%s, last_active=NOW() WHERE user_id=%s',
                (availability, current_user['id'])
            )
        else:
            cursor.execute(
                'UPDATE riders SET availability=?, last_active=? WHERE user_id=?',
                (availability, datetime.utcnow().isoformat(), current_user['id'])
            )
        
        db.commit()
        
        return success_response({
            'availability': availability,
            'updated_at': datetime.utcnow().isoformat()
        }, 'Availability updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/riders/location', methods=['PUT'])
@token_required
def api_update_rider_location(current_user):
    """Rider updates their current location"""
    try:
        data = request.get_json()
        location = data.get('location')
        
        if not location:
            return error_response('Location is required', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Update location
        if DB_ENGINE == 'mysql':
            cursor.execute(
                'UPDATE riders SET current_location=%s, last_active=NOW() WHERE user_id=%s',
                (location, current_user['id'])
            )
        else:
            cursor.execute(
                'UPDATE riders SET current_location=?, last_active=? WHERE user_id=?',
                (location, datetime.utcnow().isoformat(), current_user['id'])
            )
        
        db.commit()
        
        return success_response({
            'location': location,
            'updated_at': datetime.utcnow().isoformat()
        }, 'Location updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/riders/<int:rider_id>/suspend', methods=['POST'])
@role_required('admin')
def api_admin_suspend_rider(rider_id, current_user):
    """Admin suspends a rider account - instant system-wide effect"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Violation of delivery standards')
        suspension_type = data.get('type', 'temporary')  # 'temporary' or 'permanent'
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider info for notification
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT r.user_id, r.vehicle_type, u.email, u.first_name
                FROM riders r
                JOIN users u ON r.user_id = u.id
                WHERE r.id=%s
            ''', (rider_id,))
        else:
            cursor.execute('''
                SELECT r.user_id, r.vehicle_type, u.email, u.first_name
                FROM riders r
                JOIN users u ON r.user_id = u.id
                WHERE r.id=?
            ''', (rider_id,))
        
        rider_info = cursor.fetchone()
        if not rider_info:
            return error_response('Rider not found', 404)
        
        # Suspend rider with detailed tracking
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE riders 
                SET rider_status=%s, 
                    availability=%s,
                    suspended_at=NOW(),
                    suspended_by=%s,
                    suspension_reason=%s,
                    suspension_type=%s
                WHERE id=%s
            ''', ('suspended', 'offline', current_user['id'], reason, suspension_type, rider_id))
        else:
            cursor.execute('''
                UPDATE riders 
                SET rider_status=?, 
                    availability=?,
                    suspended_at=?,
                    suspended_by=?,
                    suspension_reason=?,
                    suspension_type=?
                WHERE id=?
            ''', ('suspended', 'offline', datetime.utcnow().isoformat(), current_user['id'], reason, suspension_type, rider_id))
        
        db.commit()
        
        # Send suspension notification
        if rider_info:
            try:
                from backend.email_service import send_email
                rider_data = rider_info if isinstance(rider_info, dict) else {
                    'email': rider_info[2],
                    'first_name': rider_info[3],
                    'vehicle_type': rider_info[1]
                }
                
                suspension_status = 'PERMANENTLY' if suspension_type == 'permanent' else 'TEMPORARILY'
                subject = f"⚠️ Your Rider Account Has Been {suspension_status.title()} Suspended"
                body = f"""Dear {rider_data['first_name']},

Your rider account has been {suspension_status.lower()} suspended.

⛔ Suspension Details:
- Type: {suspension_status}
- Reason: {reason}
- Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

🚫 Effect of Suspension:
- You are removed from active riders list
- You cannot receive new delivery tasks
- You cannot accept orders
- You are marked as offline in the system
- All delivery permissions disabled

{'This suspension is permanent.' if suspension_type == 'permanent' else 'This is a temporary suspension. Contact support to appeal.'}

If you believe this is a mistake, please contact our support team.

Support: support@hubcommerce.com

Best regards,
Hub E-Commerce Admin Team
"""
                send_email(rider_data['email'], subject, body)
            except Exception as email_error:
                print(f"Rider suspension email failed: {email_error}")
        
        return success_response({
            'rider_id': rider_id,
            'rider_status': 'suspended',
            'suspension_type': suspension_type,
            'availability': 'offline',
            'reason': reason,
            'suspended_at': datetime.utcnow().isoformat(),
            'effect': 'Rider removed from active list and cannot receive orders'
        }, f'Rider {suspension_type}ly suspended')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/riders/<int:rider_id>/reactivate', methods=['POST'])
@role_required('admin')
def api_admin_reactivate_rider(rider_id):
    """Admin reactivates a suspended rider - instant restoration"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get rider info
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT r.user_id, u.email, u.first_name, r.rider_status
                FROM riders r
                JOIN users u ON r.user_id = u.id
                WHERE r.id=%s
            ''', (rider_id,))
        else:
            cursor.execute('''
                SELECT r.user_id, u.email, u.first_name, r.rider_status
                FROM riders r
                JOIN users u ON r.user_id = u.id
                WHERE r.id=?
            ''', (rider_id,))
        
        rider_info = cursor.fetchone()
        if not rider_info:
            return error_response('Rider not found', 404)
        
        # Clear suspension and reactivate
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE riders 
                SET rider_status=%s, 
                    availability=%s,
                    suspended_at=NULL,
                    suspended_by=NULL,
                    suspension_reason=NULL,
                    suspension_type=NULL
                WHERE id=%s
            ''', ('active', 'offline', rider_id))
        else:
            cursor.execute('''
                UPDATE riders 
                SET rider_status=?, 
                    availability=?,
                    suspended_at=NULL,
                    suspended_by=NULL,
                    suspension_reason=NULL,
                    suspension_type=NULL
                WHERE id=?
            ''', ('active', 'offline', rider_id))
        
        db.commit()
        
        # Send reactivation email
        if rider_info:
            try:
                from backend.email_service import send_email
                rider_data = rider_info if isinstance(rider_info, dict) else {
                    'email': rider_info[1],
                    'first_name': rider_info[2]
                }
                
                subject = "✅ Your Rider Account Has Been Reactivated!"
                body = f"""Dear {rider_data['first_name']},

Good news! Your rider account has been reactivated.

✅ Your account is now ACTIVE
✅ You can receive delivery tasks
✅ You can accept orders
✅ All delivery permissions restored

You are currently set to OFFLINE. Please update your availability to AVAILABLE to start receiving orders.

Please comply with our delivery standards to avoid future suspensions.

Best regards,
Hub E-Commerce Admin Team
"""
                send_email(rider_data['email'], subject, body)
            except Exception as email_error:
                print(f"Rider reactivation email failed: {email_error}")
        
        return success_response({
            'rider_id': rider_id,
            'rider_status': 'active',
            'availability': 'offline',
            'reactivated_at': datetime.utcnow().isoformat(),
            'effect': 'Rider can now receive orders after setting availability'
        }, 'Rider reactivated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/riders/available', methods=['GET'])
@role_required('admin')
def api_admin_available_riders():
    """Get list of available riders for order assignment"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT r.id, r.user_id, u.first_name, u.last_name, u.email,
                       r.vehicle_type, r.current_location, r.last_active,
                       r.rider_status, r.availability
                FROM riders r
                INNER JOIN users u ON r.user_id = u.id
                WHERE r.verified = 1 
                AND r.rider_status = 'active'
                AND r.rider_status != 'suspended'
                AND r.availability = 'available'
                ORDER BY r.last_active DESC
            ''')
        else:
            cursor.execute('''
                SELECT r.id, r.user_id, u.first_name, u.last_name, u.email,
                       r.vehicle_type, r.current_location, r.last_active,
                       r.rider_status, r.availability
                FROM riders r
                INNER JOIN users u ON r.user_id = u.id
                WHERE r.verified = 1 
                AND r.rider_status = 'active'
                AND r.rider_status != 'suspended'
                AND r.availability = 'available'
                ORDER BY r.last_active DESC
            ''')
        
        riders = cursor.fetchall()
        result = format_rows(riders)
        
        return success_response(result, f'Found {len(result)} available riders')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/riders', methods=['GET'])
@role_required('admin')
def api_admin_list_all_riders():
    """Admin gets list of all riders with status"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT r.id, r.user_id, u.first_name, u.last_name, u.email,
                       r.vehicle_type, r.driver_license, r.plate_number,
                       r.verified, r.rider_status, r.availability, 
                       r.current_location, r.approved_at, r.last_active,
                       u.created_at
                FROM riders r
                INNER JOIN users u ON r.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT r.id, r.user_id, u.first_name, u.last_name, u.email,
                       r.vehicle_type, r.driver_license, r.plate_number,
                       r.verified, r.rider_status, r.availability, 
                       r.current_location, r.approved_at, r.last_active,
                       u.created_at
                FROM riders r
                INNER JOIN users u ON r.user_id = u.id
                ORDER BY u.created_at DESC
            ''')
        
        riders = cursor.fetchall()
        result = format_rows(riders)
        
        return success_response(result, 'All riders retrieved')
    except Exception as e:
        return error_response(str(e), 500)

@app.route('/api/admin/analytics/revenue', methods=['GET'])
@role_required('admin')
def api_admin_revenue_analytics():
    """Admin views revenue analytics"""
    try:
        db = get_db()
        cursor = db.cursor()
        period = request.args.get('period', 'month')
        
        cursor.execute('''
            SELECT DATE(created_at) as date, SUM(total) as revenue, COUNT(*) as orders
            FROM orders WHERE status='delivered' AND created_at > datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        ''')
        
        data = cursor.fetchall()
        result = [{'date': d[0], 'revenue': round(d[1], 2), 'orders': d[2]} for d in data]
        
        return success_response(result, 'Revenue analytics')
    except Exception as e:
        return error_response(str(e), 500)

# ----------------------
# Customer–Seller Messaging Endpoints (SQLite-Based)
# ----------------------
from datetime import datetime

# Old route removed - now handled by messaging_api.py blueprint
# The blueprint route /api/messages/send handles the new messaging system

@app.route('/api/messages/conversation/<int:user1>/<int:user2>', methods=['GET'])
def get_conversation(user1, user2):
    db = get_db()
    messages = db.execute(
        """
        SELECT * FROM messages
        WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
        ORDER BY sent_at ASC
        """,
        (user1, user2, user2, user1)
    ).fetchall()
    return jsonify([dict(msg) for msg in messages])

@app.errorhandler(404)
def handle_404(e):
    return jsonify({'error':'not_found'}), 404


# ==================== CHAT FEATURE API ====================

@app.route('/api/chat/conversations', methods=['GET'])
@token_required
def api_get_conversations(current_user):
    """Get all conversations for the current user (customer or seller)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        user_id = current_user['id']
        user_role = current_user['role']
        
        # Get conversations based on role
        if user_role == 'customer':
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT 
                        c.id, c.customer_id, c.seller_id, c.created_at, c.updated_at,
                        u.first_name as seller_first_name, u.last_name as seller_last_name,
                        u.email as seller_email,
                        s.business_name as seller_business_name,
                        (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND sender_type = 'seller' AND is_read = 0) as unread_count,
                        (SELECT message FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message,
                        (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message_time
                    FROM conversations c
                    JOIN users u ON c.seller_id = u.id
                    LEFT JOIN sellers s ON u.id = s.user_id
                    WHERE c.customer_id = %s
                    ORDER BY c.updated_at DESC
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT 
                        c.id, c.customer_id, c.seller_id, c.created_at, c.updated_at,
                        u.first_name as seller_first_name, u.last_name as seller_last_name,
                        u.email as seller_email,
                        s.business_name as seller_business_name,
                        (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND sender_type = 'seller' AND is_read = 0) as unread_count,
                        (SELECT message FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message,
                        (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message_time
                    FROM conversations c
                    JOIN users u ON c.seller_id = u.id
                    LEFT JOIN sellers s ON u.id = s.user_id
                    WHERE c.customer_id = ?
                    ORDER BY c.updated_at DESC
                ''', (user_id,))
        
        elif user_role == 'seller':
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT 
                        c.id, c.customer_id, c.seller_id, c.created_at, c.updated_at,
                        u.first_name as customer_first_name, u.last_name as customer_last_name,
                        u.email as customer_email,
                        (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND sender_type = 'customer' AND is_read = 0) as unread_count,
                        (SELECT message FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message,
                        (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message_time
                    FROM conversations c
                    JOIN users u ON c.customer_id = u.id
                    WHERE c.seller_id = %s
                    ORDER BY c.updated_at DESC
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT 
                        c.id, c.customer_id, c.seller_id, c.created_at, c.updated_at,
                        u.first_name as customer_first_name, u.last_name as customer_last_name,
                        u.email as customer_email,
                        (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND sender_type = 'customer' AND is_read = 0) as unread_count,
                        (SELECT message FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message,
                        (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message_time
                    FROM conversations c
                    JOIN users u ON c.customer_id = u.id
                    WHERE c.seller_id = ?
                    ORDER BY c.updated_at DESC
                ''', (user_id,))
        else:
            return error_response('Only customers and sellers can access chat', 403)
        
        conversations = cursor.fetchall()
        result = format_rows(conversations)
        
        return success_response(result, f'Found {len(result)} conversations')
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/chat/conversations/<int:other_user_id>', methods=['GET'])
@token_required
def api_get_or_create_conversation(other_user_id, current_user):
    """Get or create a conversation between current user and another user"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        user_id = current_user['id']
        user_role = current_user['role']
        
        # Determine customer_id and seller_id
        if user_role == 'customer':
            customer_id = user_id
            seller_id = other_user_id
            
            # Verify other user is a seller
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT role FROM users WHERE id = %s', (other_user_id,))
            else:
                cursor.execute('SELECT role FROM users WHERE id = ?', (other_user_id,))
            other_user = cursor.fetchone()
            
            if not other_user or (other_user['role'] if isinstance(other_user, dict) else other_user[0]) != 'seller':
                return error_response('Target user must be a seller', 400)
        
        elif user_role == 'seller':
            customer_id = other_user_id
            seller_id = user_id
            
            # Verify other user is a customer
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT role FROM users WHERE id = %s', (other_user_id,))
            else:
                cursor.execute('SELECT role FROM users WHERE id = ?', (other_user_id,))
            other_user = cursor.fetchone()
            
            if not other_user or (other_user['role'] if isinstance(other_user, dict) else other_user[0]) != 'customer':
                return error_response('Target user must be a customer', 400)
        else:
            return error_response('Only customers and sellers can use chat', 403)
        
        # Check if conversation exists
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT id, customer_id, seller_id, created_at, updated_at
                FROM conversations
                WHERE customer_id = %s AND seller_id = %s
            ''', (customer_id, seller_id))
        else:
            cursor.execute('''
                SELECT id, customer_id, seller_id, created_at, updated_at
                FROM conversations
                WHERE customer_id = ? AND seller_id = ?
            ''', (customer_id, seller_id))
        
        conversation = cursor.fetchone()
        
        if conversation:
            conv_data = conversation if isinstance(conversation, dict) else {
                'id': conversation[0],
                'customer_id': conversation[1],
                'seller_id': conversation[2],
                'created_at': conversation[3],
                'updated_at': conversation[4]
            }
            return success_response(conv_data, 'Conversation found')
        else:
            # Create new conversation
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    INSERT INTO conversations (customer_id, seller_id, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                ''', (customer_id, seller_id))
            else:
                cursor.execute('''
                    INSERT INTO conversations (customer_id, seller_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (customer_id, seller_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            
            db.commit()
            conversation_id = cursor.lastrowid
            
            return success_response({
                'id': conversation_id,
                'customer_id': customer_id,
                'seller_id': seller_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }, 'New conversation created')
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/chat/conversations/<int:conversation_id>/messages', methods=['GET'])
@token_required
def api_get_messages(conversation_id, current_user):
    """Get all messages in a conversation and mark opposite sender's messages as read"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        user_id = current_user['id']
        user_role = current_user['role']
        
        # Verify user is part of the conversation
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT customer_id, seller_id
                FROM conversations
                WHERE id = %s
            ''', (conversation_id,))
        else:
            cursor.execute('''
                SELECT customer_id, seller_id
                FROM conversations
                WHERE id = ?
            ''', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            return error_response('Conversation not found', 404)
        
        customer_id = conversation['customer_id'] if isinstance(conversation, dict) else conversation[0]
        seller_id = conversation['seller_id'] if isinstance(conversation, dict) else conversation[1]
        
        if user_id != customer_id and user_id != seller_id:
            return error_response('You are not part of this conversation', 403)
        
        # Mark messages from opposite sender as read
        opposite_sender_type = 'seller' if user_role == 'customer' else 'customer'
        
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE messages
                SET is_read = 1
                WHERE conversation_id = %s
                AND sender_type = %s
                AND is_read = 0
            ''', (conversation_id, opposite_sender_type))
        else:
            cursor.execute('''
                UPDATE messages
                SET is_read = 1
                WHERE conversation_id = ?
                AND sender_type = ?
                AND is_read = 0
            ''', (conversation_id, opposite_sender_type))
        
        db.commit()
        
        # Get all messages in chronological order
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT 
                    m.id, m.conversation_id, m.sender_id, m.sender_type,
                    m.message, m.is_read, m.created_at,
                    u.first_name, u.last_name, u.email
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.conversation_id = %s
                ORDER BY m.created_at ASC
            ''', (conversation_id,))
        else:
            cursor.execute('''
                SELECT 
                    m.id, m.conversation_id, m.sender_id, m.sender_type,
                    m.message, m.is_read, m.created_at,
                    u.first_name, u.last_name, u.email
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.conversation_id = ?
                ORDER BY m.created_at ASC
            ''', (conversation_id,))
        
        messages = cursor.fetchall()
        result = format_rows(messages)
        
        return success_response(result, f'Found {len(result)} messages')
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/chat/conversations/<int:conversation_id>/messages', methods=['POST'])
@token_required
def api_send_message(conversation_id, current_user):
    """Send a message in a conversation"""
    try:
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return error_response('Message cannot be empty', 400)
        
        if len(message_text) > 5000:
            return error_response('Message too long (max 5000 characters)', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        user_id = current_user['id']
        user_role = current_user['role']
        
        # Verify user is part of the conversation
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                SELECT customer_id, seller_id
                FROM conversations
                WHERE id = %s
            ''', (conversation_id,))
        else:
            cursor.execute('''
                SELECT customer_id, seller_id
                FROM conversations
                WHERE id = ?
            ''', (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            return error_response('Conversation not found', 404)
        
        customer_id = conversation['customer_id'] if isinstance(conversation, dict) else conversation[0]
        seller_id = conversation['seller_id'] if isinstance(conversation, dict) else conversation[1]
        
        if user_id != customer_id and user_id != seller_id:
            return error_response('You are not part of this conversation', 403)
        
        # Determine sender_type
        if user_role == 'customer' and user_id == customer_id:
            sender_type = 'customer'
        elif user_role == 'seller' and user_id == seller_id:
            sender_type = 'seller'
        else:
            return error_response('Invalid sender type for this conversation', 403)
        
        # Insert message
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                INSERT INTO messages (conversation_id, sender_id, sender_type, message, is_read, created_at)
                VALUES (%s, %s, %s, %s, 0, NOW())
            ''', (conversation_id, user_id, sender_type, message_text))
        else:
            cursor.execute('''
                INSERT INTO messages (conversation_id, sender_id, sender_type, message, is_read, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (conversation_id, user_id, sender_type, message_text, datetime.utcnow().isoformat()))
        
        message_id = cursor.lastrowid
        
        # Update conversation's updated_at timestamp
        if DB_ENGINE == 'mysql':
            cursor.execute('''
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s
            ''', (conversation_id,))
        else:
            cursor.execute('''
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), conversation_id))
        
        db.commit()
        
        return success_response({
            'id': message_id,
            'conversation_id': conversation_id,
            'sender_id': user_id,
            'sender_type': sender_type,
            'message': message_text,
            'is_read': 0,
            'created_at': datetime.utcnow().isoformat()
        }, 'Message sent successfully')
    except Exception as e:
        return error_response(str(e), 500)


@app.route('/api/chat/unread-count', methods=['GET'])
@token_required
def api_get_unread_count(current_user):
    """Get total unread message count for current user"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        user_id = current_user['id']
        user_role = current_user['role']
        
        # Get unread count based on role
        if user_role == 'customer':
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT COUNT(*) as unread_count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.customer_id = %s
                    AND m.sender_type = 'seller'
                    AND m.is_read = 0
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as unread_count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.customer_id = ?
                    AND m.sender_type = 'seller'
                    AND m.is_read = 0
                ''', (user_id,))
        
        elif user_role == 'seller':
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT COUNT(*) as unread_count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.seller_id = %s
                    AND m.sender_type = 'customer'
                    AND m.is_read = 0
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as unread_count
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.seller_id = ?
                    AND m.sender_type = 'customer'
                    AND m.is_read = 0
                ''', (user_id,))
        else:
            return error_response('Only customers and sellers can access chat', 403)
        
        result = cursor.fetchone()
        unread_count = result['unread_count'] if isinstance(result, dict) else result[0]
        
        return success_response({'unread_count': unread_count}, 'Unread count retrieved')
    except Exception as e:
        return error_response(str(e), 500)


# ==================== END CHAT FEATURE API ====================


# ==================== SALES SYSTEM API ====================
# Import sales logic functions
try:
    from .sales_logic import calculate_smart_discount, get_expiring_products
except ImportError:
    from sales_logic import calculate_smart_discount, get_expiring_products


@app.route('/api/sellers/sale-suggestions', methods=['GET'])
@token_required
def api_get_sale_suggestions():
    """Get auto-generated discount suggestions for seller's expiring products"""
    try:
        # Get seller_id from token payload or g.user_id
        token = get_token_from_request()
        if not token:
            return error_response('Unauthorized', 401)
        
        payload = verify_token(token)
        seller_id = payload.get('user_id') or getattr(g, 'user_id', None)
        
        if not seller_id:
            return error_response('Unable to identify seller', 401)
        
        # Check if sales_logic functions are available
        try:
            # Get products expiring in 1-14 days
            expiring = get_expiring_products(seller_id=seller_id, min_days=1, max_days=14)
            
            suggestions = []
            for product in expiring:
                try:
                    discount_data = calculate_smart_discount(
                        product.get('price', 0),
                        product.get('days_until_expiry', 0)
                    )
                    suggestions.append({
                        'product_id': product.get('id'),
                        'product_title': product.get('title', 'Unknown Product'),
                        'current_price': product.get('price', 0),
                        'stock': product.get('stock', 0),
                        'expiry_date': product.get('expiry_date'),
                        'days_until_expiry': product.get('days_until_expiry', 0),
                        **discount_data
                    })
                except Exception as product_err:
                    app.logger.warning(f'Error processing product {product.get("id")}: {product_err}')
                    continue
            
            return success_response({
                'suggestions': suggestions,
                'total_products': len(suggestions)
            }, 'Sale suggestions generated')
        except NameError as import_err:
            app.logger.warning(f'Sales logic functions not available: {import_err}')
            return success_response({
                'suggestions': [],
                'total_products': 0
            }, 'No suggestions available')
    except Exception as e:
        app.logger.error(f'Sale suggestions error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return success_response({
            'suggestions': [],
            'total_products': 0
        }, 'No suggestions available')


@app.route('/api/sellers/products/<int:product_id>/request-sale', methods=['POST'])
@token_required
def api_request_sale(product_id):
    """Seller requests a sale/discount for their product"""
    try:
        seller_id = g.user_id
        data = request.json or {}
        
        discount_pct = float(data.get('discount_percentage', 0))
        reason = data.get('reason', 'expiring_soon')
        
        if discount_pct <= 0 or discount_pct > 50:
            return error_response('Discount must be between 1% and 50%', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify product ownership
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                SELECT id, seller_id, title, price, stock, expiry_date,
                       DATEDIFF(expiry_date, CURDATE()) as days_until_expiry
                FROM products WHERE id = %s
            """, (product_id,))
        else:
            cursor.execute("""
                SELECT id, seller_id, title, price, stock, expiry_date,
                       CAST((julianday(expiry_date) - julianday('now')) AS INTEGER) as days_until_expiry
                FROM products WHERE id = ?
            """, (product_id,))
        
        product = cursor.fetchone()
        if not product:
            return error_response('Product not found', 404)
        
        product_dict = dict(product) if hasattr(product, 'keys') else {
            'id': product[0], 'seller_id': product[1], 'title': product[2],
            'price': float(product[3]), 'stock': product[4],
            'expiry_date': product[5], 'days_until_expiry': product[6] or 999
        }
        
        if product_dict['seller_id'] != seller_id:
            return error_response('Not authorized', 403)
        
        # Check if sale already exists
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                SELECT id FROM product_sales
                WHERE product_id = %s AND status IN ('pending', 'approved')
            """, (product_id,))
        else:
            cursor.execute("""
                SELECT id FROM product_sales
                WHERE product_id = ? AND status IN ('pending', 'approved')
            """, (product_id,))
        
        if cursor.fetchone():
            return error_response('Sale request already exists for this product', 400)
        
        # Calculate prices
        original_price = product_dict['price']
        sale_price = original_price * (1 - discount_pct / 100.0)
        
        # Calculate margins
        discount_data = calculate_smart_discount(original_price, product_dict['days_until_expiry'])
        
        # Insert sale request
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                INSERT INTO product_sales (
                    product_id, discount_percentage, original_price, sale_price,
                    reason, status, days_until_expiry, seller_profit_margin,
                    requested_by, valid_from
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                product_id, discount_pct, original_price, sale_price,
                reason, 'pending', product_dict['days_until_expiry'],
                discount_data['seller_profit_margin'], seller_id
            ))
        else:
            cursor.execute("""
                INSERT INTO product_sales (
                    product_id, discount_percentage, original_price, sale_price,
                    reason, status, days_until_expiry, seller_profit_margin,
                    requested_by, valid_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                product_id, discount_pct, original_price, sale_price,
                reason, 'pending', product_dict['days_until_expiry'],
                discount_data['seller_profit_margin'], seller_id
            ))
        
        db.commit()
        sale_id = cursor.lastrowid
        cursor.close()
        
        return success_response({
            'sale_id': sale_id,
            'product_id': product_id,
            'status': 'pending',
            'discount_percentage': discount_pct,
            'sale_price': round(sale_price, 2),
            'suggested_discount': discount_data['suggested_discount']
        }, 'Sale request submitted for admin approval')
    except Exception as e:
        app.logger.error(f'Request sale error: {e}')
        return error_response(str(e), 500)


@app.route('/api/admin/pending-sales', methods=['GET'])
@role_required('admin')
def api_get_pending_sales():
    """Admin: Get sale requests with optional filters
    Query params:
        - filter: 'pending', 'review', 'approved_today', 'rejected', 'critical', or 'all'
        - status: specific status filter (overrides filter if provided)
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get filter parameter
        filter_type = request.args.get('filter', 'pending')
        status_filter = request.args.get('status')
        
        # Check if product_sales table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'product_sales'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_sales'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return success_response([], 'No sales (table does not exist)')
        except Exception as check_err:
            app.logger.warning(f'Could not check for product_sales table: {check_err}')
            cursor.close()
            return success_response([], 'No sales')
        
        # Build WHERE clause based on filter (safe parameterized queries)
        where_conditions = []
        params = []
        
        if status_filter:
            # Direct status filter
            where_conditions.append("ps.status = %s" if DB_ENGINE == 'mysql' else "ps.status = ?")
            params.append(status_filter)
        elif filter_type == 'pending':
            where_conditions.append("ps.status = %s" if DB_ENGINE == 'mysql' else "ps.status = ?")
            params.append('pending')
        elif filter_type == 'review':
            # Review: items flagged for adjustment/verification (status pending with admin_notes or needs_review flag)
            where_conditions.append("ps.status = %s" if DB_ENGINE == 'mysql' else "ps.status = ?")
            params.append('pending')
            # Add condition for items that need review (you may need to add a needs_review column or use admin_notes)
            # For now, we'll treat all pending as needing review
        elif filter_type == 'approved_today':
            # Approved Today: only approvals from today
            where_conditions.append("ps.status = %s" if DB_ENGINE == 'mysql' else "ps.status = ?")
            params.append('approved')
            if DB_ENGINE == 'mysql':
                where_conditions.append("DATE(ps.admin_approved_at) = CURDATE()")
            else:
                where_conditions.append("DATE(ps.admin_approved_at) = DATE('now')")
        elif filter_type == 'rejected':
            where_conditions.append("ps.status IN (%s, %s)" if DB_ENGINE == 'mysql' else "ps.status IN (?, ?)")
            params.extend(['rejected', 'declined'])
        elif filter_type == 'critical':
            # Critical Urgency: pending items with days_until_expiry <= 3
            where_conditions.append("ps.status = %s" if DB_ENGINE == 'mysql' else "ps.status = ?")
            params.append('pending')
            where_conditions.append("COALESCE(ps.days_until_expiry, 999) <= 3")
        elif filter_type == 'all':
            # All: no status filter
            pass
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Build seller name - use CONCAT for first_name and last_name since display_name may not exist
        # Use LEFT JOIN to handle cases where requested_by might be NULL
        # Include expiry_date and recalculate days_until_expiry
        try:
            if DB_ENGINE == 'mysql':
                query = """
                    SELECT 
                        ps.*,
                        p.title as product_title,
                        p.img_url as product_image,
                        p.stock as current_stock,
                        p.expiry_date,
                        COALESCE(DATEDIFF(p.expiry_date, CURDATE()), ps.days_until_expiry, 999) as days_until_expiry,
                        COALESCE(u.email, '') as seller_email,
                        CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.last_name, '')) as seller_name
                    FROM product_sales ps
                        LEFT JOIN products p ON ps.product_id = p.id
                        LEFT JOIN users u ON ps.requested_by = u.id
                        """ + where_clause + """
                        ORDER BY 
                            CASE WHEN ps.status = 'pending' AND COALESCE(DATEDIFF(p.expiry_date, CURDATE()), ps.days_until_expiry, 999) <= 3 THEN 0 ELSE 1 END,
                            COALESCE(DATEDIFF(p.expiry_date, CURDATE()), ps.days_until_expiry, 999) ASC, 
                            COALESCE(ps.seller_requested_at, ps.created_at, ps.admin_approved_at) DESC
                """
                cursor.execute(query, tuple(params) if params else None)
            else:
                query = """
                SELECT 
                    ps.*,
                    p.title as product_title,
                    p.img_url as product_image,
                    p.stock as current_stock,
                        p.expiry_date,
                        COALESCE(CAST((julianday(p.expiry_date) - julianday('now')) AS INTEGER), ps.days_until_expiry, 999) as days_until_expiry,
                        COALESCE(u.email, '') as seller_email,
                        (COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) as seller_name
                FROM product_sales ps
                    LEFT JOIN products p ON ps.product_id = p.id
                    LEFT JOIN users u ON ps.requested_by = u.id
                    """ + where_clause + """
                    ORDER BY 
                        CASE WHEN ps.status = 'pending' AND COALESCE(CAST((julianday(p.expiry_date) - julianday('now')) AS INTEGER), ps.days_until_expiry, 999) <= 3 THEN 0 ELSE 1 END,
                        COALESCE(CAST((julianday(p.expiry_date) - julianday('now')) AS INTEGER), ps.days_until_expiry, 999) ASC, 
                        COALESCE(ps.seller_requested_at, ps.created_at, ps.admin_approved_at) DESC
                """
                cursor.execute(query, tuple(params) if params else None)
        
            rows = cursor.fetchall() or []
        except Exception as query_err:
            app.logger.error(f'Query error in api_get_pending_sales: {query_err}')
            import traceback
            app.logger.error(traceback.format_exc())
            # Return empty array instead of failing
            return success_response([], f'No sales (query error: {str(query_err)})')
        finally:
            cursor.close()
        
        # Format rows properly and calculate profit metrics
        sales = []
        for row in rows:
            row_dict = format_row(row)
            
            # Recalculate profit metrics if not present or if sale_price changed
            if row_dict.get('sale_price') and row_dict.get('original_price'):
                try:
                    # Calculate profit metrics using the same logic as calculate_smart_discount
                    cost_ratio = 0.65  # 65% cost ratio
                    platform_commission = get_platform_commission_rate()  # Get from platform settings
                    
                    original_price = float(row_dict.get('original_price', 0))
                    sale_price = float(row_dict.get('sale_price', 0))
                    estimated_cost = original_price * cost_ratio
                    
                    # Calculate seller revenue after commission
                    seller_revenue = sale_price * (1 - platform_commission)
                    seller_profit = seller_revenue - estimated_cost
                    seller_margin_pct = (seller_profit / estimated_cost) * 100.0 if estimated_cost > 0 else 0
                    platform_commission_amount = sale_price * platform_commission
                    platform_commission_pct = platform_commission * 100
                    
                    # Update row_dict with calculated values
                    row_dict['seller_profit_margin'] = round(seller_margin_pct, 2)
                    row_dict['platform_commission'] = round(platform_commission_pct, 2)
                    row_dict['platform_commission_amount'] = round(platform_commission_amount, 2)
                    row_dict['seller_revenue'] = round(seller_revenue, 2)
                    row_dict['seller_profit'] = round(seller_profit, 2)
                    row_dict['estimated_cost'] = round(estimated_cost, 2)
                except Exception as calc_err:
                    app.logger.warning(f'Error calculating profit metrics: {calc_err}')
                    # Set defaults if calculation fails
                    row_dict['seller_profit_margin'] = 0
                    default_commission_pct = get_platform_commission_rate() * 100
                    row_dict['platform_commission'] = round(default_commission_pct, 2)
            
            sales.append(row_dict)
        
        # Frontend expects data.data to be the array directly
        return success_response(sales, f'Sales retrieved (filter: {filter_type})')
    except Exception as e:
        app.logger.error(f'Get pending sales error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(f'Failed to fetch sales: {str(e)}', 500)


@app.route('/api/admin/sales/<int:sale_id>/approve', methods=['POST'])
@role_required('admin')
def api_approve_sale(sale_id):
    """Admin: Approve a sale request"""
    try:
        admin_id = g.user_id
        data = request.json or {}
        admin_notes = data.get('notes', '')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get sale details
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT * FROM product_sales WHERE id = %s', (sale_id,))
        else:
            cursor.execute('SELECT * FROM product_sales WHERE id = ?', (sale_id,))
        
        sale = cursor.fetchone()
        if not sale:
            return error_response('Sale request not found', 404)
        
        sale_dict = dict(sale) if hasattr(sale, 'keys') else {
            'id': sale[0], 'product_id': sale[1], 'status': sale[6]
        }
        
        if sale_dict['status'] != 'pending':
            return error_response('Sale request already processed', 400)
        
        # Get sale details including sale_price
        sale_dict = format_row(sale)
        product_id = sale_dict.get('product_id')
        sale_price = sale_dict.get('sale_price')
        
        if not product_id or not sale_price:
            cursor.close()
            return error_response('Invalid sale data', 400)
        
        # Update sale status
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                UPDATE product_sales
                SET status = 'approved',
                    is_active = 1,
                    approved_by = %s,
                    admin_approved_at = NOW(),
                    admin_notes = %s
                WHERE id = %s
            """, (admin_id, admin_notes, sale_id))
            
            # Update product price to sale price
            cursor.execute("""
                UPDATE products
                SET price = %s
                WHERE id = %s
            """, (sale_price, product_id))
        else:
            cursor.execute("""
                UPDATE product_sales
                SET status = 'approved',
                    is_active = 1,
                    approved_by = ?,
                    admin_approved_at = datetime('now'),
                    admin_notes = ?
                WHERE id = ?
            """, (admin_id, admin_notes, sale_id))
            
            # Update product price to sale price
            cursor.execute("""
                UPDATE products
                SET price = ?
                WHERE id = ?
            """, (sale_price, product_id))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'sale_id': sale_id,
            'status': 'approved',
            'product_id': product_id,
            'new_price': float(sale_price)
        }, 'Sale approved successfully and product price updated')
    except Exception as e:
        app.logger.error(f'Approve sale error: {e}')
        return error_response(str(e), 500)


@app.route('/api/admin/sales/<int:sale_id>/review', methods=['POST'])
@role_required('admin')
def api_review_sale(sale_id):
    """Admin: Mark a sale request as needing review/clarification"""
    try:
        admin_id = g.user_id
        data = request.json or {}
        admin_notes = data.get('notes', 'Needs clarification from seller')
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if sale exists and is pending
        if DB_ENGINE == 'mysql':
            cursor.execute('SELECT status FROM product_sales WHERE id = %s', (sale_id,))
        else:
            cursor.execute('SELECT status FROM product_sales WHERE id = ?', (sale_id,))
        
        sale = cursor.fetchone()
        if not sale:
            cursor.close()
            return error_response('Sale request not found', 404)
        
        sale_status = sale[0] if isinstance(sale, (tuple, list)) else sale.get('status')
        if sale_status != 'pending':
            cursor.close()
            return error_response('Can only review pending sales', 400)
        
        # Update sale with review notes (keep status as 'pending' but add admin_notes)
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                UPDATE product_sales
                SET admin_notes = %s
                WHERE id = %s AND status = 'pending'
            """, (admin_notes, sale_id))
        else:
            cursor.execute("""
                UPDATE product_sales
                SET admin_notes = ?
                WHERE id = ? AND status = 'pending'
            """, (admin_notes, sale_id))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'sale_id': sale_id,
            'status': 'pending',
            'review_notes': admin_notes
        }, 'Sale marked for review - seller will be notified')
    except Exception as e:
        app.logger.error(f'Review sale error: {e}')
        return error_response(str(e), 500)


@app.route('/api/admin/sales/<int:sale_id>/reject', methods=['POST'])
@role_required('admin')
def api_reject_sale(sale_id):
    """Admin: Reject a sale request"""
    try:
        admin_id = g.user_id
        data = request.json or {}
        admin_notes = data.get('notes', 'Rejected by admin')
        
        db = get_db()
        cursor = db.cursor()
        
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                UPDATE product_sales
                SET status = 'rejected',
                    is_active = 0,
                    approved_by = %s,
                    admin_rejected_at = NOW(),
                    admin_notes = %s
                WHERE id = %s AND status = 'pending'
            """, (admin_id, admin_notes, sale_id))
        else:
            cursor.execute("""
                UPDATE product_sales
                SET status = 'rejected',
                    is_active = 0,
                    approved_by = ?,
                    admin_rejected_at = datetime('now'),
                    admin_notes = ?
                WHERE id = ? AND status = 'pending'
            """, (admin_id, admin_notes, sale_id))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'sale_id': sale_id,
            'status': 'rejected'
        }, 'Sale rejected')
    except Exception as e:
        app.logger.error(f'Reject sale error: {e}')
        return error_response(str(e), 500)


@app.route('/api/sellers/sales', methods=['GET'])
@token_required
def api_seller_get_sales():
    """Seller: Get all their sale requests"""
    try:
        seller_id = g.user_id
        db = get_db()
        cursor = db.cursor()
        
        # Check if product_sales table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'product_sales'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_sales'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return success_response([], 'No sales found')
        except Exception as check_err:
            app.logger.warning(f'Could not check for product_sales table: {check_err}')
            cursor.close()
            return success_response([], 'No sales found')
        
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("""
                    SELECT 
                        ps.*,
                        p.title as product_title,
                        p.img_url as product_image,
                        p.price as current_price
                    FROM product_sales ps
                    LEFT JOIN products p ON ps.product_id = p.id
                    WHERE ps.requested_by = %s
                    ORDER BY ps.created_at DESC
                """, (seller_id,))
            else:
                cursor.execute("""
                    SELECT 
                        ps.*,
                        p.title as product_title,
                        p.img_url as product_image,
                        p.price as current_price
                    FROM product_sales ps
                    LEFT JOIN products p ON ps.product_id = p.id
                    WHERE ps.requested_by = ?
                    ORDER BY ps.created_at DESC
                """, (seller_id,))
            
            sales = cursor.fetchall()
            cursor.close()
            
            formatted_sales = []
            for sale in sales:
                sale_dict = format_row(sale)
                formatted_sales.append(sale_dict)
            
            return success_response(formatted_sales, 'Sales retrieved successfully')
        except Exception as query_err:
            app.logger.error(f'Error fetching seller sales: {query_err}')
            cursor.close()
            return success_response([], 'No sales found')
    except Exception as e:
        app.logger.error(f'Get seller sales error: {e}')
        return error_response(str(e), 500)


@app.route('/api/sellers/sales/<int:sale_id>', methods=['PUT'])
@token_required
def api_seller_update_sale(sale_id):
    """Seller: Update a sale request (only if pending)"""
    try:
        seller_id = g.user_id
        data = request.json or {}
        
        discount_pct = float(data.get('discount_percentage', 0))
        reason = data.get('reason', 'expiring_soon')
        valid_until = data.get('valid_until')  # Optional end date
        
        if discount_pct <= 0 or discount_pct > 50:
            return error_response('Discount must be between 1% and 50%', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Verify sale ownership and status
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                SELECT ps.*, p.price as current_price
                FROM product_sales ps
                JOIN products p ON ps.product_id = p.id
                WHERE ps.id = %s AND ps.requested_by = %s
            """, (sale_id, seller_id))
        else:
            cursor.execute("""
                SELECT ps.*, p.price as current_price
                FROM product_sales ps
                JOIN products p ON ps.product_id = p.id
                WHERE ps.id = ? AND ps.requested_by = ?
            """, (sale_id, seller_id))
        
        sale = cursor.fetchone()
        if not sale:
            cursor.close()
            return error_response('Sale not found or unauthorized', 404)
        
        sale_dict = format_row(sale)
        
        if sale_dict.get('status') != 'pending':
            cursor.close()
            return error_response('Can only edit pending sales', 400)
        
        # Recalculate prices
        current_price = float(sale_dict.get('current_price', sale_dict.get('original_price', 0)))
        sale_price = current_price * (1 - discount_pct / 100.0)
        
        # Update sale
        if DB_ENGINE == 'mysql':
            update_query = """
                UPDATE product_sales
                SET discount_percentage = %s,
                    original_price = %s,
                    sale_price = %s,
                    reason = %s
            """
            params = [discount_pct, current_price, sale_price, reason]
            
            if valid_until:
                update_query += ", valid_until = %s"
                params.append(valid_until)
            
            update_query += " WHERE id = %s"
            params.append(sale_id)
            
            cursor.execute(update_query, tuple(params))
        else:
            update_query = """
                UPDATE product_sales
                SET discount_percentage = ?,
                    original_price = ?,
                    sale_price = ?,
                    reason = ?
            """
            params = [discount_pct, current_price, sale_price, reason]
            
            if valid_until:
                update_query += ", valid_until = ?"
                params.append(valid_until)
            
            update_query += " WHERE id = ?"
            params.append(sale_id)
            
            cursor.execute(update_query, tuple(params))
        
        db.commit()
        cursor.close()
        
        return success_response({
            'sale_id': sale_id,
            'discount_percentage': discount_pct,
            'sale_price': round(sale_price, 2)
        }, 'Sale updated successfully')
    except Exception as e:
        app.logger.error(f'Update sale error: {e}')
        return error_response(str(e), 500)


@app.route('/api/sellers/sales/<int:sale_id>', methods=['DELETE'])
@token_required
def api_seller_delete_sale(sale_id):
    """Seller: Delete a sale request (only if pending)"""
    try:
        seller_id = g.user_id
        db = get_db()
        cursor = db.cursor()
        
        # Verify sale ownership and status
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                SELECT status FROM product_sales
                WHERE id = %s AND requested_by = %s
            """, (sale_id, seller_id))
        else:
            cursor.execute("""
                SELECT status FROM product_sales
                WHERE id = ? AND requested_by = ?
            """, (sale_id, seller_id))
        
        sale = cursor.fetchone()
        if not sale:
            cursor.close()
            return error_response('Sale not found or unauthorized', 404)
        
        sale_dict = format_row(sale)
        
        if sale_dict.get('status') != 'pending':
            cursor.close()
            return error_response('Can only delete pending sales', 400)
        
        # Delete sale
        if DB_ENGINE == 'mysql':
            cursor.execute("DELETE FROM product_sales WHERE id = %s", (sale_id,))
        else:
            cursor.execute("DELETE FROM product_sales WHERE id = ?", (sale_id,))
        
        db.commit()
        cursor.close()
        
        return success_response({'sale_id': sale_id}, 'Sale deleted successfully')
    except Exception as e:
        app.logger.error(f'Delete sale error: {e}')
        return error_response(str(e), 500)


@app.route('/api/products/<int:product_id>/sale', methods=['GET'])
def api_get_product_sale(product_id):
    """Public: Get active sale for a product"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if product_sales table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'product_sales'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_sales'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return success_response({
                    'active': False
                }, 'No active sale')
        except Exception as check_err:
            app.logger.warning(f'Could not check for product_sales table: {check_err}')
            cursor.close()
            return success_response({
                'active': False
            }, 'No active sale')
        
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("""
                    SELECT * FROM product_sales
                    WHERE product_id = %s
                      AND is_active = 1
                      AND status = 'approved'
                          AND (valid_until IS NULL OR valid_until > NOW())
                    LIMIT 1
                """, (product_id,))
            else:
                cursor.execute("""
                    SELECT * FROM product_sales
                    WHERE product_id = ?
                      AND is_active = 1
                      AND status = 'approved'
                          AND (valid_until IS NULL OR valid_until > datetime('now'))
                    LIMIT 1
                """, (product_id,))
            
            sale = cursor.fetchone()
            
            # Auto-expire expired sales
            if DB_ENGINE == 'mysql':
                cursor.execute("""
                    UPDATE product_sales
                    SET is_active = 0, status = 'expired'
                    WHERE product_id = %s
                      AND is_active = 1
                      AND status = 'approved'
                      AND valid_until IS NOT NULL
                      AND valid_until <= NOW()
                """, (product_id,))
            else:
                cursor.execute("""
                    UPDATE product_sales
                    SET is_active = 0, status = 'expired'
                    WHERE product_id = ?
                      AND is_active = 1
                      AND status = 'approved'
                      AND valid_until IS NOT NULL
                      AND valid_until <= datetime('now')
                """, (product_id,))
            
            if cursor.rowcount > 0:
                db.commit()
        except Exception as query_err:
            app.logger.warning(f'Product sale query failed: {query_err}')
            sale = None
        finally:
            cursor.close()
        
        if not sale:
            return success_response({
                'active': False
            }, 'No active sale')
        
        # Format sale data safely
        try:
            if hasattr(sale, 'keys'):
                sale_data = format_row(sale)
            else:
                # Handle tuple/list format - try to get common fields
                sale_dict = {}
                if len(sale) > 0:
                    sale_dict['id'] = sale[0]
                if len(sale) > 1:
                    sale_dict['product_id'] = sale[1]
                if len(sale) > 2:
                    try:
                        sale_dict['discount_percentage'] = float(sale[2]) if sale[2] is not None else 0
                    except (ValueError, TypeError):
                        sale_dict['discount_percentage'] = 0
                if len(sale) > 3:
                    try:
                        sale_dict['original_price'] = float(sale[3]) if sale[3] is not None else 0
                    except (ValueError, TypeError):
                        sale_dict['original_price'] = 0
                if len(sale) > 4:
                    try:
                        sale_dict['sale_price'] = float(sale[4]) if sale[4] is not None else 0
                    except (ValueError, TypeError):
                        sale_dict['sale_price'] = 0
                if len(sale) > 5:
                    sale_dict['reason'] = sale[5] if sale[5] else None
                
                sale_data = sale_dict
            
            # Ensure required fields exist
            if 'active' not in sale_data:
                sale_data['active'] = True
            if 'sale_price' not in sale_data or sale_data.get('sale_price') is None:
                sale_data['active'] = False
                return success_response({
                    'active': False
                }, 'No active sale')
            
            # Ensure valid_until is included if it exists
            if 'valid_until' in sale_data and sale_data['valid_until']:
                # Convert to ISO string if it's a datetime object
                if hasattr(sale_data['valid_until'], 'isoformat'):
                    sale_data['valid_until'] = sale_data['valid_until'].isoformat()
        
            return success_response(sale_data, 'Active sale found')
        except Exception as format_err:
            app.logger.warning(f'Error formatting sale data: {format_err}')
            return success_response({
                'active': False
            }, 'No active sale')
    except Exception as e:
        app.logger.error(f'Get product sale error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return success_response({
            'active': False
        }, 'No active sale')


# ==================== END SALES SYSTEM API ====================


# ==================== HEALTH CHECK & MONITORING ====================

@app.route('/api/deals/zero-waste', methods=['GET'])
def api_zero_waste_deals():
    """Public: Get currently approved active sale deals for near-expiry/zero-waste items.
    Returns a lightweight list suitable for homepage highlights.
    Query params:
      - limit: max number of items (default 8)
    """
    try:
        limit = int(request.args.get('limit', 8))
        if limit <= 0 or limit > 50:
            limit = 8
        db = get_db()
        cursor = db.cursor()

        # Check if product_sales table exists
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW TABLES LIKE 'product_sales'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_sales'")
                table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                cursor.close()
                return success_response({'count': 0, 'items': []}, 'No deals available')
        except Exception as check_err:
            app.logger.warning(f'Could not check for product_sales table: {check_err}')

        # Build SQL according to engine
        try:
            if DB_ENGINE == 'mysql':
                sql = (
                    "SELECT ps.id as sale_id, p.id as product_id, p.title, p.img_url, p.category, "
                    "ps.discount_percentage, ps.original_price, ps.sale_price, ps.reason, p.expiry_date, p.manufacture_date "
                    "FROM product_sales ps "
                    "JOIN products p ON p.id = ps.product_id "
                    "WHERE ps.is_active = 1 AND ps.status = 'approved' "
                    "ORDER BY ps.sale_price ASC, ps.discount_percentage DESC "
                    "LIMIT %s"
                )
                cursor.execute(sql, (limit,))
            else:
                sql = (
                    "SELECT ps.id as sale_id, p.id as product_id, p.title, p.img_url, p.category, "
                    "ps.discount_percentage, ps.original_price, ps.sale_price, ps.reason, p.expiry_date, p.manufacture_date "
                    "FROM product_sales ps "
                    "JOIN products p ON p.id = ps.product_id "
                    "WHERE ps.is_active = 1 AND ps.status = 'approved' "
                    "ORDER BY ps.sale_price ASC, ps.discount_percentage DESC "
                    "LIMIT ?"
                )
                cursor.execute(sql, (limit,))

            rows = cursor.fetchall() or []
        except Exception as query_err:
            app.logger.warning(f'Zero-waste deals query failed (table may not exist): {query_err}')
            rows = []
        finally:
            cursor.close()

        deals = []
        for r in rows:
            try:
                if isinstance(r, dict):
                    row = r
                else:
                    # Fallback mapping by position
                    row = {
                        'sale_id': r[0], 'product_id': r[1], 'title': r[2], 'img_url': r[3], 'category': r[4],
                        'discount_percentage': float(r[5]) if r[5] is not None else 0, 
                        'original_price': float(r[6]) if r[6] is not None else 0, 
                        'sale_price': float(r[7]) if r[7] is not None else 0,
                        'reason': r[8] if len(r) > 8 else None, 
                        'expiry_date': r[9] if len(r) > 9 else None, 
                        'manufacture_date': r[10] if len(r) > 10 else None
                    }
                deals.append(row)
            except Exception as row_err:
                app.logger.warning(f'Error processing zero-waste deal row: {row_err}')
                continue

        return success_response({'count': len(deals), 'items': deals}, f'{len(deals)} deals found')
    except Exception as e:
        app.logger.error(f'Zero-waste deals error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return success_response({'count': 0, 'items': []}, 'No deals available')

@app.route('/api/health', methods=['GET'])
def api_health_check():
    """Basic health check endpoint"""
    try:
        from .health_check import health_check_endpoint
        return health_check_endpoint()
    except ImportError:
        # Fallback if health_check module not available
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'message': 'Server is running'
        }), 200


@app.route('/api/system/status', methods=['GET'])
@token_required
@role_required(['admin'])
def api_system_status():
    """Detailed system status (admin only)"""
    try:
        from .health_check import detailed_status_endpoint
        return detailed_status_endpoint()
    except ImportError:
        return error_response('Health check module not available', 500)
    except Exception as e:
        return error_response(str(e), 500)


# ==================== STOCK MANAGEMENT ====================

@app.route('/api/sellers/stock/low', methods=['GET'])
@token_required
@role_required(['seller'])
def api_get_low_stock():
    """Get low stock products for seller"""
    token = get_token_from_request()
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        threshold = int(request.args.get('threshold', 10))
        
        from .stock_manager import StockManager
        low_stock = StockManager.get_low_stock_products(threshold, user_id)
        
        products = format_rows(low_stock)
        
        return success_response({
            'products': products,
            'count': len(products),
            'threshold': threshold
        }, f'Found {len(products)} low stock products')
    except Exception as e:
        app.logger.error(f'Get low stock error: {e}')
        return error_response(str(e), 500)


@app.route('/api/sellers/stock/out', methods=['GET'])
@token_required
@role_required(['seller'])
def api_get_out_of_stock():
    """Get out of stock products for seller"""
    token = get_token_from_request()
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        from .stock_manager import StockManager
        out_of_stock = StockManager.get_out_of_stock_products(user_id)
        
        products = format_rows(out_of_stock)
        
        return success_response({
            'products': products,
            'count': len(products)
        }, f'Found {len(products)} out of stock products')
    except Exception as e:
        app.logger.error(f'Get out of stock error: {e}')
        return error_response(str(e), 500)


# ==================== ENHANCED ORDER MANAGEMENT ====================

@app.route('/api/orders/<int:order_id>/details', methods=['GET'])
@token_required
def api_get_order_details(order_id):
    """Get complete order details"""
    token = get_token_from_request()
    try:
        payload = verify_token(token)
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        from .order_manager import OrderManager
        order = OrderManager.get_order_details(order_id)
        
        if not order:
            return error_response('Order not found', 404)
        
        # Check permissions
        if role not in ['admin', 'rider']:
            if order.get('customer_id') != user_id:
                # Check if user is the seller of any item
                is_seller = False
                db = get_db()
                cursor = db.cursor()
                
                for item in order.get('items', []):
                    if DB_ENGINE == 'mysql':
                        cursor.execute(
                            'SELECT seller_id FROM products WHERE id = %s',
                            (item.get('product_id'),)
                        )
                    else:
                        cursor.execute(
                            'SELECT seller_id FROM products WHERE id = ?',
                            (item.get('product_id'),)
                        )
                    
                    result = cursor.fetchone()
                    if result:
                        seller_id = result['seller_id'] if isinstance(result, dict) else result[0]
                        if seller_id == user_id:
                            is_seller = True
                            break
                
                cursor.close()
                
                if not is_seller:
                    return error_response('Forbidden', 403)
        
        return success_response(order, 'Order details retrieved')
    except Exception as e:
        app.logger.error(f'Get order details error: {e}')
        return error_response(str(e), 500)


# ==================== ADMIN REPORTS ENDPOINTS ====================

@app.route('/api/admin/reports/data', methods=['GET'])
@role_required('admin')
def api_admin_reports_data():
    """Get comprehensive reports data for admin dashboard"""
    try:
        # Get date range from query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'month')  # today, week, month, quarter, year, custom
        
        db = get_db()
        cursor = db.cursor()
        
        # Calculate date range based on period
        now = datetime.now()
        
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == 'week':
            start = now - timedelta(days=7)
            end = now
        elif period == 'month':
            start = now - timedelta(days=30)
            end = now
        elif period == 'quarter':
            start = now - timedelta(days=90)
            end = now
        elif period == 'year':
            start = now - timedelta(days=365)
            end = now
        elif period == 'custom' and start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                end = end.replace(hour=23, minute=59, second=59)
            except:
                start = now - timedelta(days=30)
                end = now
        else:
            start = now - timedelta(days=30)
            end = now
        
        # Format dates for SQL
        start_str = start.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end.strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. User Registrations Trend
        registrations_data = []
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT DATE(created_at) as date, COUNT(*) as count, role
                    FROM users
                    WHERE created_at >= %s AND created_at <= %s
                    GROUP BY DATE(created_at), role
                    ORDER BY date ASC
                ''', (start_str, end_str))
            else:
                cursor.execute('''
                    SELECT DATE(created_at) as date, COUNT(*) as count, role
                    FROM users
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY DATE(created_at), role
                    ORDER BY date ASC
                ''', (start_str, end_str))
            
            for row in cursor.fetchall():
                row_dict = format_row(row)
                registrations_data.append({
                    'date': str(row_dict.get('date', '')),
                    'count': int(row_dict.get('count', 0) or 0),
                    'role': row_dict.get('role', 'customer') or 'customer'
                })
        except Exception as reg_err:
            app.logger.warning(f'Could not fetch registrations data: {reg_err}')
            registrations_data = []
        
        # 2. Revenue Analytics
        revenue_data = []
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT DATE(created_at) as date, 
                           COALESCE(SUM(total), 0) as revenue,
                           COUNT(*) as orders
                    FROM orders
                    WHERE created_at >= %s AND created_at <= %s
                    AND status IN ('delivered', 'completed', 'dispatched')
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                ''', (start_str, end_str))
            else:
                cursor.execute('''
                    SELECT DATE(created_at) as date, 
                           COALESCE(SUM(total), 0) as revenue,
                           COUNT(*) as orders
                    FROM orders
                    WHERE created_at >= ? AND created_at <= ?
                    AND status IN ('delivered', 'completed', 'dispatched')
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                ''', (start_str, end_str))
            
            for row in cursor.fetchall():
                row_dict = format_row(row)
                revenue_data.append({
                    'date': str(row_dict.get('date', '')),
                    'revenue': float(row_dict.get('revenue', 0) or 0),
                    'orders': int(row_dict.get('orders', 0) or 0)
                })
        except Exception as rev_err:
            app.logger.warning(f'Could not fetch revenue data: {rev_err}')
            revenue_data = []
        
        # Revenue by category (from products)
        revenue_by_category = []
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT p.category, COALESCE(SUM(oi.price * oi.quantity), 0) as revenue
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN products p ON oi.product_id = p.id
                    WHERE o.created_at >= %s AND o.created_at <= %s
                    AND o.status IN ('delivered', 'completed', 'dispatched')
                    GROUP BY p.category
                    ORDER BY revenue DESC
                ''', (start_str, end_str))
            else:
                cursor.execute('''
                    SELECT p.category, COALESCE(SUM(oi.price * oi.quantity), 0) as revenue
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN products p ON oi.product_id = p.id
                    WHERE o.created_at >= ? AND o.created_at <= ?
                    AND o.status IN ('delivered', 'completed', 'dispatched')
                    GROUP BY p.category
                    ORDER BY revenue DESC
                ''', (start_str, end_str))
            
            for row in cursor.fetchall():
                row_dict = format_row(row)
                revenue_by_category.append({
                    'category': row_dict.get('category', 'Uncategorized') or 'Uncategorized',
                    'revenue': float(row_dict.get('revenue', 0) or 0)
                })
        except Exception as cat_err:
            app.logger.warning(f'Could not fetch revenue by category: {cat_err}')
            revenue_by_category = []
        
        # 3. User Satisfaction (from reviews)
        satisfaction_data = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_ratings = 0
        weighted_sum = 0
        avg_rating = 0
        
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT rating, COUNT(*) as count
                    FROM reviews
                    WHERE created_at >= %s AND created_at <= %s
                    GROUP BY rating
                    ORDER BY rating DESC
                ''', (start_str, end_str))
            else:
                cursor.execute('''
                    SELECT rating, COUNT(*) as count
                    FROM reviews
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY rating
                    ORDER BY rating DESC
                ''', (start_str, end_str))
            
            for row in cursor.fetchall():
                row_dict = format_row(row)
                rating = int(row_dict.get('rating', 0) or 0)
                count = int(row_dict.get('count', 0) or 0)
                if 1 <= rating <= 5:
                    satisfaction_data[rating] = count
                    total_ratings += count
                    weighted_sum += rating * count
            
            avg_rating = weighted_sum / total_ratings if total_ratings > 0 else 0
        except Exception as sat_err:
            app.logger.warning(f'Could not fetch satisfaction data: {sat_err}')
            # Keep default values
        
        # 4. Summary Metrics
        # Total Users (ALL TIME - not filtered by date range for summary)
        total_users_all = 0
        try:
            cursor.execute('SELECT COUNT(*) as total FROM users')
            row = cursor.fetchone()
            if row:
                total_users_all = int(format_row(row).get('total', 0) or 0)
        except Exception as users_err:
            app.logger.warning(f'Could not fetch total users: {users_err}')
            total_users_all = 0
        
        # Approved Users (ALL TIME - count all approved sellers, riders, and customers)
        approved_users_all = 0
        try:
            # Count customers (all customers are considered approved)
            if DB_ENGINE == 'mysql':
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'customer'")
            else:
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'customer'")
            row = cursor.fetchone()
            approved_customers = int(format_row(row).get('count', 0) or 0) if row else 0
            
            # Count approved sellers
            if DB_ENGINE == 'mysql':
                cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM sellers WHERE shop_status = 'active'")
            else:
                cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM sellers WHERE shop_status = 'active'")
            row = cursor.fetchone()
            approved_sellers = int(format_row(row).get('count', 0) or 0) if row else 0
            
            # Count approved riders
            if DB_ENGINE == 'mysql':
                cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM riders WHERE rider_status = 'active'")
            else:
                cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM riders WHERE rider_status = 'active'")
            row = cursor.fetchone()
            approved_riders = int(format_row(row).get('count', 0) or 0) if row else 0
            
            # Total approved = customers + approved sellers + approved riders
            approved_users_all = approved_customers + approved_sellers + approved_riders
            
            app.logger.info(f'Approved users breakdown: customers={approved_customers}, sellers={approved_sellers}, riders={approved_riders}, total={approved_users_all}')
        except Exception as approved_err:
            app.logger.warning(f'Could not fetch approved users: {approved_err}')
            import traceback
            app.logger.warning(traceback.format_exc())
            # Fallback: count all users as approved if query fails
            approved_users_all = total_users_all
        
        # For summary, use all-time data; for date range, use filtered data
        total_users_in_range = 0
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute('''
                    SELECT COUNT(*) as total FROM users
                    WHERE created_at >= %s AND created_at <= %s
                ''', (start_str, end_str))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as total FROM users
                    WHERE created_at >= ? AND created_at <= ?
                ''', (start_str, end_str))
            
            row = cursor.fetchone()
            if row:
                total_users_in_range = int(format_row(row).get('total', 0) or 0)
        except Exception:
            total_users_in_range = 0
        
        approval_rate = (approved_users_all / total_users_all * 100) if total_users_all > 0 else 0
        
        # Average Response Time (using order processing time from created_at to delivered_at)
        avg_response_hours = 0.0
        try:
            if DB_ENGINE == 'mysql':
                # Only use delivered_at if it exists, otherwise use NOW() for delivered/completed orders
                cursor.execute('''
                    SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, 
                        COALESCE(delivered_at, NOW()))) as avg_hours
                    FROM orders
                    WHERE created_at >= %s AND created_at <= %s
                    AND status IN ('delivered', 'completed')
                ''', (start_str, end_str))
            else:
                # SQLite version - use delivered_at or current time
                cursor.execute('''
                    SELECT AVG((julianday(COALESCE(delivered_at, datetime('now'))) - 
                               julianday(created_at)) * 24) as avg_hours
                    FROM orders
                    WHERE created_at >= ? AND created_at <= ?
                    AND status IN ('delivered', 'completed')
                ''', (start_str, end_str))
            
            row = cursor.fetchone()
            if row:
                row_dict = format_row(row)
                avg_hours_val = row_dict.get('avg_hours')
                if avg_hours_val is not None:
                    avg_response_hours = float(avg_hours_val)
                    app.logger.info(f'Average response time calculated: {avg_response_hours} hours')
        except Exception as avg_err:
            app.logger.warning(f'Could not calculate avg response time: {avg_err}')
            import traceback
            app.logger.warning(traceback.format_exc())
            avg_response_hours = 0.0
        
        # 5. Platform Performance Metrics (simplified - using order stats)
        total_revenue = sum(r['revenue'] for r in revenue_data)
        total_orders = sum(r['orders'] for r in revenue_data)
        
        # System uptime (simplified - assume 99.9% if orders are processing)
        uptime_percentage = 99.9 if total_orders > 0 else 0
        
        # API request volume (simplified - estimate based on orders)
        api_requests = total_orders * 10  # Estimate
        
        # Average server load (simplified)
        avg_server_load = min(85.0, (total_orders / 100) * 10) if total_orders > 0 else 0
        
        cursor.close()
        
        return success_response({
            'registrations': registrations_data,
            'revenue': revenue_data,
            'revenue_by_category': revenue_by_category,
            'satisfaction': {
                'distribution': satisfaction_data,
                'average': round(avg_rating, 2),
                'total_ratings': total_ratings
            },
            'summary': {
                'total_users': total_users_all,  # All-time total
                'approved_users': approved_users_all,  # All-time approved
                'approval_rate': round(approval_rate, 2),
                'avg_response_time_hours': round(avg_response_hours, 2),
                'users_in_range': total_users_in_range  # Users in selected date range
            },
            'performance': {
                'uptime_percentage': uptime_percentage,
                'avg_server_load': round(avg_server_load, 2),
                'api_request_volume': api_requests,
                'total_revenue': total_revenue,
                'total_orders': total_orders
            },
            'date_range': {
                'start': start_str,
                'end': end_str,
                'period': period
            }
        }, 'Reports data retrieved successfully')
        
    except Exception as e:
        app.logger.error(f'Admin reports data error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(f'Failed to fetch reports data: {str(e)}', 500)


# ==================== PLATFORM SETTINGS HELPERS ====================

def get_platform_setting(setting_key, default_value=None):
    """
    Get a single platform setting value from database
    Returns the setting value as string, or default_value if not found
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT setting_value FROM platform_settings WHERE setting_key = %s', (setting_key,))
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            row_dict = format_row(row)
            value = row_dict.get('setting_value')
            return value if value is not None else default_value
        return default_value
    except Exception as e:
        app.logger.warning(f'Could not fetch platform setting {setting_key}: {e}')
        return default_value

def get_platform_commission_rate():
    """
    Get platform commission rate as decimal (e.g., 0.10 for 10%)
    Returns float between 0 and 1
    """
    commission_str = get_platform_setting('default_commission', '10')
    try:
        commission_pct = float(commission_str)
        return commission_pct / 100.0  # Convert percentage to decimal
    except (ValueError, TypeError):
        return 0.10  # Default 10%

def get_rider_service_fee_rate():
    """
    Get rider service fee rate as decimal (e.g., 0.05 for 5%)
    Returns float between 0 and 1
    """
    fee_str = get_platform_setting('rider_service_fee', '5')
    try:
        fee_pct = float(fee_str)
        return fee_pct / 100.0  # Convert percentage to decimal
    except (ValueError, TypeError):
        return 0.05  # Default 5%

# ==================== PLATFORM SETTINGS ENDPOINTS ====================

@app.route('/api/admin/platform-settings', methods=['GET'])
@role_required('admin')
def api_get_platform_settings():
    """Get all platform settings"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT setting_key, setting_value, description FROM platform_settings')
        
        settings = {}
        for row in cursor.fetchall():
            row_dict = format_row(row)
            settings[row_dict.get('setting_key')] = {
                'value': row_dict.get('setting_value'),
                'description': row_dict.get('description')
            }
        
        cursor.close()
        
        # Return with default values if table doesn't exist or is empty
        if not settings:
            settings = {
                'platform_name': {'value': 'Hub', 'description': 'Platform name displayed throughout the application'},
                'default_commission': {'value': '10', 'description': 'Default commission percentage for sellers'},
                'rider_service_fee': {'value': '5', 'description': 'Service fee percentage for riders'},
                'seller_approval_required': {'value': '1', 'description': 'Whether seller approval is required'}
            }
        
        return success_response(settings, 'Platform settings retrieved')
        
    except Exception as e:
        app.logger.warning(f'Could not fetch platform settings (table may not exist): {e}')
        # Return defaults if table doesn't exist
        return success_response({
            'platform_name': {'value': 'Hub', 'description': 'Platform name displayed throughout the application'},
            'default_commission': {'value': '10', 'description': 'Default commission percentage for sellers'},
            'rider_service_fee': {'value': '5', 'description': 'Service fee percentage for riders'},
            'seller_approval_required': {'value': '1', 'description': 'Whether seller approval is required'}
        }, 'Platform settings retrieved (using defaults)')


@app.route('/api/admin/platform-settings', methods=['PUT'])
@role_required('admin')
def api_update_platform_settings():
    """Update platform settings"""
    try:
        data = request.json or {}
        admin_id = g.user_id
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if table exists
        try:
            cursor.execute("SHOW TABLES LIKE 'platform_settings'")
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                # Create table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE platform_settings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        setting_key VARCHAR(100) UNIQUE NOT NULL,
                        setting_value TEXT,
                        description TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        updated_by INT,
                        FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                db.commit()
        except Exception as create_err:
            app.logger.warning(f'Could not create platform_settings table: {create_err}')
        
        # Update settings
        updated_settings = {}
        for key, value_info in data.items():
            if isinstance(value_info, dict):
                value = value_info.get('value', value_info)
                description = value_info.get('description', '')
            else:
                value = value_info
                description = ''
            
            cursor.execute("""
                INSERT INTO platform_settings (setting_key, setting_value, description, updated_by)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    setting_value = VALUES(setting_value),
                    updated_by = VALUES(updated_by),
                    updated_at = CURRENT_TIMESTAMP
            """, (key, str(value), description, admin_id))
            
            updated_settings[key] = value
        
        db.commit()
        cursor.close()
        
        return success_response(updated_settings, 'Platform settings updated successfully')
        
    except Exception as e:
        app.logger.error(f'Update platform settings error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return error_response(f'Failed to update platform settings: {str(e)}', 500)


@app.route('/api/platform/name', methods=['GET'])
def api_get_platform_name():
    """Public endpoint to get platform name (no auth required)"""
    try:
        platform_name = get_platform_setting('platform_name', 'Hub') or 'Hub'
        return success_response({'platform_name': platform_name}, 'Platform name retrieved')
    except Exception as e:
        # Always return a default value
        return success_response({'platform_name': 'Hub'}, 'Platform name retrieved (default)')


@app.errorhandler(500)
def handle_500(e):
    app.logger.error('Server error: %s', e)
    return jsonify({'error':'server_error'}), 500
