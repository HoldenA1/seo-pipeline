"""Main file for the author service

The purpose of the author is to make calls to the LLM to generate content,
process the content, then upload that content to the CMS
"""

import keys
import requests
from schema import Article, Review

class Author:

    def __init__(self, strapi_key: str):
        self.strapi_key = strapi_key

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
                # Figure out how to do images
                "Slug": article.slug,
                "publishedAt": None  # Set this to a date/time string to publish immediately
            }
        }

        # Send the request
        response = requests.post(url, json=data, headers=headers)

        print(response.status_code, response.json())



a = Author(keys.STRAPI_API_KEY)

article = Article()

a.write_article_to_cms(article, "http://localhost:1337/api/articles")