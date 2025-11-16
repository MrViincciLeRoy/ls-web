# PDF Upload Duplicate Detection Fix

## Issues Fixed

### 1. ✅ Duplicate Detection Scoped to Same Statement
**Problem**: The system was checking for duplicates across ALL statements, causing legitimate transactions from different PDF statements to be incorrectly skipped as duplicates.

**Solution**: Modified duplicate detection to only check within the same `statement_id`, preventing false positives when uploading different PDF statements.

**Files Changed**:
- `lsuite/gmail/routes.py` - Updated `upload_pdf()` route duplicate checking logic

**Before**:
```python
# Checked duplicates across ALL user statements
existing = BankTransaction.query.filter_by(
    user_id=current_user.id,
    date=trans_date,
    description=description,
).filter(...).first()
```

**After**:
```python
# ✅ Checks duplicates ONLY within the same statement
existing = BankTransaction.query.filter_by(
    user_id=current_user.id,
    statement_id=statement.id,  # ← Added this
    date=trans_date,
    description=description,
).filter(...).first()
```

### 2. ✅ Disabled SQL Command Logging
**Problem**: `SQLALCHEMY_ECHO = True` was printing every SQL command to the console, flooding the logs and making debugging difficult.

**Solution**: Disabled SQL echo in development config and added SQLAlchemy engine logger configuration.

**Files Changed**:
- `config.py` - Changed `SQLALCHEMY_ECHO = False` in `DevelopmentConfig`
- `lsuite/__init__.py` - Added `logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)`

### 3. ✅ Implemented Proper Python Logging
**Problem**: Mix of print statements and inconsistent logging configuration made debugging difficult.

**Solution**: Implemented comprehensive Python logging with:
- Structured log format with timestamps
- Separate log levels for console and file
- Debug logs to `logs/lsuite_debug.log`
- Reduced werkzeug and SQLAlchemy noise
- Clear startup banner with configuration info

**Files Changed**:
- `lsuite/__init__.py` - Complete logging configuration rewrite
- `lsuite/gmail/routes.py` - Added proper logging statements

## Logging Configuration

### Log Format
```
YYYY-MM-DD HH:MM:SS | LEVEL    | logger_name | message
```

Example:
```
2025-11-16 10:30:45 | INFO     | lsuite.gmail.routes | Processing 42 transactions from PDF
2025-11-16 10:30:46 | DEBUG    | lsuite.gmail.routes | Skipped duplicate: Sample Transaction on 2025-09-23
2025-11-16 10:30:47 | INFO     | lsuite.gmail.routes | PDF upload completed: 42 imported, 0 duplicates
```

### Log Levels by Mode

**Development Mode** (DEBUG = True):
- Console: INFO and above
- File (`logs/lsuite_debug.log`): DEBUG and above
- Root logger: DEBUG

**Production Mode** (DEBUG = False):
- Console: WARNING and above
- File (`lsuite.log`): INFO and above (configurable via LOG_LEVEL env var)
- Root logger: INFO

### Reduced Noise Loggers
- `werkzeug`: WARNING only (no HTTP request logs in development)
- `sqlalchemy.engine`: WARNING only (no SQL commands unless debugging SQL issues)

## Testing the Fixes

### Test 1: Upload Same PDF Twice
1. Upload a PDF statement
2. Note the transaction count (e.g., "309 transactions imported")
3. Upload the SAME PDF again
4. Should see: "309 transactions imported (309 duplicates skipped)"
5. ✅ **Expected**: All transactions detected as duplicates within the same statement

### Test 2: Upload Different PDFs
1. Upload PDF statement for October 2025
2. Note transaction count (e.g., "150 transactions imported")
3. Upload PDF statement for November 2025
4. Note transaction count (e.g., "145 transactions imported")
5. ✅ **Expected**: Both sets of transactions imported, no false duplicates

### Test 3: Check Logs
1. Start the application
2. Look for startup banner:
```
============================================================
LSuite Application Starting
Mode: DEBUG
Database: SQLite (Offline)
============================================================
```
3. Upload a PDF
4. Check `logs/lsuite_debug.log` for detailed logging
5. ✅ **Expected**: Clear, structured logs; no SQL commands flooding console

### Test 4: Verify No SQL Echo
1. Start the application
2. Perform any database operation (login, view transactions, etc.)
3. Check console output
4. ✅ **Expected**: No SQL commands in console, only INFO/WARNING logs

## Log Files Location

- **Development Debug Log**: `LiquidSuite/logs/lsuite_debug.log`
- **Production Log**: `LiquidSuite/lsuite.log` (or path set in LOG_FILE env var)

**Note**: The `logs/` directory is created automatically if it doesn't exist.

## Environment Variables

Control logging via environment variables:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export LOG_LEVEL=DEBUG

# Set custom log file path
export LOG_FILE=/var/log/lsuite/app.log

# Enable offline mode (SQLite)
export OFFLINE_MODE=true
```

## Debugging Tips

### Enable SQL Logging Temporarily
If you need to see SQL commands for debugging:

**Option 1**: Edit `config.py`
```python
class DevelopmentConfig(Config):
    SQLALCHEMY_ECHO = True  # Temporarily enable
```

**Option 2**: Set SQLAlchemy logger level
```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### View Debug Logs
```bash
# Tail the debug log in real-time
tail -f logs/lsuite_debug.log

# Search for specific transactions
grep "Processing.*transactions" logs/lsuite_debug.log

# Search for duplicates
grep "duplicate" logs/lsuite_debug.log
```

### Common Log Patterns

**Successful PDF Upload**:
```
INFO     | lsuite.gmail.routes | Processing 42 transactions from PDF
DEBUG    | lsuite.gmail.routes | Skipped duplicate: Transaction 1 on 2025-09-23
DEBUG    | lsuite.gmail.routes | Skipped duplicate: Transaction 2 on 2025-09-23
INFO     | lsuite.gmail.routes | PDF upload completed: 40 imported, 2 duplicates
```

**Password Protected PDF**:
```
ERROR    | lsuite.gmail.routes | Password error for statement 123: PDF is password protected
```

**Parsing Error**:
```
ERROR    | lsuite.gmail.routes | PDF upload error: No valid transactions found in PDF file
```

## Summary

These fixes ensure that:
1. ✅ Different PDF statements don't have false duplicate detections
2. ✅ Console output is clean and readable
3. ✅ Detailed debugging information is available in log files
4. ✅ Production logs are appropriately filtered
5. ✅ Developers can easily track transaction processing

**All changes are backwards compatible** - existing functionality remains unchanged, only duplicate detection scope and logging have been improved.
