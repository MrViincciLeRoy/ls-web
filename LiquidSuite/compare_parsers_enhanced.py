"""
Compare current parser vs enhanced parser
Shows which transactions are being missed and why
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from lsuite.gmail.parsers import PDFParser as CurrentParser
from lsuite.gmail.parsers_enhanced import PDFParser as EnhancedParser

def compare_parsers():
    """Compare current vs enhanced parser"""
    
    pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'account_statement.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        return
    
    print(f"📄 Reading PDF: {pdf_path}\n")
    
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # Parse with current parser
    print("=" * 100)
    print("1️⃣  CURRENT PARSER")
    print("=" * 100)
    current_parser = CurrentParser()
    current_trans = current_parser.parse_pdf(pdf_data, 'capitec')
    
    print(f"✓ Extracted {len(current_trans)} transactions\n")
    
    # Parse with enhanced parser
    print("=" * 100)
    print("2️⃣  ENHANCED PARSER")
    print("=" * 100)
    enhanced_parser = EnhancedParser()
    enhanced_trans = enhanced_parser.parse_pdf(pdf_data, 'capitec')
    
    print(f"✓ Extracted {len(enhanced_trans)} transactions\n")
    
    # Compare results
    print("=" * 100)
    print("📊 COMPARISON")
    print("=" * 100)
    print(f"Current Parser:  {len(current_trans)} transactions")
    print(f"Enhanced Parser: {len(enhanced_trans)} transactions")
    print(f"Difference:      {len(enhanced_trans) - len(current_trans)} transactions")
    
    if len(enhanced_trans) > len(current_trans):
        print(f"\n✅ Enhanced parser found {len(enhanced_trans) - len(current_trans)} MORE transactions!")
    elif len(current_trans) > len(enhanced_trans):
        print(f"\n⚠️  Current parser found {len(current_trans) - len(enhanced_trans)} MORE transactions")
    else:
        print(f"\n✓ Both parsers found the same number of transactions")
    
    # Financial summary
    print(f"\n💰 FINANCIAL SUMMARY")
    print("=" * 100)
    
    def calc_totals(trans_list):
        credits = sum(t['amount'] for t in trans_list if t['type'] == 'credit')
        debits = sum(t['amount'] for t in trans_list if t['type'] == 'debit')
        return credits, debits, credits - debits
    
    current_credits, current_debits, current_net = calc_totals(current_trans)
    enhanced_credits, enhanced_debits, enhanced_net = calc_totals(enhanced_trans)
    
    print(f"\nCurrent Parser:")
    print(f"  Credits:  R {current_credits:>12,.2f}")
    print(f"  Debits:   R {current_debits:>12,.2f}")
    print(f"  Net:      R {current_net:>12,.2f}")
    
    print(f"\nEnhanced Parser:")
    print(f"  Credits:  R {enhanced_credits:>12,.2f}")
    print(f"  Debits:   R {enhanced_debits:>12,.2f}")
    print(f"  Net:      R {enhanced_net:>12,.2f}")
    
    print(f"\nDifference:")
    print(f"  Credits:  R {(enhanced_credits - current_credits):>12,.2f}")
    print(f"  Debits:   R {(enhanced_debits - current_debits):>12,.2f}")
    print(f"  Net:      R {(enhanced_net - current_net):>12,.2f}")
    
    # Show sample of enhanced transactions
    print(f"\n📋 SAMPLE TRANSACTIONS (Enhanced Parser)")
    print("=" * 100)
    print(f"{'DATE':<12} {'DESCRIPTION':<50} {'TYPE':<8} {'AMOUNT':>12} {'BALANCE':>12}")
    print("-" * 100)
    
    for trans in enhanced_trans[:20]:
        desc = trans['description'][:49]
        trans_type = trans['type'].upper()
        amount = f"R {trans['amount']:,.2f}"
        balance = f"R {trans.get('balance', 0):,.2f}" if trans.get('balance') else "N/A"
        
        print(f"{trans['date']:<12} {desc:<50} {trans_type:<8} {amount:>12} {balance:>12}")
    
    if len(enhanced_trans) > 20:
        print(f"\n... and {len(enhanced_trans) - 20} more transactions")
    
    # Balance verification
    print(f"\n🔍 BALANCE VERIFICATION")
    print("=" * 100)
    
    # Check if all transactions have balance
    trans_with_balance = [t for t in enhanced_trans if t.get('balance') and t['balance'] != 0]
    trans_without_balance = [t for t in enhanced_trans if not t.get('balance') or t['balance'] == 0]
    
    print(f"Transactions WITH balance:    {len(trans_with_balance)}")
    print(f"Transactions WITHOUT balance: {len(trans_without_balance)}")
    
    if trans_without_balance:
        print(f"\n⚠️  Some transactions missing balance:")
        for trans in trans_without_balance[:5]:
            print(f"  - {trans['date']} | {trans['description'][:60]}")
        if len(trans_without_balance) > 5:
            print(f"  ... and {len(trans_without_balance) - 5} more")
    else:
        print(f"✅ All transactions have balance information!")
    
    # Check ordering
    print(f"\n📅 ORDERING VERIFICATION")
    print("=" * 100)
    
    # Pick a day with multiple transactions
    by_date = {}
    for trans in enhanced_trans:
        date_str = trans['date'].strftime('%Y-%m-%d')
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append(trans)
    
    # Find day with most transactions
    max_date = max(by_date.items(), key=lambda x: len(x[1]))
    date_str, day_trans = max_date
    
    print(f"Day with most transactions: {date_str} ({len(day_trans)} transactions)")
    print(f"\nVerifying balance ordering (balance should decrease through day):")
    print(f"{'#':<4} {'DESCRIPTION':<45} {'TYPE':<6} {'AMOUNT':>10} {'BALANCE':>10}")
    print("-" * 80)
    
    for idx, trans in enumerate(day_trans[:10], 1):
        desc = trans['description'][:44]
        trans_type = trans['type'].upper()[:2]
        amount = f"{trans['amount']:,.2f}"
        balance = f"{trans.get('balance', 0):,.2f}"
        print(f"{idx:<4} {desc:<45} {trans_type:<6} {amount:>10} {balance:>10}")
    
    if len(day_trans) > 10:
        print(f"... and {len(day_trans) - 10} more transactions for this day")
    
    # Check if balance is properly descending
    balances = [t.get('balance', 0) for t in day_trans if t.get('balance')]
    if balances:
        is_ordered = all(balances[i] >= balances[i+1] for i in range(len(balances)-1))
        if is_ordered:
            print(f"\n✅ Transactions properly ordered by balance!")
        else:
            print(f"\n⚠️  Some transactions may be out of order")
            # Show where ordering breaks
            for i in range(len(balances)-1):
                if balances[i] < balances[i+1]:
                    print(f"  Order break at position {i+1}: {balances[i]:.2f} -> {balances[i+1]:.2f}")
    
    print(f"\n" + "=" * 100)
    print("✅ Comparison complete!")
    print("=" * 100)

if __name__ == '__main__':
    compare_parsers()
