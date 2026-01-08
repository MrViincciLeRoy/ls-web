"""
Auto Table Creator - Automatically creates missing database tables on startup
Location: lsuite/utils/auto_table_creator.py
"""
import logging
from sqlalchemy import inspect, text
from lsuite.extensions import db

logger = logging.getLogger(__name__)


def auto_create_tables(app):
    """Automatically create missing tables on startup"""
    
    try:
        # Test database connection first
        db.session.execute(text('SELECT 1'))
        logger.info("✓ Database connection successful")
        
        # Get existing tables
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        
        # Define all required tables with their models
        required_tables = {
            'users': 'User',
            'bank_accounts': 'BankAccount',
            'transactions': 'Transaction',
            'bank_transactions': 'BankTransaction',
            'transaction_categories': 'TransactionCategory',
            'email_statements': 'EmailStatement',
            'google_credentials': 'GoogleCredential',
            'invoices': 'Invoice',
            'invoice_items': 'InvoiceItem',
            'erpnext_configs': 'ERPNextConfig',
            'erpnext_sync_logs': 'ERPNextSyncLog',
            'uploaded_documents': 'UploadedDocument',
            'document_transactions': 'DocumentTransaction',
            'cash_flow_forecasts': 'CashFlowForecast',
            'business_statements': 'BusinessStatement'
        }
        
        # Find missing tables
        missing_tables = [t for t in required_tables.keys() if t not in existing_tables]
        
        if missing_tables:
            logger.warning("="*60)
            logger.warning(f"⚠ Missing {len(missing_tables)} tables detected")
            logger.warning(f"Tables: {', '.join(missing_tables)}")
            logger.warning("Auto-creating missing tables...")
            logger.warning("="*60)
            
            # Import all models to ensure they're registered with SQLAlchemy
            from lsuite.models import (
                User, BankAccount, Transaction, BankTransaction, 
                TransactionCategory, EmailStatement, GoogleCredential,
                Invoice, InvoiceItem, ERPNextConfig, ERPNextSyncLog,
                UploadedDocument, DocumentTransaction,
                CashFlowForecast, BusinessStatement
            )
            
            # Create all missing tables
            db.create_all()
            
            # Verify creation
            inspector = inspect(db.engine)
            new_tables = set(inspector.get_table_names())
            created = [t for t in missing_tables if t in new_tables]
            still_missing = [t for t in missing_tables if t not in new_tables]
            
            if created:
                logger.info("="*60)
                logger.info(f"✓ Successfully created {len(created)} tables:")
                for table in created:
                    logger.info(f"  ✓ {table}")
                logger.info("="*60)
            
            if still_missing:
                logger.error("="*60)
                logger.error(f"✗ Failed to create {len(still_missing)} tables:")
                for table in still_missing:
                    logger.error(f"  ✗ {table}")
                logger.error("Run: flask db migrate && flask db upgrade")
                logger.error("="*60)
        else:
            logger.info(f"✓ All {len(required_tables)} required tables exist")
        
        # Log table counts
        if existing_tables or missing_tables:
            logger.info(f"Database has {len(existing_tables) + len(missing_tables)} total tables")
        
        return len(missing_tables) == 0
        
    except Exception as e:
        logger.error(f"Auto-create tables failed: {e}")
        logger.error("Database may be unavailable or migrations needed")
        return False


def verify_critical_tables(app):
    """Verify critical tables exist for basic app functionality"""
    
    critical_tables = [
        'users',
        'bank_accounts', 
        'bank_transactions',
        'transaction_categories'
    ]
    
    try:
        inspector = inspect(db.engine)
        existing = set(inspector.get_table_names())
        
        missing_critical = [t for t in critical_tables if t not in existing]
        
        if missing_critical:
            logger.error("="*60)
            logger.error("CRITICAL: Missing essential tables!")
            logger.error(f"Missing: {', '.join(missing_critical)}")
            logger.error("App functionality will be limited")
            logger.error("="*60)
            return False
        
        logger.info("✓ All critical tables present")
        return True
        
    except Exception as e:
        logger.error(f"Critical table check failed: {e}")
        return False


def get_table_stats():
    """Get statistics about database tables"""
    
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        stats = {
            'total_tables': len(tables),
            'tables': sorted(tables)
        }
        
        # Try to get row counts for main tables
        try:
            from lsuite.models import User, BankTransaction, EmailStatement, UploadedDocument
            
            stats['users'] = User.query.count()
            stats['transactions'] = BankTransaction.query.count()
            stats['statements'] = EmailStatement.query.count()
            stats['documents'] = UploadedDocument.query.count()
            
        except Exception as e:
            logger.debug(f"Could not get row counts: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Could not get table stats: {e}")
        return {'total_tables': 0, 'tables': []}


def check_bi_tables_exist():
    """Check if Business Intelligence tables exist"""
    
    bi_tables = [
        'uploaded_documents',
        'document_transactions',
        'cash_flow_forecasts',
        'business_statements'
    ]
    
    try:
        inspector = inspect(db.engine)
        existing = set(inspector.get_table_names())
        
        missing = [t for t in bi_tables if t not in existing]
        
        if missing:
            logger.warning(f"Missing BI tables: {', '.join(missing)}")
            return False
        
        logger.info("✓ All Business Intelligence tables present")
        return True
        
    except Exception as e:
        logger.error(f"BI table check failed: {e}")
        return False
