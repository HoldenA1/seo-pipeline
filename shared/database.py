# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)

# Third party imports
import sqlite3
from google.maps import places_v1

# Custom modules
from shared.schema import *

# Constants
DATABASE_FILENAME = "places.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_FILENAME)


# Database and helper methods
def init_db():
    """Create the database if it doesn't already exist"""
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
            business_site TEXT,
            status INT
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

def get_write_connection() -> sqlite3.Connection:
    """Returns a connection to the database with WAL mode enabled"""
    conn = sqlite3.connect(DATABASE_PATH, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")  # Ensure WAL mode
    return conn

def get_read_connection() -> sqlite3.Connection:
    """Returns a read-only database connection."""
    uri = f"file:{DATABASE_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    return conn


# Get data methods
def get_places(query: str) -> list[PlaceData]:
    """Returns a list of places that match the SQL query string
    
    An example query is "WHERE status = {status.value}". The "SELECT * FROM places "
    is already appended to the start of the query string.
    """
    places = []
    try:
        conn = get_read_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM places {query}")
        rows = cursor.fetchall()

        for row in rows:
            places.append(
                PlaceData(
                    place_name=row[1],
                    place_id=row[0],
                    general_summary=row[5],
                    rating=row[3],
                    reviews_count=row[4],
                    formatted_address=row[2],
                    business_url=row[6]
                )
            )
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

    return places

def get_places_by_status(status: ArticleStatus) -> list[PlaceData]:
    """Returns a list of all the places with the given article status"""
    return get_places(f"WHERE status = {status.value}")

def get_place(place_id: str) -> PlaceData:
    """Returns a single place with the given place_id"""
    place_list = get_places(f"WHERE id = \"{place_id}\"")
    if len(place_list) == 0: return None
    else: return place_list[0]

def get_reviews(place_id: str) -> list[Review]:
    """Returns the reviews for a given place_id"""
    reviews = []
    try:
        conn = get_read_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT author_name, author_uri, author_photo, rating, publish_time, review_text FROM reviews WHERE place_id = ?", (place_id,))
        rows = cursor.fetchall()

        for row in rows:
            reviews.append(
                Review(
                    author_name=row[0],
                    author_profile_url=row[1],
                    author_photo_url=row[2],
                    rating=row[3],
                    time_published=row[4],
                    content=row[5]
                )
            )
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

    return reviews


# Store data methods
def store_places(places: list[PlaceData]):
    """Stores the place data of a list of places
    
    If you only need to store a single place, pass in a list with one item
    """
    try:
        conn = get_write_connection()
        cursor = conn.cursor()

        for place in places:
            cursor.execute("""
                INSERT OR IGNORE INTO places (id, name, address, rating, reviews_count, editorial_summary, business_site, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                place.place_id,
                place.place_name,
                place.formatted_address,
                place.rating,
                place.rating,
                place.general_summary,
                place.business_url,
                ArticleStatus.SCOUTED.value
            ))

        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        conn.close()

def store_reviews(reviews: list[Review], place_id: str):
    """Stores the reviews in the reviews table
    
    Retrieve these reviews with the place_id you store them under
    """
    try:
        conn = get_write_connection()
        cursor = conn.cursor()

        for review in reviews:
            cursor.execute("""
                INSERT INTO reviews (place_id, author_name, author_uri, author_photo, rating, publish_time, review_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                place_id,
                review.author_name,
                review.author_profile_url,
                review.author_photo_url,
                review.rating,
                review.time_published,
                review.content
            ))

        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        conn.close()

def update_place_status(place_id: str, new_status: ArticleStatus):
    """Modifies the status of the data store under place_id"""
    try:
        conn = get_write_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE places SET status = ? WHERE id = ?", (new_status.value, place_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()
