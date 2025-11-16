"""
Analyze PDF to see exact text extraction and identify all transactions
"""
import io
import sys
import os
from datetime import datetime

# Set UTF-8 encoding for stdout to handle emojis and special characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def extract_pdf_text():
    """Extract raw text from PDF"""
    pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'account_statement.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF not found at: {pdf_path}")
        return
    
    print(f"[INFO] Reading PDF: {pdf_path}")
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # Extract text using PyPDF2
    try:
        import PyPDF2
        pdf_file = io.BytesIO(pdf_data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            text += page_text + "\n"
            print(f"\n{'='*80}")
            print(f"PAGE {page_num + 1}")
            print('='*80)
            print(page_text)
        
        # Now analyze the text for transaction patterns
        print("\n\n" + "="*80)
        print("TRANSACTION LINE ANALYSIS")
        print("="*80)
        
        lines = text.split('\n')
        transaction_count = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for lines starting with dates
            if line and len(line) > 10:
                # Check if starts with date pattern
                import re
                date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
                if date_match:
                    transaction_count += 1
                    date_str = date_match.group(1)
                    rest = date_match.group(2)
                    
                    print(f"\n[{transaction_count}] Line {i}: {date_str}")
                    print(f"    Full line: {line}")
                    
                    # Check if amounts are on this line
                    amounts = re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}', rest)
                    if amounts:
                        print(f"    Amounts found: {amounts}")
                    else:
                        print(f"    No amounts on this line, checking next lines...")
                        # Look ahead
                        for j in range(i+1, min(i+4, len(lines))):
                            next_line = lines[j].strip()
                            if next_line and not re.match(r'^\d{2}/\d{2}/\d{4}', next_line):
                                next_amounts = re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}', next_line)
                                if next_amounts:
                                    print(f"    Line {j}: {next_line}")
                                    print(f"    Amounts: {next_amounts}")
        
        print(f"\n\n{'='*80}")
        print(f"SUMMARY: Found {transaction_count} transaction lines")
        print('='*80)
        
    except ImportError:
        print("[ERROR] PyPDF2 not installed. Install with: pip install PyPDF2")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    extract_pdf_text()
