from db_config import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'inventoryitems' AND TABLE_SCHEMA = DATABASE()
""")
print("Inventory table columns:")
for row in cursor.fetchall():
    print(f"  {row[0]}")

cursor.close()
conn.close()
