"""
Legistar scraper for SF Board of Supervisors.

Scrapes meeting data from https://sfgov.legistar.com/Calendar.aspx
"""

import re
import time
from datetime import datetime
from typing import Generator, Optional

import pandas as pd
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

    def scrape_members(self):
        pass

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

            # Collect all pages into a single dataframe
            print(f"[{self.source_name()}] Collecting all pages into a single dataframe...")
            all_pages_df = self._collect_all_pages(driver)

            if all_pages_df.empty:
                print(f"[{self.source_name()}] No data found in calendar")
                return

            print(f"[{self.source_name()}] Collected {len(all_pages_df)} rows from all pages")

            # Process transcripts from the combined dataframe
            count = 0
            for transcript_url in self._extract_transcript_urls(all_pages_df, session, incremental, force):
                if limit and count >= limit:
                    return

                try:
                    # Fetch the document
                    print(f"[{self.source_name()}] Fetching: {transcript_url}")
                    driver.get(transcript_url)
                    time.sleep(2)

                    # Get page source
                    page_content = driver.page_source

                    # For transcripts, extract and convert to markdown (if enabled)
                    converted_content = None
                    if self.convert_with_ai:
                        converted_content = self._extract_and_convert_transcript(page_content)

                    # Create Document model
                    doc = Document(
                        source=self.source_name(),
                        url=transcript_url,
                        raw_content=page_content,
                        content_format=ContentFormat.HTML,
                        converted_content=converted_content
                    )

                    count += 1
                    yield doc

                except Exception as e:
                    print(f"[{self.source_name()}] Error fetching {transcript_url}: {e}")
                    continue

            print(f"[{self.source_name()}] Successfully scraped {count} documents")

        finally:
            if driver:
                driver.quit()
    
    def _collect_all_pages(self, driver: webdriver.Chrome) -> pd.DataFrame:
        """
        Collect all pages of the calendar table into a single dataframe.

        Args:
            driver: Selenium WebDriver

        Returns:
            Combined DataFrame from all pages
        """
        all_dfs = []
        page_num = 1

        while True:
            print(f"[{self.source_name()}] Collecting page {page_num}")

            # Get page source and parse with BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Find the calendar grid table
            grid = soup.find('table', id=re.compile(r'gridCalendar'))
            if not grid:
                break

            # Parse table into pandas dataframe
            df = self._parse_table_to_dataframe(grid)
            if df.empty:
                break

            all_dfs.append(df)

            # Try to navigate to next page
            if not self._go_to_next_page(driver, page_num + 1):
                print(f"[{self.source_name()}] No more pages")
                break

            page_num += 1
            time.sleep(1)  # Be polite

        # Combine all dataframes
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            return combined_df
        else:
            return pd.DataFrame()

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

    def _parse_table_to_dataframe(self, table_element) -> pd.DataFrame:
        """
        Parse HTML table into pandas DataFrame.

        Extracts table headings from HTML and converts links to URLs.

        Args:
            table_element: BeautifulSoup table element

        Returns:
            DataFrame with table data
        """
        try:
            # Extract column headings from table header
            thead = table_element.find('thead')
            if not thead:
                return pd.DataFrame()

            print(thead)
            # Get heading cells and extract visible inner HTML
            heading_cells = thead.find_all('th', class_='rgHeader')
            columns = []
            for cell in heading_cells:
                # Get visible inner HTML (text content)
                heading_text = cell.get_text(strip=True)
                columns.append(heading_text)
            print('Columns', columns)

            # Extract table rows
            tbody = table_element.find('tbody', recursive=False)
            if not tbody:
                return pd.DataFrame()

            rows_data = []
            print('Tbody', tbody)
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                row_data = []

                for cell in cells:
                    # Check if cell contains links
                    link = cell.find('a')
                    if link:
                        # Convert link to URL string
                        onclick = link.get('onclick', '')
                        url = self._extract_url_from_onclick(onclick)

                        if url:
                            # Make URL absolute
                            if url.startswith('/'):
                                url = self.BASE_URL + url
                            elif not url.startswith('http'):
                                url = self.BASE_URL + '/' + url
                            row_data.append(url)
                        else:
                            # Fallback to link text if no onclick
                            row_data.append(link.get_text(strip=True))
                    else:
                        # Regular cell content
                        row_data.append(cell.get_text(strip=True))

                rows_data.append(row_data)

            print ('Rows data', rows_data)
            # Create DataFrame
            df = pd.DataFrame(rows_data, columns=columns)
            return df

        except Exception as e:
            print(f"[{self.source_name()}] Error parsing table to dataframe: {e}")
            return pd.DataFrame()

    def _extract_transcript_urls(self, df: pd.DataFrame, session, incremental: bool, force: bool) -> Generator[str, None, None]:
        """
        Extract transcript URLs from the Transcripts column in the dataframe.

        Filters for transcript URLs and checks against database if incremental mode is enabled.

        Args:
            df: DataFrame with table data
            session: SQLAlchemy session for database checks
            incremental: Whether to check database for existing URLs
            force: Whether to force re-scrape

        Yields:
            Transcript URLs to process
        """
        # Find the Transcripts column
        transcript_col = None
        for col in df.columns:
            if 'transcript' in col.lower():
                transcript_col = col
                break

        if transcript_col is None:
            print(f"[{self.source_name()}] Warning: Transcripts column not found in table")
            return

        # Iterate through transcript URLs
        for url in df[transcript_col]:
            if not url or not isinstance(url, str):
                continue

            # Skip if not a URL (shouldn't happen but be safe)
            if not url.startswith('http'):
                continue

            # Check if already in database (incremental by default)
            if incremental and not force and session:
                existing = session.query(Document).filter_by(url=url).first()
                if existing:
                    print(f"[{self.source_name()}] Skipping (already in database): {url}")
                    continue

            yield url

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

