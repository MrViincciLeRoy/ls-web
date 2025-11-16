# ============================================================================
# LiquidSuite/lsuite/gmail/routes.py - COMPLETE FIXED VERSION
# ============================================================================
"""
Gmail Routes - OAuth, Statement Import, CSV Upload
"""
from flask import render_template, redirect, url_for, flash, request, current_app, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

from lsuite.extensions import db
from lsuite.models import (
    GoogleCredential, EmailStatement, BankTransaction, 
    TransactionCategory
)
from lsuite.gmail.services import GmailService
from lsuite.gmail.csv_parser import CSVParser
from lsuite.gmail import gmail_bp

logger = logging.getLogger(__name__)


# ============================================================================
# Google OAuth Routes
# ============================================================================

@gmail_bp.route('/credentials')
@login_required
def credentials():
    """List Google OAuth credentials"""
    creds = GoogleCredential.query.filter_by(user_id=current_user.id).all()
    return render_template('gmail/credentials.html', credentials=creds)


@gmail_bp.route('/credentials/new', methods=['GET', 'POST'])
@login_required
def new_credential():
    """Create new Google OAuth credential"""
    if request.method == 'POST':
        credential = GoogleCredential(
            user_id=current_user.id,
            name=request.form['name'],
            client_id=request.form['client_id'],
            client_secret=request.form['client_secret']
        )
        
        db.session.add(credential)
        db.session.commit()
        
        flash('Google credential created! Now authorize access.', 'success')
        return redirect(url_for('gmail.authorize', id=credential.id))
    
    return render_template('gmail/credential_form.html')


@gmail_bp.route('/credentials/<int:id>/authorize')
@login_required
def authorize(id):
    """Start OAuth authorization flow"""
    credential = GoogleCredential.query.get_or_404(id)
    
    if credential.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    auth_url = service.get_auth_url(credential)
    
    return redirect(auth_url)


