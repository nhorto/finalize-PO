"""
Investigate Database State
==========================
Figure out why inventory items exist but PO items show Finalized = 1
"""
from db_config import get_connection

def main():
    print("=" * 70)
    print("INVESTIGATING DATABASE STATE")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Check 1: What's the Finalized status of PO items linked to these inventory items?
    print("\n[1] Finalized status of PO items linked to Qty=0 inventory items...")
    print("-" * 50)

    cursor.execute("""
        SELECT
            poi.Finalized,
            COUNT(*) as count
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        WHERE inv.Quantity = 0
        GROUP BY poi.Finalized
    """)
    results = cursor.fetchall()
    for row in results:
        status = "Finalized" if row['Finalized'] == 1 else "Not Finalized"
        print(f"  Finalized = {row['Finalized']} ({status}): {row['count']} items")

    # Check 2: Are there inventory items with Qty=0 that are NOT linked to any PO item?
    print("\n[2] Inventory items (Qty=0) NOT linked to any PO item...")
    print("-" * 50)

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM inventoryitems inv
        LEFT JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        WHERE inv.Quantity = 0
          AND poi.PurchaseOrderItemID IS NULL
    """)
    result = cursor.fetchone()
    print(f"  Orphaned inventory items (no PO link): {result['count']}")

    # Check 3: Show sample of the linked items to understand the state
    print("\n[3] Sample of inventory items linked to FINALIZED PO items...")
    print("-" * 50)

    cursor.execute("""
        SELECT
            inv.ItemID as InvItemID,
            inv.Quantity as InvQty,
            inv.OnOrder,
            poi.PurchaseOrderItemID,
            poi.Finalized,
            poi.OnOrderInventoryItemID,
            po.PONumber
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        INNER JOIN purchaseorders po ON po.PurchaseOrderID = poi.PurchaseOrderID
        WHERE inv.Quantity = 0
          AND poi.Finalized = 1
        LIMIT 10
    """)
    items = cursor.fetchall()

    if items:
        print(f"\n  {'InvItemID':<12} {'PONumber':<12} {'POItemID':<12} {'Finalized':<10} {'OnOrderInvID':<15}")
        print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*10} {'-'*15}")
        for item in items:
            print(f"  {item['InvItemID']:<12} {item['PONumber']:<12} {item['PurchaseOrderItemID']:<12} {item['Finalized']:<10} {item['OnOrderInventoryItemID']:<15}")

        print("\n  OBSERVATION: These PO items have Finalized=1 but still have")
        print("  OnOrderInventoryItemID pointing to existing inventory items.")
        print("  This is inconsistent - finalization should set this to NULL")
        print("  and delete the inventory item.")

    # Check 4: What SHOULD finalization look like? Show a properly finalized item
    print("\n[4] Example of PROPERLY finalized PO items (OnOrderInventoryItemID = NULL)...")
    print("-" * 50)

    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.Finalized,
            poi.OnOrderInventoryItemID,
            po.PONumber
        FROM purchaseorderitems poi
        INNER JOIN purchaseorders po ON po.PurchaseOrderID = poi.PurchaseOrderID
        WHERE poi.Finalized = 1
          AND poi.OnOrderInventoryItemID IS NULL
        LIMIT 5
    """)
    proper_items = cursor.fetchall()

    if proper_items:
        print(f"\n  {'PONumber':<12} {'POItemID':<12} {'Finalized':<10} {'OnOrderInvID':<15}")
        print(f"  {'-'*12} {'-'*12} {'-'*10} {'-'*15}")
        for item in proper_items:
            inv_id = item['OnOrderInventoryItemID'] if item['OnOrderInventoryItemID'] else "NULL"
            print(f"  {item['PONumber']:<12} {item['PurchaseOrderItemID']:<12} {item['Finalized']:<10} {inv_id:<15}")
        print("\n  These are properly finalized - OnOrderInventoryItemID is NULL.")
    else:
        print("  No properly finalized items found (all have OnOrderInventoryItemID set)")

    # Summary
    print("\n" + "=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    print("""
The issue: PO items are marked Finalized=1 but:
  - OnOrderInventoryItemID is NOT NULL (still points to inventory)
  - The inventory items still exist (should have been deleted)

This is an INCOMPLETE finalization state. The question is:
  Should we just delete these orphaned inventory items?

If yes, we can modify the script to:
  1. Find inventory items with Quantity = 0
  2. Delete them directly (they're placeholders that should be gone)
  3. Optionally also set OnOrderInventoryItemID = NULL on the PO items
""")
    print("=" * 70)

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
