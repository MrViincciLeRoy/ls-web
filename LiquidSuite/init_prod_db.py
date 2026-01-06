"""
Production Database Initialization Script for LiquidSuite
Run this script to create all database tables and seed initial data on PostgreSQL
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_database(create_admin=False, admin_email=None, admin_username=None, admin_password=None):
    """Initialize database with optional admin creation"""
    
    print("=" * 60)
    print("LiquidSuite Production Database Initialization")
    print("=" * 60)
    print()

    # Import after loading env vars
    from lsuite import create_app
    from lsuite.extensions import db
    from lsuite.models import User, TransactionCategory

    # Create app
    app = create_app('production')

    with app.app_context():
        print("Step 1: Creating database tables...")
        try:
            db.create_all()
            print("✅ Database tables created successfully!")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False
        
        print()
        print("Step 2: Seeding default transaction categories...")
        
        categories = [
            {
                'name': 'Transport',
                'erpnext_account': 'Transport Expenses - Company',
                'transaction_type': 'expense',
                'keywords': 'uber, bolt, taxi, transport, fuel, petrol'
            },
            {
                'name': 'Food & Beverages',
                'erpnext_account': 'Food Expenses - Company',
                'transaction_type': 'expense',
                'keywords': 'restaurant, coffee, lunch, dinner, food, cafe'
            },
            {
                'name': 'Office Supplies',
                'erpnext_account': 'Office Expenses - Company',
                'transaction_type': 'expense',
                'keywords': 'stationery, office, supplies, printer'
            },
            {
                'name': 'Utilities',
                'erpnext_account': 'Utilities - Company',
                'transaction_type': 'expense',
                'keywords': 'electricity, water, internet, mobile, telkom'
            },
            {
                'name': 'Salary Payment',
                'erpnext_account': 'Salary - Company',
                'transaction_type': 'expense',
                'keywords': 'salary, wages, payment'
            },
            {
                'name': 'Customer Payment',
                'erpnext_account': 'Sales - Company',
                'transaction_type': 'income',
                'keywords': 'payment received, deposit, income'
            },
            {
                'name': 'Bank Transfer',
                'erpnext_account': 'Bank Account - Company',
                'transaction_type': 'transfer',
                'keywords': 'transfer, own account'
            }
        ]
        
        added = 0
        for cat_data in categories:
            if not TransactionCategory.query.filter_by(name=cat_data['name']).first():
                category = TransactionCategory(**cat_data)
                db.session.add(category)
                added += 1
        
        try:
            db.session.commit()
            print(f"✅ Seeded {added} transaction categories!")
        except Exception as e:
            print(f"❌ Error seeding categories: {e}")
            db.session.rollback()
            return False
        
        print()
        
        if create_admin:
            print("Step 3: Creating admin user...")
            
            if not admin_email or not admin_username or not admin_password:
                print("❌ Missing admin credentials!")
                return False
            
            # Check if user already exists
            if User.query.filter_by(email=admin_email).first():
                print(f"ℹ️  User with email {admin_email} already exists. Updating password...")
                user = User.query.filter_by(email=admin_email).first()
                user.set_password(admin_password)
                user.is_admin = True
                user.is_active = True
            elif User.query.filter_by(username=admin_username).first():
                print(f"ℹ️  User with username {admin_username} already exists. Updating password...")
                user = User.query.filter_by(username=admin_username).first()
                user.set_password(admin_password)
                user.is_admin = True
                user.is_active = True
            else:
                user = User(
                    email=admin_email,
                    username=admin_username,
                    is_admin=True,
                    is_active=True
                )
                user.set_password(admin_password)
                db.session.add(user)
            
            try:
                db.session.commit()
                print(f"✅ Admin user '{admin_username}' created/updated successfully!")
                print(f"   Email: {admin_email}")
                print(f"   Username: {admin_username}")
            except Exception as e:
                print(f"❌ Error creating/updating user: {e}")
                db.session.rollback()
                return False
        else:
            print("Step 3: Skipped admin user creation")
        
        print()
        print("=" * 60)
        print("✅ Database initialization complete!")
        print("=" * 60)
        print()
        print("Database connection:")
        print(f"   {db.engine.url}")
        print()
        
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initialize production database')
    parser.add_argument('--create-admin', type=lambda x: x.lower() == 'true', 
                        default=False, help='Create admin user')
    parser.add_argument('--admin-email', type=str, default='admin@lsuite.local',
                        help='Admin email')
    parser.add_argument('--admin-username', type=str, default='admin',
                        help='Admin username')
    parser.add_argument('--admin-password', type=str, default='Admin123!',
                        help='Admin password')
    
    args = parser.parse_args()
    
    success = init_database(
        create_admin=args.create_admin,
        admin_email=args.admin_email,
        admin_username=args.admin_username,
        admin_password=args.admin_password
    )
    
    sys.exit(0 if success else 1)
