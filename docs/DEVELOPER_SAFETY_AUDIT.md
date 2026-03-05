# PO Finalize Tool - Developer Safety Audit

**Purpose:** This document is intended for the Tekla PowerFab development team to review the exact database operations performed by this tool so they can confirm it is safe for client distribution.

**Tool Version:** 2.0 (Inventory-Based Approach)
**Date:** March 2026
**Database Engine:** MySQL (via `mysql-connector-python`)

---

## Executive Summary

This tool automates the "Finalize Displayed Items" action that users perform manually in the PowerFab UI. It removes zero-quantity on-order placeholder inventory items after materials have been received, and marks the associated PO items as finalized.

**The tool touches exactly 3 tables:**

| Table | Operations | Scope |
|-------|-----------|-------|
| `inventoryitems` | READ, DELETE | Only rows where `Quantity = 0` AND linked to a non-finalized PO item |
| `purchaseorderitems` | READ, UPDATE | Only rows where `Finalized = 0` or `NULL` AND linked to a zero-quantity inventory item |
| `purchaseorders` | READ, UPDATE | Only the `NumberOfFinalizedItems` counter on affected POs |

**The tool does NOT:**
- Create any new rows in any table
- Modify any other tables in the database
- Touch inventory items with `Quantity > 0`
- Touch PO items that are already finalized
- Modify ordered quantities, received quantities, pricing, or any other PO data
- Access or modify any log tables, user tables, job tables, or other PowerFab tables

---

## Complete SQL Operation Inventory

Every SQL statement executed by the tool is documented below, organized by operation type.

### READ Operations (SELECT)

These queries gather data but make no changes.

#### R1: Find Items to Finalize (Core Query)

**Used by:** `finalize.py`, `gui/finalize_gui.py`

```sql
SELECT
    inv.ItemID as InventoryItemID,
    inv.Quantity as InvQuantity,
    inv.OnOrder,
    poi.PurchaseOrderItemID,
    poi.PurchaseOrderID,
    poi.OnOrderInventoryItemID,
    poi.Quantity as OrderedQty,
    poi.QuantityReceived,
    poi.Finalized,
    po.PONumber
FROM inventoryitems inv
INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
INNER JOIN purchaseorders po ON po.PurchaseOrderID = poi.PurchaseOrderID
WHERE inv.Quantity = 0
  AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
ORDER BY po.PONumber, poi.PurchaseOrderItemID
```

**Tables read:** `inventoryitems`, `purchaseorderitems`, `purchaseorders`
**Columns read:**
- `inventoryitems`: `ItemID`, `Quantity`, `OnOrder`
- `purchaseorderitems`: `PurchaseOrderItemID`, `PurchaseOrderID`, `OnOrderInventoryItemID`, `Quantity`, `QuantityReceived`, `Finalized`
- `purchaseorders`: `PurchaseOrderID`, `PONumber`

**Join conditions:**
- `purchaseorderitems.OnOrderInventoryItemID = inventoryitems.ItemID`
- `purchaseorders.PurchaseOrderID = purchaseorderitems.PurchaseOrderID`

**Filter logic:**
- `inv.Quantity = 0` -- Only zero-quantity placeholder items
- `poi.Finalized = 0 OR poi.Finalized IS NULL` -- Only non-finalized PO items

**Why this is safe:** INNER JOINs ensure only inventory items that are linked to a PO item via `OnOrderInventoryItemID` are selected. Random zero-quantity inventory items not linked to any PO are excluded.

---

#### R2: Verification - Check PO Item Status (Post-Finalization)

**Used by:** `finalize.py`, `gui/finalize_gui.py`

```sql
SELECT Finalized, OnOrderInventoryItemID
FROM purchaseorderitems
WHERE PurchaseOrderItemID = %s
```

**Tables read:** `purchaseorderitems`
**Columns read:** `Finalized`, `OnOrderInventoryItemID`
**Purpose:** Confirms the PO item was updated correctly (expects `Finalized = 1`, `OnOrderInventoryItemID = NULL`).

---

#### R3: Verification - Check Inventory Item Deleted (Post-Finalization)

**Used by:** `finalize.py`, `gui/finalize_gui.py`

```sql
SELECT ItemID FROM inventoryitems WHERE ItemID = %s
```

**Tables read:** `inventoryitems`
**Columns read:** `ItemID`
**Purpose:** Confirms the inventory placeholder was deleted (expects 0 rows returned).

---

### WRITE Operations (UPDATE)

#### W1: Mark PO Item as Finalized

**Used by:** `finalize.py`, `gui/finalize_gui.py`

```sql
UPDATE purchaseorderitems
SET Finalized = 1, OnOrderInventoryItemID = NULL
WHERE PurchaseOrderItemID = %s
```

**Table modified:** `purchaseorderitems`
**Columns modified:**
| Column | Before | After | Purpose |
|--------|--------|-------|---------|
| `Finalized` | `0` or `NULL` | `1` | Marks item as finalized |
| `OnOrderInventoryItemID` | `[ItemID value]` | `NULL` | Removes link to the deleted inventory placeholder |

