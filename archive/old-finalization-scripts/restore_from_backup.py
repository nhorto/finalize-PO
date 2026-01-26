"""
RESTORE DATABASE FROM BACKUP
============================
This script restores the database from the backup created before finalization.

WARNING: This will overwrite ALL current data with the backup data!

Usage:
    python restore_from_backup.py --dry-run    # Show what would happen
    python restore_from_backup.py              # Actually restore
"""

import argparse
import subprocess
import os
from datetime import datetime

BACKUP_FILE = r"C:\Users\nickb\Documents\test\backup_20260125_113946.sql"

def main():
    parser = argparse.ArgumentParser(description='Restore database from backup')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    args = parser.parse_args()

    print("=" * 60)
    print("DATABASE RESTORE")
    print("=" * 60)

    # Check if backup exists
    if not os.path.exists(BACKUP_FILE):
        print(f"ERROR: Backup file not found: {BACKUP_FILE}")
        return

    file_size = os.path.getsize(BACKUP_FILE) / (1024 * 1024 * 1024)  # GB
    print(f"Backup file: {BACKUP_FILE}")
    print(f"File size: {file_size:.2f} GB")
    print(f"")

    if args.dry_run:
        print("[DRY RUN] Would restore database from backup")
        print("[DRY RUN] This would overwrite ALL current data")
        print("")
        print("To actually restore, run without --dry-run flag")
        return

    print("!" * 60)
    print("WARNING: This will OVERWRITE all current database data!")
    print("!" * 60)
    print("")
    response = input("Type 'RESTORE' to proceed: ")

    if response != 'RESTORE':
        print("Aborted.")
        return

    print("")
    print(f"Starting restore at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This may take several minutes for a large database...")
    print("")

    # Build the mysql command
    cmd = [
        'mysql',
        '-h', 'localhost',
        '-P', '3307',
        '-u', 'admin',
        '-pYOUR_PASSWORD_HERE',  # Replace with actual password
        'YOUR_DATABASE_HERE'
    ]

    try:
        with open(BACKUP_FILE, 'r') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                text=True
            )

        if result.returncode == 0:
            print("Restore completed successfully!")
        else:
            print(f"Restore failed with error:")
            print(result.stderr)

    except Exception as e:
        print(f"Error during restore: {e}")

    print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
