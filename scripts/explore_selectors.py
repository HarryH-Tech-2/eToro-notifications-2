"""One-off helper to discover post selectors on an eToro profile.

Usage: python scripts/explore_selectors.py https://www.etoro.com/people/harryh1993
"""
import sys
from playwright.sync_api import sync_playwright


def main(url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headed so you can see
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        print("Page loaded. Inspect the feed in the browser devtools.")
        print("Look for: stable [data-etoro-automation-id=...] on post containers,")
        print("and stable permalink href patterns (e.g. /posts/<id>).")
        print("When done, press Enter to exit.")
        input()
        browser.close()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.etoro.com/people/harryh1993"
    main(url)
