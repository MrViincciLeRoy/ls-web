"""
PDF Extraction Service for Invoices and Purchase Orders
"""
import re
import logging
from datetime import datetime
from decimal import Decimal
import PyPDF2
from lsuite.ai_insights.ai_service import get_ai_service

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Extract data from PDF invoices and purchase orders"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def extract_from_pdf(self, pdf_path):
        """Extract text and data from PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            # Try rule-based extraction first
            extracted = self._rule_based_extraction(text)
            
            # If incomplete, use AI
            if not self._is_extraction_complete(extracted):
                extracted = self._ai_extraction(text, extracted)
            
            return {
                'success': True,
                'text': text,
                'data': extracted,
                'method': 'rule_based' if self._is_extraction_complete(extracted) else 'ai_assisted'
            }
        
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _rule_based_extraction(self, text):
        """Extract data using regex patterns"""
        data = {}
        
        # Document number patterns
        doc_patterns = [
            r'(?:invoice|inv|po|purchase order)[\s#:]*([A-Z0-9\-]+)',
            r'(?:number|no|#)[\s:]*([A-Z0-9\-]+)',
        ]
        for pattern in doc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['document_number'] = match.group(1).strip()
                break
        
        # Date patterns
        date_patterns = [
            r'(?:date|dated)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    data['document_date'] = self._parse_date(date_str)
                    break
                except:
                    pass
        
        # Due date
        due_patterns = [
            r'due[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'due date[\s:]*(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in due_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    data['due_date'] = self._parse_date(match.group(1))
                    break
                except:
                    pass
        
        # Amount patterns
        amount_patterns = [
            r'total[\s:]*(?:R|ZAR)?[\s]*([0-9,]+\.?\d{0,2})',
            r'amount due[\s:]*(?:R|ZAR)?[\s]*([0-9,]+\.?\d{0,2})',
            r'grand total[\s:]*(?:R|ZAR)?[\s]*([0-9,]+\.?\d{0,2})',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    data['total_amount'] = float(amount_str)
                    break
                except:
                    pass
        
        # VAT/Tax patterns
        vat_patterns = [
            r'vat[\s:]*(?:R|ZAR)?[\s]*([0-9,]+\.?\d{0,2})',
            r'tax[\s:]*(?:R|ZAR)?[\s]*([0-9,]+\.?\d{0,2})',
        ]
        for pattern in vat_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    data['tax_amount'] = float(amount_str)
                    break
                except:
                    pass
        
        # Supplier/Customer name (first few lines often contain this)
        lines = text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if len(line) > 5 and len(line) < 100:
                if not any(x in line.lower() for x in ['invoice', 'date', 'number', 'page', 'total']):
                    if 'supplier_name' not in data:
                        data['supplier_name'] = line
                        break
        
        return data
    
    def _parse_date(self, date_str):
        """Parse various date formats"""
        formats = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%y',
            '%d/%m/%y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        
        return None
    
    def _is_extraction_complete(self, data):
        """Check if extraction has minimum required fields"""
        required = ['document_number', 'total_amount']
        return all(field in data and data[field] for field in required)
    
    def _ai_extraction(self, text, partial_data):
        """Use AI to extract missing data"""
        if not self.ai_service.enabled:
            return partial_data
        
        try:
            prompt = f"""Extract invoice/purchase order data from this text:

{text[:2000]}

Already extracted: {partial_data}

Return ONLY JSON with these fields:
{{
    "document_number": "string",
    "document_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "supplier_name": "string",
    "customer_name": "string",
    "subtotal": 0.00,
    "tax_amount": 0.00,
    "total_amount": 0.00,
    "currency": "ZAR",
    "line_items": [
        {{"description": "string", "quantity": 0, "unit_price": 0, "total": 0}}
    ]
}}

Only include fields you can confidently extract."""
            
            messages = [
                {"role": "system", "content": "You are a document data extraction expert. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.ai_service._call_api(messages, temperature=0.1)
            cleaned = self.ai_service._clean_json_response(response)
            
            import json
            ai_data = json.loads(cleaned)
            
            # Merge AI data with partial data
            return {**partial_data, **ai_data}
        
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return partial_data
    
    def analyze_document_with_context(self, document, transactions):
        """Analyze document with related transaction context"""
        if not self.ai_service.enabled:
            return self._basic_analysis(document, transactions)
        
        try:
            # Prepare transaction context
            trans_summary = []
            for t in transactions[:20]:
                trans_summary.append({
                    'date': t.date.isoformat(),
                    'description': t.description,
                    'amount': float(t.withdrawal or t.deposit or 0),
                    'type': 'expense' if t.withdrawal else 'income'
                })
            
            prompt = f"""Analyze this invoice/PO with bank transaction context:

Document:
- Number: {document.document_number}
- Date: {document.document_date}
- Supplier: {document.supplier_name}
- Total: R{document.total_amount}

Related Transactions (last 20):
{trans_summary}

Provide analysis in JSON:
{{
    "payment_status": "paid/unpaid/partial",
    "matched_transactions": [transaction_indices],
    "amount_variance": 0.00,
    "expected_payment_date": "YYYY-MM-DD",
    "insights": ["insight 1", "insight 2"],
    "risk_flags": ["flag if any"],
    "recommendations": ["recommendation 1"]
}}"""
            
            messages = [
                {"role": "system", "content": "Financial analyst. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.ai_service._call_api(messages, temperature=0.3)
            cleaned = self.ai_service._clean_json_response(response)
            
            import json
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return self._basic_analysis(document, transactions)
    
    def _basic_analysis(self, document, transactions):
        """Basic analysis without AI"""
        analysis = {
            'payment_status': 'unknown',
            'matched_transactions': [],
            'amount_variance': 0,
            'insights': [f"Document total: R{document.total_amount}"],
            'risk_flags': [],
            'recommendations': []
        }
        
        # Look for matching amounts
        target = float(document.total_amount)
        for idx, t in enumerate(transactions):
            amount = float(t.withdrawal or t.deposit or 0)
            if abs(amount - target) < 1.0:  # Within R1
                analysis['matched_transactions'].append(idx)
                analysis['payment_status'] = 'paid'
        
        if not analysis['matched_transactions']:
            analysis['payment_status'] = 'unpaid'
            analysis['recommendations'].append('No matching payment found')
        
        return analysis
