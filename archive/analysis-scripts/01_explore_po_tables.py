"""
PHASE 1: Explore Purchase Order Related Tables
==============================================
This script is READ-ONLY - it only runs SELECT queries.

Goals:
1. Find all tables related to Purchase Orders
2. Find all tables related to Inventory
3. Understand the structure of these tables
4. Look for "Finalized" or similar fields
"""
from db_config import get_connection, run_query, run_query_raw

def main():
    print("=" * 70)
    print("PHASE 1: Exploring Purchase Order Tables")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor()

    # Step 1: Find all tables with "purchase" in the name
    print("\n[1] Tables containing 'purchase':")
    print("-" * 50)
    cursor.execute("SHOW TABLES LIKE '%purchase%'")
    purchase_tables = [row[0] for row in cursor.fetchall()]
    for table in purchase_tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")

    # Step 2: Find all tables with "inventory" in the name
    print("\n[2] Tables containing 'inventory':")
    print("-" * 50)
    cursor.execute("SHOW TABLES LIKE '%inventory%'")
    inventory_tables = [row[0] for row in cursor.fetchall()]
    for table in inventory_tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")

    # Step 3: Find tables with "order" in the name
    print("\n[3] Tables containing 'order':")
    print("-" * 50)
    cursor.execute("SHOW TABLES LIKE '%order%'")
    order_tables = [row[0] for row in cursor.fetchall()]
    for table in order_tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")

    # Step 4: Look for "finalize" in any column name
    print("\n[4] Searching for 'finalize' in column names:")
    print("-" * 50)
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND COLUMN_NAME LIKE '%finalize%'
    """)
    finalize_cols = cursor.fetchall()
    if finalize_cols:
        for row in finalize_cols:
            print(f"  {row[0]}.{row[1]} ({row[2]})")
    else:
        print("  No columns found with 'finalize' in the name")

    # Step 5: Look for "final" in any column name (broader search)
    print("\n[5] Searching for 'final' in column names:")
    print("-" * 50)
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND COLUMN_NAME LIKE '%final%'
    """)
    final_cols = cursor.fetchall()
    if final_cols:
        for row in final_cols:
            print(f"  {row[0]}.{row[1]} ({row[2]})")
    else:
        print("  No columns found with 'final' in the name")

    # Step 6: Describe the main purchase order tables if they exist
    if purchase_tables:
        for table in purchase_tables[:3]:  # First 3 tables
            print(f"\n[6] Structure of '{table}':")
            print("-" * 50)
            cursor.execute(f"DESCRIBE `{table}`")
            for row in cursor.fetchall():
                print(f"  {row[0]:40} {str(row[1]):20} Null:{row[2]} Key:{row[3]}")

    # Step 7: Look for "onorder" or "on_order" columns
    print("\n[7] Searching for 'onorder' or 'on_order' columns:")
    print("-" * 50)
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND (COLUMN_NAME LIKE '%onorder%' OR COLUMN_NAME LIKE '%on_order%')
    """)
    onorder_cols = cursor.fetchall()
    if onorder_cols:
        for row in onorder_cols:
            print(f"  {row[0]}.{row[1]} ({row[2]})")
    else:
        print("  No columns found")

    # Step 8: Look for "received" columns
    print("\n[8] Searching for 'received' columns:")
    print("-" * 50)
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND COLUMN_NAME LIKE '%received%'
        ORDER BY TABLE_NAME
    """)
    received_cols = cursor.fetchall()
    if received_cols:
        for row in received_cols:
            print(f"  {row[0]}.{row[1]} ({row[2]})")
    else:
        print("  No columns found")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("Phase 1 Complete - All queries were READ-ONLY")
    print("=" * 70)

if __name__ == '__main__':
    main()
