"""
IMPROVED PDF Parser - Better Capitec transaction extraction
This file contains the fixed _parse_capitec method
"""
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_capitec_improved(text):
    """
    Improved Capitec PDF parser that handles:
    - Transactions without amounts (Insufficient Funds notices)
    - Better multi-line transaction handling
    - More accurate category extraction
    - Proper fee handling
    """
    transactions = []
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines, headers, and summary sections
        if (not line or 
            'Transaction History' in line or 
            'Money In' in line or 'Money Out' in line or
            'Date Description Category' in line or
            '* Includes VAT' in line or
            'Spending Summary' in line or
            'Fee Summary' in line or
            'Page of' in line):
            i += 1
            continue
        
        # Look for date at start: DD/MM/YYYY
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
        
        if date_match:
            try:
                date_str = date_match.group(1)
                rest_of_line = date_match.group(2).strip()
                
                # Parse date
                trans_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                
                # Check if this is just a notification line (no amounts)
                # These typically end with a reference number in parentheses
                # Example: "Recurring Transfer Insufficient Funds of R1 000.00 (16916070)"
                if (('insufficient funds' in rest_of_line.lower() or 
                     'authentication fee' in rest_of_line.lower()) and
                    not re.search(r'\d+\.\d{2}\s+\d+\.\d{2}\s*$', rest_of_line)):
                    # This is a notification, skip it
                    logger.debug(f"Skipping notification: {rest_of_line[:50]}")
                    i += 1
                    continue
                
                # Try to extract amounts from current line
                # Capitec format: Description [Category] [Amount1] [Amount2] [Amount3]
                # where amounts can be: transaction_amount, fee (optional), balance
                
                # Pattern 1: Three numbers at end (transaction, fee, balance)
                three_amounts = re.search(
                    r'(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s*$',
                    rest_of_line
                )
                
                # Pattern 2: Two numbers at end (transaction/fee, balance)
                two_amounts = re.search(
                    r'(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s*$',
                    rest_of_line
                )
                
                trans_amount = 0.0
                fee = 0.0
                balance = 0.0
                description = ""
                category = ""
                
                if three_amounts:
                    # Three amounts: description category amount fee balance
                    desc_and_cat = three_amounts.group(1).strip()
                    amount_str = three_amounts.group(2).strip()
                    fee_str = three_amounts.group(3).strip()
                    balance_str = three_amounts.group(4).strip()
                    
                    trans_amount = parse_amount(amount_str)
                    fee = abs(parse_amount(fee_str))  # Fees are always positive
                    balance = parse_amount(balance_str)
                    
                    description, category = extract_description_and_category(desc_and_cat)
                    
                elif two_amounts:
                    # Two amounts: could be (amount, balance) or (fee, balance)
                    desc_and_cat = two_amounts.group(1).strip()
                    amount1_str = two_amounts.group(2).strip()
                    amount2_str = two_amounts.group(3).strip()
                    
                    amount1 = parse_amount(amount1_str)
                    balance = parse_amount(amount2_str)
                    
                    # Determine if amount1 is transaction or fee
                    if 'fee' in desc_and_cat.lower():
                        fee = abs(amount1)
                        trans_amount = fee  # For fee-only transactions
                    else:
                        trans_amount = amount1
                        fee = 0.0
                    
                    description, category = extract_description_and_category(desc_and_cat)
                    
                else:
                    # No amounts on this line - might be notification or multi-line
                    # Skip notifications
                    i += 1
                    continue
                
                # Determine transaction type
                is_credit = determine_if_credit(description, trans_amount, category)
                
                # Use absolute value for amount
                trans_amount = abs(trans_amount)
                
                # Only add if we have a valid transaction
                if trans_amount > 0 and len(description) >= 3:
                    transactions.append({
                        'date': trans_date,
                        'description': description,
                        'amount': trans_amount,
                        'type': 'credit' if is_credit else 'debit',
                        'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}",
                        'category': category,
                        'fee': fee,
                        'balance': balance
                    })
                    logger.debug(f"✓ Parsed: {trans_date} | {description[:40]} | R{trans_amount} | {'CR' if is_credit else 'DR'}")
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse line: {line[:80]} | Error: {e}")
        
        i += 1
    
    logger.info(f"✓ Successfully parsed {len(transactions)} Capitec transactions")
    return transactions


def parse_amount(amount_str):
    """Parse amount string to float"""
    if not amount_str or amount_str == '-':
        return 0.0
    try:
        cleaned = amount_str.replace(',', '').replace(' ', '').strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0


def extract_description_and_category(text):
    """
    Extract description and category from combined text
    Categories appear at the end and are capitalized
    """
    # Known Capitec categories
    categories = [
        'Other Income', 'Investment Income', 'Transfer', 'Cash Withdrawal',
        'Digital Payments', 'Cellphone', 'Groceries', 'Takeaways', 
        'Online Store', 'Furniture & Appliances', 'Uncategorised',
        'Investments', 'Savings', 'Fees', 'Interest', 'Alcohol',
        'Other Personal & Family'
    ]
    
    # Check if text ends with a category
    for cat in categories:
        if text.endswith(cat):
            description = text[:-(len(cat))].strip()
            return description, cat
    
    # No category found
    return text, 'Uncategorised'


def determine_if_credit(description, amount, category):
    """Determine if transaction is a credit (incoming) or debit (outgoing)"""
    desc_lower = description.lower()
    cat_lower = category.lower() if category else ''
    
    # Strong credit indicators
    credit_keywords = [
        'payment received', 'received', 'payshap payment received',
        'deposit', 'interest received', 'transfer received', 'refund',
        'dispute', 'set-off applied'
    ]
    
    # Strong debit indicators
    debit_keywords = [
        'purchase', 'payment:', 'cash sent', 'cash withdrawal',
        'prepaid purchase', 'voucher purchase', 'debit order',
        'transfer to', 'external payment', 'immediate payment',
        'card replacement', 'admin fee', 'withdrawal', 'capitec pay'
    ]
    
    # Check keywords in description
    if any(kw in desc_lower for kw in credit_keywords):
        return True
    if any(kw in desc_lower for kw in debit_keywords):
        return False
    
    # Check category
    if any(word in cat_lower for word in ['income', 'interest']):
        return True
    if any(word in cat_lower for word in ['withdrawal', 'fees', 'payments']):
        return False
    
    # Fallback: negative amounts are debits
    if amount < 0:
        return False
    
    # Default to debit if unclear
    return False
