"""
Test script for Capitec PDF Parser
Tests category extraction, credit/debit detection, and balance tracking
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite.gmail.parsers_capitec import CapitecPDFParser
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_capitec_parser(pdf_path, password=None):
    """
    Test Capitec parser with a PDF file
    
    Args:
        pdf_path: Path to Capitec PDF statement
        password: PDF password if protected
    """
    logger.info(f"Testing Capitec parser with: {pdf_path}")
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return
    
    # Read PDF file
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    logger.info(f"PDF file size: {len(pdf_data)} bytes")
    
    # Create parser
    parser = CapitecPDFParser()
    
    try:
        # Parse PDF
        result = parser.parse_pdf(pdf_data, password)
        
        transactions = result['transactions']
        statement_info = result['statement_info']
        
        # Display statement info
        logger.info("=" * 80)
        logger.info("STATEMENT INFORMATION")
        logger.info("=" * 80)
        for key, value in statement_info.items():
            logger.info(f"{key}: {value}")
        
        # Display transactions
        logger.info("=" * 80)
        logger.info(f"TRANSACTIONS ({len(transactions)} total)")
        logger.info("=" * 80)
        
        # Group by date
        from collections import defaultdict
        by_date = defaultdict(list)
        
        for trans in transactions:
            by_date[trans['date']].append(trans)
        
        # Display by date
        total_credits = 0
        total_debits = 0
        
        for date in sorted(by_date.keys(), reverse=True):
            logger.info(f"\n{date.strftime('%d %B %Y')}")
            logger.info("-" * 80)
            
            for trans in by_date[date]:
                trans_type = trans['type'].upper()
                amount = trans['amount']
                category = trans.get('category', 'N/A')
                balance = trans.get('balance', 'N/A')
                
                # Track totals
                if trans['type'] == 'credit':
                    total_credits += amount
                else:
                    total_debits += amount
                
                # Format output
                logger.info(
                    f"  {trans_type:6} | R{amount:>10.2f} | Bal: R{balance if isinstance(balance, str) else f'{balance:,.2f}'} | "
                    f"Cat: {category:20} | {trans['description'][:50]}"
                )
        
        # Summary
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Credits:     R {total_credits:>12,.2f}")
        logger.info(f"Total Debits:      R {total_debits:>12,.2f}")
        logger.info(f"Net Movement:      R {(total_credits - total_debits):>12,.2f}")
        logger.info(f"Total Transactions: {len(transactions)}")
        
        # Category breakdown
        logger.info("\n" + "=" * 80)
        logger.info("CATEGORY BREAKDOWN")
        logger.info("=" * 80)
        
        from collections import Counter
        categories = [t.get('category', 'Uncategorised') for t in transactions]
        category_counts = Counter(categories)
        
        for category, count in category_counts.most_common():
            # Calculate total for this category
            cat_total = sum(
                t['amount'] for t in transactions 
                if t.get('category') == category
            )
            logger.info(f"  {category:30} | {count:3} trans | R {cat_total:>10,.2f}")
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Parser error: {e}", exc_info=True)


if __name__ == '__main__':
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python test_capitec_parser.py <path_to_pdf> [password]")
        print("\nExample:")
        print("  python test_capitec_parser.py data/capitec_statement.pdf")
        print("  python test_capitec_parser.py data/capitec_statement.pdf mypassword")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else None
    
    test_capitec_parser(pdf_path, password)
