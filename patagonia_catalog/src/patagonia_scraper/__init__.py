"""Patagonia Japan catalogue scraper."""

from .constants import OUTPUT_COLUMNS
from .scraper import PatagoniaScraper, ScraperConfig

__all__ = ["OUTPUT_COLUMNS", "PatagoniaScraper", "ScraperConfig"]
