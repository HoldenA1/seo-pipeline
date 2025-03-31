"""Defines the schema for article data pulled from the CMS"""

from dataclasses import dataclass

@dataclass
class Review:
    """Represents a user generated review from Google."""
    author_name: str
    author_profile_url: str
    author_photo_url: str
    rating: int
    time_published: str
    content: str

@dataclass
class Article:
    title: str
    place_name: str
    place_id: str
    general_summary: str
    seo_meta: str
    rating: float
    reviews_count: int
    reviews_summary: str
    reviews: list[Review]
    detailed_info: str
    formatted_address: str
    business_url: str
    city: str
    sources: list[str]
    images: list[dict]
    slug: str