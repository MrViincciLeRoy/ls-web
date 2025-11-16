"""
TEST: Verify no duplicate filtering exists
"""
import sys
from pathlib import Path

base = Path(__file__).parent

# Check routes.py for duplicate checking code
routes_file = base / 'lsuite' / 'gmail' / 'routes.py'
with open(routes_file, 'r', encoding='utf-8') as f:
    content = f.read()

# These should NOT exist
bad_patterns = [
    'Check for duplicates',
    'existing = BankTransaction.query',
    'skipped_count',
    'duplicates skipped'
]

# These SHOULD exist
good_patterns = [
    'no duplicate filtering',
    'Bank statements are authoritative'
]

print("Checking routes.py...")
errors = []

for pattern in bad_patterns:
    if pattern in content:
        errors.append(f"❌ Found old code: '{pattern}'")

for pattern in good_patterns:
    if pattern not in content:
        errors.append(f"❌ Missing new code: '{pattern}'")

# Check config.py
config_file = base / 'config.py'
with open(config_file, 'r', encoding='utf-8') as f:
    config = f.read()

if 'SQLALCHEMY_ECHO = True' in config:
    errors.append("❌ SQL echo still enabled in config")
elif 'SQLALCHEMY_ECHO = False' not in config:
    errors.append("❌ SQL echo not disabled in config")

if errors:
    print("\n".join(errors))
    sys.exit(1)
else:
    print("✅ ALL CHECKS PASSED")
    print("✅ No duplicate filtering code found")
    print("✅ SQL echo disabled")
    print("✅ Ready to import ALL transactions!")
    sys.exit(0)
