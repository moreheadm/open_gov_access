"""
Legistar scraper for SF Board of Supervisors.

Scrapes meeting data from https://sfgov.legistar.com/Calendar.aspx
"""

import re
import time
from datetime import datetime
from typing import Generator, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import Scraper
from models.database import Document, ContentFormat
from utils.llm import convert_transcript_to_markdown
from utils.transcript_parser import NonAITranscriptParser
from sqlalchemy.orm import Session


class LegistarScraper(Scraper):
    """
    Scraper for SF Board of Supervisors Legistar calendar.
    
    Scrapes from: https://sfgov.legistar.com/Calendar.aspx
    """
    
    BASE_URL = "https://sfgov.legistar.com"
    CALENDAR_URL = "https://sfgov.legistar.com/Calendar.aspx"
    
    def __init__(self, headless: bool = True, convert_with_ai: bool = False, use_non_ai_parsing: bool = True):
        """
        Initialize Legistar scraper.

        Args:
            headless: Whether to run browser in headless mode
            convert_with_ai: Whether to convert documents with AI (default: False)
            use_non_ai_parsing: Whether to use non-AI transcript parsing
        """
        super().__init__()
        self.headless = headless
        self.convert_with_ai = convert_with_ai

    def source_name(self) -> str:
        return "legistar"
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=options)
        return driver
    
    def scrape(
        self,
        limit: Optional[int] = None,
        incremental: bool = True,
        force: bool = False,
        department: str = "BOS and Committees",
        year: str = "2025",
        session: Optional[Session] = None
    ) -> Generator[Document, None, None]:
        """
        Main scraping method.

        Navigates Legistar calendar, filters by department and year,
        and yields Document models.

        Args:
            limit: Maximum number of documents to scrape
            incremental: Only scrape new documents (not already in database)
            force: Force re-scrape even if already in database
            department: Department filter (default: "BOS and Committees")
            year: Year filter (default: "2025")
            session: SQLAlchemy session for checking existing URLs

        Yields:
            Document models (not yet persisted to database)
        """
        print(f"[{self.source_name()}] Starting Legistar scrape...")
        print(f"[{self.source_name()}] Department: {department}, Year: {year}")

        driver = None
        try:
            driver = self._setup_driver()

            # Navigate to calendar page
            print(f"[{self.source_name()}] Navigating to {self.CALENDAR_URL}")
            driver.get(self.CALENDAR_URL)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_lstBodies_Input"))
            )

            # Set department filter
            print(f"[{self.source_name()}] Setting department filter to '{department}'")
            self._set_dropdown(driver, "ctl00_ContentPlaceHolder1_lstBodies_Input", department)

            # Set year filter
            print(f"[{self.source_name()}] Setting year filter to '{year}'")
            self._set_dropdown(driver, "ctl00_ContentPlaceHolder1_lstYears_Input", year)

            # Click the Search Calendar button
            print(f"[{self.source_name()}] Clicking Search Calendar button")
            search_button = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSearch")
            search_button.click()

            # Wait for grid to load
            time.sleep(3)

            # Process pages and yield documents
            page_num = 1
            count = 0

            while True:
                print(f"[{self.source_name()}] Processing page {page_num}")

                # Get page source and parse with BeautifulSoup
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')

                # Find the calendar grid table
                grid = soup.find('table', id=re.compile(r'gridCalendar'))
                if not grid:
                    break

                # Find all rows in the table body
                rows = grid.find_all('tr', class_=re.compile(r'rgRow|rgAltRow'))

                for row in rows:
                    if limit and count >= limit:
                        return

                    try:
                        # Find all links in the row
                        links = row.find_all('a')

                        for link in links:
                            if limit and count >= limit:
                                return

                            onclick = link.get('onclick', '')
                            link_text = link.get_text(strip=True).lower()

                            # Extract URL from onclick attribute
                            url = self._extract_url_from_onclick(onclick)
                            if not url:
                                continue

                            # Make URL absolute
                            if url.startswith('/'):
                                url = self.BASE_URL + url
                            elif not url.startswith('http'):
                                url = self.BASE_URL + '/' + url

                            # Check if already in database (incremental by default)
                            if incremental and not force and session:
                                existing = session.query(Document).filter_by(url=url).first()
                                if existing:
                                    print(f"[{self.source_name()}] Skipping (already in database): {url}")
                                    continue

                            # Determine document type and content format
                            if 'transcript' in link_text:
                                doc_type = 'transcript'
                                content_format = ContentFormat.HTML
                            elif 'meeting detail' in link_text or 'detail' in link_text:
                                # skip meeting details
                                doc_type = 'meeting_details'
                                content_format = ContentFormat.HTML
                                continue
                            else:
                                continue  # Skip other link types

                            # Fetch the document
                            try:
                                print(f"[{self.source_name()}] Fetching: {url}")
                                driver.get(url)
                                time.sleep(2)

                                # Get page source
                                page_content = driver.page_source

                                # For transcripts, extract and convert to markdown (if enabled)
                                converted_content = None
                                if doc_type == 'transcript' and self.convert_with_ai:
                                    converted_content = self._extract_and_convert_transcript(page_content)

                                # Create Document model
                                doc = Document(
                                    source=self.source_name(),
                                    url=url,
                                    raw_content=page_content,
                                    content_format=content_format,
                                    converted_content=converted_content
                                )

                                count += 1
                                yield doc

                            except Exception as e:
                                print(f"[{self.source_name()}] Error fetching {url}: {e}")
                                continue

                    except Exception as e:
                        print(f"[{self.source_name()}] Error parsing row: {e}")
                        continue

                # Try to navigate to next page
                if not self._go_to_next_page(driver, page_num + 1):
                    print(f"[{self.source_name()}] No more pages")
                    break

                page_num += 1
                time.sleep(1)  # Be polite

            print(f"[{self.source_name()}] Successfully scraped {count} documents")

        finally:
            if driver:
                driver.quit()
    
    def _set_dropdown(self, driver: webdriver.Chrome, input_id: str, value: str):
        """
        Set a dropdown value by clicking the input and selecting from the dropdown.
        
        Args:
            driver: Selenium WebDriver
            input_id: ID of the input element
            value: Value to select
        """
        try:
            # Click the input to open dropdown
            input_elem = driver.find_element(By.ID, input_id)
            input_elem.click()
            
            # Wait for dropdown to appear
            time.sleep(0.5)
            
            # Find and click the option with the desired value
            # The dropdown items are typically in a list with class 'rcbList'
            dropdown_items = driver.find_elements(By.CSS_SELECTOR, ".rcbList li")
            for item in dropdown_items:
                if item.text.strip() == value:
                    item.click()
                    time.sleep(0.5)
                    return
            
            print(f"[{self.source_name()}] Warning: Could not find dropdown option '{value}'")
            
        except Exception as e:
            print(f"[{self.source_name()}] Error setting dropdown: {e}")
    
    def _go_to_next_page(self, driver: webdriver.Chrome, page_num: int) -> bool:
        """
        Navigate to the next page in the paginator.
        
        Args:
            driver: Selenium WebDriver
            page_num: Page number to navigate to
            
        Returns:
            True if navigation was successful, False otherwise
        """
        try:
            # Look for the page link in the paginator
            page_link = driver.find_element(
                By.XPATH, 
                f"//div[@id='ctl00_ContentPlaceHolder1_gridCalendar_ctl00NPPHTop']//a[span[text()='{page_num}']]"
            )
            
            # Click the page link
            page_link.click()
            
            # Wait for page to load
            time.sleep(2)
            
            return True
            
        except NoSuchElementException:
            return False
        except Exception as e:
            print(f"[{self.source_name()}] Error navigating to page {page_num}: {e}")
            return False

    def _extract_url_from_onclick(self, onclick: str) -> Optional[str]:
        """
        Extract URL from onclick attribute.

        Example: onclick="window.open('/LegislationDetail.aspx?ID=123', '_blank')"

        Args:
            onclick: onclick attribute value

        Returns:
            Extracted URL or None
        """
        # Look for patterns like window.open('URL', ...) or window.location='URL'
        patterns = [
            r"window\.open\(['\"]([^'\"]+)['\"]",
            r"window\.location\s*=\s*['\"]([^'\"]+)['\"]",
            r"location\.href\s*=\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, onclick)
            if match:
                return match.group(1)

        return None

    def _extract_and_convert_transcript(self, html_content: str) -> Optional[str]:
        """
        Extract transcript div from HTML and convert to markdown using LLM.

        Args:
            html_content: Full HTML page content

        Returns:
            Markdown formatted transcript or None if div not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find the transcript div
            transcript_div = soup.find('div', id='divTranscript')

            if not transcript_div:
                print(f"[{self.source_name()}] Warning: divTranscript not found in HTML")
                return None

            # Get the HTML content of the div
            transcript_html = str(transcript_div)

            # Use non-AI parsing if enabled, otherwise use LLM
            if self.convert_with_ai:
                print(f"[{self.source_name()}] Converting transcript to markdown using LLM...")
                markdown_content = convert_transcript_to_markdown(transcript_html)
            else:
                print(f"[{self.source_name()}] Converting transcript to markdown using non-AI parser...")
                markdown_content = NonAITranscriptParser().convert(transcript_html)

            return markdown_content

        except Exception as e:
            print(f"[{self.source_name()}] Error extracting/converting transcript: {e}")
            return None

