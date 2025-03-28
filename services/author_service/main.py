"""Main file for the author service

The purpose of the author is to make calls to the LLM to generate content,
process the content, then upload that content to the CMS
"""

# Make shared files accessible
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.keys import STRAPI_API_KEY
import requests
from shared.schema import Article, Review
from shared.database import get_read_connection
import sqlite3
from prompt import INITIAL_PROMPT

class Author:

    def __init__(self, strapi_key: str, db_path: str):
        self.strapi_key = strapi_key
        self.db_path = db_path

    
    def write_prompt_for_place(self, place_id: str) -> str:
        """Generates the prompt to feed to the LLM"""
        article_data = self.fetch_place_data_from_db(place_id)
        prompt = INITIAL_PROMPT
        prompt += "\n\n===== PLACE INFO =====\n"
        prompt += f"Name: {article_data.place_name}\n"
        prompt += f"Address: {article_data.formatted_address}\n"
        prompt += f"Rating: {article_data.rating} ({article_data.reviews_count} reviews)\n"
        prompt += f"Summary: {article_data.general_summary}\n"
        prompt += f"Website: {article_data.business_url}\n"
        prompt += "Reviews:\n"
        for review in article_data.reviews:
            prompt += f"  Rating: {review.rating}\n"
            prompt += f"  Review: {review.content}\n\n"
        return prompt


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
                # For now manually add images
                "Slug": article.slug,
                "publishedAt": None  # Set this to a date/time string to publish immediately
            }
        }

        # Send the request
        response = requests.post(url, json=data, headers=headers)

        print(response.status_code, response.json())


PLACE_ID = "ChIJDcRm4OMGhYARMhxK8pdb1Tg"

a = Author(STRAPI_API_KEY, "places.db")

#print(a.write_prompt_for_place(PLACE_ID))

