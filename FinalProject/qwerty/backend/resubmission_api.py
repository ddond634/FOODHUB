"""
Resubmission Workflow API Endpoints
Handles seller and rider application declines, missing requirements, and resubmissions
"""

from flask import Blueprint, request, jsonify
from backend.auth import token_required, role_required, verify_token, get_token_from_request
from backend.api_utils import success_response, error_response, format_row
from backend.email_service import send_email
import json
from datetime import datetime

resubmission_bp = Blueprint('resubmission', __name__)

def get_db():
    """Get database connection from Flask g object"""
    from flask import g
    import pymysql
    import os
    
    DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()
    
    if not hasattr(g, 'db'):
        if DB_ENGINE == 'mysql':
            MYSQL_CONFIG = {
                'host': os.environ.get('DB_HOST', '127.0.0.1'),
                'user': os.environ.get('DB_USER', 'root'),
                'password': os.environ.get('DB_PASS', ''),
                'db': os.environ.get('DB_NAME', 'qwerty'),
                'port': int(os.environ.get('DB_PORT', '3306')),
                'cursorclass': pymysql.cursors.DictCursor,
                'autocommit': False,
                'charset': 'utf8mb4'
            }
            g.db = pymysql.connect(**MYSQL_CONFIG)
    
    return g.db


