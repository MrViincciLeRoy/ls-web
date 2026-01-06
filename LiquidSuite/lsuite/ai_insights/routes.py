"""
AI Insights Routes - Full implementation matching Insights module
Location: lsuite/ai_insights/routes.py
"""
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from collections import defaultdict
from lsuite.ai_insights import ai_insights_bp
from lsuite.extensions import db
from lsuite.models import BankTransaction, TransactionCategory, ERPNextSyncLog
from lsuite.services.ai_service import get_ai_service
import calendar
import logging

logger = logging.getLogger(__name__)


@ai_insights_bp.route('/dashboard')
@login_required
def dashboard():
    """AI-powered insights dashboard (matches insights/dashboard)"""
    
    days = request.args.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).all()
    
    # Top suppliers
    supplier_stats = defaultdict(lambda: {'count': 0, 'total': 0})
    for t in transactions:
        if t.withdrawal and t.withdrawal > 0:
            desc = t.description[:50]
            supplier_stats[desc]['count'] += 1
            supplier_stats[desc]['total'] += float(t.withdrawal)
    
    top_suppliers = sorted(
        [{'name': k, 'count': v['count'], 'total': v['total']} 
         for k, v in supplier_stats.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:10]
    
    # Recurring transactions
    recurring = defaultdict(lambda: {'count': 0, 'amounts': []})
    for t in transactions:
        desc = t.description[:50]
        recurring[desc]['count'] += 1
        recurring[desc]['amounts'].append(float(t.withdrawal or t.deposit or 0))
    
    recurring_transactions = [
        {
            'description': k,
            'count': v['count'],
            'avg_amount': sum(v['amounts']) / len(v['amounts']),
            'total': sum(v['amounts'])
        }
        for k, v in recurring.items() if v['count'] >= 3
    ]
    recurring_transactions = sorted(recurring_transactions, key=lambda x: x['count'], reverse=True)[:10]
    
    # Category breakdown
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
    ).all()
    
    categories = [
        {
            'name': c.name,
            'count': c.count,
            'expenses': float(c.expenses or 0),
            'income': float(c.income or 0)
        }
        for c in category_stats
    ]
    
    # Uncategorized
    uncategorized_count = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.category_id == None,
        BankTransaction.date >= start_date.date()
    ).count()
    
    # Monthly trends
    monthly_data = db.session.query(
        extract('year', BankTransaction.date).label('year'),
        extract('month', BankTransaction.date).label('month'),
        func.sum(BankTransaction.withdrawal).label('expenses'),
        func.sum(BankTransaction.deposit).label('income'),
        func.count(BankTransaction.id).label('count')
    ).filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).group_by('year', 'month').order_by('year', 'month').all()
    
    monthly_trends = [
        {
            'month': calendar.month_abbr[int(m.month)],
            'year': int(m.year),
            'expenses': float(m.expenses or 0),
            'income': float(m.income or 0),
            'count': m.count
        }
        for m in monthly_data
    ]
    
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
    
    # Summary stats
    total_expenses = sum(float(t.withdrawal or 0) for t in transactions)
    total_income = sum(float(t.deposit or 0) for t in transactions)
    total_transactions = len(transactions)
    avg_transaction = (total_expenses + total_income) / total_transactions if total_transactions > 0 else 0
    
    # Prepare AI analysis data
    transaction_data = [{
        'date': t.date.isoformat(),
        'description': t.description,
        'withdrawal': float(t.withdrawal or 0),
        'deposit': float(t.deposit or 0),
        'category': t.category.name if t.category else 'Uncategorized'
    } for t in transactions]
    
    ai_service = get_ai_service()
    summary = ai_service.prepare_transaction_summary(transaction_data)
    
    return render_template('ai_insights/dashboard.html',
        days=days,
        top_suppliers=top_suppliers,
        recurring_transactions=recurring_transactions,
        categories=categories,
        uncategorized_count=uncategorized_count,
        monthly_trends=monthly_trends,
        sync_success=sync_success,
        sync_failed=sync_failed,
        synced_count=synced_count,
        pending_sync=pending_sync,
        total_expenses=total_expenses,
        total_income=total_income,
        total_transactions=total_transactions,
        avg_transaction=avg_transaction,
        transaction_data=transaction_data,
        transaction_summary=summary
    )


