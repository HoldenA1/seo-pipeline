"""Main file for the scout service"""

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PHOTOS_FOLDER = os.path.abspath(os.path.join(PROJECT_ROOT, "shared/scraped_photos"))
sys.path.append(PROJECT_ROOT)

import requests
import shared.database as db
from shared.schema import Review, PlaceData, ArticleStatus
from google.maps import places_v1

# Constants
INCLUDED_FIELDS = [
    "display_name",
    "id",
    "formatted_address",
    "types",
    "rating",
    "user_rating_count",
    "website_uri",
    "editorial_summary"
]
FIELD_MASK = ','.join(INCLUDED_FIELDS)


def main():
    """Main scout loop"""
    scout = Scout()

    ids = [
        # "ChIJtQG0Z6yAj4ARbtnTvKbH4uE",
        # "ChIJt8Cb82l_j4ARaCVSzzc8gYc",
        # "ChIJBZ57qH6HhYARIrlrkRUFIXc",
        # "ChIJZWuUMTl9j4ARaZg735s0HQ4",
        # "ChIJ1YxQz_6fj4ARVPxTSbRXuoo",
        # "ChIJDcRm4OMGhYARMhxK8pdb1Tg",
        # "ChIJE6itKDe1j4ARgUt0_iojJgQ",
        # "ChIJZ2skEjx-j4ARYGXhoxMdpSk",
        # "ChIJNdJ0mKC1j4ARfW-tKRRpmow",
        # "ChIJuwR-D9p0j4ARPi-8zlkLd54",
        "ChIJqUgTD6uAj4ARkv-s_124I0k"
    ]
    for id in ids:
        # pull data
        print("fetching data...")
        place = scout.fetch_place(id, FIELD_MASK)
        data = PlaceData(
            place_id=place.id,
            place_name=place.display_name.text,
            general_summary=place.editorial_summary.text,
            rating=place.rating,
            reviews_count=place.user_rating_count,
            formatted_address=place.formatted_address,
            business_url=place.website_uri
        )
        print("storing data...")
        db.store_places([data])
        print("downloading reviews and photos...")
        scout.mark_place_as_filtered(id)
        print("done.")


class Scout:

    def __init__(self):
        self.client = places_v1.PlacesClient()
        # Initialize db on startup
        db.init_db()

    def fetch_place(self, place_id: str, field_mask: str) -> places_v1.Place:
        """Fetches the place data that fits the fieldmask.

        This is mainly a helper function. Use the other fetch functions for specific data
        """
        request = places_v1.GetPlaceRequest(
            name=f"places/{place_id}",
            language_code="en"
        )
        response = self.client.get_place(request, metadata=[("x-goog-fieldmask", field_mask)])
        return response

    def fetch_photos(self, place_id: str):
        return self.fetch_place(place_id, "photos").photos
    
    def fetch_reviews(self, place_id: str) -> list[Review]:
        response = self.fetch_place(place_id, "reviews")

        reviews = []
        for review in response.reviews:
            author = review.author_attribution
            reviews.append(
                Review(
                    author_name=author.display_name,
                    author_profile_url=author.uri,
                    author_photo_url=author.photo_uri,
                    rating=review.rating,
                    time_published=review.publish_time.isoformat(),
                    content=review.text.text
                )
            )

        return reviews

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

    def search_text(self, activity: str, location: str) -> list[PlaceData]:
        """Searches for businesses fitting activity in the location provided"""

        request = places_v1.SearchTextRequest(
            text_query = f"{activity} in {location}",
        )
        response = self.client.search_text(request, metadata=[("x-goog-fieldmask", FIELD_MASK)])

        places = []
        for place in response.places:
            places.append(
                PlaceData(
                    place_id=place.id,
                    place_name=place.display_name.text,
                    general_summary=place.editorial_summary.text,
                    rating=place.rating,
                    reviews_count=place.user_rating_count,
                    formatted_address=place.formatted_address,
                    business_url=place.website_uri
                )
            )

        return places
    
    def mark_place_as_filtered(self, place_id: str):
        """This function downloads the reviews and photos for the specified place
        then marks it as filtered in the database.
        """
        reviews = self.fetch_reviews(place_id)
        db.store_reviews(reviews, place_id)

        photos = self.fetch_photos(place_id)
        for idx, photo in enumerate(photos):
            dir = os.path.join(PHOTOS_FOLDER, place_id)
            os.makedirs(dir, exist_ok=True)
            self.download_photo(photo, f"photo_{idx}", dir)

        db.update_place_status(place_id, ArticleStatus.FILTERED)


PLACE_ID = "ChIJE6itKDe1j4ARgUt0_iojJgQ"

# s = Scout()
# places = s.search_text("Kayaking", "Half Moon Bay")
# db.store_places(places)
# retrieved = db.get_places_by_status(ArticleStatus.SCOUTED)
# for results in retrieved:
#     print(results)
# db.update_place_status("ChIJpaH4-suAj4AR-RFlCOUHmmQ", ArticleStatus.FILTERED)
# db.update_place_status("ChIJEwzHjrdzj4AR42bc3UdrPRY", ArticleStatus.FILTERED)
# db.update_place_status("ChIJP3TumKN-hYARq1EojP4PAjI", ArticleStatus.FILTERED)
# db.update_place_status("ChIJt1bt4b9QhIARoB4vbHo6M1k", ArticleStatus.FILTERED)
retrieved = db.get_places_by_status(ArticleStatus.FILTERED)
for results in retrieved:
    print(results)

# reviews = s.fetch_reviews(PLACE_ID)
# db.store_reviews(reviews, PLACE_ID)
# reviews_from_db = db.get_reviews(PLACE_ID)
# print(reviews_from_db[0])

# main script entry point
if __name__ == "__main__":
    main()
