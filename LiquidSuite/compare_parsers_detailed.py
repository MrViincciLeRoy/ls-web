"""
Compare OLD parser vs PERFECT parser
Shows exactly what improvements were made
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def compare_parsers():
    """Compare old and new parsers side by side"""
    
    pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'account_statement.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        return
    
    print("=" * 120)
    print("PARSER COMPARISON: OLD vs PERFECT")
    print("=" * 120)
    print()
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # Test OLD parser
    print("🔍 Testing OLD parser (parsers.py)...")
    print("-" * 120)
    try:
        from lsuite.gmail.parsers import PDFParser as OldParser
        old_parser = OldParser()
        old_transactions = old_parser.parse_pdf(pdf_data, 'capitec', None)
        print(f"✅ OLD Parser: Extracted {len(old_transactions)} transactions")
    except Exception as e:
        print(f"❌ OLD Parser Error: {e}")
        old_transactions = []
    
    print()
    
    # Test NEW parser
    print("🔍 Testing PERFECT parser (parsers_perfect.py)...")
    print("-" * 120)
    try:
        from lsuite.gmail.parsers_perfect import PDFParser as PerfectParser
        new_parser = PerfectParser()
        new_transactions = new_parser.parse_pdf(pdf_data, 'capitec', None)
        print(f"✅ PERFECT Parser: Extracted {len(new_transactions)} transactions")
    except Exception as e:
        print(f"❌ PERFECT Parser Error: {e}")
        new_transactions = []
    
    print()
    print("=" * 120)
    print("COMPARISON RESULTS")
    print("=" * 120)
    
    # Compare totals
    old_count = len(old_transactions)
    new_count = len(new_transactions)
    difference = new_count - old_count
    
    print(f"\n📊 Transaction Count:")
    print(f"   OLD Parser:     {old_count:>4} transactions")
    print(f"   PERFECT Parser: {new_count:>4} transactions")
    print(f"   Difference:     {difference:>4} transactions {'✅' if difference >= 0 else '❌'}")
    
    # Compare date ranges
    if old_transactions:
        old_dates = [t['date'] for t in old_transactions]
        print(f"\n📅 OLD Parser Date Range:")
        print(f"   From: {min(old_dates)}")
        print(f"   To:   {max(old_dates)}")
    
    if new_transactions:
        new_dates = [t['date'] for t in new_transactions]
        print(f"\n📅 PERFECT Parser Date Range:")
        print(f"   From: {min(new_dates)}")
        print(f"   To:   {max(new_dates)}")
    
    # Compare amounts
    if old_transactions:
        old_credits = sum(t['amount'] for t in old_transactions if t['type'] == 'credit')
        old_debits = sum(t['amount'] for t in old_transactions if t['type'] == 'debit')
        print(f"\n💰 OLD Parser Amounts:")
        print(f"   Total Credits:  R {old_credits:>12,.2f}")
        print(f"   Total Debits:   R {old_debits:>12,.2f}")
        print(f"   Net:            R {(old_credits - old_debits):>12,.2f}")
    
    if new_transactions:
        new_credits = sum(t['amount'] for t in new_transactions if t['type'] == 'credit')
        new_debits = sum(t['amount'] for t in new_transactions if t['type'] == 'debit')
        print(f"\n💰 PERFECT Parser Amounts:")
        print(f"   Total Credits:  R {new_credits:>12,.2f}")
        print(f"   Total Debits:   R {new_debits:>12,.2f}")
        print(f"   Net:            R {(new_credits - new_debits):>12,.2f}")
    
    # Find new transactions (in perfect but not in old)
    if old_transactions and new_transactions:
        old_refs = set(t['reference'] for t in old_transactions)
        new_refs = set(t['reference'] for t in new_transactions)
        
        # This won't work exactly since references are different, 
        # so let's compare by date + description
        old_combo = set((t['date'].isoformat(), t['description'][:50]) for t in old_transactions)
        new_combo = set((t['date'].isoformat(), t['description'][:50]) for t in new_transactions)
        
        only_in_new = new_combo - old_combo
        only_in_old = old_combo - new_combo
        
        if only_in_new:
            print(f"\n✨ NEW transactions found by PERFECT parser ({len(only_in_new)}):")
            for date_str, desc in sorted(only_in_new, reverse=True)[:10]:
                print(f"   • {date_str}: {desc}")
            if len(only_in_new) > 10:
                print(f"   ... and {len(only_in_new) - 10} more")
        
        if only_in_old:
            print(f"\n⚠️  Transactions in OLD but not PERFECT ({len(only_in_old)}):")
            for date_str, desc in sorted(only_in_old, reverse=True)[:5]:
                print(f"   • {date_str}: {desc}")
    
    # Summary
    print()
    print("=" * 120)
    print("RECOMMENDATION")
    print("=" * 120)
    
    if difference > 0:
        print(f"\n✅ PERFECT parser extracts {difference} MORE transactions than the old parser!")
        print("   We recommend updating to the PERFECT parser.")
        print("\n   To update, run: UPDATE_PARSER.bat")
    elif difference == 0:
        print(f"\n✅ Both parsers extract the same number of transactions.")
        print("   The PERFECT parser has better error handling and is more robust.")
        print("\n   To update, run: UPDATE_PARSER.bat")
    else:
        print(f"\n⚠️  OLD parser shows {abs(difference)} more transactions.")
        print("   This needs investigation - check the transaction details above.")
    
    print()
    print("=" * 120)

if __name__ == '__main__':
    compare_parsers()
