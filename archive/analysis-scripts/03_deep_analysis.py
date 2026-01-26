"""
PHASE 3: Deep Analysis of Finalized vs Non-Finalized Items
==========================================================
This script is READ-ONLY - it only runs SELECT queries.

Key finding from Phase 2:
- Finalized items have: OnOrderInventoryItemID = NULL, Finalized = 1
- Non-finalized items likely have: OnOrderInventoryItemID = some ID, Finalized = 0

This script will:
1. Count finalized vs non-finalized items
2. Find items that are RECEIVED but NOT FINALIZED
3. Check if those items have OnOrderInventoryItemID pointing to inventory
4. Look at the corresponding inventory items
"""
from db_config import get_connection

def main():
    print("=" * 70)
    print("PHASE 3: Deep Analysis - Finalized vs Non-Finalized")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Count finalized vs non-finalized
    print("\n[1] Count of Finalized vs Non-Finalized PO Items:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            Finalized,
            COUNT(*) as count,
            SUM(QuantityReceived) as total_received
        FROM purchaseorderitems
        GROUP BY Finalized
    """)
    for row in cursor.fetchall():
        status = "Finalized" if row['Finalized'] == 1 else "Not Finalized"
        print(f"  {status}: {row['count']} items, {row['total_received']} total received")

    # 2. Find items that are RECEIVED but NOT FINALIZED
    print("\n[2] Items that are RECEIVED but NOT FINALIZED:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            COUNT(*) as count,
            SUM(Quantity) as total_qty,
            SUM(QuantityReceived) as total_received
        FROM purchaseorderitems
        WHERE QuantityReceived > 0 AND Finalized = 0
    """)
    row = cursor.fetchone()
    print(f"  Count: {row['count']} items")
    print(f"  Total Quantity: {row['total_qty']}")
    print(f"  Total Received: {row['total_received']}")

    # 3. Sample some received-but-not-finalized items
    print("\n[3] Sample Received-but-Not-Finalized Items:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.OnOrderInventoryItemID,
            poi.Finalized,
            poi.Quantity,
            poi.QuantityReceived,
            poi.JobNumber,
            poi.DimensionString
        FROM purchaseorderitems poi
        WHERE poi.QuantityReceived > 0 AND poi.Finalized = 0
        LIMIT 10
    """)
    samples = cursor.fetchall()
    for s in samples:
        print(f"  PO Item {s['PurchaseOrderItemID']}:")
        print(f"    PurchaseOrderID: {s['PurchaseOrderID']}")
        print(f"    OnOrderInventoryItemID: {s['OnOrderInventoryItemID']}")
        print(f"    Finalized: {s['Finalized']}")
        print(f"    Quantity: {s['Quantity']}, Received: {s['QuantityReceived']}")
        print(f"    Job: {s['JobNumber']}, Size: {s['DimensionString']}")
        print()

    # 4. Check OnOrderInventoryItemID pattern
    print("\n[4] OnOrderInventoryItemID Pattern:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            Finalized,
            COUNT(*) as total,
            SUM(CASE WHEN OnOrderInventoryItemID IS NULL THEN 1 ELSE 0 END) as null_inv_id,
            SUM(CASE WHEN OnOrderInventoryItemID IS NOT NULL THEN 1 ELSE 0 END) as has_inv_id
        FROM purchaseorderitems
        GROUP BY Finalized
    """)
    for row in cursor.fetchall():
        status = "Finalized" if row['Finalized'] == 1 else "Not Finalized"
        print(f"  {status}:")
        print(f"    Total: {row['total']}")
        print(f"    OnOrderInventoryItemID IS NULL: {row['null_inv_id']}")
        print(f"    OnOrderInventoryItemID IS NOT NULL: {row['has_inv_id']}")

    # 5. Check inventory items with OnOrder = 1
    print("\n[5] Inventory Items with OnOrder = 1:")
    print("-" * 50)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM inventoryitems
        WHERE OnOrder = 1
    """)
    row = cursor.fetchone()
    print(f"  Total inventory items with OnOrder=1: {row['count']}")

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM inventoryitems
        WHERE OnOrder = 0
    """)
    row = cursor.fetchone()
    print(f"  Total inventory items with OnOrder=0: {row['count']}")

    # 6. Cross-reference: Find inventory items linked to non-finalized PO items
    print("\n[6] Inventory Items Linked to Non-Finalized PO Items:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            inv.InventoryItemID,
            inv.OnOrder,
            inv.Quantity,
            poi.PurchaseOrderItemID,
            poi.Finalized as POItemFinalized,
            poi.QuantityReceived
        FROM inventoryitems inv
        JOIN purchaseorderitems poi ON inv.InventoryItemID = poi.OnOrderInventoryItemID
        WHERE poi.Finalized = 0
        LIMIT 10
    """)
    results = cursor.fetchall()
    if results:
        for r in results:
            print(f"  Inventory {r['InventoryItemID']}:")
            print(f"    OnOrder: {r['OnOrder']}, Quantity: {r['Quantity']}")
            print(f"    Linked to PO Item: {r['PurchaseOrderItemID']}")
            print(f"    PO Item Finalized: {r['POItemFinalized']}, Received: {r['QuantityReceived']}")
            print()
    else:
        print("  No inventory items found linked to non-finalized PO items")

    # 7. Look at what happens to inventory when PO is finalized
    print("\n[7] Sample of Finalized PO Items (for comparison):")
    print("-" * 50)
    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.OnOrderInventoryItemID,
            poi.Finalized,
            poi.Quantity,
            poi.QuantityReceived
        FROM purchaseorderitems poi
        WHERE poi.Finalized = 1 AND poi.QuantityReceived > 0
        LIMIT 5
    """)
    for s in cursor.fetchall():
        print(f"  PO Item {s['PurchaseOrderItemID']}:")
        print(f"    OnOrderInventoryItemID: {s['OnOrderInventoryItemID']}")
        print(f"    Finalized: {s['Finalized']}")
        print(f"    Quantity: {s['Quantity']}, Received: {s['QuantityReceived']}")
        print()

    # 8. Check purchaseorders.NumberOfFinalizedItems
    print("\n[8] Purchase Orders - NumberOfFinalizedItems:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            po.PurchaseOrderID,
            po.PONumber,
            po.NumberOfFinalizedItems,
            COUNT(poi.PurchaseOrderItemID) as total_items,
            SUM(CASE WHEN poi.Finalized = 1 THEN 1 ELSE 0 END) as actual_finalized
        FROM purchaseorders po
        LEFT JOIN purchaseorderitems poi ON po.PurchaseOrderID = poi.PurchaseOrderID
        GROUP BY po.PurchaseOrderID, po.PONumber, po.NumberOfFinalizedItems
        HAVING actual_finalized != NumberOfFinalizedItems OR actual_finalized > 0
        LIMIT 10
    """)
    results = cursor.fetchall()
    for r in results:
        print(f"  PO {r['PONumber']} (ID: {r['PurchaseOrderID']}):")
        print(f"    NumberOfFinalizedItems: {r['NumberOfFinalizedItems']}")
        print(f"    Total Items: {r['total_items']}")
        print(f"    Actual Finalized: {r['actual_finalized']}")
        print()

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("SUMMARY OF FINDINGS:")
    print("=" * 70)
    print("""
Based on the analysis, the finalization process appears to:

1. Set purchaseorderitems.Finalized = 1
2. Set purchaseorderitems.OnOrderInventoryItemID = NULL
3. Delete the corresponding inventory item (where OnOrder = 1)
4. Update purchaseorders.NumberOfFinalizedItems

To automate finalization, we would need to:
1. Find PO items where QuantityReceived > 0 AND Finalized = 0
2. For each item:
   a. Delete the inventory item referenced by OnOrderInventoryItemID
   b. Set OnOrderInventoryItemID = NULL
   c. Set Finalized = 1
3. Update purchaseorders.NumberOfFinalizedItems count
    """)

if __name__ == '__main__':
    main()
