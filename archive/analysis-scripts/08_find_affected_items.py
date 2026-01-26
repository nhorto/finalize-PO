"""
FIND AFFECTED ITEMS
===================
Find all items that were finalized by our script but had partial receipts.
"""
from db_config import get_connection

def main():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    print("=" * 70)
    print("FINDING ITEMS INCORRECTLY FINALIZED")
    print("=" * 70)

    # Find all finalized items where Quantity != QuantityReceived
    # These are potential problems
    print("\n[1] Finalized items with Quantity != QuantityReceived:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.Quantity,
            poi.QuantityReceived,
            poi.Finalized,
            poi.OnOrderInventoryItemID,
            po.PONumber
        FROM purchaseorderitems poi
        JOIN purchaseorders po ON poi.PurchaseOrderID = po.PurchaseOrderID
        WHERE poi.Finalized = 1
        AND poi.Quantity != poi.QuantityReceived
        AND poi.QuantityReceived > 0
        ORDER BY (poi.Quantity - poi.QuantityReceived) DESC
    """)
    results = cursor.fetchall()

    partial_finalized = []
    over_received = []

    for r in results:
        remaining = r['Quantity'] - r['QuantityReceived']
        if remaining > 0:
            partial_finalized.append(r)
        else:
            over_received.append(r)

    print(f"\n  Items finalized with REMAINING quantity on order: {len(partial_finalized)}")
    for r in partial_finalized:
        remaining = r['Quantity'] - r['QuantityReceived']
        print(f"    PO# {r['PONumber']} Item {r['PurchaseOrderItemID']}: Ordered {r['Quantity']}, Received {r['QuantityReceived']}, REMAINING: {remaining}")

    print(f"\n  Items finalized with OVER-receipt (received > ordered): {len(over_received)}")
    for r in over_received[:10]:  # Just show first 10
        over = r['QuantityReceived'] - r['Quantity']
        print(f"    PO# {r['PONumber']} Item {r['PurchaseOrderItemID']}: Ordered {r['Quantity']}, Received {r['QuantityReceived']}, OVER: {over}")
    if len(over_received) > 10:
        print(f"    ... and {len(over_received) - 10} more")

    # Check which of the partial finalized items might have been done by our script
    # (items that now have OnOrderInventoryItemID = NULL and were recently finalized)
    print("\n[2] Summary of potential issues:")
    print("-" * 50)
    print(f"  Total finalized with remaining qty: {len(partial_finalized)}")

    total_remaining = sum(r['Quantity'] - r['QuantityReceived'] for r in partial_finalized)
    print(f"  Total items still on order (but marked finalized): {total_remaining}")

    print("\n  These items may need to be un-finalized or have their inventory records restored.")

    # Get details for remediation
    print("\n[3] Items needing potential remediation:")
    print("-" * 50)
    for r in partial_finalized:
        remaining = r['Quantity'] - r['QuantityReceived']
        print(f"\n  PO Item {r['PurchaseOrderItemID']}:")
        print(f"    PO#: {r['PONumber']}")
        print(f"    Ordered: {r['Quantity']}")
        print(f"    Received: {r['QuantityReceived']}")
        print(f"    Remaining on order: {remaining}")
        print(f"    OnOrderInventoryItemID: {r['OnOrderInventoryItemID']}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print("""
For these items, we have two options:

OPTION 1: Accept as-is (if items won't be received)
  - If the remaining items will never arrive, the finalization is acceptable
  - The business should confirm if these partial orders are complete

OPTION 2: Revert finalization (if items will still arrive)
  - Set Finalized = 0
  - Re-create the inventory placeholder item with OnOrder=1 and Quantity=[remaining]
  - Update OnOrderInventoryItemID to point to the new inventory item
  - Decrement purchaseorders.NumberOfFinalizedItems

IMPORTANT: Check with the business to understand the correct action.
""")

if __name__ == '__main__':
    main()
