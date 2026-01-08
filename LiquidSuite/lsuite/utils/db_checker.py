"""
Database Checker & Auto-Migration Tool
Location: lsuite/utils/db_checker.py

Run: flask db-check
     flask db-fix
"""
import logging
from sqlalchemy import inspect, text
from flask import current_app
from lsuite.extensions import db
import subprocess
import sys

logger = logging.getLogger(__name__)


class DatabaseChecker:
    """Check database schema against models and auto-fix issues"""
    
    def __init__(self):
        self.inspector = inspect(db.engine)
        self.issues = []
        self.missing_tables = []
        self.missing_columns = {}
        
    def get_all_models(self):
        """Get all SQLAlchemy models"""
        models = {}
        for mapper in db.Model.registry.mappers:
            model = mapper.class_
            if hasattr(model, '__tablename__'):
                models[model.__tablename__] = model
        return models
    
    def check_tables(self):
        """Check if all model tables exist in database"""
        models = self.get_all_models()
        existing_tables = set(self.inspector.get_table_names())
        
        logger.info(f"Found {len(existing_tables)} tables in database")
        logger.info(f"Found {len(models)} models in application")
        
        for table_name, model in models.items():
            if table_name not in existing_tables:
                self.missing_tables.append(table_name)
                self.issues.append(f"❌ Missing table: {table_name}")
                logger.warning(f"Missing table: {table_name}")
            else:
                logger.info(f"✓ Table exists: {table_name}")
        
        return len(self.missing_tables) == 0
    
    def check_columns(self):
        """Check if all model columns exist in database tables"""
        models = self.get_all_models()
        existing_tables = set(self.inspector.get_table_names())
        
        for table_name, model in models.items():
            if table_name not in existing_tables:
                continue
            
            # Get existing columns
            existing_columns = {col['name'] for col in self.inspector.get_columns(table_name)}
            
            # Get model columns
            model_columns = {col.name for col in model.__table__.columns}
            
            # Find missing columns
            missing = model_columns - existing_columns
            if missing:
                self.missing_columns[table_name] = missing
                for col in missing:
                    self.issues.append(f"❌ Missing column: {table_name}.{col}")
                    logger.warning(f"Missing column: {table_name}.{col}")
        
        return len(self.missing_columns) == 0
    
    def check_relationships(self):
        """Check foreign key constraints"""
        models = self.get_all_models()
        issues = []
        
        for table_name in self.inspector.get_table_names():
            fks = self.inspector.get_foreign_keys(table_name)
            for fk in fks:
                ref_table = fk['referred_table']
                if ref_table not in self.inspector.get_table_names():
                    issue = f"❌ Foreign key references missing table: {table_name} -> {ref_table}"
                    issues.append(issue)
                    self.issues.append(issue)
                    logger.warning(issue)
        
        return len(issues) == 0
    
    def full_check(self):
        """Run all checks"""
        logger.info("="*60)
        logger.info("DATABASE SCHEMA VALIDATION")
        logger.info("="*60)
        
        tables_ok = self.check_tables()
        columns_ok = self.check_columns()
        relationships_ok = self.check_relationships()
        
        all_ok = tables_ok and columns_ok and relationships_ok
        
        logger.info("="*60)
        if all_ok:
            logger.info("✓ DATABASE SCHEMA IS VALID")
        else:
            logger.error("✗ DATABASE SCHEMA HAS ISSUES")
            logger.error(f"Found {len(self.issues)} issues:")
            for issue in self.issues:
                logger.error(f"  {issue}")
        logger.info("="*60)
        
        return all_ok, self.issues
    
    def generate_report(self):
        """Generate detailed report"""
        report = []
        report.append("\n" + "="*60)
        report.append("DATABASE SCHEMA REPORT")
        report.append("="*60)
        
        models = self.get_all_models()
        existing_tables = set(self.inspector.get_table_names())
        
        report.append(f"\nModels defined: {len(models)}")
        report.append(f"Tables in database: {len(existing_tables)}")
        
        if self.missing_tables:
            report.append(f"\n❌ MISSING TABLES ({len(self.missing_tables)}):")
            for table in self.missing_tables:
                report.append(f"  - {table}")
        
        if self.missing_columns:
            report.append(f"\n❌ MISSING COLUMNS:")
            for table, columns in self.missing_columns.items():
                report.append(f"  {table}:")
                for col in columns:
                    report.append(f"    - {col}")
        
        if not self.missing_tables and not self.missing_columns:
            report.append("\n✓ All tables and columns present")
        
        report.append("="*60 + "\n")
        
        return "\n".join(report)
    
    def auto_fix(self):
        """Automatically fix database issues"""
        logger.info("="*60)
        logger.info("AUTO-FIX DATABASE SCHEMA")
        logger.info("="*60)
        
        try:
            # Check current state
            all_ok, issues = self.full_check()
            
            if all_ok:
                logger.info("✓ No issues to fix")
                return True
            
            logger.info(f"Found {len(issues)} issues. Attempting auto-fix...")
            
            # Run migrations
            logger.info("\n1. Creating migration...")
            result = self._run_flask_command(['db', 'migrate', '-m', 'Auto-generated migration'])
            
            if result.returncode != 0:
                logger.error("Migration creation failed")
                logger.error(result.stderr)
                return False
            
            logger.info("✓ Migration created successfully")
            
            logger.info("\n2. Applying migration...")
            result = self._run_flask_command(['db', 'upgrade'])
            
            if result.returncode != 0:
                logger.error("Migration application failed")
                logger.error(result.stderr)
                return False
            
            logger.info("✓ Migration applied successfully")
            
            # Re-check
            logger.info("\n3. Verifying fix...")
            self.issues = []
            self.missing_tables = []
            self.missing_columns = {}
            
            all_ok, remaining_issues = self.full_check()
            
            if all_ok:
                logger.info("✓ ALL ISSUES FIXED!")
                return True
            else:
                logger.warning(f"⚠ {len(remaining_issues)} issues remain:")
                for issue in remaining_issues:
                    logger.warning(f"  {issue}")
                return False
            
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
            return False
    
    def _run_flask_command(self, args):
        """Run flask command"""
        cmd = [sys.executable, '-m', 'flask'] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=current_app.root_path
        )
    
    def check_specific_tables(self, table_names):
        """Check specific tables"""
        existing_tables = set(self.inspector.get_table_names())
        results = {}
        
        for table in table_names:
            exists = table in existing_tables
            results[table] = {
                'exists': exists,
                'columns': None
            }
            
            if exists:
                columns = self.inspector.get_columns(table)
                results[table]['columns'] = [col['name'] for col in columns]
        
        return results


