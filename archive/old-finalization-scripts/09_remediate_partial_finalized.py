"""
REMEDIATION SCRIPT
==================
Reverts finalization for items that were finalized but had partial receipts.

This script will:
1. Create new inventory placeholder items for the remaining quantity
2. Update the PO items to be NOT finalized
3. Link the PO items to the new inventory items
4. Decrement the NumberOfFinalizedItems counter

USE WITH CAUTION: Only run this if you need to un-finalize items.
"""

import argparse
from datetime import datetime
from db_config import get_connection

LOG_FILE = f"remediation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def log(message, also_print=True):
    """Log message to file and optionally print to console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')
    if also_print:
        print(log_line)

def get_affected_items(cursor):
    """Get items that are finalized but have remaining quantity."""
    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.OnOrderInventoryItemID,
            poi.Quantity,
            poi.QuantityReceived,
            poi.ShapeID,
            poi.GradeID,
            poi.SizeID,
            poi.JobNumber,
            poi.DimensionString,
            po.PONumber
        FROM purchaseorderitems poi
        JOIN purchaseorders po ON poi.PurchaseOrderID = po.PurchaseOrderID
        WHERE poi.Finalized = 1
        AND poi.QuantityReceived < poi.Quantity
        AND poi.QuantityReceived > 0
        AND poi.OnOrderInventoryItemID IS NULL
        ORDER BY poi.PurchaseOrderID, poi.PurchaseOrderItemID
    """)
    return cursor.fetchall()

def get_sample_inventory_item(cursor):
    """Get a sample on-order inventory item to understand the structure."""
    cursor.execute("""
        SELECT *
        FROM inventoryitems
        WHERE OnOrder = 1
        LIMIT 1
    """)
    return cursor.fetchone()

def create_inventory_placeholder(cursor, po_item, remaining_qty):
    """Create a new inventory placeholder item for the remaining quantity."""
    # Insert a minimal placeholder record matching the PO item's material
    cursor.execute("""
        INSERT INTO inventoryitems (
            OnOrder,
            Quantity,
            ShapeID,
            GradeID,
            SizeID,
            DimensionString,
            Job,
            OriginalJob,
            Stock,
            Reorder
        ) VALUES (
            1,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            0,
            0
        )
    """, (
        remaining_qty,
        po_item.get('ShapeID'),
        po_item.get('GradeID'),
        po_item.get('SizeID'),
        po_item.get('DimensionString'),
        po_item.get('JobNumber'),
        po_item.get('JobNumber')
    ))

    # Get the auto-generated ItemID
    cursor.execute("SELECT LAST_INSERT_ID() as new_id")
    return cursor.fetchone()['new_id']

def remediate_item(cursor, item, dry_run=False):
    """Remediate a single incorrectly finalized item."""
    po_item_id = item['PurchaseOrderItemID']
    po_id = item['PurchaseOrderID']
    po_number = item['PONumber']
    qty_ordered = item['Quantity']
    qty_received = item['QuantityReceived']
    remaining = qty_ordered - qty_received

    log(f"  Processing PO Item {po_item_id} (PO# {po_number})")
    log(f"    - Ordered: {qty_ordered}, Received: {qty_received}, Remaining: {remaining}")

    if dry_run:
        log(f"    [DRY RUN] Would create new inventory item with Qty={remaining}, OnOrder=1")
        log(f"    [DRY RUN] Would update PO item {po_item_id}: Finalized=0, OnOrderInventoryItemID=<new_id>")
        log(f"    [DRY RUN] Would decrement NumberOfFinalizedItems for PO {po_id}")
        return True

    # Step 1: Create new inventory placeholder
    log(f"    Step 1: Creating inventory placeholder (Qty={remaining}, OnOrder=1)")
    new_inv_id = create_inventory_placeholder(cursor, item, remaining)
    log(f"    Created inventory item {new_inv_id}")

    # Step 2: Update PO item
    log(f"    Step 2: Updating PO item {po_item_id}")
    cursor.execute("""
        UPDATE purchaseorderitems
        SET Finalized = 0, OnOrderInventoryItemID = %s
        WHERE PurchaseOrderItemID = %s
    """, (new_inv_id, po_item_id))

    # Step 3: Decrement NumberOfFinalizedItems
    log(f"    Step 3: Decrementing NumberOfFinalizedItems for PO {po_id}")
    cursor.execute("""
        UPDATE purchaseorders
        SET NumberOfFinalizedItems = NumberOfFinalizedItems - 1
        WHERE PurchaseOrderID = %s
    """, (po_id,))

    log(f"    SUCCESS: PO Item {po_item_id} remediated")
    return True

def main():
    parser = argparse.ArgumentParser(description='Remediate incorrectly finalized partial receipts')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would happen without making changes')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Skip confirmation prompt')
    parser.add_argument('--po-item-id', type=int,
                        help='Only remediate a specific PO item ID')
    args = parser.parse_args()

    log("=" * 60)
    log("PARTIAL RECEIPT REMEDIATION SCRIPT")
    log("=" * 60)

    if args.dry_run:
        log("MODE: DRY RUN (no changes will be made)")
    else:
        log("MODE: LIVE (changes will be committed)")

    log(f"LOG FILE: {LOG_FILE}")
    log("")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get affected items
        log("Finding items that need remediation...")
        items = get_affected_items(cursor)

        if args.po_item_id:
            items = [i for i in items if i['PurchaseOrderItemID'] == args.po_item_id]

        log(f"Found {len(items)} items to remediate")

        if not items:
            log("\nNo items need remediation. Exiting.")
            return

        log("\nItems to remediate:")
        total_remaining = 0
        for item in items:
            remaining = item['Quantity'] - item['QuantityReceived']
            total_remaining += remaining
            log(f"  PO# {item['PONumber']} Item {item['PurchaseOrderItemID']}: {remaining} remaining")

        log(f"\nTotal items to restore to on-order: {total_remaining}")

        if not args.dry_run and not args.no_confirm:
            log("\n" + "!" * 60)
            log("WARNING: This will create new inventory records!")
            log("!" * 60)
            response = input("Type 'YES' to proceed: ")
            if response != 'YES':
                log("Aborted by user.")
                return
        elif not args.dry_run and args.no_confirm:
            log("\n[--no-confirm flag set, skipping confirmation]")

        if not args.dry_run:
            log("\nStarting transaction...")
            conn.autocommit = False

        # Process each item
        log("\n" + "-" * 60)
        log("PROCESSING ITEMS")
        log("-" * 60)

        success_count = 0
        for item in items:
            if remediate_item(cursor, item, args.dry_run):
                success_count += 1
            log("")

        # Summary
        log("=" * 60)
        log("SUMMARY")
        log("=" * 60)
        log(f"Total items processed: {success_count}")

        if args.dry_run:
            log("\n[DRY RUN] No changes were made to the database.")
        else:
            log("\nCommitting transaction...")
            conn.commit()
            log("Transaction committed successfully!")

    except Exception as e:
        log(f"\nERROR: {str(e)}")
        import traceback
        log(traceback.format_exc())
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
