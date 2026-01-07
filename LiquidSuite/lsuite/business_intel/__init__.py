"""
Business Intelligence & Reconciliation Blueprint
"""
from flask import Blueprint

bi_bp = Blueprint('business_intel', __name__)

from lsuite.business_intel import routes
