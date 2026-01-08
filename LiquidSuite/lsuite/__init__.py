"""
LSuite Application Factory - WITH AUTO DATABASE CHECKING
"""
import logging
from flask import Flask, render_template
from config import config
from lsuite.extensions import db, migrate, login_manager, cors


def create_app(config_name='default'):
    """Application factory pattern with database validation"""
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cors.init_app(app)
    
    # Configure logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Check database on startup (if not in migration mode)
    if not app.config.get('SKIP_DB_CHECK', False):
        check_database_startup(app)
    
    # Shell context for flask shell
    @app.shell_context_processor
    def make_shell_context():
        from lsuite import models
        from lsuite.utils.db_checker import DatabaseChecker, check_database, fix_database
        return {
            'db': db,
            'User': models.User,
            'BankTransaction': models.BankTransaction,
            'TransactionCategory': models.TransactionCategory,
            'UploadedDocument': models.UploadedDocument,
            'check_db': check_database,
            'fix_db': fix_database,
            'checker': DatabaseChecker,
        }
    
    return app


def register_blueprints(app):
    """Register Flask blueprints"""
    from lsuite.auth import auth_bp
    from lsuite.gmail import gmail_bp
    from lsuite.erpnext import erpnext_bp
    from lsuite.bridge import bridge_bp
    from lsuite.api import api_bp
    from lsuite.main import main_bp
    from lsuite.insights import insights_bp
    from lsuite.ai_insights import ai_insights_bp
    from lsuite.business_intel import bi_bp
    
    app.register_blueprint(bi_bp, url_prefix='/business-intel')
    app.register_blueprint(ai_insights_bp, url_prefix='/ai-insights')
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(gmail_bp, url_prefix='/gmail')
    app.register_blueprint(erpnext_bp, url_prefix='/erpnext')
    app.register_blueprint(bridge_bp, url_prefix='/bridge')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(insights_bp, url_prefix='/insights')


def register_error_handlers(app):
    """Register error handlers with better error messages"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Internal error: {error}")
        
        # Check if it's a database error
        error_str = str(error)
        if 'does not exist' in error_str or 'no such table' in error_str:
            app.logger.error("DATABASE ERROR DETECTED!")
            app.logger.error("Run: flask db-fix")
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403


def register_cli_commands(app):
    """Register custom CLI commands"""
    from lsuite.utils.db_checker import register_db_commands
    register_db_commands(app)


def check_database_startup(app):
    """Check database on application startup"""
    try:
        from lsuite.utils.startup_checker import check_database_on_startup
        check_database_on_startup(app)
    except Exception as e:
        app.logger.warning(f"Could not run startup database check: {e}")


def configure_logging(app):
    """Configure application logging with proper Python logging"""
    
    # Remove all existing handlers to prevent duplicates
    app.logger.handlers.clear()
    logging.getLogger('werkzeug').handlers.clear()
    
    # Define log format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler for all modes
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
    
    if app.debug or app.testing:
        # Development/Testing: INFO level to console, DEBUG to file
        console_handler.setLevel(logging.INFO)
        app.logger.setLevel(logging.DEBUG)
        
        # Also log to file in development
        import os
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.FileHandler('logs/lsuite_debug.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
    else:
        # Production: WARNING+ to console, INFO+ to file
        console_handler.setLevel(logging.WARNING)
        app.logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
    
    app.logger.addHandler(console_handler)
    
    # Configure root logger to catch all application logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Reduce werkzeug noise
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    # Reduce SQLAlchemy noise
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    app.logger.info('='*60)
    app.logger.info('LSuite Application Starting')
    app.logger.info(f"Mode: {'DEBUG' if app.debug else 'PRODUCTION'}")
    app.logger.info(f"Database: {'SQLite (Offline)' if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI'] else 'PostgreSQL (Online)'}")
    app.logger.info('='*60)
