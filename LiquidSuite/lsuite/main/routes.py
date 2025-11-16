# ============================================================================
# lsuite/main/routes.py - ENHANCED WITH INSIGHTS - FIXED
# ============================================================================
"""
Main Blueprint - Dashboard and Home
"""
from flask import render_template, jsonify
from flask_login import login_required, current_user
from lsuite.models import (
    EmailStatement, BankTransaction, TransactionCategory,
    ERPNextConfig, ERPNextSyncLog
)
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from collections import defaultdict
from lsuite.main import main_bp
import calendar


@main_bp.route('/')
@login_required
def index():
    """Dashboard home page with insights"""
    
    # Date range for insights - default last 30 days
    days = 30
    start_date = datetime.now() - timedelta(days=days)
    
    # Initialize all variables with defaults
    stats = {'statements': 0, 'transactions': 0, 'categorized': 0, 'synced': 0}
    recent_statements = []
    recent_transactions = []
    total_expenses = 0
    total_income = 0
    total_transactions_count = 0
    top_suppliers = []
    categories = []
    uncategorized_count = 0
    monthly_trends = []
    sync_success = 0
    sync_failed = 0
    synced_count = 0
    pending_sync = 0
    recent_syncs = []
    erpnext_config = None
    ready_to_sync = 0
    period_transactions = []
    
    try:
        # Get statistics
        stats = {
            'statements': EmailStatement.query.count(),
            'transactions': BankTransaction.query.count(),
            'categorized': BankTransaction.query.filter(
                BankTransaction.category_id.isnot(None)
            ).count(),
            'synced': BankTransaction.query.filter_by(erpnext_synced=True).count(),
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
    
    try:
        # Recent statements
        recent_statements = EmailStatement.query.order_by(
            EmailStatement.received_date.desc()
        ).limit(5).all()
    except Exception as e:
        print(f"Error getting recent statements: {e}")
    
    try:
        # Recent transactions
        recent_transactions = BankTransaction.query.order_by(
            BankTransaction.date.desc()
        ).limit(10).all()
    except Exception as e:
        print(f"Error getting recent transactions: {e}")
    
    # ========== INSIGHTS DATA ==========
    
    try:
        # Get transactions for period
        period_transactions = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.date >= start_date.date()
        ).all()
        
        # Calculate financial metrics
        total_expenses = sum(float(t.withdrawal or 0) for t in period_transactions)
        total_income = sum(float(t.deposit or 0) for t in period_transactions)
        total_transactions_count = len(period_transactions)
        
    except Exception as e:
        print(f"Error calculating financial metrics: {e}")
        period_transactions = []
    
    try:
        # Top 5 suppliers - only if we have transactions
        if period_transactions:
            supplier_stats = defaultdict(lambda: {'count': 0, 'total': 0})
            for t in period_transactions:
                if t.withdrawal and t.withdrawal > 0:
                    desc = t.description[:50] if t.description else 'Unknown'
                    supplier_stats[desc]['count'] += 1
                    supplier_stats[desc]['total'] += float(t.withdrawal)
            
            top_suppliers = sorted(
                [{'name': k, 'count': v['count'], 'total': v['total']} 
                 for k, v in supplier_stats.items()],
                key=lambda x: x['total'],
                reverse=True
            )[:5]
    except Exception as e:
        print(f"Error calculating top suppliers: {e}")
    
    try:
        # Category breakdown (top 5)
        from lsuite.extensions import db
        category_stats = db.session.query(
            TransactionCategory.name,
            func.count(BankTransaction.id).label('count'),
            func.sum(BankTransaction.withdrawal).label('expenses'),
            func.sum(BankTransaction.deposit).label('income')
        ).join(
            BankTransaction
        ).filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.date >= start_date.date()
        ).group_by(
            TransactionCategory.name
        ).order_by(
            func.sum(BankTransaction.withdrawal).desc()
        ).limit(5).all()
        
        categories = [
            {
                'name': c.name,
                'count': c.count,
                'expenses': float(c.expenses or 0),
                'income': float(c.income or 0)
            }
            for c in category_stats
        ]
    except Exception as e:
        print(f"Error getting categories: {e}")
    
    try:
        # Uncategorized count
        uncategorized_count = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.category_id == None,
            BankTransaction.date >= start_date.date()
        ).count()
    except Exception as e:
        print(f"Error getting uncategorized count: {e}")
    
    try:
        # Monthly trends (last 6 months)
        from lsuite.extensions import db
        monthly_data = db.session.query(
            extract('year', BankTransaction.date).label('year'),
            extract('month', BankTransaction.date).label('month'),
            func.sum(BankTransaction.withdrawal).label('expenses'),
            func.sum(BankTransaction.deposit).label('income')
        ).filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.date >= (datetime.now() - timedelta(days=180)).date()
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        monthly_trends = [
            {
                'month': calendar.month_abbr[int(m.month)],
                'year': int(m.year),
                'expenses': float(m.expenses or 0),
                'income': float(m.income or 0)
            }
            for m in monthly_data
        ]
    except Exception as e:
        print(f"Error getting monthly trends: {e}")
    
    try:
        # ERPNext sync status
        sync_success = ERPNextSyncLog.query.filter_by(status='success').count()
        sync_failed = ERPNextSyncLog.query.filter_by(status='failed').count()
        
        synced_count = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.erpnext_synced == True
        ).count()
        
        pending_sync = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.erpnext_synced == False,
            BankTransaction.category_id != None
        ).count()
    except Exception as e:
        print(f"Error getting sync status: {e}")
    
    try:
        # Recent sync logs
        recent_syncs = ERPNextSyncLog.query.order_by(
            ERPNextSyncLog.sync_date.desc()
        ).limit(5).all()
    except Exception as e:
        print(f"Error getting recent syncs: {e}")
    
    try:
        # ERPNext config status
        erpnext_config = ERPNextConfig.query.filter_by(is_active=True).first()
    except Exception as e:
        print(f"Error getting ERPNext config: {e}")
    
    try:
        # Calculate ready to sync
        ready_to_sync = BankTransaction.query.filter(
            BankTransaction.category_id.isnot(None),
            BankTransaction.erpnext_synced == False
        ).count()
    except Exception as e:
        print(f"Error getting ready to sync: {e}")
    
    return render_template(
        'main/index.html',
        stats=stats,
        recent_statements=recent_statements,
        recent_transactions=recent_transactions,
        recent_syncs=recent_syncs,
        erpnext_config=erpnext_config,
        ready_to_sync=ready_to_sync,
        # Insights data
        total_expenses=total_expenses,
        total_income=total_income,
        total_transactions_count=total_transactions_count,
        top_suppliers=top_suppliers,
        categories=categories,
        uncategorized_count=uncategorized_count,
        monthly_trends=monthly_trends,
        sync_success=sync_success,
        sync_failed=sync_failed,
        synced_count=synced_count,
        pending_sync=pending_sync,
        days=days
    )


@main_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring (no authentication required)"""
    try:
        from lsuite.extensions import db
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'ok',
        'app': 'LSuite',
        'version': '1.0.0',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@main_bp.route('/about')
def about():
    """About page"""
    return render_template('main/about.html')
