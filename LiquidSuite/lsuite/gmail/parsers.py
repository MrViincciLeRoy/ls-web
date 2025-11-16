"""
IMPROVED PDF Parser - Extract ALL transactions from bank statement PDFs
Fixed version with proper chronological ordering using balance
"""
import io
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF statement parser with improved Capitec parsing and balance-based ordering"""
    
    def parse_pdf(self, pdf_data, bank_name, password=None):
        """
        Parse PDF and extract transactions
        
        Args:
            pdf_data: Binary PDF data
            bank_name: Bank identifier (tymebank, capitec, other)
            password: PDF password if protected
            
        Returns:
            List of transaction dictionaries sorted chronologically
        """
        text = self._extract_text_from_pdf(pdf_data, password)
        
        # Log extracted text for debugging
        logger.info(f"Extracted text length: {len(text)} characters")
        logger.debug(f"First 500 chars: {text[:500]}")
        
        if bank_name == 'tymebank':
            transactions = self._parse_tymebank(text)
        elif bank_name == 'capitec':
            transactions = self._parse_capitec_improved(text)
        else:
            transactions = self._parse_generic(text)
        
        # Sort transactions chronologically using balance
        return self._sort_by_balance(transactions)
    
    def _sort_by_balance(self, transactions):
        """
        Sort transactions chronologically using date and balance.
        Lower balance = later transaction (balance decreases through the day)
        Matches exact PDF order
        """
        if not transactions:
            return transactions
        
        # Sort by: date (newest first), then balance (lowest first = chronological order)
        sorted_trans = sorted(
            transactions,
            key=lambda x: (
                -x['date'].toordinal(),  # Newest date first
                float(x.get('balance', 0)) if x.get('balance') is not None else 0  # Lowest balance first
            )
        )
        
        logger.info(f"Sorted {len(sorted_trans)} transactions by date and balance")
        return sorted_trans
    
    def _extract_text_from_pdf(self, pdf_data, password=None):
        """Extract text from PDF using available library"""
        text = ""
        
        try:
            # Try PyPDF2 first
            import PyPDF2
            pdf_file = io.BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Handle encrypted PDFs
            if pdf_reader.is_encrypted:
                if not password:
                    raise ValueError("PDF is password protected but no password provided")
                
                decrypt_result = pdf_reader.decrypt(password)
                if decrypt_result == 0:
                    raise ValueError("Incorrect PDF password")
            
            # Extract text from all pages
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            logger.info(f"Extracted {len(text)} characters using PyPDF2")
            
        except ImportError:
            # Fallback to pdfplumber
            try:
                import pdfplumber
                pdf_file = io.BytesIO(pdf_data)
                
                with pdfplumber.open(pdf_file, password=password) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                
                logger.info(f"Extracted {len(text)} characters using pdfplumber")
                
            except ImportError:
                raise ImportError("No PDF library available. Install PyPDF2 or pdfplumber")
        
        return text
    
    def _parse_capitec_improved(self, text):
        """
        IMPROVED Capitec PDF parser - captures ALL transactions
        Maintains proper order using balance field
        """
        transactions = []
        lines = text.split('\n')
        
        def parse_amount(amount_str):
            """Convert amount string to float"""
            if not amount_str or amount_str == '-' or amount_str.strip() == '':
                return 0.0
            try:
                cleaned = amount_str.replace(',', '').replace(' ', '').strip()
                # Handle negative amounts
                if cleaned.startswith('-'):
                    return -float(cleaned[1:])
                return float(cleaned)
            except (ValueError, AttributeError):
                return 0.0
        
        def is_credit_transaction(description, category):
            """Determine if transaction is a credit based on keywords"""
            desc_lower = description.lower()
            cat_lower = (category or '').lower()
            
            # Strong credit indicators
            credit_keywords = [
                'payment received', 'received', 'payshap payment received',
                'deposit', 'interest', 'transfer received', 'refund',
                'dispute', 'set-off', 'received:', 'income', 'sweep'
            ]
            
            # Strong debit indicators
            debit_keywords = [
                'purchase', 'payment:', 'cash sent', 'cash withdrawal',
                'prepaid purchase', 'voucher', 'debit order',
                'transfer to', 'external payment', 'immediate payment',
                'card replacement', 'admin fee', 'withdrawal', 'capitec pay',
                'fee', 'charge', 'round-up'
            ]
            
            # Check description
            if any(kw in desc_lower for kw in credit_keywords):
                return True
            if any(kw in desc_lower for kw in debit_keywords):
                return False
            
            # Check category
            if any(word in cat_lower for word in ['income', 'interest', 'received']):
                return True
            if any(word in cat_lower for word in ['withdrawal', 'fees', 'payments', 'purchase']):
                return False
            
            return False
        
        def extract_category(text_str):
            """Extract category from end of description"""
            categories = [
                'Other Income', 'Investment Income', 'Transfer', 'Cash Withdrawal',
                'Digital Payments', 'Cellphone', 'Groceries', 'Takeaways', 
                'Online Store', 'Furniture & Appliances', 'Uncategorised',
                'Investments', 'Savings', 'Fees', 'Interest', 'Alcohol',
                'Other Personal & Family', 'Transfers'
            ]
            
            for cat in categories:
                if text_str.endswith(cat):
                    description = text_str[:-(len(cat))].strip()
                    return description, cat
            
            return text_str, None
        
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and headers
            if (not line or 
                'Transaction History' in line or 
                'Money In' in line or 'Money Out' in line or
                'Date Description Category' in line or
                '* Includes VAT' in line or
                'Spending Summary' in line or
                'Fee Summary' in line or
                'Page ' in line and ' of ' in line):
                i += 1
                continue
            
            # Match date at start of line
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
            
            if date_match:
                try:
                    date_str = date_match.group(1)
                    rest_of_line = date_match.group(2).strip()
                    trans_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    
                    # Skip notification lines without amounts
                    if ('insufficient funds' in rest_of_line.lower() or 
                        'authentication fee' in rest_of_line.lower()) and \
                       not re.search(r'\d+\.\d{2}', rest_of_line):
                        i += 1
                        continue
                    
                    # Pattern 1: Three amounts (main amount, fee, balance)
                    pattern_3amt = re.search(
                        r'(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s*$',
                        rest_of_line
                    )
                    
                    # Pattern 2: Two amounts (amount and balance, OR fee and balance)
                    pattern_2amt = re.search(
                        r'(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s*$',
                        rest_of_line
                    )
                    
                    trans_amount = 0.0
                    fee = 0.0
                    balance = 0.0
                    description = ""
                    category = None
                    
                    if pattern_3amt:
                        # Three amounts: description | amount | fee | balance
                        desc_and_cat = pattern_3amt.group(1).strip()
                        amount_str = pattern_3amt.group(2).strip()
                        fee_str = pattern_3amt.group(3).strip()
                        balance_str = pattern_3amt.group(4).strip()
                        
                        trans_amount = parse_amount(amount_str)
                        fee = abs(parse_amount(fee_str))
                        balance = parse_amount(balance_str)
                        description, category = extract_category(desc_and_cat)
                        
                        # Create main transaction if amount > 0
                        if abs(trans_amount) > 0:
                            is_credit = is_credit_transaction(description, category)
                            transactions.append({
                                'date': trans_date,
                                'description': description,
                                'amount': abs(trans_amount),
                                'type': 'credit' if is_credit else 'debit',
                                'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}",
                                'category': category,
                                'fee': fee,
                                'balance': balance
                            })
                            logger.debug(f"[3AMT] {trans_date} | Bal:{balance:>8.2f} | {description[:40]:<40} | R{abs(trans_amount):>8.2f} | {'CR' if is_credit else 'DR'}")
                        
                        # Create separate fee transaction if fee > 0
                        # Fee happens AFTER main transaction, so balance is lower
                        if fee > 0:
                            fee_balance = balance
                            transactions.append({
                                'date': trans_date,
                                'description': f"{description} (Fee)",
                                'amount': fee,
                                'type': 'debit',
                                'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}-FEE",
                                'category': 'Fees',
                                'fee': 0.0,
                                'balance': fee_balance
                            })
                            logger.debug(f"[FEE]  {trans_date} | Bal:{fee_balance:>8.2f} | {description[:40]:<40} (Fee) | R{fee:>8.2f} | DR")
                    
                    elif pattern_2amt:
                        # Two amounts: could be (amount, balance) OR (fee, balance)
                        desc_and_cat = pattern_2amt.group(1).strip()
                        amount1_str = pattern_2amt.group(2).strip()
                        amount2_str = pattern_2amt.group(3).strip()
                        
                        amount1 = parse_amount(amount1_str)
                        amount2 = parse_amount(amount2_str)
                        description, category = extract_category(desc_and_cat)
                        
                        # If 'fee' in description or category, treat first amount as fee
                        if 'fee' in description.lower() or (category and 'fee' in category.lower()):
                            trans_amount = abs(amount1)
                            fee = 0.0
                            balance = amount2
                        else:
                            trans_amount = amount1
                            fee = 0.0
                            balance = amount2
                        
                        if abs(trans_amount) > 0:
                            is_credit = is_credit_transaction(description, category)
                            transactions.append({
                                'date': trans_date,
                                'description': description,
                                'amount': abs(trans_amount),
                                'type': 'credit' if is_credit else 'debit',
                                'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}",
                                'category': category,
                                'fee': fee,
                                'balance': balance
                            })
                            logger.debug(f"[2AMT] {trans_date} | Bal:{balance:>8.2f} | {description[:40]:<40} | R{abs(trans_amount):>8.2f} | {'CR' if is_credit else 'DR'}")
                    
                    else:
                        # Description only - check if amounts are on next line(s)
                        desc_and_cat = rest_of_line.strip()
                        
                        # Look ahead for amounts
                        j = i + 1
                        found_amounts = False
                        while j < len(lines) and j < i + 3:  # Look ahead max 3 lines
                            next_line = lines[j].strip()
                            
                            # Stop if we hit another date
                            if re.match(r'^\d{2}/\d{2}/\d{4}', next_line):
                                break
                            
                            # Try to find amounts
                            amounts_match = re.search(
                                r'^(-?\d{1,3}(?:,\d{3})*\.\d{2})(?:\s+(-?\d{1,3}(?:,\d{3})*\.\d{2}))?(?:\s+(-?\d{1,3}(?:,\d{3})*\.\d{2}))?',
                                next_line
                            )
                            
                            if amounts_match:
                                found_amounts = True
                                amt1 = parse_amount(amounts_match.group(1))
                                amt2 = parse_amount(amounts_match.group(2)) if amounts_match.group(2) else 0
                                amt3 = parse_amount(amounts_match.group(3)) if amounts_match.group(3) else 0
                                
                                description, category = extract_category(desc_and_cat)
                                
                                # Determine structure based on number of amounts
                                if amt3 != 0:
                                    # Three amounts
                                    trans_amount = amt1
                                    fee = abs(amt2)
                                    balance = amt3
                                elif amt2 != 0:
                                    # Two amounts
                                    trans_amount = amt1
                                    fee = 0
                                    balance = amt2
                                else:
                                    # One amount
                                    trans_amount = amt1
                                    fee = 0
                                    balance = 0
                                
                                if abs(trans_amount) > 0:
                                    is_credit = is_credit_transaction(description, category)
                                    transactions.append({
                                        'date': trans_date,
                                        'description': description,
                                        'amount': abs(trans_amount),
                                        'type': 'credit' if is_credit else 'debit',
                                        'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}",
                                        'category': category,
                                        'fee': fee,
                                        'balance': balance
                                    })
                                    logger.debug(f"[MLNE] {trans_date} | Bal:{balance:>8.2f} | {description[:40]:<40} | R{abs(trans_amount):>8.2f} | {'CR' if is_credit else 'DR'}")
                                
                                # Add fee transaction if exists
                                if fee > 0:
                                    fee_balance = balance
                                    transactions.append({
                                        'date': trans_date,
                                        'description': f"{description} (Fee)",
                                        'amount': fee,
                                        'type': 'debit',
                                        'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}-FEE",
                                        'category': 'Fees',
                                        'fee': 0.0,
                                        'balance': fee_balance
                                    })
                                    logger.debug(f"[FEE]  {trans_date} | Bal:{fee_balance:>8.2f} | {description[:40]:<40} (Fee) | R{fee:>8.2f} | DR")
                                
                                i = j
                                break
                            
                            j += 1
                        
                        if not found_amounts:
                            # Try to extract amounts from description itself
                            embedded_amounts = re.findall(r'(?:R\s*)?(-?\d{1,3}(?:,\d{3})*\.\d{2})', desc_and_cat)
                            if embedded_amounts and len(embedded_amounts) >= 1:
                                # Found amounts in description
                                if len(embedded_amounts) == 1:
                                    # Only one amount - assume it's the transaction amount, no balance
                                    trans_amount = parse_amount(embedded_amounts[0])
                                    balance = 0
                                else:
                                    # Multiple amounts - first is transaction, last is balance
                                    trans_amount = parse_amount(embedded_amounts[0])
                                    balance = parse_amount(embedded_amounts[-1])
                                
                                # Clean description - remove amounts
                                clean_desc = desc_and_cat
                                for amt_str in embedded_amounts:
                                    clean_desc = clean_desc.replace(f'R{amt_str}', '').replace(amt_str, '')
                                clean_desc = ' '.join(clean_desc.split())
                                description, category = extract_category(clean_desc)
                                
                                if abs(trans_amount) > 0:
                                    is_credit = is_credit_transaction(description, category)
                                    transactions.append({
                                        'date': trans_date,
                                        'description': description,
                                        'amount': abs(trans_amount),
                                        'type': 'credit' if is_credit else 'debit',
                                        'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}",
                                        'category': category,
                                        'fee': 0.0,
                                        'balance': balance
                                    })
                                    logger.debug(f"[EMBD] {trans_date} | Bal:{balance:>8.2f} | {description[:40]:<40} | R{abs(trans_amount):>8.2f} | {'CR' if is_credit else 'DR'}")
                            else:
                                logger.warning(f"No amounts found for: {desc_and_cat[:60]}")
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Parse error: {line[:80]} | {e}")
            
            i += 1
        
        logger.info(f"Successfully parsed {len(transactions)} Capitec transactions")
        return transactions
    
    def _parse_tymebank(self, text):
        """Parse TymeBank PDF format"""
        transactions = []
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            date_match = re.match(r'^(\d{1,2}\s+\w{3}\s+\d{4})\s+(.+)', line)
            
            if date_match:
                try:
                    date_str = date_match.group(1)
                    rest_of_line = date_match.group(2).strip()
                    trans_date = datetime.strptime(date_str, '%d %b %Y').date()
                    
                    description_parts = [rest_of_line]
                    j = i + 1
                    amounts_found = False
                    fees = money_out = money_in = balance = None
                    
                    while j < len(lines) and j < i + 6:
                        next_line = lines[j].strip()
                        if re.match(r'^\d{1,2}\s+\w{3}\s+\d{4}', next_line):
                            break
                        
                        amount_pattern = r'^(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+(-|(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s+((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)\s*$'
                        amount_match = re.match(amount_pattern, next_line)
                        
                        if amount_match:
                            fees = amount_match.group(1).strip()
                            money_out = amount_match.group(2).strip()
                            money_in = amount_match.group(3).strip()
                            balance = amount_match.group(4).strip()
                            amounts_found = True
                            i = j
                            break
                        elif next_line and not re.match(r'^\d{10,}$', next_line):
                            if len(next_line) > 0 and not next_line.startswith('-'):
                                description_parts.append(next_line)
                        
                        j += 1
                    
                    if amounts_found:
                        description = ' '.join(description_parts)
                        description = ' '.join(description.split())
                        
                        if len(description) < 3 or 'Description' in description:
                            i += 1
                            continue
                        
                        def parse_amount_safe(amount_str):
                            if not amount_str or amount_str == '-':
                                return 0
                            try:
                                cleaned = amount_str.replace(',', '').replace(' ', '').strip()
                                val = float(cleaned)
                                if val > 10_000_000:
                                    return 0
                                return val
                            except (ValueError, AttributeError):
                                return 0
                        
                        amount = 0
                        trans_type = 'debit'
                        
                        money_in_val = parse_amount_safe(money_in)
                        if money_in_val > 0:
                            amount = money_in_val
                            trans_type = 'credit'
                        
                        money_out_val = parse_amount_safe(money_out)
                        if amount == 0 and money_out_val > 0:
                            amount = money_out_val
                            trans_type = 'debit'
                        
                        fees_val = parse_amount_safe(fees)
                        if amount == 0 and fees_val > 0:
                            amount = fees_val
                            trans_type = 'debit'
                            description = f"{description} (Fee)"
                        
                        if amount > 0:
                            transactions.append({
                                'date': trans_date,
                                'description': description,
                                'amount': amount,
                                'type': trans_type,
                                'reference': f"TYME-{trans_date.strftime('%Y%m%d')}-{len(transactions)}",
                                'balance': parse_amount_safe(balance)
                            })
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse TymeBank transaction: {e}")
            
            i += 1
        
        logger.info(f"Successfully parsed {len(transactions)} TymeBank transactions")
        return transactions
    
    def _parse_generic(self, text):
        """Generic PDF parsing for unknown banks"""
        transactions = []
        
        patterns = [
            (r'(\d{2}/\d{2}/\d{4})\s*[|\|]\s*([^|\|]+?)\s*[|\|]\s*(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
            (r'(\d{2}/\d{2}/\d{4})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%d/%m/%Y'),
            (r'(\d{4}-\d{2}-\d{2})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%Y-%m-%d'),
            (r'(\d{2}\s+\w{3}\s+\d{4})\s+([^\d\-\+\$R]+?)\s+(-?R?[\d,]+\.\d{2})', '%d %b %Y'),
        ]
        
        for pattern, date_format in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            
            if matches:
                for match in matches:
                    try:
                        trans_date = datetime.strptime(match[0].strip(), date_format).date()
                        description = match[1].strip()
                        amount_str = match[2].replace('R', '').replace('$', '').replace(',', '').strip()
                        amount = float(amount_str)
                        
                        if len(description) < 3:
                            continue
                        
                        transactions.append({
                            'date': trans_date,
                            'description': description,
                            'amount': abs(amount),
                            'type': 'debit' if amount < 0 else 'credit',
                            'reference': f"GEN-{trans_date.strftime('%Y%m%d')}-{len(transactions)}",
                            'balance': 0
                        })
                    except (ValueError, IndexError) as e:
                        continue
                
                if transactions:
                    break
        
        return transactions
