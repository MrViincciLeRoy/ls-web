"""
Celery Application Configuration for LiquidSuite
Background task processing for ERPNext sync and other async operations
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Initialize Celery
celery_app = Celery(
    'lsuite',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=['lsuite.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Johannesburg',
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        'lsuite.tasks.sync_transaction_to_erpnext': {'queue': 'erpnext'},
        'lsuite.tasks.sync_bulk_transactions_to_erpnext': {'queue': 'erpnext'},
    },
)

if __name__ == '__main__':
    celery_app.start()
