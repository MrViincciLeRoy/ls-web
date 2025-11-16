# Capitec Bank Statement Parser

## Overview

This specialized parser extracts transactions from Capitec Bank PDF statements with full support for:
- **Transaction Categories** - Capitec's built-in categorization (Groceries, Cellphone, etc.)
- **Credit/Debit Detection** - Accurately identifies whether transactions are credits or debits
- **Balance Tracking** - Maintains running balance for each transaction
- **Fee Handling** - Separates fees as distinct transactions
- **Chronological Ordering** - Sorts transactions correctly using balance

## Features

### 1. Category Extraction
The parser automatically extracts Capitec's transaction categories:
- Other Income
- Investment Income
- Transfer
- Cash Withdrawal
- Digital Payments
- Cellphone
- Groceries
- Takeaways
- Online Store
- Furniture & Appliances
- Fees
- Interest
- And many more...

Categories are stored in the transaction's `notes` field as "Category: [name]".

### 2. Credit vs Debit Detection
The parser intelligently determines whether a transaction is a credit or debit by analyzing:
- **Keywords in description**: "payment received", "deposit", "withdrawal", "purchase", etc.
- **Category context**: "Income" categories are credits, "Fees" categories are debits
- **Transaction patterns**: Capitec-specific transaction types

This ensures:
- Credits show in the `deposit` field
- Debits show in the `withdrawal` field
- Balance calculations are accurate

### 3. Balance Tracking
Each transaction includes the account balance after the transaction:
- Used for chronological sorting
- Helps verify transaction accuracy
- Stored in the `balance` field

### 4. Fee Handling
Transaction fees are handled as separate entries:
- Main transaction and fee both recorded
- Fee transactions marked with "(Fee)" in description
- Fee category set to "Fees"
- Both transactions maintain proper balance

## Usage

### Basic Usage

```python
from lsuite.gmail.parsers_capitec import CapitecPDFParser

# Create parser
parser = CapitecPDFParser()

# Read PDF file
with open('statement.pdf', 'rb') as f:
    pdf_data = f.read()

# Parse PDF
result = parser.parse_pdf(pdf_data, password='optional_password')

# Access results
transactions = result['transactions']
statement_info = result['statement_info']

# Each transaction contains:
# - date: Transaction date
# - description: Transaction description
# - amount: Transaction amount (always positive)
# - type: 'credit' or 'debit'
# - category: Capitec category (or None)
# - balance: Account balance after transaction
# - fee: Associated fee amount (0 if no fee)
# - reference: Transaction reference
```

### Testing the Parser

Run the test script to verify parsing:

```bash
# Without password
python test_capitec_parser.py data/capitec_statement.pdf

# With password
python test_capitec_parser.py data/capitec_statement.pdf mypassword
```

The test script will display:
- Statement information (account number, period, balances)
- All transactions grouped by date
- Transaction totals (credits, debits, net)
- Category breakdown with counts and amounts

### Integration with LiquidSuite

The parser is automatically used when:
1. **Uploading PDF manually**: Select "Capitec" as bank name
2. **Importing from Gmail**: Capitec statements detected automatically
3. **Parsing existing statements**: Re-parse uses new Capitec parser

## Transaction Format

### Input (Capitec PDF)
```
01/10/2024 Purchase at Pick n Pay R500.00 R50.00 R4,500.00 Groceries
```

### Output (Parsed Transaction)
```python
{
    'date': datetime.date(2024, 10, 1),
    'description': 'Purchase at Pick n Pay',
    'amount': 500.00,
    'type': 'debit',
    'category': 'Groceries',
    'fee': 50.00,
    'balance': 4500.00,
    'reference': 'CAP-20241001'
}
```

### Database Storage
```
BankTransaction:
  date: 2024-10-01
  description: "Purchase at Pick n Pay"
  withdrawal: 500.00
  deposit: 0.00
  balance: 4500.00
  notes: "Category: Groceries"
```

## Credit/Debit Detection Rules

### Credits (Deposits)
Identified by:
- Keywords: "payment received", "deposit", "interest", "refund", "reversal"
- Categories: "Other Income", "Investment Income", "Interest"
- Positive flow indicators

