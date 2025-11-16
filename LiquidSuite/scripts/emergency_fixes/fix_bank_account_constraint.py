"""
Emergency fix for bank_account_id NOT NULL constraint issue.
This script will:
1. Drop the NOT NULL constraint on bank_account_id
2. Fix all existing NULL values
3. Optionally re-add the constraint

Run this script: python scripts/emergency_fixes/fix_bank_account_constraint.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import BankTransaction, EmailStatement, BankAccount
from sqlalchemy import text

def drop_not_null_constraint():
    """Drop NOT NULL constraint from bank_account_id"""
    try:
        sql = text("""
            ALTER TABLE bank_transactions 
            ALTER COLUMN bank_account_id DROP NOT NULL;
        """)
        db.session.execute(sql)
        db.session.commit()
        print("✓ Successfully dropped NOT NULL constraint on bank_account_id")
        return True
    except Exception as e:
        print(f"⚠️  Could not drop constraint (it may already be nullable): {str(e)}")
        db.session.rollback()
        return False

def fix_null_bank_account_ids():
    """Fix all transactions with NULL bank_account_id"""
    print("\nFixing transactions with NULL bank_account_id...")
    
    # Get all transactions with NULL bank_account_id
    null_transactions = BankTransaction.query.filter_by(bank_account_id=None).all()
    print(f"Found {len(null_transactions)} transactions with NULL bank_account_id")
    
    if len(null_transactions) == 0:
        print("✓ No NULL bank_account_id values found!")
        return 0
    
    fixed_count = 0
    created_accounts = {}
    
    for trans in null_transactions:
        try:
            # Get the statement associated with this transaction
            statement = EmailStatement.query.get(trans.statement_id) if trans.statement_id else None
            
            if not statement:
                print(f"⚠️  Transaction {trans.id}: No statement found, trying to create default account")
                bank_name = 'unknown'
            else:
                bank_name = statement.bank_name
            
            # Create account key
            account_key = f"{trans.user_id}:{bank_name}"
            
            # Check if we already created this account in this run
            if account_key in created_accounts:
                bank_account = created_accounts[account_key]
            else:
                # Find or create bank account
                bank_account = BankAccount.query.filter_by(
                    user_id=trans.user_id,
                    bank_name=bank_name
                ).first()
                
                if not bank_account:
                    # Create new bank account
                    bank_account = BankAccount(
                        user_id=trans.user_id,
                        account_name=f"{bank_name.title()} Account",
                        bank_name=bank_name,
                        currency='ZAR',
                        is_active=True
                    )
                    db.session.add(bank_account)
                    db.session.flush()
                    created_accounts[account_key] = bank_account
                    print(f"✓ Created bank account: {bank_account.account_name} (ID: {bank_account.id})")
            
            # Update transaction
            trans.bank_account_id = bank_account.id
            fixed_count += 1
            
            if fixed_count % 50 == 0:
                db.session.commit()
                print(f"  Progress: Fixed {fixed_count}/{len(null_transactions)} transactions...")
        
        except Exception as e:
            print(f"✗ Error fixing transaction {trans.id}: {str(e)}")
            db.session.rollback()
            continue
    
    # Final commit
    try:
        db.session.commit()
        print(f"\n✓ Successfully fixed {fixed_count} transactions")
        print(f"✓ Created {len(created_accounts)} new bank accounts")
        return fixed_count
    except Exception as e:
        print(f"✗ Error committing changes: {str(e)}")
        db.session.rollback()
        return 0

def add_not_null_constraint():
    """Re-add NOT NULL constraint (only if all values are fixed)"""
    try:
        # Check if there are any NULL values
        null_count = BankTransaction.query.filter_by(bank_account_id=None).count()
        
        if null_count > 0:
            print(f"\n⚠️  WARNING: Cannot add NOT NULL constraint - {null_count} NULL values still exist")
            return False
        
        sql = text("""
            ALTER TABLE bank_transactions 
            ALTER COLUMN bank_account_id SET NOT NULL;
        """)
        db.session.execute(sql)
        db.session.commit()
        print("\n✓ Successfully added NOT NULL constraint back to bank_account_id")
        return True
    except Exception as e:
        print(f"✗ Could not add NOT NULL constraint: {str(e)}")
        db.session.rollback()
        return False

def verify_fix():
    """Verify that all transactions have bank_account_id"""
    print("\nVerifying fix...")
    
    null_count = BankTransaction.query.filter_by(bank_account_id=None).count()
    total_count = BankTransaction.query.count()
    
    print(f"Total transactions: {total_count}")
    print(f"Transactions with NULL bank_account_id: {null_count}")
    
    if null_count == 0:
        print("✓ All transactions have valid bank_account_id!")
        return True
    else:
        print(f"⚠️  WARNING: {null_count} transactions still have NULL bank_account_id")
        return False

def main():
    """Main function"""
    app = create_app()
    
    with app.app_context():
        print("="*70)
        print("LIQUIDSUITE - EMERGENCY BANK ACCOUNT ID FIX")
        print("="*70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Step 1: Drop NOT NULL constraint
        print("STEP 1: Dropping NOT NULL constraint...")
        drop_not_null_constraint()
        
        # Step 2: Fix NULL values
        print("\nSTEP 2: Fixing NULL bank_account_id values...")
        fixed_count = fix_null_bank_account_ids()
        
        # Step 3: Verify
        print("\nSTEP 3: Verifying fix...")
        all_fixed = verify_fix()
        
        # Step 4: Optionally re-add constraint
        if all_fixed and fixed_count > 0:
            response = input("\n✓ All fixed! Do you want to re-add the NOT NULL constraint? (y/n): ")
            if response.lower() == 'y':
                add_not_null_constraint()
            else:
                print("Skipped re-adding NOT NULL constraint. You can do this manually later.")
        
        print("\n" + "="*70)
        print("FIX COMPLETED")
        print("="*70)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nYou can now try parsing the statement again!")
        print("="*70 + "\n")

if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Script failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
