"""
Business Intelligence Routes
"""
import os
import logging
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from lsuite.business_intel import bi_bp
from lsuite.extensions import db
from lsuite.models import BankTransaction
from lsuite.business_intel.pdf_service import DocumentExtractor
from lsuite.business_intel.forecast_service import CashFlowForecaster

logger = logging.getLogger(__name__)

# Import models - need to add these to main models.py
try:
    from lsuite.models import UploadedDocument, DocumentTransaction, CashFlowForecast, BusinessStatement
except ImportError:
    logger.warning("Business Intelligence models not found - add to models.py")

ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = 'uploads/documents'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bi_bp.route('/dashboard')
@login_required
def dashboard():
    """Business Intelligence dashboard"""
    
    days = request.args.get('days', 90, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # Get transactions
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).order_by(BankTransaction.date.desc()).all()
    
    # Get uploaded documents
    try:
        documents = UploadedDocument.query.filter_by(
            user_id=current_user.id
        ).order_by(UploadedDocument.created_at.desc()).limit(20).all()
    except:
        documents = []
    
    # Calculate summary stats
    total_income = sum(float(t.deposit or 0) for t in transactions)
    total_expenses = sum(float(t.withdrawal or 0) for t in transactions)
    
    try:
        total_invoices = sum(
            float(d.total_amount) for d in documents 
            if d.document_type == 'invoice' and not d.is_reconciled
        )
        total_pos = sum(
            float(d.total_amount) for d in documents 
            if d.document_type == 'purchase_order' and not d.is_reconciled
        )
    except:
        total_invoices = 0
        total_pos = 0
    
    # Generate forecast
    forecaster = CashFlowForecaster()
    try:
        forecast = forecaster.generate_forecast(transactions, documents, period_days=30)
    except:
        forecast = {
            'predicted_income': 0,
            'predicted_expenses': 0,
            'predicted_balance': 0,
            'confidence_score': 0,
            'insights': []
        }
    
    # Analyze fees
    try:
        fee_analysis = forecaster.analyze_transaction_fees(transactions)
    except:
        fee_analysis = {'total_fees': 0, 'insights': []}
    
    return render_template('business_intel/dashboard.html',
        days=days,
        total_income=total_income,
        total_expenses=total_expenses,
        total_invoices=total_invoices,
        total_pos=total_pos,
        documents=documents,
        document_count=len(documents),
        forecast=forecast,
        fee_analysis=fee_analysis,
        transactions=transactions
    )


@bi_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    """Upload invoice or PO"""
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        doc_type = request.form.get('document_type', 'invoice')
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            # Ensure upload folder exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Create document record
            try:
                document = UploadedDocument(
                    user_id=current_user.id,
                    filename=file.filename,
                    document_type=doc_type,
                    file_path=filepath,
                    file_size=os.path.getsize(filepath),
                    total_amount=0,
                    processing_status='uploaded'
                )
                db.session.add(document)
                db.session.commit()
                
                # Extract data in background (or inline for simplicity)
                try:
                    extractor = DocumentExtractor()
                    result = extractor.extract_from_pdf(filepath)
                    
                    if result['success']:
                        # Update document with extracted data
                        data = result['data']
                        document.extracted_text = result['text']
                        document.extracted_data = data
                        document.extraction_method = result['method']
                        
                        document.document_number = data.get('document_number')
                        document.document_date = data.get('document_date')
                        document.due_date = data.get('due_date')
                        document.supplier_name = data.get('supplier_name')
                        document.customer_name = data.get('customer_name')
                        document.subtotal = data.get('subtotal')
                        document.tax_amount = data.get('tax_amount')
                        document.total_amount = data.get('total_amount', 0)
                        
                        document.processing_status = 'extracted'
                    else:
                        document.processing_status = 'failed'
                        document.error_message = result.get('error')
                    
                    db.session.commit()
                    
                    flash(f'Document uploaded and processed! (Method: {result.get("method", "unknown")})', 'success')
                    return redirect(url_for('business_intel.document_detail', id=document.id))
                
                except Exception as e:
                    logger.error(f"Extraction failed: {e}")
                    document.processing_status = 'failed'
                    document.error_message = str(e)
                    db.session.commit()
                    flash(f'Document uploaded but extraction failed: {str(e)}', 'warning')
                    return redirect(url_for('business_intel.documents'))
            
            except Exception as e:
                logger.error(f"Document creation failed: {e}")
                flash(f'Upload failed: {str(e)}', 'danger')
                return redirect(request.url)
        
        else:
            flash('Invalid file type. Only PDF files are allowed.', 'danger')
            return redirect(request.url)
    
    return render_template('business_intel/upload.html')


@bi_bp.route('/documents')
@login_required
def documents():
    """List uploaded documents"""
    
    try:
        docs = UploadedDocument.query.filter_by(
            user_id=current_user.id
        ).order_by(UploadedDocument.created_at.desc()).all()
    except:
        docs = []
        flash('Document tracking not yet configured. Run database migrations.', 'warning')
    
    return render_template('business_intel/documents.html', documents=docs)


