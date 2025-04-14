"""Main file for the scout service"""
import requests, os
import shared.database as db
from shared.schema import Review, PlaceData, ArticleStatus
from google.maps import places_v1

import llm

# Constants
INCLUDED_FIELDS = [
    "display_name",
    "id",
    "formatted_address",
    "types",
    "rating",
    "user_rating_count",
    "website_uri",
    "editorial_summary",
    "location"
]
FIELD_MASK = ','.join(INCLUDED_FIELDS)
SEARCH_FIELDS = [
    "places.display_name",
    "places.id",
    "places.formatted_address",
    "places.types",
    "places.rating",
    "places.user_rating_count",
    "places.website_uri",
    "places.editorial_summary",
    "places.location"
]
SEARCH_FIELD_MASK = ','.join(SEARCH_FIELDS)
MAX_PHOTO_HEIGHT = 400
MAX_PHOTO_WIDTH = 800
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")


def main():
    """Main scout loop"""
    scout = Scout()
    searches = [("Restaurants", "San Jose, CA")]
    for activity, location in searches:
        # search for new places
        print(f"Searching for {activity} in {location}...")
        scouted_places = scout.search_text(activity, location)
        print(f"Found {len(scouted_places)} places from search.")
        print("Storing places in db...")
        db.store_places(scouted_places)
        # filter places
        print("Filtering places")
        scouted_places = db.get_places_by_status(ArticleStatus.SCOUTED)
        filtered_ids = llm.filter_places(scouted_places)
        print(f"Filtered ids: {filtered_ids}")
        for place in scouted_places:
            if place.place_id in filtered_ids:
                # good for meetups
                scout.mark_place_as_filtered(place.place_id)
            else:
                # filtered by ai
                db.update_place_status(place.place_id, ArticleStatus.REJECTED)


class Scout:

    def __init__(self):
        self.client = places_v1.PlacesClient()

    def get_city(self, lat: float, lng: float) -> str:
        if GOOGLE_MAPS_KEY == None: raise Exception('No Google Maps key found in environment.')
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_MAPS_KEY}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "OK":
            for result in data["results"]:
                for component in result["address_components"]:
                    if "locality" in component["types"]:
                        return component["long_name"]
        
        return None

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
            max_width_px=MAX_PHOTO_WIDTH,
            max_height_px=MAX_PHOTO_HEIGHT
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
        response = self.client.search_text(request, metadata=[("x-goog-fieldmask", SEARCH_FIELD_MASK)])
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
                    business_url=place.website_uri,
                    city=self.get_city(place.location.latitude, place.location.longitude)
                )
            )
        return places
    
    def mark_place_as_filtered(self, place_id: str):
        """This function downloads the reviews and photos for the specified place
        then marks it as filtered in the database.
        """
        print("Getting Reviews")
        reviews = self.fetch_reviews(place_id)
        db.store_reviews(reviews, place_id)
        print("Fetching photos")
        photos = self.fetch_photos(place_id)
        for idx, photo in enumerate(photos):
            PHOTOS_FOLDER = "/tmp/photos"
            dir = os.path.join(PHOTOS_FOLDER, place_id)
            os.makedirs(dir, exist_ok=True)
            self.download_photo(photo, f"photo_{idx}", dir)
        db.update_place_status(place_id, ArticleStatus.FILTERED)


# main script entry point
if __name__ == "__main__":
    main()
