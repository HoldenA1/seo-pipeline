"""Main file for the scout service"""
import requests, os
from io import BytesIO
from google.maps import places_v1
from google.cloud import storage
import llm
import staging.database as db
from staging.schema import Review, PlaceData, ArticleStatus, Location

# Constants
INCLUDED_FIELDS = [
    "display_name",
    "id",
    "formatted_address",
    "types",
    "primary_type",
    "rating",
    "user_rating_count",
    "website_uri",
    "editorial_summary",
    "location"
]
FIELD_MASK = ','.join(INCLUDED_FIELDS)
SEARCH_FIELDS = [f"places.{field}" for field in INCLUDED_FIELDS]
SEARCH_FIELD_MASK = ','.join(SEARCH_FIELDS)
MAX_PHOTO_HEIGHT = 400
MAX_PHOTO_WIDTH = 800
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")
ENV_TYPE = os.getenv("ENV_TYPE")
ENV_TYPES = {"prod", "dev"}
CLOUD_BUCKET_NAME = "prod-seo-images"
PHOTOS_FOLDER = "/tmp/photos"


def main():
    """Main scout loop"""

    if ENV_TYPE not in ENV_TYPES:
        print(f"Invalid environment type: was \"{ENV_TYPE}\" should be one of the following {ENV_TYPES}.")
        return
    
    scout = Scout()

    searches = [
        ("Bars", "La Jolla, CA"),
        ("Restaurants", "El Cajon, CA"),
        ("Restaurants", "Los Gatos, CA"),
        ("Parks", "Palo Alto, CA")
    ]

    for activity, location in searches:

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
        self.bucket = None
        if ENV_TYPE == "prod":
            self.bucket = storage.Client().get_bucket(CLOUD_BUCKET_NAME)

    def get_location(self, lat: float, lng: float) -> Location:
        if GOOGLE_MAPS_KEY == None: raise Exception('No Google Maps key found in environment.')
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_MAPS_KEY}"
        response = requests.get(url)
        results = response.json()["results"]
        city = state = country = ""
        if results:
            for component in results[0]["address_components"]:
                if "locality" in component["types"]:
                    city = component["long_name"]
                elif "administrative_area_level_1" in component["types"]:
                    state = component["long_name"]
                elif "country" in component["types"]:
                    country = component["long_name"]
        return Location(city, state, country)

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

    def download_photo(self, photo_ref: places_v1.Photo) -> bytes:
        """Downloads a photo given a photo reference."""
        request = places_v1.GetPhotoMediaRequest(
            name=f"{photo_ref.name}/media",
            max_width_px=MAX_PHOTO_WIDTH,
            max_height_px=MAX_PHOTO_HEIGHT
        )
        # Fetch the photo
        response = self.client.get_photo_media(request=request)
        data = requests.get(response.photo_uri).content
        return data

    def save_photo(self, photo_data: bytes, filename: str, place_id: str) -> str:
        match ENV_TYPE:
            case "dev": # Save to volume
                path = os.path.join(PHOTOS_FOLDER, place_id, filename)
                f = open(path, 'wb') 
                f.write(photo_data) 
                f.close()
                return f"{place_id}/{filename}"
            case "prod": # Upload to bucket
                blob = self.bucket.blob(f"{place_id}/{filename}")
                blob.upload_from_file(BytesIO(photo_data), content_type='image/jpeg')
                return blob.public_url

    def create_folder(self, place_id: str):
        match ENV_TYPE:
            case "dev":
                place_photos_dir = os.path.join(PHOTOS_FOLDER, place_id)
                os.makedirs(place_photos_dir, exist_ok=True)
            case "prod":
                # Create placeholder folder blob (optional, just for UI appearance)
                folder_blob = self.bucket.blob(f"{place_id}/")
                folder_blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')

    def download_place_photos(self, place_id: str) -> list[str]:
        """Returns the uris of the saved images"""
        photo_references = self.fetch_photos(place_id)
        self.create_folder(place_id)
        # Download each photo
        uris = []
        for idx, photo_ref in enumerate(photo_references):
            photo_data = self.download_photo(photo_ref)
            uris.append(self.save_photo(photo_data, f"photo_{idx}.jpg", place_id))
        return uris

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
                    location=self.get_location(place.location.latitude, place.location.longitude),
                    types=[t for t in place.types if t not in {"establishment", "point_of_interest", "food"}], # filter generic types
                    primary_type=place.primary_type
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
        os.makedirs(PHOTOS_FOLDER, exist_ok=True)
        photo_uris = self.download_place_photos(place_id)
        db.store_images(photo_uris, place_id)

        db.update_place_status(place_id, ArticleStatus.FILTERED)


# main script entry point
if __name__ == "__main__":
    main()
