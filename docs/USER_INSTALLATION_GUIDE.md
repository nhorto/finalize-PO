# PO Finalize Tool - User Installation Guide

This guide explains how to set up and run the PO Finalize Tool on your computer.

---

## What You'll Receive

A folder called `finalize-tool` containing:

```
finalize-tool/
├── finalize.exe       # The program
├── .env.template      # Configuration template (you'll edit this)
├── README.txt         # Quick reference
└── logs/              # Where logs are saved
```

---

## Step 1: Configure Your Database Connection

Before running the tool, you need to tell it how to connect to your database.

### 1.1 Find the `.env.template` file

Open the `finalize-tool` folder and find the file called `.env.template`

### 1.2 Edit the file

Open `.env.template` in Notepad (right-click → Open with → Notepad)

You'll see:
```
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=your_database_name
```

### 1.3 Fill in your details

| Setting | What to enter | Example |
|---------|---------------|---------|
| `MYSQL_HOST` | Your database server address | `localhost` or `192.168.1.50` |
| `MYSQL_PORT` | Database port number | `3307` (PowerFab default) |
| `MYSQL_USER` | Your database username | `admin` |
| `MYSQL_PASSWORD` | Your database password | `MySecretPassword123` |
| `MYSQL_DATABASE` | Name of your database | `all-things-metal` |

**Example of a filled-in file:**
```
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=MySecretPassword123
MYSQL_DATABASE=all-things-metal
```

### 1.4 Save and rename the file

1. Save the file (Ctrl+S)
2. Rename the file from `.env.template` to `.env`
   - Remove the `.template` part
   - The file should now just be called `.env`

**Note:** Windows might warn you about changing the file extension. Click "Yes" to confirm.

---

## Step 2: Run the Tool

### 2.1 Open Command Prompt

1. Open the `finalize-tool` folder in File Explorer
2. Click in the address bar at the top
3. Type `cmd` and press Enter
4. A black Command Prompt window will open

**Important:** Use **Command Prompt** (cmd), not PowerShell. If you're in PowerShell, you'll need to add `.\` before the command (e.g., `.\finalize.exe` instead of `finalize.exe`).

### 2.2 Preview First (Recommended)

Always preview what will happen before making changes:

```
finalize.exe --dry-run
```

This shows you what would be finalized **without making any changes**.

You'll see output like:
```
======================================================================
PO ITEM FINALIZATION (Inventory-Based Approach)
======================================================================
MODE: DRY RUN (no changes will be made)

Fetching items to finalize...
Found 1226 items to finalize

Items to finalize by PO (156 POs):
  PO# 0000023: 12 items
  PO# 0000045: 8 items
  ...

[DRY RUN] No changes were made to the database.
```

### 2.3 Run for Real

When you're ready to finalize:

```
finalize.exe
```

The tool will:
1. Show you what will be finalized
2. Ask you to type `YES` to confirm
3. Process all items
4. Show you a summary

---

## Step 3: Check the Logs

Every time you run the tool, it creates a log file in the `logs` folder.

```
logs/
└── 2026-01-25_run1/
    └── finalization_123456.txt
```

Open the log file to see exactly what was done.

---

## Command Reference

| Command | What it does |
|---------|--------------|
| `finalize.exe --dry-run` | Preview without making changes |
| `finalize.exe` | Run and finalize items |
| `finalize.exe --limit 10` | Only process 10 items (for testing) |
| `finalize.exe --no-confirm` | Skip the YES confirmation |

---

## Troubleshooting

### "Access denied" error

Your username or password is incorrect. Double-check your `.env` file.

### "Can't connect to MySQL server"

1. Check that `MYSQL_HOST` is correct
2. Check that `MYSQL_PORT` is correct (usually 3307 for PowerFab)
3. Make sure the database server is running

### "Unknown database"

The database name in `MYSQL_DATABASE` doesn't exist. Check the spelling.

### "No items to finalize"

This means there are no zero-quantity items to clean up. The inventory is already clean!

### The program closes immediately

Run it from Command Prompt (see Step 2.1) to see any error messages.

---

## Frequently Asked Questions

**Q: Is it safe to run?**
A: Yes. The tool only removes zero-quantity placeholder items. It won't touch real inventory.

**Q: Can I run it multiple times?**
A: Yes. If there's nothing to finalize, it will just tell you "No items to finalize."

**Q: What if something goes wrong?**
A: The tool uses database transactions. If there's an error, all changes are automatically rolled back.

**Q: Do I need to close PowerFab first?**
A: No, you can run this while PowerFab is open.

---

## Need Help?

Contact the developer if you have questions or run into issues.
