from google.maps import places_v1
import sqlite3
# Make shared files accessible
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(PROJECT_ROOT)
import shared.database as db

INCLUDED_FIELDS = [
    "places.display_name",
    "places.id",
    "places.formatted_address",
    "places.types",
    "places.rating",
    "places.user_rating_count",
    "places.website_uri",
    "places.editorial_summary"
]

ACTIVITES = {
    "Afternoon Tea",
    "Arcade Night",
    "Archery",
    "Arts & Crafts",
    "Attend a Ballet",
    "Attend a Cooking Class",
    "Attend Lecture",
    "ATV and Offroading",
    "Axe Throwing",
    "Backyard BBQ",
    "Badminton",
    "Ballet",
    "Bar Hop",
    "Bar Hopping",
    "Basketball",
    "BBQ",
    "Beach Day",
    "Beach Volleyball",
    "Biking",
    "Billiards",
    "Bingo Night",
    "Birdwatching",
    "Birthday Celebration",
    "Board Game Cafe",
    "Boba and Hang",
    "Bocce Ball",
    "Boogie Boarding",
    "Book Club Meeting",
    "Boot Camp Workout",
    "Botanical Garden",
    "Brew at Home",
    "Browse the Bookstore",
    "Brunch Time",
    "Camping Trip",
    "Casino Night",
    "Catch Up!",
    "Check Out the Aquarium",
    "Check Out the Fair",
    "Church Event",
    "Cigar Lounge",
    "Climbing",
    "Clubbing",
    "Cocktail Making",
    "Coffee and Hang",
    "Comedy Show",
    "Concert Time",
    "Cooking Class",
    "Cosplay Anyone?",
    "Cricket",
    "Dancing",
    "Day at the Lake",
    "Dinner and Drinks",
    "Dinner Cruise",
    "DIY Day",
    "Documentary Watch Party",
    "Donut Tasting",
    "Drive-In Movie",
    "Drone Racing",
    "Dungeons & Dragons",
    "Electric Biking",
    "Escape Room",
    "Family Gathering",
    "Fantasy Sports",
    "Farmers Market",
    "Fashion Show",
    "Fishing",
    "Fitness Class",
    "Fondue Party",
    "Food Hall",
    "Food Tour",
    "Food Trucks",
    "Frisbee Golf",
    "Fruit Picking",
    "Gaming",
    "Gardening",
    "Geocaching",
    "Glamping",
    "Go Bowling",
    "Go for Ice Cream",
    "Go Karting",
    "Go Running",
    "Golf",
    "Grab Dessert",
    "Group Digital Detox",
    "Hackathon",
    "Hang at a Cigar Lounge",
    "Hang on a Boat",
    "Happy Hour",
    "Head to Comedy Show",
    "Hiking",
    "Horseback Riding",
    "Hot Springs",
    "Hunting",
    "Hydrofoil",
    "Ice Skating",
    "Investing Discussion",
    "Jam Session",
    "Jet Skiing",
    "Karaoke",
    "Kayaking",
    "Kickball Game!",
    "Kitesurfing",
    "Knitting",
    "Korean BBQ and Soju",
    "Laser Tag",
    "Let's Go Climbing",
    "Live Music",
    "Live Theatre",
    "Luau",
    "Lunch Catch Up",
    "Magic Show",
    "Mahjong",
    "Mani Pedi",
    "Metal Detecting Treasure Hunt",
    "Microbrew Tasting",
    "Mini Golf",
    "Motorcying",
    "Mountain Biking",
    "Movie Night",
    "Museum Day",
    "Musical",
    "Opera",
    "Padel",
    "Paintball Battle",
    "Painting Class",
    "Photography Class",
    "Pickle Ball",
    "Pickup Basketball",
    "Picnic and Games",
    "Pilates",
    "Ping Pong",
    "Pizza Party",
    "Play Badminton",
    "Play Board Games",
    "Play Bocce Ball",
    "Play Cricket",
    "Play Football",
    "Playdate",
    "Poker Night",
    "Pool Day",
    "Potluck Dinner",
    "Pottery Class",
    "Pub Crawl",
    "Pumpkin Patch",
    "Qigong",
    "Racetrack",
    "Reading Poetry",
    "Road Biking",
    "Roller Skating",
    "Rollerblade",
    "Ropes Course",
    "Sailing",
    "Salsa Dancing",
    "Scavenger Hunt",
    "Scrapping",
    "Scuba Diving",
    "Seafood Boil",
    "Segway Tour",
    "Shoot Some Pool",
    "Shooting Range",
    "Shopping",
    "Singing",
    "Skateboarding",
    "Skiing",
    "Skydive",
    "Sledding",
    "Sleepover",
    "Snorkeling",
    "Snowboarding",
    "Snowmobiling",
    "Soap Making",
    "Soccer",
    "Sofball Game",
    "Some Dim Sum?",
    "Spa Day",
    "Spin Class",
    "Stargazing",
    "Storytime at the Library",
    "Study Sesh",
    "SUP",
    "Surfing",
    "Sushi Night",
    "Tai Chi",
    "Tapas",
    "Tennis",
    "Theme Park Day",
    "Thrifting",
    "Throw Some Darts",
    "Trampoline Park",
    "Trivia Night",
    "Try New Restaurant",
    "Ultimate Frisbee",
    "Visit an Animal Farm",
    "Visit Botanical Garden",
    "Visit Gallery",
    "Visit Wineries",
    "Volleyball",
    "Volunteering",
    "Wakeboarding",
    "Walk Together",
    "Watch F1",
    "Watch Game Live",
    "Watch the Game",
    "Weekend Getaway",
    "Whale Watching",
    "Whiskey Tasting",
    "White Water Rafting",
    "Wine Tasting",
    "Workout Class",
    "Workout Sesh",
    "Yoga",
    "Zip Lining",
    "Zoo",
    "Zoom Catch-Up"
}

# Top ten US cities by population
CITIES = {
    "New York City, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Phoenix, AZ",
    "Philadelphia, PA",
    "San Antonio, TX",
    "San Diego, CA",
    "Dallas, TX",
    "Jacksonville, FL"
}

def search_text(activity: str, location: str, fields: list[str]):
    """Searches for businesses fitting activity in the location provided"""

    # Create a client
    client = places_v1.PlacesClient()

    # Initialize request argument(s)
    request = places_v1.SearchTextRequest(
        text_query = f"{activity} in {location}",
    )

    # Define the field mask in metadata
    field_mask = ','.join(fields)

    # Make the request
    response = client.search_text(request, metadata=[("x-goog-fieldmask", field_mask)])

    db.store_places(response.places)

    # Handle the response
    print(response)

from shared.schema import ArticleStatus

#sample_search_text("bars", "San Francisco, CA", INCLUDED_FIELDS)
db.initialize_database()
# search_text("Wineries", "Berkeley, CA", INCLUDED_FIELDS)
db.update_place_status("ChIJG6etHvx_hYARBM3DExZDaFc", ArticleStatus.REJECTED)
places = db.get_places_by_status(ArticleStatus.REJECTED)
# reviews = db.get_reviews()
for place in places:
    print(place)
