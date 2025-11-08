"""
Base Data Source Scraper
Generic scraper framework for civic data sources
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Set
import json
from datetime import datetime
import hashlib


class Document:
    """Represents a scraped document"""
    
    def __init__(self, doc_id: str, doc_type: str, url: str, date: str, metadata: Dict = None):
        self.doc_id = doc_id
        self.doc_type = doc_type
        self.url = url
        self.date = date
        self.metadata = metadata or {}
        self.original_path: Optional[Path] = None
        self.text_path: Optional[Path] = None
        self.text_content: Optional[str] = None
        self.scraped_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "url": self.url,
            "date": self.date,
            "metadata": self.metadata,
            "original_path": str(self.original_path) if self.original_path else None,
            "text_path": str(self.text_path) if self.text_path else None,
            "scraped_at": self.scraped_at,
        }
    
    @staticmethod
    def generate_id(url: str, doc_type: str, date: str) -> str:
        """Generate a unique document ID from URL, type, and date"""
        id_string = f"{url}|{doc_type}|{date}"
        return hashlib.md5(id_string.encode()).hexdigest()[:12]


class ScraperState:
    """Manages scraper state for incremental scraping"""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.scraped_ids: Set[str] = set()
        self.load()
    
    def load(self):
        """Load state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.scraped_ids = set(data.get('scraped_ids', []))
            except Exception as e:
                print(f"Warning: Could not load state file: {e}")
                self.scraped_ids = set()
    
    def save(self):
        """Save state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'scraped_ids': list(self.scraped_ids),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state file: {e}")
    
    def is_scraped(self, doc_id: str) -> bool:
        """Check if a document has been scraped"""
        return doc_id in self.scraped_ids
    
    def mark_scraped(self, doc_id: str):
        """Mark a document as scraped"""
        self.scraped_ids.add(doc_id)
    
    def reset(self):
        """Clear all state"""
        self.scraped_ids = set()
        self.save()


class BaseDataSourceScraper(ABC):
    """
    Abstract base class for data source scrapers
    Handles common functionality: state management, file organization, deduplication
    """
    
    def __init__(self, output_dir: str, source_name: str):
        self.source_name = source_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.raw_dir = self.output_dir / "raw"
        self.text_dir = self.output_dir / "text"
        self.metadata_dir = self.output_dir / "metadata"
        self.state_dir = self.output_dir / ".state"
        
        for d in [self.raw_dir, self.text_dir, self.metadata_dir, self.state_dir]:
            d.mkdir(exist_ok=True)
        
        # Initialize state management
        self.state = ScraperState(self.state_dir / "scraper_state.json")
        
        # Statistics
        self.stats = {
            'total_found': 0,
            'new_documents': 0,
            'skipped_existing': 0,
            'failed': 0
        }
    
    @abstractmethod
    def discover_documents(self) -> List[Document]:
        """
        Discover available documents to scrape
        Returns: List of Document objects (not yet downloaded)
        """
        pass
    
    @abstractmethod
    def download_document(self, doc: Document) -> bool:
        """
        Download a document and save to raw_dir
        Returns: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def extract_text(self, doc: Document) -> str:
        """
        Extract text from a downloaded document
        Returns: Extracted text content
        """
        pass
    
    def process_document(self, doc: Document, force: bool = False) -> bool:
        """
        Complete processing pipeline for a document
        Returns: True if successful, False otherwise
        """
        # Check if already scraped
        if not force and self.state.is_scraped(doc.doc_id):
            print(f"  ⏭️  Skipping (already scraped): {doc.doc_id}")
            self.stats['skipped_existing'] += 1
            return True
        
        try:
            # Download
            if not self.download_document(doc):
                self.stats['failed'] += 1
                return False
            
            # Extract text
            text_content = self.extract_text(doc)
            if not text_content:
                print(f"  ⚠️  Warning: No text extracted from {doc.doc_id}")
                self.stats['failed'] += 1
                return False
            
            doc.text_content = text_content
            
            # Save text file
            text_filename = f"{doc.doc_id}.txt"
            text_path = self.text_dir / text_filename
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            doc.text_path = text_path
            
            # Save metadata
            metadata_path = self.metadata_dir / f"{doc.doc_id}.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(doc.to_dict(), f, indent=2)
            
            # Mark as scraped
            self.state.mark_scraped(doc.doc_id)
            self.stats['new_documents'] += 1
            
            print(f"  ✓ Processed: {doc.doc_id}")
            return True
            
        except Exception as e:
            print(f"  ✗ Error processing {doc.doc_id}: {e}")
            self.stats['failed'] += 1
            return False
    
    def scrape(self, limit: Optional[int] = None, force: bool = False) -> List[Document]:
        """
        Main scraping method
        
        Args:
            limit: Maximum number of documents to discover
            force: If True, re-scrape even if already processed
        
        Returns:
            List of successfully processed documents
        """
        print("=" * 70)
        print(f"{self.source_name} Scraper")
        print("=" * 70)
        
        # Discover available documents
        print("\n🔍 Discovering documents...")
        all_documents = self.discover_documents()
        
        if limit:
            all_documents = all_documents[:limit]
        
        self.stats['total_found'] = len(all_documents)
        print(f"Found {len(all_documents)} documents")
        
        # Filter out already-scraped documents (unless force=True)
        if not force:
            new_documents = [doc for doc in all_documents if not self.state.is_scraped(doc.doc_id)]
            if len(new_documents) < len(all_documents):
                print(f"   {len(all_documents) - len(new_documents)} already scraped")
                print(f"   {len(new_documents)} new documents to process")
            documents_to_process = new_documents
        else:
            print("   Force mode: re-scraping all documents")
            documents_to_process = all_documents
        
        # Process each document
        processed_documents = []
        for i, doc in enumerate(documents_to_process, 1):
            print(f"\n[{i}/{len(documents_to_process)}] Processing: {doc.date} - {doc.doc_type}")
            if self.process_document(doc, force=force):
                processed_documents.append(doc)
        
        # Save state
        self.state.save()
        
        # Print summary
        self._print_summary()
        
        return processed_documents
    
    def _print_summary(self):
        """Print scraping summary"""
        print("\n" + "=" * 70)
        print("Scraping Summary")
        print("=" * 70)
        print(f"Total documents found:    {self.stats['total_found']}")
        print(f"New documents processed:  {self.stats['new_documents']}")
        print(f"Already scraped (skipped): {self.stats['skipped_existing']}")
        print(f"Failed:                   {self.stats['failed']}")
        print(f"\nOutput directory: {self.output_dir.absolute()}")
        print("=" * 70)
    
    def reset_state(self):
        """Reset scraper state (will re-scrape everything)"""
        print("⚠️  Resetting scraper state...")
        self.state.reset()
        print("✓ State reset. Next scrape will process all documents.")
