"""
LSuite Configuration - WITH OFFLINE/ONLINE MODE SUPPORT
"""
import os
from datetime import timedelta
from pathlib import Path


class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # ============================================================================
    # DATABASE CONFIGURATION - OFFLINE/ONLINE MODE
    # ============================================================================
    
    # Check for OFFLINE_MODE environment variable (defaults to False = online)
    OFFLINE_MODE = os.environ.get('OFFLINE_MODE', 'false').lower() in ('true', '1', 'yes', 'on')
    
    if OFFLINE_MODE:
        # OFFLINE MODE: Use SQLite (no PostgreSQL needed)
        BASE_DIR = Path(__file__).parent
        SQLITE_DB_PATH = BASE_DIR / 'data' / 'lsuite.db'
        SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{SQLITE_DB_PATH}'
        print(f"🔵 OFFLINE MODE: Using SQLite at {SQLITE_DB_PATH}")
    else:
        # ONLINE MODE: Use PostgreSQL (requires PostgreSQL server)
        database_url = os.environ.get('DATABASE_URL') or 'postgresql://postgres:postgres@localhost:5432/lsuite'
        
        # ✅ CRITICAL FIX: Convert postgres:// to postgresql://
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        SQLALCHEMY_DATABASE_URI = database_url
        print(f"🟢 ONLINE MODE: Using PostgreSQL")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Session
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI') or \
        'http://localhost:5000/gmail/oauth/callback'
    
    # ERPNext
    ERPNEXT_BASE_URL = os.environ.get('ERPNEXT_BASE_URL')
    ERPNEXT_API_KEY = os.environ.get('ERPNEXT_API_KEY')
    ERPNEXT_API_SECRET = os.environ.get('ERPNEXT_API_SECRET')
    
    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Pagination
    ITEMS_PER_PAGE = 50
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'lsuite.log'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # ✅ Disable SQL echo to prevent log flooding
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Force HTTPS in production
    SESSION_COOKIE_SECURE = True
    
    # More strict security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'


class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    
    # Always use SQLite for tests (offline mode)
    OFFLINE_MODE = True
    BASE_DIR = Path(__file__).parent
    SQLITE_DB_PATH = BASE_DIR / 'data' / 'test_lsuite.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{SQLITE_DB_PATH}'
    SQLALCHEMY_ECHO = False
    
    # Test-specific settings
    ITEMS_PER_PAGE = 10
    SECRET_KEY = 'test-secret-key-for-testing-only'
    
    # Disable external services in tests
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True


# Update config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}
