"""
PO ITEM FINALIZATION SCRIPT v2
==============================
This script finalizes PO items that have been FULLY received.

CHANGES FROM v1:
- Only finalizes items where QuantityReceived >= Quantity (fully received)
- Verifies inventory item has Quantity = 0 before deletion
- Warns about partial receipts but does NOT finalize them
- Added --include-partial flag for intentional partial finalization

SAFETY FEATURES:
- Transaction-based (all changes commit together or roll back)
- Dry-run mode (--dry-run) to see what would happen without making changes
- Single-PO test mode (--po-id <id>) to test on one PO first
- Comprehensive logging to timestamped file
- Verification after completion

USAGE:
  Dry run (see what would happen):
    python 05_finalize_po_items_v2.py --dry-run

  Test on single PO:
    python 05_finalize_po_items_v2.py --po-id 12345 --dry-run
    python 05_finalize_po_items_v2.py --po-id 12345

  Full run (finalize all fully-received items):
    python 05_finalize_po_items_v2.py

  Include partial receipts (use with caution):
    python 05_finalize_po_items_v2.py --include-partial
"""

import argparse
import sys
from datetime import datetime
from db_config import get_connection

# Create log file with timestamp
LOG_FILE = f"finalization_log_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def log(message, also_print=True):
    """Log message to file and optionally print to console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')
    if also_print:
        print(log_line)

def get_items_to_finalize(cursor, po_id=None, limit=None, include_partial=False):
    """Get list of PO items that need finalization."""
    query = """
        SELECT
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.OnOrderInventoryItemID,
            poi.Quantity,
            poi.QuantityReceived,
            poi.JobNumber,
            poi.DimensionString,
            po.PONumber
        FROM purchaseorderitems poi
        JOIN purchaseorders po ON poi.PurchaseOrderID = po.PurchaseOrderID
        WHERE poi.QuantityReceived > 0
          AND poi.Finalized = 0
          AND poi.OnOrderInventoryItemID IS NOT NULL
    """

    # v2 CHANGE: Only include fully received items by default
    if not include_partial:
        query += " AND poi.QuantityReceived >= poi.Quantity"

    if po_id:
        query += f" AND poi.PurchaseOrderID = {po_id}"

    query += " ORDER BY poi.PurchaseOrderID, poi.PurchaseOrderItemID"

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    return cursor.fetchall()

def get_partial_receipt_items(cursor, po_id=None):
    """Get items that have partial receipts (not fully received)."""
    query = """
        SELECT
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.OnOrderInventoryItemID,
            poi.Quantity,
            poi.QuantityReceived,
            po.PONumber
        FROM purchaseorderitems poi
        JOIN purchaseorders po ON poi.PurchaseOrderID = po.PurchaseOrderID
        WHERE poi.QuantityReceived > 0
          AND poi.Finalized = 0
          AND poi.OnOrderInventoryItemID IS NOT NULL
          AND poi.QuantityReceived < poi.Quantity
    """

    if po_id:
        query += f" AND poi.PurchaseOrderID = {po_id}"

    query += " ORDER BY poi.PurchaseOrderID, poi.PurchaseOrderItemID"

    cursor.execute(query)
    return cursor.fetchall()

def verify_inventory_item(cursor, inventory_item_id):
    """Verify the inventory item exists and is an on-order placeholder."""
    cursor.execute("""
        SELECT ItemID, OnOrder, Quantity
        FROM inventoryitems
        WHERE ItemID = %s
    """, (inventory_item_id,))
    return cursor.fetchone()

def finalize_item(cursor, item, dry_run=False, include_partial=False):
    """
    Finalize a single PO item.
    Returns tuple: (success: bool, skipped_reason: str or None)
    """
    po_item_id = item['PurchaseOrderItemID']
    po_id = item['PurchaseOrderID']
    inv_item_id = item['OnOrderInventoryItemID']
    po_number = item['PONumber']
    qty_ordered = item['Quantity']
    qty_received = item['QuantityReceived']

    log(f"  Processing PO Item {po_item_id} (PO# {po_number})")
    log(f"    - OnOrderInventoryItemID: {inv_item_id}")
    log(f"    - Quantity: {qty_ordered}, Received: {qty_received}")

    # EDGE CASE 1: Partial receipt check
    if qty_received < qty_ordered:
        remaining = qty_ordered - qty_received
        if not include_partial:
            log(f"    SKIPPED: Partial receipt - {remaining} items still on order")
            log(f"    (Use --include-partial to force finalization of partial receipts)")
            return False, f"Partial receipt: {remaining} remaining"
        else:
            log(f"    WARNING: Partial receipt - {remaining} items still on order (--include-partial enabled)")

    # Verify the inventory item
    inv_item = verify_inventory_item(cursor, inv_item_id)
    if not inv_item:
        log(f"    WARNING: Inventory item {inv_item_id} not found! Skipping.")
        return False, "Inventory item not found"

    log(f"    - Inventory item found: OnOrder={inv_item['OnOrder']}, Qty={inv_item['Quantity']}")

    # EDGE CASE 2: Inventory item not marked as OnOrder
    if inv_item['OnOrder'] != 1:
        log(f"    WARNING: Inventory item {inv_item_id} is not marked as OnOrder! Skipping.")
        return False, "Inventory item OnOrder != 1"

    # EDGE CASE 3: Inventory item has quantity > 0
    if inv_item['Quantity'] > 0:
        if not include_partial:
            log(f"    SKIPPED: Inventory item has Qty={inv_item['Quantity']} (not 0)")
            log(f"    This suggests items are still on order. Use --include-partial to force.")
            return False, f"Inventory has Qty={inv_item['Quantity']}"
        else:
            log(f"    WARNING: Inventory item has Qty={inv_item['Quantity']} (will delete anyway due to --include-partial)")

    if dry_run:
        log(f"    [DRY RUN] Would delete inventory item {inv_item_id}")
        log(f"    [DRY RUN] Would update PO item {po_item_id}: Finalized=1, OnOrderInventoryItemID=NULL")
        log(f"    [DRY RUN] Would increment NumberOfFinalizedItems for PO {po_id}")
        return True, None

    # Step 1: Delete the inventory placeholder item
    log(f"    Step 1: Deleting inventory item {inv_item_id}")
    cursor.execute("DELETE FROM inventoryitems WHERE ItemID = %s", (inv_item_id,))

    # Step 2: Update the PO item
    log(f"    Step 2: Updating PO item {po_item_id}")
    cursor.execute("""
        UPDATE purchaseorderitems
        SET Finalized = 1, OnOrderInventoryItemID = NULL
        WHERE PurchaseOrderItemID = %s
    """, (po_item_id,))

    # Step 3: Increment the PO's NumberOfFinalizedItems
    log(f"    Step 3: Incrementing NumberOfFinalizedItems for PO {po_id}")
    cursor.execute("""
        UPDATE purchaseorders
        SET NumberOfFinalizedItems = NumberOfFinalizedItems + 1
        WHERE PurchaseOrderID = %s
    """, (po_id,))

    log(f"    SUCCESS: PO Item {po_item_id} finalized")
    return True, None

def verify_results(cursor, processed_items):
    """Verify that finalization was successful."""
    log("\n" + "=" * 60)
    log("VERIFICATION")
    log("=" * 60)

    success_count = 0
    fail_count = 0

    for item in processed_items:
        po_item_id = item['PurchaseOrderItemID']
        inv_item_id = item['OnOrderInventoryItemID']

        # Check PO item is finalized
        cursor.execute("""
            SELECT Finalized, OnOrderInventoryItemID
            FROM purchaseorderitems
            WHERE PurchaseOrderItemID = %s
        """, (po_item_id,))
        result = cursor.fetchone()

        if result and result['Finalized'] == 1 and result['OnOrderInventoryItemID'] is None:
            # Check inventory item is deleted
            cursor.execute("SELECT ItemID FROM inventoryitems WHERE ItemID = %s", (inv_item_id,))
            inv_result = cursor.fetchone()

            if inv_result is None:
                success_count += 1
            else:
                log(f"  FAIL: PO Item {po_item_id} - Inventory item {inv_item_id} still exists!")
                fail_count += 1
        else:
            log(f"  FAIL: PO Item {po_item_id} - Not properly finalized")
            fail_count += 1

    log(f"\nVerification complete: {success_count} succeeded, {fail_count} failed")
    return fail_count == 0

def main():
    parser = argparse.ArgumentParser(description='Finalize PO items that have been fully received')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would happen without making changes')
    parser.add_argument('--po-id', type=int,
                        help='Only process items for a specific PO ID')
    parser.add_argument('--limit', type=int,
                        help='Limit the number of items to process')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Skip confirmation prompt (use with caution)')
    parser.add_argument('--include-partial', action='store_true',
                        help='Include items with partial receipts (QuantityReceived < Quantity)')
    args = parser.parse_args()

    log("=" * 60)
    log("PO ITEM FINALIZATION SCRIPT v2")
    log("=" * 60)

    if args.dry_run:
        log("MODE: DRY RUN (no changes will be made)")
    else:
        log("MODE: LIVE (changes will be committed)")

    if args.po_id:
        log(f"FILTER: Only PO ID {args.po_id}")

    if args.limit:
        log(f"LIMIT: Processing up to {args.limit} items")

    if args.include_partial:
        log("WARNING: --include-partial enabled - will finalize partial receipts!")
    else:
        log("SAFETY: Only processing FULLY RECEIVED items (QuantityReceived >= Quantity)")

    log(f"LOG FILE: {LOG_FILE}")
    log("")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get items to finalize
        log("Fetching items to finalize...")
        items = get_items_to_finalize(cursor, args.po_id, args.limit, args.include_partial)
        log(f"Found {len(items)} items to finalize")

        # Also check for partial receipt items (for informational purposes)
        if not args.include_partial:
            partial_items = get_partial_receipt_items(cursor, args.po_id)
            if partial_items:
                log(f"\nNOTE: {len(partial_items)} items have partial receipts and will be SKIPPED:")
                for p in partial_items[:10]:
                    remaining = p['Quantity'] - p['QuantityReceived']
                    log(f"  PO# {p['PONumber']} Item {p['PurchaseOrderItemID']}: {remaining} remaining on order")
                if len(partial_items) > 10:
                    log(f"  ... and {len(partial_items) - 10} more")
                log("Use --include-partial to include these items")

        if not items:
            log("\nNo items to finalize. Exiting.")
            return

        # Show summary by PO
        po_counts = {}
        for item in items:
            po_num = item['PONumber']
            po_counts[po_num] = po_counts.get(po_num, 0) + 1

        log("\nItems by PO:")
        for po_num, count in sorted(po_counts.items()):
            log(f"  PO# {po_num}: {count} items")

        if not args.dry_run and not args.no_confirm:
            log("\n" + "!" * 60)
            log("WARNING: This will make changes to the database!")
            log("!" * 60)
            response = input("Type 'YES' to proceed: ")
            if response != 'YES':
                log("Aborted by user.")
                return
        elif not args.dry_run and args.no_confirm:
            log("\n[--no-confirm flag set, skipping confirmation]")

        # Ensure autocommit is off for transaction support
        if not args.dry_run:
            log("\nStarting transaction (autocommit disabled)...")
            conn.autocommit = False

        # Process each item
        log("\n" + "-" * 60)
        log("PROCESSING ITEMS")
        log("-" * 60)

        processed = []
        success_count = 0
        skip_count = 0
        skip_reasons = {}

        for item in items:
            success, skip_reason = finalize_item(cursor, item, args.dry_run, args.include_partial)
            if success:
                success_count += 1
                processed.append(item)
            else:
                skip_count += 1
                skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
            log("")  # Blank line between items

        # Summary
        log("=" * 60)
        log("PROCESSING SUMMARY")
        log("=" * 60)
        log(f"Total items found: {len(items)}")
        log(f"Successfully processed: {success_count}")
        log(f"Skipped: {skip_count}")

        if skip_reasons:
            log("\nSkip reasons:")
            for reason, count in skip_reasons.items():
                log(f"  {reason}: {count}")

        if args.dry_run:
            log("\n[DRY RUN] No changes were made to the database.")
        else:
            if processed:
                # Verify results before committing
                log("\nVerifying results before commit...")
                if verify_results(cursor, processed):
                    log("\nAll verifications passed. Committing transaction...")
                    conn.commit()
                    log("Transaction committed successfully!")
                else:
                    log("\nVerification FAILED! Rolling back transaction...")
                    conn.rollback()
                    log("Transaction rolled back. No changes were made.")
            else:
                log("\nNo items were processed. Nothing to commit.")

    except Exception as e:
        log(f"\nERROR: {str(e)}")
        if not args.dry_run:
            log("Rolling back transaction...")
            conn.rollback()
            log("Transaction rolled back. No changes were made.")
        raise

    finally:
        cursor.close()
        conn.close()
        log(f"\nLog saved to: {LOG_FILE}")

if __name__ == '__main__':
    main()
