# Configuration Reference for Production Deployment
# 
# This file shows the recommended configuration settings that should be added
# to config.py for production deployment with high user loads.
#
# DO NOT replace your config.py with this file - use it as a reference to
# update your existing config.py with the production settings below.

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # =============================================================================
    # BASIC FLASK CONFIGURATION
    # =============================================================================
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    
    # File upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Application settings
    GIFT_BUDGET = int(os.environ.get('GIFT_BUDGET', 1500))
    COMPANY_DOMAIN = os.environ.get('COMPANY_DOMAIN')  # e.g., '@company.com'
    
    # =============================================================================
    # DATABASE CONFIGURATION (PRODUCTION)
    # =============================================================================
    
    # Database URL - supports both SQLite (dev) and Azure SQL (production)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection Pool Settings (Critical for Azure SQL and high loads)
    SQLALCHEMY_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 10))
    SQLALCHEMY_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', 30))
    SQLALCHEMY_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 20))
    SQLALCHEMY_POOL_PRE_PING = True  # Test connections before using
    
    # Engine options for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,              # Verify connections are alive
        'pool_recycle': 3600,               # Recycle connections after 1 hour
        'pool_size': 10,                    # Number of connections to maintain
        'max_overflow': 20,                 # Additional connections when pool is full
        'pool_timeout': 30,                 # Seconds to wait for a connection
        'echo': False,                      # Don't log all SQL statements
        'echo_pool': False,                 # Don't log pool checkouts/checkins
        'connect_args': {
            'connect_timeout': 30,          # Connection timeout in seconds
            'application_name': 'SecretSanta'  # Shows in Azure SQL monitoring
        }
    }
    
    # =============================================================================
    # SESSION MANAGEMENT (PRODUCTION)
    # =============================================================================
    
    # For production with multiple workers, use Redis for session storage
    # Comment out these lines if you want to use cookie-based sessions (not recommended)
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')  # Use 'redis' in production
    SESSION_PERMANENT = True
    
    # Redis session configuration (uncomment for production)
    # Requires: pip install redis flask-session
    # SESSION_REDIS = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    
    # =============================================================================
    # RATE LIMITING (PRODUCTION)
    # =============================================================================
    
    # For production with multiple workers, use Redis for rate limiting
    # For development, use memory-based rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    
    # Rate limit settings
    RATELIMIT_ENABLED = True
    RATELIMIT_HEADERS_ENABLED = True
    
    # =============================================================================
    # SOCKETIO CONFIGURATION
    # =============================================================================
    
    # SocketIO async mode
    # Use 'eventlet' for production (already set in app.py)
    SOCKETIO_ASYNC_MODE = 'eventlet'
    
    # Message queue for multiple workers (optional but recommended for scale)
    # Requires Redis
    # SOCKETIO_MESSAGE_QUEUE = os.environ.get('REDIS_URL')
    
    # =============================================================================
    # CACHING (PRODUCTION)
    # =============================================================================
    
    # Cache configuration (optional but recommended)
    # Requires: pip install Flask-Caching
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')  # Use 'redis' in production
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))
    
    # Redis cache configuration (uncomment for production)
    # CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # =============================================================================
    # LOGGING (PRODUCTION)
    # =============================================================================
    
    # Log level
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Log format
    LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    
    # =============================================================================
    # SECURITY SETTINGS (PRODUCTION)
    # =============================================================================
    
    # Force HTTPS in production
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'http')  # Set to 'https' in production
    
    # CORS settings for SocketIO
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '*').split(',')
    
    # Security headers (should be set by reverse proxy/Azure, but good to have)
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
    }
    
    # =============================================================================
    # EMAIL/SMTP CONFIGURATION
    # =============================================================================
    
    # SMTP settings (already handled in your app)
    # These are loaded from environment or database
    SMTP_TIMEOUT = int(os.environ.get('SMTP_TIMEOUT', 30))
    SMTP_RETRY_ATTEMPTS = int(os.environ.get('SMTP_RETRY_ATTEMPTS', 3))
    
    # =============================================================================
    # PERFORMANCE SETTINGS
    # =============================================================================
    
    # Compress responses (optional)
    # Requires: pip install Flask-Compress
    # COMPRESS_MIMETYPES = ['text/html', 'text/css', 'text/xml', 'application/json', 'application/javascript']
    # COMPRESS_LEVEL = 6
    # COMPRESS_MIN_SIZE = 500
    
    # =============================================================================
    # MONITORING (PRODUCTION)
    # =============================================================================
    
    # Application Insights (Azure)
    APPLICATIONINSIGHTS_CONNECTION_STRING = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
    
    # Enable or disable certain features based on environment
    TESTING = os.environ.get('TESTING', 'false').lower() == 'true'
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Log SQL queries in development


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Force HTTPS
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'
    
    # Use Redis for everything in production
    SESSION_TYPE = 'redis'
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    CACHE_TYPE = 'redis'
    
    # Stricter security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)  # Shorter sessions in prod


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================

