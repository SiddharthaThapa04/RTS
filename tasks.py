import os
import smtplib
import sqlite3

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from RPA.Excel.Files import Files
from robocorp import browser
from robocorp.tasks import task


# Absolute path for the local SQLite database file.
# The database is created in the current working directory if it does not exist.
DB_PATH = os.path.join(os.getcwd(), "movies.db")


# ─── Email config ─────────────────────────────────────────────────────────────
# SMTP sender and recipient configuration used for the final HTML report email.
# Replace these placeholder values with valid credentials before execution.


SENDER_EMAIL = "your-sender-email"         # Gmail account used to send the report
SENDER_PASSWORD = "your-sender-password-(NOT LOGIN PASSWORD)"       # Gmail App Password for SMTP authentication
RECEIVER_EMAIL = "your-receiver-email"       # Destination email for the scrape report


# ─── Inventory ────────────────────────────────────────────────────────────────

MOVIE_ONLY_FILTER = '//search-page-result [@type="movie"]//search-page-media-row'
SEARCH_INPUT_SELECTOR = "input[placeholder='Search']"
SEARCH_RESULTS_SUGGESTION_SELECTOR = "ul[data-qa='search-results-list'], [class*='search-suggestion']"
MOVIES_TAB_SELECTOR = "li"
MOVIES_TAB_TEXT = "Movies"
CONTINUE_BUTTON_SELECTOR = "button:text('Continue')"
TITLE_SELECTOR = "a[slot='title']"
MEDIA_SCORECARD_SELECTOR = "media-scorecard"
CRITICS_SCORE_SELECTOR = "rt-text[slot='critics-score']"
AUDIENCE_SCORE_SELECTOR = "rt-text[slot='audience-score']"
DESCRIPTION_SELECTOR = "div[slot='description'] rt-text[slot='content']"
REVIEW_CARD_SELECTOR = "review-card"
REVIEW_NAME_SELECTOR = "rt-link[slot='name']"
REVIEW_PUBLICATION_SELECTOR = "rt-link[slot='publication']"
REVIEW_CONTENT_SELECTOR = "span[slot='content']"
REVIEW_SENTIMENT_SELECTOR = "score-icon-critics"
ITEM_WRAP_SELECTOR_TEMPLATE = "div[data-qa='item']:has(rt-text[data-qa='item-label']:text-is('{label}'))"
ITEM_VALUE_SELECTOR = "[data-qa='item-value']"


class MovieDatabase:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """
        Initialize the local SQLite database.

        Creates the `movies` table if it does not already exist.
        The movie title is stored as the PRIMARY KEY to ensure uniqueness.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    title             TEXT PRIMARY KEY,
                    year              INTEGER,
                    tomatometer       TEXT,
                    audience_score    TEXT,
                    storyline         TEXT,
                    genre             TEXT,
                    runtime           TEXT,
                    rating            TEXT,
                    release_date      TEXT,
                    critic_1          TEXT,
                    critic_2          TEXT,
                    critic_3          TEXT,
                    critic_4          TEXT,
                    critic_5          TEXT,
                    critic_6          TEXT
                )
            """)
            conn.commit()

        print(f"[DB] Initialised at: {self.db_path}")

    def save_movie(self, data: dict) -> None:
        """
        Insert or replace a movie record in the database.

        `INSERT OR REPLACE` ensures that if a movie with the same title already exists,
        the new data overwrites the previous record.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO movies
                    (title, year, tomatometer, audience_score, storyline,
                     genre, runtime, rating, release_date,
                     critic_1, critic_2, critic_3, critic_4, critic_5, critic_6)
                VALUES
                    (:title, :year, :tomatometer, :audience_score, :storyline,
                     :genre, :runtime, :rating, :release_date,
                     :critic_1, :critic_2, :critic_3, :critic_4, :critic_5, :critic_6)
            """, data)
            conn.commit()

        print(f"[DB] Saved: {data['title']} ({data['year']})")


