import os, json
from sqlalchemy import create_engine, text, TextClause
from sqlalchemy.exc import SQLAlchemyError
from staging.schema import PlaceData, Review, ArticleStatus, Location

# Database config
DB_USER = os.getenv("DB_USER", "aiuser")
DB_PASS = os.getenv("DB_PASS", "aipassword")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aidb")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, echo=False)


def get_places(query: TextClause, params: dict) -> list[PlaceData]:
    """Returns a list of places that match the SQL query string"""
    places = []
    try:
        with engine.connect() as conn:
            result = conn.execute(query, params)
            for row in result.mappings():
                places.append(
                    PlaceData(
                        place_name=row["name"],
                        place_id=row["id"],
                        general_summary=row["editorial_summary"],
                        rating=row["rating"],
                        reviews_count=row["reviews_count"],
                        formatted_address=row["address"],
                        business_url=row["business_site"],
                        location=Location(row["city"],row["state"],row["country"]),
                        types=json.loads(row["types"]),
                        primary_type=row["primary_type"]
                    )
                )
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
    return places

def get_places_by_status(status: ArticleStatus) -> list[PlaceData]:
    """Returns a list of all the places with the given article status"""
    query = text("SELECT * FROM places WHERE status = :status")
    params = { "status": status.value }
    return get_places(query, params)

def get_place(place_id: str) -> PlaceData:
    """Returns a single place with the given place_id"""
    query = text("SELECT * FROM places WHERE id = :place_id")
    params = { "place_id": place_id }
    places = get_places(query, params)
    return places[0] if places else None

def get_reviews(place_id: str) -> list[Review]:
    """Returns the reviews for a given place_id"""
    reviews = []
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT author_name, author_uri, author_photo, rating, publish_time, review_text FROM reviews WHERE place_id = :pid"),
                {"pid": place_id}
            )
            for row in result.mappings():
                reviews.append(
                    Review(
                        author_name=row["author_name"],
                        author_profile_url=row["author_uri"],
                        author_photo_url=row["author_photo"],
                        rating=row["rating"],
                        time_published=row["publish_time"],
                        content=row["review_text"]
                    )
                )
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
    return reviews

def get_images(place_id: str) -> list[str]:
    """Returns a list of uris that point to the photos for the given place_id"""
    images = []
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT url FROM images WHERE place_id = :pid"),
                {"pid": place_id}
            )
            for row in result.mappings():
                images.append(row["url"])
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
    return images

def store_places(places: list[PlaceData]):
    """Stores the place data of a list of places
    
    If you only need to store a single place, pass in a list with one item
    """
    try:
        with engine.begin() as conn:  # Automatically commits
            for place in places:
                conn.execute(text("""
                    INSERT INTO places (id, name, address, rating, reviews_count, editorial_summary, business_site, city, state, country, types, primary_type, status)
                    VALUES (:id, :name, :address, :rating, :reviews_count, :summary, :site, :city, :state, :country, :types, :primary_type, :status)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": place.place_id,
                    "name": place.place_name,
                    "address": place.formatted_address,
                    "rating": place.rating,
                    "reviews_count": place.reviews_count,
                    "summary": place.general_summary,
                    "site": place.business_url,
                    "city": place.location.city,
                    "state": place.location.state,
                    "country": place.location.country,
                    "types": json.dumps(place.types),
                    "primary_type": place.primary_type,
                    "status": ArticleStatus.SCOUTED.value
                })
    except SQLAlchemyError as e:
        print(f"Database error: {e}")

def store_reviews(reviews: list[Review], place_id: str):
    """Stores the reviews in the reviews table
    
    Retrieve these reviews with the place_id you store them under
    """
    try:
        with engine.begin() as conn:
            for review in reviews:
                conn.execute(text("""
                    INSERT INTO reviews (place_id, author_name, author_uri, author_photo, rating, publish_time, review_text)
                    VALUES (:place_id, :name, :uri, :photo, :rating, :time, :text)
                """), {
                    "place_id": place_id,
                    "name": review.author_name,
                    "uri": review.author_profile_url,
                    "photo": review.author_photo_url,
                    "rating": review.rating,
                    "time": review.time_published,
                    "text": review.content
                })
    except SQLAlchemyError as e:
        print(f"Database error: {e}")

def store_images(images: list[str], place_id: str):
    """Stores the list of image uris in the respective table
    
    Retrieve these image uris with the place_id you store them under
    """
    try:
        with engine.begin() as conn:
            for uri in images:
                conn.execute(text("""
                    INSERT INTO images (place_id, uri)
                    VALUES (:place_id, :uri)
                """), {
                    "place_id": place_id,
                    "uri": uri
                })
    except SQLAlchemyError as e:
        print(f"Database error: {e}")

def update_place_status(place_id: str, new_status: ArticleStatus):
    """Modifies the status of the data store under place_id"""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE places SET status = :status WHERE id = :id"),
                {"status": new_status.value, "id": place_id}
            )
    except SQLAlchemyError as e:
        print(f"Database error: {e}")