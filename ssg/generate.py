from jinja2 import Template
import os

DIR_NAME = "website"


def get_articles() -> list:
    """Get a list with all the articles to generate

    For now we just want to manually add articles for testing, but we'll be
    able to customize this function to pull data from a database and later on
    a CMS.
    """

    articles = []
    article = {}
    article["title"] = "Discover the Flavors of Peru at La Mar Cocina Peruana in San Francisco"
    article["slug"] = "visit-la-mar-cocina-peruana"
    article["content"] = """Nestled along the scenic San Francisco waterfront, La Mar Cocina Peruana offers a vibrant and authentic taste of Peru in a stunning setting. With a 4.5-star rating, this lively eatery, helmed by celebrity chef Gastón Acurio, is a must-visit for food lovers seeking fresh, flavorful seafood with a Peruvian twist.
    A Culinary Experience by the Bay

    Located right on the pier, La Mar boasts a spacious, partially outdoor dining area, making it the perfect spot to enjoy breathtaking bay views while indulging in expertly crafted dishes. Whether you're looking for a casual lunch, a romantic dinner, or a lively gathering with friends, the atmosphere is as inviting as the food itself.
    Menu Highlights: A Celebration of Peruvian Seafood

    La Mar’s menu showcases the bold and diverse flavors of Peruvian cuisine, with standouts such as:

        Ceviche – Freshly prepared with zesty citrus, spice, and the perfect balance of textures.
        Tacos – A Peruvian take on a classic favorite, packed with vibrant flavors.
        Cooked Seafood – Expertly prepared dishes that highlight the best of the ocean’s bounty.

    Why Visit La Mar?

    Beyond its exceptional cuisine, La Mar is a culinary destination that brings the rich traditions of Peruvian seafood to the heart of San Francisco. Whether you’re a ceviche connoisseur or a first-time explorer of Peruvian flavors, this restaurant delivers a dining experience that is both authentic and unforgettable.

    Ready to embark on a flavorful journey? Visit La Mar Cocina Peruana to explore the menu and make your reservation today!\n"""
    articles.append(article)
    return articles

articles = get_articles()

# Load Jinja2 template
with open("template.html") as f:
    template = Template(f.read())

# Create output directory
os.makedirs("website", exist_ok=True)

# Generate HTML files
for article in articles:
    title = article["title"]
    slug = article["slug"]
    paragraphs = article["content"].split('\n')
    seo = article.get("seoMetaDescription", "")

    content = "</p><p>".join(paragraphs)

    html_content = template.render(title=title, content=content, seo=seo)

    with open(f"{DIR_NAME}/{slug}.html", "w") as f:
        f.write(html_content)

print(f"Static site generated in '{DIR_NAME}/' directory!")