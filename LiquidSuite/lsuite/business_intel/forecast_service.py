"""
Cash Flow Forecasting with AI
"""
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from lsuite.ai_insights.ai_service import get_ai_service

logger = logging.getLogger(__name__)


class CashFlowForecaster:
    """Generate cash flow forecasts using historical data and AI"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def generate_forecast(self, transactions, documents, period_days=30):
        """Generate cash flow forecast"""
        
        # Analyze historical patterns
        patterns = self._analyze_patterns(transactions)
        
        # Calculate current position
        current = self._calculate_current_position(transactions)
        
        # Analyze pending documents
        pending = self._analyze_pending_documents(documents)
        
        # Generate predictions
        if self.ai_service.enabled:
            forecast = self._ai_forecast(patterns, current, pending, period_days)
        else:
            forecast = self._rule_based_forecast(patterns, current, pending, period_days)
        
        return forecast
    
    def _analyze_patterns(self, transactions):
        """Analyze transaction patterns"""
        patterns = {
            'recurring_income': [],
            'recurring_expenses': [],
            'average_daily_expense': 0,
            'average_daily_income': 0,
            'trend': 'stable'
        }
        
        if not transactions:
            return patterns
        
        # Group by description for recurring detection
        grouped = defaultdict(list)
        for t in transactions:
            desc = t.description[:50] if t.description else 'Unknown'
            grouped[desc].append({
                'date': t.date,
                'amount': float(t.withdrawal or t.deposit or 0),
                'type': 'expense' if t.withdrawal else 'income'
            })
        
        # Find recurring patterns (3+ occurrences)
        for desc, items in grouped.items():
            if len(items) >= 3:
                avg_amount = sum(i['amount'] for i in items) / len(items)
                trans_type = items[0]['type']
                
                # Calculate average interval
                dates = sorted([i['date'] for i in items])
                intervals = []
                for i in range(1, len(dates)):
                    intervals.append((dates[i] - dates[i-1]).days)
                avg_interval = sum(intervals) / len(intervals) if intervals else 30
                
                pattern = {
                    'description': desc,
                    'average_amount': avg_amount,
                    'frequency_days': avg_interval,
                    'count': len(items)
                }
                
                if trans_type == 'expense':
                    patterns['recurring_expenses'].append(pattern)
                else:
                    patterns['recurring_income'].append(pattern)
        
        # Calculate daily averages
        if transactions:
            days = (max(t.date for t in transactions) - min(t.date for t in transactions)).days or 1
            total_expense = sum(float(t.withdrawal or 0) for t in transactions)
            total_income = sum(float(t.deposit or 0) for t in transactions)
            
            patterns['average_daily_expense'] = total_expense / days
            patterns['average_daily_income'] = total_income / days
        
        return patterns
    
    def _calculate_current_position(self, transactions):
        """Calculate current cash position"""
        if not transactions:
            return {'balance': 0, 'income_30d': 0, 'expense_30d': 0}
        
        cutoff = datetime.now().date() - timedelta(days=30)
        recent = [t for t in transactions if t.date >= cutoff]
        
        income = sum(float(t.deposit or 0) for t in recent)
        expense = sum(float(t.withdrawal or 0) for t in recent)
        
        return {
            'balance': income - expense,
            'income_30d': income,
            'expense_30d': expense,
            'transaction_count': len(recent)
        }
    
    def _analyze_pending_documents(self, documents):
        """Analyze pending invoices/POs"""
        pending = {
            'unpaid_invoices': [],
            'pending_orders': [],
            'total_receivable': 0,
            'total_payable': 0
        }
        
        for doc in documents:
            if not doc.is_reconciled:
                amount = float(doc.total_amount)
                
                if doc.document_type == 'invoice':
                    pending['unpaid_invoices'].append({
                        'number': doc.document_number,
                        'amount': amount,
                        'due_date': doc.due_date
                    })
                    pending['total_receivable'] += amount
                
                elif doc.document_type == 'purchase_order':
                    pending['pending_orders'].append({
                        'number': doc.document_number,
                        'amount': amount,
                        'due_date': doc.due_date
                    })
                    pending['total_payable'] += amount
        
        return pending
    
    def _ai_forecast(self, patterns, current, pending, period_days):
        """Generate AI-powered forecast"""
        try:
            prompt = f"""Generate cash flow forecast for next {period_days} days:

Current Position:
- Balance: R{current['balance']:.2f}
- Last 30d Income: R{current['income_30d']:.2f}
- Last 30d Expenses: R{current['expense_30d']:.2f}

Recurring Patterns:
- Daily avg expense: R{patterns['average_daily_expense']:.2f}
- Daily avg income: R{patterns['average_daily_income']:.2f}
- Recurring expenses: {len(patterns['recurring_expenses'])} items
- Recurring income: {len(patterns['recurring_income'])} items

