"""Defines the schema for article data pulled from the CMS"""

from dataclasses import dataclass
from enum import Enum

class ArticleStatus(Enum):
    """Represents the state of an article"""
    SCOUTED = 0 # Places that were just found by the scout
    FILTERED = 1 # Places validated by the scout. Ready for author
    PUBLISHED = 2 # Author has published article
    NEEDS_UPDATE = 3 # Info has changed since article was published
    REJECTED = 4 # Filtered out by the scout

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
    """Represents everything that is stored in the CMS"""
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
    timestamp: str

@dataclass
class PlaceData:
    """Represents the data scraped from Google"""
    place_name: str
    place_id: str
    general_summary: str
    rating: float
    reviews_count: int
    formatted_address: str
    business_url: str
    city: str