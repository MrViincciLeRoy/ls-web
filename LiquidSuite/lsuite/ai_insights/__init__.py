"""
AI Insights Blueprint - Groq AI-powered financial analysis
"""
from flask import Blueprint

ai_insights_bp = Blueprint('ai_insights', __name__)

from lsuite.ai_insights import routes
