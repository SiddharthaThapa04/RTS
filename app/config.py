"""Centralized configuration and selector definitions for the robot."""

import os


# SQLite database lives in the current working directory by default so runs are
# self-contained and easy to inspect locally.
DB_PATH = os.path.join(os.getcwd(), "movies.db")


# SMTP credentials used by the final report email.
# Store real secrets in a secure secret manager before running in production.

SENDER_EMAIL = "your-sender-email"         # Gmail account used to send the report
SENDER_PASSWORD = "your-sender-password-(NOT LOGIN PASSWORD)"       # Gmail App Password for SMTP authentication
RECEIVER_EMAIL = "your-receiver-email"       # Destination email for the scrape report

# Selectors and literals used by the browser automation layer.
MOVIE_ONLY_FILTER = '//search-page-result [@type="movie"]//search-page-media-row'
SEARCH_INPUT_SELECTOR = "input[placeholder='Search']"
SEARCH_RESULTS_SUGGESTION_SELECTOR = (
    "ul[data-qa='search-results-list'], [class*='search-suggestion']"
)
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
ITEM_WRAP_SELECTOR_TEMPLATE = (
    "div[data-qa='item']:has(rt-text[data-qa='item-label']:text-is('{label}'))"
)
ITEM_VALUE_SELECTOR = "[data-qa='item-value']"
