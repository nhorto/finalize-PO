"""
PO ITEM FINALIZATION SCRIPT (Simplified Inventory-Based Approach)
=================================================================
This script finalizes PO items by finding inventory items with Quantity = 0.

HOW IT WORKS:
1. Find inventory items with Quantity = 0 (received items ready to finalize)
2. Join back to PO items via OnOrderInventoryItemID
3. Finalize each item (delete inventory placeholder, update PO item)

This approach is simpler because:
- Zero quantity in inventory = received and ready to finalize
- No need for complex QuantityReceived >= Quantity checks
- Matches how users would do it in the PowerFab UI

SAFETY FEATURES:
- Transaction-based (all changes commit together or roll back)
- Dry-run mode (--dry-run) to preview without making changes
- Comprehensive logging to timestamped file in logs/ folder
- Verification after completion

USAGE:
  Dry run (see what would happen):
    python finalize.py --dry-run

  Full run (finalize all items):
    python finalize.py

  Limit items processed:
    python finalize.py --limit 10

  Skip confirmation:
    python finalize.py --no-confirm
"""

import argparse
import os
import sys
from datetime import datetime
from db_config import get_connection, get_app_directory

# Create log directory structure
def get_log_path():
    """Create and return path for log file in logs/YYYY-MM-DD_runN/ folder."""
    base_dir = get_app_directory()  # Works for both .py and .exe
    logs_dir = os.path.join(base_dir, 'logs')

    # Create logs dir if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Find the next run number for today
    today = datetime.now().strftime('%Y-%m-%d')
    run_num = 1

    while True:
        run_dir = os.path.join(logs_dir, f"{today}_run{run_num}")
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
            break
        run_num += 1

    timestamp = datetime.now().strftime('%H%M%S')
    log_file = os.path.join(run_dir, f"finalization_{timestamp}.txt")
    return log_file, run_dir

LOG_FILE, LOG_DIR = get_log_path()

def log(message, also_print=True):
    """Log message to file and optionally print to console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')
    if also_print:
        print(log_line)

def get_items_to_finalize(cursor, limit=None):
    """
    Get list of items to finalize using the simplified inventory-based approach.

    This finds:
    - Inventory items with Quantity = 0 (received and ready to finalize)
    - Joined to PO items via OnOrderInventoryItemID
    - Where the PO item is not yet finalized (Finalized = 0)
    """
    query = """
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
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    return cursor.fetchall()

def finalize_item(cursor, item, dry_run=False):
    """
    Finalize a single PO item.

    Steps:
    1. Delete the placeholder inventory item
    2. Update the PO item: Finalized=1, OnOrderInventoryItemID=NULL
    3. Increment the PO's NumberOfFinalizedItems counter

    Returns tuple: (success: bool, error_message: str or None)
    """
    inv_item_id = item['InventoryItemID']
    po_item_id = item['PurchaseOrderItemID']
    po_id = item['PurchaseOrderID']
    po_number = item['PONumber']

    log(f"  Processing: PO# {po_number}, PO Item {po_item_id}, Inventory Item {inv_item_id}")
    log(f"    - Ordered: {item['OrderedQty']}, Received: {item['QuantityReceived']}, Inv Qty: {item['InvQuantity']}")

    # Info: show OnOrder status (not a blocker since the join ensures it's PO-linked)
    if item['OnOrder'] != 1:
        log(f"    NOTE: Inventory item OnOrder={item['OnOrder']} (proceeding anyway - item is PO-linked)")

    if dry_run:
        log(f"    [DRY RUN] Would delete inventory item {inv_item_id}")
        log(f"    [DRY RUN] Would update PO item {po_item_id}: Finalized=1, OnOrderInventoryItemID=NULL")
        log(f"    [DRY RUN] Would increment NumberOfFinalizedItems for PO {po_id}")
        return True, None

    # Step 1: Delete the inventory placeholder
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

    log(f"    SUCCESS: Finalized PO Item {po_item_id}")
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
        inv_item_id = item['InventoryItemID']

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
    parser = argparse.ArgumentParser(
        description='Finalize PO items by finding inventory items with Quantity = 0'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would happen without making changes')
    parser.add_argument('--limit', type=int,
                        help='Limit the number of items to process')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Skip confirmation prompt')
    args = parser.parse_args()

    log("=" * 60)
    log("PO ITEM FINALIZATION (Inventory-Based Approach)")
    log("=" * 60)

    if args.dry_run:
        log("MODE: DRY RUN (no changes will be made)")
    else:
        log("MODE: LIVE (changes will be committed)")

    if args.limit:
        log(f"LIMIT: Processing up to {args.limit} items")

    log(f"LOG DIR: {LOG_DIR}")
    log(f"LOG FILE: {LOG_FILE}")
    log("")
    log("APPROACH: Finding inventory items with Quantity = 0")
    log("         (These are received items ready to be finalized)")
    log("")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get items to finalize
        log("Fetching items to finalize...")
        items = get_items_to_finalize(cursor, args.limit)
        log(f"Found {len(items)} items to finalize")

        if not items:
            log("\nNo items to finalize. Exiting.")
            return

        # Show summary by PO
        po_counts = {}
        for item in items:
            po_num = item['PONumber']
            po_counts[po_num] = po_counts.get(po_num, 0) + 1

        log(f"\nItems to finalize by PO ({len(po_counts)} POs):")
        for po_num, count in sorted(po_counts.items()):
            log(f"  PO# {po_num}: {count} items")

        # Confirmation
        if not args.dry_run and not args.no_confirm:
            log("\n" + "!" * 60)
            log("WARNING: This will make changes to the database!")
            log("!" * 60)
            response = input("\nType 'YES' to proceed: ")
            if response != 'YES':
                log("Aborted by user.")
                return
        elif not args.dry_run and args.no_confirm:
            log("\n[--no-confirm flag set, skipping confirmation]")

        # Start transaction
        if not args.dry_run:
            log("\nStarting transaction...")
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
            success, error = finalize_item(cursor, item, args.dry_run)
            if success:
                success_count += 1
                processed.append(item)
            else:
                skip_count += 1
                skip_reasons[error] = skip_reasons.get(error, 0) + 1
            log("")

        # Summary
        log("=" * 60)
        log("SUMMARY")
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
                # Verify before committing
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
