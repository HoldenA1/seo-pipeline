"""This file is the main static site generator"""

# Make shared files accessible
import sys, os, time
sys.path.append("/app/shared")

import requests
from shared.schema import Article, Review
from jinja2 import Template
import markdown
import json
from flask import Flask, request, jsonify

# Constants
STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL", "http://localhost:1337")
STRAPI_ARTICLE_URL = f"{STRAPI_BASE_URL}/api/articles"
TEMPLATE_PATH = "/app/template.html"
WEBSITE_FOLDER = "/app/website"
LAST_PROCESSED_FILE = "/opt/last_online.json" # Docker is using a volume for this to persist across builds
STRAPI_API_KEY = os.getenv("STRAPI_API_KEY")
STRAPI_WEBHOOK_KEY = os.getenv("STRAPI_WEBHOOK_KEY")

# Create webhook endpoint
app = Flask(__name__)

# Load templates
f = open("/app/template.html")
template = Template(f.read())
f.close()
f = open("/app/state_dir_template.html")
state_template = Template(f.read())
f.close()
f = open("/app/city_dir_template.html")
city_template = Template(f.read())
f.close()



def main():
    # First, check strapi connection
    wait_for_strapi()

    # Create articles published since last online
    recover_missed_articles()

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
        article = process_article_data(article_data)
        write_article(article)

    return jsonify({"status": "received"}), 200

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

def load_last_timestamp():
    if os.path.exists(LAST_PROCESSED_FILE):
        with open(LAST_PROCESSED_FILE, "r") as file:
            return json.load(file).get("last_timestamp", 0)
    return 0

def save_last_timestamp(timestamp):
    with open(LAST_PROCESSED_FILE, "w") as file:
        json.dump({"last_timestamp": timestamp}, file)

def fetch_articles_since(timestamp):
    articles = []
    params = {
        "filters[publishedAt][$gt]": timestamp,
        "pagination[limit]": 100,
        "populate": "*" # Fetch all relations, including images
    }
    headers = { "Authorization": f"Bearer {STRAPI_API_KEY}" }
    response = requests.get(STRAPI_ARTICLE_URL, headers=headers, params=params)
    if response.status_code == 200: # Check response
        json = response.json()
        for data in json["data"]:
            articles.append(process_article_data(data))
    return articles

def recover_missed_articles():
    last_timestamp = load_last_timestamp()
    articles = fetch_articles_since(last_timestamp)
    for article in articles:
        write_article(article)

def process_article_data(article_data: dict) -> Article:
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
        if "medium" in img["formats"]:
            images_list.append(img["formats"]["medium"]["url"])
        elif "small" in img["formats"]:
            images_list.append(img["formats"]["small"]["url"])

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
        city=article_data["City"],
        sources=article_data["Sources"],
        images=images_list,
        slug=article_data["Slug"],
        timestamp=article_data["publishedAt"]
    )
    return article

def write_article(article: Article):
    html = generate_html(article, template)
    with open(f"{WEBSITE_FOLDER}/{article.slug}.html", "w") as f:
        f.write(html)
        print(f"Made page {article.slug}")
        save_last_timestamp(article.timestamp)

# def create_states_directory(states: list[list[dict]]):
#     states

# def create_city_directory(places: list[dict]):


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
        city=article.city,
        sources=article.sources,
        images=article.images,
        slug=article.slug
    )
    return html_content
        

# main script entry point
if __name__ == "__main__":
    main()
