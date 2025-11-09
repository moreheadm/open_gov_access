"""
Legistar scraper for SF Board of Supervisors.

Scrapes meeting data from https://sfgov.legistar.com/Calendar.aspx
"""

import re
import time
from datetime import datetime
from typing import Generator, Optional, Union

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base import Scraper
from models.database import Document, ContentFormat, Legislation, Official, Meeting, Action, ActionType, VoteType
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

    def __init__(self, headless: bool = True, convert_with_ai: bool = False, use_non_ai_parsing: bool = True, limit: Optional[int] = None, incremental: bool = True):
        """
        Initialize Legistar scraper.

        Args:
            headless: Whether to run browser in headless mode
            convert_with_ai: Whether to convert documents with AI (default: False)
            use_non_ai_parsing: Whether to use non-AI transcript parsing
            limit: Maximum number of documents to scrape
            incremental: Only scrape new documents (not already in database)
        """
        super().__init__()
        self.headless = headless
        self.convert_with_ai = convert_with_ai
        self.limit = limit
        self.incremental = incremental

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

    def scrape_members(self,
                    url: str = "https://sfgov.legistar.com/People.aspx",
                    driver: webdriver.Chrome = None,
                    session: Optional[Session] = None
                    ) -> Generator[Union[Document, Legislation, Official, Meeting, Action], None, None]:

        new_driver = False
        try:
            if not driver:
                new_driver = True
                driver = self._setup_driver()

            driver.get(url)

            time.sleep(3)

            all_members_df = self._collect_all_pages(driver, table_id=r'gridPeople')
            for url in all_members_df['Person Name']:
                yield from self.scrape_member(url, driver, session)


        finally:
            if driver and new_driver:
                driver.quit()

    def scrape_member(self, url: str, driver: webdriver.Chrome, session: Optional[Session] = None
    ) -> Generator[Union[Document, Legislation, Official, Meeting, Action], None, None]:
        """
        Scrape a single member's page for their bio.

        Args:
            url: URL of member's page
            driver: Selenium WebDriver
            session: SQLAlchemy session for database operations

        Yields:
            Document and/or Official models
        """
        new_driver = False
        try:
            if not driver:
                new_driver = True
                driver = self._setup_driver()

            driver.get(url)

            # Wait for page to load
            time.sleep(2)

            # click on link <a class="rtsLink rtsSelected" href="#"><span class="rtsOut"><span class="rtsIn"><span class="rtsTxt">Votes (1438)</span></span></span></a>
            votes_button = driver.find_element(By.XPATH, "//a[contains(@href, 'Votes')]")
            votes_button.click()

            # Wait for page to load
            time.sleep(3)
            votes_df = self._collect_all_pages(driver, table_id='rgMasterTable')

            for legislation_row in votes_df:
                legislation = legislation_row['File #']
                if not isinstance(legislation, dict):
                    continue

                # If legislation not in database yet, scrape it
                if not session.query(Legislation).filter_by(file_number=legislation['text']).first():
                    yield from self.scrape_legislation(legislation['url'], driver, session)

                vote = legislation_row['Vote']

                meeting_url = legislation_row['Meeting Details']
                meeting_file_number = None
                if isinstance(meeting_url, dict):
                    if res := re.search(r'ID=(\d+)', meeting_url['url']):
                        meeting_file_number = res.group(1)

                legislation_file_number = legislation['text']

                # Get meeting ID from database
                meeting_id = session.query(Meeting).filter_by(meeting_file_number=meeting_file_number).first()
                official_id = session.query(Official).filter_by(url=url).first()
                legislation_id = session.query(Legislation).filter_by(file_number=legislation_file_number).first()

                action = Action(
                    legislation_id=legislation_id,
                    meeting_id=meeting_id,
                    official_id=official_id,
                    action_type=ActionType.VOTE,
                    vote=vote
                )
                yield action

        finally:
            if driver and new_driver:
                driver.quit()

    def scrape_meeting(self, url: str, driver: webdriver.Chrome, session: Optional[Session] = None
    ) -> Generator[Union[Document, Legislation, Official, Meeting, Action], None, None]:
        """
        Scrape a single meeting's page for its details and agenda items.

        Args:
            url: URL of meeting's page
            driver: Selenium WebDriver
            session: SQLAlchemy session for database operations

        Yields:
            Document and Meeting models
        """
        new_driver = False
        try:
            if not driver:
                new_driver = True
                driver = self._setup_driver()

            # Navigate to the meeting page
            print(f"[{self.source_name()}] Fetching meeting: {url}")
            driver.get(url)
            time.sleep(2)

            # Get page source and parse
            page_content = driver.page_source
            soup = BeautifulSoup(page_content, 'html.parser')

            # Extract meeting details
            meeting_data = self._extract_meeting_details(soup, url)

            if not meeting_data:
                print(f"[{self.source_name()}] Could not extract meeting details from {url}")
                return

            meeting_file_number = None
            if match := re.search(r'ID=(\d+)', url):
                meeting_file_number = match.group(1)

            # Create and yield Meeting model
            meeting = Meeting(
                meeting_file_number=meeting_file_number,
                meeting_datetime=meeting_data.get('meeting_datetime'),
                meeting_type=meeting_data.get('meeting_type', 'Committee Hearing')
            )
            yield meeting

        finally:
            if driver and new_driver:
                driver.quit()

    def scrape_legislation(self, url: str, driver: webdriver.Chrome, session: Optional[Session] = None
    ) -> Generator[Union[Document, Legislation, Official, Meeting, Action], None, None]:
        """
        Scrape a single legislation's page for its details.

        Args:
            url: URL of legislation's page
            driver: Selenium WebDriver
            session: SQLAlchemy session for database operations

        Yields:
            Document and/or Legislation models
        """
        new_driver = False
        try:
            if not driver:
                new_driver = True
                driver = self._setup_driver()

            # Navigate to the legislation page
            print(f"[{self.source_name()}] Fetching legislation: {url}")
            driver.get(url)
            time.sleep(2)

            # Get page source and parse
            page_content = driver.page_source
            soup = BeautifulSoup(page_content, 'html.parser')

            # Extract legislation details
            legislation_data = self._extract_legislation_details(soup, url)

            if not legislation_data:
                print(f"[{self.source_name()}] Could not extract legislation details from {url}")
                return

            # Create Legislation model
            legislation = Legislation(
                file_number=legislation_data['file_number'],
                title=legislation_data['title'],
                description=legislation_data['description'],
                legislation_type=legislation_data['type'],
                category=legislation_data['category'],
                status=legislation_data['status'],
                url=legislation_data['url'],
            )

            yield legislation

        except Exception as e:
            print(f"[{self.source_name()}] Error scraping legislation {url}: {e}")

        finally:
            if driver and new_driver:
                driver.quit()





    def scrape(
        self,
        department: str = "BOS and Committees",
        year: str = "Last Month",
        session: Optional[Session] = None
    ) -> Generator[Union[Document, Legislation, Official, Meeting, Action], None, None]:
        """
        Main scraping method (delegates to scrape_meetings).

        Args:
            department: Department filter (default: "BOS and Committees")
            year: Year filter (default: "2025")
            session: SQLAlchemy session for checking existing URLs

        Yields:
            Database models (Document, Legislation, Official, Meeting, or Action)
        """
        yield from self.scrape_meetings(
            department=department,
            year=year,
            session=session
        )

        #yield from self.scrape_members(
        #    session=session
        #)

    def scrape_meetings(
        self,
        url: str = CALENDAR_URL,
        department: str = "BOS and Committees",
        year: str = "2025",
        session: Optional[Session] = None,
    ) -> Generator[Union[Document, Legislation, Official, Meeting, Action], None, None]:
        """
        Main scraping method.

        Navigates Legistar calendar, filters by department and year,
        and yields database models.

        Args:
            department: Department filter (default: "BOS and Committees")
            year: Year filter (default: "2025")
            session: SQLAlchemy session for checking existing URLs

        Yields:
            Database models (Document, Legislation, Official, Meeting, or Action)
        """
        print(f"[{self.source_name()}] Starting Legistar scrape...")
        print(f"[{self.source_name()}] Department: {department}, Year: {year}")

        driver = None
        try:
            driver = self._setup_driver()

            # Navigate to calendar page
            print(f"[{self.source_name()}] Navigating to {url}")
            driver.get(url)

            time.sleep(2)

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
            time.sleep(2)

            # Collect all pages into a single dataframe
            print(f"[{self.source_name()}] Collecting all pages into a single dataframe...")
            all_pages_df = self._collect_all_pages(driver)

            if all_pages_df.empty:
                print(f"[{self.source_name()}] No data found in calendar")
                return

            print(f"[{self.source_name()}] Collected {len(all_pages_df)} rows from all pages")

            # First, scrape meeting details from the "Meeting Details" column
            count = 0
            print(all_pages_df['Meeting Details'])
            for meeting_detail in all_pages_df['Meeting Details']:
                # Check if it's a dict with URL (from link parsing)
                if isinstance(meeting_detail, dict) and 'url' in meeting_detail:
                    meeting_url = meeting_detail['url']
                    print(f"[{self.source_name()}] Scraping meeting: {meeting_url}")
                    try:
                        yield from self.scrape_meeting(meeting_url, driver, session)
                        count += 1
                    except Exception as e:
                        print(f"[{self.source_name()}] Error scraping meeting {meeting_url}: {e}")
                        continue

            # Process transcripts from the combined dataframe
            for transcript_url, transcript_text, meeting_detail in self._extract_transcript_urls(all_pages_df, session):
                if self.limit and count >= self.limit:
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

                    # Extract meeting ID from meeting_detail if available
                    meeting_id = None
                    if meeting_detail and isinstance(meeting_detail, dict) and 'url' in meeting_detail:
                        # Extract meeting ID from the meeting detail URL
                        meeting_url = meeting_detail['url']
                        if match := re.search(r'ID=(\d+)', meeting_url):
                            meeting_id_str = match.group(1)
                            # Query database for the meeting with this ID
                            if session:
                                meeting = session.query(Meeting).filter_by(meeting_file_number=meeting_id_str).first()
                                if meeting:
                                    meeting_id = meeting.id

                    # Create Document model linked to meeting
                    doc = Document(
                        source=self.source_name(),
                        url=transcript_url,
                        raw_content=page_content,
                        content_format=ContentFormat.HTML,
                        converted_content=converted_content,
                        doc_metadata={'link_text': transcript_text} if transcript_text else None,
                        meeting_id=meeting_id
                    )

                    count += 1
                    yield doc

                except Exception as e:
                    print(f"[{self.source_name()}] Error fetching {transcript_url}: {e}")
                    continue

            print(f"[{self.source_name()}] Successfully scraped {count} objects")

        finally:
            if driver:
                driver.quit()

    def _collect_all_pages(self, driver: webdriver.Chrome,
                           table_id: str = r'gridCalendar') -> pd.DataFrame:
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
            grid = soup.find('table', id=re.compile(table_id))
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
                        link_text = link.get_text(strip=True)

                        # Also check for href attribute (some links don't use onclick)
                        if not url:
                            url = link.get('href', '')

                        if url:
                            # Make URL absolute
                            if url.startswith('/'):
                                url = self.BASE_URL + url
                            elif not url.startswith('http'):
                                url = self.BASE_URL + '/' + url
                            # Store as dict with both URL and text
                            row_data.append({'url': url, 'text': link_text})
                        else:
                            # Fallback to link text if no onclick
                            row_data.append(link_text)
                    else:
                        # Regular cell content
                        row_data.append(cell.get_text(strip=True))

                rows_data.append(row_data)

            # Create DataFrame
            df = pd.DataFrame(rows_data, columns=columns)
            return df

        except Exception as e:
            print(f"[{self.source_name()}] Error parsing table to dataframe: {e}")
            return pd.DataFrame()

    def _extract_transcript_urls(self, df: pd.DataFrame, session) -> Generator[tuple, None, None]:
        """
        Extract transcript URLs from the Transcripts column in the dataframe.

        Filters for transcript URLs and checks against database if incremental mode is enabled.

        Args:
            df: DataFrame with table data
            session: SQLAlchemy session for database checks

        Yields:
            Tuples of (url, text, meeting_detail) for each transcript to process
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

        # Iterate through transcript URLs with their corresponding meeting details
        for idx, item in df[transcript_col].items():
            if not item:
                continue

            # Handle both dict format (url + text) and string format (just url)
            if isinstance(item, dict):
                url = item.get('url')
                text = item.get('text', '')
            elif isinstance(item, str):
                url = item
                text = ''
            else:
                continue

            # Skip if not a URL (shouldn't happen but be safe)
            if not url or not isinstance(url, str) or not url.startswith('http'):
                continue

            # Check if already in database (incremental by default)
            if self.incremental and session:
                existing = session.query(Document).filter_by(url=url).first()
                if existing:
                    print(f"[{self.source_name()}] Skipping (already in database): {url}")
                    continue

            # Get the meeting detail from the same row
            meeting_detail = df.loc[idx, 'Meeting Details'] if 'Meeting Details' in df.columns else None

            yield (url, text, meeting_detail)

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

    def _extract_meeting_details(self, soup: BeautifulSoup, url: str) -> Optional[dict]:
        """
        Extract meeting details from the meeting detail page.

        Args:
            soup: BeautifulSoup object of the page
            url: URL of the meeting page

        Returns:
            Dictionary with extracted meeting data or None if extraction fails
        """
        try:
            details = {
                'url': url,
                'meeting_name': None,
                'meeting_date': None,
                'meeting_time': None,
                'meeting_location': None,
                'agenda_status': None,
                'minutes_status': None,
                'agenda_url': None,
                'minutes_url': None,
                'agenda_items': []
            }

            # Extract meeting name
            name_link = soup.find('a', id=re.compile(r'hypName'))
            if name_link:
                details['meeting_name'] = name_link.get_text(strip=True)

            # Extract meeting date
            date_span = soup.find('span', id=re.compile(r'lblDate$'))
            print('Date:', date_span)
            if date_span:
                date_text = date_span.get_text(strip=True)
                try:
                    details['meeting_date'] = datetime.strptime(date_text, '%m/%d/%Y').date()
                except ValueError:
                    details['meeting_date'] = date_text

            # Extract meeting time
            time_span = soup.find('span', id=re.compile(r'lblTime'))
            if time_span:
                details['meeting_time'] = time_span.get_text(strip=True)

            details['meeting_datetime'] = f"{details['meeting_date']} {details['meeting_time']}"

            # Extract meeting location
            location_span = soup.find('span', id=re.compile(r'lblLocation'))
            if location_span:
                details['meeting_location'] = location_span.get_text(strip=True)

            # Extract agenda status
            agenda_status_span = soup.find('span', id=re.compile(r'lblAgendaStatus'))
            if agenda_status_span:
                details['agenda_status'] = agenda_status_span.get_text(strip=True)

            # Extract minutes status
            minutes_status_span = soup.find('span', id=re.compile(r'lblMinutesStatus'))
            if minutes_status_span:
                details['minutes_status'] = minutes_status_span.get_text(strip=True)

            # Extract agenda link
            agenda_link = soup.find('a', id=re.compile(r'hypAgenda'))
            if agenda_link and agenda_link.get('href'):
                details['agenda_url'] = agenda_link.get('href')

            # Extract minutes link
            minutes_link = soup.find('a', id=re.compile(r'hypMinutes'))
            if minutes_link and minutes_link.get('href') and 'Not available' not in minutes_link.get_text():
                details['minutes_url'] = minutes_link.get('href')

            # Extract agenda items from the grid table
            grid_table = soup.find('table', id=re.compile(r'gridMain_ctl00'))
            if grid_table:
                tbody = grid_table.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr', class_=re.compile(r'rgRow|rgAltRow')):
                        cells = row.find_all('td')
                        if len(cells) >= 7:
                            item = {
                                'file_number': cells[0].get_text(strip=True),
                                'version': cells[1].get_text(strip=True),
                                'agenda_number': cells[2].get_text(strip=True),
                                'name': cells[3].get_text(strip=True),
                                'type': cells[4].get_text(strip=True),
                                'status': cells[5].get_text(strip=True),
                                'title': cells[6].get_text(strip=True)
                            }
                            details['agenda_items'].append(item)

            return details

        except Exception as e:
            print(f"[{self.source_name()}] Error extracting meeting details: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_legislation_details(self, soup: BeautifulSoup, url: str) -> Optional[dict]:
        """
        Extract legislation details from the legislation detail page.

        Args:
            soup: BeautifulSoup object of the page
            url: URL of the legislation page

        Returns:
            Dictionary with extracted legislation data or None if extraction fails
        """
        try:
            details = {
                'url': url,
                'file_number': None,
                'title': None,
                'status': None,
                'introduced_date': None,
                'in_control': None,
                'sponsors': [],
                'attachments': [],
                'history': []
            }

            # Extract file number from page title or URL
            # File number is typically in format "250792"
            match = re.search(r'File\s*#\s*(\d+)', soup.get_text())
            if match:
                details['file_number'] = match.group(1)

            # Extract title
            title_span = soup.find('span', id=re.compile(r'lblTitle2'))
            if title_span:
                details['title'] = title_span.get_text(strip=True)

            # Extract status
            status_span = soup.find('span', id=re.compile(r'lblStatus2'))
            if status_span:
                details['status'] = status_span.get_text(strip=True)

            # Extract introduced date
            intro_span = soup.find('span', id=re.compile(r'lblIntroduced2'))
            if intro_span:
                details['introduced_date'] = intro_span.get_text(strip=True)

            # Extract in control (committee)
            control_link = soup.find('a', id=re.compile(r'hypInControlOf2'))
            if control_link:
                details['in_control'] = control_link.get_text(strip=True)

            # Extract sponsors
            sponsors_span = soup.find('span', id=re.compile(r'lblSponsors2'))
            if sponsors_span:
                sponsor_links = sponsors_span.find_all('a')
                for link in sponsor_links:
                    sponsor_name = link.get_text(strip=True)
                    sponsor_url = link.get('href', '')
                    details['sponsors'].append({
                        'name': sponsor_name,
                        'url': sponsor_url
                    })

            # Extract attachments
            attachments_span = soup.find('span', id=re.compile(r'lblAttachments2'))
            if attachments_span:
                attachment_links = attachments_span.find_all('a')
                for link in attachment_links:
                    attachment_name = link.get_text(strip=True)
                    attachment_url = link.get('href', '')
                    details['attachments'].append({
                        'name': attachment_name,
                        'url': attachment_url
                    })

            # Extract history (actions)
            history_table = soup.find('table', id=re.compile(r'gridLegislation'))
            if history_table:
                tbody = history_table.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            history_entry = {
                                'date': cells[0].get_text(strip=True),
                                'version': cells[1].get_text(strip=True),
                                'action_by': cells[2].get_text(strip=True),
                                'action': cells[3].get_text(strip=True),
                                'result': cells[4].get_text(strip=True) if len(cells) > 4 else None
                            }
                            details['history'].append(history_entry)

            return details

        except Exception as e:
            print(f"[{self.source_name()}] Error extracting legislation details: {e}")
            return None

