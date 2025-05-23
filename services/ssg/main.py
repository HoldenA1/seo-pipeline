"""This file is the main static site generator"""

import os, time
import requests
from staging.schema import Article, Review, Location
from jinja2 import Template
import markdown
from google.cloud import storage
import json
from flask import Flask, request, jsonify

# Constants
STRAPI_BASE_URL = os.getenv("STRAPI_BASE_URL", "http://localhost:1337")
STRAPI_ARTICLE_URL = f"{STRAPI_BASE_URL}/api/articles"
TEMPLATE_PATH = "/app/template.html"
WEBSITE_FOLDER = "/app/website"
LAST_PROCESSED_FILE = "/opt/last_online.json" # Docker is using a volume for this to persist across builds
STRAPI_API_KEY = os.getenv("STRAPI_API_KEY") # This key is for requesting article info from strapi on startup
STRAPI_WEBHOOK_KEY = os.getenv("STRAPI_WEBHOOK_KEY") # This is the key strapi uses when sending data to this endpoint
ENV_TYPE = os.getenv("ENV_TYPE")
ENV_TYPES = {"prod", "dev"}
CLOUD_BUCKET_NAME = "prod-seo-content"
STATES = {"alaska", "arizona", "california", "colorado", "hawaii", "idaho", "montana", "nevada", "new-mexico", "oregon", "utah", "washington", "wyoming", "illinois", "indiana", "iowa", "kansas", "michigan", "minnesota", "missouri", "nebraska", "north-dakota", "ohio", "south-dakota", "wisconsin", "alabama", "arkansas", "delaware", "florida", "georgia", "kentucky", "louisiana", "maryland", "mississippi", "north-carolina", "oklahoma", "south-carolina", "tennessee", "texas", "virginia", "west-virginia", "connecticut", "maine", "massachusetts", "new-hampshire", "new-jersey", "new-york", "pennsylvania", "rhode-island", "vermont"}

# Index variables
states = {}

# Create webhook endpoint
app = Flask(__name__)
app.logger.setLevel('INFO')

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

# Connect to bucket
bucket = None
if ENV_TYPE == "prod":
    bucket = storage.Client().get_bucket(CLOUD_BUCKET_NAME)



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
    app.logger.info('Webhook triggered and authorized.')

    # Process the webhook payload
    hook_data = request.json

    if hook_data.get("event") == "entry.publish":
        article_data = hook_data.get("entry", {})
        article = process_article_data(article_data)
        write_article(article)
        generate_state_city_page(slugify(article.location.state))
        app.logger.info('Successfully created article page.')

    return jsonify({"status": "received"}), 200

def wait_for_strapi(max_retries=3, delay=5):
    app.logger.info("Attempting connection to strapi...")
    for attempt in range(max_retries):
        try:
            headers = { "Authorization": f"Bearer {STRAPI_API_KEY}" }
            response = requests.get(STRAPI_ARTICLE_URL, headers=headers)
            if response.ok:
                app.logger.info("Strapi is up and running.")
                return True
        except requests.exceptions.RequestException as e:
            app.logger.info(f"Attempt {attempt+1} failed: {e}")
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
        "pagination[limit]": 1000,
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
    # Gen all state pages
    for state in STATES:
        generate_state_city_page(state)

def process_article_data(article_data: dict) -> Article:
    # Convert markdown to html
    main_html = markdown.markdown(article_data["DetailedInformation"])
    reviews_html = markdown.markdown(article_data["ReviewsSummary"])
    summary_html = markdown.markdown(article_data["Summary"])
    
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

    if ENV_TYPE == "dev":
        for idx in range(len(article_data["Images"])):
            article_data["Images"][idx] = f"../../assets/{article_data["Images"][idx]}"

    article = Article(
        title=article_data["Title"],
        place_name=article_data["PlaceName"],
        place_id=article_data["PlaceID"],
        general_summary=summary_html,
        seo_meta=article_data["SEOMetaDescription"],
        rating=article_data["Rating"],
        reviews_count=article_data["ReviewsCount"],
        reviews_summary=reviews_html,
        reviews=reviews_list,
        detailed_info=main_html,
        formatted_address=article_data["FormattedAddress"],
        business_url=article_data["WebsiteURL"],
        location=Location(article_data["City"], article_data["State"], article_data["Country"]),
        sources=article_data["Sources"],
        images=article_data["Images"],
        slug=article_data["Slug"],
        timestamp=article_data["publishedAt"],
        primary_type=article_data["PrimaryType"],
        types=article_data["Types"]
    )
    return article

