"""
PO Finalize Tool - GUI Version
===============================
A graphical interface for finalizing PO items in Tekla PowerFab.

Double-click to run. No command line needed.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import sys
import json
from datetime import datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_app_directory():
    """Get the directory where the app is running from (.exe or .py)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(get_app_directory(), 'config.json')

def get_log_path():
    """Create and return path for log file."""
    logs_dir = os.path.join(get_app_directory(), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    today = datetime.now().strftime('%Y-%m-%d')
    run_num = 1
    while True:
        run_dir = os.path.join(logs_dir, f"{today}_run{run_num}")
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
            break
        run_num += 1

    timestamp = datetime.now().strftime('%H%M%S')
    log_file = os.path.join(run_dir, f"finalization_{timestamp}.txt")
    return log_file

# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def get_connection(host, port, user, password, database):
    """Create a database connection from provided settings."""
    import mysql.connector
    return mysql.connector.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        use_pure=True,
    )

def find_items_to_finalize(conn):
    """Find all inventory items with Quantity=0 linked to non-finalized PO items."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            inv.ItemID as InventoryItemID,
            inv.Quantity as InvQuantity,
            inv.OnOrder,
            poi.PurchaseOrderItemID,
            poi.PurchaseOrderID,
            poi.OnOrderInventoryItemID,
            poi.Quantity as OrderedQty,
            poi.QuantityReceived,
            poi.Finalized,
            po.PONumber
        FROM inventoryitems inv
        INNER JOIN purchaseorderitems poi ON poi.OnOrderInventoryItemID = inv.ItemID
        INNER JOIN purchaseorders po ON po.PurchaseOrderID = poi.PurchaseOrderID
        WHERE inv.Quantity = 0
          AND (poi.Finalized = 0 OR poi.Finalized IS NULL)
        ORDER BY po.PONumber, poi.PurchaseOrderItemID
    """)
    items = cursor.fetchall()
    cursor.close()
    return items

def finalize_item(cursor, item):
    """Finalize a single PO item. Returns (success, message)."""
    inv_item_id = item['InventoryItemID']
    po_item_id = item['PurchaseOrderItemID']
    po_id = item['PurchaseOrderID']

    # Step 1: Delete the placeholder inventory item
    cursor.execute("DELETE FROM inventoryitems WHERE ItemID = %s", (inv_item_id,))

    # Step 2: Update the PO item
    cursor.execute("""
        UPDATE purchaseorderitems
        SET Finalized = 1, OnOrderInventoryItemID = NULL
        WHERE PurchaseOrderItemID = %s
    """, (po_item_id,))

    # Step 3: Increment the PO's NumberOfFinalizedItems
    cursor.execute("""
        UPDATE purchaseorders
        SET NumberOfFinalizedItems = NumberOfFinalizedItems + 1
        WHERE PurchaseOrderID = %s
    """, (po_id,))

    return True, f"Finalized PO Item {po_item_id} (Inventory {inv_item_id})"

def verify_item(cursor, item):
    """Verify a single item was finalized correctly."""
    po_item_id = item['PurchaseOrderItemID']
    inv_item_id = item['InventoryItemID']

    cursor.execute("""
        SELECT Finalized, OnOrderInventoryItemID
        FROM purchaseorderitems WHERE PurchaseOrderItemID = %s
    """, (po_item_id,))
    result = cursor.fetchone()

    if not result or result['Finalized'] != 1 or result['OnOrderInventoryItemID'] is not None:
        return False

    cursor.execute("SELECT ItemID FROM inventoryitems WHERE ItemID = %s", (inv_item_id,))
    if cursor.fetchone() is not None:
        return False

    return True

# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class FinalizeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PO Finalize Tool")
        self.root.geometry("750x650")
        self.root.resizable(True, True)

        self.running = False
        self.load_saved_config()
        self.build_ui()

    def load_saved_config(self):
        """Load saved connection settings."""
        self.saved_config = {
            'host': 'localhost',
            'port': '3307',
            'user': 'admin',
            'password': '',
            'database': '',
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    self.saved_config.update(saved)
            except Exception:
                pass

    def save_config(self):
        """Save connection settings (not password)."""
        config = {
            'host': self.host_var.get(),
            'port': self.port_var.get(),
            'user': self.user_var.get(),
            'database': self.db_var.get(),
            # Password is intentionally NOT saved
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    def build_ui(self):
        """Build the GUI layout."""
        # --- Connection Frame ---
        conn_frame = ttk.LabelFrame(self.root, text="Database Connection", padding=10)
        conn_frame.pack(fill='x', padx=10, pady=(10, 5))

        # Row 0: Host and Port
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.host_var = tk.StringVar(value=self.saved_config['host'])
        ttk.Entry(conn_frame, textvariable=self.host_var, width=30).grid(row=0, column=1, sticky='w')

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky='e', padx=(15, 5))
        self.port_var = tk.StringVar(value=self.saved_config['port'])
        ttk.Entry(conn_frame, textvariable=self.port_var, width=8).grid(row=0, column=3, sticky='w')

        # Row 1: Username and Password
        ttk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky='e', padx=(0, 5), pady=(5, 0))
        self.user_var = tk.StringVar(value=self.saved_config['user'])
        ttk.Entry(conn_frame, textvariable=self.user_var, width=30).grid(row=1, column=1, sticky='w', pady=(5, 0))

        ttk.Label(conn_frame, text="Password:").grid(row=1, column=2, sticky='e', padx=(15, 5), pady=(5, 0))
        self.pass_var = tk.StringVar(value=self.saved_config['password'])
        ttk.Entry(conn_frame, textvariable=self.pass_var, width=20, show='*').grid(row=1, column=3, sticky='w', pady=(5, 0))

        # Row 2: Database
        ttk.Label(conn_frame, text="Database:").grid(row=2, column=0, sticky='e', padx=(0, 5), pady=(5, 0))
        self.db_var = tk.StringVar(value=self.saved_config['database'])
        ttk.Entry(conn_frame, textvariable=self.db_var, width=30).grid(row=2, column=1, sticky='w', pady=(5, 0))

        # Test connection button
        ttk.Button(conn_frame, text="Test Connection", command=self.test_connection).grid(
            row=2, column=2, columnspan=2, sticky='e', padx=(15, 0), pady=(5, 0))

        # --- Action Frame ---
        action_frame = ttk.Frame(self.root, padding=10)
        action_frame.pack(fill='x', padx=10)

        self.preview_btn = ttk.Button(action_frame, text="Preview (Dry Run)", command=self.run_preview)
        self.preview_btn.pack(side='left', padx=(0, 10))

        self.finalize_btn = ttk.Button(action_frame, text="Finalize Items", command=self.run_finalize)
        self.finalize_btn.pack(side='left')

        self.clear_btn = ttk.Button(action_frame, text="Clear Output", command=self.clear_output)
        self.clear_btn.pack(side='right')

        # --- Output Frame ---
        output_frame = ttk.LabelFrame(self.root, text="Output", padding=10)
        output_frame.pack(fill='both', expand=True, padx=10, pady=(5, 10))

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap='word', font=('Consolas', 9))
        self.output_text.pack(fill='both', expand=True)
        self.output_text.config(state='disabled')

        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken', anchor='w', padding=5)
        status_bar.pack(fill='x', side='bottom')

    def log(self, message, log_file=None):
        """Write message to the output area and optionally to a log file."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        line = f"[{timestamp}] {message}\n"

        self.output_text.config(state='normal')
        self.output_text.insert('end', line)
        self.output_text.see('end')
        self.output_text.config(state='disabled')

        if log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

    def clear_output(self):
        """Clear the output area."""
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', 'end')
        self.output_text.config(state='disabled')

    def set_buttons_enabled(self, enabled):
        """Enable or disable action buttons."""
        state = 'normal' if enabled else 'disabled'
        self.preview_btn.config(state=state)
        self.finalize_btn.config(state=state)

    def get_connection(self):
        """Create a connection from the GUI fields."""
        return get_connection(
            host=self.host_var.get(),
            port=self.port_var.get(),
            user=self.user_var.get(),
            password=self.pass_var.get(),
            database=self.db_var.get(),
        )

    def test_connection(self):
        """Test the database connection."""
        self.save_config()
        try:
            conn = self.get_connection()
            conn.close()
            self.log("Connection successful!")
            self.status_var.set("Connection successful")
        except Exception as e:
            self.log(f"Connection FAILED: {e}")
            self.status_var.set("Connection failed")

    def run_preview(self):
        """Run a dry-run preview in a background thread."""
        if self.running:
            return
        self.save_config()
        self.running = True
        self.set_buttons_enabled(False)
        self.status_var.set("Running preview...")
        threading.Thread(target=self._preview_thread, daemon=True).start()

    def _preview_thread(self):
        """Background thread for preview."""
        log_file = get_log_path()

        try:
            self.log("=" * 55)
            self.log("PREVIEW (DRY RUN) - No changes will be made")
            self.log("=" * 55)
            self.log(f"Log file: {log_file}", log_file)
            self.log("")

            conn = self.get_connection()
            self.log("Connected to database", log_file)
            self.log("Finding items to finalize...", log_file)

            items = find_items_to_finalize(conn)
            self.log(f"Found {len(items)} items to finalize", log_file)

            if not items:
                self.log("")
                self.log("No items to finalize. Inventory is clean!")
                conn.close()
                self.root.after(0, lambda: self.status_var.set("Preview complete - 0 items found"))
                return

            # Group by PO
            po_counts = {}
            for item in items:
                po_num = item['PONumber']
                po_counts[po_num] = po_counts.get(po_num, 0) + 1

            self.log(f"\nItems by PO ({len(po_counts)} POs):", log_file)
            for po_num, count in sorted(po_counts.items()):
                self.log(f"  PO# {po_num}: {count} items", log_file)

            self.log("")
            self.log(f"TOTAL: {len(items)} items ready to finalize", log_file)
            self.log("")
            self.log("[DRY RUN] No changes were made.", log_file)

            conn.close()
            self.root.after(0, lambda: self.status_var.set(f"Preview complete - {len(items)} items found"))

        except Exception as e:
            self.log(f"\nERROR: {e}", log_file)
            self.root.after(0, lambda: self.status_var.set("Preview failed - see output"))

        finally:
            self.running = False
            self.root.after(0, lambda: self.set_buttons_enabled(True))

    def run_finalize(self):
        """Run finalization after confirmation."""
        if self.running:
            return

        result = messagebox.askyesno(
            "Confirm Finalization",
            "This will finalize all items with Quantity = 0 in inventory.\n\n"
            "This will:\n"
            "  - Delete zero-quantity placeholder inventory items\n"
            "  - Mark associated PO items as finalized\n\n"
            "Are you sure you want to proceed?",
            icon='warning'
        )

        if not result:
            self.log("Finalization cancelled by user.")
            return

        self.save_config()
        self.running = True
        self.set_buttons_enabled(False)
        self.status_var.set("Finalizing...")
        threading.Thread(target=self._finalize_thread, daemon=True).start()

    def _finalize_thread(self):
        """Background thread for finalization."""
        log_file = get_log_path()

        try:
            self.log("=" * 55)
            self.log("FINALIZATION - LIVE RUN")
            self.log("=" * 55)
            self.log(f"Log file: {log_file}", log_file)
            self.log("")

            conn = self.get_connection()
            conn.autocommit = False
            cursor = conn.cursor(dictionary=True)

            self.log("Connected to database", log_file)
            self.log("Finding items to finalize...", log_file)

            items = find_items_to_finalize(conn)
            self.log(f"Found {len(items)} items to finalize", log_file)

            if not items:
                self.log("")
                self.log("No items to finalize. Inventory is clean!")
                cursor.close()
                conn.close()
                self.root.after(0, lambda: self.status_var.set("Complete - 0 items to finalize"))
                return

            # Group by PO
            po_counts = {}
            for item in items:
                po_num = item['PONumber']
                po_counts[po_num] = po_counts.get(po_num, 0) + 1

            self.log(f"\nItems by PO ({len(po_counts)} POs):", log_file)
            for po_num, count in sorted(po_counts.items()):
                self.log(f"  PO# {po_num}: {count} items", log_file)

            # Process items
            self.log("\n" + "-" * 55)
            self.log("PROCESSING", log_file)
            self.log("-" * 55)

            success_count = 0
            fail_count = 0
            processed = []

            for item in items:
                try:
                    success, msg = finalize_item(cursor, item)
                    if success:
                        success_count += 1
                        processed.append(item)
                        self.log(f"  OK: PO# {item['PONumber']} - {msg}", log_file)
                except Exception as e:
                    fail_count += 1
                    self.log(f"  FAIL: PO# {item['PONumber']} Item {item['PurchaseOrderItemID']} - {e}", log_file)

            # Verify
            self.log("\n" + "-" * 55)
            self.log("VERIFYING", log_file)
            self.log("-" * 55)

            verify_pass = 0
            verify_fail = 0
            for item in processed:
                if verify_item(cursor, item):
                    verify_pass += 1
                else:
                    verify_fail += 1
                    self.log(f"  VERIFY FAIL: PO Item {item['PurchaseOrderItemID']}", log_file)

            # Commit or rollback
            if verify_fail == 0 and fail_count == 0:
                conn.commit()
                self.log("\nAll verifications passed. Changes committed!", log_file)
            else:
                conn.rollback()
                self.log(f"\n{verify_fail} verification failures. Changes ROLLED BACK!", log_file)

            # Summary
            self.log("\n" + "=" * 55)
            self.log("SUMMARY", log_file)
            self.log("=" * 55)
            self.log(f"Total items found:    {len(items)}", log_file)
            self.log(f"Successfully processed: {success_count}", log_file)
            self.log(f"Failed:                {fail_count}", log_file)
            self.log(f"Verification passed:   {verify_pass}", log_file)
            self.log(f"Verification failed:   {verify_fail}", log_file)

            if verify_fail == 0 and fail_count == 0:
                self.log(f"\nDone! {success_count} items finalized.", log_file)
                self.root.after(0, lambda: self.status_var.set(f"Complete - {success_count} items finalized"))
            else:
                self.log("\nErrors occurred. All changes were rolled back.", log_file)
                self.root.after(0, lambda: self.status_var.set("Failed - changes rolled back"))

            cursor.close()
            conn.close()

        except Exception as e:
            self.log(f"\nERROR: {e}", log_file)
            self.root.after(0, lambda: self.status_var.set("Failed - see output"))

        finally:
            self.running = False
            self.root.after(0, lambda: self.set_buttons_enabled(True))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    app = FinalizeApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
