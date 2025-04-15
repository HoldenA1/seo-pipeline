"""Main file for the author service

The purpose of the author is to make calls to the LLM to generate content,
process the content, then upload that content to the CMS
"""

# Make shared files accessible
import sys, os, time
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)

import requests
import glob
from shared.schema import Article, ArticleStatus
import shared.database as db
import llm

# Constants
STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL", "http://localhost:1337")
STRAPI_ARTICLE_URL = f"{STRAPI_BASE_URL}/api/articles"
STRAPI_MEDIA_UPLOAD_URL = f"{STRAPI_BASE_URL}/api/upload"
STRAPI_API_KEY = os.getenv("STRAPI_API_KEY")

def main():
    """Main author loop"""
    # First, test connection to strapi (needed for upload)
    wait_for_strapi()
    # Get all of the articles approved by the scout
    places_data = db.get_places_by_status(ArticleStatus.FILTERED)
    # Loop through the places
    while len(places_data) > 0:
        for place in places_data:
            # Write and publish article
            print(f"Writing an article on {place.place_name}")
            while True: # Do while loop
                print("Generating fields...")
                generated_fields = llm.generate_fields(
                    place.place_name,
                    place.rating,
                    place.reviews_count,
                    place.general_summary,
                    place.formatted_address,
                    place.business_url
                )
                if "error" in generated_fields:
                    # If the LLM generated poorly formatted content, try again
                    print(generated_fields["error"])
                    print(f"Raw response from LLM: {generated_fields["raw_response"]}\n")
                else:
                    break
            generated_content = llm.generate_detailed_content(
                place.place_name,
                place.rating,
                place.reviews_count,
                place.general_summary,
                place.formatted_address,
                place.business_url
            )
            article = Article(
                title=generated_fields['title'],
                place_name=place.place_name,
                place_id=place.place_id,
                general_summary=generated_fields['general_summary'],
                seo_meta=generated_fields['seo_meta'],
                rating=place.rating,
                reviews_count=place.reviews_count,
                reviews_summary=generated_fields['reviews_summary'],
                reviews=db.get_reviews(place.place_id),
                detailed_info=generated_content,
                formatted_address=place.formatted_address,
                business_url=place.business_url,
                location=place.location,
                types=place.types,
                primary_type=place.primary_type,
                sources=generated_fields['sources'],
                slug=generated_fields['slug'],
                images=[], # populate later
                timestamp=None
            )
            # Upload photos (for docker config photos are stored in volume)
            print("Uploading photos...")
            IMAGE_FOLDER = os.path.join("/tmp/photos", place.place_id)
            image_paths = glob.glob(f"{IMAGE_FOLDER}/*.jpg")
            image_ids = upload_images_to_cms(image_paths, STRAPI_MEDIA_UPLOAD_URL)
            article.images = image_ids
            print("Uploading to CMS...")
            write_article_to_cms(article, STRAPI_ARTICLE_URL)
            # Mark as completed to avoid infinite loop
            db.update_place_status(place.place_id, ArticleStatus.PUBLISHED)
            print("Done.")
        # Check again for any newly filtered places
        places_data = db.get_places_by_status(ArticleStatus.FILTERED)

def wait_for_strapi(max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            headers = { "Authorization": f"Bearer {STRAPI_API_KEY}" }
            response = requests.get(STRAPI_ARTICLE_URL, headers=headers)
            if response.ok:
                print("Strapi is up and running!")
                return True
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(delay)
    raise Exception("Strapi did not become available in time.")

def upload_images_to_cms(image_paths: list[str], url: str) -> list[dict]:
    """Returns the document ids of the uploaded images"""
    headers = { "Authorization": f"Bearer {STRAPI_API_KEY}" }
    uploaded_image_ids = []
    for image_path in image_paths:
        # Open the image file in binary mode
        files = {'files': ('image.jpg', open(image_path, 'rb'), 'image', {'uri': ''})}
        upload_response = requests.post(url, headers=headers, files=files)
        # Check if upload is successful
        if upload_response.status_code == 201:
            print(f"Image {image_path} uploaded successfully!")
            image_data = upload_response.json()[0]  # Assuming one image is uploaded
            uploaded_image_ids.append({"id": image_data["id"]})  # Add image ID to the list
            try: # Delete the image after successful upload
                os.remove(image_path)
                print(f"Image {image_path} deleted successfully!")
            except Exception as e:
                print(f"Error deleting {image_path}: {e}")
        else:
            print(f"Failed to upload image {image_path}", upload_response.status_code, upload_response.text)
            return None
    return uploaded_image_ids


def write_article_to_cms(article: Article, url: str):
    headers = {
        "Authorization": f"Bearer {STRAPI_API_KEY}",
        "Content-Type": "application/json"
    }
    reviews = []
    for review in article.reviews:
        rev_dict = {
            "AuthorName": review.author_name,
            "AuthorProfileURL": review.author_profile_url,
            "AuthorPhotoURL": review.author_photo_url,
            "TimePublished": review.time_published,
            "Rating": review.rating,
            "Review": review.content
        }
        reviews.append(rev_dict)
    data = {
        "data": {
            "Title": article.title,
            "PlaceName": article.place_name,
            "PlaceID": article.place_id,
            "Summary": article.general_summary,
            "SEOMetaDescription": article.seo_meta,
            "Rating": article.rating,
            "ReviewsCount": article.reviews_count,
            "ReviewsSummary": article.reviews_summary,
            "SampleReviews": reviews,
            "DetailedInformation": article.detailed_info,
            "FormattedAddress": article.formatted_address,
            "WebsiteURL": article.business_url,
            "City": article.location.city,
            "State": article.location.state,
            "Country": article.location.country,
            "Types": article.types,
            "PrimaryType": article.primary_type,
            "Sources": article.sources,
            "Images": article.images,
            "Slug": article.slug,
            "publishedAt": None  # Set this to a date/time string to publish immediately
        }
    }
    # Send the request
    response = requests.post(url, json=data, headers=headers)
    print(response.status_code, response.json())


# main script entry point
if __name__ == "__main__":
    main()
