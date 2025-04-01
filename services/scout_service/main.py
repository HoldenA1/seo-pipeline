"""Main file for the scout service"""

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PHOTOS_FOLDER = os.path.abspath(os.path.join(PROJECT_ROOT, "shared/scraped_photos"))
sys.path.append(PROJECT_ROOT)

import requests
from shared.database import initialize_database, DATABASE_PATH
from google.maps import places_v1
import sqlite3

class Scout:

    def __init__(self, client: places_v1.PlacesClient):
        self.client = client
        # Initialize db on startup
        initialize_database()

    def fetch_photos(self, place_id: str):
        request = places_v1.GetPlaceRequest(
            name=f"places/{place_id}",
            language_code="en"
        )
        # Fetch the place details
        response = self.client.get_place(request=request, metadata=[("x-goog-fieldmask", "photos")])

        return response.photos
    
    def fetch_reviews(self, place_id: str) -> places_v1.Place:
        # Create a client
        request = places_v1.GetPlaceRequest(
            name=f"places/{place_id}",
            language_code="en"
        )
        # Fetch the place details
        response = self.client.get_place(request=request, metadata=[("x-goog-fieldmask", "reviews")])

        return response
    
    def insert_review_into_db(self, review: places_v1.Review, place_id: str, conn: sqlite3.Connection):
        author = review.author_attribution

        cursor = conn.cursor()
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

    def store_reviews(self, reviews, place_id: str):
        """Store reviews in the SQLite database."""
        with sqlite3.connect(DATABASE_PATH) as conn:
            # Insert each review
            for review in reviews:
                self.insert_review_into_db(review, place_id, conn)
            conn.commit()  # Auto-closes connection when block ends
        print(f"Stored reviews for place {place_id}.")

    def download_photo(self, photo_ref: places_v1.Photo, filename: str, photos_dir: str):
        """Downloads a photo given a photo reference."""

        request = places_v1.GetPhotoMediaRequest(
            name=f"{photo_ref.name}/media",
            max_width_px=photo_ref.width_px
        )
        # Fetch the photo
        response = self.client.get_photo_media(request=request)
        filename = os.path.join(photos_dir, f"{filename}.jpg")
        data = requests.get(response.photo_uri).content
        f = open(filename,'wb') 
        f.write(data) 
        f.close() 
        print(f"Downloaded photo: {response.name}")

    def download_place_photos(self, place_id: str, photos_dir: str):
        photo_references = self.fetch_photos(place_id)

        place_photos_dir = os.path.join(photos_dir, place_id)
        os.makedirs(place_photos_dir, exist_ok=True)

        # Download each photo
        for idx, photo_ref in enumerate(photo_references):
            self.download_photo(photo_ref, str(idx), place_photos_dir)


PLACE_ID = "ChIJb5PjCwCrEmsRlq2Mj1VBiJQ"

s = Scout(places_v1.PlacesClient())

place = s.fetch_reviews(PLACE_ID)
s.store_reviews(place.reviews, PLACE_ID)