from db_config import get_connection

conn = get_connection()
cursor = conn.cursor()

# Check primary key
cursor.execute("""
    SELECT COLUMN_NAME, COLUMN_KEY
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'inventoryitems' AND TABLE_SCHEMA = DATABASE()
    AND COLUMN_KEY != ''
""")
print("Inventory table keys:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check inventoryitemlinks table - might be the link
cursor.execute("""
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'inventoryitemlinks' AND TABLE_SCHEMA = DATABASE()
""")
print("\nInventoryItemLinks columns:")
for row in cursor.fetchall():
    print(f"  {row[0]}")

# Sample inventory item
print("\nSample inventory item with OnOrder=1:")
cursor.execute("""
    SELECT * FROM inventoryitems WHERE OnOrder = 1 LIMIT 1
""")
row = cursor.fetchone()
if row:
    cursor.execute("DESCRIBE inventoryitems")
    cols = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM inventoryitems WHERE OnOrder = 1 LIMIT 1")
    row = cursor.fetchone()
    for i, col in enumerate(cols):
        print(f"  {col}: {row[i]}")

cursor.close()
conn.close()
