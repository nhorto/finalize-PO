"""
PO ITEM FINALIZATION SCRIPT
============================
This script finalizes PO items that have been received but not yet finalized.

SAFETY FEATURES:
- Transaction-based (all changes commit together or roll back)
- Dry-run mode (--dry-run) to see what would happen without making changes
- Single-PO test mode (--po-id <id>) to test on one PO first
- Comprehensive logging to timestamped file
- Verification after completion

USAGE:
  Dry run (see what would happen):
    python 05_finalize_po_items.py --dry-run

  Test on single PO:
    python 05_finalize_po_items.py --po-id 12345 --dry-run
    python 05_finalize_po_items.py --po-id 12345

  Full run (finalize all):
    python 05_finalize_po_items.py

  Limit number of items:
    python 05_finalize_po_items.py --limit 10
"""

import argparse
import sys
from datetime import datetime
from db_config import get_connection

# Create log file with timestamp
LOG_FILE = f"finalization_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def log(message, also_print=True):
    """Log message to file and optionally print to console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')
    if also_print:
        print(log_line)

def get_items_to_finalize(cursor, po_id=None, limit=None):
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

    if po_id:
        query += f" AND poi.PurchaseOrderID = {po_id}"

    query += " ORDER BY poi.PurchaseOrderID, poi.PurchaseOrderItemID"

    if limit:
        query += f" LIMIT {limit}"

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

def finalize_item(cursor, item, dry_run=False):
    """
    Finalize a single PO item.
    Returns True if successful, False otherwise.
    """
    po_item_id = item['PurchaseOrderItemID']
    po_id = item['PurchaseOrderID']
    inv_item_id = item['OnOrderInventoryItemID']
    po_number = item['PONumber']

    log(f"  Processing PO Item {po_item_id} (PO# {po_number})")
    log(f"    - OnOrderInventoryItemID: {inv_item_id}")
    log(f"    - Quantity: {item['Quantity']}, Received: {item['QuantityReceived']}")

    # Verify the inventory item
    inv_item = verify_inventory_item(cursor, inv_item_id)
    if not inv_item:
        log(f"    WARNING: Inventory item {inv_item_id} not found! Skipping.")
        return False

    log(f"    - Inventory item found: OnOrder={inv_item['OnOrder']}, Qty={inv_item['Quantity']}")

    if inv_item['OnOrder'] != 1:
        log(f"    WARNING: Inventory item {inv_item_id} is not marked as OnOrder! Skipping.")
        return False

    if dry_run:
        log(f"    [DRY RUN] Would delete inventory item {inv_item_id}")
        log(f"    [DRY RUN] Would update PO item {po_item_id}: Finalized=1, OnOrderInventoryItemID=NULL")
        log(f"    [DRY RUN] Would increment NumberOfFinalizedItems for PO {po_id}")
        return True

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
    return True

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
    parser = argparse.ArgumentParser(description='Finalize PO items that have been received')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would happen without making changes')
    parser.add_argument('--po-id', type=int,
                        help='Only process items for a specific PO ID')
    parser.add_argument('--limit', type=int,
                        help='Limit the number of items to process')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Skip confirmation prompt (use with caution)')
    args = parser.parse_args()

    log("=" * 60)
    log("PO ITEM FINALIZATION SCRIPT")
    log("=" * 60)

    if args.dry_run:
        log("MODE: DRY RUN (no changes will be made)")
    else:
        log("MODE: LIVE (changes will be committed)")

    if args.po_id:
        log(f"FILTER: Only PO ID {args.po_id}")

    if args.limit:
        log(f"LIMIT: Processing up to {args.limit} items")

    log(f"LOG FILE: {LOG_FILE}")
    log("")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get items to finalize
        log("Fetching items to finalize...")
        items = get_items_to_finalize(cursor, args.po_id, args.limit)
        log(f"Found {len(items)} items to finalize")

        if not items:
            log("No items to finalize. Exiting.")
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

        for item in items:
            if finalize_item(cursor, item, args.dry_run):
                success_count += 1
                processed.append(item)
            else:
                skip_count += 1
            log("")  # Blank line between items

        # Summary
        log("=" * 60)
        log("PROCESSING SUMMARY")
        log("=" * 60)
        log(f"Total items found: {len(items)}")
        log(f"Successfully processed: {success_count}")
        log(f"Skipped (warnings): {skip_count}")

        if args.dry_run:
            log("\n[DRY RUN] No changes were made to the database.")
        else:
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
