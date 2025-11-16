"""
Test script to verify offline mode configuration
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("LiquidSuite Configuration Test")
print("=" * 60)
print()

# Check environment variables
offline_mode = os.environ.get('OFFLINE_MODE', 'not set')
flask_env = os.environ.get('FLASK_ENV', 'not set')
flask_app = os.environ.get('FLASK_APP', 'not set')

print(f"OFFLINE_MODE: {offline_mode}")
print(f"FLASK_ENV: {flask_env}")
print(f"FLASK_APP: {flask_app}")
print()

# Test config loading
from config import Config

print("Configuration Test:")
print(f"  OFFLINE_MODE setting: {Config.OFFLINE_MODE}")
print(f"  Database URI: {Config.SQLALCHEMY_DATABASE_URI}")
print()

if Config.OFFLINE_MODE:
    print("✅ OFFLINE MODE is configured correctly!")
    print(f"   Using SQLite at: {Config.SQLITE_DB_PATH}")
else:
    print("⚠️  ONLINE MODE is active")
    print("   PostgreSQL is required")

print()
print("=" * 60)
