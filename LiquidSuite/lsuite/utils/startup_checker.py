"""
Startup Database Checker
Location: lsuite/utils/startup_checker.py

Automatically checks database on application startup
"""
import logging
from sqlalchemy import text, inspect
from lsuite.extensions import db

logger = logging.getLogger(__name__)


def check_database_on_startup(app):
    """Check database schema on startup and warn if issues found"""
    
    with app.app_context():
        try:
            # Quick connection test
            db.session.execute(text('SELECT 1'))
            logger.info("✓ Database connection successful")
            
            # Check critical tables
            inspector = inspect(db.engine)
            existing_tables = set(inspector.get_table_names())
            
            # Critical tables for basic operation
            critical_tables = [
                'users',
                'bank_accounts',
                'bank_transactions',
                'transaction_categories',
                'email_statements'
            ]
            
            # Business Intelligence tables
            bi_tables = [
                'uploaded_documents',
                'document_transactions',
                'cash_flow_forecasts',
                'business_statements'
            ]
            
            missing_critical = [t for t in critical_tables if t not in existing_tables]
            missing_bi = [t for t in bi_tables if t not in existing_tables]
            
            if missing_critical:
                logger.error("="*60)
                logger.error("CRITICAL: Missing essential database tables!")
                logger.error("Missing tables: " + ", ".join(missing_critical))
                logger.error("Run: flask db upgrade")
                logger.error("="*60)
                return False
            
            if missing_bi:
                logger.warning("="*60)
                logger.warning("⚠ Missing Business Intelligence tables")
                logger.warning("Missing: " + ", ".join(missing_bi))
                logger.warning("Run: flask db-fix (to auto-create)")
                logger.warning("Or: flask db migrate -m 'Add BI tables' && flask db upgrade")
                logger.warning("="*60)
            else:
                logger.info("✓ All Business Intelligence tables present")
            
            logger.info(f"✓ Database schema check complete ({len(existing_tables)} tables)")
            return True
            
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False


def ensure_bi_tables(app):
    """Ensure Business Intelligence tables exist, create if missing"""
    
    with app.app_context():
        try:
            from lsuite.utils.db_checker import DatabaseChecker
            
            checker = DatabaseChecker()
            bi_tables = [
                'uploaded_documents',
                'document_transactions', 
                'cash_flow_forecasts',
                'business_statements'
            ]
            
            results = checker.check_specific_tables(bi_tables)
            missing = [t for t, info in results.items() if not info['exists']]
            
            if missing:
                logger.warning(f"Creating missing BI tables: {missing}")
                
                # Create tables directly using metadata
                from lsuite.models import (
                    UploadedDocument, 
                    DocumentTransaction,
                    CashFlowForecast, 
                    BusinessStatement
                )
                
                db.create_all()
                logger.info("✓ Business Intelligence tables created")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Could not ensure BI tables: {e}")
            return False


def safe_table_check(table_name):
    """Safely check if table exists"""
    try:
        inspector = inspect(db.engine)
        return table_name in inspector.get_table_names()
    except:
        return False


def get_database_stats():
    """Get database statistics"""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        stats = {
            'total_tables': len(tables),
            'tables': tables,
            'status': 'healthy'
        }
        
        # Count rows in major tables
        try:
            from lsuite.models import User, BankTransaction, EmailStatement
            stats['users'] = User.query.count()
            stats['transactions'] = BankTransaction.query.count()
            stats['statements'] = EmailStatement.query.count()
        except:
            pass
        
        return stats
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
