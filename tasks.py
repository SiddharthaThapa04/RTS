"""Robocorp entrypoint for the Rotten Tomatoes scraping workflow."""

from robocorp.tasks import task

from app.browser_helpers import RottenTomatoesBrowser
from app.database import MovieDatabase
from app.mailer import ReportMailer
from app.scraper import MoviePageScraper
from app.workflow import MovieSearchWorkflow


@task
def rts():
    """Create the workflow dependencies and execute the full robot."""
    workflow = MovieSearchWorkflow(
        database=MovieDatabase(),
        browser_helper=RottenTomatoesBrowser(),
        scraper=MoviePageScraper(),
        mailer=ReportMailer(),
    )
    workflow.run()