class ReportMailer:
    def __init__(
        self,
        db_path: str = DB_PATH,
        sender_email: str = SENDER_EMAIL,
        sender_password: str = SENDER_PASSWORD,
        receiver_email: str = RECEIVER_EMAIL,
    ) -> None:
        self.db_path = db_path
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_email = receiver_email

    def _ndf_record(self, title: str) -> dict:
        """
        Build a standard fallback record for movies that could not be found.

        `NDF` is used here as a placeholder value meaning "No Data Found".
        This keeps the database output structurally consistent even when a movie
        cannot be matched or scraped successfully.
        """
        return {
            "title": title,
            "year": -1,
            "tomatometer": "NDF",
            "audience_score": "NDF",
            "storyline": "NDF",
            "genre": "NDF",
            "runtime": "NDF",
            "rating": "NDF",
            "release_date": "NDF",
            "critic_1": "NDF",
            "critic_2": "NDF",
            "critic_3": "NDF",
            "critic_4": "NDF",
            "critic_5": "NDF",
            "critic_6": "NDF",
        }

    def send_movie_report(self) -> None:
        """
        Generates a high-fidelity, dashboard-style HTML movie report
        with rock-solid UI alignment for email clients.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM movies")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        except Exception as e:
            print(f"Database Error: {e}")
            return

        def make_score_pill(label, score_val):
            """Creates a stable, rounded badge using nested tables."""
            if not score_val or score_val == "NDF" or score_val == "N/A":
                bg, text, border = "#f1f5f9", "#94a3b8", "#e2e8f0"
            else:
                try:
                    score = int(str(score_val).replace("%", ""))
                    if score >= 60:
                        bg, text, border = "#f0fdf4", "#16a34a", "#bbf7d0"
                    else:
                        bg, text, border = "#fef2f2", "#dc2626", "#fecaca"
                except ValueError:
                    bg, text, border = "#f1f5f9", "#94a3b8", "#e2e8f0"

            return f"""
            <table cellpadding="0" cellspacing="0" border="0" style="margin: 4px auto;">
                <tr>
                    <td style="background-color: {bg}; border: 1px solid {border}; border-radius: 12px; padding: 4px 10px; line-height: 1;">
                        <span style="color: {text}; font-size: 11px; font-weight: bold; font-family: sans-serif; white-space: nowrap;">
                            {label} {score_val}
                        </span>
                    </td>
                </tr>
            </table>"""

        body_rows = ""
        for row in rows:
            data = dict(zip(columns, row))

            raw_rating = str(data.get("rating") or "N/A")
            rating_parts = raw_rating.split("(", 1)
            main_rating = rating_parts[0].strip()
            sub_rating = f"({rating_parts[1]}" if len(rating_parts) > 1 else ""

            toma_pill = make_score_pill("🍅", data.get("tomatometer"))
            aud_pill = make_score_pill("🎟️", data.get("audience_score"))

            storyline = data.get("storyline", "")
            storyline = storyline[:160] + "..." if storyline and len(storyline) > 160 else storyline

            body_rows += f"""
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 20px 15px; vertical-align: top; width: 220px;">
                    <div style="font-weight: 700; color: #1e293b; font-size: 15px; margin-bottom: 2px;">{data.get('title')}</div>
                    <div style="color: #94a3b8; font-size: 12px;">Year: {data.get('year')}</div>
                </td>

                <td style="padding: 20px 10px; vertical-align: middle; text-align: center; width: 140px;">
                    <table cellpadding="0" cellspacing="0" border="0" style="margin: 0 auto;">
                        <tr>
                            <td style="border: 1.5px solid #475569; border-radius: 4px; padding: 3px 6px;">
                                <span style="color: #475569; font-size: 11px; font-weight: 800; font-family: sans-serif;">{main_rating}</span>
                            </td>
                        </tr>
                    </table>
                    <div style="color: #94a3b8; font-size: 10px; margin-top: 6px; line-height: 1.2; font-style: italic;">{sub_rating}</div>
                </td>

                <td style="padding: 20px 10px; vertical-align: middle; text-align: center; width: 120px;">
                    <div style="color: #475569; font-size: 12px; font-weight: 600; font-family: sans-serif;">{data.get('release_date') or '---'}</div>
                </td>

                <td style="padding: 10px; vertical-align: middle; text-align: center; width: 120px;">
                    {toma_pill}
                    {aud_pill}
                </td>

                <td style="padding: 20px 15px; color: #64748b; font-size: 13px; line-height: 1.5; vertical-align: top;">
                    {storyline}
                </td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="margin:0; padding:0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="padding: 40px 10px;">
                <tr>
                    <td align="center">
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 1000px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">

                            <tr>
                                <td style="background-color: #0f172a; padding: 35px 40px; text-align: left;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">
                                        <span style="color: #ef4444;">RT</span> MOVIE INTELLIGENCE
                                    </h1>
                                    <p style="margin: 8px 0 0; color: #94a3b8; font-size: 13px; letter-spacing: 0.5px;">
                                        {len(rows)} TITLES PROCESSED &nbsp; | &nbsp; DATABASE SYNC COMPLETE
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding: 0;">
                                    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="border-collapse: collapse;">
                                        <thead>
                                            <tr style="background-color: #f8fafc; border-bottom: 2px solid #f1f5f9;">
                                                <th style="text-align: left; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Movie Title</th>
                                                <th style="text-align: center; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Rating</th>
                                                <th style="text-align: center; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Release</th>
                                                <th style="text-align: center; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Scores</th>
                                                <th style="text-align: left; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Storyline</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {body_rows}
                                        </tbody>
                                    </table>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding: 30px; background-color: #f8fafc; text-align: center; border-top: 1px solid #f1f5f9;">
                                    <p style="margin: 0; color: #cbd5e1; font-size: 11px; letter-spacing: 1px;">
                                        AUTOMATED REPORT • GENERATED BY RT-SCRAPER-BOT
                                        <br>
                                        This report scans for 'Movie' only, TV Series are not included in final report.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎬 RT Report: {len(rows)} Movies Synchronized"
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            print(f"✨ Success! The premium report has been sent to {self.receiver_email}")
        except Exception as e:
            print(f"❌ SMTP Error: {e}")


