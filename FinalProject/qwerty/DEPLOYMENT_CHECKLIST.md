# Production Deployment Checklist

## Pre-Deployment Checklist

### 1. Security Configuration ✓
- [ ] Change `SECRET_KEY` in `.env` to a strong random value
- [ ] Set strong admin password (not default)
- [ ] Enable HTTPS/SSL certificates
- [ ] Configure CORS for production domains only
- [ ] Review all API endpoints for authentication requirements
- [ ] Enable rate limiting on sensitive endpoints
- [ ] Set up firewall rules

### 2. Database Setup ✓
- [ ] Run all migrations:
  ```bash
  python database/migrate_add_food_product_dates.py
  python database/migrate_add_product_variations.py
  python database/migrate_add_sales_system.py
  python database/migrate_add_cart_table.py
  python database/migrate_add_messaging_system.py
  ```
- [ ] Set up database backups (automated)
- [ ] Configure database connection pooling
- [ ] Enable database foreign key constraints
- [ ] Set up database monitoring

### 3. Environment Variables
Create a production `.env` file with:

```env
# Server Configuration
FLASK_ENV=production
SECRET_KEY=<generate-strong-random-key>
SERVER_NAME=yourdomain.com

# Database Configuration (MySQL recommended for production)
DB_ENGINE=mysql
DB_HOST=localhost
DB_USER=qwerty_user
DB_PASS=<strong-database-password>
DB_NAME=qwerty_production
DB_PORT=3306

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=<app-specific-password>
EMAIL_FROM=noreply@yourdomain.com

# File Upload Configuration
MAX_UPLOAD_SIZE=5242880
UPLOAD_FOLDER=/var/www/qwerty/uploads

# Session Configuration
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Rate Limiting
RATELIMIT_ENABLED=True
RATELIMIT_DEFAULT=100 per hour
```

### 4. File Uploads & Storage
- [ ] Create upload directories with proper permissions:
  ```bash
  mkdir -p uploads/products
  mkdir -p uploads/store-logos
  mkdir -p uploads/store-banners
  chmod 755 uploads/
  ```
- [ ] Set up file size limits (currently 5MB)
- [ ] Configure allowed file extensions
- [ ] Consider using cloud storage (S3, CloudFlare R2) for production

### 5. Logging & Monitoring
- [ ] Set up log rotation
- [ ] Configure error tracking (Sentry, Rollbar)
- [ ] Set up uptime monitoring
- [ ] Configure database query logging
- [ ] Set up performance monitoring (New Relic, DataDog)

### 6. Performance Optimization
- [ ] Enable response compression (gzip)
- [ ] Set up CDN for static assets
- [ ] Configure caching (Redis recommended)
- [ ] Optimize database queries with indexes
- [ ] Set up connection pooling (already implemented)

### 7. Testing
- [ ] Run comprehensive API tests:
  ```bash
  python test_api_comprehensive.py
  ```
- [ ] Load testing with expected traffic
- [ ] Security testing (SQL injection, XSS)
- [ ] Mobile responsiveness testing
- [ ] Browser compatibility testing

### 8. Backup & Recovery
- [ ] Set up automated database backups (daily)
- [ ] Test backup restoration process
- [ ] Set up file system backups
- [ ] Document recovery procedures
- [ ] Store backups in multiple locations

## Deployment Steps

### Option 1: Traditional Server (Ubuntu/Debian)

#### 1. Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install MySQL
sudo apt install mysql-server -y

# Install Nginx
sudo apt install nginx -y

# Install Supervisor (for process management)
sudo apt install supervisor -y
```

#### 2. Set Up Application
```bash
# Create application directory
sudo mkdir -p /var/www/qwerty
cd /var/www/qwerty

# Clone your repository or upload files
# git clone <your-repo>

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
nano .env  # Edit with production values
```

#### 3. Set Up Database
```bash
# Secure MySQL installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p
```

```sql
CREATE DATABASE qwerty_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'qwerty_user'@'localhost' IDENTIFIED BY 'strong_password_here';
GRANT ALL PRIVILEGES ON qwerty_production.* TO 'qwerty_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

```bash
# Run migrations
python database/setup_fresh_database.py
```

#### 4. Configure Gunicorn
Create `/var/www/qwerty/gunicorn_config.py`:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/www/qwerty/logs/access.log"
errorlog = "/var/www/qwerty/logs/error.log"
loglevel = "info"
```

#### 5. Configure Supervisor
Create `/etc/supervisor/conf.d/qwerty.conf`:

```ini
[program:qwerty]
directory=/var/www/qwerty
command=/var/www/qwerty/venv/bin/gunicorn -c gunicorn_config.py backend.run_server:app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/www/qwerty/logs/supervisor.log
```

```bash
# Create logs directory
sudo mkdir -p /var/www/qwerty/logs
sudo chown www-data:www-data /var/www/qwerty/logs

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start qwerty
```

#### 6. Configure Nginx
Create `/etc/nginx/sites-available/qwerty`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration (use Certbot for Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 10M;

    # Static files
    location /uploads/ {
        alias /var/www/qwerty/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /static/ {
        alias /var/www/qwerty/frontend/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Frontend files
    location / {
        root /var/www/qwerty/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/qwerty /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 7. Set Up SSL with Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Option 2: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "backend.run_server:app"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DB_ENGINE=mysql
      - DB_HOST=db
      - DB_NAME=qwerty
      - DB_USER=root
      - DB_PASS=password
    depends_on:
      - db
    volumes:
      - ./uploads:/app/uploads

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: qwerty
    volumes:
      - mysql_data:/var/lib/mysql

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./frontend:/usr/share/nginx/html
    depends_on:
      - web

volumes:
  mysql_data:
```

## Post-Deployment

### 1. Health Checks
```bash
# Check server health
curl https://yourdomain.com/api/health

# Check system status (requires admin auth)
curl -H "Authorization: Bearer <admin-token>" https://yourdomain.com/api/system/status
```

### 2. Monitoring Setup
- Set up uptime monitoring (Pingdom, UptimeRobot)
- Configure error alerts
- Set up performance dashboards
- Monitor database performance

### 3. Regular Maintenance
- [ ] Daily database backups
- [ ] Weekly security updates
- [ ] Monthly performance reviews
- [ ] Quarterly security audits

## Rollback Procedure

If issues occur:
1. Stop the application:
   ```bash
   sudo supervisorctl stop qwerty
   ```

2. Restore database from backup:
   ```bash
   mysql -u qwerty_user -p qwerty_production < backup_YYYYMMDD.sql
   ```

3. Revert to previous code version

4. Restart application:
   ```bash
   sudo supervisorctl start qwerty
   ```

## Performance Benchmarks

Expected performance targets:
- API response time: < 200ms (average)
- Database query time: < 50ms (average)
- Page load time: < 2s (full page)
- Concurrent users: 1000+
- Uptime: 99.9%

## Support & Documentation

- API Documentation: `/docs/API_DOCUMENTATION.md`
- Admin Guide: `/docs/ADMIN_SALES_APPROVAL_GUIDE.md`
- Sales System: `/docs/SALES_SYSTEM_GUIDE.md`
- Troubleshooting: Contact technical support

---

## Quick Start Commands

```bash
# Start server (development)
python run.py

# Start server (production with Gunicorn)
gunicorn -c gunicorn_config.py backend.run_server:app

# Run tests
python test_api_comprehensive.py

# Check logs
tail -f logs/app.log
tail -f logs/error.log

# Database backup
mysqldump -u qwerty_user -p qwerty_production > backup_$(date +%Y%m%d).sql

# Check system health
curl http://localhost:5000/api/health
```
