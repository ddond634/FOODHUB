# Quick Start Guide - Post-Security-Audit

## CRITICAL: Before Starting the Server

### 1. Configure Environment Variables

Copy the example environment file:
```bash
copy .env.example .env
```

Edit `.env` and set these **REQUIRED** values:

```bash
# Generate these with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<your-64-char-hex-string>
JWT_SECRET=<your-64-char-hex-string>

# Database credentials
DB_PASS=<your-mysql-password>

# Email configuration (for OTP)
SMTP_USER=<your-email@gmail.com>
SMTP_PASS=<your-app-specific-password>
```

### 2. Generate Secure Secrets

Run this command to generate both secrets:
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32)); print('JWT_SECRET=' + secrets.token_hex(32))"
```

Copy the output to your `.env` file.

### 3. Verify Database is Running

Make sure MySQL is running:
```bash
# Check MySQL status
mysql -u root -p -e "SELECT 1;"
```

### 4. Start the Server

```bash
python run.py
```

The server will **refuse to start** if SECRET_KEY or JWT_SECRET are not configured when ENV=prod.

## Security Changes Summary

### What Changed
1. **Hardcoded secrets removed** - Server now requires environment variables
2. **8 endpoints secured** - Admin/seller endpoints now require authentication
3. **Input validation added** - All user inputs validated before processing
4. **File uploads hardened** - Path traversal prevention, size limits, type validation
5. **CORS configured** - Only allowed origins can access API

### Testing the Fixes

#### Test Authentication
```bash
# Should fail without token
curl http://localhost:5000/api/users

# Should work with admin token
curl -H "Authorization: Bearer <admin-token>" http://localhost:5000/api/users
```

#### Test Input Validation
```bash
# Should reject negative prices
curl "http://localhost:5000/api/products/filter?price_min=-100"

# Should reject SQL injection
curl "http://localhost:5000/api/products/search?q=test%27OR%271%27=%271"
```

#### Test File Upload
```bash
# Should reject files over 5MB
curl -F "image=@large_file.jpg" \
  -H "Authorization: Bearer <seller-token>" \
  http://localhost:5000/api/upload/product-image

# Should reject invalid file types
curl -F "image=@malware.exe" \
  -H "Authorization: Bearer <seller-token>" \
  http://localhost:5000/api/upload/product-image
```

## Common Issues

### Server won't start
**Error:** `RuntimeError: SECRET_KEY environment variable MUST be set in production`

**Solution:** 
1. Check `.env` file exists in project root
2. Verify SECRET_KEY is set
3. Make sure ENV is not set to 'prod' during development

### CORS errors in browser
**Error:** `Access-Control-Allow-Origin` blocked

**Solution:** Add your frontend URL to CORS_ORIGINS in `.env`:
```bash
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### File upload fails
**Error:** `File too large`

**Solution:** Files must be under 5MB. Increase MAX_FILE_SIZE in `.env` if needed:
```bash
MAX_FILE_SIZE=10485760  # 10MB
```

## Next Steps

1. Review `SECURITY_AUDIT_REPORT.md` for detailed security improvements
2. Test all critical workflows (registration, login, orders)
3. Set up production environment with proper secrets
4. Configure HTTPS/TLS for production deployment
5. Implement rate limiting (see recommendations)

## Production Deployment Checklist

- [ ] Set ENV=prod in .env
- [ ] Generate unique SECRET_KEY (64 chars)
- [ ] Generate unique JWT_SECRET (64 chars)
- [ ] Configure production CORS_ORIGINS
- [ ] Set up MySQL with strong password
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up automated backups
- [ ] Enable database query logging
- [ ] Implement rate limiting
- [ ] Add monitoring/alerting

## Support

For security concerns, review:
- `SECURITY_AUDIT_REPORT.md` - Comprehensive security analysis
- `.env.example` - All configuration options
- `docs/` - API documentation
