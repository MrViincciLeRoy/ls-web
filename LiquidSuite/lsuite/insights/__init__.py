"""
Insights Blueprint - Analytics for Accountants
"""
from flask import Blueprint

insights_bp = Blueprint('insights', __name__)

from lsuite.insights import routes
