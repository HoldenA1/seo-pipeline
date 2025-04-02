"""Main file for the author service

The purpose of the author is to make calls to the LLM to generate content,
process the content, then upload that content to the CMS
"""

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)

import requests
import glob
from shared.schema import Article, Review, ArticleStatus
import shared.database as db
from llm import generate_article_content
import re

# Constants
STRAPI_UPLOAD_URL = "http://localhost:1337/api/upload"
STRAPI_ARTICLE_URL = "http://localhost:1337/api/articles"
from shared.keys import STRAPI_API_KEY, STRAPI_UPLOAD_KEY
    

def upload_images_to_cms(image_paths: list[str], url: str) -> list[dict]:
    """Returns the document ids of the uploaded images"""
    headers = { "Authorization": f"Bearer {STRAPI_UPLOAD_KEY}" }

    uploaded_image_ids = []  # List to store uploaded image IDs

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
            "City": article.city,
            "Sources": article.sources,
            "Images": article.images,
            "Slug": article.slug,
            "publishedAt": None  # Set this to a date/time string to publish immediately
        }
    }

    # Send the request
    response = requests.post(url, json=data, headers=headers)

    print(response.status_code, response.json())


"""
This is the entrypoint for the author
"""

# First we get all of the articles approved by the scout
place_data = db.get_places_by_status(ArticleStatus.FILTERED)

while len(place_data) > 0:
    # Now we generate the articles for the filtered places
    place = place_data.pop()
    print(f"Writing an article on {place.place_name}")
    db.update_place_status(place.place_id, ArticleStatus.PUBLISHED)

# print("Generating content...")
# generated_content = generate_article_content(
#     article.place_name,
#     article.rating,
#     article.reviews_count,
#     article.general_summary,
#     article.formatted_address,
#     article.business_url
# )

# def clean(data: str):
#     # Sometimes the llm prepends a : or - to the field. Why? I don't know.
#     remove_colons = re.sub(r'^:+', '', data)
#     remove_hyphens = re.sub(r'^-+', '', remove_colons)
#     return remove_hyphens

# article.city = "Cupertino"
# article.slug = clean(generated_content['slug'])
# article.detailed_info = clean(generated_content['detailed_info'])
# article.general_summary = clean(generated_content['general_summary'])
# article.title = clean(generated_content['title'])
# article.reviews_summary = clean(generated_content['reviews_summary'])
# article.seo_meta = clean(generated_content['seo_meta'])
# article.sources = generated_content['sources']

# # Upload photos
# print("Uploading photos...")
# IMAGE_FOLDER = os.path.join(PROJECT_ROOT, "shared/scraped_photos", PLACE_ID)
# image_paths = glob.glob(os.path.join(IMAGE_FOLDER, "*.jpg"))
# image_ids = a.upload_images_to_cms(image_paths)
# article.images = image_ids

# print("Uploading to CMS...")
# a.write_article_to_cms(article, "http://localhost:1337/api/articles")

# print("Done.")