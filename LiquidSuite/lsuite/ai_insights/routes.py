"""
AI Insights Routes - Groq AI-powered analysis
"""
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from collections import defaultdict
from lsuite.ai_insights import ai_insights_bp
from lsuite.extensions import db
from lsuite.models import BankTransaction, TransactionCategory
from lsuite.ai_insights.services import GroqAIService
import logging

logger = logging.getLogger(__name__)


@ai_insights_bp.route('/dashboard')
@login_required
def dashboard():
    """AI-powered insights dashboard"""
    
    days = request.args.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).all()
    
    stats = {
        'total': len(transactions),
        'total_expenses': sum(float(t.withdrawal or 0) for t in transactions),
        'total_income': sum(float(t.deposit or 0) for t in transactions),
        'avg_transaction': 0,
        'uncategorized': sum(1 for t in transactions if not t.category_id)
    }
    
    if stats['total'] > 0:
        stats['avg_transaction'] = (stats['total_expenses'] + stats['total_income']) / stats['total']
    
    return render_template('ai_insights/dashboard.html',
        days=days,
        stats=stats,
        transaction_count=len(transactions)
    )


@ai_insights_bp.route('/analyze-period', methods=['POST'])
@login_required
def analyze_period():
    """Analyze transactions for a period using AI"""
    
    days = request.form.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).all()
    
    if not transactions:
        return jsonify({
            'success': False,
            'message': 'No transactions found for this period'
        }), 400
    
    transaction_data = []
    for t in transactions:
        transaction_data.append({
            'date': t.date.isoformat(),
            'description': t.description,
            'amount': float(t.withdrawal or t.deposit or 0),
            'type': 'debit' if t.withdrawal else 'credit',
            'category': t.category.name if t.category else 'Uncategorized',
            'withdrawal': float(t.withdrawal or 0),
            'deposit': float(t.deposit or 0)
        })
    
    try:
        ai_service = GroqAIService()
        analysis = ai_service.analyze_transactions(transaction_data, days)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@ai_insights_bp.route('/transaction/<int:id>/analyze', methods=['POST'])
@login_required
def analyze_transaction(id):
    """Analyze a single transaction using AI"""
    
    transaction = BankTransaction.query.get_or_404(id)
    
    if transaction.user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'Unauthorized'
        }), 403
    
    transaction_data = {
        'date': transaction.date.isoformat(),
        'description': transaction.description,
        'amount': float(transaction.withdrawal or transaction.deposit or 0),
        'type': 'debit' if transaction.withdrawal else 'credit',
        'category': transaction.category.name if transaction.category else 'Uncategorized'
    }
    
    try:
        ai_service = GroqAIService()
        analysis = ai_service.analyze_single_transaction(transaction_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'transaction': transaction_data
        })
    
    except Exception as e:
        logger.error(f"Transaction analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@ai_insights_bp.route('/supplier/<path:name>/analyze', methods=['POST'])
@login_required
def analyze_supplier(name):
    """Analyze supplier spending using AI"""
    
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
            'message': 'No transactions found for this supplier'
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
        ai_service = GroqAIService()
        analysis = ai_service.analyze_supplier(name, supplier_data)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'supplier_data': supplier_data
        })
    
    except Exception as e:
        logger.error(f"Supplier analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@ai_insights_bp.route('/category/<int:id>/analyze', methods=['POST'])
@login_required
def analyze_category(id):
    """Analyze spending in a specific category"""
    
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
    
    prompt = f"""Analyze spending in this category:

Category: {category_data['name']}
Type: {category_data['type']}
Total Transactions: {category_data['count']}
Total Amount: R{category_data['total']:.2f}
Average: R{category_data['avg']:.2f}

Recent transactions:
{category_data['transactions'][:10]}

Provide insights on:
1. Spending patterns and trends
2. Unusual or concerning transactions
3. Optimization opportunities
4. Budget recommendations

Format as JSON with keys: patterns, concerns, opportunities, budget_recommendation"""
    
    try:
        ai_service = GroqAIService()
        messages = [
            {"role": "system", "content": "You are a financial analyst specializing in budget optimization."},
            {"role": "user", "content": prompt}
        ]
        
        response = ai_service._call_api(messages, temperature=0.4)
        
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        
        import json
        analysis = json.loads(response_clean.strip())
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'category_data': category_data
        })
    
    except Exception as e:
        logger.error(f"Category analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@ai_insights_bp.route('/smart-suggestions')
@login_required
def smart_suggestions():
    """Get AI-powered smart suggestions"""
    
    days = 30
    start_date = datetime.now() - timedelta(days=days)
    
    uncategorized = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.category_id == None,
        BankTransaction.date >= start_date.date()
    ).count()
    
    unsynced = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.category_id != None,
        BankTransaction.erpnext_synced == False
    ).count()
    
    suggestions = []
    
    if uncategorized > 0:
        suggestions.append({
            'type': 'action',
            'priority': 'high',
            'title': f'{uncategorized} Uncategorized Transactions',
            'description': 'Categorize transactions to enable ERPNext sync and better insights',
            'action': 'Categorize Now',
            'url': '/gmail/transactions?uncategorized=1'
        })
    
    if unsynced > 0:
        suggestions.append({
            'type': 'action',
            'priority': 'medium',
            'title': f'{unsynced} Transactions Ready to Sync',
            'description': 'Sync categorized transactions to ERPNext',
            'action': 'Sync to ERPNext',
            'url': '/bridge/bulk-operations'
        })
    
    return jsonify({
        'success': True,
        'suggestions': suggestions
    })