@bi_bp.route('/documents/<int:id>')
@login_required
def document_detail(id):
    """Document detail with AI analysis"""
    
    try:
        document = UploadedDocument.query.get_or_404(id)
        
        if document.user_id != current_user.id:
            flash('Unauthorized', 'danger')
            return redirect(url_for('business_intel.documents'))
        
        # Get related transactions
        transactions = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id
        ).order_by(BankTransaction.date.desc()).limit(100).all()
        
        # Get AI analysis
        extractor = DocumentExtractor()
        analysis = extractor.analyze_document_with_context(document, transactions)
        
        return render_template('business_intel/document_detail.html',
            document=document,
            analysis=analysis,
            transactions=transactions[:20]
        )
    
    except Exception as e:
        logger.error(f"Document detail error: {e}")
        flash(f'Error loading document: {str(e)}', 'danger')
        return redirect(url_for('business_intel.documents'))


@bi_bp.route('/documents/<int:id>/analyze', methods=['POST'])
@login_required
def analyze_document(id):
    """Run AI analysis on document"""
    
    try:
        document = UploadedDocument.query.get_or_404(id)
        
        if document.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        transactions = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id
        ).order_by(BankTransaction.date.desc()).limit(100).all()
        
        extractor = DocumentExtractor()
        analysis = extractor.analyze_document_with_context(document, transactions)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bi_bp.route('/forecast')
@login_required
def forecast():
    """Cash flow forecast page"""
    
    days_history = request.args.get('history', 90, type=int)
    days_forecast = request.args.get('forecast', 30, type=int)
    
    start_date = datetime.now() - timedelta(days=days_history)
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id,
        BankTransaction.date >= start_date.date()
    ).all()
    
    try:
        documents = UploadedDocument.query.filter_by(
            user_id=current_user.id
        ).all()
    except:
        documents = []
    
    forecaster = CashFlowForecaster()
    forecast_data = forecaster.generate_forecast(transactions, documents, period_days=days_forecast)
    
    # Analyze patterns
    patterns = forecaster._analyze_patterns(transactions)
    
    # Fee analysis
    fee_analysis = forecaster.analyze_transaction_fees(transactions)
    
    return render_template('business_intel/forecast.html',
        days_history=days_history,
        days_forecast=days_forecast,
        forecast=forecast_data,
        patterns=patterns,
        fee_analysis=fee_analysis,
        transactions=transactions
    )


@bi_bp.route('/statements/generate', methods=['GET', 'POST'])
@login_required
def generate_statement():
    """Generate business statement"""
    
    if request.method == 'POST':
        statement_type = request.form.get('statement_type', 'internal')
        period_start = datetime.strptime(request.form['period_start'], '%Y-%m-%d').date()
        period_end = datetime.strptime(request.form['period_end'], '%Y-%m-%d').date()
        
        # Get transactions for period
        transactions = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.date >= period_start,
            BankTransaction.date <= period_end
        ).order_by(BankTransaction.date).all()
        
        # Calculate totals
        total_income = sum(float(t.deposit or 0) for t in transactions)
        total_expenses = sum(float(t.withdrawal or 0) for t in transactions)
        
        # For customer statement, would need customer selection
        customer_name = request.form.get('customer_name', '')
        customer_email = request.form.get('customer_email', '')
        
        try:
            statement = BusinessStatement(
                user_id=current_user.id,
                statement_type=statement_type,
                statement_number=f"STMT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                statement_date=datetime.now().date(),
                period_start=period_start,
                period_end=period_end,
                customer_name=customer_name,
                customer_email=customer_email,
                opening_balance=0,  # Would calculate from previous period
                total_invoices=total_income,
                total_payments=total_expenses,
                closing_balance=total_income - total_expenses,
                statement_data={
                    'transactions': [
                        {
                            'date': t.date.isoformat(),
                            'description': t.description,
                            'debit': float(t.withdrawal or 0),
                            'credit': float(t.deposit or 0),
                            'balance': float(t.balance or 0)
                        }
                        for t in transactions
                    ]
                }
            )
            
            db.session.add(statement)
            db.session.commit()
            
            flash('Statement generated successfully!', 'success')
            return redirect(url_for('business_intel.statement_detail', id=statement.id))
        
        except Exception as e:
            logger.error(f"Statement generation failed: {e}")
            flash(f'Failed to generate statement: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('business_intel/generate_statement.html')


@bi_bp.route('/statements')
@login_required
def statements():
    """List generated statements"""
    
    try:
        stmts = BusinessStatement.query.filter_by(
            user_id=current_user.id
        ).order_by(BusinessStatement.created_at.desc()).all()
    except:
        stmts = []
        flash('Statement tracking not configured. Run database migrations.', 'warning')
    
    return render_template('business_intel/statements.html', statements=stmts)


@bi_bp.route('/statements/<int:id>')
@login_required
def statement_detail(id):
    """View statement detail"""
    
    try:
        statement = BusinessStatement.query.get_or_404(id)
        
        if statement.user_id != current_user.id:
            flash('Unauthorized', 'danger')
            return redirect(url_for('business_intel.statements'))
        
        return render_template('business_intel/statement_detail.html', statement=statement)
    
    except Exception as e:
        logger.error(f"Statement detail error: {e}")
        flash(f'Error loading statement: {str(e)}', 'danger')
        return redirect(url_for('business_intel.statements'))
