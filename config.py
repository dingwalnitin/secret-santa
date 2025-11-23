# config.py
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    SQLALCHEMY_DATABASE_URI = (
        "mssql+pyodbc://santa:1Q2w1q2w@santa.database.windows.net:1433/santabase"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&Encrypt=yes"
        "&TrustServerCertificate=no"
        "&Connection Timeout=30"
        "&MARS_Connection=yes"
    )


    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    
    # File upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Application settings
    GIFT_BUDGET = 1500
    COMPANY_DOMAIN = None  # Set to restrict emails, e.g., '@company.com'
    
    # SocketIO
    SOCKETIO_ASYNC_MODE = 'threading'
