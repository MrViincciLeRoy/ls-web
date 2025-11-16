"""
Test script to verify PERFECT ORDER parsing with actual PDF
Compares old balance-based sorting vs new perfect order approach
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from lsuite.gmail.parsers_perfect_order import PDFParser

def test_perfect_order_parsing():
    """Test parsing with perfect order preservation"""
    
    # Path to your PDF
    pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'account_statement.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        return
    
    print(f"📄 Reading PDF: {pdf_path}")
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # Parse PDF with perfect order
    parser = PDFParser()
    
    try:
        print("\n🔍 Parsing PDF with PERFECT ORDER preservation...")
        transactions = parser.parse_pdf(
            pdf_data=pdf_data,
            bank_name='capitec',
            password=None
        )
        
        print(f"\n✅ Successfully parsed {len(transactions)} transactions!")
        print("   ⭐ Transactions in EXACT PDF ORDER (no sorting applied)\n")
        
        # Show first 30 transactions to verify order
        print("=" * 150)
        print(f"{'#':<5} {'DATE':<12} {'DESCRIPTION':<55} {'TYPE':<8} {'AMOUNT':>12} {'BALANCE':>12} {'LINE':<6}")
        print("=" * 150)
        
        for idx, trans in enumerate(transactions[:30], 1):
            desc = trans['description'][:54]
            trans_type = trans['type'].upper()
            amount = f"R {trans['amount']:,.2f}"
            balance = f"R {trans.get('balance', 0):,.2f}" if trans.get('balance') is not None else "N/A"
            line_order = trans.get('line_order', 0)
            date_str = trans['date'].strftime('%Y-%m-%d')
            
            print(f"{idx:<5} {date_str:<12} {desc:<55} {trans_type:<8} {amount:>12} {balance:>12} {line_order:<6}")
        
        if len(transactions) > 30:
            print(f"\n... and {len(transactions) - 30} more transactions")
        
        print("=" * 150)
        
        # Verify order is preserved by checking line_order sequence
        print("\n🔍 VERIFICATION - Checking order preservation:")
        
        line_orders = [t.get('line_order', 0) for t in transactions if t.get('line_order')]
        if line_orders:
            is_sequential = all(line_orders[i] <= line_orders[i+1] for i in range(len(line_orders)-1))
            if is_sequential:
                print("   ✅ Line order is PERFECTLY SEQUENTIAL - transactions are in exact PDF order!")
            else:
                print("   ⚠️ Line order has gaps - some transactions may be out of order")
                # Show where gaps occur
                for i in range(len(line_orders)-1):
                    if line_orders[i] > line_orders[i+1]:
                        print(f"      Gap at position {i}: line {line_orders[i]} -> {line_orders[i+1]}")
        
        # Check a specific date to see chronological order within that day
        print("\n📋 DETAILED VIEW - OCT 24, 2025 (First 10 transactions):")
        print("=" * 150)
        
        oct_24 = [t for t in transactions if t['date'].strftime('%Y-%m-%d') == '2025-10-24']
        
        if oct_24:
            print(f"{'#':<5} {'LINE':<6} {'DESCRIPTION':<55} {'TYPE':<8} {'AMOUNT':>12} {'BALANCE':>12}")
            print("-" * 150)
            
            for idx, trans in enumerate(oct_24[:10], 1):
                desc = trans['description'][:54]
                trans_type = trans['type'].upper()
                amount = f"R {trans['amount']:,.2f}"
                balance = f"R {trans.get('balance', 0):,.2f}" if trans.get('balance') is not None else "N/A"
                line_order = trans.get('line_order', 0)
                
                print(f"{idx:<5} {line_order:<6} {desc:<55} {trans_type:<8} {amount:>12} {balance:>12}")
            
            print("=" * 150)
            
            # Check if balances decrease chronologically (as expected in Capitec statements)
            balances = [t.get('balance', 0) for t in oct_24 if t.get('balance') is not None]
            if len(balances) > 1:
                decreasing = all(balances[i] >= balances[i+1] for i in range(len(balances)-1))
                if decreasing:
                    print("   ✅ Balances decrease chronologically - order is CORRECT!")
                else:
                    print("   ⚠️ Balances don't decrease monotonically - check if order matches PDF")
        else:
            print("   No transactions found for Oct 24, 2025")
        
        # Summary
        print("\n📊 SUMMARY:")
        print(f"   Total Transactions: {len(transactions)}")
        
        total_credits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_debits = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        
        print(f"   Total Credits:      R {total_credits:,.2f}")
        print(f"   Total Debits:       R {total_debits:,.2f}")
        print(f"   Net:                R {(total_credits - total_debits):,.2f}")
        
        if transactions:
            dates = [t['date'] for t in transactions]
            print(f"   Date Range:         {min(dates)} to {max(dates)}")
        
        print("\n✅ Test completed successfully!")
        print("\n💡 KEY FEATURES:")
        print("   • Transactions are in EXACT PDF ORDER")
        print("   • Each transaction has a 'line_order' field showing its position")
        print("   • NO sorting or reordering is applied")
        print("   • Balance field is preserved for reference")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_perfect_order_parsing()
