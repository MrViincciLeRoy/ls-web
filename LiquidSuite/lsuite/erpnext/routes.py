# ============================================================================
# LiquidSuite/lsuite/erpnext/routes.py - FIXED WITHOUT CELERY
# ============================================================================
"""
ERPNext Routes - Configuration and Sync Management
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from lsuite.extensions import db
from lsuite.models import ERPNextConfig, ERPNextSyncLog, BankTransaction
from lsuite.erpnext.services import ERPNextService
from lsuite.erpnext import erpnext_bp


@erpnext_bp.route('/configs')
@login_required
def configs():
    """List ERPNext configurations"""
    configs = ERPNextConfig.query.filter_by(user_id=current_user.id).all()
    return render_template('erpnext/configs.html', configs=configs)


@erpnext_bp.route('/configs/new', methods=['GET', 'POST'])
@login_required
def new_config():
    """Create new ERPNext configuration"""
    if request.method == 'POST':
        # Check if this should be active
        is_active = request.form.get('is_active') == 'true'
        if is_active:
            # Deactivate all other configs for this user
            ERPNextConfig.query.filter_by(user_id=current_user.id).update({'is_active': False})
        
        config = ERPNextConfig(
            user_id=current_user.id,
            name=request.form['name'],
            base_url=request.form['base_url'],
            api_key=request.form['api_key'],
            api_secret=request.form['api_secret'],
            default_company=request.form.get('default_company', ''),
            bank_account=request.form.get('bank_account', ''),
            default_cost_center=request.form.get('default_cost_center', ''),
            is_active=is_active
        )
        
        # Test connection
        service = ERPNextService(config)
        success, message = service.test_connection()
        
        if not success:
            flash(f'Connection test failed: {message}', 'danger')
            return render_template('erpnext/config_form.html', config=config)
        
        db.session.add(config)
        db.session.commit()
        
        flash(f'Configuration created successfully! {message}', 'success')
        return redirect(url_for('erpnext.configs'))
    
    return render_template('erpnext/config_form.html')


@erpnext_bp.route('/configs/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_config(id):
    """Edit ERPNext configuration"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('erpnext.configs'))
    
    if request.method == 'POST':
        config.name = request.form['name']
        config.base_url = request.form['base_url']
        config.api_key = request.form['api_key']
        config.api_secret = request.form['api_secret']
        config.default_company = request.form.get('default_company', '')
        config.bank_account = request.form.get('bank_account', '')
        config.default_cost_center = request.form.get('default_cost_center', '')
        
        # Handle active status
        is_active = request.form.get('is_active') == 'true'
        if is_active:
            # Deactivate all other configs for this user
            ERPNextConfig.query.filter_by(user_id=current_user.id).update({'is_active': False})
        config.is_active = is_active
        
        # Test connection
        service = ERPNextService(config)
        success, message = service.test_connection()
        
        if not success:
            flash(f'Connection test failed: {message}', 'warning')
        
        db.session.commit()
        
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('erpnext.configs'))
    
    return render_template('erpnext/config_form.html', config=config)


@erpnext_bp.route('/configs/<int:id>/test', methods=['POST'])
@login_required
def test_config(id):
    """Test ERPNext connection"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    service = ERPNextService(config)
    success, message = service.test_connection()
    
    return jsonify({'success': success, 'message': message})


@erpnext_bp.route('/configs/<int:id>/delete', methods=['POST'])
@login_required
def delete_config(id):
    """Delete ERPNext configuration"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('erpnext.configs'))
    
    db.session.delete(config)
    db.session.commit()
    
    flash('Configuration deleted successfully!', 'success')
    return redirect(url_for('erpnext.configs'))


@erpnext_bp.route('/configs/<int:id>/activate', methods=['POST'])
@login_required
def activate_config(id):
    """Set configuration as active"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('erpnext.configs'))
    
    # Deactivate all other configs
    ERPNextConfig.query.filter_by(user_id=current_user.id).update({'is_active': False})
    
    # Activate this config
    config.is_active = True
    db.session.commit()
    
    flash(f'"{config.name}" is now the active configuration', 'success')
    return redirect(url_for('erpnext.configs'))


@erpnext_bp.route('/sync-logs')
@login_required
def sync_logs():
    """View sync logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = ERPNextSyncLog.query.join(ERPNextConfig).filter(
        ERPNextConfig.user_id == current_user.id
    ).order_by(
        ERPNextSyncLog.sync_date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('erpnext/sync_logs.html', logs=logs)


@erpnext_bp.route('/transactions/<int:id>/sync', methods=['POST'])
@login_required
def sync_transaction(id):
    """Sync single transaction to ERPNext (async with threading)"""
    from lsuite.tasks_simple import run_task_async, sync_transaction_to_erpnext
    from lsuite.models import IncomingTransaction
    
    transaction = BankTransaction.query.get_or_404(id)
    
    if transaction.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if not transaction.category_id:
        return jsonify({'success': False, 'message': 'Transaction must be categorized first'}), 400
    
    config = ERPNextConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'No active ERPNext configuration'}), 400
    
    try:
        # Queue task for background processing
        task_id = run_task_async(
            sync_transaction_to_erpnext,
            id,
            current_user.id
        )
        
        # Create incoming transaction log
        incoming = IncomingTransaction(
            user_id=current_user.id,
            transaction_id=transaction.id,
            transaction_type='erpnext_sync',
            status='pending',
            task_id=task_id,
            request_data={
                'transaction_id': id,
                'category': transaction.category.name if transaction.category else None
            }
        )
        db.session.add(incoming)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sync started in background - check status below',
            'task_id': task_id,
            'status_url': url_for('erpnext.task_status', task_id=task_id)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to queue sync: {str(e)}'
        }), 500


