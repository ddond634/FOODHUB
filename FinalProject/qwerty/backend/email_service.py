"""Email and OTP service for Hub e-commerce platform."""
import smtplib
import random
import string
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Email configuration (supports both naming conventions)
SMTP_SERVER = os.environ.get('SMTP_SERVER') or os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS') or os.environ.get('SMTP_USER', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD') or os.environ.get('SMTP_PASS', '')
SENDER_NAME = os.environ.get('SENDER_NAME', 'Hub E-Commerce')
EMAIL_FROM = os.environ.get('EMAIL_FROM', EMAIL_ADDRESS)

# OTP configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10

# In-memory OTP storage (replace with database in production)
otp_storage = {}

def generate_otp():
    """Generate a 6-digit OTP code."""
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))

def store_otp(email, otp_code):
    """Store OTP with expiry time (in-memory, replace with DB in production)."""
    expiry = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    otp_storage[email] = {
        'code': otp_code,
        'expiry': expiry,
        'attempts': 0
    }

def verify_otp(email, otp_code):
    """Verify OTP for given email."""
    if email not in otp_storage:
        return False, 'OTP not found'
    
    data = otp_storage[email]
    
    # Check expiry
    if datetime.now() > data['expiry']:
        del otp_storage[email]
        return False, 'OTP expired'
    
    # Check attempts
    if data['attempts'] >= 5:
        del otp_storage[email]
        return False, 'Too many attempts'
    
    # Verify code
    if data['code'] != otp_code:
        data['attempts'] += 1
        return False, 'Invalid OTP'
    
    # Success - remove OTP
    del otp_storage[email]
    return True, 'OTP verified'

def revoke_otp(email):
    """Revoke OTP for given email."""
    if email in otp_storage:
        del otp_storage[email]

def send_email(recipient_email, subject, html_content):
    """Send email via SMTP."""
    try:
        # If no email config, just log (development mode)
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            print(f"[DEV MODE] Email to {recipient_email}")
            print(f"  Subject: {subject}")
            print(f"  SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
            return True
        
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{SENDER_NAME} <{EMAIL_ADDRESS}>"
        message['To'] = recipient_email
        
        message.attach(MIMEText(html_content, 'html'))
        
        # Log email sending attempt
        print(f"[MAILER] Sending email to {recipient_email}")
        print(f"  Subject: {subject}")
        print(f"  Server: {SMTP_SERVER}:{SMTP_PORT}")
        print(f"  Sender: {EMAIL_ADDRESS}")
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(message)
        
        print(f"[MAILER] Email sent successfully to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[MAILER ERROR] Authentication failed for {EMAIL_ADDRESS}: {str(e)}")
        print(f"  Check SMTP_USER and SMTP_PASS in .env file")
        return False
    except smtplib.SMTPException as e:
        print(f"[MAILER ERROR] SMTP error sending to {recipient_email}: {str(e)}")
        return False
    except Exception as e:
        print(f"[MAILER ERROR] Error sending email to {recipient_email}: {str(e)}")
        return False

def send_otp_email(email, otp_code, user_type='customer'):
    """Send OTP verification email."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 8px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
            .content {{ text-align: center; }}
            .otp-code {{ 
                font-size: 32px; 
                font-weight: bold; 
                letter-spacing: 4px; 
                color: #ff6b35; 
                margin: 30px 0;
                background-color: #f0f0f0;
                padding: 20px;
                border-radius: 8px;
                font-family: monospace;
            }}
            .footer {{ margin-top: 30px; color: #999; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">Hub</div>
            </div>
            <div class="content">
                <h2>Email Verification</h2>
                <p>Thank you for signing up as a {user_type}!</p>
                <p>Use this code to verify your email address:</p>
                <div class="otp-code">{otp_code}</div>
                <p style="color: #999; font-size: 14px;">This code will expire in {OTP_EXPIRY_MINUTES} minutes.</p>
            </div>
            <div class="footer">
                <p>If you didn't sign up for a Hub account, please ignore this email.</p>
                <p>&copy; 2025 Hub E-Commerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, f"Hub - {user_type.capitalize()} Email Verification", html_content)

def send_welcome_email(email, user_name):
    """Send welcome email to new user."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 8px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
            .footer {{ margin-top: 30px; color: #999; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">Hub</div>
            </div>
            <div class="content">
                <h2>Welcome to Hub, {user_name}!</h2>
                <p>Your account has been successfully created.</p>
                <p>You can now browse products, place orders, and manage your account.</p>
                <p style="margin-top: 30px;">
                    <a href="http://127.0.0.1:5000/" style="display: inline-block; padding: 12px 30px; background-color: #ff6b35; color: white; text-decoration: none; border-radius: 5px;">Start Shopping</a>
                </p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Hub E-Commerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, "Welcome to Hub!", html_content)

def send_password_reset_email(email, reset_token):
    """Send password reset email."""
    reset_url = f"http://127.0.0.1:5000/#resetPassword?token={reset_token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 8px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
            .footer {{ margin-top: 30px; color: #999; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">Hub</div>
            </div>
            <div class="content">
                <h2>Password Reset Request</h2>
                <p>We received a request to reset your password.</p>
                <p>Click the link below to create a new password:</p>
                <p style="margin: 30px 0;">
                    <a href="{reset_url}" style="display: inline-block; padding: 12px 30px; background-color: #ff6b35; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a>
                </p>
                <p style="color: #999; font-size: 14px;">This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Hub E-Commerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, "Hub - Password Reset Request", html_content)

def send_order_confirmation_email(email, order_id, total, items):
    """Send order confirmation email."""
    items_html = ''.join([f"<li>{item['name']} x{item['qty']} - ₱{item['price']}</li>" for item in items])
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 8px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
            .order-id {{ color: #ff6b35; font-size: 18px; font-weight: bold; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
            .total {{ font-size: 20px; font-weight: bold; color: #ff6b35; margin-top: 20px; }}
            .footer {{ margin-top: 30px; color: #999; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">Hub</div>
            </div>
            <div class="content">
                <h2>Order Confirmation</h2>
                <p>Thank you for your order!</p>
                <p>Order ID: <span class="order-id">#ORD-{order_id}</span></p>
                <h3>Items Ordered:</h3>
                <ul>
                    {items_html}
                </ul>
                <p class="total">Total: ₱{total}</p>
                <p>Your order will be delivered within 1-3 business days.</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Hub E-Commerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, f"Order Confirmation - Order #{order_id}", html_content)

