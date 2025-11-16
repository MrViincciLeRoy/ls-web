"""
Compare old vs new parser results
Shows what transactions were missing before
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def parse_with_old():
    """Parse using backup (old) parser"""
    from lsuite.gmail import parsers_backup as old_parser
    
    pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'account_statement.pdf')
    
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    parser = old_parser.PDFParser()
    return parser.parse_pdf(pdf_data, 'capitec', None)

def parse_with_new():
    """Parse using new parser"""
    from lsuite.gmail.parsers import PDFParser
    
    pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'account_statement.pdf')
    
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    parser = PDFParser()
    return parser.parse_pdf(pdf_data, 'capitec', None)

def main():
    print("\n" + "="*100)
    print("COMPARING OLD vs NEW PARSER")
    print("="*100 + "\n")
    
    try:
        print("📋 Parsing with OLD parser...")
        old_transactions = parse_with_old()
        print(f"   Found: {len(old_transactions)} transactions\n")
        
        print("📋 Parsing with NEW parser...")
        new_transactions = parse_with_new()
        print(f"   Found: {len(new_transactions)} transactions\n")
        
        # Compare
        improvement = len(new_transactions) - len(old_transactions)
        improvement_pct = (improvement / len(old_transactions) * 100) if len(old_transactions) > 0 else 0
        
        print("="*100)
        print("RESULTS:")
        print("="*100)
        print(f"Old Parser:     {len(old_transactions)} transactions")
        print(f"New Parser:     {len(new_transactions)} transactions")
        print(f"Improvement:    +{improvement} transactions ({improvement_pct:+.1f}%)")
        print("="*100 + "\n")
        
        if improvement > 0:
            print(f"✅ SUCCESS! The new parser found {improvement} additional transactions!\n")
            
            # Show some examples of newly found transactions
            print("Examples of newly captured transactions:")
            print("-"*100)
            
            # Create signature for comparison
            def make_sig(t):
                return f"{t['date']}_{t['description'][:30]}_{t['amount']}"
            
            old_sigs = {make_sig(t) for t in old_transactions}
            new_only = [t for t in new_transactions if make_sig(t) not in old_sigs]
            
            for i, trans in enumerate(new_only[:10], 1):  # Show first 10
                print(f"{i}. {trans['date']} | {trans['description'][:50]:<50} | R{trans['amount']:>10,.2f} | {trans['type'].upper()}")
            
            if len(new_only) > 10:
                print(f"   ... and {len(new_only) - 10} more")
            
            print("-"*100)
            
        elif improvement < 0:
            print(f"⚠️ WARNING: New parser found {abs(improvement)} fewer transactions!")
            print("   This might indicate an issue. Please review carefully.")
        else:
            print("ℹ️ Both parsers found the same number of transactions.")
            print("   The improvement may be in fee extraction or classification.")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
