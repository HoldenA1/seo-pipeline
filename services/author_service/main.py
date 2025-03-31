"""Main file for the author service

The purpose of the author is to make calls to the LLM to generate content,
process the content, then upload that content to the CMS
"""

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)

from shared.keys import STRAPI_API_KEY, STRAPI_UPLOAD_KEY
import requests
import glob
from shared.schema import Article, Review
from shared.database import get_read_connection
import sqlite3
from llm import generate_article_content
import re

STRAPI_UPLOAD_URL = "http://localhost:1337/api/upload"

class Author:

    def __init__(self, strapi_key: str, db_path: str, upload_key: str):
        self.strapi_key = strapi_key
        self.db_path = db_path
        self.upload_key = upload_key

    
    # def write_prompt_for_place(self, place_id: str) -> str:
    #     """Generates the prompt to feed to the LLM"""
    #     article_data = self.fetch_place_data_from_db(place_id)
    #     prompt = INITIAL_PROMPT
    #     prompt += "\n\n===== PLACE INFO =====\n"
    #     prompt += f"Name: {article_data.place_name}\n"
    #     prompt += f"Address: {article_data.formatted_address}\n"
    #     prompt += f"Rating: {article_data.rating} ({article_data.reviews_count} reviews)\n"
    #     prompt += f"Summary: {article_data.general_summary}\n"
    #     prompt += f"Website: {article_data.business_url}\n"
    #     prompt += "Reviews:\n"
    #     for review in article_data.reviews:
    #         prompt += f"  Rating: {review.rating}\n"
    #         prompt += f"  Review: {review.content}\n\n"
    #     return prompt


    def fetch_place_data_from_db(self, place_id: str) -> Article:
        """Fetches all stored data about a place (including reviews)"""
        conn = get_read_connection()
        cursor = conn.cursor()

        # Fetch place details
        cursor.execute("SELECT * FROM places WHERE id = ?", (place_id,))
        place = cursor.fetchone()

        if not place:
            print(f"No place found with ID: {place_id}")
            conn.close()
            return
        
        article = Article(
            place_name=place[1],
            place_id=place_id,
            rating=place[3],
            general_summary=place[5] or "N/A",
            reviews_count=place[4],
            reviews=self.fetch_reviews_from_db(place_id, conn),
            formatted_address=place[2],
            business_url=place[6] or "N/A",
            title="",
            seo_meta="",
            reviews_summary="",
            detailed_info="",
            city="",
            sources=[],
            images=[],
            slug=""
        )
        conn.close()
        return article
    

    def fetch_reviews_from_db(self, place_id: str, conn: sqlite3.Connection=get_read_connection()) -> list[Review]:
        """Fetches and reviews for a specific place."""
        cursor = conn.cursor()

        cursor.execute("SELECT author_name, author_uri, author_photo, rating, publish_time, review_text FROM reviews WHERE place_id = ?", (place_id,))
        reviews_data = cursor.fetchall()

        reviews_list = []
        if reviews_data:
            for rev_data in reviews_data:
                review = Review(
                    author_name=rev_data[0],
                    author_profile_url=rev_data[1],
                    author_photo_url=rev_data[2],
                    rating=rev_data[3],
                    time_published=rev_data[4],
                    content=rev_data[5]
                )
                reviews_list.append(review)
        
        return reviews_list
    

    def upload_images_to_cms(self, image_paths: list[str]) -> list[dict]:
        """Returns the document ids of the uploaded images"""
        headers = { "Authorization": f"Bearer {self.upload_key}" }

        uploaded_image_ids = []  # List to store uploaded image IDs

        for image_path in image_paths:
            # Open the image file in binary mode
            files = {'files': ('image.jpg', open(image_path, 'rb'), 'image', {'uri': ''})}
            upload_response = requests.post(STRAPI_UPLOAD_URL, headers=headers, files=files)

            # Check if upload is successful
            if upload_response.status_code == 201:
                print(f"Image {image_path} uploaded successfully!")
                image_data = upload_response.json()[0]  # Assuming one image is uploaded
                uploaded_image_ids.append({"id": image_data["id"]})  # Add image ID to the list
                try: # Delete the image after successful upload
                    #os.remove(image_path)
                    print(f"Image {image_path} deleted successfully!")
                except Exception as e:
                    print(f"Error deleting {image_path}: {e}")
            else:
                print(f"Failed to upload image {image_path}", upload_response.status_code, upload_response.text)
                return None
        return uploaded_image_ids


    def write_article_to_cms(self, article: Article, url: str):
        headers = {
            "Authorization": f"Bearer {self.strapi_key}",
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


PLACE_ID = "ChIJuwR-D9p0j4ARPi-8zlkLd54"

a = Author(STRAPI_API_KEY, "places.db", STRAPI_UPLOAD_KEY)

print("Fetching article content...")
article = a.fetch_place_data_from_db(PLACE_ID)

print("Generating content...")
generated_content = generate_article_content(
    article.place_name,
    article.rating,
    article.reviews_count,
    article.general_summary,
    article.formatted_address,
    article.business_url
)

def clean(data: str):
    remove_colons = re.sub(r'^:+', '', data)
    remove_hyphens = re.sub(r'^-+', '', remove_colons)
    return remove_hyphens

article.city = "Cupertino"
article.slug = clean(generated_content['slug'])
article.detailed_info = clean(generated_content['detailed_info']) # I'll never understand why a colon is sometimes prepended to this string. Why???
article.general_summary = clean(generated_content['general_summary'])
article.title = clean(generated_content['title'])
article.reviews_summary = clean(generated_content['reviews_summary'])
article.seo_meta = clean(generated_content['seo_meta'])
article.sources = generated_content['sources']

# Upload photos
print("Uploading photos...")
IMAGE_FOLDER = os.path.join(PROJECT_ROOT, "shared/scraped_photos", PLACE_ID)
image_paths = glob.glob(os.path.join(IMAGE_FOLDER, "*.jpg"))
image_ids = a.upload_images_to_cms(image_paths)
article.images = image_ids


print("Uploading to CMS...")
a.write_article_to_cms(article, "http://localhost:1337/api/articles")

print("Done.")