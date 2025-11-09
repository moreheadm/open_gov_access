"""
Generic scraper framework for data sources.

Provides an abstract Scraper class that can be extended for different data sources.
Includes support for incremental scraping with state management.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional


class ScraperState:
    """
    Manages scraper state for incremental scraping.

    Tracks which documents have been scraped to avoid re-scraping.
    """

    def __init__(self, state_dir: str, scraper_name: str):
        """
        Initialize scraper state.

        Args:
            state_dir: Directory to store state files
            scraper_name: Name of the scraper (used for state file name)
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{scraper_name}_state.json"
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "scraped_urls": set(),
            "last_scrape": None,
            "metadata": {}
        }

    def _save_state(self):
        """Save state to file"""
        state_to_save = {
            "scraped_urls": list(self.state["scraped_urls"]),
            "last_scrape": self.state["last_scrape"],
            "metadata": self.state["metadata"]
        }
        with open(self.state_file, 'w') as f:
            json.dump(state_to_save, f, indent=2, default=str)

    def is_scraped(self, url: str) -> bool:
        """Check if document URL has been scraped"""
        if isinstance(self.state["scraped_urls"], list):
            self.state["scraped_urls"] = set(self.state["scraped_urls"])
        return url in self.state["scraped_urls"]

    def mark_scraped(self, url: str):
        """Mark document URL as scraped"""
        if isinstance(self.state["scraped_urls"], list):
            self.state["scraped_urls"] = set(self.state["scraped_urls"])
        if url not in self.state["scraped_urls"]:
            self.state["scraped_urls"].add(url)
            self.state["last_scrape"] = datetime.now().isoformat()
            self._save_state()

    def reset(self):
        """Reset scraper state"""
        self.state = {
            "scraped_urls": set(),
            "last_scrape": None,
            "metadata": {}
        }
        self._save_state()

    def get_metadata(self, key: str, default=None):
        """Get metadata value"""
        return self.state["metadata"].get(key, default)

    def set_metadata(self, key: str, value: Any):
        """Set metadata value"""
        self.state["metadata"][key] = value
        self._save_state()


class Scraper(ABC):
    """
    Abstract base class for data source scrapers.

    Subclasses must implement:
    - source_name(): Return the name of the data source
    - scrape(): Main scraping method that yields Document models
    """

    def __init__(self, state_dir: str = "data/state"):
        """
        Initialize scraper.

        Args:
            state_dir: Directory to store scraper state
        """
        self.state = ScraperState(state_dir, self.source_name())

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
    ) -> Generator['Document', None, None]:
        """
        Main scraping method.

        Discovers and fetches documents from the data source.
        Yields Document database models (not yet persisted).

        Args:
            limit: Maximum number of documents to scrape
            incremental: Only scrape new documents (not already in state)
            force: Force re-scrape even if already scraped

        Yields:
            Document models (from models.database)
        """
        pass

    def reset_state(self):
        """Reset scraper state"""
        self.state.reset()
        print(f"[{self.source_name()}] State reset")

