"""
Quick verification script for PDF/CSV upload fix
Verifies that duplicate checking has been REMOVED
"""
import os
import sys
from pathlib import Path

def check_file_changes():
    """Verify all necessary files have been updated"""
    
    print("="*60)
    print("PDF/CSV Upload Fix - Verification")
    print("NO DUPLICATE FILTERING (Import ALL transactions)")
    print("="*60)
    print()
    
    base_dir = Path(__file__).parent
    
    checks = [
        {
            'file': 'config.py',
            'check': 'SQLALCHEMY_ECHO = False',
            'not_check': 'SQLALCHEMY_ECHO = True',
            'description': 'SQL echo disabled in development config'
        },
        {
            'file': 'lsuite/__init__.py',
            'check': "logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)",
            'not_check': None,
            'description': 'SQLAlchemy logger configured to reduce noise'
        },
        {
            'file': 'lsuite/gmail/routes.py',
            'check': 'no duplicate filtering',
            'not_check': 'Check for duplicates',
            'description': 'Duplicate filtering removed from routes'
        },
        {
            'file': 'lsuite/gmail/routes.py',
            'check': 'Bank statements are authoritative',
            'not_check': None,
            'description': 'Comment explaining no duplicate checking'
        },
        {
            'file': 'logs/.gitignore',
            'check': '*.log',
            'not_check': None,
            'description': 'Logs directory gitignore created'
        }
    ]
    
    all_passed = True
    
    for i, check in enumerate(checks, 1):
        file_path = base_dir / check['file']
        
        print(f"{i}. Checking: {check['description']}")
        print(f"   File: {check['file']}")
        
        if not file_path.exists():
            print(f"   ❌ FAILED: File not found")
            all_passed = False
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required text
            if check['check'] in content:
                print(f"   ✅ PASSED: Found required text")
            else:
                print(f"   ❌ FAILED: Required text not found")
                print(f"   Looking for: {check['check'][:50]}...")
                all_passed = False
                continue
            
            # Check that old code is removed
            if check['not_check'] and check['not_check'] in content:
                print(f"   ⚠️  WARNING: Old code still present!")
                print(f"   Found: {check['not_check'][:50]}...")
                print(f"   (Should be removed)")
                all_passed = False
            
        except Exception as e:
            print(f"   ❌ FAILED: Error reading file - {e}")
            all_passed = False
        
        print()
    
    # Check if logs directory exists
    print(f"{len(checks)+1}. Checking: Logs directory created")
    logs_dir = base_dir / 'logs'
    if logs_dir.exists() and logs_dir.is_dir():
        print(f"   ✅ PASSED: {logs_dir}")
    else:
        print(f"   ❌ FAILED: Logs directory not found")
        all_passed = False
    
    print()
    print("="*60)
    
    if all_passed:
        print("✅ All checks PASSED!")
        print()
        print("What changed:")
        print("• Duplicate filtering REMOVED (imports ALL transactions)")
        print("• SQL logging disabled (clean console)")
        print("• Proper Python logging (logs/lsuite_debug.log)")
        print()
        print("Next steps:")
        print("1. Start the application: python app.py")
        print("2. Upload a PDF - ALL transactions will be imported")
        print("3. Check logs/lsuite_debug.log for details")
        print("4. No SQL commands in console ✅")
        print()
        print("Important:")
        print("• Upload same PDF twice = imports ALL twice (618 trans)")
        print("• This is CORRECT - bank statements are authoritative")
        print("• Delete duplicate statements manually if needed")
    else:
        print("❌ Some checks FAILED!")
        print()
        print("Please review the errors above and ensure all files")
        print("have been properly updated.")
    
    print("="*60)
    
    return all_passed


if __name__ == '__main__':
    success = check_file_changes()
    sys.exit(0 if success else 1)
