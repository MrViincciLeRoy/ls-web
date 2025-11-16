# Bank Account ID Fix - LiquidSuite

## Issue
The Capitec bank statement import was failing with the error:
```
psycopg2.errors.NotNullViolation: null value in column "bank_account_id" 
of relation "bank_transactions" violates not-null constraint
```

## Root Cause
When parsing bank statements from PDF attachments, the system was creating `BankTransaction` records without assigning a `bank_account_id`. The database constraint requires this field to be non-null, causing insert operations to fail.

## Solution
The fix involves three changes:

### 1. **Updated Model** (`lsuite/models.py`)
- Changed `bank_account_id` column to explicitly allow NULL for backward compatibility:
  ```python
  bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=True)
  ```

### 2. **Enhanced Gmail Service** (`lsuite/gmail/services.py`)
- Modified `download_and_parse_pdf()` method to:
  - Find existing bank accounts by `bank_name`
  - Automatically create new bank accounts if they don't exist
  - Assign the `bank_account_id` to each transaction
  
  ```python
  # Find or create bank account for this statement
  bank_account = BankAccount.query.filter_by(
      user_id=statement.user_id,
      bank_name=statement.bank_name
  ).first()
  
  if not bank_account:
      bank_account = BankAccount(
          user_id=statement.user_id,
          account_name=f"{statement.bank_name.title()} Account",
          bank_name=statement.bank_name,
          currency='ZAR',
          is_active=True
      )
      db.session.add(bank_account)
      db.session.flush()
  
  # Create transaction with bank_account_id
  transaction = BankTransaction(
      user_id=statement.user_id,
      bank_account_id=bank_account.id,  # ← Now assigned
      statement_id=statement.id,
      ...
  )
  ```

### 3. **Migration Script** (`scripts/fix_bank_account_id.py`)
- Fixes existing transactions with NULL `bank_account_id` values
- Creates necessary bank accounts for each user
- Usage:
  ```bash
  python scripts/fix_bank_account_id.py
  ```

## How It Works

### Automatic Account Creation
When a statement is parsed:
1. The system checks if a bank account exists for that bank and user
2. If not found, it automatically creates one with:
   - Account name: "{Bank Name} Account" (e.g., "Capitec Account")
   - Bank name: From statement (capitec, tymebank, etc.)
   - Currency: ZAR (South African Rand)
   - Active: True

### Transaction Processing
Each transaction now includes:
- User ID (from statement)
- Bank Account ID (linked or newly created)
- Statement ID (source statement)
- Transaction details (date, description, amounts, etc.)

## Testing the Fix

### Step 1: Run Migration Script
```bash
cd c:\Users\tv work\Documents\LiquidSuite-main\LiquidSuite-main\LiquidSuite
python scripts/fix_bank_account_id.py
```

### Step 2: Re-import Statements
1. Go to Gmail → Credentials
2. Select your Gmail account
3. Click "Fetch Statements"
4. Select the Capitec statement
5. Click "Parse PDF"

### Step 3: Verify
- Navigate to Bridge → Categories
- You should see transactions listed without errors
- Check "Statement Details" for proper categorization

## Files Modified
- `lsuite/models.py` - Updated BankTransaction model
- `lsuite/gmail/services.py` - Enhanced transaction creation logic
- `scripts/fix_bank_account_id.py` - New migration script (created)

## Supported Banks
- Capitec (`capitec`)
- Tyme Bank (`tymebank`)
- Other generic PDFs (`other`)

## Notes
- All amounts are stored with 2 decimal places
- Currency defaults to ZAR (South African Rand)
- Duplicate statements are prevented using `gmail_id`
- Bank accounts are user-specific (each user has their own accounts)

## Future Improvements
- Add ability to map parsed statements to existing bank accounts
- Support for multiple accounts per bank
- Account reconciliation features
- Multi-currency support
