import smtplib

import sqlite3
import os

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from robocorp.tasks import task
from robocorp import browser

from RPA.Excel.Files import Files


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

movie_only_filter = '//search-page-result [@type="movie"]//search-page-media-row'


# ─── Database ────────────────────────────────────────────────────────────────

def init_db():
    """
    Initialize the local SQLite database.

    Creates the `movies` table if it does not already exist.
    The movie title is stored as the PRIMARY KEY to ensure uniqueness.
    """
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

    print(f"[DB] Initialised at: {DB_PATH}")


def save_movie(data: dict):
    """
    Insert or replace a movie record in the database.

    `INSERT OR REPLACE` ensures that if a movie with the same title already exists,
    the new data overwrites the previous record.
    """
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

    print(f"[DB] Saved: {data['title']} ({data['year']})")


def _ndf_record(title: str) -> dict:
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

# ─── Mail Sender ─────────────────────────────────────────────────────────

def send_movie_report():
    """
    Generates a high-fidelity, dashboard-style HTML movie report 
    with rock-solid UI alignment for email clients.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")
        return

    # ── Helper: Pill Generator (The "Secret Sauce" for Email UI) ─────────────
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

    # ── Table Rows Generation ──────────────────────────────────────────────────
    body_rows = ""
    for row in rows:
        data = dict(zip(columns, row))
        
        # Format Rating (Split main rating from long descriptions)
        raw_rating = str(data.get('rating') or 'N/A')
        rating_parts = raw_rating.split('(', 1)
        main_rating = rating_parts[0].strip()
        sub_rating = f"({rating_parts[1]}" if len(rating_parts) > 1 else ""

        # Generate Pills
        toma_pill = make_score_pill("🍅", data.get('tomatometer'))
        aud_pill = make_score_pill("🎟️", data.get('audience_score'))

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
                {data.get('storyline', '')[:160] + '...' if data.get('storyline') and len(data.get('storyline')) > 160 else data.get('storyline')}
            </td>
        </tr>
        """

    # ── Full HTML Email Template ──────────────────────────────────────────────
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

    # ── Email Sending Logic ───────────────────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎬 RT Report: {len(rows)} Movies Synchronized"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print(f"✨ Success! The premium report has been sent to {RECEIVER_EMAIL}")
    except Exception as e:
        print(f"❌ SMTP Error: {e}")

# ─── Browser helpers ─────────────────────────────────────────────────────────

def open_rt_web():
    """
    Open the Rotten Tomatoes homepage.
    """
    browser.goto("https://www.rottentomatoes.com/")


def accept_cookies():
    """
    Accept the cookie banner if it appears.

    The banner may not always be displayed, so any failure is safely ignored.
    """
    page = browser.page()
    try:
        page.click("button:text('Continue')", timeout=5000)
    except Exception:
        pass


def go_back_to_home():
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


# ─── Search & filter ─────────────────────────────────────────────────────────

def process_movie(mov_name):
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

    # Wait for the search box to become visible before interacting with it.
    # Clear any previous text and type the movie title gradually for stability.
    search_input = page.locator("input[placeholder='Search']")
    search_input.wait_for(state="visible", timeout=5000)
    search_input.click()
    search_input.fill("")
    search_input.type(name, delay=50)

    # Give the site a brief chance to render search suggestions.
    # The selector is intentionally flexible to handle minor UI differences.
    try:
        page.wait_for_selector(
            "ul[data-qa='search-results-list'], [class*='search-suggestion']",
            timeout=3000
        )
    except Exception:
        pass

    # Submit the search.
    page.keyboard.press("Enter")

    # Confirm that the search results page has loaded successfully.
    # If not, reset the session and stop processing this title.
    try:
        page.wait_for_load_state("load", timeout=10000)
        page.wait_for_url("**/search**", timeout=10000)
    except Exception as e:
        print(f"[ERROR] Search page did not load for '{name}': {e}")
        go_back_to_home()
        return

    # Ensure search results are present before attempting to filter or match.
    # If no results exist, store an NDF placeholder record and continue.
    try:
        page.wait_for_selector(
            movie_only_filter,
            timeout=5000
        )
    except Exception:
        print(f"[NO RESULTS] No search results found for: {name}")
        save_movie(_ndf_record(name))
        go_back_to_home()
        return

    # Attempt to switch to the Movies tab so that non-movie results are filtered out.
    # Rotten Tomatoes may render this control inside a dynamic drawer, so force-click
    # is used to make interaction more reliable.
    try:
        movies_tab = page.locator("li", has_text="Movies").first
        movies_tab.scroll_into_view_if_needed(timeout=3000)
        movies_tab.click(force=True, timeout=5000)
        page.wait_for_load_state("load", timeout=5000)
        print("[FILTER] Clicked Movies tab")
    except Exception as e:
        print(f"[WARN] Could not click Movies filter, proceeding anyway: {e}")

    # Open the best matching movie details page.
    open_movie_details(mov_name)

    # Always return to the homepage before processing the next movie.
    go_back_to_home()


# ─── Match & open ─────────────────────────────────────────────────────────────