@erpnext_bp.route('/fetch-accounts')
@login_required
def fetch_accounts():
    """Fetch chart of accounts from ERPNext"""
    config = ERPNextConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'No active ERPNext configuration'}), 400
    
    try:
        service = ERPNextService(config)
        accounts = service.get_chart_of_accounts()
        
        return jsonify({
            'success': True,
            'accounts': accounts
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@erpnext_bp.route('/fetch-cost-centers')
@login_required
def fetch_cost_centers():
    """Fetch cost centers from ERPNext"""
    config = ERPNextConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'No active ERPNext configuration'}), 400
    
    try:
        service = ERPNextService(config)
        cost_centers = service.get_cost_centers()
        
        return jsonify({
            'success': True,
            'cost_centers': cost_centers
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@erpnext_bp.route('/transactions/sync-bulk', methods=['POST'])
@login_required
def sync_bulk_transactions():
    """Sync multiple transactions to ERPNext (async with threading)"""
    from lsuite.tasks_simple import run_task_async, sync_bulk_transactions_to_erpnext
    from lsuite.models import IncomingTransaction
    
    data = request.get_json()
    transaction_ids = data.get('transaction_ids', [])
    
    if not transaction_ids:
        return jsonify({'success': False, 'message': 'No transactions selected'}), 400
    
    config = ERPNextConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'No active ERPNext configuration'}), 400
    
    try:
        # Queue task for background processing
        task_id = run_task_async(
            sync_bulk_transactions_to_erpnext,
            transaction_ids,
            current_user.id
        )
        
        # Create incoming transaction log for bulk operation
        incoming = IncomingTransaction(
            user_id=current_user.id,
            transaction_type='erpnext_bulk_sync',
            status='pending',
            task_id=task_id,
            request_data={
                'transaction_ids': transaction_ids,
                'count': len(transaction_ids)
            }
        )
        db.session.add(incoming)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Queued {len(transaction_ids)} transactions for sync',
            'task_id': task_id,
            'status_url': url_for('erpnext.task_status', task_id=task_id)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to queue bulk sync: {str(e)}'
        }), 500


@erpnext_bp.route('/tasks/<task_id>/status')
@login_required
def task_status(task_id):
    """Check status of a background task"""
    from lsuite.tasks_simple import get_task_status
    from lsuite.models import IncomingTransaction
    
    # Get task status
    task = get_task_status(task_id)
    
    # Get incoming transaction log
    incoming = IncomingTransaction.query.filter_by(task_id=task_id).first()
    
    response = {
        'task_id': task_id,
        'state': task['state'],
        'ready': task['state'] in ['SUCCESS', 'FAILURE'],
    }
    
    if task['state'] == 'PENDING':
        response['status'] = 'pending'
        response['message'] = 'Task is waiting to be processed'
    elif task['state'] == 'PROCESSING':
        response['status'] = 'processing'
        if task['info']:
            response['progress'] = task['info']
    elif task['state'] == 'SUCCESS':
        response['status'] = 'success'
        response['result'] = task['info']
        if incoming:
            response['incoming_log'] = {
                'id': incoming.id,
                'created_at': incoming.created_at.isoformat(),
                'completed_at': incoming.completed_at.isoformat() if incoming.completed_at else None
            }
    elif task['state'] == 'FAILURE':
        response['status'] = 'failed'
        response['error'] = str(task['info'])
    else:
        response['status'] = task['state'].lower()
    
    return jsonify(response)


@erpnext_bp.route('/incoming-logs')
@login_required
def incoming_logs():
    """View incoming transaction logs"""
    from lsuite.models import IncomingTransaction
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = IncomingTransaction.query.filter_by(
        user_id=current_user.id
    ).order_by(
        IncomingTransaction.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('erpnext/incoming_logs.html', logs=logs)
