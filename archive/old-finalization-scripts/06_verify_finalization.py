"""
VERIFICATION SCRIPT
===================
Verify that finalization was successful for specific PO items.
This is a READ-ONLY script.
"""
import argparse
from db_config import get_connection

def main():
    parser = argparse.ArgumentParser(description='Verify finalization results')
    parser.add_argument('--po-id', type=int, help='Check specific PO ID')
    parser.add_argument('--po-item-id', type=int, help='Check specific PO Item ID')
    parser.add_argument('--summary', action='store_true', help='Show summary of all items')
    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    print("=" * 60)
    print("FINALIZATION VERIFICATION")
    print("=" * 60)

    if args.po_item_id:
        # Check specific PO item
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
            WHERE poi.PurchaseOrderItemID = %s
        """, (args.po_item_id,))
        item = cursor.fetchone()

        if item:
            print(f"\nPO Item {item['PurchaseOrderItemID']}:")
            print(f"  PO Number: {item['PONumber']}")
            print(f"  Finalized: {'YES' if item['Finalized'] == 1 else 'NO'}")
            print(f"  OnOrderInventoryItemID: {item['OnOrderInventoryItemID']}")
            print(f"  Quantity: {item['Quantity']}, Received: {item['QuantityReceived']}")

            if item['OnOrderInventoryItemID']:
                cursor.execute("SELECT * FROM inventoryitems WHERE ItemID = %s",
                             (item['OnOrderInventoryItemID'],))
                inv = cursor.fetchone()
                if inv:
                    print(f"  Linked inventory item EXISTS (OnOrder={inv['OnOrder']}, Qty={inv['Quantity']})")
                else:
                    print(f"  Linked inventory item DELETED")
        else:
            print(f"PO Item {args.po_item_id} not found")

    elif args.po_id:
        # Check all items on a specific PO
        cursor.execute("""
            SELECT
                poi.PurchaseOrderItemID,
                poi.OnOrderInventoryItemID,
                poi.Finalized,
                poi.Quantity,
                poi.QuantityReceived
            FROM purchaseorderitems poi
            WHERE poi.PurchaseOrderID = %s
            ORDER BY poi.PurchaseOrderItemID
        """, (args.po_id,))
        items = cursor.fetchall()

        cursor.execute("""
            SELECT PONumber, NumberOfFinalizedItems
            FROM purchaseorders WHERE PurchaseOrderID = %s
        """, (args.po_id,))
        po = cursor.fetchone()

        print(f"\nPO# {po['PONumber']} (ID: {args.po_id})")
        print(f"NumberOfFinalizedItems: {po['NumberOfFinalizedItems']}")
        print(f"\nItems ({len(items)} total):")
        print("-" * 50)

        finalized_count = 0
        for item in items:
            status = "FINALIZED" if item['Finalized'] == 1 else "NOT FINALIZED"
            if item['Finalized'] == 1:
                finalized_count += 1
            inv_status = ""
            if item['OnOrderInventoryItemID']:
                cursor.execute("SELECT ItemID FROM inventoryitems WHERE ItemID = %s",
                             (item['OnOrderInventoryItemID'],))
                if cursor.fetchone():
                    inv_status = f"(inv {item['OnOrderInventoryItemID']} exists)"
                else:
                    inv_status = f"(inv {item['OnOrderInventoryItemID']} MISSING!)"
            print(f"  Item {item['PurchaseOrderItemID']}: {status} {inv_status}")

        print(f"\nActual finalized count: {finalized_count}")
        if finalized_count == po['NumberOfFinalizedItems']:
            print("COUNT MATCHES!")
        else:
            print(f"COUNT MISMATCH! Header says {po['NumberOfFinalizedItems']}")

    elif args.summary:
        # Show overall summary
        print("\n[Overall Summary]")
        print("-" * 50)

        cursor.execute("""
            SELECT COUNT(*) as count FROM purchaseorderitems WHERE Finalized = 1
        """)
        print(f"Total finalized PO items: {cursor.fetchone()['count']}")

        cursor.execute("""
            SELECT COUNT(*) as count FROM purchaseorderitems WHERE Finalized = 0
        """)
        print(f"Total non-finalized PO items: {cursor.fetchone()['count']}")

        cursor.execute("""
            SELECT COUNT(*) as count FROM purchaseorderitems
            WHERE QuantityReceived > 0 AND Finalized = 0
        """)
        remaining = cursor.fetchone()['count']
        print(f"Items still needing finalization: {remaining}")

        cursor.execute("""
            SELECT COUNT(*) as count FROM inventoryitems WHERE OnOrder = 1
        """)
        print(f"On-order inventory items: {cursor.fetchone()['count']}")

    else:
        print("Use --po-id, --po-item-id, or --summary to specify what to check")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
