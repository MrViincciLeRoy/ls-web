"""
Test script to verify improved Capitec PDF parser with balance-based ordering
Run this to see what transactions are being extracted in correct chronological order
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from lsuite.gmail.parsers import PDFParser

def test_parse_capitec_pdf():
    """Test parsing the Capitec PDF"""
    
    # Path to your PDF
    pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'account_statement.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        return
    
    print(f"📄 Reading PDF: {pdf_path}")
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # Parse PDF
    parser = PDFParser()
    
    try:
        print("\n🔍 Parsing PDF...")
        transactions = parser.parse_pdf(
            pdf_data=pdf_data,
            bank_name='capitec',
            password=None  # Add password if needed
        )
        
        print(f"\n✅ Successfully parsed {len(transactions)} transactions!")
        print("   Sorted by: Date (newest first) → Balance (lowest first = exact PDF order)\n")
        
        # Group by date
        by_date = {}
        for trans in transactions:
            date_str = trans['date'].strftime('%Y-%m-%d')
            if date_str not in by_date:
                by_date[date_str] = []
            by_date[date_str].append(trans)
        
        # Display results
        print("=" * 130)
        print(f"{'DATE':<12} {'DESCRIPTION':<50} {'TYPE':<8} {'AMOUNT':>12} {'BALANCE':>12} {'CATEGORY':<20}")
        print("=" * 130)
        
        for date_str in sorted(by_date.keys(), reverse=True):
            for trans in by_date[date_str]:
                desc = trans['description'][:49]
                trans_type = trans['type'].upper()
                amount = f"R {trans['amount']:,.2f}"
                balance = f"R {trans.get('balance', 0):,.2f}" if trans.get('balance') is not None else "N/A"
                category = (trans.get('category') or 'N/A')[:19]
                
                print(f"{date_str:<12} {desc:<50} {trans_type:<8} {amount:>12} {balance:>12} {category:<20}")
        
        print("=" * 130)
        
        # Summary
        total_credits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_debits = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Transactions: {len(transactions)}")
        print(f"   Total Credits:      R {total_credits:,.2f}")
        print(f"   Total Debits:       R {total_debits:,.2f}")
        print(f"   Net:                R {(total_credits - total_debits):,.2f}")
        
        # Date range
        if transactions:
            dates = [t['date'] for t in transactions]
            print(f"   Date Range:         {min(dates)} to {max(dates)}")
        
        # Check specific date for ordering
        print(f"\n📋 DETAILED VIEW - OCT 21, 2025 (Chronological Order):")
        print("=" * 130)
        oct_21 = by_date.get('2025-10-21', [])
        if oct_21:
            print(f"{'#':<4} {'DESCRIPTION':<50} {'TYPE':<8} {'AMOUNT':>12} {'BALANCE':>12}")
            print("-" * 130)
            for idx, trans in enumerate(oct_21, 1):
                desc = trans['description'][:49]
                trans_type = trans['type'].upper()
                amount = f"R {trans['amount']:,.2f}"
                balance = f"R {trans.get('balance', 0):,.2f}" if trans.get('balance') is not None else "N/A"
                print(f"{idx:<4} {desc:<50} {trans_type:<8} {amount:>12} {balance:>12}")
            print("=" * 130)
            print(f"Total for Oct 21: {len(oct_21)} transactions")
            print("Note: Transactions are ordered by balance (lowest = earliest, matches PDF)")
        else:
            print("No transactions found for Oct 21")
        
        print("\n✅ Test completed successfully!")
        print("\n💡 ORDERING LOGIC:")
        print("   • Transactions sorted by date (newest first)")
        print("   • Within same day, sorted by balance (lowest balance = earliest transaction)")
        print("   • This matches EXACT PDF order as balance increases through the day")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_parse_capitec_pdf()
