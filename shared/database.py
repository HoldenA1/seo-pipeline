import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "places.db")

def get_read_connection() -> sqlite3.Connection:
    """Returns a read-only database connection."""
    uri = f"file:{DATABASE_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Allows dict-like access to results
    return conn

def get_write_connection() -> sqlite3.Connection:
    """Returns a write-enabled database connection for the scout service."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Sets up tables (should only be run once, ideally on scout service startup)."""
    conn = get_write_connection()
    cursor = conn.cursor()

    # Create a table to store Google Places data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id TEXT PRIMARY KEY,
            name TEXT,
            address TEXT,
            rating REAL,
            reviews_count REAL,
            editorial_summary TEXT,
            business_site TEXT
        )
    """)
    
    # Ensure the reviews table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT,
            author_name TEXT,
            author_uri TEXT,
            author_photo TEXT,
            rating REAL,
            publish_time TEXT,
            review_text TEXT,
            FOREIGN KEY (place_id) REFERENCES places (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

