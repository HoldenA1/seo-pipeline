"""Main file for the scout service"""

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PHOTOS_FOLDER = os.path.abspath(os.path.join(PROJECT_ROOT, "shared/scraped_photos"))
sys.path.append(PROJECT_ROOT)

import requests
from shared.database import initialize_database
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


s = Scout(places_v1.PlacesClient())

s.download_place_photos("ChIJuwR-D9p0j4ARPi-8zlkLd54", PHOTOS_FOLDER)
