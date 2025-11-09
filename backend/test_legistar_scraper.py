#!/usr/bin/env python3
"""
Quick test script for the Legistar scraper.
"""

from scrapers.legistar import LegistarScraper


def main():
    print("Testing Legistar Scraper...")
    print("=" * 60)

    # Create scraper instance
    scraper = LegistarScraper(state_dir="data/state", headless=False)

    # Test scraping with a small limit
    try:
        count = 0
        for doc in scraper.scrape(
            limit=5,  # Only scrape 5 documents for testing
            incremental=False,  # Don't use state management for testing
            force=True,  # Force re-scrape
            department="BOS and Committees",
            year="2025"
        ):
            count += 1
            print(f"\nDocument {count}:")
            print(f"  Source: {doc.source}")
            print(f"  URL: {doc.url}")
            print(f"  Format: {doc.content_format}")
            print(f"  Content length: {len(doc.raw_content)} chars")

        print("\n" + "=" * 60)
        print(f"Successfully scraped {count} documents")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during scraping: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

