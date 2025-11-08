"""
Demo: Incremental Scraping
Shows how the scraper only processes new documents on subsequent runs
"""

import sys
sys.path.insert(0, '/home/claude')

from base_scraper import BaseDataSourceScraper, Document
from typing import List
import time


class MockDataSourceScraper(BaseDataSourceScraper):
    """
    Mock scraper that simulates a data source with growing content
    """
    
    def __init__(self, output_dir: str = "data/mock_demo", num_docs: int = 5):
        super().__init__(output_dir, "Mock Data Source (Demo)")
        self.num_docs = num_docs
    
    def discover_documents(self) -> List[Document]:
        """Simulate discovering documents"""
        documents = []
        
        for i in range(1, self.num_docs + 1):
            doc = Document(
                doc_id=f"doc_{i:03d}",
                doc_type="report",
                url=f"https://example.com/doc{i}.pdf",
                date=f"2025-11-{i:02d}",
                metadata={"number": i}
            )
            documents.append(doc)
        
        return documents
    
    def download_document(self, doc: Document) -> bool:
        """Simulate downloading"""
        filename = f"{doc.doc_id}.txt"
        path = self.raw_dir / filename
        
        # Simulate download with fake content
        with open(path, 'w') as f:
            f.write(f"This is document {doc.doc_id}\n")
        
        doc.original_path = path
        time.sleep(0.1)  # Simulate network delay
        return True
    
    def extract_text(self, doc: Document) -> str:
        """Simulate text extraction"""
        return f"Document {doc.doc_id}\nDate: {doc.date}\nContent goes here..."


def main():
    """Demonstrate incremental scraping"""
    
    print("\n" + "=" * 70)
    print("DEMO: Incremental Scraping")
    print("=" * 70)
    
    # Run 1: Scrape 5 documents
    print("\n🔵 RUN 1: Initial scrape with 5 documents")
    print("-" * 70)
    scraper = MockDataSourceScraper(num_docs=5)
    scraper.scrape()
    
    input("\nPress Enter to continue to Run 2...")
    
    # Run 2: Same 5 documents (should skip all)
    print("\n🔵 RUN 2: Same 5 documents (expect: all skipped)")
    print("-" * 70)
    scraper = MockDataSourceScraper(num_docs=5)
    scraper.scrape()
    
    input("\nPress Enter to continue to Run 3...")
    
    # Run 3: 8 documents (3 new)
    print("\n🔵 RUN 3: Now 8 documents available (expect: 5 skipped, 3 new)")
    print("-" * 70)
    scraper = MockDataSourceScraper(num_docs=8)
    scraper.scrape()
    
    input("\nPress Enter to continue to Run 4...")
    
    # Run 4: Force re-scrape all 8
    print("\n🔵 RUN 4: Force re-scrape all 8 documents")
    print("-" * 70)
    scraper = MockDataSourceScraper(num_docs=8)
    scraper.scrape(force=True)
    
    input("\nPress Enter to see state file...")
    
    # Show state file
    print("\n📄 State File Contents:")
    print("-" * 70)
    state_file = scraper.state_dir / "scraper_state.json"
    with open(state_file) as f:
        print(f.read())
    
    print("\n✅ Demo complete! Key takeaways:")
    print("   1. First run: processes all documents")
    print("   2. Second run: skips everything (already scraped)")
    print("   3. Third run: only processes new documents")
    print("   4. Force mode: re-processes everything")
    print("   5. State is persistent across runs")


if __name__ == "__main__":
    main()
