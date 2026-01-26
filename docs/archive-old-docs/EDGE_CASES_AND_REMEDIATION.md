# Edge Cases and Remediation Guide

**Date:** January 25, 2026
**Status:** ✅ REMEDIATED

---

## Issue Summary

During the initial finalization run, **4 items were incorrectly finalized** because they had partial receipts (QuantityReceived < Quantity). These items still had inventory on order, and the original script did not check for this condition.

### Affected Items

| PO# | Item ID | Ordered | Received | Remaining |
|-----|---------|---------|----------|-----------|
| 0002549 | 17087 | 60 | 34 | **26** |
| 0002549 | 17095 | 70 | 44 | **26** |
| 0002549 | 17096 | 70 | 44 | **26** |
| 0003283 | 23739 | 40 | 35 | **5** |

**Total items incorrectly marked as finalized:** 4
**Total quantity still on order:** 83 items

---

## Root Cause Analysis

### What Happened

1. The original script (`05_finalize_po_items.py`) finalized any item where `QuantityReceived > 0`
2. It did NOT check if `QuantityReceived >= Quantity` (fully received)
3. It did NOT check if the linked inventory item had `Quantity > 0`

### The Problem

When a PO item has a partial receipt:
- `Quantity = 60` (ordered)
- `QuantityReceived = 34` (received so far)
- The linked inventory item has `Quantity = 26` (still on order)

The inventory item with `Quantity > 0` was a legitimate tracking record for items still on order, NOT just a zero-quantity placeholder.

### Why This Wasn't Caught Initially

During our analysis phase, we examined inventory items and found most had `Qty=0`. We assumed ALL on-order inventory items would have `Qty=0`, but this was incorrect for partial receipts.

---

## Edge Cases Identified

### Edge Case 1: Partial Receipts
- **Condition:** `QuantityReceived < Quantity`
- **Risk:** Finalizing loses track of remaining on-order items
- **Fix:** Only finalize when `QuantityReceived >= Quantity`

### Edge Case 2: Inventory Quantity > 0
- **Condition:** Linked inventory item has `Quantity > 0`
- **Risk:** Deleting valid tracking data
- **Fix:** Verify inventory `Quantity = 0` before deletion

### Edge Case 3: Over-Receipts
- **Condition:** `QuantityReceived > Quantity` (received more than ordered)
- **Risk:** None - these are valid to finalize
- **Status:** Handled correctly (44 items had over-receipts and were finalized)

---

## Updated Script (v2)

The new script `05_finalize_po_items_v2.py` includes these safety checks:

```python
# Only finalize fully-received items by default
AND poi.QuantityReceived >= poi.Quantity

# Verify inventory item is just a placeholder
if inv_item['Quantity'] > 0:
    log("SKIPPED: Inventory item has Qty > 0")
```

### v2 Safety Features

1. **Default:** Only finalizes items where `QuantityReceived >= Quantity`
2. **Inventory Check:** Skips if inventory `Quantity > 0`
3. **Partial Warning:** Shows list of skipped partial receipts
4. **Optional Flag:** `--include-partial` to force (with warnings)

---

## Remediation Options

### Option 1: Accept As-Is (No Action)

**Choose this if:**
- The remaining items on these POs will never arrive
- The business has written off these partial orders
- The POs are old and effectively closed

**Impact:**
- 83 items technically on order but not tracked
- May cause discrepancy in "on order" reports

### Option 2: Run Remediation Script

**Choose this if:**
- The remaining items are still expected to arrive
- You need accurate "on order" tracking
- These POs are still active

**What the remediation does:**
1. Creates new inventory placeholder items with `OnOrder=1` and `Quantity=[remaining]`
2. Updates PO items: `Finalized=0`, links to new inventory
3. Decrements `NumberOfFinalizedItems` on the PO headers

**Command:**
```bash
# Dry run first
python 09_remediate_partial_finalized.py --dry-run

# Actually remediate
python 09_remediate_partial_finalized.py
```

---

## Recommendation

**Check with the business** about the status of these 4 PO items:

1. **PO# 0002549** (3 items, 78 remaining total)
   - Is this PO still active?
   - Are these items expected to arrive?

2. **PO# 0003283** (1 item, 5 remaining)
   - Same questions

If the business says these partial orders are complete (won't receive more), then **Option 1** is fine.

If the business expects to receive the remaining items, run the **remediation script**.

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `05_finalize_po_items.py` | Original script (DO NOT USE) |
| `05_finalize_po_items_v2.py` | Updated script with edge case handling |
| `06_verify_finalization.py` | Verify finalization status |
| `07_investigate_impacts.py` | Investigate impacts |
| `08_find_affected_items.py` | Find incorrectly finalized items |
| `09_remediate_partial_finalized.py` | Fix incorrectly finalized items |

---

## Lessons Learned

1. **Always check for partial receipts** - Don't assume received means fully received
2. **Verify inventory state** - Check the actual data, not just the flag
3. **Test edge cases** - Include partial receipts in test data
4. **Dry-run extensively** - Review output carefully before committing

---

## Future Recommendations

For future finalization runs:

1. **Use v2 script only:** `05_finalize_po_items_v2.py`
2. **Always dry-run first:** `--dry-run`
3. **Review partial receipts:** Check the "SKIPPED" items in the output
4. **Consult business:** For any partial receipts that should be finalized

---

---

## Remediation Executed

**Date:** January 25, 2026

The remediation script was run and all 4 items were successfully fixed:

```
PO Item 17087: Created inventory item 48936 (Qty=26)
PO Item 17095: Created inventory item 48937 (Qty=26)
PO Item 17096: Created inventory item 48938 (Qty=26)
PO Item 23739: Created inventory item 48939 (Qty=5)
```

**Post-Remediation State:**
- Finalized items: 12,417
- Items needing finalization: 4 (the partial receipts - correctly non-finalized)
- On-order inventory items: 9,165

The 4 partial receipt items will remain non-finalized until they are fully received. The v2 script will not finalize them until `QuantityReceived >= Quantity`.

---

*Document prepared for stakeholder review and decision-making.*
