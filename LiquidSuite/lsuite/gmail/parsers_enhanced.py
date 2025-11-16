"""
ENHANCED PDF Parser - Extract ALL transactions including multi-line entries
Uses balance column to ensure no transactions are missed and proper ordering
"""
import io
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFParser:
    """Enhanced PDF statement parser with complete balance extraction"""
    
    def parse_pdf(self, pdf_data, bank_name, password=None):
        """
        Parse PDF and extract ALL transactions with balance
        
        Args:
            pdf_data: Binary PDF data
            bank_name: Bank identifier (tymebank, capitec, other)
            password: PDF password if protected
            
        Returns:
            List of transaction dictionaries sorted chronologically
        """
        text = self._extract_text_from_pdf(pdf_data, password)
        
        logger.info(f"Extracted text length: {len(text)} characters")
        
        if bank_name == 'tymebank':
            transactions = self._parse_tymebank(text)
        elif bank_name == 'capitec':
            transactions = self._parse_capitec_enhanced(text)
        else:
            transactions = self._parse_generic(text)
        
        # Sort transactions chronologically using balance
        return self._sort_by_balance(transactions)
    
    def _sort_by_balance(self, transactions):
        """
        Sort transactions chronologically using date and balance.
        Higher balance = earlier transaction (balance decreases through the day)
        """
        if not transactions:
            return transactions
        
        sorted_trans = sorted(
            transactions,
            key=lambda x: (
                x['date'],
                -float(x.get('balance', 0)) if x.get('balance') is not None else 0
            ),
            reverse=True
        )
        
        logger.info(f"✓ Sorted {len(sorted_trans)} transactions by date and balance")
        return sorted_trans
    
    def _extract_text_from_pdf(self, pdf_data, password=None):
        """Extract text from PDF using available library"""
        text = ""
        
        try:
            import PyPDF2
            pdf_file = io.BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if pdf_reader.is_encrypted:
                if not password:
                    raise ValueError("PDF is password protected but no password provided")
                
                decrypt_result = pdf_reader.decrypt(password)
                if decrypt_result == 0:
                    raise ValueError("Incorrect PDF password")
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            logger.info(f"Extracted {len(text)} characters using PyPDF2")
            
        except ImportError:
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
    
    def _parse_capitec_enhanced(self, text):
        """
        ENHANCED Capitec parser - extracts ALL transactions using balance column
        Key improvement: Uses balance as anchor to find ALL transactions
        """
        transactions = []
        lines = text.split('\n')
        
        def parse_amount(amount_str):
            """Convert amount string to float"""
            if not amount_str or amount_str == '-' or amount_str.strip() == '':
                return None
            try:
                cleaned = amount_str.replace(',', '').replace(' ', '').replace('R', '').strip()
                if cleaned.startswith('-'):
                    return -float(cleaned[1:])
                return float(cleaned)
            except (ValueError, AttributeError):
                return None
        
        def is_credit_transaction(description, category=None):
            """Determine if transaction is a credit"""
            desc_lower = description.lower()
            cat_lower = (category or '').lower()
            
            credit_keywords = [
                'payment received', 'received', 'payshap payment received',
                'deposit', 'interest', 'transfer received', 'refund',
                'dispute', 'set-off', 'sweep', 'income'
            ]
            
            debit_keywords = [
                'purchase', 'payment:', 'cash sent', 'cash withdrawal',
                'prepaid purchase', 'voucher', 'debit order',
                'transfer to', 'external payment', 'immediate payment',
                'card replacement', 'admin fee', 'withdrawal', 
                'fee', 'charge', 'round-up'
            ]
            
            if any(kw in desc_lower for kw in credit_keywords):
                return True
            if any(kw in desc_lower for kw in debit_keywords):
                return False
            if any(word in cat_lower for word in ['income', 'interest', 'received']):
                return True
            if any(word in cat_lower for word in ['withdrawal', 'fees', 'payment']):
                return False
            
            return False
        
        def extract_category(text_str):
            """Extract category from end of description"""
            categories = [
                'Other Income', 'Investment Income', 'Transfer', 'Cash Withdrawal',
                'Digital Payments', 'Cellphone', 'Groceries', 'Takeaways', 
                'Online Store', 'Furniture & Appliances', 'Uncategorised',
                'Investments', 'Savings', 'Fees', 'Interest', 'Alcohol',
                'Other Personal & Family', 'Transfers', 'N/A'
            ]
            
            for cat in categories:
                if text_str.endswith(cat):
                    description = text_str[:-(len(cat))].strip()
                    return description, cat
            
            return text_str, None
        
        # Strategy: Look for balance amounts (ALWAYS present) then work backwards to find description
        # This ensures we NEVER miss a transaction
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip headers and empty lines
            if (not line or 
                'Transaction History' in line or 
                'Money In' in line or 'Money Out' in line or
                'Date Description' in line or
                '* Includes VAT' in line or
                'Page ' in line):
                i += 1
                continue
            
            # Match date at start of line
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
            
            if date_match:
                try:
                    date_str = date_match.group(1)
                    rest_of_line = date_match.group(2).strip()
                    trans_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    
                    # Now extract the transaction data
                    # Format can be:
                    # 1. DATE DESCRIPTION AMOUNT BALANCE
                    # 2. DATE DESCRIPTION AMOUNT FEE BALANCE
                    # 3. DATE DESCRIPTION (multi-line)
                    #         AMOUNT BALANCE
                    
                    # Look for balance pattern (most reliable indicator)
                    # Balance is typically: space + number + space + number (balance is last)
                    balance_pattern = r'(-?\d{1,3}(?:[,\s]\d{3})*\.\d{2})\s*$'
                    
                    # Collect all content until next date or end
                    transaction_lines = [rest_of_line]
                    j = i + 1
                    
                    while j < len(lines) and j < i + 5:
                        next_line = lines[j].strip()
                        
                        # Stop at next date
                        if re.match(r'^\d{2}/\d{2}/\d{4}', next_line):
                            break
                        
                        # Stop at headers
                        if ('Transaction History' in next_line or 
                            'Page ' in next_line):
                            break
                        
                        if next_line:
                            transaction_lines.append(next_line)
                        
                        j += 1
                    
                    # Join all lines for this transaction
                    full_text = ' '.join(transaction_lines)
                    
                    # Extract all numbers from the text
                    all_numbers = re.findall(r'-?\d{1,3}(?:[,\s]\d{3})*\.\d{2}', full_text)
                    
                    if not all_numbers:
                        logger.debug(f"No amounts found for: {full_text[:80]}")
                        i = j - 1 if j > i + 1 else i
                        i += 1
                        continue
                    
                    # Parse all numbers
                    parsed_numbers = [parse_amount(n) for n in all_numbers]
                    parsed_numbers = [n for n in parsed_numbers if n is not None]
                    
                    if not parsed_numbers:
                        i = j - 1 if j > i + 1 else i
                        i += 1
                        continue
                    
                    # Determine structure based on count
                    balance = parsed_numbers[-1]  # Balance is ALWAYS last
                    trans_amount = 0.0
                    fee = 0.0
                    
                    # Extract description (everything before the numbers)
                    desc_match = re.match(r'(.+?)\s+-?\d{1,3}(?:[,\s]\d{3})*\.\d{2}', full_text)
                    if desc_match:
                        description_raw = desc_match.group(1).strip()
                    else:
                        description_raw = full_text
                    
                    description, category = extract_category(description_raw)
                    
                    # Determine transaction type and amounts
                    if len(parsed_numbers) == 1:
                        # Only balance - this is likely a notification/info line, skip it
                        logger.debug(f"Skipping info line (balance only): {description[:60]}")
                        i = j - 1 if j > i + 1 else i
                        i += 1
                        continue
                    
                    elif len(parsed_numbers) == 2:
                        # AMOUNT BALANCE
                        trans_amount = abs(parsed_numbers[0])
                        fee = 0.0
                    
                    elif len(parsed_numbers) >= 3:
                        # AMOUNT FEE BALANCE
                        trans_amount = abs(parsed_numbers[0])
                        fee = abs(parsed_numbers[1])
                    
                    # Create main transaction
                    if trans_amount > 0:
                        is_credit = is_credit_transaction(description, category)
                        
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
                        
                        logger.debug(
                            f"✓ {trans_date} | Bal:{balance:>9.2f} | "
                            f"{description[:40]:<40} | R{trans_amount:>8.2f} | "
                            f"{'CR' if is_credit else 'DR'}"
                        )
                        
                        # Create separate fee transaction if exists
                        if fee > 0:
                            transactions.append({
                                'date': trans_date,
                                'description': f"{description} (Fee)",
                                'amount': fee,
                                'type': 'debit',
                                'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-{len(transactions):04d}-FEE",
                                'category': 'Fees',
                                'fee': 0.0,
                                'balance': balance  # Fee transaction shares balance with main
                            })
                            
                            logger.debug(
                                f"✓ {trans_date} | Bal:{balance:>9.2f} | "
                                f"{description[:40]:<40} (Fee) | R{fee:>8.2f} | DR"
                            )
                    
                    # Move to next transaction
                    i = j - 1 if j > i + 1 else i
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Parse error: {line[:80]} | {e}")
            
            i += 1
        
        logger.info(f"✓ Successfully parsed {len(transactions)} Capitec transactions")
        return transactions
    
    def _parse_tymebank(self, text):
        """Parse TymeBank PDF format with balance extraction"""
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
                        
                        # TymeBank format: FEES MONEY_OUT MONEY_IN BALANCE
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
                    except (ValueError, IndexError):
                        continue
                
                if transactions:
                    break
        
        return transactions
