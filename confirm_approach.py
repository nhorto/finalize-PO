"""
Confirm New Inventory-Based Approach
====================================
This script validates the new simpler approach:
1. Find inventory items with Quantity = 0
2. Join back to PO items via OnOrderInventoryItemID
3. Show what would be finalized

This is READ-ONLY - no changes are made.
"""
from db_config import get_connection, run_query

def main():
    print("=" * 70)
    print("CONFIRMING NEW INVENTORY-BASED APPROACH")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Step 1: Find ALL inventory items with Quantity = 0
    print("\n[1] Finding ALL inventory items with Quantity = 0...")
    print("-" * 50)

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM inventoryitems
        WHERE Quantity = 0
    """)
    result = cursor.fetchone()
    print(f"  Total inventory items with Quantity = 0: {result['count']}")

    # Step 2: Break down by OnOrder flag to understand the data
    print("\n[2] Breaking down by OnOrder flag...")
    print("-" * 50)

    cursor.execute("""
        SELECT OnOrder, COUNT(*) as count
        FROM inventoryitems
        WHERE Quantity = 0
        GROUP BY OnOrder
    """)
    results = cursor.fetchall()
    for row in results:
        on_order_label = "Yes (placeholder)" if row['OnOrder'] == 1 else "No (real inventory)"
        print(f"  OnOrder = {row['OnOrder']} ({on_order_label}): {row['count']}")

    # Step 3: Find items linked to PO items (via OnOrderInventoryItemID)
    print("\n[3] Finding items linked to PO items...")
    print("-" * 50)

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        WHERE inv.Quantity = 0
    """)
    result = cursor.fetchone()
    print(f"  Inventory items (Qty=0) linked to PO items: {result['count']}")

    # Step 4: Filter to NOT yet finalized (Finalized = 0 OR NULL)
    print("\n[4] Filtering to NOT yet finalized PO items...")
    print("-" * 50)

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        WHERE inv.Quantity = 0
          AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
    """)
    result = cursor.fetchone()
    print(f"  Items to finalize (Qty=0, not finalized): {result['count']}")

    # Step 4: Show the full query with PO details
    print("\n[4] Full details of items to finalize...")
    print("-" * 50)

    cursor.execute("""
        SELECT
            inv.ItemID as InventoryItemID,
            inv.Quantity as InvQuantity,
            inv.OnOrder,
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.Finalized,
            poi.Quantity as OrderedQty,
            poi.QuantityReceived,
            po.PONumber
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        INNER JOIN purchaseorders po ON po.PurchaseOrderID = poi.PurchaseOrderID
        WHERE inv.Quantity = 0
          AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
        ORDER BY po.PONumber, poi.PurchaseOrderItemID
        LIMIT 20
    """)

    items = cursor.fetchall()

    if items:
        print(f"\n  Showing first {len(items)} items:\n")
        print(f"  {'PO#':<12} {'InvItemID':<12} {'POItemID':<12} {'Ordered':<10} {'Received':<10} {'InvQty':<8}")
        print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*10} {'-'*10} {'-'*8}")

        for item in items:
            print(f"  {item['PONumber']:<12} {item['InventoryItemID']:<12} {item['PurchaseOrderItemID']:<12} "
                  f"{item['OrderedQty']:<10} {item['QuantityReceived']:<10} {item['InvQuantity']:<8}")
    else:
        print("  No items found to finalize!")

    # Step 5: Group by PO to see distribution
    print("\n[5] Items to finalize grouped by PO...")
    print("-" * 50)

    cursor.execute("""
        SELECT
            po.PONumber,
            COUNT(*) as ItemCount
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        INNER JOIN purchaseorders po ON po.PurchaseOrderID = poi.PurchaseOrderID
        WHERE inv.Quantity = 0
          AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
        GROUP BY po.PONumber
        ORDER BY ItemCount DESC
        LIMIT 20
    """)

    po_groups = cursor.fetchall()

    if po_groups:
        print(f"\n  {'PO#':<15} {'Items to Finalize':<20}")
        print(f"  {'-'*15} {'-'*20}")
        for po in po_groups:
            print(f"  {po['PONumber']:<15} {po['ItemCount']:<20}")

    # Step 6: Sanity check - verify these items have been received
    print("\n[6] Sanity check: Verify all items have been received...")
    print("-" * 50)

    cursor.execute("""
        SELECT
            CASE
                WHEN poi.QuantityReceived >= poi.Quantity THEN 'Fully Received'
                WHEN poi.QuantityReceived > 0 THEN 'Partially Received'
                ELSE 'Not Received'
            END as ReceiveStatus,
            COUNT(*) as Count
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        WHERE inv.Quantity = 0
          AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
        GROUP BY ReceiveStatus
    """)

    status_groups = cursor.fetchall()

    for status in status_groups:
        print(f"  {status['ReceiveStatus']}: {status['Count']} items")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
The new approach finds items by:
  1. Looking at inventoryitems WHERE Quantity = 0
  2. Joining to purchaseorderitems via OnOrderInventoryItemID
  3. Filtering to Finalized = 0 (not yet finalized)

This is simpler than the old approach because:
  - We start from inventory (what the user sees in the UI)
  - Zero quantity = received and ready to finalize
  - No need for complex QuantityReceived >= Quantity checks
""")
    print("=" * 70)

if __name__ == '__main__':
    main()
