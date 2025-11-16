"""
Celery Tasks for LiquidSuite
Background task definitions for async operations
"""
from celery_app import celery_app
from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import BankTransaction, ERPNextConfig, ERPNextSyncLog, IncomingTransaction
from lsuite.erpnext.services import ERPNextService
import os


# Create Flask app context for tasks
flask_app = create_app(os.getenv('FLASK_ENV', 'development'))


@celery_app.task(bind=True, name='lsuite.tasks.sync_transaction_to_erpnext')
def sync_transaction_to_erpnext(self, transaction_id, user_id):
    """
    Sync a single transaction to ERPNext
    
    Args:
        transaction_id: ID of the BankTransaction to sync
        user_id: ID of the user performing the sync
    
    Returns:
        dict: Result with success status and message
    """
    with flask_app.app_context():
        try:
            # Update task state
            self.update_state(state='PROCESSING', meta={'current': 1, 'total': 1})
            
            # Get transaction
            transaction = BankTransaction.query.get(transaction_id)
            if not transaction:
                return {
                    'success': False,
                    'message': f'Transaction {transaction_id} not found'
                }
            
            # Verify user owns transaction
            if transaction.user_id != user_id:
                return {
                    'success': False,
                    'message': 'Unauthorized'
                }
            
            # Check if categorized
            if not transaction.category_id:
                return {
                    'success': False,
                    'message': 'Transaction must be categorized first'
                }
            
            # Get active ERPNext config
            config = ERPNextConfig.query.filter_by(
                user_id=user_id,
                is_active=True
            ).first()
            
            if not config:
                return {
                    'success': False,
                    'message': 'No active ERPNext configuration'
                }
            
            # Perform sync
            service = ERPNextService(config)
            journal_entry_name = service.create_journal_entry(transaction)
            
            # Log to incoming transactions
            incoming = IncomingTransaction(
                transaction_id=transaction.id,
                user_id=user_id,
                transaction_type='erpnext_sync',
                status='success',
                erpnext_journal_entry=journal_entry_name,
                request_data={
                    'transaction_id': transaction_id,
                    'category': transaction.category.name if transaction.category else None
                },
                response_data={
                    'journal_entry': journal_entry_name
                }
            )
            db.session.add(incoming)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Synced successfully: {journal_entry_name}',
                'journal_entry': journal_entry_name
            }
            
        except Exception as e:
            # Log error to incoming transactions
            incoming = IncomingTransaction(
                transaction_id=transaction_id,
                user_id=user_id,
                transaction_type='erpnext_sync',
                status='failed',
                error_message=str(e),
                request_data={'transaction_id': transaction_id}
            )
            db.session.add(incoming)
            db.session.commit()
            
            return {
                'success': False,
                'message': f'Sync failed: {str(e)}'
            }


@celery_app.task(bind=True, name='lsuite.tasks.sync_bulk_transactions_to_erpnext')
def sync_bulk_transactions_to_erpnext(self, transaction_ids, user_id):
    """
    Sync multiple transactions to ERPNext
    
    Args:
        transaction_ids: List of BankTransaction IDs to sync
        user_id: ID of the user performing the sync
    
    Returns:
        dict: Result with success/fail counts and messages
    """
    with flask_app.app_context():
        results = {
            'success_count': 0,
            'fail_count': 0,
            'messages': []
        }
        
        total = len(transaction_ids)
        
        for idx, transaction_id in enumerate(transaction_ids, 1):
            # Update progress
            self.update_state(
                state='PROCESSING',
                meta={
                    'current': idx,
                    'total': total,
                    'success': results['success_count'],
                    'failed': results['fail_count']
                }
            )
            
            # Sync individual transaction
            result = sync_transaction_to_erpnext(transaction_id, user_id)
            
            if result['success']:
                results['success_count'] += 1
                results['messages'].append(f"✓ {result['message']}")
            else:
                results['fail_count'] += 1
                results['messages'].append(f"✗ {result['message']}")
        
        return results


@celery_app.task(name='lsuite.tasks.test_task')
def test_task(message):
    """Test task to verify Celery is working"""
    return f"Test task received: {message}"
