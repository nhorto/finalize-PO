"""
Build Script for PO Finalize Tool
=================================
Creates standalone .exe files for distribution.

Builds two versions:
  - finalize_gui.exe  (GUI - double-click to run, recommended for users)
  - finalize.exe      (CLI - command line version)

REQUIREMENTS:
    pip install pyinstaller mysql-connector-python python-dotenv

USAGE:
    python build.py          # Build both versions
    python build.py gui      # Build GUI only
    python build.py cli      # Build CLI only
"""

import os
import shutil
import subprocess
import sys

# MySQL hidden imports needed by PyInstaller
MYSQL_HIDDEN_IMPORTS = [
    '--hidden-import', 'mysql.connector.plugins.mysql_native_password',
    '--hidden-import', 'mysql.connector.plugins.caching_sha2_password',
    '--hidden-import', 'mysql.connector.plugins.sha256_password',
    '--hidden-import', 'mysql.connector.locales',
    '--hidden-import', 'mysql.connector.locales.eng',
    '--hidden-import', 'mysql.connector.locales.eng.client_error',
    '--collect-submodules', 'mysql.connector',
]

def clean_build():
    """Remove previous build artifacts."""
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"[...] Cleaning {folder}/")
            shutil.rmtree(folder)
    for spec in ['finalize.spec', 'finalize_gui.spec']:
        if os.path.exists(spec):
            os.remove(spec)

def build_gui():
    """Build the GUI version (double-click to run)."""
    print("\n[...] Building GUI version...")

    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name', 'finalize_gui',
        '--windowed',          # No console window - output goes to the GUI
        *MYSQL_HIDDEN_IMPORTS,
        os.path.join('gui', 'finalize_gui.py'),
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("[ERROR] GUI build failed!")
        print(result.stderr)
        return False

    print("[OK] GUI build completed!")
    return True

def build_cli():
    """Build the CLI version (command line)."""
    print("\n[...] Building CLI version...")

    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name', 'finalize',
        '--console',           # Show console window for CLI output
        *MYSQL_HIDDEN_IMPORTS,
        'finalize.py',
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("[ERROR] CLI build failed!")
        print(result.stderr)
        return False

    print("[OK] CLI build completed!")
    return True

def create_distribution(built_gui, built_cli):
    """Package the builds into a distribution folder."""
    dist_folder = os.path.join('dist', 'finalize-tool')
    os.makedirs(dist_folder, exist_ok=True)

    # Move executables
    if built_gui and os.path.exists(os.path.join('dist', 'finalize_gui.exe')):
        shutil.move(
            os.path.join('dist', 'finalize_gui.exe'),
            os.path.join(dist_folder, 'finalize_gui.exe')
        )

    if built_cli and os.path.exists(os.path.join('dist', 'finalize.exe')):
        shutil.move(
            os.path.join('dist', 'finalize.exe'),
            os.path.join(dist_folder, 'finalize.exe')
        )

    # Create logs folder
    os.makedirs(os.path.join(dist_folder, 'logs'), exist_ok=True)

    # Create .env template (for CLI version)
    env_template = """# PO Finalize Tool - Database Configuration (for CLI version)
# ===========================================================
# Edit this file with your database connection details.
# Then rename it to .env (remove the .template part)
#
# NOTE: The GUI version (finalize_gui.exe) does not need this file.
#       You enter connection details directly in the GUI.

MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=your_database_name
"""
    with open(os.path.join(dist_folder, '.env.template'), 'w') as f:
        f.write(env_template)

    # Create README
    readme = """PO Finalize Tool
================

This tool cleans up zero-quantity placeholder items in Tekla PowerFab
inventory after materials have been received.


OPTION 1: GUI VERSION (Recommended)
------------------------------------
Double-click "finalize_gui.exe" to open the tool.

1. Enter your database connection details
2. Click "Test Connection" to verify
3. Click "Preview (Dry Run)" to see what will be finalized
4. Click "Finalize Items" to run the finalization

Your connection settings (except password) are saved automatically.


OPTION 2: COMMAND LINE VERSION
------------------------------
For advanced users who prefer the command line.

Setup:
1. Rename ".env.template" to ".env"
2. Edit ".env" with your database connection details

Usage (from Command Prompt):
  finalize.exe --dry-run     Preview what will be finalized
  finalize.exe               Run the finalization

If using PowerShell, prefix with .\\
  .\\finalize.exe --dry-run


LOGS
----
Each run creates a log file in the "logs" folder.


TROUBLESHOOTING
---------------
- "Access denied": Check your database username and password
- "Can't connect": Check your host and port settings
- "Unknown database": Check your database name

For more help, contact the developer.
"""
    with open(os.path.join(dist_folder, 'README.txt'), 'w') as f:
        f.write(readme)

    return dist_folder

def main():
    print("=" * 60)
    print("Building PO Finalize Tool")
    print("=" * 60)

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"[OK] PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[ERROR] PyInstaller not installed!")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)

    # Set working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"[OK] Working directory: {script_dir}")

    # Parse build target
    target = sys.argv[1] if len(sys.argv) > 1 else 'all'

    # Clean
    clean_build()

    # Build
    built_gui = False
    built_cli = False

    if target in ('all', 'gui'):
        built_gui = build_gui()

    if target in ('all', 'cli'):
        built_cli = build_cli()

    if not built_gui and not built_cli:
        print("\n[ERROR] No builds succeeded!")
        sys.exit(1)

    # Package
    dist_folder = create_distribution(built_gui, built_cli)

    # Summary
    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print(f"\nDistribution folder: {dist_folder}")
    print("\nContents:")
    for item in sorted(os.listdir(dist_folder)):
        size = ""
        full = os.path.join(dist_folder, item)
        if os.path.isfile(full):
            size_mb = os.path.getsize(full) / (1024 * 1024)
            size = f"  ({size_mb:.1f} MB)"
        print(f"  - {item}{size}")

    print("\n" + "-" * 60)
    print("TO DISTRIBUTE:")
    print("-" * 60)
    print(f"Give users the entire '{dist_folder}' folder.")
    print("They double-click finalize_gui.exe and they're ready to go.")
    print("-" * 60)

if __name__ == '__main__':
    main()