**Columns NOT modified:** `PurchaseOrderItemID`, `PurchaseOrderID`, `Quantity`, `QuantityReceived`, and all other columns on the row remain untouched.

**Scope:** Exactly 1 row per execution (filtered by primary key `PurchaseOrderItemID`).

**Why this is safe:** This is the same state change that occurs when a user clicks "Finalize Displayed Items" in the PowerFab UI. Analysis of 12,294 previously UI-finalized items confirms 100% have `Finalized = 1` and `OnOrderInventoryItemID = NULL`.

---

#### W2: Increment PO Finalized Item Counter

**Used by:** `finalize.py`, `gui/finalize_gui.py`

```sql
UPDATE purchaseorders
SET NumberOfFinalizedItems = NumberOfFinalizedItems + 1
WHERE PurchaseOrderID = %s
```

**Table modified:** `purchaseorders`
**Columns modified:**
| Column | Before | After | Purpose |
|--------|--------|-------|---------|
| `NumberOfFinalizedItems` | `N` | `N + 1` | Increments the finalized items counter |

**Columns NOT modified:** `PurchaseOrderID`, `PONumber`, and all other columns on the row remain untouched.

**Scope:** Exactly 1 row per execution (filtered by primary key `PurchaseOrderID`). Executed once per PO item finalized (so if a PO has 5 items being finalized, this runs 5 times for that PO, incrementing by 1 each time).

---

### DELETE Operations

#### D1: Delete Inventory Placeholder Item

**Used by:** `finalize.py`, `gui/finalize_gui.py`

```sql
DELETE FROM inventoryitems WHERE ItemID = %s
```

**Table modified:** `inventoryitems`
**Scope:** Exactly 1 row per execution (filtered by primary key `ItemID`).

**What is being deleted:**
- Rows where `Quantity = 0` (verified by the SELECT in R1)
- Rows that are linked to a PO item via `purchaseorderitems.OnOrderInventoryItemID` (verified by the INNER JOIN in R1)
- These are on-order placeholder records, NOT real inventory with physical stock

**What is NOT deleted:**
- Inventory items with `Quantity > 0` (real inventory or partial-receipt tracking items)
- Inventory items not linked to any PO item
- Inventory items linked to already-finalized PO items

**Why this is safe:** The tool first runs query R1, which only selects inventory items where `Quantity = 0` AND linked to non-finalized PO items. The `ItemID` values passed to this DELETE come exclusively from that result set.

---

## Operation Sequence Per Item

For each item to finalize, these 3 SQL statements execute in this exact order:

```
1. DELETE FROM inventoryitems WHERE ItemID = %s          -- Remove placeholder
2. UPDATE purchaseorderitems SET ... WHERE ... = %s      -- Mark finalized
3. UPDATE purchaseorders SET ... WHERE ... = %s          -- Increment counter
```

After all items are processed, verification queries (R2 + R3) run for each item to confirm correctness before committing.

---

## Transaction Safety

All modifications run within a single database transaction:

```
BEGIN TRANSACTION
  For each item:
    Execute D1 (DELETE inventory placeholder)
    Execute W1 (UPDATE PO item)
    Execute W2 (UPDATE PO counter)
  For each item:
    Execute R2 (verify PO item updated)
    Execute R3 (verify inventory item deleted)
  If ALL verifications pass:
    COMMIT
  Else:
    ROLLBACK   -- ALL changes are undone, database is unchanged
ON ERROR:
  ROLLBACK     -- ALL changes are undone, database is unchanged
```

**Key guarantees:**
- If any single operation fails, the entire batch is rolled back
- If verification detects any inconsistency, the entire batch is rolled back
- The database is never left in a partially-modified state
- `autocommit` is explicitly set to `False` before any modifications begin

---

## Dry-Run Mode

The tool supports a `--dry-run` flag (CLI) and "Preview" button (GUI) that executes ONLY the read query (R1) and reports what would be changed. No UPDATE or DELETE statements are executed in dry-run mode.

---

## Filtering Safety Analysis

### Why only the correct items are affected

The selection criteria form a narrow funnel:

```
All inventoryitems rows
  └─ WHERE Quantity = 0                              -- Eliminates all real inventory
      └─ INNER JOIN purchaseorderitems               -- Eliminates items not linked to POs
          ON OnOrderInventoryItemID = ItemID
          └─ WHERE Finalized = 0 OR Finalized IS NULL -- Eliminates already-finalized items
```

Each filter narrows the scope:

1. **`Quantity = 0`**: Eliminates any inventory item with physical stock. Real inventory always has `Quantity > 0`.
2. **`INNER JOIN` on `OnOrderInventoryItemID`**: Eliminates zero-quantity items that aren't PO placeholders (e.g., consumed material, scrapped items). Only items with an active PO link pass.
3. **`Finalized = 0 OR NULL`**: Eliminates items already processed. Prevents double-finalization.

### What cannot be affected

