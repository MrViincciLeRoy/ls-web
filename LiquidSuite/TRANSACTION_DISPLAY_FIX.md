✅ FIXED - All Transactions Showing Correct Debit/Credit

## Issues Fixed:

1. **Template using wrong field names** - was using `trans.amount` and `trans.transaction_type == 'debit'` but model has `withdrawal` and `deposit` fields
2. **Fixed transaction display** - now correctly shows:
   - Debit (red) when withdrawal > 0
   - Credit (green) when deposit > 0

## Changes Made:

**File**: `lsuite/templates/gmail/transactions.html`

**Before**:
```html
{% if trans.transaction_type == 'debit' %}
    <span class="badge bg-danger">Debit</span>
{% else %}
    <span class="badge bg-success">Credit</span>
{% endif %}
R{{ "%.2f"|format(trans.amount) }}
```

**After**:
```html
{% if trans.withdrawal and trans.withdrawal > 0 %}
    <span class="badge bg-danger">Debit</span>
{% else %}
    <span class="badge bg-success">Credit</span>
{% endif %}
R{{ "%.2f"|format(trans.withdrawal if trans.withdrawal else trans.deposit) }}
```

## Test It:
Refresh your transactions page - you should now see proper Debit/Credit badges and amounts!
