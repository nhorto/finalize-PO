"""
Database configuration for Tekla PowerFab MySQL connection

This module handles database connections and works both when running
as a Python script and as a standalone .exe (built with PyInstaller).
"""
import mysql.connector
from dotenv import load_dotenv
import os
import sys

def get_app_directory():
    """
    Get the directory where the application is running from.
    Works for both Python scripts and PyInstaller .exe files.
    """
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller .exe
        return os.path.dirname(sys.executable)
    else:
        # Running as a Python script
        return os.path.dirname(os.path.abspath(__file__))

def load_config():
    """Load configuration from .env file in the application directory."""
    app_dir = get_app_directory()
    env_path = os.path.join(app_dir, '.env')

    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Try current working directory as fallback
        load_dotenv()

    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3307)),
        'user': os.getenv('MYSQL_USER', 'admin'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'use_pure': True,
        'auth_plugin': 'mysql_native_password'
    }

# Load config on import
DB_CONFIG = load_config()

def get_connection():
    """Get a database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def run_query(sql, params=None):
    """Run a query and return results as dictionaries"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def run_query_raw(sql, params=None):
    """Run a query and return results as tuples"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params or ())
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    cursor.close()
    conn.close()
    return columns, results