article = a.fetch_place_data_from_db(PLACE_ID)
article.city = "San Francisco"
article.slug = "adventure-cat-sailing-charters-san-francisco-bay-meetup"
article.detailed_info = """## What activities can you do at Adventure Cat Sailing Charters?

Adventure Cat Sailing Charters offers a variety of exciting activities for groups looking to explore San Francisco Bay. The main attraction is their sailing tours, which provide a unique perspective of the city's iconic landmarks. Guests can enjoy breathtaking views of Alcatraz Island, the Golden Gate Bridge, and the San Francisco skyline from the comfort of a stable catamaran. These tours typically last between 60 to 90 minutes, giving ample time to soak in the sights and capture memorable photos.

## What makes Adventure Cat's sailing experience unique?

Adventure Cat's custom-built catamarans offer a distinctive sailing experience that sets them apart from traditional boats. The dual-hull design of these vessels ensures a remarkably smooth and stable ride, making it comfortable for guests of all ages. The boats feature both open-air decks and sheltered cabins, allowing passengers to enjoy the best of both worlds – the exhilaration of feeling the wind and spray on the deck, and the comfort of a protected area if needed. This versatility makes Adventure Cat an ideal choice for groups with diverse preferences and needs.

## What wildlife might you see during an Adventure Cat sail?

One of the highlights of sailing with Adventure Cat is the opportunity to spot local marine wildlife. As you cruise around the bay, keep your eyes peeled for pelicans soaring overhead and playful sea lions lounging near the piers. Lucky passengers might even catch glimpses of dolphins gliding through the water or, on rare occasions, whales breaching the surface. This chance to connect with nature adds an extra layer of excitement to the sailing experience and provides excellent photo opportunities for nature enthusiasts.

## What are the dining options on Adventure Cat charters?

Adventure Cat Sailing Charters offers a range of dining options to suit different group preferences and event types. For private charters, they partner with local San Francisco providers to offer a variety of menu choices. These options range from light appetizers to full buffet platters, ensuring that groups of all sizes can find suitable catering solutions. While specific menu details may vary, past catering has included items such as chicken skewers, beef kafta meatball skewers, rice pilaf, dolmas, hummus, pitas, and falafels – a diverse selection that caters to various dietary preferences.

## What beverage options are available during the sail?

Adventure Cat provides several beverage packages to enhance your sailing experience. They offer a Soft Drink Bar, which includes soda, bottled water, and juice. For those looking for alcoholic options, there's a Premium Beer and Wine package, as well as a Full Open Liquor Bar. Prices for these packages vary based on the duration of the charter, ranging from two to four hours. It's worth noting that outside beverages are generally not permitted, with the exception of wine or champagne, which can be brought on board for a corkage fee of \$15 per bottle.

## Why is Adventure Cat perfect for group meetups?

Adventure Cat Sailing Charters is an excellent choice for group meetups due to its versatility and unique offerings. The company's two custom-made catamarans can accommodate groups ranging from 10 to 90 passengers, making it suitable for various event sizes. The spacious design of the boats ensures that even with larger groups, there's plenty of room for everyone to move around comfortably. The combination of open-air decks and sheltered areas means that guests can socialize in different settings, whether they prefer the excitement of the open water or the coziness of the cabin.

## How does Adventure Cat cater to corporate events and team-building activities?

Adventure Cat has become one of the most popular choices for team offsite activities in San Francisco. The unique sailing experience provides an excellent backdrop for team bonding and networking. The change of scenery from the typical office environment can inspire creativity and foster better communication among team members. Additionally, the crew's friendly and professional demeanor adds to the overall positive experience, ensuring that corporate events run smoothly. The option to include catering and bar services also simplifies the planning process for event organizers.

## What makes Adventure Cat suitable for special occasions like birthdays or family reunions?

The versatility of Adventure Cat's offerings makes it an ideal venue for special occasions such as birthdays, family reunions, or gatherings with friends. The memorable experience of sailing on San Francisco Bay provides a unique backdrop for celebrations. The ability to customize the experience with various food and beverage packages allows hosts to tailor the event to their specific needs. Moreover, the stunning views and potential for wildlife sightings add an element of excitement and natural beauty to any celebration, creating lasting memories for all attendees.

## How does Adventure Cat ensure safety and comfort for all passengers?

Safety is a top priority for Adventure Cat Sailing Charters. Their catamarans are known for their stability, providing a comfortable ride even for those who might be prone to seasickness. Life jackets are provided for all passengers, including children, ensuring everyone's safety on board. The experienced and friendly crew members are not only knowledgeable about sailing and the bay area but are also attentive to passengers' needs and comfort. For those who might feel chilly, the boats offer sheltered areas, and the company recommends dressing in layers to ensure comfort throughout the sail.

## What additional amenities does Adventure Cat offer to enhance the group experience?

To further enhance the group experience, Adventure Cat offers several amenities. They provide multilingual audio tours, allowing international visitors to fully appreciate the rich history and sights of San Francisco Bay. The boats are equipped with comfortable seating areas and even feature "trampolines" on the bow where guests can get close to the water while remaining safe on deck. For private charters, groups have the flexibility to customize their experience, from choosing their preferred route around the bay to selecting music that suits their taste. These thoughtful touches ensure that each group's experience is tailored to their preferences, making for a truly memorable outing."""
article.general_summary = """The reviews for Adventure Cat Sailing Charters are overwhelmingly positive, with users consistently praising various aspects of the experience. Many reviewers highlight the friendly and attentive nature of the crew, describing them as not only committed to safety but also highly interactive and engaging with passengers. The stunning views of San Francisco Bay, including close-up vistas of the Golden Gate Bridge, Alcatraz, and the city skyline, are frequently mentioned as highlights of the trip.

Positive reviews often emphasize the quality of the experience, with many describing it as "unforgettable" and "breathtaking." Guests appreciate the spaciousness and stability of the catamarans, which contribute to a comfortable journey even for those without sailing experience. The sunset sails receive particular praise, with many considering them the perfect time to enjoy the bay's beauty. Reviewers also commend the value for money, viewing the experience as well worth the cost.

Interestingly, there are very few negative reviews mentioned in the provided information. The vast majority of feedback is overwhelmingly positive, with the business maintaining a high rating of 4.9 out of 5 stars based on 889 reviews. This suggests that most customers are highly satisfied with their experience.

In conclusion, the reviews paint a picture of Adventure Cat Sailing Charters as an exceptional choice for a meetup venue. The combination of stunning views, friendly and professional staff, comfortable vessels, and the unique experience of sailing on San Francisco Bay makes it a highly recommended activity for both locals and visitors alike. The consistently positive feedback across hundreds of reviews indicates that Adventure Cat delivers a reliable and enjoyable experience for groups and gatherings."""
article.title = "Set Sail for Memorable Meetups: Adventure Cat Sailing Charters in San Francisco"
article.reviews_summary = """Adventure Cat Sailing Charters offers an exceptional setting for meetups with friends and family in San Francisco. Located at Pier 39, this sailing experience provides a unique and exciting way to gather and create lasting memories. The company's spacious catamarans offer a perfect blend of open-air excitement and sheltered comfort, making it suitable for groups of all ages and preferences.

What sets Adventure Cat apart as a meetup destination is its ability to combine stunning views, thrilling sailing, and comfortable amenities. As you sail around the bay, you and your group will enjoy breathtaking close-up views of iconic landmarks such as Alcatraz Island, the Golden Gate Bridge, and the city's famous skyline. The experience also offers the chance to spot marine wildlife, including pelicans, sea lions, dolphins, and even the occasional whale, adding an element of natural wonder to your gathering.

The company's commitment to creating a fun and relaxing atmosphere ensures that your meetup will be enjoyable for everyone. Whether you're planning a family outing or a get-together with friends, Adventure Cat's tours cater to all group dynamics. The stable and safe ride of their catamarans, combined with the exhilaration of fresh air and waves, provides an ideal backdrop for socializing and bonding.

For those seeking a more romantic setting for a couples' meetup, the sunset sails offer a particularly magical experience. As the sun dips below the horizon, painting the sky in vibrant hues, you and your friends can toast to the spectacular views and shared moments. The availability of beverages on board, including a complimentary first drink on some tours, adds to the convivial atmosphere."""
article.seo_meta = "Discover why Adventure Cat Sailing Charters is the perfect venue for unforgettable meetups with friends and family on San Francisco Bay."
article.sources = [
    "https://www.greatworkperks.com/perks/act-ca/adventure-cats",
    "https://www.yelp.com/biz/adventure-cat-sailing-charters-san-francisco-2",
    "https://www.pier39.com/adventure-cat-sailing-charters/",
    "https://www.adventurecat.com",
    "https://luxuryliners.com/product/san-francisco-catamaran-charter/",
    "https://sfbayadventures.com/adventure-cat-1/",
    "https://www.sailoyc.com/catering"
]

a.write_article_to_cms(article, "http://localhost:1337/api/articles")