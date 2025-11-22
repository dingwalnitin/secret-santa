# Secret Santa Application - Scalability Guide

## Problem Statement
When the number of users is high, the website crashes - not everyone gets the spin wheel animation to load properly. The database has been migrated from SQLite to Azure SQL, which resolves database-related bottlenecks, but there are other configuration and deployment issues that need to be addressed.

## Table of Contents
1. [Critical Issues](#critical-issues)
2. [Server Configuration](#server-configuration)
3. [Database Connection Management](#database-connection-management)
4. [Static File Serving](#static-file-serving)
5. [Session Management](#session-management)
6. [Rate Limiting at Scale](#rate-limiting-at-scale)
7. [WebSocket/SocketIO Configuration](#websocketsocketio-configuration)
8. [Caching Strategy](#caching-strategy)
9. [Monitoring and Diagnostics](#monitoring-and-diagnostics)
10. [Azure-Specific Recommendations](#azure-specific-recommendations)
11. [Deployment Checklist](#deployment-checklist)

---

## Critical Issues

### 1. **No Production Server Configuration**
**Problem:** The application currently runs with `python app.py` which uses Flask's development server. The `socketio.run()` command at the end of `app.py` is NOT suitable for production with high user loads.

**Impact:** 
- Limited to single process
- No worker concurrency
- Poor performance under load
- Will crash or hang with 20+ simultaneous users

**Solution:** Use Gunicorn with eventlet workers

### 2. **Missing Worker Configuration**
**Problem:** While `gunicorn` and `eventlet` are in `requirements.txt`, there's no configuration file specifying how many workers to run.

**Impact:**
- Single worker = single point of failure
- All users compete for one process
- If one user's request blocks, everyone waits

---

## Server Configuration

### Production Server Setup

#### Option 1: Gunicorn with Eventlet (Recommended)

Create a file named `gunicorn_config.py`:

```python
# gunicorn_config.py
import multiprocessing
import os

# Binding
bind = "0.0.0.0:5000"

# Worker configuration
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "eventlet"
worker_connections = 1000

# Timeout settings
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "secret-santa"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Performance
preload_app = True
max_requests = 1000
max_requests_jitter = 50
```

**Start the application:**
```bash
gunicorn -c gunicorn_config.py app:app
```

#### Option 2: Gunicorn Command Line

```bash
gunicorn \
  --worker-class eventlet \
  --workers 4 \
  --worker-connections 1000 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app
```

#### Worker Calculation
- **Formula:** `(2 × CPU cores) + 1`
- **For Azure B1/B2:** 1-2 cores → 3-5 workers
- **For Azure S1:** 1 core → 3 workers
- **For Azure S2:** 2 cores → 5 workers
- **For Azure S3:** 4 cores → 9 workers

⚠️ **Important:** More workers ≠ better. Too many workers can cause:
- Memory exhaustion
- Database connection pool exhaustion
- Context switching overhead

### Environment-Specific Configuration

Create different configurations for different environments:

```bash
# .env.production
GUNICORN_WORKERS=5
WORKER_CONNECTIONS=1000
TIMEOUT=120

# .env.staging
GUNICORN_WORKERS=2
WORKER_CONNECTIONS=500
TIMEOUT=60
```

---

## Database Connection Management

### Current Issue
The app uses SQLAlchemy but doesn't explicitly configure connection pooling, which is critical for Azure SQL.

### Recommended Configuration

Add to `config.py`:

```python
class Config:
    # ... existing config ...
    
    # SQLAlchemy connection pooling
    SQLALCHEMY_POOL_SIZE = 10          # Number of connections to keep open
    SQLALCHEMY_POOL_TIMEOUT = 30       # Seconds to wait for connection
    SQLALCHEMY_POOL_RECYCLE = 3600     # Recycle connections after 1 hour
    SQLALCHEMY_MAX_OVERFLOW = 20       # Additional connections when pool is full
    SQLALCHEMY_POOL_PRE_PING = True    # Test connections before using
    
    # Azure SQL specific
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 30,
            'application_name': 'SecretSanta'
        }
    }
```

### Azure SQL Connection String

Ensure the connection string is properly formatted:

```bash
# In .env or Azure App Settings
DATABASE_URL=mssql+pyodbc://username:password@server.database.windows.net:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30
```

### Connection Pool Sizing

**Formula:** `(workers × 2) + overflow`

Example for 5 workers:
- Pool size: 10 connections
- Max overflow: 20 connections
- Total possible: 30 connections

⚠️ **Azure SQL DTU limits:**
- Basic: 30 concurrent connections
- Standard (S0): 60 concurrent connections
- Standard (S1): 90 concurrent connections
- Standard (S2): 120 concurrent connections

Make sure pool size + overflow < Azure SQL connection limit.

---

## Static File Serving

### Current Issue
Flask serving static files (CSS, JS, images) directly in production is inefficient and causes:
- Worker threads blocked serving static content
- No caching headers
- No compression
- No CDN benefits

### Solution 1: Nginx Reverse Proxy (Recommended)

**Nginx configuration:**

```nginx
# /etc/nginx/sites-available/secret-santa

upstream secret_santa {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 16M;
    
    # Serve static files directly
    location /static/ {
        alias /path/to/secret-santa/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://secret_santa;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### Solution 2: Azure CDN / Azure Blob Storage

For Azure deployments, use Azure CDN with Blob Storage:

1. **Upload static files to Azure Blob Storage:**
   ```bash
   az storage blob upload-batch \
     --account-name yourstorage \
     --destination '$web' \
     --source ./static
   ```

2. **Configure Azure CDN endpoint**

3. **Update templates to use CDN URL:**
   ```python
   # config.py
   STATIC_URL = os.environ.get('STATIC_URL', '/static/')
   ```

### Solution 3: WhiteNoise (Python-based)

For simpler deployments, use WhiteNoise:

```bash
pip install whitenoise
```

Update `app.py`:
```python
from whitenoise import WhiteNoise

app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')
```

---

## Session Management

### Current Issue
Flask sessions stored in browser cookies have limitations:
- 4KB size limit
- Sent with every request (overhead)
- Not suitable for multi-server deployments

### Solution: Redis Session Store

**Install Redis client:**
```bash
pip install redis flask-session
```

**Configuration:**
```python
# config.py
from datetime import timedelta

class Config:
    # Session configuration
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_REDIS = redis.from_url(
        os.environ.get('REDIS_URL', 'redis://localhost:6379')
    )
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
```

**Azure Redis Cache:**
```bash
# .env
REDIS_URL=rediss://:password@your-cache.redis.cache.windows.net:6380/0
```

### Alternative: Database Sessions

If Redis is not available, use database sessions:

```python
# config.py
SESSION_TYPE = 'sqlalchemy'
SESSION_SQLALCHEMY = db
SESSION_SQLALCHEMY_TABLE = 'sessions'
```

---

## Rate Limiting at Scale

### Current Issue
The app uses in-memory rate limiting which:
- Doesn't work across multiple workers
- Resets when worker restarts
- Not shared between servers

### Solution: Redis-Based Rate Limiting

```python
# config.py
RATELIMIT_STORAGE_URL = os.environ.get(
    'REDIS_URL', 
    'redis://localhost:6379'
)
```

**Azure Redis Cache connection:**
```bash
REDIS_URL=rediss://:password@your-cache.redis.cache.windows.net:6380/0
```

### Rate Limit Recommendations

```python
# For reveal endpoint
@app.route('/reveal')
@limiter.limit("10 per minute")  # Prevent spam refreshing
@user_required
def reveal():
    # ...

# For API endpoints
@app.route('/api/complete-reveal', methods=['POST'])
@limiter.limit("5 per minute")
@user_required
def complete_reveal():
    # ...
```

---

## WebSocket/SocketIO Configuration

### Current Issues
1. **CORS set to `*`** - Security risk and potential performance issue
2. **No connection limits** - Users can open unlimited connections
3. **No reconnection strategy** - If connection drops, may not reconnect properly

### Production SocketIO Configuration

```python
# app.py
socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "https://your-domain.com",
        "https://www.your-domain.com"
    ],
    async_mode='eventlet',
    logger=True,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6,  # 1MB
    async_handlers=True
)
```

### Nginx WebSocket Configuration

Ensure Nginx is configured for WebSocket upgrade:

```nginx
location /socket.io/ {
    proxy_pass http://secret_santa;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

### Azure App Service WebSocket

Enable WebSockets in Azure App Service:

```bash
az webapp config set \
  --name your-app-name \
  --resource-group your-resource-group \
  --web-sockets-enabled true
```

Or in Azure Portal:
1. Go to App Service → Configuration → General settings
2. Enable "Web sockets"
3. Save and restart

---

## Caching Strategy

### Frontend Caching

**Add cache headers for static resources:**

```python
# Add to app.py
from flask import make_response
from functools import wraps

def add_cache_header(max_age=3600):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = make_response(f(*args, **kwargs))
            response.cache_control.max_age = max_age
            response.cache_control.public = True
            return response
        return decorated_function
    return decorator

@app.route('/static/<path:filename>')
@add_cache_header(max_age=86400)  # 24 hours
def static_files(filename):
    return send_from_directory('static', filename)
```

### Database Query Caching

For frequently accessed data that doesn't change often:

```python
# Example: Cache system settings
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL'),
    'CACHE_DEFAULT_TIMEOUT': 300
})

@cache.cached(timeout=60, key_prefix='system_settings')
def get_system_settings():
    return SystemSettings.query.first()
```

---

## Monitoring and Diagnostics

### Application Performance Monitoring (APM)

**Azure Application Insights:**

```bash
pip install opencensus-ext-azure opencensus-ext-flask
```

```python
# app.py
from opencensus.ext.azure import metrics_exporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware

# Application Insights
middleware = FlaskMiddleware(
    app,
    exporter=metrics_exporter.new_metrics_exporter(
        connection_string=os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
    )
)
```

### Health Check Endpoint

```python
@app.route('/health')
def health_check():
    try:
        # Check database
        db.session.execute('SELECT 1')
        
        # Check Redis if using
        if cache:
            cache.set('health_check', 'ok', timeout=1)
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'cache': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503
```

### Logging Configuration

```python
# app.py
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    # File handler
    file_handler = RotatingFileHandler(
        'logs/secret-santa.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('Secret Santa startup')
```

### Key Metrics to Monitor

1. **Response Time**
   - Average response time per endpoint
   - 95th percentile response time
   - Target: < 200ms for API, < 1s for pages

2. **Error Rate**
   - 500 errors
   - 404 errors
   - Failed database queries
   - Target: < 0.1%

3. **Throughput**
   - Requests per second
   - Concurrent users
   - WebSocket connections

4. **Resource Usage**
   - CPU utilization (target: < 70%)
   - Memory usage (target: < 80%)
   - Database connections (target: < 80% of pool)

5. **Database Performance**
   - Query execution time
   - Connection pool utilization
   - Slow query log

---

## Azure-Specific Recommendations

### App Service Plan Sizing

For high user loads, recommended minimum:

| Users     | App Service Plan | vCPU | RAM  | DTU   | Workers |
|-----------|------------------|------|------|-------|---------|
| 1-50      | B1               | 1    | 1.75 | Basic | 3       |
| 50-200    | S1               | 1    | 1.75 | S0    | 3       |
| 200-500   | S2               | 2    | 3.5  | S1    | 5       |
| 500-1000  | S3               | 4    | 7    | S2    | 9       |
| 1000+     | P1V2+            | 2+   | 8+   | S3+   | 5+      |

### Auto-scaling Rules

Configure auto-scaling in Azure:

```json
{
  "rules": [
    {
      "metricTrigger": {
        "metricName": "CpuPercentage",
        "operator": "GreaterThan",
        "threshold": 70,
        "timeAggregation": "Average",
        "timeWindow": "PT5M"
      },
      "scaleAction": {
        "direction": "Increase",
        "type": "ChangeCount",
        "value": 1,
        "cooldown": "PT5M"
      }
    },
    {
      "metricTrigger": {
        "metricName": "CpuPercentage",
        "operator": "LessThan",
        "threshold": 30,
        "timeAggregation": "Average",
        "timeWindow": "PT5M"
      },
      "scaleAction": {
        "direction": "Decrease",
        "type": "ChangeCount",
        "value": 1,
        "cooldown": "PT5M"
      }
    }
  ],
  "enabled": true,
  "profiles": [
    {
      "name": "Auto scale",
      "capacity": {
        "minimum": "2",
        "maximum": "10",
        "default": "2"
      }
    }
  ]
}
```

### Application Settings (Environment Variables)

Configure in Azure Portal → App Service → Configuration:

```bash
# Database
DATABASE_URL=mssql+pyodbc://...

# Redis
REDIS_URL=rediss://...

# Gunicorn
GUNICORN_WORKERS=5
WORKER_CONNECTIONS=1000

# Session
SECRET_KEY=<generate-strong-key>
SESSION_COOKIE_SECURE=true

# SMTP (if using)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=noreply@company.com
SMTP_PASSWORD=<app-password>
SMTP_USE_TLS=true

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

### Startup Command

In Azure App Service → Configuration → General settings:

```bash
gunicorn --worker-class eventlet --workers 4 --worker-connections 1000 --bind 0.0.0.0:8000 --timeout 120 app:app
```

Or create `startup.sh`:

```bash
#!/bin/bash
python -m pip install --upgrade pip
pip install -r requirements.txt
gunicorn -c gunicorn_config.py app:app
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Create `gunicorn_config.py` with appropriate worker settings
- [ ] Configure database connection pooling in `config.py`
- [ ] Set up Redis for sessions and rate limiting
- [ ] Configure CORS for SocketIO (remove `*`)
- [ ] Set up Azure Application Insights
- [ ] Configure environment variables in Azure
- [ ] Enable Web Sockets in Azure App Service

### Infrastructure
- [ ] Provision Azure SQL Database (S1 or higher for 200+ users)
- [ ] Provision Azure Redis Cache (Basic or Standard)
- [ ] Configure Azure CDN for static files (optional but recommended)
- [ ] Set up Azure Application Gateway or Traffic Manager for HA (if needed)
- [ ] Configure auto-scaling rules

### Application
- [ ] Update `DATABASE_URL` to Azure SQL connection string
- [ ] Update `REDIS_URL` to Azure Redis connection string
- [ ] Set strong `SECRET_KEY`
- [ ] Configure SMTP settings
- [ ] Enable Application Insights
- [ ] Set up health check endpoint monitoring

### Testing
- [ ] Load test with expected user count
- [ ] Test WebSocket connections under load
- [ ] Verify session persistence across workers
- [ ] Test database connection pooling
- [ ] Verify rate limiting works across workers
- [ ] Test reveal animation with 50+ concurrent users
- [ ] Monitor resource usage during peak load

### Monitoring
- [ ] Set up alerts for high CPU/memory
- [ ] Set up alerts for error rate > 1%
- [ ] Set up alerts for slow response times
- [ ] Configure log retention
- [ ] Set up dashboard for key metrics

### Security
- [ ] Enable HTTPS only
- [ ] Configure firewall rules for Azure SQL
- [ ] Restrict Redis access to App Service
- [ ] Set up Azure Key Vault for secrets (recommended)
- [ ] Configure security headers
- [ ] Enable Azure DDoS protection

---

## Performance Testing

### Load Testing with Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class SecretSantaUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        # Login
        self.client.post("/login", {
            "email": "test@example.com",
            "emp_id": "EMP001"
        })
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/dashboard")
    
    @task(1)
    def view_reveal(self):
        self.client.get("/reveal")
    
    @task(2)
    def chat(self):
        self.client.get("/chat")
```

**Run load test:**
```bash
locust -f locustfile.py --host=https://your-app.azurewebsites.net --users 100 --spawn-rate 10
```

### Expected Performance Targets

| Metric                     | Target          |
|----------------------------|-----------------|
| Homepage load time         | < 500ms         |
| Dashboard load time        | < 1s            |
| Reveal animation start     | < 2s            |
| WebSocket connection       | < 500ms         |
| API response time          | < 200ms         |
| Concurrent users supported | 500+            |
| Error rate                 | < 0.1%          |

---

## Common Issues and Solutions

### Issue 1: "Not everyone gets the spin wheel"

**Root Causes:**
1. Worker process crashes under load
2. Static files (JS/CSS) not loading
3. WebSocket connections failing
4. Session lost during reveal

**Solutions:**
- Increase workers and worker connections
- Serve static files via CDN or Nginx
- Configure WebSocket properly in Azure
- Use Redis for session management

### Issue 2: "Website crashes"

**Root Causes:**
1. Single worker can't handle load
2. Database connection pool exhausted
3. Memory leak in long-running workers
4. Unhandled exceptions in async code

**Solutions:**
- Use multiple workers with auto-restart
- Configure proper connection pooling
- Set `max_requests` to restart workers periodically
- Add exception handling to SocketIO events

### Issue 3: "Slow page loads"

**Root Causes:**
1. Database queries not optimized
2. Static files served by Flask
3. No caching
4. Synchronous email sending

**Solutions:**
- Add database indexes
- Use CDN for static files
- Implement Redis caching
- Send emails asynchronously (Celery)

### Issue 4: "Users logged out randomly"

**Root Causes:**
1. Cookie sessions don't work across workers
2. Session timeout too short
3. Worker restarts clear sessions

**Solutions:**
- Use Redis for session storage
- Increase session lifetime
- Use `preload_app` in Gunicorn

---

## Summary

The main issues causing crashes with high user loads are:

1. **No production server** - Must use Gunicorn with eventlet workers
2. **No worker configuration** - Single worker can't handle 20+ users
3. **Poor database pooling** - Connection exhaustion with Azure SQL
4. **Static file serving** - Workers blocked serving CSS/JS
5. **In-memory sessions** - Don't work across workers
6. **In-memory rate limiting** - Not shared across workers
7. **CORS misconfiguration** - Performance and security issue

**Critical Actions (In Order):**

1. ✅ **Create `gunicorn_config.py`** with 4-5 workers
2. ✅ **Configure database pooling** in `config.py`
3. ✅ **Set up Redis** for sessions and rate limiting
4. ✅ **Enable WebSockets** in Azure App Service
5. ✅ **Use CDN or Nginx** for static files
6. ✅ **Configure monitoring** with Application Insights
7. ✅ **Load test** before production deployment

With these configurations, the application should easily handle 500+ concurrent users without crashes.

---

**Need help implementing?** Follow the deployment checklist and test incrementally with increasing load.
