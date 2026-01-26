# PO Finalize Tool

Automated Purchase Order (PO) item finalization for Tekla PowerFab.

## What This Tool Does

When materials are received in Tekla PowerFab, the system creates temporary "placeholder" inventory items. These placeholders show up as **zero quantity lines** in inventory reports, cluttering the view. This tool automatically removes those placeholders by "finalizing" the received PO items.

**In simple terms:** It cleans up inventory by removing the zero-quantity clutter after materials have been received.

## How It Works

The tool uses a simple approach based on how users would do it manually in the PowerFab UI:

1. **Find** all inventory items with `Quantity = 0` (these are received items ready to be cleaned up)
2. **Look up** the associated Purchase Order items
3. **Finalize** each one by removing the placeholder and marking the PO item as complete

## Two Versions

| Version | Best For | How to Run |
|---------|----------|------------|
| **GUI** (`finalize_gui.exe`) | End users | Double-click to open a window with buttons |
| **CLI** (`finalize.py`) | Developers / advanced users | Run from the command line |

## Quick Start (GUI)

1. Double-click `finalize_gui.exe`
2. Enter your database connection details
3. Click **Test Connection** to verify
4. Click **Preview (Dry Run)** to see what will be finalized
5. Click **Finalize Items** to run

## Quick Start (CLI)

```bash
# 1. Test database connection
python 00_test_connection.py

# 2. See what would be finalized (preview mode)
python finalize.py --dry-run

# 3. Run the finalization
python finalize.py
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview what would happen without making changes |
| `--limit N` | Only process N items (useful for testing) |
| `--no-confirm` | Skip the confirmation prompt |

## Project Structure

```
po-finalize-tool/
├── finalize.py              # CLI finalization script
├── confirm_approach.py      # Query to preview items to finalize
├── investigate_state.py     # Diagnostic script for troubleshooting
├── 00_test_connection.py    # Test database connectivity
├── db_config.py             # Database connection settings
├── build.py                 # Build .exe files for distribution
├── .env                     # Database credentials (not in git)
├── requirements.txt         # Python dependencies
│
├── gui/                     # GUI version
│   └── finalize_gui.py      # Tkinter GUI application
│
├── docs/                    # Documentation
│   ├── STAKEHOLDER_GUIDE.md       # For stakeholders (business overview)
│   ├── TECHNICAL_REFERENCE.md     # For developers (detailed technical info)
│   └── USER_INSTALLATION_GUIDE.md # For end users receiving the .exe
│
├── logs/                    # Run logs organized by date (not in git)
│   └── YYYY-MM-DD_runN/
│
└── archive/                 # Old scripts (reference only)
    ├── analysis-scripts/
    └── old-finalization-scripts/
```

## Building .exe Files for Distribution

To create standalone `.exe` files that can be given to users (no Python install needed):

```bash
# Install build dependencies
pip install pyinstaller mysql-connector-python python-dotenv

# Build both GUI and CLI
python build.py

# Or build just one
python build.py gui
python build.py cli
```

This creates a `dist/finalize-tool/` folder ready to distribute:

```
dist/finalize-tool/
├── finalize_gui.exe    # GUI version (double-click to run)
├── finalize.exe        # CLI version
├── .env.template       # Config template for CLI version
├── README.txt          # User instructions
└── logs/               # Where logs are saved
```

**Note:** Build with x64 Python (not ARM64) if distributing to Intel/AMD machines.

## Documentation

- **[Stakeholder Guide](docs/STAKEHOLDER_GUIDE.md)** - Business overview, what the tool does, why it's needed
- **[Technical Reference](docs/TECHNICAL_REFERENCE.md)** - Database schema, SQL queries, troubleshooting
- **[User Installation Guide](docs/USER_INSTALLATION_GUIDE.md)** - For end users receiving the .exe

## Configuration

### GUI Version
Enter connection details directly in the application window. Settings (except password) are saved automatically.

### CLI Version
Edit `.env` with your database connection:

```
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database_name
```

## Requirements

- Python 3.12+
- mysql-connector-python
- python-dotenv

Install with: `pip install -r requirements.txt`