### Debits (Withdrawals)
Identified by:
- Keywords: "purchase", "withdrawal", "payment:", "fee", "charge"
- Categories: "Fees", "Cash Withdrawal", "Groceries", "Digital Payments"
- Negative flow indicators

### Examples

| Description | Category | Type |
|-------------|----------|------|
| PayShap Payment Received | Other Income | CREDIT |
| Interest Earned | Interest | CREDIT |
| Purchase at Shoprite | Groceries | DEBIT |
| Cash Withdrawal ATM | Cash Withdrawal | DEBIT |
| Capitec Pay Transaction | Digital Payments | DEBIT |
| Monthly Admin Fee | Fees | DEBIT |

## Supported Transaction Patterns

### Pattern 1: Three Amounts (Main + Fee + Balance)
```
01/10/2024 Transaction Description 500.00 10.00 4,500.00
           ↓                        ↓       ↓     ↓
           Date                     Amount  Fee   Balance
```

### Pattern 2: Two Amounts (Amount + Balance)
```
01/10/2024 Transaction Description 500.00 4,500.00
           ↓                        ↓       ↓
           Date                     Amount  Balance
```

### Pattern 3: Multi-line Transaction
```
01/10/2024 Long Transaction Description
           That Spans Multiple Lines
           500.00 10.00 4,500.00
```

## Balance-Based Sorting

Transactions are sorted chronologically using:
1. **Date** (newest first)
2. **Balance** (lowest first within same date)

This ensures:
- Multiple transactions on same day are in correct order
- Matches the exact order shown in Capitec PDF
- Balance decreases through the day (debits reduce balance)

## Category Mapping

For ERPNext integration, categories can be mapped to accounts:

| Capitec Category | Suggested ERPNext Account |
|-----------------|---------------------------|
| Groceries | 5100 - Groceries Expense |
| Cellphone | 5200 - Telecom Expense |
| Fees | 5900 - Bank Charges |
| Interest | 4100 - Interest Income |
| Other Income | 4000 - Other Income |
| Digital Payments | 5000 - General Expenses |

## Error Handling

The parser handles:
- **Password-protected PDFs**: Provide password parameter
- **Multi-line descriptions**: Automatically combines lines
- **Missing amounts**: Skips invalid entries with warning
- **Malformed dates**: Logs error and continues
- **Unknown categories**: Sets category to None

## Logging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Logs include:
- Extraction progress
- Transaction parsing details
- Category detection
- Balance tracking
- Error messages

## Comparison with Generic Parser

### Capitec Parser Advantages
✅ Extracts transaction categories  
✅ Accurate credit/debit detection  
✅ Balance tracking per transaction  
✅ Fee separation  
✅ Capitec-specific patterns  
✅ Better handling of multi-line transactions  

### Generic Parser
❌ No category extraction  
❌ Basic credit/debit heuristics  
❌ No balance tracking  
❌ Fees mixed with main transactions  
❌ Generic patterns only  

## Future Enhancements

Planned features:
- [ ] Automatic category-to-ERPNext account mapping
- [ ] Transaction tagging based on patterns
- [ ] Merchant name extraction
- [ ] Duplicate detection using balance
- [ ] Monthly spending analysis by category
- [ ] Budget tracking per category

## Troubleshooting

### No transactions extracted
- Check PDF password is correct
- Verify PDF is a Capitec statement
- Enable debug logging to see parsing details

### Wrong credit/debit classification
- Check transaction description for keywords
- Verify category detection
- Report issue with transaction details

### Missing categories
- Some transactions may not have categories in PDF
- Check notes field for category information
- Default behavior: category = None

### Balance mismatches
- Verify all transactions parsed correctly
- Check for duplicate transactions
- Compare with PDF statement totals

## Support

For issues or questions:
1. Enable debug logging
2. Run test_capitec_parser.py
3. Check parser logs
4. Verify PDF format matches expected Capitec format

## Files

- `lsuite/gmail/parsers_capitec.py` - Main Capitec parser
- `lsuite/gmail/services.py` - Integration with Gmail service
- `lsuite/gmail/routes.py` - Web routes for PDF upload
- `test_capitec_parser.py` - Test script
- `CAPITEC_PARSER_README.md` - This documentation