def create_notification(user_id, notification_type, title, message, action_url=None):
    """Create an in-platform notification for a user"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO notifications (user_id, type, title, message, action_url, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''', (user_id, notification_type, title, message, action_url))
        
        db.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error creating notification: {e}")
        return False


def send_decline_email(email, user_type, missing_requirements):
    """Send email notification about declined application"""
    req_list = ', '.join(missing_requirements) if isinstance(missing_requirements, list) else 'various requirements'
    
    if user_type == 'seller':
        subject = "Seller Application – Additional Documents Required"
        body = f"""
        <h2>Seller Application Review</h2>
        <p>Thank you for applying to become a seller on our platform.</p>
        <p>Your application has been reviewed, but we need some additional documents to proceed:</p>
        <ul>
            {''.join([f'<li>{req}</li>' for req in (missing_requirements if isinstance(missing_requirements, list) else [req_list])])}
        </ul>
        <p>Please log in to your account and resubmit the required documents to continue.</p>
        <p>If you have any questions, feel free to contact our support team.</p>
        <p>Best regards,<br>The Hub Team</p>
        """
    else:  # rider
        subject = "Rider Application – Re-Submission Required"
        body = f"""
        <h2>Rider Application Review</h2>
        <p>Thank you for applying to become a rider on our platform.</p>
        <p>Your application needs re-submission. The following requirements are missing:</p>
        <ul>
            {''.join([f'<li>{req}</li>' for req in (missing_requirements if isinstance(missing_requirements, list) else [req_list])])}
        </ul>
        <p>Please log in to your account and complete the missing requirements.</p>
        <p>If you have any questions, feel free to contact our support team.</p>
        <p>Best regards,<br>The Hub Team</p>
        """
    
    try:
        send_email(email, subject, body)
        return True
    except Exception as e:
        print(f"Error sending decline email: {e}")
        return False


# ==========================================
# SELLER RESUBMISSION ENDPOINTS
# ==========================================

@resubmission_bp.route('/api/admin/sellers/<int:seller_id>/decline', methods=['POST'])
@role_required('admin')
def decline_seller(seller_id):
    """Decline a seller application with missing requirements"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        missing_requirements = data.get('missing_requirements', [])  # Array of requirement IDs
        decline_reason = data.get('reason', 'Missing requirements')
        
        if not missing_requirements:
            return error_response('Please select at least one missing requirement', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get seller user_id and email
        cursor.execute('''
            SELECT s.user_id, u.email, u.first_name, s.business_name
            FROM sellers s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = %s
        ''', (seller_id,))
        
        seller_data = cursor.fetchone()
        if not seller_data:
            cursor.close()
            return error_response('Seller not found', 404)
        
        user_id = seller_data['user_id']
        email = seller_data['email']
        business_name = seller_data.get('business_name', 'Your Business')
        
        # Update seller status to declined with missing requirements
        missing_req_json = json.dumps(missing_requirements)
        cursor.execute('''
            UPDATE sellers 
            SET shop_status = 'declined',
                missing_requirements = %s,
                declined_at = NOW(),
                declined_by = %s,
                decline_reason = %s
            WHERE id = %s
        ''', (missing_req_json, admin_id, decline_reason, seller_id))
        
        # Log in audit_logs
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES ('seller', %s, 'DECLINED', %s, %s, NOW())
        ''', (seller_id, f"Missing requirements: {', '.join(missing_requirements)}", admin_id))
        
        db.commit()
        cursor.close()
        
        # Create in-platform notification
        create_notification(
            user_id,
            'warning',
            'Additional Documents Required',
            f'Your seller application for "{business_name}" requires additional documents. Please resubmit the missing requirements.',
            '/seller_dashboard.html?action=resubmit'
        )
        
        # Send email notification
        send_decline_email(email, 'seller', missing_requirements)
        
        return success_response('Seller application declined. Notification sent.', {
            'seller_id': seller_id,
            'status': 'declined',
            'missing_requirements': missing_requirements
        })
        
    except Exception as e:
        print(f"Error declining seller: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/admin/sellers/<int:seller_id>/approve', methods=['POST'])
@role_required('admin')
def approve_seller(seller_id):
    """Approve a seller application"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get seller details
        cursor.execute('''
            SELECT s.user_id, u.email, u.first_name, s.business_name
            FROM sellers s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = %s
        ''', (seller_id,))
        
        seller_data = cursor.fetchone()
        if not seller_data:
            cursor.close()
            return error_response('Seller not found', 404)
        
        user_id = seller_data['user_id']
        email = seller_data['email']
        business_name = seller_data.get('business_name', 'Your Business')
        
        # Update seller status to active
        cursor.execute('''
            UPDATE sellers 
            SET shop_status = 'active',
                verified = 1,
                approved_at = NOW(),
                missing_requirements = NULL,
                declined_at = NULL,
                declined_by = NULL,
                decline_reason = NULL
            WHERE id = %s
        ''', (seller_id,))
        
        # Update user as verified
        cursor.execute('''
            UPDATE users SET is_verified = 1 WHERE id = %s
        ''', (user_id,))
        
        # Log in audit_logs
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES ('seller', %s, 'APPROVED', 'Seller application approved', %s, NOW())
        ''', (seller_id, admin_id))
        
        db.commit()
        cursor.close()
        
        # Create in-platform notification
        create_notification(
            user_id,
            'success',
            'Seller Application Approved!',
            f'Congratulations! Your seller application for "{business_name}" has been approved. You can now start selling on our platform.',
            '/seller_dashboard.html'
        )
        
        # Send approval email
        try:
            send_email(email, 
                      'Seller Application Approved!',
                      f'''<h2>Congratulations!</h2>
                      <p>Your seller application for <strong>{business_name}</strong> has been approved.</p>
                      <p>You can now access your seller dashboard and start listing products.</p>
                      <p>Welcome to the Hub family!</p>''')
        except:
            pass
        
        return success_response('Seller approved successfully', {
            'seller_id': seller_id,
            'status': 'active'
        })
        
    except Exception as e:
        print(f"Error approving seller: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/admin/sellers/<int:seller_id>/request-documents', methods=['POST'])
@role_required('admin')
def request_seller_documents(seller_id):
    """Request additional documents from seller without declining"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        message = data.get('message', 'Additional documents required')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get seller details
        cursor.execute('''
            SELECT s.user_id, u.email, u.first_name, s.business_name
            FROM sellers s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = %s
        ''', (seller_id,))
        
        seller_data = cursor.fetchone()
        if not seller_data:
            cursor.close()
            return error_response('Seller not found', 404)
        
        user_id = seller_data['user_id']
        email = seller_data['email']
        
        # Log the request
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES ('seller', %s, 'DOCUMENT_REQUEST', %s, %s, NOW())
        ''', (seller_id, message, admin_id))
        
        db.commit()
        cursor.close()
        
        # Create notification
        create_notification(
            user_id,
            'info',
            'Additional Documents Requested',
            message,
            '/seller_dashboard.html?action=documents'
        )
        
        # Send email
        try:
            send_email(email,
                      'Additional Documents Requested',
                      f'''<h2>Document Request</h2>
                      <p>{message}</p>
                      <p>Please log in to your account to upload the requested documents.</p>''')
        except:
            pass
        
        return success_response('Document request sent successfully')
        
    except Exception as e:
        print(f"Error requesting documents: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/seller/resubmit', methods=['POST'])
@token_required
def seller_resubmit():
    """Handle seller resubmission of missing documents"""
    try:
        token_data = verify_token(get_token_from_request())
        user_id = token_data.get('user_id')
        
        # Get uploaded documents from request
        # This would handle file uploads for the missing requirements
        data = request.get_json()
        submitted_documents = data.get('documents', {})
        
        db = get_db()
        cursor = db.cursor()
        
        # Get seller ID
        cursor.execute('SELECT id FROM sellers WHERE user_id = %s', (user_id,))
        seller = cursor.fetchone()
        
        if not seller:
            cursor.close()
            return error_response('Seller not found', 404)
        
        seller_id = seller['id']
        
        # Update seller status to resubmitted
        cursor.execute('''
            UPDATE sellers 
            SET shop_status = 'resubmitted',
                resubmitted_at = NOW()
            WHERE id = %s
        ''', (seller_id,))
        
        db.commit()
        cursor.close()
        
        return success_response('Documents resubmitted successfully. Admin will review your application.')
        
    except Exception as e:
        print(f"Error in seller resubmission: {e}")
        return error_response(str(e), 500)


# ==========================================
# RIDER RESUBMISSION ENDPOINTS
# ==========================================

@resubmission_bp.route('/api/admin/riders/<int:rider_id>/decline', methods=['POST'])
@role_required('admin')
def decline_rider(rider_id):
    """Decline a rider application with missing requirements"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        missing_requirements = data.get('missing_requirements', [])
        decline_reason = data.get('reason', 'Missing requirements')
        
        if not missing_requirements:
            return error_response('Please select at least one missing requirement', 400)
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider user_id and email
        cursor.execute('''
            SELECT r.user_id, u.email, u.first_name, u.last_name
            FROM riders r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = %s
        ''', (rider_id,))
        
        rider_data = cursor.fetchone()
        if not rider_data:
            cursor.close()
            return error_response('Rider not found', 404)
        
        user_id = rider_data['user_id']
        email = rider_data['email']
        rider_name = f"{rider_data.get('first_name', '')} {rider_data.get('last_name', '')}".strip()
        
        # Update rider status to declined
        missing_req_json = json.dumps(missing_requirements)
        cursor.execute('''
            UPDATE riders 
            SET rider_status = 'declined',
                missing_requirements = %s,
                declined_at = NOW(),
                declined_by = %s,
                decline_reason = %s
            WHERE id = %s
        ''', (missing_req_json, admin_id, decline_reason, rider_id))
        
        # Log in audit_logs
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES ('rider', %s, 'DECLINED', %s, %s, NOW())
        ''', (rider_id, f"Missing requirements: {', '.join(missing_requirements)}", admin_id))
        
        db.commit()
        cursor.close()
        
        # Create notification
        create_notification(
            user_id,
            'warning',
            'Re-Submission Required',
            f'Your rider application requires re-submission. Please complete the missing requirements.',
            '/rider_dashboard.html?action=resubmit'
        )
        
        # Send email
        send_decline_email(email, 'rider', missing_requirements)
        
        return success_response('Rider application declined. Notification sent.', {
            'rider_id': rider_id,
            'status': 'declined',
            'missing_requirements': missing_requirements
        })
        
    except Exception as e:
        print(f"Error declining rider: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/admin/riders/<int:rider_id>/approve', methods=['POST'])
@role_required('admin')
def approve_rider(rider_id):
    """Approve a rider application"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider details
        cursor.execute('''
            SELECT r.user_id, u.email, u.first_name, u.last_name
            FROM riders r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = %s
        ''', (rider_id,))
        
        rider_data = cursor.fetchone()
        if not rider_data:
            cursor.close()
            return error_response('Rider not found', 404)
        
        user_id = rider_data['user_id']
        email = rider_data['email']
        rider_name = f"{rider_data.get('first_name', '')} {rider_data.get('last_name', '')}".strip()
        
        # Update rider status to active
        cursor.execute('''
            UPDATE riders 
            SET rider_status = 'active',
                verified = 1,
                approved_at = NOW(),
                missing_requirements = NULL,
                declined_at = NULL,
                declined_by = NULL,
                decline_reason = NULL,
                availability = 'available'
            WHERE id = %s
        ''', (rider_id,))
        
        # Update user as verified
        cursor.execute('''
            UPDATE users SET is_verified = 1 WHERE id = %s
        ''', (user_id,))
        
        # Log approval
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES ('rider', %s, 'APPROVED', 'Rider application approved', %s, NOW())
        ''', (rider_id, admin_id))
        
        db.commit()
        cursor.close()
        
        # Create notification
        create_notification(
            user_id,
            'success',
            'Rider Application Approved!',
            f'Congratulations! Your rider application has been approved. You can now start accepting delivery orders.',
            '/rider_dashboard.html'
        )
        
        # Send email
        try:
            send_email(email,
                      'Rider Application Approved!',
                      f'''<h2>Congratulations, {rider_name}!</h2>
                      <p>Your rider application has been approved.</p>
                      <p>You can now access your rider dashboard and start accepting delivery orders.</p>
                      <p>Welcome to the Hub family!</p>''')
        except:
            pass
        
        return success_response('Rider approved successfully', {
            'rider_id': rider_id,
            'status': 'active'
        })
        
    except Exception as e:
        print(f"Error approving rider: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/admin/riders/<int:rider_id>/request-resubmission', methods=['POST'])
@role_required('admin')
def request_rider_resubmission(rider_id):
    """Request rider to resubmit application"""
    try:
        token_data = verify_token(get_token_from_request())
        admin_id = token_data.get('user_id')
        
        data = request.get_json()
        message = data.get('message', 'Please review and resubmit your application')
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider details
        cursor.execute('''
            SELECT r.user_id, u.email, u.first_name
            FROM riders r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = %s
        ''', (rider_id,))
        
        rider_data = cursor.fetchone()
        if not rider_data:
            cursor.close()
            return error_response('Rider not found', 404)
        
        user_id = rider_data['user_id']
        email = rider_data['email']
        
        # Log the request
        cursor.execute('''
            INSERT INTO audit_logs (target_type, target_id, action_type, reason, admin_id, created_at)
            VALUES ('rider', %s, 'RESUBMISSION_REQUEST', %s, %s, NOW())
        ''', (rider_id, message, admin_id))
        
        db.commit()
        cursor.close()
        
        # Create notification
        create_notification(
            user_id,
            'info',
            'Application Review Needed',
            message,
            '/rider_dashboard.html?action=resubmit'
        )
        
        # Send email
        try:
            send_email(email,
                      'Rider Application Review',
                      f'''<h2>Application Review</h2>
                      <p>{message}</p>
                      <p>Please log in to your account to review and update your application.</p>''')
        except:
            pass
        
        return success_response('Resubmission request sent successfully')
        
    except Exception as e:
        print(f"Error requesting resubmission: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/rider/resubmit', methods=['POST'])
@token_required
def rider_resubmit():
    """Handle rider resubmission"""
    try:
        token_data = verify_token(get_token_from_request())
        user_id = token_data.get('user_id')
        
        data = request.get_json()
        submitted_documents = data.get('documents', {})
        
        db = get_db()
        cursor = db.cursor()
        
        # Get rider ID
        cursor.execute('SELECT id FROM riders WHERE user_id = %s', (user_id,))
        rider = cursor.fetchone()
        
        if not rider:
            cursor.close()
            return error_response('Rider not found', 404)
        
        rider_id = rider['id']
        
        # Update rider status to resubmitted
        cursor.execute('''
            UPDATE riders 
            SET rider_status = 'resubmitted',
                resubmitted_at = NOW()
            WHERE id = %s
        ''', (rider_id,))
        
        db.commit()
        cursor.close()
        
        return success_response('Application resubmitted successfully. Admin will review your application.')
        
    except Exception as e:
        print(f"Error in rider resubmission: {e}")
        return error_response(str(e), 500)


# ==========================================
# NOTIFICATION ENDPOINTS
# ==========================================

@resubmission_bp.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications():
    """Get notifications for current user"""
    try:
        token_data = verify_token(get_token_from_request())
        user_id = token_data.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT * FROM notifications
            WHERE user_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            LIMIT 20
        ''', (user_id,))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append(format_row(row))
        
        cursor.close()
        
        return success_response('Notifications retrieved', {'notifications': notifications})
        
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/notifications/<int:notification_id>/mark-read', methods=['PUT'])
@token_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        token_data = verify_token(get_token_from_request())
        user_id = token_data.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE notifications 
            SET is_read = 1
            WHERE id = %s AND user_id = %s
        ''', (notification_id, user_id))
        
        db.commit()
        cursor.close()
        
        return success_response('Notification marked as read')
        
    except Exception as e:
        print(f"Error marking notification read: {e}")
        return error_response(str(e), 500)


@resubmission_bp.route('/api/user/status', methods=['GET'])
@token_required
def get_user_status():
    """Get user status and missing requirements if declined"""
    try:
        token_data = verify_token(get_token_from_request())
        user_id = token_data.get('user_id')
        role = token_data.get('role')
        
        db = get_db()
        cursor = db.cursor()
        
        if role == 'seller':
            cursor.execute('''
                SELECT shop_status as status, missing_requirements, decline_reason
                FROM sellers WHERE user_id = %s
            ''', (user_id,))
        elif role == 'rider':
            cursor.execute('''
                SELECT rider_status as status, missing_requirements, decline_reason
                FROM riders WHERE user_id = %s
            ''', (user_id,))
        else:
            cursor.close()
            return success_response('User status retrieved', {'status': 'active'})
        
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            return success_response('User status retrieved', {'status': 'pending'})
        
        status_data = {
            'status': result['status'],
            'missing_requirements': json.loads(result['missing_requirements']) if result.get('missing_requirements') else [],
            'decline_reason': result.get('decline_reason')
        }
        
        return success_response('User status retrieved', status_data)
        
    except Exception as e:
        print(f"Error getting user status: {e}")
        return error_response(str(e), 500)
