# LiquidSuite Emergency Fixes & Utilities

This folder contains quick-fix tools and utilities for common LiquidSuite issues.

---

## 🚀 QUICK START - Choose Your Launcher

### 🌟 Recommended: Smart Launcher
**Double-click: `START_LIQUIDSUITE.bat`**
- Auto-detects if PostgreSQL is available
- Uses PostgreSQL if running (ONLINE mode)
- Falls back to SQLite if not (OFFLINE mode)
- Perfect for beginners!

### 🔵 Offline Mode (SQLite - No PostgreSQL Needed)
**Double-click: `RUN_OFFLINE.bat`**
- Perfect for development/testing
- No database server required
- Works immediately
- Database: `data/lsuite.db`

### 🟢 Online Mode (PostgreSQL Required)
**Double-click: `RUN_ONLINE.bat`**
- Checks PostgreSQL is running first
- Better for production
- Requires PostgreSQL server

---

## 🔧 Available Tools

### 1. Database Mode Switching

| File | Purpose | When to Use |
|------|---------|-------------|
| `START_LIQUIDSUITE.bat` | Smart launcher | Always - it auto-detects! |
| `RUN_OFFLINE.bat` | Force offline mode | No PostgreSQL available |
| `RUN_ONLINE.bat` | Force online mode | PostgreSQL is running |
| `START_POSTGRES.bat` | Start PostgreSQL | Need to start database |

**See:** `OFFLINE_ONLINE_GUIDE.txt` for detailed instructions

---

### 2. Bank Account ID Fix

**Problem:** Statement failed to parse - "null value in bank_account_id violates not-null constraint"

**Files:**
- `RUN_FIX.bat` - One-click fix
- `fix_bank_account_constraint.py` - Python script version

**Quick Fix:**
```bash
# Double-click:
RUN_FIX.bat

# Or run manually:
python fix_bank_account_constraint.py
```

**What it does:**
1. Drops NOT NULL constraint on bank_account_id
2. Finds transactions with NULL bank_account_id
3. Creates missing bank accounts
4. Links transactions to accounts
5. Verifies everything is fixed

**See:** `QUICK_REFERENCE.txt` for details

---

## 📚 Documentation Files

| File | Contents |
|------|----------|
| `README.md` | This file - overview of all tools |
| `OFFLINE_ONLINE_GUIDE.txt` | Complete guide to database modes |
| `QUICK_REFERENCE.txt` | Quick reference for bank account fix |

---

## 🆘 Common Issues & Solutions

### Issue 1: "Connection refused" Error

**Cause:** PostgreSQL not running (trying ONLINE mode)

**Solution A - Use Offline Mode (Easiest):**
```bash
# Double-click:
RUN_OFFLINE.bat
```

**Solution B - Start PostgreSQL:**
```bash
# Double-click (as Administrator):
START_POSTGRES.bat

# Then use:
RUN_ONLINE.bat
```

---

### Issue 2: Statement Won't Parse (298 transactions failed)

**Cause:** Bank account ID missing from transactions

**Solution:**
```bash
# Double-click:
RUN_FIX.bat

# Then try parsing the statement again
```

---

### Issue 3: Don't Know Which Mode to Use

**Solution:**
```bash
# Use the smart launcher:
START_LIQUIDSUITE.bat

# It will auto-detect and choose for you!
```

---

### Issue 4: PostgreSQL Not Installed

**Solution A - Use Offline Mode:**
```bash
# No PostgreSQL needed:
RUN_OFFLINE.bat
```

**Solution B - Install PostgreSQL:**
1. Download: https://www.postgresql.org/download/windows/
2. Install with defaults
3. Remember postgres password
4. Use: `RUN_ONLINE.bat`

---

## 🎯 Which Tool Should I Use?

### For First Time Users:
→ **`START_LIQUIDSUITE.bat`** (smart launcher)

### For Development:
→ **`RUN_OFFLINE.bat`** (SQLite, no setup)

### For Production:
→ **`RUN_ONLINE.bat`** (PostgreSQL, better performance)

### PostgreSQL Not Starting:
→ **`START_POSTGRES.bat`** (start database)

### Statement Parse Error:
→ **`RUN_FIX.bat`** (fix bank account IDs)

### Need Help Deciding:
→ **Read: `OFFLINE_ONLINE_GUIDE.txt`**

