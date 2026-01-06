"""
Groq AI Service - API key rotation and intelligent analysis
"""
import os
import logging
import json
from groq import Groq
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GroqAPIKeyRotator:
    """Manages multiple Groq API keys with automatic rotation"""
    
    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.current_index = 0
        self.failed_keys = set()
        
    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment or config"""
        keys_str = os.getenv('GROQ_API_KEYS', '')
        
        if not keys_str:
            raise ValueError("No Groq API keys configured. Set GROQ_API_KEYS environment variable")
        
        keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        
        if not keys:
            raise ValueError("No valid Groq API keys found")
        
        logger.info(f"Loaded {len(keys)} Groq API keys")
        return keys
    
    def get_next_key(self) -> str:
        """Get next available API key"""
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
        """Rotate to next API key"""
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        logger.debug(f"Rotated to API key index {self.current_index}")
    
    def mark_failed(self, key: str):
        """Mark a key as failed"""
        self.failed_keys.add(key)
        logger.warning(f"Marked API key as failed (total failed: {len(self.failed_keys)})")


class GroqAIService:
    """Groq AI service for financial insights"""
    
    def __init__(self):
        self.key_rotator = GroqAPIKeyRotator()
        self.model = "llama-3.3-70b-versatile"
        self.max_retries = 3
    
    def _get_client(self) -> Groq:
        """Get Groq client with current API key"""
        api_key = self.key_rotator.get_next_key()
        return Groq(api_key=api_key)
    
    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Call Groq API with retry and key rotation"""
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
    
    def analyze_transactions(self, transactions: List[Dict], period_days: int) -> Dict[str, Any]:
        """Analyze transactions and provide insights"""
        
        transaction_summary = self._prepare_transaction_summary(transactions)
        
        prompt = f"""You are a financial analyst AI. Analyze these transactions from the last {period_days} days and provide actionable insights.

Transaction Data:
{json.dumps(transaction_summary, indent=2)}

Provide analysis in the following JSON format:
{{
    "overview": "Brief overview of financial health",
    "key_insights": [
        "insight 1",
        "insight 2",
        "insight 3"
    ],
    "spending_patterns": {{
        "observations": ["observation 1", "observation 2"],
        "concerns": ["concern 1"],
        "opportunities": ["opportunity 1"]
    }},
    "recommendations": [
        "recommendation 1",
        "recommendation 2"
    ],
    "risk_score": "LOW/MEDIUM/HIGH",
    "savings_potential": "estimated amount in ZAR"
}}

Focus on: unusual spending, recurring costs, optimization opportunities, and financial health."""
        
        messages = [
            {"role": "system", "content": "You are an expert financial analyst providing insights on bank transactions."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_api(messages, temperature=0.3)
            
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            return json.loads(response_clean.strip())
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {
                "overview": "Analysis completed but formatting error occurred",
                "key_insights": ["Unable to parse structured insights"],
                "spending_patterns": {"observations": [], "concerns": [], "opportunities": []},
                "recommendations": ["Review transactions manually"],
                "risk_score": "UNKNOWN",
                "savings_potential": "Unknown"
            }
    
    def analyze_single_transaction(self, transaction: Dict) -> Dict[str, Any]:
        """Analyze a single transaction"""
        
        prompt = f"""Analyze this bank transaction and provide insights:

Date: {transaction.get('date')}
Description: {transaction.get('description')}
Amount: R{transaction.get('amount')}
Type: {transaction.get('type')}
Category: {transaction.get('category', 'Uncategorized')}

Provide analysis in JSON format:
{{
    "summary": "Brief summary",
    "insights": ["insight 1", "insight 2"],
    "flags": ["any concerns or unusual patterns"],
    "suggestions": ["actionable suggestions"],
    "similar_transactions": "guidance on similar transactions"
}}"""
        
        messages = [
            {"role": "system", "content": "You are a financial analyst reviewing individual transactions."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_api(messages, temperature=0.4)
            
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            return json.loads(response_clean.strip())
        
        except json.JSONDecodeError:
            return {
                "summary": "Transaction recorded",
                "insights": [],
                "flags": [],
                "suggestions": [],
                "similar_transactions": "N/A"
            }
    
    def analyze_supplier(self, supplier_name: str, supplier_data: Dict) -> Dict[str, Any]:
        """Analyze supplier spending patterns"""
        
        prompt = f"""Analyze spending with this supplier:

Supplier: {supplier_name}
Total Transactions: {supplier_data.get('count')}
Total Spent: R{supplier_data.get('total')}
Average Transaction: R{supplier_data.get('avg')}
Last Transaction: {supplier_data.get('last_date')}
Categories: {', '.join(supplier_data.get('categories', []))}

Recent transactions:
{json.dumps(supplier_data.get('recent_transactions', [])[:5], indent=2)}

Provide analysis in JSON format:
{{
    "relationship_assessment": "brief assessment",
    "spending_trend": "increasing/stable/decreasing",
    "insights": ["insight 1", "insight 2"],
    "concerns": ["any red flags"],
    "recommendations": ["recommendation 1", "recommendation 2"]
}}"""
        
        messages = [
            {"role": "system", "content": "You are a procurement and vendor management analyst."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_api(messages, temperature=0.4)
            
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            return json.loads(response_clean.strip())
        
        except json.JSONDecodeError:
            return {
                "relationship_assessment": "Unable to analyze",
                "spending_trend": "Unknown",
                "insights": [],
                "concerns": [],
                "recommendations": []
            }
    
    def _prepare_transaction_summary(self, transactions: List[Dict]) -> Dict:
        """Prepare transaction summary for AI"""
        
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
