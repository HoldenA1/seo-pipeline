from google.maps import places_v1
import requests
import os

PLACE_ID = "ChIJDcRm4OMGhYARMhxK8pdb1Tg"

def fetch_photos(id: str, client: places_v1.PlacesClient):
    request = places_v1.GetPlaceRequest(
        name=f"places/{id}",
        language_code="en"
    )

    # Fetch the place details
    response = client.get_place(request=request, metadata=[("x-goog-fieldmask", "photos")])

    print(response.photos)

    return response.photos

# Directories to store images
OUTPUT_DIR = "place_photos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_photo(photo_ref: places_v1.Photo, index: int, client: places_v1.PlacesClient, max_width=4800):
    """Downloads a photo given a photo reference."""

    request = places_v1.GetPhotoMediaRequest(
        name=f"{photo_ref.name}/media",
        max_width_px=photo_ref.width_px
    )

    # Fetch the photo
    response = client.get_photo_media(request=request)

    filename = os.path.join(OUTPUT_DIR, f"photo_{index}.jpg")
    data = requests.get(response.photo_uri).content
    f = open(filename,'wb') 
    f.write(data) 
    f.close() 
    print(f"Fetched photo {response.name}")

# Create a client
client = places_v1.PlacesClient()

# Fetch photo references
photo_references = fetch_photos(PLACE_ID, client)

# Download each photo
for idx, photo_ref in enumerate(photo_references):
    download_photo(photo_ref, idx, client)
