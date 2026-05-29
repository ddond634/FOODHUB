# Email OTP Setup Guide

This guide explains how to configure email sending for OTP verification and welcome emails in the Hub E-Commerce system.

## Overview

The system supports SMTP-based email delivery through the `email_service.py` module. Emails are sent for:
- **OTP Verification**: During user registration (customer, seller, rider)
- **Welcome Emails**: After successful account creation
- **Password Reset**: Password recovery flow (when implemented)
- **Order Confirmation**: Order placement notifications

## Configuration

### Environment Variables

Update the `.env` file in the root directory with your SMTP credentials:

```env
# Email Configuration (SMTP for OTP verification and notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SENDER_NAME=Hub E-Commerce
EMAIL_FROM=noreply@hub-ecommerce.com
```

## Gmail Configuration (Recommended for Testing)

### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable "2-Step Verification" if not already enabled

### Step 2: Generate App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and "Windows Computer"
3. Google will generate a 16-character password
4. Copy this password and use it as `SMTP_PASS` in `.env`

### Step 3: Update .env
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx  # 16-char app password (paste without spaces)
```

## Alternative Email Providers

### SendGrid
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=SG.your_sendgrid_api_key_here
```

### AWS SES (Simple Email Service)
```env
SMTP_HOST=email-smtp.region.amazonaws.com
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASS=your_smtp_password
```

### Mailgun
```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your_domain.mailgun.org
SMTP_PASS=your_mailgun_smtp_password
```

## Development Mode (No Email)

Leave `SMTP_USER` and `SMTP_PASS` empty to use **dev mode**. Emails will be logged to the console instead of being sent:

```env
SMTP_USER=
SMTP_PASS=
```

This is useful for testing without actual email delivery.

## Testing Email Sending

### 1. Run the Server
```bash
python "py files/run_server.py"
```

### 2. Test OTP Endpoint
```bash
curl -X POST http://localhost:5000/api/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","type":"customer"}'
```

### 3. Check Console Output
- **Dev Mode**: Email details printed to console
- **Production**: Email sent via SMTP (check logs for confirmation)

Example output:
```
[MAILER] Sending email to test@example.com
  Subject: Hub - Customer Email Verification
  Server: smtp.gmail.com:587
  Sender: your.email@gmail.com
[MAILER] Email sent successfully to test@example.com
```

## Email Templates

### OTP Verification Email
- **Recipient**: New user registering
- **Trigger**: After registration form submission
- **Content**: 6-digit OTP code with 10-minute expiry
- **Template**: `send_otp_email()` in `email_service.py`

### Welcome Email
- **Recipient**: User after OTP verification
- **Trigger**: After successful OTP verification
- **Content**: Welcome message + account details
- **Template**: `send_welcome_email()` in `email_service.py`

## Troubleshooting

### "Authentication failed" Error
- **Cause**: Incorrect SMTP credentials
- **Solution**: 
  - For Gmail: Verify you're using an [App Password](https://myaccount.google.com/apppasswords), not your regular password
  - Verify `SMTP_USER` and `SMTP_PASS` are correct in `.env`

### "Connection timeout" Error
- **Cause**: SMTP server unreachable or wrong host/port
- **Solution**:
  - Verify `SMTP_HOST` and `SMTP_PORT` are correct
  - Check if your network allows SMTP (some ISPs block port 587)
  - Try port 465 (SSL/TLS) instead of 587

### Emails not received
- **Cause**: Emails sent to spam folder or email not actually sent
- **Solution**:
  - Check spam/junk folder
  - Enable "Less secure app access" if using Gmail (older method)
  - Review SMTP logs in console for error messages

### Blank SMTP_USER/SMTP_PASS (Dev Mode)
- **Behavior**: Emails logged to console, not actually sent
- **Use Case**: Testing without email provider setup
- **Next Step**: Configure real SMTP credentials for production

## Production Checklist

- [ ] Update `.env` with production SMTP credentials
- [ ] Enable 2FA on email account (if using Gmail)
- [ ] Generate App Password (if using Gmail)
- [ ] Test OTP flow end-to-end
- [ ] Verify emails arrive in user inbox (not spam)
- [ ] Monitor email delivery logs
- [ ] Set up email rate limiting if needed
- [ ] Document email provider contact for support

## Email Rate Limiting

The system currently sends OTP without rate limiting. For production, consider:
1. Limit OTP sends to 3 per hour per email
2. Add cooldown period (e.g., 60 seconds) between resend requests
3. Log all email sends for audit trail

## Support

For issues with specific email providers:
- **Gmail**: Check [Google Support](https://support.google.com/accounts/)
- **SendGrid**: Check [SendGrid Docs](https://docs.sendgrid.com/)
- **AWS SES**: Check [AWS Documentation](https://docs.aws.amazon.com/ses/)
