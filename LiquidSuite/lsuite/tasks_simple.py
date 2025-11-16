"""
Simple Background Tasks for LiquidSuite (No Celery/Redis Required)
Uses threading for background processing
"""
import threading
import time
from datetime import datetime
from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import BankTransaction, ERPNextConfig, ERPNextSyncLog, IncomingTransaction
from lsuite.erpnext.services import ERPNextService
import os


# Task status storage (in-memory)
task_status = {}


def update_task_status(task_id, state, info=None):
    """Update task status in memory"""
    task_status[task_id] = {
        'state': state,
        'info': info,
        'updated_at': datetime.utcnow()
    }


def get_task_status(task_id):
    """Get task status"""
    return task_status.get(task_id, {'state': 'PENDING', 'info': None})


def sync_transaction_to_erpnext(transaction_id, user_id, task_id=None):
    """
    Sync a single transaction to ERPNext
    
    Args:
        transaction_id: ID of the BankTransaction to sync
        user_id: ID of the user performing the sync
        task_id: Optional task ID for status tracking
    
    Returns:
        dict: Result with success status and message
    """
    flask_app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with flask_app.app_context():
        try:
            # Update task state
            if task_id:
                update_task_status(task_id, 'PROCESSING', {'current': 1, 'total': 1})
            
            # Get transaction
            transaction = BankTransaction.query.get(transaction_id)
            if not transaction:
                result = {
                    'success': False,
                    'message': f'Transaction {transaction_id} not found'
                }
                if task_id:
                    update_task_status(task_id, 'FAILURE', result)
                return result
            
            # Verify user owns transaction
            if transaction.user_id != user_id:
                result = {
                    'success': False,
                    'message': 'Unauthorized'
                }
                if task_id:
                    update_task_status(task_id, 'FAILURE', result)
                return result
            
            # Check if categorized
            if not transaction.category_id:
                result = {
                    'success': False,
                    'message': 'Transaction must be categorized first'
                }
                if task_id:
                    update_task_status(task_id, 'FAILURE', result)
                return result
            
            # Get active ERPNext config
            config = ERPNextConfig.query.filter_by(
                user_id=user_id,
                is_active=True
            ).first()
            
            if not config:
                result = {
                    'success': False,
                    'message': 'No active ERPNext configuration'
                }
                if task_id:
                    update_task_status(task_id, 'FAILURE', result)
                return result
            
            # Perform sync
            service = ERPNextService(config)
            journal_entry_name = service.create_journal_entry(transaction)
            
            # Update incoming transaction
            incoming = IncomingTransaction.query.filter_by(task_id=task_id).first()
            if incoming:
                incoming.status = 'success'
                incoming.erpnext_journal_entry = journal_entry_name
                incoming.response_data = {'journal_entry': journal_entry_name}
                incoming.completed_at = datetime.utcnow()
                db.session.commit()
            
            result = {
                'success': True,
                'message': f'Synced successfully: {journal_entry_name}',
                'journal_entry': journal_entry_name
            }
            
            if task_id:
                update_task_status(task_id, 'SUCCESS', result)
            
            return result
            
        except Exception as e:
            # Update incoming transaction
            incoming = IncomingTransaction.query.filter_by(task_id=task_id).first()
            if incoming:
                incoming.status = 'failed'
                incoming.error_message = str(e)
                incoming.completed_at = datetime.utcnow()
                db.session.commit()
            
            result = {
                'success': False,
                'message': f'Sync failed: {str(e)}'
            }
            
            if task_id:
                update_task_status(task_id, 'FAILURE', result)
            
            return result


def sync_bulk_transactions_to_erpnext(transaction_ids, user_id, task_id=None):
    """
    Sync multiple transactions to ERPNext
    
    Args:
        transaction_ids: List of BankTransaction IDs to sync
        user_id: ID of the user performing the sync
        task_id: Optional task ID for status tracking
    
    Returns:
        dict: Result with success/fail counts and messages
    """
    flask_app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with flask_app.app_context():
        results = {
            'success_count': 0,
            'fail_count': 0,
            'messages': []
        }
        
        total = len(transaction_ids)
        
        for idx, transaction_id in enumerate(transaction_ids, 1):
            # Update progress
            if task_id:
                update_task_status(
                    task_id,
                    'PROCESSING',
                    {
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
        
        # Update incoming transaction
        incoming = IncomingTransaction.query.filter_by(task_id=task_id).first()
        if incoming:
            incoming.status = 'success' if results['fail_count'] == 0 else 'partial'
            incoming.response_data = results
            incoming.completed_at = datetime.utcnow()
            db.session.commit()
        
        if task_id:
            update_task_status(task_id, 'SUCCESS', results)
        
        return results


def run_task_async(func, *args, **kwargs):
    """
    Run a function in a background thread
    
    Returns:
        str: Task ID
    """
    task_id = f"task_{int(time.time() * 1000)}"
    
    def wrapper():
        try:
            func(*args, task_id=task_id, **kwargs)
        except Exception as e:
            update_task_status(task_id, 'FAILURE', {'error': str(e)})
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    
    update_task_status(task_id, 'PENDING', None)
    
    return task_id
