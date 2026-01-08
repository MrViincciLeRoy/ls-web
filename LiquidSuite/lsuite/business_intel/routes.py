"""
Business Intelligence Routes - Fixed with PostgreSQL storage
"""
import logging
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from lsuite.business_intel import bi_bp
from lsuite.extensions import db
from lsuite.models import BankTransaction, UploadedDocument, DocumentTransaction, CashFlowForecast, BusinessStatement
from lsuite.business_intel.pdf_service import DocumentExtractor
from lsuite.business_intel.forecast_service import CashFlowForecaster

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

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
    documents = UploadedDocument.query.filter_by(
        user_id=current_user.id
    ).order_by(UploadedDocument.created_at.desc()).limit(20).all()
    
    # Calculate summary stats
    total_income = sum(float(t.deposit or 0) for t in transactions)
    total_expenses = sum(float(t.withdrawal or 0) for t in transactions)
    
    total_invoices = sum(
        float(d.total_amount) for d in documents 
        if d.document_type == 'invoice' and not d.is_reconciled
    )
    total_pos = sum(
        float(d.total_amount) for d in documents 
        if d.document_type == 'purchase_order' and not d.is_reconciled
    )
    
    # Generate forecast
    forecaster = CashFlowForecaster()
    try:
        forecast = forecaster.generate_forecast(transactions, documents, period_days=30)
    except Exception as e:
        logger.error(f"Forecast error: {e}")
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
    except Exception as e:
        logger.error(f"Fee analysis error: {e}")
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
    """Upload invoice or PO - Store in PostgreSQL"""
    
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
            
            # Read file into memory
            file_data = file.read()
            file_size = len(file_data)
            
            if file_size > MAX_FILE_SIZE:
                flash(f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB', 'danger')
                return redirect(request.url)
            
            # Create document record with binary data
            try:
                document = UploadedDocument(
                    user_id=current_user.id,
                    filename=filename,
                    document_type=doc_type,
                    file_size=file_size,
                    file_data=file_data,  # Store in PostgreSQL
                    total_amount=0,
                    processing_status='uploaded'
                )
                db.session.add(document)
                db.session.commit()
                
                # Extract data
                try:
                    import tempfile
                    import os
                    
                    # Create temporary file for extraction
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        tmp.write(file_data)
                        tmp_path = tmp.name
                    
                    extractor = DocumentExtractor()
                    result = extractor.extract_from_pdf(tmp_path)
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    if result['success']:
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
                db.session.rollback()
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
    
    docs = UploadedDocument.query.filter_by(
        user_id=current_user.id
    ).order_by(UploadedDocument.created_at.desc()).all()
    
    return render_template('business_intel/documents.html', documents=docs)


@bi_bp.route('/documents/<int:id>')
@login_required
def document_detail(id):
    """Document detail with AI analysis"""
    
    document = UploadedDocument.query.get_or_404(id)
    
    if document.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('business_intel.documents'))
    
    # Get related transactions
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id
    ).order_by(BankTransaction.date.desc()).limit(100).all()
    
    # Get AI analysis
    try:
        extractor = DocumentExtractor()
        analysis = extractor.analyze_document_with_context(document, transactions)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        analysis = {
            'payment_status': 'unknown',
            'insights': [],
            'risk_flags': []
        }
    
    return render_template('business_intel/document_detail.html',
        document=document,
        analysis=analysis,
        transactions=transactions[:20]
    )


@bi_bp.route('/documents/<int:id>/download')
@login_required
def download_document(id):
    """Download original PDF from PostgreSQL"""
    from flask import send_file
    import io
    
    document = UploadedDocument.query.get_or_404(id)
    
    if document.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('business_intel.documents'))
    
    if not document.file_data:
        flash('File not found', 'danger')
        return redirect(url_for('business_intel.document_detail', id=id))
    
    return send_file(
        io.BytesIO(document.file_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=document.filename
    )


@bi_bp.route('/documents/<int:id>/analyze', methods=['POST'])
@login_required
def analyze_document(id):
    """Run AI analysis on document"""
    
    document = UploadedDocument.query.get_or_404(id)
    
    if document.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    transactions = BankTransaction.query.filter(
        BankTransaction.user_id == current_user.id
    ).order_by(BankTransaction.date.desc()).limit(100).all()
    
    try:
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
    
    documents = UploadedDocument.query.filter_by(
        user_id=current_user.id
    ).all()
    
    forecaster = CashFlowForecaster()
    forecast_data = forecaster.generate_forecast(transactions, documents, period_days=days_forecast)
    
    patterns = forecaster._analyze_patterns(transactions)
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
        
        transactions = BankTransaction.query.filter(
            BankTransaction.user_id == current_user.id,
            BankTransaction.date >= period_start,
            BankTransaction.date <= period_end
        ).order_by(BankTransaction.date).all()
        
        total_income = sum(float(t.deposit or 0) for t in transactions)
        total_expenses = sum(float(t.withdrawal or 0) for t in transactions)
        
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
                opening_balance=0,
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
            db.session.rollback()
            logger.error(f"Statement generation failed: {e}")
            flash(f'Failed to generate statement: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('business_intel/generate_statement.html')


@bi_bp.route('/statements')
@login_required
def statements():
    """List generated statements"""
    
    stmts = BusinessStatement.query.filter_by(
        user_id=current_user.id
    ).order_by(BusinessStatement.created_at.desc()).all()
    
    return render_template('business_intel/statements.html', statements=stmts)


@bi_bp.route('/statements/<int:id>')
@login_required
def statement_detail(id):
    """View statement detail"""
    
    statement = BusinessStatement.query.get_or_404(id)
    
    if statement.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('business_intel.statements'))
    
    return render_template('business_intel/statement_detail.html', statement=statement)
