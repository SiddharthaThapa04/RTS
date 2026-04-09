from robocorp import browser
from RPA.Excel.Files import Files

from app.browser_helpers import RottenTomatoesBrowser
from app.config import (
    MEDIA_SCORECARD_SELECTOR,
    MOVIE_ONLY_FILTER,
    MOVIES_TAB_SELECTOR,
    MOVIES_TAB_TEXT,
    SEARCH_INPUT_SELECTOR,
    SEARCH_RESULTS_SUGGESTION_SELECTOR,
    TITLE_SELECTOR,
)
from app.database import MovieDatabase
from app.mailer import ReportMailer
from app.scraper import MoviePageScraper
from app.utils import build_ndf_record


class MovieSearchWorkflow:
    def __init__(
        self,
        database: MovieDatabase,
        browser_helper: RottenTomatoesBrowser,
        scraper: MoviePageScraper,
        mailer: ReportMailer,
    ) -> None:
        self.database = database
        self.browser_helper = browser_helper
        self.scraper = scraper
        self.mailer = mailer

    def process_movie(self, mov_name) -> None:
        """
        Execute the end-to-end workflow for a single movie.

        Flow:
        1. Read the movie title from the Excel row.
        2. Search Rotten Tomatoes for the title.
        3. Confirm the results page loaded correctly.
        4. Apply the Movies filter when available.
        5. Open the best-matching result.
        6. Reset the page for the next movie.
        """
        page = browser.page()
        name = mov_name["Movies"].strip()

        print(f"\n[SEARCHING] {name}")

        search_input = page.locator(SEARCH_INPUT_SELECTOR)
        search_input.wait_for(state="visible", timeout=5000)
        search_input.click()
        search_input.fill("")
        search_input.type(name, delay=50)

        try:
            page.wait_for_selector(SEARCH_RESULTS_SUGGESTION_SELECTOR, timeout=3000)
        except Exception:
            pass

        page.keyboard.press("Enter")

        try:
            page.wait_for_load_state("load", timeout=10000)
            page.wait_for_url("**/search**", timeout=10000)
        except Exception as e:
            print(f"[ERROR] Search page did not load for '{name}': {e}")
            self.browser_helper.go_back_to_home()
            return

        try:
            page.wait_for_selector(MOVIE_ONLY_FILTER, timeout=5000)
        except Exception:
            print(f"[NO RESULTS] No search results found for: {name}")
            self.database.save_movie(build_ndf_record(name))
            self.browser_helper.go_back_to_home()
            return

        try:
            movies_tab = page.locator(MOVIES_TAB_SELECTOR, has_text=MOVIES_TAB_TEXT).first
            movies_tab.scroll_into_view_if_needed(timeout=3000)
            movies_tab.click(force=True, timeout=5000)
            page.wait_for_load_state("load", timeout=5000)
            print("[FILTER] Clicked Movies tab")
        except Exception as e:
            print(f"[WARN] Could not click Movies filter, proceeding anyway: {e}")

        self.open_movie_details(mov_name)
        self.browser_helper.go_back_to_home()

    def open_movie_details(self, mov_name) -> None:
        """
        Open the correct movie details page from the search results.

        Matching rules:
        - Only exact title matches are accepted.
        - If multiple exact matches exist, the most recent release year wins.
        - If no valid match is found, an NDF placeholder record is stored.
        """
        page = browser.page()
        target_name = mov_name["Movies"].strip().lower()

        try:
            page.wait_for_selector(MOVIE_ONLY_FILTER, timeout=7000)
        except Exception:
            print(f"[NOT FOUND] Results disappeared for: {mov_name['Movies']}")
            self.database.save_movie(build_ndf_record(mov_name["Movies"].strip()))
            return

        results = page.locator(MOVIE_ONLY_FILTER).all()
        if not results:
            print(f"[NOT FOUND] Result list is empty for: {mov_name['Movies']}")
            self.database.save_movie(build_ndf_record(mov_name["Movies"].strip()))
            return

        best_match_el = None
        latest_year = -1
        matched_year = -1

        for result in results:
            try:
                title_el = result.locator(TITLE_SELECTOR)
                title = title_el.inner_text().strip().lower()
            except Exception:
                continue

            if title != target_name:
                continue

            try:
                year = int(result.get_attribute("release-year") or -1)
            except Exception:
                year = -1

            if year > latest_year:
                latest_year = year
                matched_year = year
                best_match_el = title_el

        if not best_match_el:
            print(f"[NOT FOUND] No exact match for: {mov_name['Movies']}")
            self.database.save_movie(build_ndf_record(mov_name["Movies"].strip()))
            return

        print(f"[FOUND] '{mov_name['Movies']}' ({matched_year}) — opening...")
        best_match_el.click()

        try:
            page.wait_for_load_state("load", timeout=15000)
        except Exception:
            pass

        try:
            page.wait_for_selector(MEDIA_SCORECARD_SELECTOR, timeout=8000)
        except Exception:
            print(f"[WARN] Scorecard not found for: {mov_name['Movies']}")

        data = self.scraper.scrape(page, mov_name["Movies"].strip(), matched_year)
        if data:
            self.database.save_movie(data)

    def read_movie_data(self) -> None:
        """
        Read movie titles from the Excel workbook and process them sequentially.

        Expected workbook structure:
        - file name: `movies.xlsx`
        - sheet name: `data`
        - column name: `Movies`
        """
        excel = Files()
        excel.open_workbook("movies.xlsx")
        worksheet = excel.read_worksheet_as_table("data", header=True)
        excel.close_workbook()

        for row in worksheet:
            try:
                self.process_movie(row)
            except Exception as e:
                print(f"[ERROR] Failed processing '{row.get('Movies', 'unknown')}': {e}")
                self.browser_helper.go_back_to_home()

    def run(self) -> None:
        """
        Main robot workflow.

        Responsibilities:
        - configure browser execution
        - initialize the database
        - open Rotten Tomatoes
        - accept cookies if necessary
        - process all movies from the Excel file
        - send the final email report
        """
        browser.configure(slowmo=100)
        self.database.init_db()
        self.browser_helper.open_home()
        self.browser_helper.accept_cookies()
        self.read_movie_data()
        self.mailer.send_movie_report()
