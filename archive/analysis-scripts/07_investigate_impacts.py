"""
IMPACT INVESTIGATION SCRIPT
===========================
Investigate the impact of deleting inventory items, particularly item 47366.
"""
from db_config import get_connection

def main():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    print("=" * 70)
    print("IMPACT INVESTIGATION")
    print("=" * 70)

    # 1. Check if item 47366 still exists (it shouldn't)
    print("\n[1] Check if inventory item 47366 exists:")
    print("-" * 50)
    cursor.execute("SELECT * FROM inventoryitems WHERE ItemID = 47366")
    result = cursor.fetchone()
    if result:
        print("  Item 47366 EXISTS (unexpected)")
    else:
        print("  Item 47366 was DELETED (as expected)")

    # 2. Check the PO item that referenced it
    print("\n[2] PO Item 23739 (that referenced inventory item 47366):")
    print("-" * 50)
    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.OnOrderInventoryItemID,
            poi.Finalized,
            poi.Quantity,
            poi.QuantityReceived,
            po.PONumber
        FROM purchaseorderitems poi
        JOIN purchaseorders po ON poi.PurchaseOrderID = po.PurchaseOrderID
        WHERE poi.PurchaseOrderItemID = 23739
    """)
    item = cursor.fetchone()
    if item:
        print(f"  PO Item ID: {item['PurchaseOrderItemID']}")
        print(f"  PO Number: {item['PONumber']}")
        print(f"  Quantity Ordered: {item['Quantity']}")
        print(f"  Quantity Received: {item['QuantityReceived']}")
        print(f"  Remaining: {item['Quantity'] - item['QuantityReceived']}")
        print(f"  Finalized: {item['Finalized']}")
        print(f"  OnOrderInventoryItemID: {item['OnOrderInventoryItemID']}")

    # 3. Find tables that reference inventoryitems
    print("\n[3] Tables with foreign keys to inventoryitems:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE REFERENCED_TABLE_NAME = 'inventoryitems'
        AND TABLE_SCHEMA = DATABASE()
    """)
    fks = cursor.fetchall()
    if fks:
        for fk in fks:
            print(f"  {fk['TABLE_NAME']}.{fk['COLUMN_NAME']} -> inventoryitems.{fk['REFERENCED_COLUMN_NAME']}")
    else:
        print("  No explicit foreign key constraints found")

    # 4. Check columns that might reference inventory items
    print("\n[4] Checking for potential orphaned references:")
    print("-" * 50)

    # Check purchaseorderitems for references to deleted items
    deleted_ids = [47366]  # The one we know about

    # Also get all inventory IDs we deleted from the log
    print("  Note: Would need to parse log files to get all deleted IDs")

    # 5. Check inventoryitemlinks table
    print("\n[5] Checking inventoryitemlinks table:")
    print("-" * 50)
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'inventoryitemlinks' AND TABLE_SCHEMA = DATABASE()
    """)
    cols = cursor.fetchall()
    print(f"  Columns: {[c['COLUMN_NAME'] for c in cols]}")

    cursor.execute("SELECT COUNT(*) as count FROM inventoryitemlinks")
    print(f"  Total records: {cursor.fetchone()['count']}")

    # 6. Check inventorytransactions that might reference deleted items
    print("\n[6] Checking inventorytransactions table:")
    print("-" * 50)
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'inventorytransactions' AND TABLE_SCHEMA = DATABASE()
    """)
    cols = cursor.fetchall()
    inv_cols = [c['COLUMN_NAME'] for c in cols]
    print(f"  Columns with 'Inventory' or 'Item': {[c for c in inv_cols if 'inventory' in c.lower() or 'item' in c.lower()]}")

    # 7. Check for any partially received items that might have had quantity > 0
    print("\n[7] CRITICAL: Check finalization log for items with Qty > 0:")
    print("-" * 50)
    print("  From log file, item 47366 had Qty=5 (not 0)")
    print("  This suggests 5 items were still on order but we deleted the tracking record")

    # 8. Check if there are other PO items with partial receipts
    print("\n[8] Other PO items with partial receipts (Quantity != QuantityReceived):")
    print("-" * 50)
    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.Quantity,
            poi.QuantityReceived,
            poi.Finalized,
            po.PONumber
        FROM purchaseorderitems poi
        JOIN purchaseorders po ON poi.PurchaseOrderID = po.PurchaseOrderID
        WHERE poi.Quantity != poi.QuantityReceived
        AND poi.QuantityReceived > 0
        ORDER BY poi.Finalized, (poi.Quantity - poi.QuantityReceived) DESC
        LIMIT 20
    """)
    results = cursor.fetchall()
    print(f"  Found {len(results)} items with partial receipts (showing first 20):")
    for r in results:
        remaining = r['Quantity'] - r['QuantityReceived']
        status = "FINALIZED" if r['Finalized'] == 1 else "NOT FINALIZED"
        print(f"    PO# {r['PONumber']} Item {r['PurchaseOrderItemID']}: Ordered {r['Quantity']}, Received {r['QuantityReceived']}, Remaining {remaining} - {status}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    print("""
ISSUE IDENTIFIED:
- Inventory item 47366 had Quantity=5 (not 0)
- This meant 5 items were still on order
- By deleting it and finalizing the PO item, we may have:
  1. Lost track of 5 items still on order
  2. Potentially marked a partial shipment as complete

RECOMMENDED ACTION:
- The script should NOT finalize items where QuantityReceived < Quantity
- OR the script should check if the linked inventory item has Quantity > 0
""")

if __name__ == '__main__':
    main()
