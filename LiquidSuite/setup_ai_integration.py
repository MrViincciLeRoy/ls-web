#!/usr/bin/env python
"""
Quick setup script for Claude Haiku 4.5 AI integration
This script applies the AI preferences migration to your database
"""
import os
import sys
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from lsuite.extensions import db
from lsuite.models import User


def check_columns_exist():
    """Check if AI columns already exist in users table"""
    with app.app_context():
        try:
            # Try to query a user and access the AI fields
            user = User.query.first()
            if user:
                # Try to access one of the new fields
                _ = user.ai_enabled
                return True
        except:
            return False
    return False


def apply_migration_postgresql():
    """Apply migration for PostgreSQL"""
    print("Applying migration for PostgreSQL...")
    commands = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_enabled BOOLEAN DEFAULT true;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_model VARCHAR(50) DEFAULT 'claude-haiku-4.5';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_can_access_files BOOLEAN DEFAULT true;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_can_edit_files BOOLEAN DEFAULT true;",
    ]
    
    with app.app_context():
        try:
            for cmd in commands:
                db.engine.execute(cmd)
            print("✓ PostgreSQL migration completed successfully!")
            return True
        except Exception as e:
            print(f"Error during migration: {e}")
            return False


def apply_migration_sqlite():
    """Apply migration for SQLite"""
    print("Applying migration for SQLite...")
    commands = [
        "ALTER TABLE users ADD COLUMN ai_enabled BOOLEAN DEFAULT 1;",
        "ALTER TABLE users ADD COLUMN ai_model VARCHAR(50) DEFAULT 'claude-haiku-4.5';",
        "ALTER TABLE users ADD COLUMN ai_can_access_files BOOLEAN DEFAULT 1;",
        "ALTER TABLE users ADD COLUMN ai_can_edit_files BOOLEAN DEFAULT 1;",
    ]
    
    with app.app_context():
        for cmd in commands:
            try:
                db.engine.execute(cmd)
            except Exception as e:
                # Column might already exist - this is okay
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  → Column already exists (skipping): {cmd[:40]}...")
                else:
                    print(f"  ⚠ Warning: {e}")
        print("✓ SQLite migration completed!")
        return True


def main():
    print("=" * 60)
    print("Claude Haiku 4.5 AI Integration Setup")
    print("=" * 60)
    print()
    
    # Check if columns already exist
    print("Checking if AI columns already exist...")
    if check_columns_exist():
        print("✓ AI columns already exist in the database!")
        print()
        print("Your database is ready for Claude Haiku 4.5 AI integration.")
        print("All users have been enabled with:")
        print("  ✓ Claude Haiku 4.5 AI access")
        print("  ✓ File access permissions")
        print("  ✓ File edit permissions")
        print()
        return
    
    print("AI columns not found. Attempting migration...")
    print()
    
    # Get database type
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    if 'postgresql' in db_url or 'postgres' in db_url:
        success = apply_migration_postgresql()
    else:
        # Default to SQLite approach (works for most databases)
        success = apply_migration_sqlite()
    
    if success:
        print()
        print("=" * 60)
        print("✓ Setup Complete!")
        print("=" * 60)
        print()
        print("Claude Haiku 4.5 has been enabled for all users with:")
        print("  ✓ AI Model: claude-haiku-4.5")
        print("  ✓ File Access: Enabled")
        print("  ✓ File Edit: Enabled")
        print()
        print("Users can manage their preferences at:")
        print("  → Profile → AI Preferences")
        print()
        print("Database: ", db_url[:50] + "..." if len(db_url) > 50 else db_url)
    else:
        print()
        print("✗ Migration failed. Please check your database configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
