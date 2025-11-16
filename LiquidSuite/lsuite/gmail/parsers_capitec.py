"""
Capitec Bank Statement PDF Parser
Specialized parser for Capitec bank statements with category extraction
"""
import io
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CapitecPDFParser:
    """
    Specialized PDF parser for Capitec Bank statements
    
    Features:
    - Extracts transaction categories from Capitec statements
    - Properly identifies credits vs debits
    - Maintains balance tracking
    - Handles fees as separate transactions
    - Extracts all Capitec-specific fields
    """
    
    # Capitec transaction categories
    CAPITEC_CATEGORIES = [
        'Other Income', 'Investment Income', 'Transfer', 'Cash Withdrawal',
        'Digital Payments', 'Cellphone', 'Groceries', 'Takeaways', 
        'Online Store', 'Furniture & Appliances', 'Uncategorised',
        'Investments', 'Savings', 'Fees', 'Interest', 'Alcohol',
        'Other Personal & Family', 'Transfers', 'Entertainment',
        'Clothing & Footwear', 'Transport', 'Medical', 'Insurance',
        'Education', 'Home & Garden', 'Pets', 'Subscriptions'
    ]
    
    # Credit transaction indicators
    CREDIT_KEYWORDS = [
        'payment received', 'received', 'payshap payment received',
        'deposit', 'interest', 'transfer received', 'refund',
        'dispute', 'set-off', 'received:', 'income', 'sweep',
        'credit', 'reversal', 'cashback'
    ]
    
    # Debit transaction indicators
    DEBIT_KEYWORDS = [
        'purchase', 'payment:', 'cash sent', 'cash withdrawal',
        'prepaid purchase', 'voucher', 'debit order',
        'transfer to', 'external payment', 'immediate payment',
        'card replacement', 'admin fee', 'withdrawal', 'capitec pay',
        'fee', 'charge', 'round-up', 'swipe'
    ]
    
    def __init__(self):
        """Initialize parser"""
        self.transactions = []
        self.statement_info = {}
    
    def parse_pdf(self, pdf_data, password=None):
        """Parse Capitec PDF statement"""
        text = self._extract_text_from_pdf(pdf_data, password)
        self.statement_info = self._extract_statement_info(text)
        self.transactions = self._parse_capitec_transactions(text)
        self.transactions = self._sort_by_date_and_balance(self.transactions)
        
        logger.info(f"Parsed {len(self.transactions)} Capitec transactions")
        
        return {
            'transactions': self.transactions,
            'statement_info': self.statement_info
        }
    
    def _extract_text_from_pdf(self, pdf_data, password=None):
        """Extract text from PDF"""
        text = ""
        
        try:
            import PyPDF2
            pdf_file = io.BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if pdf_reader.is_encrypted:
                if not password:
                    raise ValueError("PDF is password protected but no password provided")
                if pdf_reader.decrypt(password) == 0:
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
    
    def _extract_statement_info(self, text):
        """Extract statement metadata"""
        info = {
            'bank_name': 'Capitec Bank',
            'account_number': None,
            'statement_period': None,
            'opening_balance': None,
            'closing_balance': None
        }
        
        account_match = re.search(r'Account number[:\s]+(\d+)', text, re.IGNORECASE)
        if account_match:
            info['account_number'] = account_match.group(1)
        
        period_match = re.search(r'Statement period[:\s]+(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if period_match:
            info['statement_period'] = {'start': period_match.group(1), 'end': period_match.group(2)}
        
        opening_match = re.search(r'Opening balance[:\s]+R?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if opening_match:
            info['opening_balance'] = self._parse_amount(opening_match.group(1))
        
        closing_match = re.search(r'Closing balance[:\s]+R?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if closing_match:
            info['closing_balance'] = self._parse_amount(closing_match.group(1))
        
        return info
    
    def _parse_capitec_transactions(self, text):
        """Parse Capitec transactions"""
        transactions = []
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip headers
            if (not line or 'Transaction History' in line or 'Money In' in line or 
                'Date Description Category' in line or '* Includes VAT' in line or
                'Spending Summary' in line or 'Page ' in line):
                i += 1
                continue
            
            # Match date
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
            
            if date_match:
                trans = self._parse_transaction_line(date_match, lines, i)
                if trans:
                    if isinstance(trans, list):
                        for t in trans:
                            transactions.append(t)
                        i = trans[0].get('_line_end', i) if trans else i
                    else:
                        transactions.append(trans)
                        i = trans.get('_line_end', i)
            
            i += 1
        
        logger.info(f"Extracted {len(transactions)} transactions")
        return transactions
    
    def _parse_transaction_line(self, date_match, lines, start_idx):
        """Parse single transaction"""
        try:
            date_str = date_match.group(1)
            rest_of_line = date_match.group(2).strip()
            trans_date = datetime.strptime(date_str, '%d/%m/%Y').date()
            
            # Try patterns
            pattern_3amt = re.search(r'(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s*$', rest_of_line)
            pattern_2amt = re.search(r'(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s*$', rest_of_line)
            
            if pattern_3amt:
                return self._parse_three_amount_transaction(trans_date, pattern_3amt, start_idx)
            elif pattern_2amt:
                return self._parse_two_amount_transaction(trans_date, pattern_2amt, start_idx)
            else:
                return self._parse_multiline_transaction(trans_date, rest_of_line, lines, start_idx)
        
        except (ValueError, IndexError) as e:
            logger.warning(f"Parse error: {e}")
            return None
    
    def _parse_three_amount_transaction(self, trans_date, match, line_idx):
        """Parse three amounts (main, fee, balance)"""
        desc_and_cat = match.group(1).strip()
        amount_str = match.group(2).strip()
        fee_str = match.group(3).strip()
        balance_str = match.group(4).strip()
        
        description, category = self._extract_category(desc_and_cat)
        trans_amount = self._parse_amount(amount_str)
        fee = abs(self._parse_amount(fee_str))
        balance = self._parse_amount(balance_str)
        
        transactions = []
        if abs(trans_amount) > 0:
            is_credit = self._is_credit_transaction(description, category)
            transactions.append({
                'date': trans_date, 'description': description, 'amount': abs(trans_amount),
                'type': 'credit' if is_credit else 'debit', 'category': category,
                'fee': fee, 'balance': balance,
                'reference': f"CAP-{trans_date.strftime('%Y%m%d')}", '_line_end': line_idx
            })
        
        if fee > 0:
            transactions.append({
                'date': trans_date, 'description': f"{description} (Fee)", 'amount': fee,
                'type': 'debit', 'category': 'Fees', 'fee': 0.0, 'balance': balance,
                'reference': f"CAP-{trans_date.strftime('%Y%m%d')}-FEE", '_line_end': line_idx
            })
        
        return transactions if len(transactions) > 1 else (transactions[0] if transactions else None)
    
    def _parse_two_amount_transaction(self, trans_date, match, line_idx):
        """Parse two amounts"""
        desc_and_cat = match.group(1).strip()
        amount1_str = match.group(2).strip()
        amount2_str = match.group(3).strip()
        
        description, category = self._extract_category(desc_and_cat)
        amount1 = self._parse_amount(amount1_str)
        amount2 = self._parse_amount(amount2_str)
        
        if 'fee' in description.lower() or (category and 'fee' in category.lower()):
            trans_amount = abs(amount1)
            balance = amount2
        else:
            trans_amount = amount1
            balance = amount2
        
        if abs(trans_amount) > 0:
            is_credit = self._is_credit_transaction(description, category)
            return {
                'date': trans_date, 'description': description, 'amount': abs(trans_amount),
                'type': 'credit' if is_credit else 'debit', 'category': category,
                'fee': 0.0, 'balance': balance,
                'reference': f"CAP-{trans_date.strftime('%Y%m%d')}", '_line_end': line_idx
            }
        return None
    
    def _parse_multiline_transaction(self, trans_date, first_line, lines, start_idx):
        """Parse multiline - IMPROVED"""
        desc_and_cat = first_line
        
        j = start_idx + 1
        while j < len(lines) and j < start_idx + 5:  # Check up to 5 lines
            next_line = lines[j].strip()
            
            if not next_line:
                j += 1
                continue
            
            if re.match(r'^\d{2}/\d{2}/\d{4}', next_line):
                break
            
            # Look for amounts
            amounts_match = re.search(r'^(-?\d{1,3}(?:,\d{3})*\.\d{2})(?:\s+(-?\d{1,3}(?:,\d{3})*\.\d{2}))?(?:\s+(-?\d{1,3}(?:,\d{3})*\.\d{2}))?\s*$', next_line)
            
            if amounts_match:
                description, category = self._extract_category(desc_and_cat)
                amt1 = self._parse_amount(amounts_match.group(1))
                amt2 = self._parse_amount(amounts_match.group(2)) if amounts_match.group(2) else 0
                amt3 = self._parse_amount(amounts_match.group(3)) if amounts_match.group(3) else 0
                
                if amt3 != 0:
                    trans_amount, fee, balance = amt1, abs(amt2), amt3
                elif amt2 != 0:
                    trans_amount, fee, balance = amt1, 0, amt2
                else:
                    trans_amount, fee, balance = amt1, 0, 0
                
                if abs(trans_amount) > 0:
                    is_credit = self._is_credit_transaction(description, category)
                    return {
                        'date': trans_date, 'description': description, 'amount': abs(trans_amount),
                        'type': 'credit' if is_credit else 'debit', 'category': category,
                        'fee': fee, 'balance': balance,
                        'reference': f"CAP-{trans_date.strftime('%Y%m%d')}", '_line_end': j
                    }
            else:
                # Add line to description
                if not re.match(r'^[\d\s,\.]+$', next_line):
                    desc_and_cat += ' ' + next_line
            
            j += 1
        
        logger.warning(f"No amounts found for: {desc_and_cat[:80]}")
        return None
    
    def _extract_category(self, text_str):
        """Extract category"""
        for cat in self.CAPITEC_CATEGORIES:
            if text_str.endswith(cat):
                return text_str[:-(len(cat))].strip(), cat
        return text_str, None
    
    def _is_credit_transaction(self, description, category):
        """Determine credit vs debit"""
        desc_lower = description.lower()
        cat_lower = (category or '').lower()
        
        if any(kw in desc_lower for kw in self.CREDIT_KEYWORDS):
            return True
        if any(kw in desc_lower for kw in self.DEBIT_KEYWORDS):
            return False
        
        if any(word in cat_lower for word in ['income', 'interest', 'received']):
            return True
        if any(word in cat_lower for word in ['withdrawal', 'fees', 'payments', 'purchase']):
            return False
        
        return False
    
    def _parse_amount(self, amount_str):
        """Parse amount"""
        if not amount_str or amount_str == '-' or amount_str.strip() == '':
            return 0.0
        try:
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()
            if cleaned.startswith('-'):
                return -float(cleaned[1:])
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0
    
    def _sort_by_date_and_balance(self, transactions):
        """Sort chronologically"""
        if not transactions:
            return transactions
        return sorted(transactions, key=lambda x: (-x['date'].toordinal(), float(x.get('balance', 0)) if x.get('balance') is not None else 0))