Pending Documents:
- Unpaid invoices: {len(pending['unpaid_invoices'])} (R{pending['total_receivable']:.2f})
- Pending orders: {len(pending['pending_orders'])} (R{pending['total_payable']:.2f})

Provide forecast in JSON:
{{
    "predicted_income": 0.00,
    "predicted_expenses": 0.00,
    "predicted_balance": 0.00,
    "confidence_score": 0.85,
    "weekly_breakdown": [
        {{"week": 1, "income": 0, "expenses": 0, "balance": 0}}
    ],
    "insights": ["insight 1", "insight 2"],
    "risk_factors": ["risk if any"],
    "recommendations": ["recommendation 1"],
    "major_upcoming": [
        {{"description": "string", "amount": 0, "date": "YYYY-MM-DD", "type": "income/expense"}}
    ]
}}"""
            
            messages = [
                {"role": "system", "content": "Financial forecasting expert. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.ai_service._call_api(messages, temperature=0.3)
            cleaned = self.ai_service._clean_json_response(response)
            
            import json
            forecast = json.loads(cleaned)
            
            return forecast
        
        except Exception as e:
            logger.error(f"AI forecast failed: {e}")
            return self._rule_based_forecast(patterns, current, pending, period_days)
    
    def _rule_based_forecast(self, patterns, current, pending, period_days):
        """Simple rule-based forecast"""
        
        # Project based on daily averages
        predicted_income = patterns['average_daily_income'] * period_days
        predicted_expenses = patterns['average_daily_expense'] * period_days
        
        # Add pending documents
        predicted_income += pending['total_receivable'] * 0.7  # 70% collection rate
        predicted_expenses += pending['total_payable']
        
        predicted_balance = current['balance'] + predicted_income - predicted_expenses
        
        forecast = {
            'predicted_income': predicted_income,
            'predicted_expenses': predicted_expenses,
            'predicted_balance': predicted_balance,
            'confidence_score': 0.6,
            'insights': [
                f"Based on {period_days}-day historical average",
                f"{len(patterns['recurring_expenses'])} recurring expenses identified",
                f"{len(patterns['recurring_income'])} recurring income sources"
            ],
            'risk_factors': [],
            'recommendations': []
        }
        
        # Add risk factors
        if predicted_balance < 0:
            forecast['risk_factors'].append('Negative balance predicted')
            forecast['recommendations'].append('Review upcoming expenses and payment terms')
        
        if pending['total_payable'] > current['income_30d']:
            forecast['risk_factors'].append('High pending obligations')
            forecast['recommendations'].append('Prioritize collections')
        
        return forecast
    
    def analyze_transaction_fees(self, transactions):
        """Analyze fees and charges in transactions"""
        if not self.ai_service.enabled:
            return self._basic_fee_analysis(transactions)
        
        try:
            # Group potential fee transactions
            fee_keywords = ['fee', 'charge', 'service', 'admin', 'bank', 'commission']
            potential_fees = []
            
            for t in transactions:
                desc_lower = t.description.lower() if t.description else ''
                if any(keyword in desc_lower for keyword in fee_keywords):
                    potential_fees.append({
                        'date': t.date.isoformat(),
                        'description': t.description,
                        'amount': float(t.withdrawal or 0)
                    })
            
            if not potential_fees:
                return {'total_fees': 0, 'fee_breakdown': [], 'insights': ['No fees detected']}
            
            prompt = f"""Analyze these potential fee transactions:

{potential_fees[:50]}

Provide analysis in JSON:
{{
    "total_fees": 0.00,
    "fee_breakdown": [
        {{"category": "bank fees", "count": 0, "total": 0.00}},
        {{"category": "service charges", "count": 0, "total": 0.00}}
    ],
    "monthly_average": 0.00,
    "insights": ["insight 1", "insight 2"],
    "recommendations": ["recommendation 1"]
}}"""
            
            messages = [
                {"role": "system", "content": "Financial analyst. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.ai_service._call_api(messages, temperature=0.3)
            cleaned = self.ai_service._clean_json_response(response)
            
            import json
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Fee analysis failed: {e}")
            return self._basic_fee_analysis(transactions)
    
    def _basic_fee_analysis(self, transactions):
        """Basic fee analysis without AI"""
        fee_keywords = ['fee', 'charge', 'service', 'admin', 'bank']
        
        total_fees = 0
        fee_count = 0
        
        for t in transactions:
            desc_lower = t.description.lower() if t.description else ''
            if any(keyword in desc_lower for keyword in fee_keywords):
                total_fees += float(t.withdrawal or 0)
                fee_count += 1
        
        return {
            'total_fees': total_fees,
            'fee_count': fee_count,
            'insights': [f'Detected {fee_count} fee transactions totaling R{total_fees:.2f}']
        }
