"""
Generic scraper framework for data sources.

Provides an abstract Scraper class that can be extended for different data sources.
Incremental scraping is database-driven (checks for existing URLs in the database).
"""

from abc import ABC, abstractmethod
from typing import Generator, Optional, Union


class Scraper(ABC):
    """
    Abstract base class for data source scrapers.

    Subclasses must implement:
    - source_name(): Return the name of the data source
    - scrape(): Main scraping method that yields database models

    Incremental scraping is database-driven: pass a SQLAlchemy session to check
    for existing URLs in the database.
    """

    def __init__(self):
        """Initialize scraper."""
        pass

    @abstractmethod
    def source_name(self) -> str:
        """
        Return the name of this data source.

        Returns:
            Source name (e.g., "sfbos", "legistar")
        """
        pass

    @abstractmethod
    def scrape(
        self,
        limit: Optional[int] = None,
        incremental: bool = True,
        force: bool = False
    ) -> Generator[Union['Document', 'Legislation', 'Official', 'Meeting', 'Action'], None, None]:
        """
        Main scraping method.

        Discovers and fetches data from the data source.
        Yields database models (not yet persisted).

        Args:
            limit: Maximum number of items to scrape
            incremental: Only scrape new items (check database for existing URLs)
            force: Force re-scrape even if already in database

        Yields:
            Database models (Document, Legislation, Official, Meeting, or Action)
        """
        pass

