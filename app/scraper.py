"""Page-level scraping logic for Rotten Tomatoes movie detail pages."""

from app.config import (
    AUDIENCE_SCORE_SELECTOR,
    CRITICS_SCORE_SELECTOR,
    DESCRIPTION_SELECTOR,
    ITEM_VALUE_SELECTOR,
    ITEM_WRAP_SELECTOR_TEMPLATE,
    REVIEW_CARD_SELECTOR,
    REVIEW_CONTENT_SELECTOR,
    REVIEW_NAME_SELECTOR,
    REVIEW_PUBLICATION_SELECTOR,
    REVIEW_SENTIMENT_SELECTOR,
)


class MoviePageScraper:
    """Extracts structured movie data from an open Rotten Tomatoes page."""

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
                    # Build a compact, source-attributed review summary.
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

        # Core scoring data from the hero scorecard.
        tomatometer = safe_text(CRITICS_SCORE_SELECTOR)
        audience_score = safe_text(AUDIENCE_SCORE_SELECTOR)

        # Short-form narrative content for reporting output.
        storyline = safe_text(DESCRIPTION_SELECTOR)

        # Structured metadata from the movie details section.
        genre = get_item_by_label("Genre")
        runtime = get_item_by_label("Runtime")
        rating = get_item_by_label("Rating")
        release_date = get_item_by_label("Release Date (Theaters)")

        # Review cards are optional; the robot pads the schema when they are absent.
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
