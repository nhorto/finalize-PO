# PO Finalization Tool - Stakeholder Guide

## Executive Summary

This tool automates the cleanup of "zero quantity" placeholder items in Tekla PowerFab inventory. These placeholders accumulate after materials are received and create clutter in inventory reports. The tool safely removes them, keeping inventory clean and accurate.

**Key Benefits:**
- Eliminates manual clicking through POs to finalize items
- Removes zero-quantity clutter from inventory reports
- Runs in seconds instead of hours of manual work
- Includes safety features to prevent accidental data loss

---

## The Problem

When you create a Purchase Order in PowerFab and receive materials, here's what happens:

### Step 1: PO Created
When a PO is created, PowerFab creates a **placeholder** in inventory to track that materials are "on order."

```
INVENTORY VIEW:
+------------------+----------+--------+
| Material         | Quantity | Status |
+------------------+----------+--------+
| L6x4x5/8 Angle   | 10       | On Order (placeholder) |
+------------------+----------+--------+
```

### Step 2: Materials Received
When the materials arrive and are received, PowerFab:
- Keeps the original placeholder (but sets its quantity to **zero**)
- Creates a **new** inventory record with the actual received quantity

```
INVENTORY VIEW:
+------------------+----------+---------------------------+
| Material         | Quantity | Status                    |
+------------------+----------+---------------------------+
| L6x4x5/8 Angle   | 0        | Placeholder (needs cleanup) |
| L6x4x5/8 Angle   | 10       | Real inventory            |
+------------------+----------+---------------------------+
```

### Step 3: The Problem - Zero Quantity Lines Accumulate
Those zero-quantity placeholders stay in inventory until someone manually "finalizes" them. Over time, you end up with hundreds or thousands of these cluttering your inventory view:

```
INVENTORY VIEW (cluttered):
+------------------+----------+
| Material         | Quantity |
+------------------+----------+
| L6x4x5/8 Angle   | 0        |  <-- Clutter
| L6x4x5/8 Angle   | 10       |
| W12x26 Beam      | 0        |  <-- Clutter
| W12x26 Beam      | 25       |
| HSS4x4x1/4       | 0        |  <-- Clutter
| HSS4x4x1/4       | 50       |
| ... hundreds more ...       |
+------------------+----------+
```

---

## The Solution

This tool automatically finds and removes those zero-quantity placeholders.

### How It Works (Simple Version)

1. **Find** all inventory items with Quantity = 0
2. **Verify** they're linked to a Purchase Order (so we don't delete real inventory)
3. **Remove** them and mark the PO items as finalized

### What "Finalize" Means

When an item is finalized:
- The zero-quantity placeholder is **deleted** from inventory
- The PO item is marked as **finalized** (complete)
- The PO's finalized item counter is **incremented**

This is exactly what happens when you click "Finalize Displayed Items" in the PowerFab UI - we're just automating it.

---

## Safety Features

The tool includes multiple safety measures:

| Feature | Description |
|---------|-------------|
| **Dry-Run Mode** | Preview what would happen without making any changes |
| **Confirmation Prompt** | Requires typing "YES" before making changes |
| **Transaction-Based** | If anything fails, ALL changes are rolled back |
| **Detailed Logging** | Every action is logged with timestamps |
| **Verification** | Results are verified before committing |

### Example Dry Run Output

```
======================================================================
PO ITEM FINALIZATION (Inventory-Based Approach)
======================================================================
MODE: DRY RUN (no changes will be made)

Fetching items to finalize...
Found 1226 items to finalize

Items to finalize by PO (156 POs):
  PO# 0000023: 12 items
  PO# 0000045: 8 items
  PO# 0000067: 23 items
  ...

[DRY RUN] No changes were made to the database.
```

---

## Before and After

### Before Running the Tool

```
INVENTORY REPORT:
- Total line items: 5,847
- Zero quantity items: 1,226 (clutter)
- Actual inventory items: 4,621
```

### After Running the Tool

```
INVENTORY REPORT:
- Total line items: 4,621
- Zero quantity items: 0
- Actual inventory items: 4,621
```

**Result:** 1,226 unnecessary lines removed, clean inventory reports.

---

## When to Run This Tool

**Recommended:** Run periodically (weekly or monthly) to keep inventory clean.

**Good times to run:**
- After a large receiving session
- Before generating inventory reports
- During off-hours (though the tool runs quickly)

**The tool is safe to run anytime** - it only removes items that are already received and have zero quantity.

---

## What This Tool Does NOT Do

- Does NOT delete real inventory items (only zero-quantity placeholders)
- Does NOT modify PO amounts or received quantities
- Does NOT affect items that haven't been received yet
- Does NOT require PowerFab to be closed

---

## Frequently Asked Questions

**Q: Can this accidentally delete real inventory?**
A: No. The tool only deletes inventory items that:
1. Have Quantity = 0
2. Are linked to a PO item
3. The PO item is not already finalized

Real inventory items always have Quantity > 0.

**Q: What if something goes wrong?**
A: The tool uses database transactions. If any error occurs, ALL changes are automatically rolled back - nothing is changed.

**Q: How long does it take?**
A: The tool processes hundreds of items in seconds. A typical run of 1,000+ items completes in under a minute.

**Q: Can I see what will happen before running it?**
A: Yes! Use `--dry-run` mode to preview without making changes.

**Q: Is there a log of what was done?**
A: Yes. Every run creates a detailed log file in the `logs/` folder showing exactly what was processed.

---

## Contact

For questions or issues, contact the developer or check the technical documentation in `docs/TECHNICAL_REFERENCE.md`.
