"""This file is the main static site generator"""

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)

import requests
from shared.schema import Article, Review
from jinja2 import Template
import markdown
from flask import Flask, request, jsonify

# Constants
STRAPI_URL = "http://localhost:1337/api/articles"
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(CUR_DIR, "template.html")
WEBSITE_FOLDER = os.path.join(PROJECT_ROOT, "website")
from shared.keys import STRAPI_API_KEY, STRAPI_WEBHOOK_KEY

# Create webhook endpoint
app = Flask(__name__)

# Load template
f = open(TEMPLATE_PATH)
template = Template(f.read())
f.close()


def main():
    # Create output directory
    os.makedirs(WEBSITE_FOLDER, exist_ok=True)

    # Start flask endpoint
    app.run(host='0.0.0.0', port=8080)


@app.route('/webhook', methods=['POST'])
def strapi_webhook():
    # Get the headers from the request
    headers = request.headers
    received_secret = headers.get("Authorization")

    # Verify the secret key
    if received_secret != STRAPI_WEBHOOK_KEY:
        return jsonify({"error": "Unauthorized"}), 403  # Reject unauthorized requests
    
    # Log the webhook
    print("Webhook triggered.")

    # Process the webhook payload
    hook_data = request.json

    if hook_data.get("event") == "entry.publish":
        article_data = hook_data.get("entry", {})

        # Convert markdown to html
        main_html = markdown.markdown(article_data["DetailedInformation"])
        # Create reviews list
        reviews_list = []
        for rev_data in article_data["SampleReviews"]:
            review = Review(
                author_name=rev_data["AuthorName"],
                author_profile_url=rev_data["AuthorProfileURL"],
                author_photo_url=rev_data["AuthorPhotoURL"],
                rating=rev_data["Rating"],
                time_published=rev_data["TimePublished"],
                content=rev_data["Review"]
            )
            reviews_list.append(review)
            
        # Create images list
        images_list = []
        for img in article_data["Images"]:
            images_list.append(img["formats"]["medium"]["url"])

        article = Article(
            title=article_data["Title"],
            place_name=article_data["PlaceName"],
            place_id=article_data["PlaceID"],
            general_summary=article_data["Summary"],
            seo_meta=article_data["SEOMetaDescription"],
            rating=article_data["Rating"],
            reviews_count=article_data["ReviewsCount"],
            reviews_summary=article_data["ReviewsSummary"],
            reviews=reviews_list,
            detailed_info=main_html,
            formatted_address=article_data["FormattedAddress"],
            business_url=article_data["WebsiteURL"],
            sources=article_data["Sources"],
            images=images_list,
            slug=article_data["Slug"]
        )
        html = generate_html(article, template)

        with open(f"{WEBSITE_FOLDER}/{article.slug}.html", "w") as f:
            f.write(html)
            print(f"Made page {article.slug}")

    return jsonify({"status": "received"}), 200


def generate_html(article: Article, template: Template) -> str:
    """Creates a page based on the template"""
    # You can only loop a list in jinja so I turned the rating into a list
    rl = []
    for review in article.reviews:
        rev_dict = {
            "AuthorName": review.author_name,
            "AuthorProfileURL": review.author_profile_url,
            "AuthorPhotoURL": review.author_photo_url,
            "TimePublished": review.time_published,
            "Review": review.content
        }
        stars = []
        for i in range(5):
            # We use these to choose which color to make the star
            if review.rating > i:
                stars.append("#ffbb29")
            else:
                stars.append("grey")
        rev_dict["Stars"] = stars
        rl.append(rev_dict)
    
    # Generate article html
    html_content = template.render(
        seo=article.seo_meta,
        title=article.title,
        placeName=article.place_name,
        placeID=article.place_id,
        generalSummary=article.general_summary,
        rating=article.rating,
        reviewsCount=article.reviews_count,
        reviewsSummary=article.reviews_summary,
        reviews=rl,
        detailedInformation=article.detailed_info,
        formattedAddress=article.formatted_address,
        locationWebsite=article.business_url,
        city="City", # placeholder for now
        sources=article.sources,
        images=article.images,
        slug=article.slug
    )
    return html_content
        

def fetch_articles(url: str) -> list[Article]:
    """Pulls article data from the CMS"""
    articles = []
    params = { "populate": "*" } # Fetch all relations, including images
    headers = { "Authorization": f"Bearer {STRAPI_API_KEY}" }

    # Send the request
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200: # Check response
        json = response.json()
        for data in json["data"]:
            # Convert markdown to html
            summary_html = markdown.markdown(data["Summary"])
            review_summary_html = markdown.markdown(data["ReviewsSummary"])
            main_html = markdown.markdown(data["DetailedInformation"])

            # Create reviews list
            reviews_list = []
            for rev_data in data["SampleReviews"]:
                review = Review(
                    author_name=rev_data["AuthorName"],
                    author_profile_url=rev_data["AuthorProfileURL"],
                    author_photo_url=rev_data["AuthorPhotoURL"],
                    rating=rev_data["Rating"],
                    time_published=rev_data["TimePublished"],
                    content=rev_data["Review"]
                )
                reviews_list.append(review)
            
            # Create images list
            images_list = []
            for img in data["Images"]:
                #print(img)
                images_list.append(img["formats"]["medium"]["url"])

            article = Article(
                title=data["Title"],
                place_name=data["PlaceName"],
                place_id=data["PlaceID"],
                general_summary=summary_html,
                seo_meta=data["SEOMetaDescription"],
                rating=data["Rating"],
                reviews_count=data["ReviewsCount"],
                reviews_summary=review_summary_html,
                reviews=reviews_list,
                detailed_info=main_html,
                formatted_address=data["FormattedAddress"],
                business_url=data["WebsiteURL"],
                sources=data["Sources"],
                images=images_list,
                slug=data["Slug"]
            )
            articles.append(article)

    return articles


# main script entry point
if __name__ == "__main__":
    main()
