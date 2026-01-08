# lsuite/models.py
"""
Database models for LiquidSuite - FIXED - NO DUPLICATES
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from lsuite.extensions import db

# =============================================================================
# User Models
# =============================================================================

class User(UserMixin, db.Model):
    """User account model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Claude Haiku 4.5 AI Settings
    ai_enabled = db.Column(db.Boolean, default=True)
    ai_model = db.Column(db.String(50), default='claude-haiku-4.5')
    ai_can_access_files = db.Column(db.Boolean, default=True)
    ai_can_edit_files = db.Column(db.Boolean, default=True)
    
    # Relationships
    bank_accounts = db.relationship('BankAccount', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    bank_transactions = db.relationship('BankTransaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    email_statements = db.relationship('EmailStatement', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def __repr__(self):
        return f'<User {self.username}>'


# =============================================================================
# Banking Models
# =============================================================================

class BankAccount(db.Model):
    """Bank account model"""
    __tablename__ = 'bank_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_name = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(100))
    bank_name = db.Column(db.String(100))
    account_type = db.Column(db.String(50))
    currency = db.Column(db.String(3), default='ZAR')
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='bank_account', lazy='dynamic', cascade='all, delete-orphan')
    bank_transactions = db.relationship('BankTransaction', backref='bank_account', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<BankAccount {self.account_name}>'


class Transaction(db.Model):
    """Bank transaction model (legacy)"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    posting_date = db.Column(db.Date)
    description = db.Column(db.String(500), nullable=False)
    reference_number = db.Column(db.String(100), index=True)
    
    # Amount fields
    debit = db.Column(db.Numeric(15, 2), default=0.00)
    credit = db.Column(db.Numeric(15, 2), default=0.00)
    balance = db.Column(db.Numeric(15, 2))
    
    # Categorization
    category = db.Column(db.String(100))
    tags = db.Column(db.String(500))
    notes = db.Column(db.Text)
    
    # Reconciliation
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.DateTime)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def amount(self):
        """Get transaction amount (credit - debit)"""
        return float(self.credit or 0) - float(self.debit or 0)
    
    @property
    def transaction_type(self):
        """Get transaction type"""
        if self.credit and self.credit > 0:
            return 'credit'
        elif self.debit and self.debit > 0:
            return 'debit'
        return 'unknown'
    
    def __repr__(self):
        return f'<Transaction {self.reference_number or self.id}>'


class GoogleCredential(db.Model):
    """Google OAuth credentials storage"""
    __tablename__ = 'google_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    client_id = db.Column(db.String(255), nullable=False)
    client_secret = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expiry = db.Column(db.DateTime)
    is_authenticated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GoogleCredential {self.name}>'


class TransactionCategory(db.Model):
    """Transaction categorization for ERPNext mapping"""
    __tablename__ = 'transaction_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    erpnext_account = db.Column(db.String(200), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    keywords = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    color = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    transactions = db.relationship('BankTransaction', back_populates='category', lazy='dynamic')
    
    def get_keywords_list(self):
        """Return keywords as a list"""
        if not self.keywords:
            return []
        return [k.strip().lower() for k in self.keywords.split(',')]
    
    def matches_description(self, description):
        """Check if any keyword matches the description"""
        if not description:
            return False
        description_lower = description.lower()
        return any(keyword in description_lower for keyword in self.get_keywords_list())
    
    def __repr__(self):
        return f'<TransactionCategory {self.name}>'


class BankTransaction(db.Model):
    """Bank transaction model for ERPNext integration"""
    __tablename__ = 'bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=True)
    statement_id = db.Column(db.Integer, db.ForeignKey('email_statements.id'))
    
    # Transaction details
    date = db.Column(db.Date, nullable=False, index=True)
    posting_date = db.Column(db.Date, index=True)
    description = db.Column(db.String(500), nullable=False)
    reference_number = db.Column(db.String(100), index=True)
    
    # Amounts
    deposit = db.Column(db.Numeric(15, 2), default=0.00)
    withdrawal = db.Column(db.Numeric(15, 2), default=0.00)
    balance = db.Column(db.Numeric(15, 2))
    
    # Additional fields
    currency = db.Column(db.String(3), default='ZAR')
    unallocated_amount = db.Column(db.Numeric(15, 2))
    
    # Categorization
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'))
    tags = db.Column(db.String(500))
    notes = db.Column(db.Text)
    
    # Reconciliation
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.DateTime)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    
    # ERPNext integration
    erpnext_id = db.Column(db.String(100), index=True)
    erpnext_synced = db.Column(db.Boolean, default=False)
    erpnext_sync_date = db.Column(db.DateTime)
    erpnext_journal_entry = db.Column(db.String(100))
    erpnext_error = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to category
    category = db.relationship('TransactionCategory', back_populates='transactions')

    @property
    def amount(self):
        """Get transaction amount"""
        return float(self.deposit or 0) - float(self.withdrawal or 0)
    
    @property
    def transaction_type(self):
        """Get transaction type"""
        if self.deposit and self.deposit > 0:
            return 'deposit'
        elif self.withdrawal and self.withdrawal > 0:
            return 'withdrawal'
        return 'unknown'
    
    @property
    def is_categorized(self):
        """Check if transaction is categorized"""
        return self.category_id is not None
    
    def to_erpnext_format(self):
        """Convert to ERPNext format"""
        return {
            "date": self.date.strftime('%Y-%m-%d') if self.date else None,
            "posting_date": self.posting_date.strftime('%Y-%m-%d') if self.posting_date else None,
            "description": self.description,
            "deposit": float(self.deposit or 0),
            "withdrawal": float(self.withdrawal or 0),
            "currency": self.currency,
            "bank_account": self.bank_account.account_name if self.bank_account else None,
            "reference_number": self.reference_number,
            "unallocated_amount": float(self.unallocated_amount or 0)
        }
    
    def __repr__(self):
        return f'<BankTransaction {self.reference_number or self.id}>'


# =============================================================================
# Email Statement Models
# =============================================================================

class EmailStatement(db.Model):
    """Email statement model for Gmail integration"""
    __tablename__ = 'email_statements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Email details
    gmail_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    thread_id = db.Column(db.String(255), index=True)
    subject = db.Column(db.String(500))
    sender = db.Column(db.String(255))
    received_date = db.Column(db.DateTime, index=True)
    
    # Statement details
    statement_date = db.Column(db.Date, index=True)
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(100))
    
    # PDF details
    has_pdf = db.Column(db.Boolean, default=False)
    pdf_password = db.Column(db.String(100))
    
    # Processing status
    state = db.Column(db.String(50), default='new')
    is_processed = db.Column(db.Boolean, default=False)
    processed_date = db.Column(db.DateTime)
    transaction_count = db.Column(db.Integer, default=0)
    
    # Content
    body_text = db.Column(db.Text)
    body_html = db.Column(db.Text)
    
    # Errors
    error_message = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('BankTransaction', backref='statement', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<EmailStatement {self.gmail_id}>'


# =============================================================================
# Invoice Models
# =============================================================================

class Invoice(db.Model):
    """Invoice model"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Invoice details
    invoice_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    invoice_date = db.Column(db.Date, nullable=False, index=True)
    due_date = db.Column(db.Date)
    
    # Customer/Supplier
    customer_name = db.Column(db.String(200), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_address = db.Column(db.Text)
    
    # Financial details
    subtotal = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    tax_amount = db.Column(db.Numeric(15, 2), default=0.00)
    tax_rate = db.Column(db.Numeric(5, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(15, 2), default=0.00)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    paid_amount = db.Column(db.Numeric(15, 2), default=0.00)
    outstanding_amount = db.Column(db.Numeric(15, 2), default=0.00)
    
    currency = db.Column(db.String(3), default='ZAR')
    
    # Status
    status = db.Column(db.String(50), default='draft', index=True)
    
    # ERPNext integration
    erpnext_id = db.Column(db.String(100), index=True)
    erpnext_synced = db.Column(db.Boolean, default=False)
    erpnext_sync_date = db.Column(db.DateTime)
    
    # Metadata
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='invoice', lazy='dynamic')
    bank_transactions = db.relationship('BankTransaction', backref='invoice', lazy='dynamic')
    
    @property
    def is_paid(self):
        """Check if invoice is fully paid"""
        return self.outstanding_amount <= 0
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.due_date and self.status not in ['paid', 'cancelled']:
            return datetime.now().date() > self.due_date
        return False
    
    def calculate_totals(self):
        """Recalculate invoice totals from items"""
        self.subtotal = sum(item.total for item in self.items)
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.outstanding_amount = self.total_amount - self.paid_amount
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class InvoiceItem(db.Model):
    """Invoice line item model"""
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    item_code = db.Column(db.String(100))
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    total = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Metadata
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_total(self):
        """Calculate line item total"""
        self.total = self.quantity * self.unit_price
    
    def __repr__(self):
        return f'<InvoiceItem {self.description[:30]}>'


# =============================================================================
# ERPNext Integration Models
# =============================================================================

class ERPNextConfig(db.Model):
    """ERPNext configuration model"""
    __tablename__ = 'erpnext_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    api_secret = db.Column(db.String(255), nullable=False)
    
    default_company = db.Column(db.String(200))
    bank_account = db.Column(db.String(200))
    default_cost_center = db.Column(db.String(200))
    
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ERPNextConfig {self.name}>'


class ERPNextSyncLog(db.Model):
    """ERPNext synchronization log model"""
    __tablename__ = 'erpnext_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('erpnext_configs.id'), nullable=False)
    
    record_type = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    
    erpnext_doctype = db.Column(db.String(100))
    erpnext_doc_name = db.Column(db.String(200))
    
    status = db.Column(db.String(20), nullable=False)
    error_message = db.Column(db.Text)
    
    sync_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ERPNextSyncLog {self.record_type}:{self.record_id} {self.status}>'


# Alias for backwards compatibility
SyncLog = ERPNextSyncLog


# =============================================================================
# Business Intelligence Models - ONLY ONE DEFINITION
# =============================================================================

class UploadedDocument(db.Model):
    """Uploaded invoice/PO documents stored in PostgreSQL"""
    __tablename__ = 'uploaded_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # File info
    filename = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer)
    file_data = db.Column(db.LargeBinary)  # Store PDF in PostgreSQL
    
    # Extracted data
    extracted_text = db.Column(db.Text)
    extracted_data = db.Column(db.JSON)
    extraction_method = db.Column(db.String(50))
    
    # Document details
    document_number = db.Column(db.String(100))
    document_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    supplier_name = db.Column(db.String(200))
    customer_name = db.Column(db.String(200))
    
    # Amounts
    subtotal = db.Column(db.Numeric(15, 2))
    tax_amount = db.Column(db.Numeric(15, 2))
    total_amount = db.Column(db.Numeric(15, 2), default=0)
    currency = db.Column(db.String(3), default='ZAR')
    
    # Status
    is_reconciled = db.Column(db.Boolean, default=False)
    processing_status = db.Column(db.String(50), default='uploaded')
    error_message = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('DocumentTransaction', back_populates='document', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UploadedDocument {self.document_number or self.filename}>'


class DocumentTransaction(db.Model):
    """Link documents to bank transactions"""
    __tablename__ = 'document_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('uploaded_documents.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('bank_transactions.id'), nullable=False)
    
    match_confidence = db.Column(db.Float)
    match_type = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('UploadedDocument', back_populates='transactions')
    transaction = db.relationship('BankTransaction')
    
    def __repr__(self):
        return f'<DocumentTransaction {self.id}>'


class CashFlowForecast(db.Model):
    """Cash flow forecasts"""
    __tablename__ = 'cash_flow_forecasts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    forecast_date = db.Column(db.Date, nullable=False)
    forecast_period_days = db.Column(db.Integer, default=30)
    
    predicted_income = db.Column(db.Numeric(15, 2))
    predicted_expenses = db.Column(db.Numeric(15, 2))
    predicted_balance = db.Column(db.Numeric(15, 2))
    
    confidence_score = db.Column(db.Float)
    forecast_data = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CashFlowForecast {self.forecast_date}>'


class BusinessStatement(db.Model):
    """Generated business statements"""
    __tablename__ = 'business_statements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    statement_type = db.Column(db.String(50), nullable=False)
    statement_number = db.Column(db.String(100), unique=True, nullable=False)
    statement_date = db.Column(db.Date, nullable=False)
    
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    customer_name = db.Column(db.String(200))
    customer_email = db.Column(db.String(200))
    
    opening_balance = db.Column(db.Numeric(15, 2))
    total_invoices = db.Column(db.Numeric(15, 2))
    total_payments = db.Column(db.Numeric(15, 2))
    closing_balance = db.Column(db.Numeric(15, 2))
    
    statement_data = db.Column(db.JSON)
    
    is_sent = db.Column(db.Boolean, default=False)
    sent_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BusinessStatement {self.statement_number}>'