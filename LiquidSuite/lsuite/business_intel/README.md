# Business Intelligence & Reconciliation Module

AI-powered invoice/PO reconciliation, cash flow forecasting, and business statement generation.

## Features

### 📄 Document Management
- **PDF Upload**: Upload invoices and purchase orders
- **Smart Extraction**: AI + rule-based data extraction
- **Auto-Reconciliation**: Match documents to bank transactions
- **Context Analysis**: AI insights with transaction history

### 📊 Cash Flow Forecasting
- **30/60/90 Day Forecasts**: Predict future cash position
- **Pattern Recognition**: Identify recurring income/expenses
- **Risk Assessment**: Flag potential cash flow issues
- **Fee Analysis**: Track and analyze transaction fees

### 📝 Statement Generation
- **Customer Statements**: Send to clients with invoice details
- **Internal Statements**: Business cash flow reports
- **Period Analysis**: Custom date range reporting
- **AI Insights**: Automated financial commentary

## Setup

### 1. Add Models to Database

Add these models to `lsuite/models.py`:

```python
from lsuite.business_intel.models import (
    UploadedDocument,
    DocumentTransaction,
    CashFlowForecast,
    BusinessStatement
)
```

### 2. Run Migrations

```bash
flask db migrate -m "Add business intelligence models"
flask db upgrade
```

### 3. Create Upload Folder

```bash
mkdir -p uploads/documents
```

### 4. Register Blueprint

In `lsuite/__init__.py`:

```python
from lsuite.business_intel import bi_bp

app.register_blueprint(bi_bp, url_prefix='/business-intel')
```

### 5. Install Dependencies

```bash
pip install PyPDF2
```

## Usage

### Upload Invoice/PO

```python
POST /business-intel/upload
Files: file (PDF)
Form: document_type (invoice/purchase_order)

Response: Redirects to document detail with extracted data
```

### Generate Forecast

```python
GET /business-intel/forecast?history=90&forecast=30

Returns:
- Predicted income/expenses
- Weekly breakdown
- Risk factors
- Recommendations
```

### Create Statement

```python
POST /business-intel/statements/generate
Form:
  - statement_type: customer/internal
  - period_start: YYYY-MM-DD
  - period_end: YYYY-MM-DD
  - customer_name (optional)
  - customer_email (optional)

Response: Generated statement with transactions
```

## AI Features

### Document Analysis
- Payment status detection
- Amount variance checking
- Due date predictions
- Risk flagging

### Cash Flow Forecasting
- Historical pattern analysis
- Recurring transaction detection
- Pending document impact
- Confidence scoring

### Fee Analysis
- Bank fee detection
- Service charge categorization
- Monthly fee averaging
- Cost optimization suggestions

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/business-intel/dashboard` | GET | BI overview |
| `/business-intel/upload` | GET/POST | Upload documents |
| `/business-intel/documents` | GET | List documents |
| `/business-intel/documents/<id>` | GET | Document detail |
| `/business-intel/documents/<id>/analyze` | POST | Run AI analysis |
| `/business-intel/forecast` | GET | Cash flow forecast |
| `/business-intel/statements/generate` | GET/POST | Create statement |
| `/business-intel/statements` | GET | List statements |
| `/business-intel/statements/<id>` | GET | Statement detail |

## Document Extraction

### Supported Formats
- Standard SA invoices (PDF)
- Purchase orders (PDF)
- Bank statements (via existing module)

### Extracted Fields
- Document number
- Document date
- Due date
- Supplier/customer name
- Line items
- Subtotal, tax, total
- Payment terms

### Extraction Methods
1. **Rule-based**: Regex patterns for common formats
2. **AI-assisted**: Groq AI for complex documents
3. **Manual**: Fallback for failed extraction

## Statement Types

### Customer Statement
- Invoices issued
- Payments received
- Outstanding balance
- Aging analysis
- Contact information

### Internal Statement
- All transactions
- Income vs expenses
- Category breakdown
- Fee analysis
- Cash flow summary
- AI insights

## Configuration

### Environment Variables

```bash
# Required for AI features
GROQ_API_KEYS=gsk_key1,gsk_key2

# Upload settings
MAX_UPLOAD_SIZE=10485760  # 10MB
UPLOAD_FOLDER=uploads/documents
```

### Database Schema

```sql
-- uploaded_documents
CREATE TABLE uploaded_documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    filename VARCHAR(255),
    document_type VARCHAR(50),
    document_number VARCHAR(100),
    total_amount DECIMAL(15,2),
    is_reconciled BOOLEAN DEFAULT FALSE,
    ...
);

-- document_transactions (many-to-many)
CREATE TABLE document_transactions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES uploaded_documents(id),
    transaction_id INTEGER REFERENCES bank_transactions(id),
    match_confidence FLOAT,
    ...
);

-- cash_flow_forecasts
CREATE TABLE cash_flow_forecasts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    forecast_date DATE,
    predicted_income DECIMAL(15,2),
    predicted_expenses DECIMAL(15,2),
    ...
);

-- business_statements
CREATE TABLE business_statements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    statement_type VARCHAR(50),
    statement_number VARCHAR(100) UNIQUE,
    period_start DATE,
    period_end DATE,
    ...
);
```

## Navigation

Add to sidebar:

```html
<li class="nav-item mt-3">
    <h6 class="sidebar-heading px-3 text-muted">Business Intel</h6>
</li>
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('business_intel.dashboard') }}">
        <i class="fas fa-chart-pie"></i> BI Dashboard
    </a>
</li>
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('business_intel.upload') }}">
        <i class="fas fa-upload"></i> Upload Document
    </a>
</li>
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('business_intel.documents') }}">
        <i class="fas fa-file-invoice"></i> Documents
    </a>
</li>
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('business_intel.forecast') }}">
        <i class="fas fa-crystal-ball"></i> Forecast
    </a>
</li>
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('business_intel.statements') }}">
        <i class="fas fa-file-alt"></i> Statements
    </a>
</li>
```

## Example Workflow

### 1. Upload Invoice
```bash
1. Go to Business Intel → Upload Document
2. Select PDF invoice
3. Choose type: Invoice
4. Click Upload
5. System extracts: number, date, amount, supplier
6. AI analyzes against transactions
7. Shows payment status and insights
```

### 2. Generate Forecast
```bash
1. Go to Business Intel → Forecast
2. Select forecast period (30/60/90 days)
3. AI analyzes:
   - Historical patterns
   - Pending documents
   - Recurring transactions
4. View predicted cash flow
5. Review risk factors
6. Follow recommendations
```

### 3. Create Statement
```bash
1. Go to Business Intel → Statements → Generate
2. Select type (Customer/Internal)
3. Choose date range
4. Add customer details (if customer statement)
5. Generate
6. Download PDF or email
```

## Troubleshooting

### Extraction Fails
- Check PDF is not password protected
- Ensure PDF contains text (not just images)
- Try re-uploading with different settings
- Check logs for specific errors

### AI Not Working
- Verify GROQ_API_KEYS is set
- Check API key validity
- Monitor rate limits
- Review error logs

### Database Errors
- Ensure migrations are run
- Check model imports
- Verify foreign key relationships
- Review database logs

## Future Enhancements

- [ ] ERPNext document sync
- [ ] Multi-currency support
- [ ] Email statement delivery
- [ ] PDF generation for statements
- [ ] Advanced reconciliation rules
- [ ] Budget tracking
- [ ] Profit/loss reporting
- [ ] Tax calculation
- [ ] Multi-company support
- [ ] Role-based access control
