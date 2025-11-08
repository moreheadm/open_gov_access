"""
SF Board of Supervisors scraper implementation
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urljoin
import time

import sys
sys.path.append('..')
from scrapers.base import Scraper


class SFBOSScraper(Scraper):
    """Scraper for SF Board of Supervisors meetings"""
    
    BASE_URL = "https://sfbos.org"
    MEETINGS_URL = "https://sfbos.org/meetings/full-board-meetings"
    
    def __init__(self, state_dir="data/state"):
        super().__init__(state_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SupervisorVotesBot/1.0)'
        })
    
    def source_name(self) -> str:
        return "sfbos"
    
    def discover(self) -> List[Dict[str, Any]]:
        """Discover available meeting documents"""
        documents = []
        
        try:
            # Fetch meetings page
            response = self.session.get(self.MEETINGS_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links to agendas and minutes
            links = soup.find_all('a', href=True)
            
            # Track meetings by date
            meetings = {}
            
            for link in links:
                href = link.get('href', '')
                
                # Look for agenda/minutes links
                if 'agenda' not in href.lower() and 'minutes' not in href.lower():
                    continue
                
                # Extract date from URL (e.g., bag102825 = October 28, 2025)
                date = self._extract_date_from_url(href)
                if not date:
                    continue
                
                # Determine document type
                doc_type = 'minutes' if 'minutes' in href.lower() else 'agenda'
                
                # Create meeting entry
                date_key = date.date()
                if date_key not in meetings:
                    meetings[date_key] = {'date': date, 'agenda': None, 'minutes': None}
                
                # Add URL
                full_url = urljoin(self.BASE_URL, href)
                meetings[date_key][doc_type] = full_url
            
            # Convert to document list (prioritize minutes over agendas for voting data)
            for date_key, meeting in sorted(meetings.items(), reverse=True):
                # Add minutes if available (has voting records)
                if meeting['minutes']:
                    documents.append({
                        'url': meeting['minutes'],
                        'doc_type': 'minutes',
                        'date': meeting['date'],
                        'metadata': {'meeting_date': date_key.isoformat()}
                    })
                
                # Also add agenda for reference
                if meeting['agenda']:
                    documents.append({
                        'url': meeting['agenda'],
                        'doc_type': 'agenda',
                        'date': meeting['date'],
                        'metadata': {'meeting_date': date_key.isoformat()}
                    })
        
        except Exception as e:
            print(f"Error discovering documents: {e}")
        
        return documents
    
    def _extract_date_from_url(self, url: str) -> datetime:
        """
        Extract date from SF BOS URL pattern
        Example: bag102825 = October 28, 2025
        """
        match = re.search(r'bag(\d{2})(\d{2})(\d{2})', url)
        if match:
            month, day, year = match.groups()
            year = f"20{year}"
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        return None
    
    def fetch(self, doc_meta: Dict[str, Any]) -> bytes:
        """Download PDF document"""
        try:
            response = self.session.get(doc_meta['url'], timeout=30)
            response.raise_for_status()
            time.sleep(1)  # Be polite
            return response.content
        except Exception as e:
            raise Exception(f"Failed to fetch {doc_meta['url']}: {e}")
    
    def parse(self, doc: 'ScrapedDocument') -> Dict[str, Any]:
        """
        Parse structured data from document
        This will be handled by the ETL pipeline
        """
        return {
            'doc_id': doc.doc_id,
            'source': doc.source,
            'doc_type': doc.doc_type,
            'date': doc.date.isoformat(),
            'url': doc.url,
            'raw_size': len(doc.raw_content)
        }


if __name__ == "__main__":
    # Test the scraper
    scraper = SFBOSScraper()
    
    # Discover documents
    docs = scraper.discover()
    print(f"\nFound {len(docs)} documents")
    
    if docs:
        print("\nFirst 3 documents:")
        for doc in docs[:3]:
            print(f"  {doc['date'].date()} - {doc['doc_type']}")
            print(f"    {doc['url']}")
