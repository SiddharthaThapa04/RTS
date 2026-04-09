from robocorp import browser

from app.config import CONTINUE_BUTTON_SELECTOR


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