"""
To use this configuration:

1. Update your config.py with the settings above

2. Set environment variables in Azure App Service or .env file:

   # Environment
   FLASK_ENV=production
   
   # Database
   DATABASE_URL=mssql+pyodbc://...
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=20
   
   # Redis (for sessions, rate limiting, caching)
   REDIS_URL=rediss://...
   
   # Session
   SESSION_TYPE=redis
   SESSION_COOKIE_SECURE=true
   
   # Security
   SECRET_KEY=your-secret-key-here
   PREFERRED_URL_SCHEME=https
   CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   
   # Application
   GIFT_BUDGET=1500
   COMPANY_DOMAIN=@yourcompany.com
   
   # Monitoring
   APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
   
   # Logging
   LOG_LEVEL=INFO

3. Update app.py to use the config:

   from config import config
   
   env = os.environ.get('FLASK_ENV', 'development')
   app.config.from_object(config[env])

4. For production deployment, ensure you have:
   - gunicorn_config.py (provided)
   - Redis instance (Azure Redis Cache)
   - Azure SQL Database
   - Application Insights (optional but recommended)

5. Install additional dependencies if using optional features:

   pip install Flask-Caching  # For caching
   pip install Flask-Session  # For Redis sessions
   pip install redis          # For Redis connection
   pip install Flask-Compress # For response compression
   pip install opencensus-ext-azure  # For Application Insights
"""

# =============================================================================
# WORKER CALCULATION HELPER
# =============================================================================

def calculate_workers(cpu_cores):
    """
    Calculate optimal number of Gunicorn workers
    Formula: (2 × CPU cores) + 1
    """
    return (2 * cpu_cores) + 1


def calculate_db_pool(workers, connections_per_worker=2):
    """
    Calculate database connection pool size
    Formula: workers × connections_per_worker
    """
    pool_size = workers * connections_per_worker
    max_overflow = pool_size  # Same as pool size for overflow
    return pool_size, max_overflow


# Example calculations for different Azure App Service Plans:
"""
B1 (1 core, 1.75 GB):
  Workers: 3
  DB Pool: 6, Max Overflow: 6
  
S1 (1 core, 1.75 GB):
  Workers: 3
  DB Pool: 6, Max Overflow: 6
  
S2 (2 cores, 3.5 GB):
  Workers: 5
  DB Pool: 10, Max Overflow: 10
  
S3 (4 cores, 7 GB):
  Workers: 9
  DB Pool: 18, Max Overflow: 18
  
P1V2 (1 core, 3.5 GB):
  Workers: 3
  DB Pool: 6, Max Overflow: 6
  
P2V2 (2 cores, 7 GB):
  Workers: 5
  DB Pool: 10, Max Overflow: 10
  
P3V2 (4 cores, 14 GB):
  Workers: 9
  DB Pool: 18, Max Overflow: 18
"""
