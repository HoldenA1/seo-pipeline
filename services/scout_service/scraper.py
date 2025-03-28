from google.maps import places_v1
from proto.datetime_helpers import DatetimeWithNanoseconds
import sqlite3

PLACE_ID = "ChIJt8Cb82l_j4ARaCVSzzc8gYc"
DB_PATH = "places.db"

def fetch_reviews(place_id: str) -> places_v1.Place:
    # Create a client
    client = places_v1.PlacesClient()

    request = places_v1.GetPlaceRequest(
        name=f"places/{place_id}",
        language_code="en"
    )

    # Fetch the place details
    response = client.get_place(request=request, metadata=[("x-goog-fieldmask", "reviews")])

    return response

def insert_into_db(cursor: sqlite3.Cursor, review: places_v1.Review, place_id: str):
    author = review.author_attribution

    cursor.execute("""
        INSERT INTO reviews (place_id, author_name, author_uri, author_photo, rating, publish_time, review_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        place_id,
        author.display_name,
        author.uri,
        author.photo_uri,
        review.rating,
        review.publish_time.isoformat(),
        review.text.text
    ))

def store_reviews(reviews, place_id: str):
    """Store reviews in the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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

    # Insert each review
    for review in reviews:
        insert_into_db(cursor, review, place_id)

    conn.commit()
    conn.close()
    print(f"Stored reviews for place {place_id}.")

ids = [
    "ChIJ1YxQz_6fj4ARVPxTSbRXuoo",
    "ChIJDcRm4OMGhYARMhxK8pdb1Tg",
    "ChIJE6itKDe1j4ARgUt0_iojJgQ",
    "ChIJZ2skEjx-j4ARYGXhoxMdpSk",
    "ChIJNdJ0mKC1j4ARfW-tKRRpmow",
    "ChIJuwR-D9p0j4ARPi-8zlkLd54",
    "ChIJqUgTD6uAj4ARkv-s_124I0k",
]

for id in ids:
    # Fetch and store reviews
    place = fetch_reviews(id)
    if place.reviews:
        store_reviews(place.reviews, id)
    else:
        print("No reviews found.")
