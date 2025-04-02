"""This file is the main static site generator"""

# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)

from shared.keys import STRAPI_API_KEY
import requests
from shared.schema import Article, Review
from jinja2 import Template
import markdown

STRAPI_URL = "http://localhost:1337/api/articles"

class Generator:

    def __init__(self, strapi_key: str):
        self.strapi_key = strapi_key

    def generate_html(self, article: Article, template: Template) -> str:
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
        

    def fetch_articles(self, url: str) -> list[Article]:
        """Pulls article data from the CMS"""
        articles = []
        params = { "populate": "*" } # Fetch all relations, including images
        headers = { "Authorization": f"Bearer {self.strapi_key}" }

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
    


CUR_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(CUR_DIR, "template.html")
WEBSITE_FOLDER = os.path.join(PROJECT_ROOT, "website")

g = Generator(STRAPI_API_KEY)
articles = g.fetch_articles(STRAPI_URL)

# Load Jinja2 template
with open(TEMPLATE_PATH) as f:
    template = Template(f.read())
    # Create output directory
    os.makedirs(WEBSITE_FOLDER, exist_ok=True)

    for article in articles:
        html = g.generate_html(article, template)

        with open(f"{WEBSITE_FOLDER}/{article.slug}.html", "w") as f:
            f.write(html)
        
            print(f"Made page {article.slug}")