@gmail_bp.route('/oauth/callback')
@login_required
def oauth_callback():
    """OAuth callback handler"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        flash('OAuth authorization failed', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    credential = GoogleCredential.query.get(int(state))
    
    if not credential or credential.user_id != current_user.id:
        flash('Invalid credential', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    success = service.exchange_code_for_tokens(credential, code)
    
    if success:
        flash('✅ Gmail access authorized!', 'success')
    else:
        flash('❌ Authorization failed', 'danger')
    
    return redirect(url_for('gmail.credentials'))


@gmail_bp.route('/credentials/<int:id>/delete', methods=['POST'])
@login_required
def delete_credential(id):
    """Delete Google OAuth credential"""
    credential = GoogleCredential.query.get_or_404(id)
    
    if credential.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    db.session.delete(credential)
    db.session.commit()
    
    flash('Credential deleted', 'success')
    return redirect(url_for('gmail.credentials'))


# ============================================================================
# Email Statement Routes
# ============================================================================

@gmail_bp.route('/statements')
@login_required
def statements():
    """List email statements"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    
    statements = EmailStatement.query.filter_by(
        user_id=current_user.id
    ).order_by(
        EmailStatement.received_date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('gmail/statements.html', statements=statements)


@gmail_bp.route('/statements/import', methods=['POST'])
@login_required
def import_statements():
    """Import statements from Gmail"""
    credential = GoogleCredential.query.filter_by(
        user_id=current_user.id,
        is_authenticated=True
    ).first()
    
    if not credential:
        flash('No authenticated Google credential found', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    try:
        service = GmailService(current_app)
        imported, skipped = service.fetch_statements(credential)
        
        flash(f'✅ Imported {imported} statements ({skipped} already existed)', 'success')
    except Exception as e:
        flash(f'❌ Import failed: {str(e)}', 'danger')
        logger.error(f"Statement import error: {str(e)}")
    
    return redirect(url_for('gmail.statements'))


@gmail_bp.route('/statements/<int:id>')
@login_required
def statement_detail(id):
    """View statement details"""
    statement = EmailStatement.query.get_or_404(id)
    
    if statement.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.statements'))
    
    transactions = BankTransaction.query.filter_by(
        statement_id=statement.id
    ).order_by(BankTransaction.date.desc()).all()
    
    return render_template('gmail/statement_detail.html', 
                         statement=statement, 
                         transactions=transactions)


@gmail_bp.route('/statements/<int:id>/parse', methods=['POST'])
@login_required
def parse_statement(id):
    """Parse PDF from statement with password support - FIXED VERSION"""
    statement = EmailStatement.query.get_or_404(id)
    
    if statement.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.statements'))
    
    credential = GoogleCredential.query.filter_by(
        user_id=current_user.id,
        is_authenticated=True
    ).first()
    
    if not credential:
        flash('No authenticated Google credential', 'danger')
        return redirect(url_for('gmail.statements'))
    
    # ✅ FIX: Get password from form - check for 'yes' value
    pdf_password = request.form.get('pdf_password', '').strip()
    save_password = request.form.get('save_password') == 'yes'
    
    logger.info(f"Parse request for statement {id}")
    logger.info(f"Password provided: {'Yes' if pdf_password else 'No'} (length: {len(pdf_password) if pdf_password else 0})")
    logger.info(f"Save password: {save_password}")
    logger.info(f"Existing saved password: {'Yes' if statement.pdf_password else 'No'}")
    
    # Determine which password to use: new password takes priority, then saved password
    password_to_use = pdf_password if pdf_password else statement.pdf_password
    
    # Save password if requested and provided
    if save_password and pdf_password:
        statement.pdf_password = pdf_password
        db.session.commit()
        logger.info(f"Saved password for statement {id}")
    
    # Log what we're using
    if password_to_use:
        logger.info(f"Using password for parsing (length: {len(password_to_use)})")
    else:
        logger.warning(f"No password available for statement {id}")
    
    try:
        service = GmailService(current_app)
        
        # ✅ FIX: Temporarily update statement password for parsing
        old_password = statement.pdf_password
        statement.pdf_password = password_to_use
        
        # Parse the PDF
        transaction_count = service.download_and_parse_pdf(credential, statement)
        
        # Restore old password if we didn't save the new one
        if not save_password and pdf_password:
            statement.pdf_password = old_password
            db.session.commit()
        
        flash(f'✅ Successfully extracted {transaction_count} transactions', 'success')
        logger.info(f"Successfully parsed {transaction_count} transactions from statement {id}")
        
    except ValueError as e:
        # ✅ FIX: Better error handling for password-related errors
        error_msg = str(e)
        if 'password' in error_msg.lower():
            flash(f'❌ {error_msg}. Please enter the correct PDF password.', 'danger')
            logger.error(f"Password error for statement {id}: {error_msg}")
        else:
            flash(f'❌ Parse failed: {error_msg}', 'danger')
            logger.error(f"Parse error for statement {id}: {error_msg}")
    except Exception as e:
        flash(f'❌ Parse failed: {str(e)}', 'danger')
        logger.error(f"Unexpected error parsing statement {id}: {str(e)}", exc_info=True)
    
    return redirect(url_for('gmail.statement_detail', id=id))


@gmail_bp.route('/statements/<int:id>/delete', methods=['POST'])
@login_required
def delete_statement(id):
    """Delete statement and all related transactions"""
    statement = EmailStatement.query.get_or_404(id)
    
    if statement.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.statements'))
    
    try:
        # Get transaction count for logging
        transaction_count = BankTransaction.query.filter_by(statement_id=statement.id).count()
        
        # Delete all related transactions (cascade should handle this, but being explicit)
        BankTransaction.query.filter_by(statement_id=statement.id).delete()
        
        # Delete the statement
        db.session.delete(statement)
        db.session.commit()
        
        flash(f'✅ Statement deleted successfully! ({transaction_count} related transactions removed)', 'success')
        logger.info(f"User {current_user.id} deleted statement {id} with {transaction_count} transactions")
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error deleting statement: {str(e)}', 'danger')
        logger.error(f"Error deleting statement {id}: {str(e)}", exc_info=True)
    
    return redirect(url_for('gmail.statements'))


@gmail_bp.route('/statements/<int:id>/reparse', methods=['POST'])
@login_required
def reparse_statement(id):
    """Delete existing transactions and re-parse statement"""
    statement = EmailStatement.query.get_or_404(id)
    
    if statement.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.statements'))
    
    try:
        # Delete existing transactions
        transaction_count = BankTransaction.query.filter_by(statement_id=statement.id).count()
        BankTransaction.query.filter_by(statement_id=statement.id).delete()
        db.session.commit()
        
        flash(f'✅ Cleared {transaction_count} existing transactions. Click "Parse PDF" to re-extract.', 'info')
        logger.info(f"User {current_user.id} cleared {transaction_count} transactions from statement {id}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error clearing transactions: {str(e)}', 'danger')
        logger.error(f"Error clearing transactions for statement {id}: {str(e)}", exc_info=True)
    
    return redirect(url_for('gmail.statement_detail', id=id))


# ============================================================================
# Transaction Routes
# ============================================================================

@gmail_bp.route('/transactions')
@login_required
def transactions():
    """List all transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    
    query = BankTransaction.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if request.args.get('uncategorized'):
        query = query.filter_by(category_id=None)
    
    if request.args.get('not_synced'):
        query = query.filter_by(erpnext_synced=False)
    
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    statement_id = request.args.get('statement_id', type=int)
    if statement_id:
        query = query.filter_by(statement_id=statement_id)
    
    # Order and paginate
    transactions = query.order_by(
        BankTransaction.date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get categories for filter dropdown
    categories = TransactionCategory.query.filter_by(active=True).all()
    
    return render_template('gmail/transactions.html', 
                         transactions=transactions,
                         categories=categories)


@gmail_bp.route('/transactions/<int:id>')
@login_required
def transaction_detail(id):
    """View transaction details"""
    transaction = BankTransaction.query.get_or_404(id)
    
    if transaction.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.transactions'))
    
    return render_template('gmail/transaction_detail.html', transaction=transaction)


@gmail_bp.route('/transactions/<int:id>/delete', methods=['POST'])
@login_required
def delete_transaction(id):
    """Delete a single transaction"""
    transaction = BankTransaction.query.get_or_404(id)
    
    if transaction.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.transactions'))
    
    # Check if transaction is synced to ERPNext
    if transaction.erpnext_synced:
        flash('⚠️ Cannot delete transaction that has been synced to ERPNext. Unsync it first.', 'warning')
        return redirect(url_for('gmail.transactions'))
    
    try:
        description_preview = transaction.description[:50]
        db.session.delete(transaction)
        db.session.commit()
        
        flash(f'✅ Transaction deleted: {description_preview}', 'success')
        logger.info(f"User {current_user.id} deleted transaction {id}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error deleting transaction: {str(e)}', 'danger')
        logger.error(f"Error deleting transaction {id}: {str(e)}", exc_info=True)
    
    return redirect(url_for('gmail.transactions'))


@gmail_bp.route('/transactions/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_transactions():
    """Delete multiple transactions"""
    transaction_ids = request.form.getlist('transaction_ids[]')
    
    if not transaction_ids:
        flash('No transactions selected', 'warning')
        return redirect(url_for('gmail.transactions'))
    
    try:
        # Convert to integers
        ids = [int(tid) for tid in transaction_ids]
        
        # Get transactions
        transactions = BankTransaction.query.filter(
            BankTransaction.id.in_(ids),
            BankTransaction.user_id == current_user.id
        ).all()
        
        # Check for synced transactions
        synced_count = sum(1 for t in transactions if t.erpnext_synced)
        if synced_count > 0:
            flash(f'⚠️ Cannot delete {synced_count} transactions that are synced to ERPNext', 'warning')
            return redirect(url_for('gmail.transactions'))
        
        # Delete transactions
        deleted_count = 0
        for transaction in transactions:
            db.session.delete(transaction)
            deleted_count += 1
        
        db.session.commit()
        
        flash(f'✅ Successfully deleted {deleted_count} transactions', 'success')
        logger.info(f"User {current_user.id} bulk deleted {deleted_count} transactions")
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error deleting transactions: {str(e)}', 'danger')
        logger.error(f"Error bulk deleting transactions: {str(e)}", exc_info=True)
    
    return redirect(url_for('gmail.transactions'))


# ============================================================================
# CSV Upload Routes
# ============================================================================

@gmail_bp.route('/upload-csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    """Upload and import CSV transactions"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'csv_file' not in request.files:
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file', 'warning')
            return redirect(request.url)
        
        try:
            # Read CSV data
            csv_data = file.read()
            
            # Get optional parameters
            bank_account = request.form.get('bank_account', '').strip()
            create_statement = request.form.get('create_statement') == 'on'
            
            # Parse CSV
            parser = CSVParser()
            transactions = parser.parse_csv(csv_data)
            
            if not transactions:
                flash('No valid transactions found in CSV file', 'warning')
                return redirect(request.url)
            
            # Create statement if requested
            statement_id = None
            if create_statement:
                statement = EmailStatement(
                    user_id=current_user.id,
                    gmail_id=f"CSV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                    subject=f"CSV Import: {secure_filename(file.filename)}",
                    sender='CSV Upload',
                    received_date=datetime.utcnow(),
                    bank_name='capitec',
                    is_processed=True,
                    has_pdf=False
                )
                db.session.add(statement)
                db.session.flush()
                statement_id = statement.id
            
            # Import ALL transactions without duplicate checking
            # Bank statements are authoritative - they don't contain duplicates
            imported_count = 0
            
            logger.info(f"Importing {len(transactions)} transactions from CSV (no duplicate filtering)")
            
            for trans_data in transactions:
                # Create transaction with proper field mapping
                transaction = BankTransaction(
                    user_id=current_user.id,
                    statement_id=statement_id,
                    date=trans_data['transaction_date'],
                    posting_date=trans_data['posting_date'],
                    description=trans_data['description'],
                    withdrawal=trans_data['debits'],
                    deposit=trans_data['credits'],
                    balance=trans_data['balance'],
                    reference_number=trans_data['reference']
                )
                db.session.add(transaction)
                imported_count += 1
            
            db.session.commit()
            
            logger.info(f"CSV import completed: {imported_count} transactions imported")
            flash(f'✅ Successfully imported {imported_count} transactions', 'success')
            return redirect(url_for('gmail.transactions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error importing CSV: {str(e)}', 'danger')
            logger.error(f"CSV import error: {str(e)}", exc_info=True)
            return redirect(request.url)
    
    return render_template('gmail/upload_csv.html')


@gmail_bp.route('/download-csv-template')
@login_required
def download_csv_template():
    """Download CSV template"""
    template = """Transaction Date,Posting Date,Description,Debits,Credits,Balance,Bank account
2025/09/23,2025/09/23,Sample Transaction,,1000.00,5000.00,5443 - Capitec Savings Account
2025/09/24,2025/09/24,Sample Payment,500.00,,4500.00,5443 - Capitec Savings Account"""
    
    response = make_response(template)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=transaction_template.csv'
    
    return response


@gmail_bp.route('/bulk-csv-import', methods=['GET', 'POST'])
@login_required
def bulk_csv_import():
    """Bulk import multiple CSV files"""
    if request.method == 'POST':
        files = request.files.getlist('csv_files')
        
        if not files:
            flash('No files selected', 'warning')
            return redirect(request.url)
        
        total_imported = 0
        files_processed = 0
        
        parser = CSVParser()
        
        for file in files:
            if not file.filename.endswith('.csv'):
                continue
            
            try:
                csv_data = file.read()
                transactions = parser.parse_csv(csv_data)
                
                # Create statement for this file
                statement = EmailStatement(
                    user_id=current_user.id,
                    gmail_id=f"CSV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{files_processed}",
                    subject=f"CSV Import: {secure_filename(file.filename)}",
                    sender='Bulk CSV Upload',
                    received_date=datetime.utcnow(),
                    bank_name='capitec',
                    is_processed=True,
                    has_pdf=False
                )
                db.session.add(statement)
                db.session.flush()
                
                # Import ALL transactions without duplicate checking
                imported = 0
                
                for trans_data in transactions:
                    transaction = BankTransaction(
                        user_id=current_user.id,
                        statement_id=statement.id,
                        date=trans_data['transaction_date'],
                        posting_date=trans_data['posting_date'],
                        description=trans_data['description'],
                        withdrawal=trans_data['debits'],
                        deposit=trans_data['credits'],
                        balance=trans_data['balance'],
                        reference_number=trans_data['reference']
                    )
                    db.session.add(transaction)
                    imported += 1
                
                total_imported += imported
                files_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                continue
        
        db.session.commit()
        
        logger.info(f"Bulk CSV import completed: {files_processed} files, {total_imported} transactions")
        flash(f'✅ Processed {files_processed} files: {total_imported} transactions imported', 'success')
        return redirect(url_for('gmail.transactions'))
    
    return render_template('gmail/bulk_csv_import.html')


# ============================================================================
# PDF Upload Routes
# ============================================================================

@gmail_bp.route('/upload-pdf', methods=['GET', 'POST'])
@login_required
def upload_pdf():
    """Upload and parse PDF statement manually"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'pdf_file' not in request.files:
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        file = request.files['pdf_file']
        
        if file.filename == '':
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        if not file.filename.lower().endswith('.pdf'):
            flash('Please upload a PDF file', 'warning')
            return redirect(request.url)
        
        try:
            # Get form data
            bank_name = request.form.get('bank_name', '').strip()
            statement_date_str = request.form.get('statement_date', '').strip()
            pdf_password = request.form.get('pdf_password', '').strip()
            save_password = request.form.get('save_password') == 'yes'
            auto_parse = request.form.get('auto_parse') == 'yes'
            
            if not bank_name:
                flash('Please select a bank', 'warning')
                return redirect(request.url)
            
            if not statement_date_str:
                flash('Please provide a statement date', 'warning')
                return redirect(request.url)
            
            # Parse date
            try:
                statement_date = datetime.strptime(statement_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format', 'warning')
                return redirect(request.url)
            
            # Save PDF temporarily
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            try:
                # Create statement record
                statement = EmailStatement(
                    user_id=current_user.id,
                    gmail_id=f"PDF-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                    subject=f"PDF Upload: {secure_filename(file.filename)}",
                    sender='Manual PDF Upload',
                    received_date=datetime.utcnow(),
                    statement_date=statement_date.date() if isinstance(statement_date, datetime) else statement_date,
                    bank_name=bank_name.lower(),
                    has_pdf=True,
                    is_processed=False,
                    state='draft'
                )
                
                # Save password if requested
                if pdf_password and save_password:
                    statement.pdf_password = pdf_password
                
                db.session.add(statement)
                db.session.flush()  # Get the statement ID
                
                # Auto-parse if requested
                if auto_parse:
                    from lsuite.gmail.parsers import PDFParser
                    from lsuite.gmail.parsers_capitec import CapitecPDFParser
                    
                    # Read PDF file
                    with open(temp_path, 'rb') as pdf_file:
                        pdf_data = pdf_file.read()
                    
                    # Use Capitec parser for Capitec statements
                    if bank_name.lower() == 'capitec':
                        parser = CapitecPDFParser()
                        result = parser.parse_pdf(
                            pdf_data=pdf_data,
                            password=pdf_password if pdf_password else None
                        )
                        transactions = result['transactions']
                        
                        # Log statement info
                        if result.get('statement_info'):
                            logger.info(f"Capitec Statement Info: {result['statement_info']}")
                    else:
                        parser = PDFParser()
                        transactions = parser.parse_pdf(
                            pdf_data=pdf_data,
                            bank_name=bank_name.lower(),
                            password=pdf_password if pdf_password else None
                        )
                    
                    if not transactions:
                        db.session.commit()
                        flash('⚠️ Statement uploaded but no transactions found. You may need to check the PDF format.', 'warning')
                        return redirect(url_for('gmail.statement_detail', id=statement.id))
                    
                    # Import ALL transactions without duplicate checking
                    # Bank statements are authoritative - they don't contain duplicates
                    imported_count = 0
                    
                    logger.info(f"Importing {len(transactions)} transactions from PDF (no duplicate filtering)")
                    
                    for trans_data in transactions:
                        # Convert parser format to database format
                        trans_date = trans_data.get('date')
                        description = trans_data.get('description', '')
                        amount = trans_data.get('amount', 0)
                        trans_type = trans_data.get('type', 'debit')
                        category = trans_data.get('category')
                        
                        # Determine deposit/withdrawal based on type
                        deposit = amount if trans_type == 'credit' else 0
                        withdrawal = amount if trans_type == 'debit' else 0
                        
                        # Map Capitec category to TransactionCategory
                        from lsuite.models import TransactionCategory
                        category_id = None
                        
                        if category:
                            # Try to find matching category by name (case-insensitive)
                            existing_category = TransactionCategory.query.filter(
                                db.func.lower(TransactionCategory.name) == category.lower()
                            ).first()
                            
                            if existing_category:
                                category_id = existing_category.id
                                logger.debug(f"Mapped '{category}' to existing category: {existing_category.name}")
                            else:
                                # Create new category for Capitec category
                                new_category = TransactionCategory(
                                    name=category,
                                    erpnext_account='',  # To be configured later
                                    transaction_type=trans_type,
                                    keywords='',
                                    active=True
                                )
                                db.session.add(new_category)
                                db.session.flush()
                                category_id = new_category.id
                                logger.info(f"Created new category: {category}")
                        
                        # Create transaction with category info
                        transaction = BankTransaction(
                            user_id=current_user.id,
                            statement_id=statement.id,
                            date=trans_date,
                            posting_date=trans_date,  # Use same date if posting_date not provided
                            description=description,
                            withdrawal=withdrawal,
                            deposit=deposit,
                            balance=trans_data.get('balance'),
                            reference_number=trans_data.get('reference', ''),
                            category_id=category_id,
                            notes=f"Capitec Category: {category}" if category else None
                        )
                        db.session.add(transaction)
                        imported_count += 1
                    
                    statement.is_processed = True
                    statement.state = 'parsed'
                    statement.transaction_count = imported_count
                    
                    db.session.commit()
                    
                    logger.info(f"PDF upload completed: {imported_count} transactions imported")
                    flash(f'✅ Successfully uploaded and parsed! {imported_count} transactions imported', 'success')
                else:
                    db.session.commit()
                    flash(f'✅ Statement uploaded successfully! You can parse it from the statement detail page.', 'success')
                
                return redirect(url_for('gmail.statement_detail', id=statement.id))
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except ValueError as e:
            db.session.rollback()
            error_msg = str(e)
            if 'password' in error_msg.lower():
                flash(f'❌ PDF is password protected. Please enter the correct password.', 'danger')
            else:
                flash(f'❌ Error parsing PDF: {error_msg}', 'danger')
            logger.error(f"PDF upload error: {error_msg}")
            return redirect(request.url)
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error uploading PDF: {str(e)}', 'danger')
            logger.error(f"PDF upload error: {str(e)}", exc_info=True)
            return redirect(request.url)
    
    return render_template('gmail/upload_pdf.html')
