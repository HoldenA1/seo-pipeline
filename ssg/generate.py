from jinja2 import Template
import requests
import keys
import get_articles
import os

DIR_NAME = "website"

articles = get_articles.articles

# Load Jinja2 template
with open("template.html") as f:
    template = Template(f.read())

# Create output directory
os.makedirs("website", exist_ok=True)

# Generate HTML files
for article in articles:
    # Generate article html
    html_content = template.render(
        seo=article["SEOMetaDescription"],
        title=article["Title"],
        placeName=article["PlaceName"],
        generalSummary=article["Summary"],
        rating=article["Rating"],
        reviewsCount=article["ReviewsCount"],
        reviewsSummary='</p><p>'.join(article["ReviewsSummary"].split('\n')),
        reviews=article["SampleReviews"],
        detailedInformation=article["DetailedInformation"],
        formattedAddress=article["FormattedAddress"],
        locationWebsite=article["WebsiteURL"],
        city=article["City"],
        sources=article["Sources"],
        images=article["Images"],
        slug=article["Slug"]
    )

    with open(f"{DIR_NAME}/{article["Slug"]}.html", "w") as f:
        f.write(html_content)
    
    print(f"Made page {article["Slug"]}")


print(f"Static site generated in '{DIR_NAME}/' directory!")