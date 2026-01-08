"""
Enhanced Health Check - Add to lsuite/main/routes.py
"""
from flask import jsonify
from datetime import datetime
from sqlalchemy import text, inspect
from lsuite.extensions import db


@main_bp.route('/health')
def health_check():
    """Enhanced health check with database validation"""
    health = {
        'status': 'ok',
        'app': 'LSuite',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    try:
        # Database connection test
        db.session.execute(text('SELECT 1'))
        health['database'] = 'connected'
        
        # Check critical tables
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        
        critical_tables = [
            'users',
            'bank_transactions',
            'transaction_categories',
            'email_statements'
        ]
        
        bi_tables = [
            'uploaded_documents',
            'document_transactions',
            'cash_flow_forecasts',
            'business_statements'
        ]
        
        missing_critical = [t for t in critical_tables if t not in existing_tables]
        missing_bi = [t for t in bi_tables if t not in existing_tables]
        
        health['tables'] = {
            'total': len(existing_tables),
            'critical_ok': len(missing_critical) == 0,
            'bi_ok': len(missing_bi) == 0,
            'missing_critical': missing_critical,
            'missing_bi': missing_bi
        }
        
        # Overall status
        if missing_critical:
            health['status'] = 'degraded'
            health['message'] = 'Critical tables missing. Run: flask db upgrade'
        elif missing_bi:
            health['status'] = 'warning'
            health['message'] = 'BI tables missing. Run: flask db-fix'
        
        # Count records in key tables
        try:
            from lsuite.models import User, BankTransaction, EmailStatement
            health['records'] = {
                'users': User.query.count(),
                'transactions': BankTransaction.query.count(),
                'statements': EmailStatement.query.count()
            }
        except Exception as e:
            health['records'] = {'error': str(e)}
        
        status_code = 200 if health['status'] == 'ok' else 503
        return jsonify(health), status_code
        
    except Exception as e:
        health['status'] = 'error'
        health['database'] = f'error: {str(e)}'
        health['message'] = 'Database connection failed'
        return jsonify(health), 503


@main_bp.route('/health/db')
def health_db():
    """Detailed database health check"""
    try:
        from lsuite.utils.db_checker import DatabaseChecker
        
        checker = DatabaseChecker()
        all_ok, issues = checker.full_check()
        
        return jsonify({
            'status': 'ok' if all_ok else 'issues_found',
            'all_ok': all_ok,
            'issue_count': len(issues),
            'issues': issues,
            'report': checker.generate_report(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