---

## ✅ Success Checklist

### First Time Setup:
- [ ] Decided on OFFLINE or ONLINE mode
- [ ] Used appropriate launcher
- [ ] LiquidSuite started successfully
- [ ] Can access http://localhost:5000
- [ ] No error messages in console

### OFFLINE Mode Checklist:
- [ ] Used `RUN_OFFLINE.bat` or `START_LIQUIDSUITE.bat`
- [ ] See "🔵 OFFLINE MODE" in console
- [ ] Database file created at `data/lsuite.db`
- [ ] Application running smoothly

### ONLINE Mode Checklist:
- [ ] PostgreSQL is installed
- [ ] PostgreSQL service is running
- [ ] Database 'lsuite' exists
- [ ] .env has correct DATABASE_URL
- [ ] Used `RUN_ONLINE.bat`
- [ ] See "🟢 ONLINE MODE" in console
- [ ] Application running smoothly

### Bank Account Fix Checklist:
- [ ] Ran `RUN_FIX.bat`
- [ ] Script completed without errors
- [ ] Reported "Successfully fixed X transactions"
- [ ] Statement now parses successfully
- [ ] All transactions visible

---

## 📞 Still Having Issues?

1. **Check the guides:**
   - `OFFLINE_ONLINE_GUIDE.txt` - Database modes
   - `QUICK_REFERENCE.txt` - Bank account fix

2. **Try the smart launcher:**
   - `START_LIQUIDSUITE.bat` - Handles most cases

3. **Use offline mode:**
   - `RUN_OFFLINE.bat` - Works without PostgreSQL

4. **Check console output:**
   - Look for error messages
   - Note which mode it's using
   - Check database connection status

5. **Common fixes:**
   - PostgreSQL issue → Use `RUN_OFFLINE.bat`
   - Parse error → Use `RUN_FIX.bat`
   - Don't know what to do → Use `START_LIQUIDSUITE.bat`

---

## 🔄 Quick Command Reference

```bash
# Start in best available mode
START_LIQUIDSUITE.bat

# Force offline mode (SQLite)
RUN_OFFLINE.bat

# Force online mode (PostgreSQL)
RUN_ONLINE.bat

# Start PostgreSQL
START_POSTGRES.bat (as Administrator)

# Fix bank account issues
RUN_FIX.bat

# Check PostgreSQL status
psql -U postgres -c "SELECT 1;"

# Create database
psql -U postgres -c "CREATE DATABASE lsuite;"
```

---

## 📊 Feature Matrix

| Feature | OFFLINE (SQLite) | ONLINE (PostgreSQL) |
|---------|-----------------|---------------------|
| Setup Time | ⚡ Instant | 🕐 5-10 min |
| PostgreSQL Required | ❌ No | ✅ Yes |
| Best For | Development | Production |
| Concurrent Users | 1-2 | 100+ |
| Data Size | Small-Medium | Any size |
| Performance | Good | Excellent |
| Launcher | RUN_OFFLINE.bat | RUN_ONLINE.bat |

---

## 📝 File Tree

```
emergency_fixes/
├── START_LIQUIDSUITE.bat      ← 🌟 Smart launcher (use this!)
├── RUN_OFFLINE.bat            ← 🔵 Offline mode
├── RUN_ONLINE.bat             ← 🟢 Online mode
├── START_POSTGRES.bat         ← Start PostgreSQL
├── RUN_FIX.bat                ← Fix bank account IDs
├── fix_bank_account_constraint.py  ← Fix script
├── README.md                  ← This file
├── OFFLINE_ONLINE_GUIDE.txt   ← Detailed mode guide
└── QUICK_REFERENCE.txt        ← Bank account fix guide
```

---

## 💡 Pro Tips

1. **First time?** → Use `START_LIQUIDSUITE.bat`
2. **PostgreSQL issues?** → Use `RUN_OFFLINE.bat`
3. **Parse errors?** → Use `RUN_FIX.bat`
4. **Not sure?** → Read `OFFLINE_ONLINE_GUIDE.txt`
5. **Quick reference?** → Open `QUICK_REFERENCE.txt`

---

*Last Updated: 2025-11-16*  
*LiquidSuite Version: Latest*  
*Emergency Fixes v2.0 - Now with Offline/Online Mode Support!*