class RottenTomatoesBrowser:
    def open_home(self) -> None:
        browser.goto("https://www.rottentomatoes.com/")

    def accept_cookies(self) -> None:
        """
        Accept the cookie banner if it appears.

        The banner may not always be displayed, so any failure is safely ignored.
        """
        page = browser.page()
        try:
            page.click(CONTINUE_BUTTON_SELECTOR, timeout=5000)
        except Exception:
            pass

    def go_back_to_home(self) -> None:
        """
        Return to the Rotten Tomatoes homepage.

        This acts as a reset mechanism so each movie search begins from a stable,
        predictable page state.
        """
        print("[RESET] Going back to home...")
        try:
            browser.goto("https://www.rottentomatoes.com/")
            browser.page().wait_for_load_state("load", timeout=10000)
        except Exception as e:
            print(f"[ERROR] Could not navigate home: {e}")


class MoviePageScraper:
    def scrape(self, page, title: str, year: int) -> dict | None:
        """
        Scrape all required movie data from the currently open Rotten Tomatoes page.

        Returns a dictionary containing:
        - title and year
        - critic and audience scores
        - storyline
        - metadata fields
        - up to six critic review summaries
        """
        print(f"[SCRAPING] {title}...")

        def safe_text(selector, timeout=4000):
            """
            Safely extract text from the first matching element.

            Returns:
                - stripped inner text if the element is found
                - None if the element is missing or unreadable
            """
            try:
                el = page.locator(selector).first
                el.wait_for(state="attached", timeout=timeout)
                return el.inner_text().strip()
            except Exception:
                return None

        def get_item_by_label(label: str):
            """
            Retrieve a metadata field from the details section using its visible label.

            Supports fields that may contain multiple values, such as Genre,
            by joining all matching values into a comma-separated string.
            """
            try:
                wrap = page.locator(ITEM_WRAP_SELECTOR_TEMPLATE.format(label=label))
                wrap.first.wait_for(state="attached", timeout=4000)
                values = wrap.first.locator(ITEM_VALUE_SELECTOR).all()
                texts = [v.inner_text().strip() for v in values if v.inner_text().strip()]
                return ", ".join(texts) if texts else None
            except Exception:
                return None

        def scrape_critics():
            """
            Scrape up to six critic review cards.

            Output format:
                "Name (Publication) [SENTIMENT]: review text"

            If no review cards are found, returns a list of six None values.
            """
            try:
                page.wait_for_selector(REVIEW_CARD_SELECTOR, timeout=5000)
            except Exception:
                return [None] * 6

            cards = page.locator(REVIEW_CARD_SELECTOR).all()
            results = []

            for card in cards[:6]:
                try:
                    name = card.locator(REVIEW_NAME_SELECTOR).inner_text().strip()
                    publication = card.locator(REVIEW_PUBLICATION_SELECTOR).inner_text().strip()
                    review_text = card.locator(REVIEW_CONTENT_SELECTOR).inner_text().strip()

                    try:
                        sentiment = card.locator(REVIEW_SENTIMENT_SELECTOR).get_attribute("sentiment") or "UNKNOWN"
                    except Exception:
                        sentiment = "UNKNOWN"

                    entry = f"{name} ({publication}) [{sentiment}]: {review_text}"
                    results.append(entry)
                except Exception:
                    results.append(None)

            while len(results) < 6:
                results.append(None)

            return results

        tomatometer = safe_text(CRITICS_SCORE_SELECTOR)
        audience_score = safe_text(AUDIENCE_SCORE_SELECTOR)
        storyline = safe_text(DESCRIPTION_SELECTOR)
        genre = get_item_by_label("Genre")
        runtime = get_item_by_label("Runtime")
        rating = get_item_by_label("Rating")
        release_date = get_item_by_label("Release Date (Theaters)")
        critics = scrape_critics()

        data = {
            "title": title,
            "year": year,
            "tomatometer": tomatometer,
            "audience_score": audience_score,
            "storyline": storyline,
            "genre": genre,
            "runtime": runtime,
            "rating": rating,
            "release_date": release_date,
            "critic_1": critics[0],
            "critic_2": critics[1],
            "critic_3": critics[2],
            "critic_4": critics[3],
            "critic_5": critics[4],
            "critic_6": critics[5],
        }

        print(f"[SCRAPED] {data}")
        return data


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
            self.database.save_movie(self.mailer._ndf_record(name))
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
            self.database.save_movie(self.mailer._ndf_record(mov_name["Movies"].strip()))
            return

        results = page.locator(MOVIE_ONLY_FILTER).all()
        if not results:
            print(f"[NOT FOUND] Result list is empty for: {mov_name['Movies']}")
            self.database.save_movie(self.mailer._ndf_record(mov_name["Movies"].strip()))
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
            self.database.save_movie(self.mailer._ndf_record(mov_name["Movies"].strip()))
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


@task
def rts():
    """Robocorp task entry point."""
    workflow = MovieSearchWorkflow(
        database=MovieDatabase(),
        browser_helper=RottenTomatoesBrowser(),
        scraper=MoviePageScraper(),
        mailer=ReportMailer(),
    )
    workflow.run()
