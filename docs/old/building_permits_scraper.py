"""
SF Building Permits Scraper (Example)
Demonstrates how to extend BaseDataSourceScraper for a different data source

This scraper works with SF OpenData API for building permits
"""

import requests
import csv
from io import StringIO
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

from base_scraper import BaseDataSourceScraper, Document


class SFBuildingPermitsScraper(BaseDataSourceScraper):
    """
    Scraper for SF Building Permits from OpenData portal
    API: https://data.sfgov.org/Housing-and-Buildings/Building-Permits/i98e-djp9
    """
    
    API_BASE = "https://data.sfgov.org/resource/i98e-djp9.json"
    API_LIMIT = 1000  # Records per request
    
    def __init__(self, output_dir: str = "data/building_permits"):
        super().__init__(output_dir, "SF Building Permits")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; CivicDataBot/1.0)'
        })
    
    def discover_documents(self) -> List[Document]:
        """
        Discover building permits from the SF OpenData API
        Each permit becomes a 'document'
        """
        documents = []
        
        try:
            # Query the API for recent permits
            # In production, you'd paginate through all records
            print(f"  Fetching permits from OpenData API...")
            
            params = {
                '$limit': self.API_LIMIT,
                '$order': 'filed_date DESC',
                '$where': "filed_date IS NOT NULL"
            }
            
            response = self.session.get(self.API_BASE, params=params, timeout=30)
            response.raise_for_status()
            
            permits = response.json()
            print(f"  Found {len(permits)} permits")
            
            # Convert each permit to a Document
            for permit in permits:
                permit_number = permit.get('permit_number', 'unknown')
                filed_date = permit.get('filed_date', 'unknown')[:10]  # YYYY-MM-DD
                
                # Generate unique document ID
                doc_id = Document.generate_id(
                    f"permit_{permit_number}",
                    'building_permit',
                    filed_date
                )
                
                doc = Document(
                    doc_id=doc_id,
                    doc_type='building_permit',
                    url=f"https://data.sfgov.org/Housing-and-Buildings/Building-Permits/i98e-djp9?permit_number={permit_number}",
                    date=filed_date,
                    metadata={
                        'permit_number': permit_number,
                        'address': permit.get('street_name', ''),
                        'description': permit.get('description', ''),
                        'status': permit.get('status', ''),
                        'estimated_cost': permit.get('estimated_cost', ''),
                        'source': 'SF OpenData',
                        'raw_permit_data': permit  # Store full permit data
                    }
                )
                documents.append(doc)
            
        except Exception as e:
            print(f"  ✗ Error discovering permits: {e}")
        
        return documents
    
    def download_document(self, doc: Document) -> bool:
        """
        'Download' a permit record by saving the JSON data
        For API sources, we already have the data, so just save it
        """
        try:
            # Create filename based on permit number and date
            permit_number = doc.metadata.get('permit_number', 'unknown')
            filename = f"{doc.date}_{permit_number}.json"
            output_path = self.raw_dir / filename
            
            # Save permit data as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(doc.metadata['raw_permit_data'], f, indent=2)
            
            doc.original_path = output_path
            return True
            
        except Exception as e:
            print(f"    ✗ Save error: {e}")
            return False
    
    def extract_text(self, doc: Document) -> str:
        """
        Extract searchable text from permit data
        Convert structured JSON to readable text format
        """
        try:
            permit = doc.metadata['raw_permit_data']
            
            # Format as readable text
            text_parts = [
                f"BUILDING PERMIT: {permit.get('permit_number', 'N/A')}",
                f"Filed Date: {permit.get('filed_date', 'N/A')}",
                f"Status: {permit.get('status', 'N/A')}",
                f"",
                f"Location:",
                f"  Address: {permit.get('street_number', '')} {permit.get('street_name', '')}",
                f"  Block: {permit.get('block', 'N/A')}",
                f"  Lot: {permit.get('lot', 'N/A')}",
                f"",
                f"Description:",
                f"  {permit.get('description', 'No description provided')}",
                f"",
                f"Details:",
                f"  Permit Type: {permit.get('permit_type', 'N/A')}",
                f"  Estimated Cost: ${permit.get('estimated_cost', '0')}",
                f"  Proposed Units: {permit.get('proposed_units', 'N/A')}",
                f"  Existing Units: {permit.get('existing_units', 'N/A')}",
            ]
            
            # Add applicant info if available
            if permit.get('applicant'):
                text_parts.extend([
                    f"",
                    f"Applicant:",
                    f"  {permit.get('applicant', 'N/A')}"
                ])
            
            return "\n".join(text_parts)
            
        except Exception as e:
            print(f"    ✗ Text extraction error: {e}")
            return ""


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scrape SF Building Permits from OpenData'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Limit number of permits to scrape (default: 100)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-scrape of existing permits'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset scraper state (clear all history)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/building_permits',
        help='Output directory (default: data/building_permits)'
    )
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = SFBuildingPermitsScraper(output_dir=args.output)
    
    # Reset state if requested
    if args.reset:
        scraper.reset_state()
        return
    
    # Run scraper
    documents = scraper.scrape(limit=args.limit, force=args.force)
    
    # Print results
    print(f"\n✓ Successfully processed {len(documents)} permits")


if __name__ == "__main__":
    main()
