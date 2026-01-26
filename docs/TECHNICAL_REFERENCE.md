# PO Finalization Tool - Technical Reference

This document provides detailed technical information about how the PO finalization tool works, including database schema, SQL queries, and troubleshooting.

---

## Table of Contents

1. [Database Schema](#database-schema)
2. [How Finalization Works](#how-finalization-works)
3. [The Query Logic](#the-query-logic)
4. [Step-by-Step Process](#step-by-step-process)
5. [Important Notes](#important-notes)
6. [Troubleshooting](#troubleshooting)
7. [Scripts Reference](#scripts-reference)

---

## Database Schema

Three tables are involved in the finalization process:

### Table: `inventoryitems`

Stores all inventory records, including "on-order" placeholders.

| Column | Type | Description |
|--------|------|-------------|
| `ItemID` | bigint | Primary key |
| `Quantity` | decimal | Amount in inventory (0 for placeholders after receiving) |
| `OnOrder` | tinyint | 1 = on-order placeholder, 0 = real inventory |

### Table: `purchaseorderitems`

Individual line items on Purchase Orders.

| Column | Type | Description |
|--------|------|-------------|
| `PurchaseOrderItemID` | bigint | Primary key |
| `PurchaseOrderID` | bigint | FK to purchaseorders |
| `OnOrderInventoryItemID` | bigint | FK to inventoryitems (NULL when finalized) |
| `Finalized` | tinyint | NULL or 0 = not finalized, 1 = finalized |
| `Quantity` | decimal | Quantity ordered |
| `QuantityReceived` | decimal | Quantity actually received |

### Table: `purchaseorders`

Purchase Order header records.

| Column | Type | Description |
|--------|------|-------------|
| `PurchaseOrderID` | bigint | Primary key |
| `PONumber` | varchar | Human-readable PO number |
| `NumberOfFinalizedItems` | bigint | Counter of finalized line items |

### Relationship Diagram

```
┌─────────────────────────┐
│    purchaseorders       │
│  (PurchaseOrderID)      │
│  PONumber               │
│  NumberOfFinalizedItems │
└───────────┬─────────────┘
            │ 1:many
            ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│  purchaseorderitems     │         │    inventoryitems       │
│  (PurchaseOrderItemID)  │────────▶│    (ItemID)             │
│  PurchaseOrderID (FK)   │   FK    │    Quantity             │
│  OnOrderInventoryItemID │ ──────▶ │    OnOrder              │
│  Finalized              │         └─────────────────────────┘
│  Quantity               │
│  QuantityReceived       │
└─────────────────────────┘

The OnOrderInventoryItemID links a PO item to its placeholder in inventory.
When finalized, this link is set to NULL and the inventory item is deleted.
```

---

## How Finalization Works

### The Lifecycle of a PO Item

```
1. PO CREATED
   ┌─────────────────┐      ┌─────────────────┐
   │ PO Item         │      │ Inventory Item  │
   │ Finalized: NULL │─────▶│ Quantity: 10    │
   │ OnOrderInvID: X │      │ OnOrder: 1      │
   └─────────────────┘      └─────────────────┘

2. MATERIALS RECEIVED
   ┌─────────────────┐      ┌─────────────────┐
   │ PO Item         │      │ Inventory Item  │
   │ Finalized: NULL │─────▶│ Quantity: 0     │  ← Qty becomes 0
   │ OnOrderInvID: X │      │ OnOrder: 1      │
   │ QtyReceived: 10 │      └─────────────────┘
   └─────────────────┘
                            ┌─────────────────┐
                            │ NEW Inv Item    │
                            │ Quantity: 10    │  ← Real inventory
                            │ OnOrder: 0      │
                            └─────────────────┘

3. AFTER FINALIZATION
   ┌─────────────────┐
   │ PO Item         │      (Inventory placeholder DELETED)
   │ Finalized: 1    │
   │ OnOrderInvID:   │──▶ NULL
   └─────────────────┘
                            ┌─────────────────┐
                            │ Real Inv Item   │
                            │ Quantity: 10    │  ← Still exists
                            │ OnOrder: 0      │
                            └─────────────────┘
```

### What the Tool Does

For each item to finalize, the tool performs 3 database operations:

1. **DELETE** the placeholder inventory item
2. **UPDATE** the PO item: set `Finalized = 1` and `OnOrderInventoryItemID = NULL`
3. **UPDATE** the PO: increment `NumberOfFinalizedItems`

---

## The Query Logic

### Finding Items to Finalize

The core query uses the **inventory-based approach**:

```sql
SELECT
    inv.ItemID as InventoryItemID,
    poi.PurchaseOrderItemID,
    poi.PurchaseOrderID,
    po.PONumber
FROM inventoryitems inv
INNER JOIN purchaseorderitems poi
    ON poi.OnOrderInventoryItemID = inv.ItemID
INNER JOIN purchaseorders po
    ON po.PurchaseOrderID = poi.PurchaseOrderID
WHERE inv.Quantity = 0
  AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
ORDER BY po.PONumber, poi.PurchaseOrderItemID
```

### Why This Works

1. **`inv.Quantity = 0`** - Only items with zero quantity (received and ready to clean up)
2. **`INNER JOIN purchaseorderitems`** - Ensures we only get inventory items linked to POs (not random zero-qty inventory)
3. **`poi.Finalized = 0 OR poi.Finalized IS NULL`** - Items not yet finalized

### Important: NULL Handling

The `Finalized` column can have three states:
- `NULL` - Not finalized (default for new items)
- `0` - Not finalized (explicitly set)
- `1` - Finalized

**You must check for both NULL and 0** when finding non-finalized items:

```sql
-- WRONG (misses NULL values):
WHERE poi.Finalized = 0

-- CORRECT:
WHERE (poi.Finalized = 0 OR poi.Finalized IS NULL)
```

---

## Step-by-Step Process

### 1. Find Items to Finalize

```sql
SELECT inv.ItemID, poi.PurchaseOrderItemID, poi.PurchaseOrderID
FROM inventoryitems inv
INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
WHERE inv.Quantity = 0
  AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
```

### 2. For Each Item, Execute These Operations

```sql
-- Step 1: Delete the placeholder inventory item
DELETE FROM inventoryitems
WHERE ItemID = [InventoryItemID];

-- Step 2: Update the PO item
UPDATE purchaseorderitems
SET Finalized = 1,
    OnOrderInventoryItemID = NULL
WHERE PurchaseOrderItemID = [PurchaseOrderItemID];

-- Step 3: Increment the PO's finalized count
UPDATE purchaseorders
SET NumberOfFinalizedItems = NumberOfFinalizedItems + 1
WHERE PurchaseOrderID = [PurchaseOrderID];
```

### 3. Verify Results

```sql
-- Check PO item is finalized
SELECT Finalized, OnOrderInventoryItemID
FROM purchaseorderitems
WHERE PurchaseOrderItemID = [PurchaseOrderItemID];
-- Expected: Finalized = 1, OnOrderInventoryItemID = NULL

-- Check inventory item is deleted
SELECT ItemID FROM inventoryitems
WHERE ItemID = [InventoryItemID];
-- Expected: No rows returned
```

---

## Important Notes

### Why We Start from Inventory (Not PO Items)

The old approach started from PO items and checked `QuantityReceived >= Quantity`. This was problematic because:
- Required complex logic for partial receipts
- Had edge cases around quantities
- Didn't match how users think about the problem

The new approach matches the UI workflow:
1. User filters inventory for Quantity = 0
2. User clicks "Finalize Displayed Items"
3. Done

### Transaction Safety

All operations are wrapped in a transaction:

```python
conn.autocommit = False
try:
    # ... all operations ...
    conn.commit()
except:
    conn.rollback()
```

If ANY operation fails, ALL changes are rolled back.

### Logging

Every run creates a log file in `logs/YYYY-MM-DD_runN/`:
- Timestamp for each operation
- Items processed
- Success/failure status
- Any errors encountered

---

## Troubleshooting

### Problem: "0 items to finalize" but I know there are items

**Check 1:** Verify inventory items exist with Quantity = 0

```sql
SELECT COUNT(*) FROM inventoryitems WHERE Quantity = 0;
```

**Check 2:** Verify they're linked to PO items

```sql
SELECT COUNT(*)
FROM inventoryitems inv
INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
WHERE inv.Quantity = 0;
```

**Check 3:** Check the Finalized status (remember NULL!)

```sql
SELECT poi.Finalized, COUNT(*)
FROM inventoryitems inv
INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
WHERE inv.Quantity = 0
GROUP BY poi.Finalized;
```

If you see `Finalized = NULL`, make sure your query uses:
```sql
WHERE (poi.Finalized = 0 OR poi.Finalized IS NULL)
```

### Problem: Connection errors

**Check 1:** Verify `.env` file has correct credentials

```
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
```

**Check 2:** Test connection

```bash
python 00_test_connection.py
```

### Problem: Script runs but nothing changes

**Check 1:** Are you running in dry-run mode?

The `--dry-run` flag previews without making changes. Remove it to make actual changes.

**Check 2:** Did you confirm with "YES"?

The script requires typing exactly `YES` (case-sensitive) to proceed.

---

## Scripts Reference

### Main Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `finalize.py` | Main finalization script | `python finalize.py [--dry-run] [--limit N]` |
| `confirm_approach.py` | Preview items to finalize | `python confirm_approach.py` |
| `investigate_state.py` | Diagnose database state | `python investigate_state.py` |
| `00_test_connection.py` | Test database connection | `python 00_test_connection.py` |

### Configuration

| File | Purpose |
|------|---------|
| `db_config.py` | Database connection functions |
| `.env` | Database credentials |
| `requirements.txt` | Python dependencies |

### Archived Scripts

The `archive/` folder contains old scripts from the previous approach. These are kept for reference but should not be used:

- `archive/analysis-scripts/` - Scripts used to analyze the database schema
- `archive/old-finalization-scripts/` - Previous finalization scripts (different approach)

---

## Database Connection

The tool connects via `db_config.py`:

```python
from db_config import get_connection

conn = get_connection()
cursor = conn.cursor(dictionary=True)

# ... do work ...

cursor.close()
conn.close()
```

Configuration is loaded from `.env`:

```python
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3307)),
    'user': os.getenv('MYSQL_USER', 'admin'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
}
```

---

## Building and Distribution

### Why You Need to Build Twice

When you build a `.exe` with PyInstaller, the resulting file **only works on the same type of processor** it was built with. This is because different processors speak different "languages" (instruction sets).

There are two main processor types in Windows PCs:

| Processor Type | Also Called | Found In |
|---------------|-------------|----------|
| **ARM64** | ARM, aarch64 | Newer Surface Pro (2021+), Surface Pro X, Snapdragon laptops |
| **x64** | AMD64, x86-64, Intel 64 | Most desktops, older laptops, older Surfaces, Intel/AMD PCs |

**Your machine** has an ARM processor (that's why you have `Python312-arm64`). If you build a `.exe` on your machine, it produces an ARM `.exe` that **only runs on other ARM machines**.

Most people have x64 (Intel/AMD) machines. So if you give them your ARM-built `.exe`, they'll get a "can't run application" error.

### How to Handle This

You have two Python installations:

| Python Install | Processor Type | Path |
|---------------|----------------|------|
| Python 3.12 ARM64 | ARM (your machine) | `C:\...\Python312-arm64\python.exe` |
| Python 3.14 x64 | Intel/AMD (other people) | `C:\...\Python314\python.exe` |

**Build for yourself (testing):**
```powershell
& "C:\Users\nickb\AppData\Local\Programs\Python\Python312-arm64\python.exe" build.py gui
```

**Build for others (distribution):**
```powershell
& "C:\Users\nickb\AppData\Local\Programs\Python\Python314\python.exe" build.py gui
```

### Recommended Workflow

1. **Build with ARM Python** → Test on your machine → Confirm it works
2. **Rebuild with x64 Python** → Give `dist/finalize-tool/` folder to others

The source code (`.py` files) is identical for both - only the `.exe` output is different.

### How to Tell Which Python Is Which

Run this to see all Python installs on your machine:
```powershell
where.exe python
```

Or check a specific install:
```powershell
& "C:\path\to\python.exe" -c "import platform; print(platform.machine())"
```
- If it prints `ARM64` → ARM build
- If it prints `AMD64` → x64 build

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Jan 2026 | New inventory-based approach, NULL handling fix |
| 1.0 | Jan 2026 | Original PO-item-based approach |