def check_database():
    """Quick database check"""
    checker = DatabaseChecker()
    all_ok, issues = checker.full_check()
    
    if not all_ok:
        print("\n" + checker.generate_report())
        print("\n💡 Run 'flask db-fix' to automatically fix issues")
    
    return all_ok


def fix_database():
    """Auto-fix database issues"""
    checker = DatabaseChecker()
    success = checker.auto_fix()
    
    if success:
        print("\n✓ Database schema fixed successfully!")
    else:
        print("\n✗ Could not fix all issues automatically")
        print("Please check the logs and run migrations manually:")
        print("  flask db migrate -m 'Manual migration'")
        print("  flask db upgrade")
    
    return success


def validate_business_intel_tables():
    """Validate Business Intelligence tables specifically"""
    required_tables = [
        'uploaded_documents',
        'document_transactions',
        'cash_flow_forecasts',
        'business_statements'
    ]
    
    checker = DatabaseChecker()
    results = checker.check_specific_tables(required_tables)
    
    print("\n" + "="*60)
    print("BUSINESS INTELLIGENCE TABLES CHECK")
    print("="*60)
    
    all_ok = True
    for table, info in results.items():
        if info['exists']:
            print(f"✓ {table}")
            if info['columns']:
                print(f"  Columns: {len(info['columns'])}")
        else:
            print(f"❌ {table} - MISSING")
            all_ok = False
    
    print("="*60)
    
    if not all_ok:
        print("\n💡 Missing tables detected. Run 'flask db-fix' to create them.")
    
    return all_ok


# Flask CLI commands
def register_db_commands(app):
    """Register database check commands with Flask CLI"""
    
    @app.cli.command('db-check')
    def db_check_command():
        """Check database schema against models"""
        with app.app_context():
            check_database()
    
    @app.cli.command('db-fix')
    def db_fix_command():
        """Auto-fix database schema issues"""
        with app.app_context():
            fix_database()
    
    @app.cli.command('db-check-bi')
    def db_check_bi_command():
        """Check Business Intelligence tables"""
        with app.app_context():
            validate_business_intel_tables()
    
    @app.cli.command('db-report')
    def db_report_command():
        """Generate detailed database report"""
        with app.app_context():
            checker = DatabaseChecker()
            checker.full_check()
            print(checker.generate_report())
