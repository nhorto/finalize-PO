"""
Test database connection
"""
from db_config import get_connection

def main():
    print("Testing database connection...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"Connection successful! Test query returned: {result[0]}")

        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()")
        table_count = cursor.fetchone()[0]
        print(f"Database has {table_count} tables")

        cursor.close()
        conn.close()
        print("Connection closed.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == '__main__':
    main()