| Scenario | Why it's excluded |
|----------|-------------------|
| Real inventory items (actual stock) | They have `Quantity > 0`, excluded by WHERE clause |
| Inventory not linked to any PO | No matching row in `purchaseorderitems`, excluded by INNER JOIN |
| Already-finalized PO items | `Finalized = 1`, excluded by WHERE clause |
| Partial receipts still on order | The inventory placeholder has `Quantity > 0` (tracking remaining items), excluded by `Quantity = 0` filter |
| PO items not yet received | Their inventory placeholders have `Quantity > 0` (full order qty), excluded by `Quantity = 0` filter |

---

## Table Impact Summary

### `inventoryitems`

| Operation | Columns | Condition | Effect |
|-----------|---------|-----------|--------|
| SELECT | `ItemID`, `Quantity`, `OnOrder` | `Quantity = 0` AND joined to non-finalized PO item | Read only |
| DELETE | Entire row | `ItemID = %s` (from SELECT result) | Removes zero-quantity placeholder row |
| SELECT | `ItemID` | `ItemID = %s` | Verification read (post-delete) |

**Net effect:** Zero-quantity on-order placeholder rows are removed. No other rows or columns are touched.

### `purchaseorderitems`

| Operation | Columns | Condition | Effect |
|-----------|---------|-----------|--------|
| SELECT | `PurchaseOrderItemID`, `PurchaseOrderID`, `OnOrderInventoryItemID`, `Quantity`, `QuantityReceived`, `Finalized` | Joined to zero-qty inventory item, `Finalized = 0/NULL` | Read only |
| UPDATE | `Finalized` (0/NULL -> 1), `OnOrderInventoryItemID` (value -> NULL) | `PurchaseOrderItemID = %s` | Marks item as finalized, clears inventory link |
| SELECT | `Finalized`, `OnOrderInventoryItemID` | `PurchaseOrderItemID = %s` | Verification read (post-update) |

**Net effect:** Two columns updated on qualifying rows. All other columns and all non-qualifying rows are untouched.

### `purchaseorders`

| Operation | Columns | Condition | Effect |
|-----------|---------|-----------|--------|
| SELECT | `PurchaseOrderID`, `PONumber` | Joined from `purchaseorderitems` | Read only |
| UPDATE | `NumberOfFinalizedItems` (+1) | `PurchaseOrderID = %s` | Increments counter |

**Net effect:** One counter column incremented on affected POs. All other columns and all non-affected POs are untouched.

---

## Shipped Executables

The tool ships as two executables built from the source files below. Both perform identical database operations.

| Executable | Source File | Interface |
|------------|-------------|-----------|
| `finalize_gui.exe` | `gui/finalize_gui.py` | Tkinter GUI window |
| `finalize.exe` | `finalize.py` | Command-line interface |

Supporting module: `db_config.py` (database connection only, no SQL operations beyond `SELECT 1` for connection testing).

### Scripts NOT shipped to clients

The following scripts exist in the repository for development/analysis purposes and are NOT included in the distributed executables:

- `confirm_approach.py` -- Read-only diagnostic queries
- `investigate_state.py` -- Read-only diagnostic queries
- `00_test_connection.py` -- Connection test only (`SELECT 1` and `INFORMATION_SCHEMA` read)
- `archive/` -- Old development scripts, not distributed

---

## Questions for PowerFab Development Team

1. **Trigger/cascade verification:** Are there any database triggers on `inventoryitems`, `purchaseorderitems`, or `purchaseorders` that fire on DELETE or UPDATE? If so, does this tool's operations align with expected trigger behavior?

2. **Foreign key constraints:** Are there additional tables with foreign keys referencing `inventoryitems.ItemID` beyond `purchaseorderitems.OnOrderInventoryItemID`? If so, would deleting the zero-quantity placeholder rows cause constraint violations?

3. **Log tables:** Does PowerFab maintain audit/log tables (e.g., `inventoryitemslog`, `purchaseorderitemslog`) that expect entries when these operations occur? Should this tool insert corresponding log records?

4. **Cache/state invalidation:** Does PowerFab cache inventory or PO data in-memory? If so, do users need to refresh their view after this tool runs?

5. **NumberOfFinalizedItems accuracy:** Is `NumberOfFinalizedItems` used by any application logic beyond display? Would an incorrect count cause issues?

6. **Concurrent access:** Is it safe to run these operations while PowerFab clients are connected and active? Are there row-level locks or application-level locks we should be aware of?

---

## Appendix: Evidence of UI Behavior Match

This tool was reverse-engineered from analyzing the database state of items finalized through the PowerFab UI:

| Observation | Finalized via UI (12,294 items) | Not Yet Finalized (9,248 items) |
|-------------|--------------------------------|--------------------------------|
| `Finalized` value | `1` (100%) | `0` or `NULL` (100%) |
| `OnOrderInventoryItemID` | `NULL` (100%) | Has a value (100%) |
| Linked inventory item exists | No (deleted) | Yes (placeholder exists) |

The 100% correlation across 21,542 items confirms this tool replicates the exact database state changes performed by the PowerFab UI's finalization feature.