@ai_insights_bp.route('/analyze-period', methods=['POST'])
@login_required
def analyze_period():
    """Analyze period with AI"""
    
    days = request.form.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).all()
    
    if not transactions:
        return jsonify({
            'success': False,
            'message': 'No transactions found'
        }), 400
    
    transaction_data = [{
        'date': t.date.isoformat(),
        'description': t.description,
        'withdrawal': float(t.withdrawal or 0),
        'deposit': float(t.deposit or 0),
        'category': t.category.name if t.category else 'Uncategorized'
    } for t in transactions]
    
    try:
        ai_service = get_ai_service()
        summary = ai_service.prepare_transaction_summary(transaction_data)
        analysis = ai_service.analyze_period(summary, days)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    
    except Exception as e:
        logger.error(f"Period analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@ai_insights_bp.route('/suppliers')
@login_required
def suppliers():
    """Supplier analysis with AI insights"""
    
    days = request.args.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date(),
        BankTransaction.withdrawal > 0
    ).all()
    
    supplier_details = defaultdict(lambda: {
        'transactions': [],
        'total': 0,
        'count': 0,
        'avg': 0,
        'last_date': None,
        'categories': set()
    })
    
    for t in transactions:
        desc = t.description[:50]
        supplier_details[desc]['transactions'].append({
            'date': t.date,
            'amount': float(t.withdrawal),
            'reference': t.reference_number,
            'category': t.category.name if t.category else 'Uncategorized'
        })
        supplier_details[desc]['total'] += float(t.withdrawal)
        supplier_details[desc]['count'] += 1
        if t.category:
            supplier_details[desc]['categories'].add(t.category.name)
        if not supplier_details[desc]['last_date'] or t.date > supplier_details[desc]['last_date']:
            supplier_details[desc]['last_date'] = t.date
    
    suppliers = []
    for name, data in supplier_details.items():
        data['avg'] = data['total'] / data['count']
        data['categories'] = list(data['categories'])
        data['name'] = name
        suppliers.append(data)
    
    suppliers = sorted(suppliers, key=lambda x: x['total'], reverse=True)
    
    return render_template('ai_insights/suppliers.html', suppliers=suppliers, days=days)


