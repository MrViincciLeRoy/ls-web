"""
Fixed Groq AI Service with better error handling
"""
import os
import logging
import json
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)


class GroqAPIKeyRotator:
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
        
        # Clear failed keys and retry
        self.failed_keys.clear()
        return self.api_keys[self.current_index]
    
    def rotate(self):
        self.current_index = (self.current_index + 1) % len(self.api_keys)
    
    def mark_failed(self, key: str):
        self.failed_keys.add(key)


class GroqAIService:
    def __init__(self):
        self.key_rotator = GroqAPIKeyRotator()
        self.model = "llama-3.3-70b-versatile"
        self.max_retries = 3
    
    def _get_client(self) -> Groq:
        api_key = self.key_rotator.get_next_key()
        return Groq(api_key=api_key)
    
    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
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
        
        raise Exception(f"Failed after {self.max_retries} retries: {str(last_error)}")
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON from markdown code blocks"""
        response = response.strip()
        
        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        
        if response.endswith("```"):
            response = response[:-3]
        
        return response.strip()
    
    def analyze_transactions(self, transactions: List[Dict], period_days: int) -> Dict[str, Any]:
        try:
            transaction_summary = self._prepare_transaction_summary(transactions)
            
            prompt = f"""Analyze these transactions from the last {period_days} days.

Transaction Data:
- Total Transactions: {transaction_summary['total_transactions']}
- Total Expenses: R{transaction_summary['total_expenses']:.2f}
- Total Income: R{transaction_summary['total_income']:.2f}
- Net Cashflow: R{transaction_summary['net_cashflow']:.2f}

Category Breakdown:
{json.dumps(transaction_summary['categories'], indent=2)}

Provide your analysis in this EXACT JSON format (no extra text):
{{
    "overview": "2-3 sentence summary",
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
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}\nResponse: {response[:200]}")
            return self._fallback_analysis(transaction_summary)
        
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return self._fallback_analysis({})
    
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
                "opportunities": ["Enable AI analysis for deeper insights"]
            },
            "recommendations": ["Configure GROQ_API_KEYS for AI-powered insights"],
            "risk_score": "UNKNOWN",
            "savings_potential": "Unknown"
        }
    
    def analyze_single_transaction(self, transaction: Dict) -> Dict[str, Any]:
        try:
            prompt = f"""Analyze this transaction:
Date: {transaction.get('date')}
Description: {transaction.get('description')}
Amount: R{transaction.get('amount')}
Type: {transaction.get('type')}

Respond ONLY with valid JSON:
{{
    "summary": "brief summary",
    "insights": ["insight 1"],
    "flags": ["any concerns"],
    "suggestions": ["suggestion 1"]
}}"""
            
            messages = [
                {"role": "system", "content": "Financial analyst. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._call_api(messages, temperature=0.4)
            cleaned = self._clean_json_response(response)
            
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Transaction analysis error: {e}")
            return {
                "summary": f"{transaction.get('description', 'Transaction')} - R{transaction.get('amount', 0)}",
                "insights": [],
                "flags": [],
                "suggestions": []
            }
    
    def analyze_supplier(self, supplier_name: str, supplier_data: Dict) -> Dict[str, Any]:
        try:
            prompt = f"""Analyze spending with supplier: {supplier_name}
Total Transactions: {supplier_data.get('count')}
Total Spent: R{supplier_data.get('total')}
Average: R{supplier_data.get('avg')}

Respond ONLY with JSON:
{{
    "relationship_assessment": "brief assessment",
    "spending_trend": "increasing",
    "insights": ["insight 1"],
    "concerns": [],
    "recommendations": ["recommendation 1"]
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
    
    def _prepare_transaction_summary(self, transactions: List[Dict]) -> Dict:
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
