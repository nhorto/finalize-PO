"""
FINALIZATION SUMMARY & VERIFICATION
===================================
This script summarizes what we've learned and verifies the finalization logic.
"""
from db_config import get_connection

def main():
    print("=" * 70)
    print("FINALIZATION PROCESS SUMMARY")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Items needing finalization
    print("\n[1] PO Items Needing Finalization (Received but not Finalized):")
    print("-" * 50)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM purchaseorderitems
        WHERE QuantityReceived > 0 AND Finalized = 0
    """)
    row = cursor.fetchone()
    print(f"  Total items to finalize: {row['count']}")

    # 2. Verify link between PO items and inventory
    print("\n[2] Verifying PO Item -> Inventory Link:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            poi.PurchaseOrderItemID,
            poi.OnOrderInventoryItemID,
            inv.ItemID as InvItemID,
            inv.OnOrder,
            inv.Quantity as InvQuantity,
            poi.QuantityReceived
        FROM purchaseorderitems poi
        JOIN inventoryitems inv ON poi.OnOrderInventoryItemID = inv.ItemID
        WHERE poi.QuantityReceived > 0 AND poi.Finalized = 0
        LIMIT 5
    """)
    results = cursor.fetchall()
    print(f"  Found {len(results)} linked items (showing first 5):")
    for r in results:
        print(f"    PO Item {r['PurchaseOrderItemID']} -> Inventory {r['InvItemID']}")
        print(f"      Inventory OnOrder={r['OnOrder']}, Qty={r['InvQuantity']}")
        print(f"      PO Item Received={r['QuantityReceived']}")

    # 3. Count inventory items that would be deleted
    print("\n[3] Inventory Items That Would Be Deleted:")
    print("-" * 50)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM inventoryitems inv
        JOIN purchaseorderitems poi ON inv.ItemID = poi.OnOrderInventoryItemID
        WHERE poi.QuantityReceived > 0 AND poi.Finalized = 0
    """)
    row = cursor.fetchone()
    print(f"  Inventory items to delete: {row['count']}")

    # 4. Purchase orders affected
    print("\n[4] Purchase Orders Affected:")
    print("-" * 50)
    cursor.execute("""
        SELECT
            po.PurchaseOrderID,
            po.PONumber,
            po.NumberOfFinalizedItems,
            COUNT(poi.PurchaseOrderItemID) as items_to_finalize
        FROM purchaseorders po
        JOIN purchaseorderitems poi ON po.PurchaseOrderID = poi.PurchaseOrderID
        WHERE poi.QuantityReceived > 0 AND poi.Finalized = 0
        GROUP BY po.PurchaseOrderID, po.PONumber, po.NumberOfFinalizedItems
        ORDER BY items_to_finalize DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    print(f"  POs with items to finalize (top 10):")
    for r in results:
        print(f"    PO {r['PONumber']}: {r['items_to_finalize']} items to finalize (currently {r['NumberOfFinalizedItems']} finalized)")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("FINALIZATION STEPS (What the script will do):")
    print("=" * 70)
    print("""
For each PO Item where QuantityReceived > 0 AND Finalized = 0:

  1. DELETE FROM inventoryitems
     WHERE ItemID = [OnOrderInventoryItemID]

  2. UPDATE purchaseorderitems
     SET Finalized = 1, OnOrderInventoryItemID = NULL
     WHERE PurchaseOrderItemID = [PurchaseOrderItemID]

  3. UPDATE purchaseorders
     SET NumberOfFinalizedItems = NumberOfFinalizedItems + 1
     WHERE PurchaseOrderID = [PurchaseOrderID]

IMPORTANT NOTES:
- This should be run in a TRANSACTION so it can be rolled back if needed
- Log tables (purchaseorderitemslog, inventoryitemslog) may need entries
- There may be triggers that handle some of this automatically
- TEST ON BACKUP FIRST before running on production
    """)

if __name__ == '__main__':
    main()