def write_article(article: Article):
    html = generate_html(article, template)
    match ENV_TYPE:
        case "dev": # Save to volume
            with open(f"{WEBSITE_FOLDER}/articles/{article.slug}.html", "w") as f:
                f.write(html)
                save_last_timestamp(article.timestamp)
        case "prod": # Upload to bucket
            blob = bucket.blob(f"places/articles/{article.slug}.html")
            blob.upload_from_string(data=html, content_type="text/html")
            save_last_timestamp(article.timestamp)
    app.logger.info(f"Made article page for {article.slug}")

def fetch_cities_for_state(state: str) -> list:
    headers = { "Authorization": f"Bearer {STRAPI_API_KEY}" }
    params = {
        "filters[State][$eq]": state,
        "pagination[limit]": 1000,  # Adjust if needed
        "fields": ["City"],
    }
    response = requests.get(STRAPI_ARTICLE_URL, headers=headers, params=params)
    cities = set()
    if response.ok:
        for item in response.json()["data"]:
            cities.add(item["City"])
    return sorted(list(cities))

def fetch_places_for_city(city_name: str):
    headers = {"Authorization": f"Bearer {STRAPI_API_KEY}"}
    params = {
        "filters[City][$eq]": city_name,
        "pagination[limit]": 1000,
        "fields": ["PlaceName", "Slug", "Types"]
    }
    response = requests.get(STRAPI_ARTICLE_URL, headers=headers, params=params)
    places = []
    if response.ok:
        for item in response.json()["data"]:
            places.append(item)
    return places

def normalize_slug(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()

def slugify(name: str) -> str:
    return name.lower().replace(" ", "-")

def generate_state_city_page(state_slug: str):
    state_name = normalize_slug(state_slug)
    cities = fetch_cities_for_state(state_name)
    html = state_template.render(state=state_name, cities=cities)

    # create city pages
    for city in cities:
        generate_city_page(city, state_slug)

    match ENV_TYPE:
        case "dev": # Save to volume
            filepath = f"{WEBSITE_FOLDER}/fun-things-to-do-near-me-by-city/{state_slug}.html"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(html)
        case "prod": # Upload to bucket
            blob = bucket.blob(f"places/fun-things-to-do-near-me-by-city/{state_slug}.html")
            blob.upload_from_string(data=html, content_type="text/html")
    
    app.logger.info(f"Made state page for {state_name}")

def generate_city_page(city_name: str, state_slug: str):
    city_slug = slugify(city_name)
    places = fetch_places_for_city(city_name)

    all_tags = set()
    for place in places:
        tags = place.get("Types", [])
        tags = [normalize_slug(item) for item in tags]
        place["Types"] = tags  # ensure it's a list
        all_tags.update(tags)

    html = city_template.render(
        city_name=city_name,
        state=state_slug,
        places=places,
        all_tags=sorted(all_tags)
    )

    match ENV_TYPE:
        case "dev": # Save to volume
            path = f"{WEBSITE_FOLDER}/cities/{city_slug}.html"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(html)
        case "prod": # Upload to bucket
            blob = bucket.blob(f"places/cities/{city_slug}.html")
            blob.upload_from_string(data=html, content_type="text/html")

    app.logger.info(f"Made city page for {city_name}")

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
        city=article.location.city,
        sources=article.sources,
        images=article.images,
        slug=article.slug
    )
    return html_content
        

# main script entry point
if __name__ == "__main__":
    main()
