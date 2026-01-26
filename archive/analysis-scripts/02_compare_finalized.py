"""
PHASE 2: Compare Finalized vs Non-Finalized PO Items
=====================================================
This script is READ-ONLY - it only runs SELECT queries.

Goals:
1. Find PO items that are finalized
2. Find PO items that are NOT finalized but have been received
3. Compare the differences
4. Understand what changes when an item is finalized
"""
from db_config import get_connection, run_query, run_query_raw
import json

def main():
    print("=" * 70)
    print("PHASE 2: Comparing Finalized vs Non-Finalized PO Items")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # First, let's find the right table names
    print("\n[1] Finding relevant tables...")
    print("-" * 50)

    cursor.execute("SHOW TABLES")
    all_tables = [list(row.values())[0] for row in cursor.fetchall()]

    # Look for purchase order item tables
    po_item_tables = [t for t in all_tables if 'purchaseorder' in t.lower() and 'item' in t.lower()]
    print(f"  PO Item tables found: {po_item_tables}")

    # Look for inventory tables
    inv_tables = [t for t in all_tables if 'inventor' in t.lower()]
    print(f"  Inventory tables found: {inv_tables[:5]}...")  # First 5

    # Step 2: Check the structure of the main PO item table
    if po_item_tables:
        main_po_table = po_item_tables[0]
        print(f"\n[2] Structure of '{main_po_table}':")
        print("-" * 50)

        cursor.execute(f"DESCRIBE `{main_po_table}`")
        columns_info = cursor.fetchall()
        for col in columns_info:
            col_name = col.get('Field', col.get('field', ''))
            col_type = col.get('Type', col.get('type', ''))
            print(f"  {col_name:40} {col_type}")

    # Step 3: Sample some PO items to understand the data
    print(f"\n[3] Sample PO Items:")
    print("-" * 50)

    # Try to find a table with Finalized field
    for table in po_item_tables:
        cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table}'
            AND COLUMN_NAME LIKE '%final%'
        """)
        final_cols = cursor.fetchall()
        if final_cols:
            print(f"  Found 'final' column in {table}: {[c['COLUMN_NAME'] for c in final_cols]}")

            # Get some samples
            cursor.execute(f"SELECT * FROM `{table}` LIMIT 5")
            samples = cursor.fetchall()
            for i, sample in enumerate(samples):
                print(f"\n  Sample {i+1}:")
                for key, value in sample.items():
                    print(f"    {key}: {value}")

    # Step 4: Look for quantity received vs finalized
    print(f"\n[4] Looking for Received but NOT Finalized items:")
    print("-" * 50)

    # Search for tables with both QuantityReceived and Finalized columns
    cursor.execute("""
        SELECT TABLE_NAME,
               GROUP_CONCAT(COLUMN_NAME) as columns
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND (COLUMN_NAME LIKE '%received%' OR COLUMN_NAME LIKE '%final%' OR COLUMN_NAME LIKE '%quantity%')
        GROUP BY TABLE_NAME
        HAVING columns LIKE '%received%' OR columns LIKE '%final%'
    """)
    relevant_tables = cursor.fetchall()
    for row in relevant_tables:
        print(f"  {row['TABLE_NAME']}: {row['columns']}")

    # Step 5: Check inventory for OnOrder items
    print(f"\n[5] Checking Inventory tables for OnOrder field:")
    print("-" * 50)

    for table in inv_tables[:5]:
        cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table}'
            AND (COLUMN_NAME LIKE '%onorder%' OR COLUMN_NAME LIKE '%on_order%' OR COLUMN_NAME LIKE '%purchaseorder%')
        """)
        cols = cursor.fetchall()
        if cols:
            col_names = [c['COLUMN_NAME'] for c in cols]
            print(f"  {table}: {col_names}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("Phase 2 Complete - All queries were READ-ONLY")
    print("=" * 70)

if __name__ == '__main__':
    main()
