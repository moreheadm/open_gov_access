"""
Base scraper framework for civic data sources
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import hashlib


@dataclass
class ScrapedDocument:
    """Represents a scraped document"""
    doc_id: str
    source: str
    doc_type: str
    date: datetime
    url: str
    raw_content: bytes
    metadata: Dict[str, Any]
    scraped_at: datetime


class ScraperState:
    """Manages incremental scraping state"""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.scraped_docs = set()
        self._load()
    
    def _load(self):
        """Load state from disk"""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.scraped_docs = set(data.get('scraped_docs', []))
            except Exception as e:
                print(f"Warning: Could not load state: {e}")
    
    def save(self):
        """Save state to disk"""
        self.state_file.write_text(json.dumps({
            'scraped_docs': list(self.scraped_docs),
            'last_updated': datetime.now().isoformat()
        }, indent=2))
    
    def is_scraped(self, doc_id: str) -> bool:
        """Check if document was already scraped"""
        return doc_id in self.scraped_docs
    
    def mark_scraped(self, doc_id: str):
        """Mark document as scraped"""
        self.scraped_docs.add(doc_id)
    
    def reset(self):
        """Clear all state"""
        self.scraped_docs.clear()
        self.save()


class Scraper(ABC):
    """
    Abstract base class for data source scrapers
    
    Subclasses must implement:
    - discover(): Find available documents
    - fetch(): Download a specific document
    - parse(): Extract structured data from document
    """
    
    def __init__(self, state_dir: Path = Path("data/state")):
        self.state_dir = Path(state_dir)
        self.state = ScraperState(self.state_dir / f"{self.source_name()}.json")
    
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source"""
        pass
    
    @abstractmethod
    def discover(self) -> List[Dict[str, Any]]:
        """
        Discover available documents to scrape
        
        Returns:
            List of document metadata dicts with at minimum:
            - url: str
            - doc_type: str  
            - date: datetime
        """
        pass
    
    @abstractmethod
    def fetch(self, doc_meta: Dict[str, Any]) -> bytes:
        """
        Fetch the raw content of a document
        
        Args:
            doc_meta: Document metadata from discover()
            
        Returns:
            Raw document content as bytes
        """
        pass
    
    @abstractmethod
    def parse(self, doc: ScrapedDocument) -> Dict[str, Any]:
        """
        Parse structured data from a scraped document
        
        Args:
            doc: ScrapedDocument with raw_content
            
        Returns:
            Structured data extracted from document
        """
        pass
    
    def _generate_doc_id(self, url: str, date: datetime, doc_type: str) -> str:
        """Generate unique document ID"""
        id_string = f"{url}|{date.isoformat()}|{doc_type}"
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]
    
    def scrape(
        self, 
        limit: Optional[int] = None,
        incremental: bool = True,
        force: bool = False
    ) -> List[ScrapedDocument]:
        """
        Main scraping method
        
        Args:
            limit: Maximum number of documents to scrape
            incremental: If True, skip already-scraped documents
            force: If True, re-scrape everything regardless of state
            
        Returns:
            List of scraped documents
        """
        print(f"🔍 Discovering documents from {self.source_name()}...")
        
        # Discover available documents
        doc_metas = self.discover()
        if limit:
            doc_metas = doc_metas[:limit]
        
        print(f"   Found {len(doc_metas)} documents")
        
        # Filter based on incremental mode
        if incremental and not force:
            new_docs = []
            for meta in doc_metas:
                doc_id = self._generate_doc_id(
                    meta['url'], 
                    meta['date'], 
                    meta['doc_type']
                )
                if not self.state.is_scraped(doc_id):
                    new_docs.append(meta)
            
            if len(new_docs) < len(doc_metas):
                print(f"   {len(doc_metas) - len(new_docs)} already scraped")
                print(f"   {len(new_docs)} new documents to process")
            doc_metas = new_docs
        
        # Scrape each document
        scraped = []
        for i, meta in enumerate(doc_metas, 1):
            print(f"\n[{i}/{len(doc_metas)}] Processing {meta['doc_type']} from {meta['date'].date()}")
            
            try:
                # Generate doc ID
                doc_id = self._generate_doc_id(
                    meta['url'],
                    meta['date'],
                    meta['doc_type']
                )
                
                # Fetch raw content
                print(f"   Downloading...")
                raw_content = self.fetch(meta)
                
                # Create document
                doc = ScrapedDocument(
                    doc_id=doc_id,
                    source=self.source_name(),
                    doc_type=meta['doc_type'],
                    date=meta['date'],
                    url=meta['url'],
                    raw_content=raw_content,
                    metadata=meta.get('metadata', {}),
                    scraped_at=datetime.now()
                )
                
                # Mark as scraped
                self.state.mark_scraped(doc_id)
                scraped.append(doc)
                
                print(f"   ✓ Success")
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
                continue
        
        # Save state
        self.state.save()
        
        print(f"\n✓ Scraped {len(scraped)}/{len(doc_metas)} documents")
        
        return scraped
    
    def reset_state(self):
        """Reset scraper state (will re-scrape everything next time)"""
        self.state.reset()
