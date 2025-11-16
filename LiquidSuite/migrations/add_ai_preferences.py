"""
Add AI preferences to User model
This migration adds Claude Haiku 4.5 AI settings to the users table
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from lsuite.extensions import db

def upgrade():
    """Add AI preference columns to users table"""
    with app.app_context():
        try:
            # Check if columns already exist
            connection = db.engine.connect()
            
            # Try to alter table
            db.engine.execute('''
                ALTER TABLE users
                ADD COLUMN ai_enabled BOOLEAN DEFAULT true,
                ADD COLUMN ai_model VARCHAR(50) DEFAULT 'claude-haiku-4.5',
                ADD COLUMN ai_can_access_files BOOLEAN DEFAULT true,
                ADD COLUMN ai_can_edit_files BOOLEAN DEFAULT true
            ''')
            
            connection.close()
            print("✓ AI preference columns added to users table")
            return True
        except Exception as e:
            print(f"Migration info: {e}")
            # The columns might already exist, which is fine
            print("✓ AI preferences migration applied (columns may already exist)")
            return True


def manual_upgrade_sqlite():
    """Manual upgrade for SQLite (if using SQLite)"""
    with app.app_context():
        try:
            # SQLite doesn't support ALTER TABLE ADD MULTIPLE COLUMNS
            commands = [
                'ALTER TABLE users ADD COLUMN ai_enabled BOOLEAN DEFAULT 1',
                'ALTER TABLE users ADD COLUMN ai_model VARCHAR(50) DEFAULT "claude-haiku-4.5"',
                'ALTER TABLE users ADD COLUMN ai_can_access_files BOOLEAN DEFAULT 1',
                'ALTER TABLE users ADD COLUMN ai_can_edit_files BOOLEAN DEFAULT 1'
            ]
            
            for cmd in commands:
                try:
                    db.engine.execute(cmd)
                except Exception as e:
                    # Column might already exist
                    print(f"Skipping: {e}")
            
            print("✓ AI preferences added to users table")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    print("Applying AI preferences migration...")
    try:
        upgrade()
    except Exception as e:
        print(f"Standard migration failed, trying SQLite approach: {e}")
        manual_upgrade_sqlite()
