"""
PDF Parser - Extract transactions from bank statement PDFs
LiquidSuite/lsuite/gmail/parsers.py - COMPLETE WORKING VERSION WITH IMPROVED CAPITEC PARSER
"""
import io
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF statement parser"""
    
    def parse_pdf(self, pdf_data, bank_name, password=None):
        """
        Parse PDF and extract transactions
        
        Args:
            pdf_data: Binary PDF data
            bank_name: Bank identifier (tymebank, capitec, other)
            password: PDF password if protected
            
        Returns:
            List of transaction dictionaries
        """
        text = self._extract_text_from_pdf(pdf_data, password)
        
        # Log extracted text for debugging
        logger.info(f"Extracted text length: {len(text)} characters")
        logger.debug(f"First 500 chars: {text[:500]}")
        
        if bank_name == 'tymebank':
            return self._parse_tymebank(text)
        elif bank_name == 'capitec':
            return self._parse_capitec(text)
        else:
            return self._parse_generic(text)
    
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
                                'reference': f"TYME-{trans_date.strftime('%Y%m%d')}-{len(transactions)}"
                            })
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse TymeBank transaction: {e}")
            
            i += 1
        
        logger.info(f"Successfully parsed {len(transactions)} TymeBank transactions")
        return transactions
    
    def _parse_capitec(self, text):
        """Parse Capitec PDF format - IMPROVED VERSION"""
        transactions = []
        lines = text.split('\n')
        
        def parse_amount(amount_str):
            if not amount_str or amount_str == '-':
                return 0.0
            try:
                cleaned = amount_str.replace(',', '').replace(' ', '').strip()
                return float(cleaned)
            except (ValueError, AttributeError):
                return 0.0
        
        def extract_description_and_category(text_str):
            categories = [
                'Other Income', 'Investment Income', 'Transfer', 'Cash Withdrawal',
                'Digital Payments', 'Cellphone', 'Groceries', 'Takeaways', 
                'Online Store', 'Furniture & Appliances', 'Uncategorised',
                'Investments', 'Savings', 'Fees', 'Interest', 'Alcohol',
                'Other Personal & Family'
            ]
            
            for cat in categories:
                if text_str.endswith(cat):
                    description = text_str[:-(len(cat))].strip()
                    return description, cat
            
            return text_str, 'Uncategorised'
        
        def determine_if_credit(description, amount_val, category):
            desc_lower = description.lower()
            cat_lower = category.lower() if category else ''
            
            credit_keywords = [
                'payment received', 'received', 'payshap payment received',
                'deposit', 'interest received', 'transfer received', 'refund',
                'dispute', 'set-off applied'
            ]
            
            debit_keywords = [
                'purchase', 'payment:', 'cash sent', 'cash withdrawal',
                'prepaid purchase', 'voucher purchase', 'debit order',
                'transfer to', 'external payment', 'immediate payment',
                'card replacement', 'admin fee', 'withdrawal', 'capitec pay'
            ]
            
            if any(kw in desc_lower for kw in credit_keywords):
                return True
            if any(kw in desc_lower for kw in debit_keywords):
                return False
            if any(word in cat_lower for word in ['income', 'interest']):
                return True
            if any(word in cat_lower for word in ['withdrawal', 'fees', 'payments']):
                return False
            if amount_val < 0:
                return False
            
            return False
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip headers and summary sections
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
            
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
            
            if date_match:
                try:
                    date_str = date_match.group(1)
                    rest_of_line = date_match.group(2).strip()
                    trans_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    
                    # Skip notification lines without amounts
                    if (('insufficient funds' in rest_of_line.lower() or 
                         'authentication fee' in rest_of_line.lower()) and
                        not re.search(r'\d+\.\d{2}\s+\d+\.\d{2}\s*$', rest_of_line)):
                        i += 1
                        continue
                    
                    # Three amounts pattern
                    three_amounts = re.search(
                        r'(.+?)\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s+(-?\d{1,3}(?:,\d{3})*\.\d{2})\s*$',
                        rest_of_line
                    )
                    
                    # Two amounts pattern
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
                        desc_and_cat = three_amounts.group(1).strip()
                        amount_str = three_amounts.group(2).strip()
                        fee_str = three_amounts.group(3).strip()
                        balance_str = three_amounts.group(4).strip()
                        
                        trans_amount = parse_amount(amount_str)
                        fee = abs(parse_amount(fee_str))
                        balance = parse_amount(balance_str)
                        description, category = extract_description_and_category(desc_and_cat)
                        
                    elif two_amounts:
                        desc_and_cat = two_amounts.group(1).strip()
                        amount1_str = two_amounts.group(2).strip()
                        amount2_str = two_amounts.group(3).strip()
                        
                        amount1 = parse_amount(amount1_str)
                        balance = parse_amount(amount2_str)
                        
                        if 'fee' in desc_and_cat.lower():
                            fee = abs(amount1)
                            trans_amount = fee
                        else:
                            trans_amount = amount1
                            fee = 0.0
                        
                        description, category = extract_description_and_category(desc_and_cat)
                    else:
                        i += 1
                        continue
                    
                    is_credit = determine_if_credit(description, trans_amount, category)
                    trans_amount = abs(trans_amount)
                    
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
                        logger.debug(f"✓ {trans_date} | {description[:40]} | R{trans_amount} | {'CR' if is_credit else 'DR'}")
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Parse error: {line[:80]} | {e}")
            
            i += 1
        
        logger.info(f"✓ Successfully parsed {len(transactions)} Capitec transactions")
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
                            'reference': f"GEN-{trans_date.strftime('%Y%m%d')}-{len(transactions)}"
                        })
                    except (ValueError, IndexError) as e:
                        continue
                
                if transactions:
                    break
        
        return transactions
    
    def parse_html_email(self, html_content, bank_name):
        """Parse transaction table from HTML email"""
        from bs4 import BeautifulSoup
        
        transactions = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:
                    cols = row.find_all('td')
                    
                    if len(cols) >= 3:
                        try:
                            date_text = cols[0].get_text().strip()
                            description = cols[1].get_text().strip()
                            amount_text = cols[2].get_text().strip()
                            
                            trans_date = None
                            for date_fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d %b %Y']:
                                try:
                                    trans_date = datetime.strptime(date_text, date_fmt).date()
                                    break
                                except ValueError:
                                    continue
                            
                            if not trans_date:
                                continue
                            
                            amount_str = re.sub(r'[^\d\.\-]', '', amount_text)
                            amount = float(amount_str)
                            
                            transactions.append({
                                'date': trans_date,
                                'description': description,
                                'amount': abs(amount),
                                'type': 'debit' if amount < 0 else 'credit',
                                'reference': f"HTML-{trans_date.strftime('%Y%m%d')}"
                            })
                        except (ValueError, IndexError):
                            continue
            
            logger.info(f"Extracted {len(transactions)} transactions from HTML email")
        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
        
        return transactions