def open_movie_details(mov_name):
    """
    Open the correct movie details page from the search results.

    Matching rules:
    - Only exact title matches are accepted.
    - If multiple exact matches exist, the most recent release year wins.
    - If no valid match is found, an NDF placeholder record is stored.
    """
    page = browser.page()
    target_name = mov_name["Movies"].strip().lower()

    # Ensure the search result rows are present before trying to inspect them.
    try:
        page.wait_for_selector(
            movie_only_filter,
            timeout=7000
        )
    except Exception:
        print(f"[NOT FOUND] Results disappeared for: {mov_name['Movies']}")
        save_movie(_ndf_record(mov_name["Movies"].strip()))
        return

    # Collect all result rows from the search results container.
    results = page.locator(
        movie_only_filter
    ).all()

    if not results:
        print(f"[NOT FOUND] Result list is empty for: {mov_name['Movies']}")
        save_movie(_ndf_record(mov_name["Movies"].strip()))
        return

    # Track the best candidate based on exact title match and latest year.
    best_match_el = None
    latest_year = -1
    matched_year = -1

    for result in results:
        try:
            title_el = result.locator("a[slot='title']")
            title = title_el.inner_text().strip().lower()
        except Exception:
            # Skip malformed or partially rendered rows.
            continue

        # Only allow exact case-insensitive title matches.
        if title != target_name:
            continue

        # Read the release year from the result metadata.
        # If unavailable, use -1 so valid years are always preferred.
        try:
            year = int(result.get_attribute("release-year") or -1)
        except Exception:
            year = -1

        # Prefer the newest exact match if duplicates exist.
        if year > latest_year:
            latest_year = year
            matched_year = year
            best_match_el = title_el

    if not best_match_el:
        print(f"[NOT FOUND] No exact match for: {mov_name['Movies']}")
        save_movie(_ndf_record(mov_name["Movies"].strip()))
        return

    print(f"[FOUND] '{mov_name['Movies']}' ({matched_year}) — opening...")

    # Open the selected movie page.
    best_match_el.click()

    try:
        page.wait_for_load_state("load", timeout=15000)
    except Exception:
        pass

    # Wait for the movie scorecard to appear as confirmation that the details page loaded.
    try:
        page.wait_for_selector("media-scorecard", timeout=8000)
    except Exception:
        print(f"[WARN] Scorecard not found for: {mov_name['Movies']}")

    # Scrape the page and persist the result if successful.
    data = scrape_movie_page(page, mov_name["Movies"].strip(), matched_year)
    if data:
        save_movie(data)


# ─── Scraper ─────────────────────────────────────────────────────────────────

def scrape_movie_page(page, title: str, year: int) -> dict | None:
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
            wrap = page.locator(
                f"div[data-qa='item']:has(rt-text[data-qa='item-label']:text-is('{label}'))"
            )
            wrap.first.wait_for(state="attached", timeout=4000)
            values = wrap.first.locator("[data-qa='item-value']").all()
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
            page.wait_for_selector("review-card", timeout=5000)
        except Exception:
            return [None] * 6

        cards = page.locator("review-card").all()
        results = []

        for card in cards[:6]:
            try:
                name = card.locator("rt-link[slot='name']").inner_text().strip()
                publication = card.locator("rt-link[slot='publication']").inner_text().strip()
                review_text = card.locator("span[slot='content']").inner_text().strip()

                try:
                    sentiment = card.locator("score-icon-critics").get_attribute("sentiment") or "UNKNOWN"
                except Exception:
                    sentiment = "UNKNOWN"

                entry = f"{name} ({publication}) [{sentiment}]: {review_text}"
                results.append(entry)
            except Exception:
                # Preserve list size consistency even if an individual card fails to parse.
                results.append(None)

        # Pad the list so the result always contains exactly six review slots.
        while len(results) < 6:
            results.append(None)

        return results

    # ── Scores ────────────────────────────────────────────────────────────────
    # Read critic and audience scores from the scorecard component.
    tomatometer = safe_text("rt-text[slot='critics-score']")
    audience_score = safe_text("rt-text[slot='audience-score']")

    # ── Storyline ─────────────────────────────────────────────────────────────
    # Read the synopsis / storyline section.
    storyline = safe_text("div[slot='description'] rt-text[slot='content']")

    # ── Info block ────────────────────────────────────────────────────────────
    # Extract structured metadata from the movie details section.
    genre = get_item_by_label("Genre")
    runtime = get_item_by_label("Runtime")
    rating = get_item_by_label("Rating")
    release_date = get_item_by_label("Release Date (Theaters)")

    # ── Critics ───────────────────────────────────────────────────────────────
    # Extract up to six critic reviews from the reviews section.
    critics = scrape_critics()

    # Assemble the final database-ready payload.
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


# ─── Entry point ─────────────────────────────────────────────────────────────

@task
def rts():
    """
    Main Robocorp task entry point.

    Responsibilities:
    - configure browser execution
    - initialize the database
    - open Rotten Tomatoes
    - accept cookies if necessary
    - process all movies from the Excel file
    - send the final email report
    """
    browser.configure(slowmo=100)
    init_db()
    open_rt_web()
    accept_cookies()
    read_movie_data()
    send_movie_report()


def read_movie_data():
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
            process_movie(row)
        except Exception as e:
            # Log the row-level failure and reset the browser state so processing
            # can continue with the next movie.
            print(f"[ERROR] Failed processing '{row.get('Movies', 'unknown')}': {e}")
            go_back_to_home()