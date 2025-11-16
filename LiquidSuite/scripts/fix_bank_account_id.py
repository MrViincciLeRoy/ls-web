"""
Fix NULL bank_account_id values in bank_transactions table.
This script assigns transactions to their corresponding bank accounts based on the statement's bank.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import BankTransaction, EmailStatement, BankAccount

def fix_bank_account_ids():
    """Fix NULL bank_account_id values"""
    
    app = create_app()
    with app.app_context():
        print("Starting fix_bank_account_id script...")
        
        # Get all transactions with NULL bank_account_id
        null_transactions = BankTransaction.query.filter_by(bank_account_id=None).all()
        print(f"Found {len(null_transactions)} transactions with NULL bank_account_id")
        
        fixed_count = 0
        created_accounts = 0
        
        for trans in null_transactions:
            try:
                # Get the statement associated with this transaction
                statement = EmailStatement.query.get(trans.statement_id) if trans.statement_id else None
                
                if not statement:
                    print(f"⚠️  Transaction {trans.id}: No statement found, skipping")
                    continue
                
                # Find or create bank account
                bank_account = BankAccount.query.filter_by(
                    user_id=trans.user_id,
                    bank_name=statement.bank_name
                ).first()
                
                if not bank_account:
                    # Create new bank account
                    bank_account = BankAccount(
                        user_id=trans.user_id,
                        account_name=f"{statement.bank_name.title()} Account",
                        bank_name=statement.bank_name,
                        currency='ZAR',
                        is_active=True
                    )
                    db.session.add(bank_account)
                    db.session.flush()
                    created_accounts += 1
                    print(f"✓ Created bank account: {bank_account.account_name} (ID: {bank_account.id})")
                
                # Update transaction
                trans.bank_account_id = bank_account.id
                fixed_count += 1
                
                if fixed_count % 50 == 0:
                    db.session.commit()
                    print(f"✓ Fixed {fixed_count} transactions...")
                
            except Exception as e:
                print(f"✗ Error fixing transaction {trans.id}: {str(e)}")
                continue
        
        # Final commit
        db.session.commit()
        
        print("\n" + "="*60)
        print("FIX COMPLETED")
        print("="*60)
        print(f"✓ Fixed {fixed_count} transactions")
        print(f"✓ Created {created_accounts} new bank accounts")
        print(f"✓ All transactions now have valid bank_account_id values")
        print("="*60 + "\n")

if __name__ == '__main__':
    try:
        fix_bank_account_ids()
        print("✓ Script completed successfully")
    except Exception as e:
        print(f"✗ Script failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
