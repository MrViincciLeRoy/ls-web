"""
Quick Database Initialization Script for LiquidSuite Offline Mode
Run this script to create all database tables and seed initial data
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("LiquidSuite Database Initialization")
print("=" * 60)
print()

# Import after loading env vars
from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import User, TransactionCategory

# Create app
app = create_app('development')

with app.app_context():
    print("Step 1: Creating database tables...")
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        exit(1)
    
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
    
    print()
    print("Step 3: Create admin user (optional)")
    create_user = input("Do you want to create an admin user now? (y/n): ").lower()
    
    if create_user == 'y':
        import getpass
        
        print()
        email = input('Admin email: ').strip()
        username = input('Admin username: ').strip()
        password = getpass.getpass('Admin password: ')
        password_confirm = getpass.getpass('Confirm password: ')
        
        if password != password_confirm:
            print("❌ Passwords don't match!")
        elif not email or not username or not password:
            print("❌ All fields are required!")
        elif User.query.filter_by(email=email).first():
            print(f"❌ User with email {email} already exists!")
        elif User.query.filter_by(username=username).first():
            print(f"❌ User with username {username} already exists!")
        else:
            try:
                user = User(
                    email=email,
                    username=username,
                    is_admin=True,
                    is_active=True
                )
                user.set_password(password)
                
                db.session.add(user)
                db.session.commit()
                
                print(f"✅ Admin user '{username}' created successfully!")
            except Exception as e:
                print(f"❌ Error creating user: {e}")
                db.session.rollback()
    else:
        print("⏭️  Skipped user creation. You can create one later with:")
        print("   python app.py create-admin")
    
    print()
    print("=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    print()
    print("Database location:")
    print(f"   {db.engine.url}")
    print()
    print("You can now start the application with:")
    print("   python app.py")
    print()
    print("Then open your browser to: http://localhost:5000")
    print("=" * 60)