@ai_insights_bp.route('/suppliers/<path:name>/analyze', methods=['POST'])
@login_required
def analyze_supplier(name):
    """Analyze specific supplier with AI"""
    
    days = request.form.get('days', 180, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date(),
        BankTransaction.description.like(f'%{name[:50]}%')
    ).all()
    
    if not transactions:
        return jsonify({
            'success': False,
            'message': 'No transactions found'
        }), 400
    
    supplier_data = {
        'count': len(transactions),
        'total': sum(float(t.withdrawal or 0) for t in transactions),
        'avg': sum(float(t.withdrawal or 0) for t in transactions) / len(transactions),
        'last_date': max([t.date for t in transactions]).isoformat(),
        'categories': list(set([t.category.name for t in transactions if t.category])),
        'recent_transactions': [
            {
                'date': t.date.isoformat(),
                'amount': float(t.withdrawal or 0),
                'description': t.description
            }
            for t in sorted(transactions, key=lambda x: x.date, reverse=True)[:10]
        ]
    }
    
    try:
        ai_service = get_ai_service()
        analysis = ai_service.analyze_supplier(name, supplier_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    
    except Exception as e:
        logger.error(f"Supplier analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@ai_insights_bp.route('/recurring')
@login_required
def recurring():
    """Recurring transaction analysis with AI"""
    
    days = request.args.get('days', 180, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).order_by(BankTransaction.date.desc()).all()
    
    recurring_groups = defaultdict(list)
    for t in transactions:
        desc = t.description[:50]
        recurring_groups[desc].append(t)
    
    recurring_analysis = []
    for desc, trans_list in recurring_groups.items():
        if len(trans_list) >= 3:
            amounts = [float(t.withdrawal or t.deposit or 0) for t in trans_list]
            dates = [t.date for t in trans_list]
            
            intervals = []
            for i in range(1, len(dates)):
                interval = (dates[i-1] - dates[i]).days
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals) if intervals else 0
            
            if avg_interval <= 10:
                frequency = 'Weekly'
            elif avg_interval <= 35:
                frequency = 'Monthly'
            elif avg_interval <= 95:
                frequency = 'Quarterly'
            else:
                frequency = 'Irregular'
            
            recurring_analysis.append({
                'description': desc,
                'count': len(trans_list),
                'avg_amount': sum(amounts) / len(amounts),
                'total': sum(amounts),
                'frequency': frequency,
                'avg_interval_days': round(avg_interval, 1),
                'last_date': dates[0],
                'category': trans_list[0].category.name if trans_list[0].category else 'Uncategorized',
                'transactions': [
                    {
                        'date': t.date,
                        'amount': float(t.withdrawal or t.deposit or 0),
                        'reference': t.reference_number
                    }
                    for t in trans_list[:10]
                ]
            })
    
    recurring_analysis = sorted(recurring_analysis, key=lambda x: x['count'], reverse=True)
    
    return render_template('ai_insights/recurring.html', recurring=recurring_analysis, days=days)


@ai_insights_bp.route('/recurring/<path:description>/analyze', methods=['POST'])
@login_required
def analyze_recurring(description):
    """Analyze specific recurring transaction"""
    
    days = request.args.get('days', 180, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date(),
        BankTransaction.description.like(f'%{description[:50]}%')
    ).order_by(BankTransaction.date.desc()).all()
    
    if len(transactions) < 3:
        return jsonify({
            'success': False,
            'message': 'Not enough transactions for pattern analysis'
        }), 400
    
    amounts = [float(t.withdrawal or t.deposit or 0) for t in transactions]
    dates = [t.date for t in transactions]
    
    intervals = []
    for i in range(1, len(dates)):
        interval = (dates[i-1] - dates[i]).days
        intervals.append(interval)
    
    avg_interval = sum(intervals) / len(intervals) if intervals else 0
    
    if avg_interval <= 10:
        frequency = 'Weekly'
    elif avg_interval <= 35:
        frequency = 'Monthly'
    elif avg_interval <= 95:
        frequency = 'Quarterly'
    else:
        frequency = 'Irregular'
    
    recurring_data = {
        'description': description,
        'count': len(transactions),
        'avg_amount': sum(amounts) / len(amounts),
        'total': sum(amounts),
        'frequency': frequency,
        'avg_interval_days': round(avg_interval, 1)
    }
    
    try:
        ai_service = get_ai_service()
        analysis = ai_service.analyze_recurring_transaction(recurring_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    
    except Exception as e:
        logger.error(f"Recurring analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@ai_insights_bp.route('/categories')
@login_required
def categories():
    """Category analysis with AI"""
    
    days = request.args.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    category_data = db.session.query(
        TransactionCategory.id,
        TransactionCategory.name,
        TransactionCategory.transaction_type,
        func.count(BankTransaction.id).label('count'),
        func.sum(BankTransaction.withdrawal).label('expenses'),
        func.sum(BankTransaction.deposit).label('income')
    ).outerjoin(
        BankTransaction
    ).filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).group_by(
        TransactionCategory.id,
        TransactionCategory.name,
        TransactionCategory.transaction_type
    ).all()
    
    categories_list = [
        {
            'id': c.id,
            'name': c.name,
            'type': c.transaction_type,
            'count': c.count,
            'expenses': float(c.expenses or 0),
            'income': float(c.income or 0),
            'total': float(c.expenses or 0) + float(c.income or 0)
        }
        for c in category_data
    ]
    
    uncategorized = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.category_id == None,
        BankTransaction.date >= start_date.date()
    ).all()
    
    uncategorized_total = sum(float(t.withdrawal or t.deposit or 0) for t in uncategorized)
    
    return render_template('ai_insights/categories.html',
        categories=categories_list,
        uncategorized_count=len(uncategorized),
        uncategorized_total=uncategorized_total,
        days=days
    )


@ai_insights_bp.route('/categories/<int:id>/analyze', methods=['POST'])
@login_required
def analyze_category(id):
    """Analyze specific category"""
    
    category = TransactionCategory.query.get_or_404(id)
    
    days = request.form.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.category_id == id,
        BankTransaction.date >= start_date.date()
    ).all()
    
    if not transactions:
        return jsonify({
            'success': False,
            'message': 'No transactions in this category'
        }), 400
    
    category_data = {
        'name': category.name,
        'type': category.transaction_type,
        'count': len(transactions),
        'total': sum(float(t.withdrawal or t.deposit or 0) for t in transactions),
        'avg': sum(float(t.withdrawal or t.deposit or 0) for t in transactions) / len(transactions),
        'transactions': [
            {
                'date': t.date.isoformat(),
                'description': t.description,
                'amount': float(t.withdrawal or t.deposit or 0)
            }
            for t in sorted(transactions, key=lambda x: x.date, reverse=True)[:20]
        ]
    }
    
    try:
        ai_service = get_ai_service()
        analysis = ai_service.analyze_category(category_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    
    except Exception as e:
        logger.error(f"Category analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500