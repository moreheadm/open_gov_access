"""
Generic scraper framework for data sources.

Provides an abstract Scraper class that can be extended for different data sources.
Includes support for incremental scraping with state management.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DocumentMetadata:
    """Metadata about a document to be scraped"""
    url: str
    doc_type: str  # "agenda", "minutes", etc.
    meeting_date: datetime
    source: str
    title: Optional[str] = None
    
    @property
    def doc_id(self) -> str:
        """Generate unique document ID from URL and date"""
        content = f"{self.url}:{self.meeting_date.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ScrapedDocument:
    """A scraped document with content"""
    doc_id: str
    url: str
    doc_type: str
    meeting_date: datetime
    source: str
    raw_content: bytes  # Raw PDF/HTML content
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


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
            "scraped_docs": [],
            "last_scrape": None,
            "metadata": {}
        }
    
    def _save_state(self):
        """Save state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def is_scraped(self, doc_id: str) -> bool:
        """Check if document has been scraped"""
        return doc_id in self.state["scraped_docs"]
    
    def mark_scraped(self, doc_id: str):
        """Mark document as scraped"""
        if doc_id not in self.state["scraped_docs"]:
            self.state["scraped_docs"].append(doc_id)
            self.state["last_scrape"] = datetime.now().isoformat()
            self._save_state()
    
    def reset(self):
        """Reset scraper state"""
        self.state = {
            "scraped_docs": [],
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
    - discover(): Discover available documents
    - fetch(): Fetch a specific document
    - parse(): Parse document content (optional)
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
            Source name (e.g., "sfbos", "campaign_finance")
        """
        pass
    
    @abstractmethod
    def discover(self, limit: Optional[int] = None) -> List[DocumentMetadata]:
        """
        Discover available documents from the data source.
        
        Args:
            limit: Maximum number of documents to discover
            
        Returns:
            List of document metadata
        """
        pass
    
    @abstractmethod
    def fetch(self, doc_meta: DocumentMetadata) -> ScrapedDocument:
        """
        Fetch a specific document.
        
        Args:
            doc_meta: Document metadata
            
        Returns:
            Scraped document with content
        """
        pass
    
    def parse(self, doc: ScrapedDocument) -> Dict[str, Any]:
        """
        Parse document content (optional).
        
        Override this method to extract structured data from documents.
        
        Args:
            doc: Scraped document
            
        Returns:
            Parsed data as dictionary
        """
        return {}
    
    def scrape(
        self,
        limit: Optional[int] = None,
        incremental: bool = True,
        force: bool = False
    ) -> List[ScrapedDocument]:
        """
        Main scraping method.
        
        Discovers documents, filters based on state, and fetches them.
        
        Args:
            limit: Maximum number of documents to scrape
            incremental: Only scrape new documents (not already in state)
            force: Force re-scrape even if already scraped
            
        Returns:
            List of scraped documents
        """
        print(f"[{self.source_name()}] Discovering documents...")
        doc_metas = self.discover(limit=limit)
        print(f"[{self.source_name()}] Found {len(doc_metas)} documents")
        
        # Filter based on state
        if incremental and not force:
            doc_metas = [
                meta for meta in doc_metas
                if not self.state.is_scraped(meta.doc_id)
            ]
            print(f"[{self.source_name()}] {len(doc_metas)} new documents to scrape")
        
        if not doc_metas:
            print(f"[{self.source_name()}] No documents to scrape")
            return []
        
        # Fetch documents
        scraped_docs = []
        for i, meta in enumerate(doc_metas, 1):
            try:
                print(f"[{self.source_name()}] Fetching {i}/{len(doc_metas)}: {meta.url}")
                doc = self.fetch(meta)
                scraped_docs.append(doc)
                
                # Mark as scraped
                if not force:
                    self.state.mark_scraped(doc.doc_id)
                    
            except Exception as e:
                print(f"[{self.source_name()}] Error fetching {meta.url}: {e}")
                continue
        
        print(f"[{self.source_name()}] Successfully scraped {len(scraped_docs)} documents")
        return scraped_docs
    
    def reset_state(self):
        """Reset scraper state"""
        self.state.reset()
        print(f"[{self.source_name()}] State reset")

