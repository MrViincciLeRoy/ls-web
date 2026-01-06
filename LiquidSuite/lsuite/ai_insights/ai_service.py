"""
Shared AI Service - Can be imported across multiple modules
Location: lsuite/services/ai_service.py
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional
from groq import Groq

logger = logging.getLogger(__name__)


class GroqAPIKeyRotator:
    """Manages multiple Groq API keys with automatic rotation"""
    
    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.current_index = 0
        self.failed_keys = set()
        
    def _load_api_keys(self) -> List[str]:
        keys_str = os.getenv('GROQ_API_KEYS', '')
        
        if not keys_str:
            raise ValueError("GROQ_API_KEYS not set in environment")
        
        keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        
        if not keys:
            raise ValueError("No valid Groq API keys found")
        
        logger.info(f"Loaded {len(keys)} Groq API keys")
        return keys
    
    def get_next_key(self) -> str:
        attempts = 0
        max_attempts = len(self.api_keys)
        
        while attempts < max_attempts:
            key = self.api_keys[self.current_index]
            
            if key not in self.failed_keys:
                return key
            
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            attempts += 1
        
        self.failed_keys.clear()
        return self.api_keys[self.current_index]
    
    def rotate(self):
        self.current_index = (self.current_index + 1) % len(self.api_keys)
    
    def mark_failed(self, key: str):
        self.failed_keys.add(key)


class AIService:
    """Shared AI service for financial analysis across all modules"""
    
    def __init__(self):
        try:
            self.key_rotator = GroqAPIKeyRotator()
            self.model = "llama-3.3-70b-versatile"
            self.max_retries = 3
            self.enabled = True
        except Exception as e:
            logger.warning(f"AI Service disabled: {e}")
            self.enabled = False
    
    def _get_client(self) -> Groq:
        api_key = self.key_rotator.get_next_key()
        return Groq(api_key=api_key)
    
    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        if not self.enabled:
            raise Exception("AI Service is not enabled")
        
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                client = self._get_client()
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=2000
                )
                
                self.key_rotator.rotate()
                return response.choices[0].message.content
            
            except Exception as e:
                last_error = e
                logger.error(f"Groq API error (attempt {retries + 1}): {str(e)}")
                
                current_key = self.key_rotator.get_next_key()
                self.key_rotator.mark_failed(current_key)
                self.key_rotator.rotate()
                
                retries += 1
        
        raise Exception(f"AI call failed after {self.max_retries} retries: {str(last_error)}")
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON from markdown code blocks"""
        response = response.strip()
        
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        
        if response.endswith("```"):
            response = response[:-3]
        
        return response.strip()
    
    def analyze_period(self, transaction_summary: Dict, period_days: int) -> Dict[str, Any]:
        """Analyze a period of transactions"""
        
        if not self.enabled:
            return self._fallback_analysis(transaction_summary)
        
        try:
            prompt = f"""Analyze these transactions from the last {period_days} days.

Transaction Data:
- Total Transactions: {transaction_summary['total_transactions']}
- Total Expenses: R{transaction_summary['total_expenses']:.2f}
- Total Income: R{transaction_summary['total_income']:.2f}
- Net Cashflow: R{transaction_summary['net_cashflow']:.2f}

Category Breakdown:
{json.dumps(transaction_summary['categories'], indent=2)}

Provide analysis in this EXACT JSON format (no extra text):
{{
    "overview": "2-3 sentence summary of financial health",
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "spending_patterns": {{
        "observations": ["observation 1", "observation 2"],
        "concerns": ["concern 1"],
        "opportunities": ["opportunity 1"]
    }},
    "recommendations": ["recommendation 1", "recommendation 2"],
    "risk_score": "LOW",
    "savings_potential": "R500"
}}"""
            
            messages = [
                {"role": "system", "content": "You are a financial analyst. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._call_api(messages, temperature=0.3)
            cleaned = self._clean_json_response(response)
            
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Period analysis error: {e}")
            return self._fallback_analysis(transaction_summary)
    
    def analyze_supplier(self, supplier_name: str, supplier_data: Dict) -> Dict[str, Any]:
        """Analyze supplier spending patterns"""
        
        if not self.enabled:
            return {
                "relationship_assessment": f"Regular supplier - R{supplier_data.get('total', 0):.2f} total spend",
                "spending_trend": "stable",
                "insights": [f"{supplier_data.get('count', 0)} transactions over period"],
                "concerns": [],
                "recommendations": ["Monitor spending with this supplier"]
            }
        
        try:
            prompt = f"""Analyze spending with supplier: {supplier_name}

Data:
- Total Transactions: {supplier_data.get('count')}
- Total Spent: R{supplier_data.get('total'):.2f}
- Average: R{supplier_data.get('avg'):.2f}
- Last Transaction: {supplier_data.get('last_date')}
- Categories: {', '.join(supplier_data.get('categories', []))}

Recent transactions: {json.dumps(supplier_data.get('recent_transactions', [])[:5], indent=2)}

Respond ONLY with JSON:
{{
    "relationship_assessment": "brief assessment of supplier relationship",
    "spending_trend": "increasing/stable/decreasing",
    "insights": ["insight 1", "insight 2"],
    "concerns": ["any red flags"],
    "recommendations": ["recommendation 1", "recommendation 2"]
}}"""
            
            messages = [
                {"role": "system", "content": "Procurement analyst. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._call_api(messages, temperature=0.4)
            cleaned = self._clean_json_response(response)
            
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Supplier analysis error: {e}")
            return {
                "relationship_assessment": f"Regular supplier - R{supplier_data.get('total', 0):.2f} total",
                "spending_trend": "stable",
                "insights": [],
                "concerns": [],
                "recommendations": []
            }
    
    def analyze_recurring_transaction(self, recurring_data: Dict) -> Dict[str, Any]:
        """Analyze recurring transaction pattern"""
        
        if not self.enabled:
            return {
                "pattern_analysis": f"{recurring_data.get('frequency')} payment pattern detected",
                "reliability": "stable",
                "insights": [],
                "optimization": []
            }
        
        try:
            prompt = f"""Analyze this recurring transaction:

Description: {recurring_data.get('description')}
Frequency: {recurring_data.get('frequency')}
Count: {recurring_data.get('count')} occurrences
Average Amount: R{recurring_data.get('avg_amount'):.2f}
Total: R{recurring_data.get('total'):.2f}
Interval: Every {recurring_data.get('avg_interval_days')} days

Respond ONLY with JSON:
{{
    "pattern_analysis": "description of payment pattern",
    "reliability": "stable/variable",
    "insights": ["insight 1", "insight 2"],
    "optimization": ["suggestion 1", "suggestion 2"]
}}"""
            
            messages = [
                {"role": "system", "content": "Financial analyst. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._call_api(messages, temperature=0.4)
            cleaned = self._clean_json_response(response)
            
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Recurring analysis error: {e}")
            return {
                "pattern_analysis": f"{recurring_data.get('frequency')} payment",
                "reliability": "stable",
                "insights": [],
                "optimization": []
            }
    
    def analyze_category(self, category_data: Dict) -> Dict[str, Any]:
        """Analyze spending in a category"""
        
        if not self.enabled:
            return {
                "patterns": [f"{category_data.get('count')} transactions in category"],
                "concerns": [],
                "opportunities": [],
                "budget_recommendation": f"Current avg: R{category_data.get('avg', 0):.2f}"
            }
        
        try:
            prompt = f"""Analyze spending in this category:

Category: {category_data.get('name')}
Type: {category_data.get('type')}
Total Transactions: {category_data.get('count')}
Total Amount: R{category_data.get('total'):.2f}
Average: R{category_data.get('avg'):.2f}

Recent transactions:
{json.dumps(category_data.get('transactions', [])[:10], indent=2)}

Respond ONLY with JSON:
{{
    "patterns": ["pattern 1", "pattern 2"],
    "concerns": ["concern 1"],
    "opportunities": ["opportunity 1"],
    "budget_recommendation": "budget advice"
}}"""
            
            messages = [
                {"role": "system", "content": "Budget analyst. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._call_api(messages, temperature=0.4)
            cleaned = self._clean_json_response(response)
            
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Category analysis error: {e}")
            return {
                "patterns": [],
                "concerns": [],
                "opportunities": [],
                "budget_recommendation": f"Monitor spending"
            }
    
    def _fallback_analysis(self, summary: Dict) -> Dict[str, Any]:
        """Provide basic analysis when AI fails"""
        total = summary.get('total_transactions', 0)
        expenses = summary.get('total_expenses', 0)
        income = summary.get('total_income', 0)
        
        return {
            "overview": f"Analyzed {total} transactions. Expenses: R{expenses:.2f}, Income: R{income:.2f}",
            "key_insights": [
                f"Processed {total} transactions",
                f"Net cashflow: R{income - expenses:.2f}"
            ],
            "spending_patterns": {
                "observations": ["Basic analysis completed"],
                "concerns": [],
                "opportunities": ["Enable AI for deeper insights"]
            },
            "recommendations": ["Configure GROQ_API_KEYS for AI insights"],
            "risk_score": "UNKNOWN",
            "savings_potential": "Unknown"
        }
    
    def prepare_transaction_summary(self, transactions: List[Dict]) -> Dict:
        """Prepare transaction summary for AI analysis"""
        total_expenses = sum(float(t.get('withdrawal', 0) or 0) for t in transactions)
        total_income = sum(float(t.get('deposit', 0) or 0) for t in transactions)
        
        category_breakdown = {}
        for t in transactions:
            cat = t.get('category', 'Uncategorized')
            if cat not in category_breakdown:
                category_breakdown[cat] = {'count': 0, 'amount': 0}
            
            amount = float(t.get('withdrawal', 0) or t.get('deposit', 0) or 0)
            category_breakdown[cat]['count'] += 1
            category_breakdown[cat]['amount'] += amount
        
        return {
            'total_transactions': len(transactions),
            'total_expenses': total_expenses,
            'total_income': total_income,
            'net_cashflow': total_income - total_expenses,
            'average_transaction': (total_expenses + total_income) / len(transactions) if transactions else 0,
            'categories': category_breakdown,
            'date_range': {
                'start': min([t.get('date') for t in transactions]) if transactions else None,
                'end': max([t.get('date') for t in transactions]) if transactions else None
            }
        }


# Global instance
_ai_service = None

def get_ai_service() -> AIService:
    """Get or create global AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
